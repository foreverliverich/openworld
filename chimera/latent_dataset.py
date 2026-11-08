"""Opt-in, append-only training-data capture for Latent Language.

This is a derived experiment log, not a second organism state store. ISCE and
RealityEngine remain authoritative. Each session is isolated by trajectory_id,
and training/validation splits are performed by whole session to prevent adjacent
timestep leakage.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

from .latent_language import LATENT_DIMENSIONS

DATASET_SCHEMA_VERSION = 1
ALIGNMENT_DIMS = {"text": 768, "image": 512, "audio": 768}


class LatentDatasetError(RuntimeError):
    """The trajectory dataset is malformed, incomplete or incompatible."""


def _finite_vector(values: Any, dimension: int, label: str) -> list[float]:
    if not isinstance(values, (list, tuple)) or len(values) != dimension:
        raise LatentDatasetError(f"{label} must contain exactly {dimension} values")
    result = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise LatentDatasetError(f"{label} values must be finite numbers")
        number = float(value)
        if not math.isfinite(number):
            raise LatentDatasetError(f"{label} values must be finite")
        result.append(number)
    return result


def _vector_digest(values: Sequence[float]) -> str:
    encoded = json.dumps(list(values), separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class LatentTrajectoryRecorder:
    """Append one validated latent snapshot per successful cognition cycle."""

    def __init__(
        self, path: str | Path, *, organism_id: str = "chimera",
        trajectory_id: str | None = None,
    ) -> None:
        if not isinstance(organism_id, str) or not organism_id.strip():
            raise ValueError("organism_id must be a non-empty string")
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.organism_id = organism_id.strip()
        self.trajectory_id = trajectory_id or uuid.uuid4().hex
        if not isinstance(self.trajectory_id, str) or not self.trajectory_id.strip():
            raise ValueError("trajectory_id must be a non-empty string")
        self.trajectory_id = self.trajectory_id.strip()
        self._lock = threading.Lock()
        self._sequence_index = 0
        self._previous_vector_digest: str | None = None
        self.last_record_digest: str | None = None

    def record(
        self, *, latent_vector: Sequence[float], latent_state_digest: str,
        timestamp: float, world_revision: int,
        modality_embeddings: Mapping[str, Mapping[str, Any]],
        alignment_pair: bool = False,
        selected_proposal_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        vector = _finite_vector(latent_vector, LATENT_DIMENSIONS, "latent_vector")
        if not isinstance(latent_state_digest, str) or not latent_state_digest:
            raise LatentDatasetError("latent_state_digest is required")
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise LatentDatasetError("timestamp must be numeric")
        timestamp = float(timestamp)
        if not math.isfinite(timestamp):
            raise LatentDatasetError("timestamp must be finite")
        if isinstance(world_revision, bool) or not isinstance(world_revision, int) or world_revision < 0:
            raise LatentDatasetError("world_revision must be a non-negative integer")
        if not isinstance(alignment_pair, bool):
            raise LatentDatasetError("alignment_pair must be boolean")

        modalities: dict[str, Any] = {}
        for modality, item in modality_embeddings.items():
            if modality not in {"text", "image", "audio", "sensor"} or not isinstance(item, Mapping):
                raise LatentDatasetError(f"Invalid modality training record: {modality}")
            embedding = item.get("training_embedding", item.get("embedding"))
            if not isinstance(embedding, (list, tuple)) or not embedding:
                raise LatentDatasetError(f"{modality} training embedding is missing")
            training_values = []
            for value in embedding:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise LatentDatasetError(f"{modality} training embedding must be numeric")
                number = float(value)
                if not math.isfinite(number):
                    raise LatentDatasetError(f"{modality} training embedding must be finite")
                training_values.append(number)
            confidence = item.get("confidence", 1.0)
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise LatentDatasetError(f"{modality} confidence must be numeric")
            confidence = float(confidence)
            if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise LatentDatasetError(f"{modality} confidence must be in [0, 1]")
            source_id = item.get("source_id")
            encoder_id = item.get("encoder_id")
            if not isinstance(source_id, str) or not source_id:
                raise LatentDatasetError(f"{modality} source_id is required")
            if not isinstance(encoder_id, str) or not encoder_id:
                raise LatentDatasetError(f"{modality} encoder_id is required")
            modalities[modality] = {
                "training_embedding": training_values,
                "runtime_embedding": list(item.get("embedding", training_values)),
                "confidence": confidence,
                "source_id": source_id,
                "encoder_id": encoder_id,
                "shared_space": item.get("shared_space"),
            }

        if alignment_pair:
            if "text" not in modalities or "image" not in modalities:
                raise LatentDatasetError(
                    "alignment_pair requires paired text and image observations in the same cycle"
                )
            if len(modalities["text"]["training_embedding"]) != 768:
                raise LatentDatasetError("Alignment text training embeddings must be 768-D")
            if len(modalities["image"]["training_embedding"]) != 512:
                raise LatentDatasetError("Alignment image training embeddings must be 512-D")
            if "audio" in modalities and len(modalities["audio"]["training_embedding"]) != 768:
                raise LatentDatasetError("Alignment audio training embeddings must be 768-D")

        with self._lock:
            vector_digest = _vector_digest(vector)
            record = {
                "schema_version": DATASET_SCHEMA_VERSION,
                "organism_id": self.organism_id,
                "trajectory_id": self.trajectory_id,
                "sequence_index": self._sequence_index,
                "timestamp": timestamp,
                "world_revision": world_revision,
                "latent_dimension": LATENT_DIMENSIONS,
                "latent_vector": vector,
                "latent_state_digest": latent_state_digest,
                "vector_digest": vector_digest,
                "previous_vector_digest": self._previous_vector_digest,
                "modalities": modalities,
                "alignment_pair": alignment_pair,
                "selected_proposal_ids": list(selected_proposal_ids),
            }
            line = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
                    handle.flush()
            except OSError as exc:
                raise LatentDatasetError(f"Cannot append latent trajectory record: {exc}") from exc
            self._sequence_index += 1
            self._previous_vector_digest = vector_digest
            self.last_record_digest = hashlib.sha256(line.encode("utf-8")).hexdigest()
            return record


def load_trajectory_sessions(path: str | Path) -> dict[str, list[list[float]]]:
    """Load and integrity-check complete sessions from the JSONL experiment log."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LatentDatasetError(f"Invalid JSON on dataset line {line_number}") from exc
            if not isinstance(record, dict) or record.get("schema_version") != DATASET_SCHEMA_VERSION:
                raise LatentDatasetError(f"Unsupported record schema on line {line_number}")
            trajectory_id = record.get("trajectory_id")
            if not isinstance(trajectory_id, str) or not trajectory_id:
                raise LatentDatasetError(f"Missing trajectory_id on line {line_number}")
            grouped.setdefault(trajectory_id, []).append(record)

    sessions: dict[str, list[list[float]]] = {}
    for trajectory_id, records in grouped.items():
        records.sort(key=lambda item: item.get("sequence_index", -1))
        vectors: list[list[float]] = []
        previous_digest = None
        previous_timestamp = None
        for expected_index, record in enumerate(records):
            if record.get("sequence_index") != expected_index:
                raise LatentDatasetError(
                    f"Trajectory {trajectory_id} has a missing or duplicate sequence index"
                )
            if record.get("latent_dimension") != LATENT_DIMENSIONS:
                raise LatentDatasetError(f"Trajectory {trajectory_id} has an incompatible latent dimension")
            timestamp = record.get("timestamp")
            if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
                raise LatentDatasetError(f"Trajectory {trajectory_id} has an invalid timestamp")
            timestamp = float(timestamp)
            if not math.isfinite(timestamp) or (
                previous_timestamp is not None and timestamp <= previous_timestamp
            ):
                raise LatentDatasetError(f"Trajectory {trajectory_id} timestamps must increase strictly")
            vector = _finite_vector(record.get("latent_vector"), LATENT_DIMENSIONS, "latent_vector")
            digest = _vector_digest(vector)
            if record.get("vector_digest") != digest:
                raise LatentDatasetError(f"Trajectory {trajectory_id} vector digest mismatch")
            if record.get("previous_vector_digest") != previous_digest:
                raise LatentDatasetError(f"Trajectory {trajectory_id} continuity chain mismatch")
            vectors.append(vector)
            previous_digest = digest
            previous_timestamp = timestamp
        if len(vectors) >= 2:
            sessions[trajectory_id] = vectors
    if not sessions:
        raise LatentDatasetError("No complete trajectory sessions with at least two samples were found")
    return sessions


def split_trajectory_sessions(
    sessions: Mapping[str, Sequence[Sequence[float]]], *,
    validation_fraction: float = 0.2, seed: str = "chimera-v1",
) -> tuple[list[list[list[float]]], list[list[list[float]]]]:
    """Deterministically split by whole organism session, never adjacent rows."""
    if isinstance(validation_fraction, bool) or not isinstance(validation_fraction, (int, float)):
        raise LatentDatasetError("validation_fraction must be numeric")
    fraction = float(validation_fraction)
    if not math.isfinite(fraction) or not 0.05 <= fraction <= 0.5:
        raise LatentDatasetError("validation_fraction must be in [0.05, 0.5]")
    if len(sessions) < 2:
        raise LatentDatasetError("At least two independent trajectory sessions are required")
    ordered = sorted(
        sessions.items(),
        key=lambda item: hashlib.sha256(f"{seed}:{item[0]}".encode()).hexdigest(),
    )
    validation_count = max(1, min(len(ordered) - 1, round(len(ordered) * fraction)))
    validation_ids = {key for key, _ in ordered[:validation_count]}
    train = [list(map(list, values)) for key, values in sessions.items() if key not in validation_ids]
    validation = [list(map(list, values)) for key, values in sessions.items() if key in validation_ids]
    return train, validation


def load_alignment_sessions(
    path: str | Path, *, include_audio: bool = False,
) -> dict[str, dict[str, list[list[float]]]]:
    """Load explicitly paired text/image cycles, optionally requiring raw 768-D audio."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LatentDatasetError(f"Invalid JSON on dataset line {line_number}") from exc
            if record.get("schema_version") != DATASET_SCHEMA_VERSION:
                raise LatentDatasetError(f"Unsupported record schema on line {line_number}")
            if record.get("alignment_pair") is True:
                grouped.setdefault(record["trajectory_id"], []).append(record)

    sessions: dict[str, dict[str, list[list[float]]]] = {}
    for trajectory_id, records in grouped.items():
        records.sort(key=lambda item: item["sequence_index"])
        rows = {"text": [], "image": [], "audio": []}
        for record in records:
            modalities = record.get("modalities", {})
            if not {"text", "image"}.issubset(modalities):
                raise LatentDatasetError(f"Alignment pair in {trajectory_id} is missing text or image")
            rows["text"].append(_finite_vector(
                modalities["text"]["training_embedding"], 768, "paired text embedding"
            ))
            rows["image"].append(_finite_vector(
                modalities["image"]["training_embedding"], 512, "paired image embedding"
            ))
            if include_audio:
                if "audio" not in modalities:
                    raise LatentDatasetError(
                        f"Audio alignment requested but {trajectory_id} has a pair without audio"
                    )
                rows["audio"].append(_finite_vector(
                    modalities["audio"]["training_embedding"], 768, "paired audio embedding"
                ))
        if len(rows["text"]) >= 2:
            if include_audio and len(rows["audio"]) != len(rows["text"]):
                raise LatentDatasetError(f"Audio pairs are not row-aligned in {trajectory_id}")
            if not include_audio:
                rows.pop("audio")
            sessions[trajectory_id] = rows
    if not sessions:
        raise LatentDatasetError("No explicitly aligned text/image sessions with at least two pairs were found")
    return sessions


def merge_alignment_sessions(
    sessions: Mapping[str, Mapping[str, Sequence[Sequence[float]]]],
) -> dict[str, list[list[float]]]:
    """Concatenate already session-split aligned rows without mixing modalities."""
    if not sessions:
        raise LatentDatasetError("No alignment sessions were supplied")
    keys = set.intersection(*(set(value) for value in sessions.values()))
    if not {"text", "image"}.issubset(keys):
        raise LatentDatasetError("Alignment sessions require text and image")
    merged = {key: [] for key in keys}
    for session in sessions.values():
        lengths = {len(session[key]) for key in keys}
        if len(lengths) != 1:
            raise LatentDatasetError("Alignment session modalities are not row-aligned")
        for key in keys:
            merged[key].extend([list(row) for row in session[key]])
    if len(merged["text"]) < 2:
        raise LatentDatasetError("At least two aligned pairs are required")
    return merged
