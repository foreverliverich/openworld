"""Grounded conversion from RealityEngine observations into ISCE inputs.

This adapter owns no persistent state. Its compact previous-observation token
lives in the existing ISCE self-model outcome field, so reloads preserve the
comparison baseline without creating a second memory store.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Iterable


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class SensoryEvidence:
    observation: dict[str, Any]
    visible_count: int
    total_entity_count: int
    nearest_distance: float | None
    proximity: float
    density: float
    salience: float
    prediction_error: float
    novelty: float
    memory_token: str


def capture_sensory_evidence(
    world: Any,
    position: Iterable[float],
    *,
    radius: float = 24.0,
    previous_token: str | None = None,
) -> SensoryEvidence:
    """Read authoritative local geometry and derive bounded sensory evidence."""
    if not math.isfinite(float(radius)) or radius < 0:
        raise ValueError("radius must be finite and non-negative")
    observation = world.observe(center=position, radius=radius)
    entities = observation.get("entities")
    if not isinstance(entities, list):
        raise ValueError("World observation must contain an entities list")

    signature_items = []
    for entity in entities:
        if not isinstance(entity, dict) or not isinstance(entity.get("entity_id"), str):
            raise ValueError("Observed entities require stable entity_id values")
        p = entity.get("position", {})
        if not isinstance(p, dict) or not all(
            isinstance(p.get(axis), (int, float)) and math.isfinite(float(p[axis]))
            for axis in ("x", "y", "z")
        ):
            raise ValueError("Observed entity position must contain finite x/y/z")
        signature_items.append((
            entity["entity_id"],
            round(float(p["x"]), 2),
            round(float(p["y"]), 2),
            round(float(p["z"]), 2),
        ))
    signature_items.sort()
    signature = hashlib.sha256(
        json.dumps(signature_items, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]

    visible_count = len(entities)
    total_count = int(observation.get("entity_count", visible_count))
    nearest = (
        min(float(entity["distance"]) for entity in entities)
        if entities else None
    )
    if nearest is not None and (not math.isfinite(nearest) or nearest < 0):
        raise ValueError("Observed distance must be finite and non-negative")
    proximity = (
        _unit(1.0 - nearest / radius)
        if nearest is not None and radius > 0 else 0.0
    )
    density = _unit(visible_count / 8.0)
    salience = _unit(0.65 * proximity + 0.35 * density)

    previous_count = None
    previous_signature = None
    if isinstance(previous_token, str):
        parts = previous_token.split(":")
        if len(parts) == 3 and parts[0] == "sense1":
            try:
                previous_count = max(0, int(parts[1]))
                previous_signature = parts[2]
            except ValueError:
                previous_count = None
                previous_signature = None

    if previous_count is None:
        prediction_error = 0.0
        novelty = 0.15 if visible_count else 0.02
    else:
        prediction_error = _unit(
            abs(visible_count - previous_count) / max(1, previous_count)
        )
        novelty = 0.02 if signature == previous_signature else 0.15

    return SensoryEvidence(
        observation=observation,
        visible_count=visible_count,
        total_entity_count=total_count,
        nearest_distance=nearest,
        proximity=proximity,
        density=density,
        salience=salience,
        prediction_error=prediction_error,
        novelty=novelty,
        memory_token=f"sense1:{visible_count}:{signature}",
    )
