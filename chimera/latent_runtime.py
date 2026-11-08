"""Production construction for the optional Latent Language 3.0 runtime.

No random encoders or untrained model fallbacks are installed. Pretrained encoders
load their real public weights; learned projections/dynamics load only validated
checkpoints produced by the training APIs.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .encoders import (
    CalibratedSensorEncoder,
    HuggingFaceAudioEncoder,
    HuggingFaceCLIPImageEncoder,
    HuggingFaceTextEncoder,
)
from .latent_language import CognitiveActionGateway, EncoderRegistry, LatentLanguageCoordinator
from .latent_training import MultimodalProjectionModel
from .learned_dynamics import TorchMorphogeneticDynamics


def build_latent_language(
    toolbox: Any,
    organism: Any,
    *,
    alignment_checkpoint: str | None = None,
    dynamics_checkpoint: str | None = None,
    text_model_id: str = "bert-base-uncased",
    image_model_id: str = "openai/clip-vit-base-patch32",
    audio_model_id: str = "facebook/wav2vec2-base",
    sensor_calibration: Mapping[str, tuple[float, float]] | None = None,
    sensor_channel_names: Sequence[str] | None = None,
    device: str = "cpu",
) -> tuple[LatentLanguageCoordinator, CognitiveActionGateway]:
    """Load actual encoders/checkpoints and bind them to this organism's one gateway."""
    if device not in {"cpu", "cuda"}:
        raise ValueError("device must be 'cpu' or 'cuda'")
    registry = EncoderRegistry()
    registry.register("text", HuggingFaceTextEncoder(text_model_id, device=device))
    registry.register("image", HuggingFaceCLIPImageEncoder(image_model_id, device=device))

    alignment_model = None
    if alignment_checkpoint:
        alignment_model = MultimodalProjectionModel(device=device)
        alignment_model.load_checkpoint(alignment_checkpoint)
        if "audio" in alignment_model.validated_modalities:
            registry.register(
                "audio",
                HuggingFaceAudioEncoder(
                    alignment_model.project_audio_slot,
                    model_id=audio_model_id,
                    device=device,
                ),
            )

    if sensor_calibration is not None:
        names = tuple(sensor_channel_names or sorted(sensor_calibration))
        registry.register("sensor", CalibratedSensorEncoder(names, sensor_calibration))

    dynamics = None
    if dynamics_checkpoint:
        dynamics = TorchMorphogeneticDynamics(device=device)
        dynamics.load_checkpoint(dynamics_checkpoint)

    coordinator = LatentLanguageCoordinator(
        registry,
        alignment_model=alignment_model,
        dynamics=dynamics,
    )
    gateway = CognitiveActionGateway(toolbox, coordinator.workspace, organism)
    return coordinator, gateway
