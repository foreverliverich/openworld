"""Production modality encoder adapters for Latent Language 3.0.

Heavy model dependencies are lazy/optional. Adapters load actual pretrained
weights; they never substitute random or hash vectors when a model is unavailable.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence
import io
import math

from .latent_language import LatentLanguageError


class EncoderDependencyError(RuntimeError):
    pass


class SharedSpaceEmbedding:
    """Aligned embedding for cross-modal comparison, outside ISCE latent slots."""

    def __init__(self, modality: str, embedding: Sequence[float], shared_space: str):
        self.modality = modality
        self.embedding = tuple(float(v) for v in embedding)
        self.shared_space = shared_space
        if not self.embedding or not all(math.isfinite(v) for v in self.embedding):
            raise LatentLanguageError("Shared-space embedding must be finite and non-empty")


class HuggingFaceTextEncoder:
    """BERT-family mean-pooled text encoder with a 768-dimensional contract."""

    encoder_id = "hf-bert-base-uncased"
    shared_space = None

    def __init__(self, model_id: str = "bert-base-uncased", *, device: str = "cpu"):
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise EncoderDependencyError(
                "Install the 'latent' extra (torch and transformers) to load text models"
            ) from exc
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModel.from_pretrained(model_id).to(device).eval()
        self.device = device
        self.encoder_id = f"hf:{model_id}"
        hidden = int(self.model.config.hidden_size)
        if hidden != 768:
            raise EncoderDependencyError(
                f"{model_id} emits {hidden} dimensions; language contract requires 768"
            )

    def encode(self, payload: Any) -> Sequence[float]:
        if not isinstance(payload, str) or not payload.strip():
            raise LatentLanguageError("Text encoder requires non-empty text")
        batch = self.tokenizer(
            payload, return_tensors="pt", truncation=True, max_length=512,
            padding=True,
        )
        batch = {key: value.to(self.device) for key, value in batch.items()}
        with self.torch.inference_mode():
            output = self.model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1).to(output.dtype)
            pooled = (output * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            pooled = self.torch.nn.functional.normalize(pooled, p=2, dim=-1)
        return tuple(float(v) for v in pooled[0].cpu().tolist())


class HuggingFaceCLIPImageEncoder:
    """CLIP image encoder; image and CLIP text outputs share the declared space."""

    encoder_id = "hf-clip-vit-base-patch32"
    shared_space = "openai-clip-vit-base-patch32"

    def __init__(
        self, model_id: str = "openai/clip-vit-base-patch32", *, device: str = "cpu"
    ):
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise EncoderDependencyError(
                "Install the 'latent' extra (torch and transformers) to load CLIP"
            ) from exc
        self.torch = torch
        self.processor = CLIPProcessor.from_pretrained(model_id)
        self.model = CLIPModel.from_pretrained(model_id).to(device).eval()
        self.device = device
        self.encoder_id = f"hf:{model_id}"

    def encode_aligned(self, payload: Any) -> SharedSpaceEmbedding:
        return SharedSpaceEmbedding("image", self.encode(payload), self.shared_space)

    def encode(self, payload: Any) -> Sequence[float]:
        # Accept a PIL image or a path readable by PIL; raw bytes are not silently decoded.
        try:
            from PIL import Image
            image = Image.open(io.BytesIO(payload)) if isinstance(payload, bytes) else (Image.open(payload) if isinstance(payload, str) else payload)
            if not isinstance(image, Image.Image):
                raise TypeError("payload is not a PIL image or image path")
            image = image.convert("RGB")
        except Exception as exc:
            raise LatentLanguageError(f"Unable to decode image input: {exc}") from exc
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self.torch.inference_mode():
            features = self.model.get_image_features(**inputs)
            features = self.torch.nn.functional.normalize(features, p=2, dim=-1)
        values = tuple(float(v) for v in features[0].cpu().tolist())
        if len(values) != 512:
            raise EncoderDependencyError("CLIP image embedding must be 512-dimensional")
        return values


class HuggingFaceCLIPTextEncoder:
    """512-D CLIP text embedding aligned with HuggingFaceCLIPImageEncoder."""

    encoder_id = "hf-clip-vit-base-patch32-text"
    shared_space = "openai-clip-vit-base-patch32"

    def __init__(
        self, model_id: str = "openai/clip-vit-base-patch32", *, device: str = "cpu"
    ):
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise EncoderDependencyError(
                "Install the 'latent' extra (torch and transformers) to load CLIP"
            ) from exc
        self.torch = torch
        self.processor = CLIPProcessor.from_pretrained(model_id)
        self.model = CLIPModel.from_pretrained(model_id).to(device).eval()
        self.device = device
        self.encoder_id = f"hf:{model_id}:text"

    def encode_aligned(self, payload: Any) -> SharedSpaceEmbedding:
        return SharedSpaceEmbedding("text", self.encode(payload), self.shared_space)

    def encode(self, payload: Any) -> Sequence[float]:
        if not isinstance(payload, str) or not payload.strip():
            raise LatentLanguageError("CLIP text encoder requires non-empty text")
        inputs = self.processor(text=[payload], return_tensors="pt", padding=True,
                                truncation=True)
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self.torch.inference_mode():
            features = self.model.get_text_features(**inputs)
            features = self.torch.nn.functional.normalize(features, p=2, dim=-1)
        return tuple(float(v) for v in features[0].cpu().tolist())


class HuggingFaceAudioEncoder:
    """Wav2Vec2 feature extractor with a required trained 768→128 projection.

    The projection is deliberately mandatory: truncating a 768-D speech vector to
    128 dimensions would destroy the source-defined audio representation without
    a learned reduction.
    """

    def __init__(
        self, projection: Any, model_id: str = "facebook/wav2vec2-base",
        *, device: str = "cpu",
    ):
        try:
            import torch
            from transformers import AutoModel, AutoProcessor
        except ImportError as exc:
            raise EncoderDependencyError(
                "Install the 'latent' extra (torch and transformers) to load audio models"
            ) from exc
        if projection is None or not callable(projection):
            raise EncoderDependencyError("A trained 768→128 audio projection is required")
        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModel.from_pretrained(model_id).to(device).eval()
        if int(self.model.config.hidden_size) != 768:
            raise EncoderDependencyError("Wav2Vec2 model must emit 768-D hidden states")
        self.projection = projection
        self.device = device
        self.encoder_id = f"hf:{model_id}+trained-audio-projection"

    def encode(self, payload: Any) -> Sequence[float]:
        # payload = {"audio": mono_float_samples, "sampling_rate": int}
        if not isinstance(payload, Mapping) or "audio" not in payload or "sampling_rate" not in payload:
            raise LatentLanguageError("Audio payload requires audio samples and sampling_rate")
        audio = payload["audio"]
        sampling_rate = int(payload["sampling_rate"])
        if sampling_rate <= 0 or len(audio) < 400:
            raise LatentLanguageError("Audio requires a valid rate and at least 400 samples")
        waveform = self.torch.as_tensor(audio, dtype=self.torch.float32)
        if waveform.ndim != 1 or not bool(self.torch.isfinite(waveform).all().item()):
            raise LatentLanguageError("Audio must be a finite mono waveform")
        if float(waveform.abs().max().item()) > 1.0:
            raise LatentLanguageError("Audio samples must be normalized to [-1, 1]")
        target_rate = int(self.processor.feature_extractor.sampling_rate)
        if sampling_rate != target_rate:
            target_length = max(1, round(waveform.numel() * target_rate / sampling_rate))
            waveform = self.torch.nn.functional.interpolate(
                waveform.reshape(1, 1, -1), size=target_length,
                mode="linear", align_corners=False,
            ).reshape(-1)
            sampling_rate = target_rate
        inputs = self.processor(
            waveform.cpu().tolist(), sampling_rate=sampling_rate,
            return_tensors="pt", padding=True
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self.torch.inference_mode():
            hidden = self.model(**inputs).last_hidden_state.mean(dim=1)
            hidden = self.torch.nn.functional.normalize(hidden, p=2, dim=-1)
            projected = self.projection(hidden)
            projected = self.torch.nn.functional.normalize(projected, p=2, dim=-1)
        values = tuple(float(v) for v in projected[0].cpu().tolist())
        if len(values) != 128:
            raise EncoderDependencyError("Audio projection must return 128 dimensions")
        return values


class CalibratedSensorEncoder:
    """Calibrated physical sensor vector; all 64 channels must be explicitly named."""

    encoder_id = "calibrated-sensor-v1"
    shared_space = None

    def __init__(self, channel_names: Sequence[str], calibration: Mapping[str, tuple[float, float]]):
        if len(channel_names) != 64 or len(set(channel_names)) != 64:
            raise LatentLanguageError("Sensor encoder requires 64 unique channel names")
        missing = set(channel_names) - set(calibration)
        if missing:
            raise LatentLanguageError(f"Missing sensor calibration for: {sorted(missing)}")
        self.channel_names = tuple(channel_names)
        self.calibration = dict(calibration)
        for name, (low, high) in self.calibration.items():
            if not high > low:
                raise LatentLanguageError(f"Invalid calibration range for {name}")

    def encode(self, payload: Any) -> Sequence[float]:
        if not isinstance(payload, Mapping):
            raise LatentLanguageError("Sensor payload must be a channel mapping")
        missing = set(self.channel_names) - set(payload)
        if missing:
            raise LatentLanguageError(f"Missing sensor channels: {sorted(missing)}")
        values = []
        for name in self.channel_names:
            low, high = self.calibration[name]
            value = float(payload[name])
            if not math.isfinite(value):
                raise LatentLanguageError(f"Sensor channel {name} is non-finite")
            values.append(max(-1.0, min(1.0, 2.0 * (value - low) / (high - low) - 1.0)))
        return tuple(values)
