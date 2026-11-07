"""Versioned, deterministic body morphology descriptors for Chimera.

The descriptor is authoritative persisted morphology metadata. Rendering is a
projection of this data; it is not an independent body-state owner.
"""
from __future__ import annotations

import math
from typing import Any

BODY_MODEL_SCHEMA = 1
BODY_FORMS = ("humanoid", "quadruped", "insect", "custom")
DEFAULT_MORPH_DURATION = 1.2


class EmbodimentError(ValueError):
    """A body morphology descriptor violates the v1 contract."""


def _finite_positive(value: Any, name: str, maximum: float = 20.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise EmbodimentError(f"{name} must be numeric") from exc
    if not math.isfinite(result) or result <= 0.0 or result > maximum:
        raise EmbodimentError(f"{name} must be finite and in (0, {maximum}]")
    return result


def make_body_model(
    form: str,
    dimensions: tuple[float, float, float] | list[float],
    *,
    previous_form: str = "humanoid",
    start_time: float = 0.0,
    duration: float = DEFAULT_MORPH_DURATION,
) -> dict[str, Any]:
    """Create a validated persistent A/B morphology transition descriptor."""
    if form not in BODY_FORMS or previous_form not in BODY_FORMS:
        raise EmbodimentError(f"form must be one of {', '.join(BODY_FORMS)}")
    if not isinstance(dimensions, (tuple, list)) or len(dimensions) != 3:
        raise EmbodimentError("dimensions must contain width, height and depth")
    width, height, depth = (
        _finite_positive(dimensions[0], "width"),
        _finite_positive(dimensions[1], "height"),
        _finite_positive(dimensions[2], "depth"),
    )
    start = float(start_time)
    span = float(duration)
    if not math.isfinite(start) or start < 0:
        raise EmbodimentError("start_time must be finite and non-negative")
    if not math.isfinite(span) or span <= 0 or span > 60:
        raise EmbodimentError("duration must be finite and in (0, 60]")
    return {
        "schema_version": BODY_MODEL_SCHEMA,
        "representation": "analytic_sdf",
        "from_form": previous_form,
        "to_form": form,
        "dimensions": {"width": width, "height": height, "depth": depth},
        "morph_start_simulation_time": start,
        "morph_duration": span,
        "material_profile": "soft_biological",
        "identity_continuity": True,
    }


def validate_body_model(model: dict[str, Any]) -> dict[str, Any]:
    """Validate persisted data before it is supplied to a renderer."""
    if not isinstance(model, dict) or model.get("schema_version") != BODY_MODEL_SCHEMA:
        raise EmbodimentError("unsupported body model schema")
    if model.get("representation") != "analytic_sdf":
        raise EmbodimentError("body representation must be analytic_sdf")
    dimensions = model.get("dimensions")
    if not isinstance(dimensions, dict):
        raise EmbodimentError("body dimensions are missing")
    return make_body_model(
        str(model.get("to_form")),
        [dimensions.get("width"), dimensions.get("height"), dimensions.get("depth")],
        previous_form=str(model.get("from_form")),
        start_time=model.get("morph_start_simulation_time", 0.0),
        duration=model.get("morph_duration", DEFAULT_MORPH_DURATION),
    )


def morph_progress(model: dict[str, Any], simulation_time: float) -> float:
    """Derive A/B blend progress exclusively from the authoritative world clock."""
    valid = validate_body_model(model)
    now = float(simulation_time)
    if not math.isfinite(now):
        raise EmbodimentError("simulation_time must be finite")
    elapsed = max(0.0, now - valid["morph_start_simulation_time"])
    return max(0.0, min(1.0, elapsed / valid["morph_duration"]))
