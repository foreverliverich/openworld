"""Trainable cross-modal projection heads for paired text/image/audio data.

The encoders produce modality-specific features. This module learns projections
into a shared 512-D comparison space using symmetric InfoNCE, and learns the
source-defined 128-D audio subspace with a reconstruction-constrained bottleneck.
"""
from __future__ import annotations

from typing import Any, Mapping

from .latent_language import LatentLanguageError


class AlignmentTrainingError(RuntimeError):
    pass


def _torch_modules():
    try:
        import torch
        from torch import nn
        import torch.nn.functional as functional
    except ImportError as exc:
        raise AlignmentTrainingError(
            "Multimodal alignment training requires PyTorch; install the 'latent' extra"
        ) from exc
    return torch, nn, functional


class MultimodalProjectionModel:
    """Trainable text/image/audio alignment and audio compression."""

    def __init__(
        self, *, text_dim: int = 768, image_dim: int = 512,
        audio_dim: int = 768, shared_dim: int = 512, audio_slot_dim: int = 128,
        seed: int = 29, device: str = "cpu",
    ):
        torch, nn, _ = _torch_modules()
        if (text_dim, image_dim, audio_dim, shared_dim, audio_slot_dim) != (
            768, 512, 768, 512, 128
        ):
            raise AlignmentTrainingError("Projection dimensions must match Latent Language 3.0 schema")
        torch.manual_seed(seed)
        self.torch = torch
        self.device = device
        self.text_projection = nn.Linear(text_dim, shared_dim, bias=False).to(device)
        self.image_projection = nn.Linear(image_dim, shared_dim, bias=False).to(device)
        self.audio_projection = nn.Linear(audio_dim, shared_dim, bias=False).to(device)
        self.audio_compressor = nn.Sequential(
            nn.Linear(audio_dim, 256), nn.GELU(), nn.Linear(256, audio_slot_dim)
        ).to(device)
        self.audio_reconstructor = nn.Linear(audio_slot_dim, audio_dim).to(device)
        self.trained = False
        self.audio_trained = False
        self.validated = False
        self.history: list[dict[str, float]] =

    def project_audio_slot(self, audio_hidden):
        """Callable adapter for HuggingFaceAudioEncoder's 768→128 projection."""
        if not self.audio_trained or not self.validated:
            raise AlignmentTrainingError("Audio bottleneck requires paired training and held-out validation")
        return self.audio_compressor(audio_hidden)

    def _batch(self, value: Any, width: int, name: str):
        torch = self.torch
        tensor = torch.as_tensor(value, dtype=torch.float32, device=self.device)
        if tensor.ndim != 2 or tensor.shape[1] != width:
            raise AlignmentTrainingError(f"{name} batch must have shape [N, {width}]")
        if not bool(torch.isfinite(tensor).all().item()):
            raise AlignmentTrainingError(f"{name} batch contains non-finite values")
        return tensor

    @staticmethod
    def _symmetric_info_nce(functional, left, right, temperature: float):
        logits = left @ right.transpose(0, 1) / temperature
        labels = left.new_tensor(range(left.shape[0]), dtype=__import__("torch").long)
        return 0.5 * (
            functional.cross_entropy(logits, labels)
            + functional.cross_entropy(logits.transpose(0, 1), labels)
        )

    def fit(
        self, pairs: Mapping[str, Any], *, epochs: int = 20,
        batch_size: int = 32, learning_rate: float = 1e-3,
        temperature: float = 0.07,
    ) -> list[dict[str, float]]:
        torch, _, functional = _torch_modules()
        if "text" not in pairs or "image" not in pairs:
            raise AlignmentTrainingError("Paired text and image embeddings are required")
        text = self._batch(pairs["text"], 768, "text")
        image = self._batch(pairs["image"], 512, "image")
        if text.shape[0] != image.shape[0] or text.shape[0] < 2:
            raise AlignmentTrainingError("Text/image pairs must align and contain at least 2 rows")
        audio = None
        if "audio" in pairs:
            audio = self._batch(pairs["audio"], 768, "audio")
            if audio.shape[0] != text.shape[0]:
                raise AlignmentTrainingError("Audio pairs must align row-for-row with text")
        if epochs < 1 or batch_size < 2 or learning_rate <= 0 or temperature <= 0:
            raise AlignmentTrainingError("Invalid alignment training hyperparameters")
        parameters = (
            list(self.text_projection.parameters()) +
            list(self.image_projection.parameters()) +
            list(self.audio_projection.parameters()) +
            list(self.audio_compressor.parameters()) +
            list(self.audio_reconstructor.parameters())
        )
        optimizer = torch.optim.AdamW(parameters, lr=learning_rate, weight_decay=1e-4)
        history = []
        for epoch in range(epochs):
            order = torch.randperm(text.shape[0], device=self.device)
            epoch_loss = 0.0
            sum_text_image = 0.0
            sum_text_audio = 0.0
            sum_audio_reconstruction = 0.0
            steps = 0
            for start in range(0, text.shape[0], batch_size):
                indices = order[start:start + batch_size]
                if indices.numel() < 2:
                    continue
                t, im = text[indices], image[indices]
                tp = functional.normalize(self.text_projection(t), dim=-1)
                ip = functional.normalize(self.image_projection(im), dim=-1)
                loss = self._symmetric_info_nce(functional, tp, ip, temperature)
                audio_loss = torch.zeros((), device=self.device)
                reconstruction_loss = torch.zeros((), device=self.device)
                if audio is not None:
                    au = audio[indices]
                    ap = functional.normalize(self.audio_projection(au), dim=-1)
                    audio_loss = self._symmetric_info_nce(functional, tp, ap, temperature)
                    compressed = self.audio_compressor(au)
                    reconstructed = self.audio_reconstructor(compressed)
                    reconstruction_loss = functional.mse_loss(reconstructed, au)
                total = loss + audio_loss + 0.1 * reconstruction_loss
                optimizer.zero_grad(set_to_none=True)
                total.backward()
                torch.nn.utils.clip_grad_norm_(parameters, 1.0)
                optimizer.step()
                epoch_loss += float(total.detach().cpu())
                sum_text_image += float(loss.detach().cpu())
                sum_text_audio += float(audio_loss.detach().cpu())
                sum_audio_reconstruction += float(reconstruction_loss.detach().cpu())
                steps += 1
            history.append({
                "epoch": float(epoch + 1),
                "loss": epoch_loss / max(1, steps),
                "text_image_loss": sum_text_image / max(1, steps),
                "text_audio_loss": sum_text_audio / max(1, steps),
                "audio_reconstruction_loss": sum_audio_reconstruction / max(1, steps),
            })
        self.history.extend(history)
        self.trained = True
        if audio is not None:
            self.audio_trained = True
        return history

    def evaluate(self, pairs: Mapping[str, Any]) -> dict[str, float]:
        torch, _, functional = _torch_modules()
        text = self._batch(pairs["text"], 768, "text")
        image = self._batch(pairs["image"], 512, "image")
        if text.shape[0] != image.shape[0] or text.shape[0] < 2:
            raise AlignmentTrainingError("Evaluation pairs must align and contain at least 2 rows")
        if "audio" in pairs and len(pairs["audio"]) != text.shape[0]:
            raise AlignmentTrainingError("Audio evaluation pairs must align row-for-row")
        self.text_projection.eval()
        self.image_projection.eval()
        with torch.inference_mode():
            t = functional.normalize(self.text_projection(text), dim=-1)
            im = functional.normalize(self.image_projection(image), dim=-1)
            similarity = t @ im.transpose(0, 1)
            recall1 = (similarity.argmax(dim=1) == torch.arange(
                similarity.shape[0], device=self.device
            )).float().mean()
            metrics = {
                "text_to_image_recall_at_1": float(recall1.cpu()),
                "paired_cosine": float(torch.diagonal(similarity).mean().cpu()),
                "examples": float(text.shape[0]),
            }
            if "audio" in pairs:
                audio = self._batch(pairs["audio"], 768, "audio")
                a = functional.normalize(self.audio_projection(audio), dim=-1)
                audio_similarity = t @ a.transpose(0, 1)
                metrics["text_to_audio_recall_at_1"] = float((
                    audio_similarity.argmax(dim=1) == torch.arange(
                        audio_similarity.shape[0], device=self.device
                    )
                ).float().mean().cpu())
                compressed = self.audio_compressor(audio)
                reconstructed = self.audio_reconstructor(compressed)
                metrics["audio_reconstruction_mse"] = float(
                    functional.mse_loss(reconstructed, audio).cpu()
                )
        self.validated = True
        return metrics

    def save_checkpoint(self, path: str) -> None:
        if not self.trained or not self.validated:
            raise AlignmentTrainingError("Cannot save untrained or unvalidated projection heads")
        self.torch.save({
            "schema_version": 1, "dimensions": [768, 512, 768, 512, 128],
            "text_projection": self.text_projection.state_dict(),
            "image_projection": self.image_projection.state_dict(),
            "audio_projection": self.audio_projection.state_dict(),
            "audio_compressor": self.audio_compressor.state_dict(),
            "audio_reconstructor": self.audio_reconstructor.state_dict(),
            "history": self.history, "audio_trained": self.audio_trained,
            "validated": self.validated,
        }, path)

    def load_checkpoint(self, path: str) -> None:
        checkpoint = self.torch.load(path, map_location=self.device, weights_only=True)
        if checkpoint.get("schema_version") != 1 or checkpoint.get("dimensions") != [
            768, 512, 768, 512, 128
        ]:
            raise AlignmentTrainingError("Projection checkpoint schema mismatch")
        for name in (
            "text_projection", "image_projection", "audio_projection",
            "audio_compressor", "audio_reconstructor",
        ):
            getattr(self, name).load_state_dict(checkpoint[name], strict=True)
        self.history = list(checkpoint.get("history", []))
        self.audio_trained = bool(checkpoint.get("audio_trained", False))
        self.validated = bool(checkpoint.get("validated", False))
        if not self.validated:
            raise AlignmentTrainingError("Projection checkpoint has no validation evidence")
        self.trained = True
