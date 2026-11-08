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
from .latent_language import (
    CognitiveActionGateway, CognitiveSpecialist, CreativeSpecialist, EmotionSpecialist,
    EncoderRegistry, LatentLanguageCoordinator, MemorySpecialist, SocialSpecialist,
    SpatialSpecialist, TemporalSpecialist,
)
from .latent_training import MultimodalProjectionModel
from .learned_dynamics import TorchMorphogeneticDynamics
from .ollama_specialist import OllamaReasoningSpecialist
from .ollama_creative_specialist import OllamaCreativeSpecialist
from .latent_dataset import LatentTrajectoryRecorder


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
    ollama_model: str | None = None,
    ollama_creative_model: str | None = None,
    ollama_base_url: str = "http://127.0.0.1:11434",
    ollama_timeout: float = 30.0,
    trajectory_log: str | None = None,
    trajectory_organism_id: str = "chimera",
) -> tuple[LatentLanguageCoordinator, CognitiveActionGateway]:
    """Load actual encoders/checkpoints and bind them to this organism's one gateway."""
    if device not in {"cpu", "cuda"}:
        raise ValueError("device must be 'cpu' or 'cuda'")
    registry = EncoderRegistry()
    registry.register("text", HuggingFaceTextEncoder(text_model_id, device=device))
    registry.register("image", HuggingFaceCLIPImageEncoder(image_model_id, device=device))

    alignment_model = None
    if alignment_checkpoint:
        alignment_model = MultimodalProjectionModel(
            device=device,
            encoder_manifest={
                "text": f"hf:{text_model_id}",
                "image": f"hf:{image_model_id}",
                "audio": f"hf:{audio_model_id}",
            },
        )
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

    specialists = None
    if ollama_model or ollama_creative_model:
        specialist_list = [
            EmotionSpecialist(),
            CognitiveSpecialist(),
            MemorySpecialist(),
            SocialSpecialist(),
            TemporalSpecialist(),
            SpatialSpecialist(),
            CreativeSpecialist(),
        ]
        if ollama_model:
            specialist_list.append(OllamaReasoningSpecialist(
                ollama_model, base_url=ollama_base_url, timeout=ollama_timeout,
            ))
        if ollama_creative_model:
            specialist_list.append(OllamaCreativeSpecialist(
                ollama_creative_model, base_url=ollama_base_url,
                timeout=max(ollama_timeout, 45.0),
            ))
        specialists = tuple(specialist_list)
    trajectory_recorder = (
        LatentTrajectoryRecorder(trajectory_log, organism_id=trajectory_organism_id)
        if trajectory_log else None
    )
    coordinator = LatentLanguageCoordinator(
        registry,
        specialists=specialists,
        alignment_model=alignment_model,
        dynamics=dynamics,
        trajectory_recorder=trajectory_recorder,
    )
    gateway = CognitiveActionGateway(toolbox, coordinator.workspace, organism)
    return coordinator, gateway
