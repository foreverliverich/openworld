"""Deterministic CCPL intervention battery for the existing ISCE kernel.

This module is an experiment harness, not another organism state owner.
It runs paired counterfactual trajectories from the same immutable initial
state and inputs. The causal graph is never edited.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional

from .isce import ISCEKernel, Intervention, OrganismState, TransitionInput

CCPL_VERSION = "0.1.0"
_ALLOWED_TARGETS = {
    "body.energy", "body.stress", "body.integrity",
    "interoception.precision", "sensorimotor.motor_readiness",
    "self_model.memory_strength", "attention.focus", "resources.reserve",
}


def _read_target(state: OrganismState, target: str) -> float:
    partition, field = target.split(".", 1)
    return float(getattr(getattr(state, partition), field))


def _write_target(state: OrganismState, target: str, value: float) -> OrganismState:
    partition, field = target.split(".", 1)
    current = getattr(state, partition)
    updated = replace(current, **{field: max(0.0, min(1.0, float(value)))})
    return replace(state, **{partition: updated})


def _apply(state: OrganismState, intervention: Intervention) -> OrganismState:
    if intervention.target not in _ALLOWED_TARGETS:
        raise ValueError(f"Unsupported CCPL target: {intervention.target}")
    return _write_target(
        state, intervention.target,
        _read_target(state, intervention.target) + intervention.delta,
    )


def _trajectory(
    kernel: ISCEKernel,
    initial: OrganismState,
    inputs: tuple[TransitionInput, ...],
    *,
    interventions: tuple[Intervention, ...] = (),
    intervention_tick: Optional[int] = None,
    mediation_target: Optional[str] = None,
    baseline: Optional[tuple[OrganismState, ...]] = None,
) -> tuple[OrganismState, ...]:
    state = initial
    states: list[OrganismState] = []
    intervention_applied = False

    for index, step_input in enumerate(inputs):
        state = kernel.transition(state, step_input).state
        if intervention_tick == index and interventions:
            for intervention in interventions:
                state = _apply(state, intervention)
            intervention_applied = True

        # A mediation run clamps the proposed mediator to its paired baseline
        # value after every subsequent transition. This blocks that path while
        # leaving the source intervention and all other dynamics intact.
        if mediation_target and intervention_applied and baseline is not None:
            state = _write_target(
                state, mediation_target,
                _read_target(baseline[index], mediation_target),
            )
        states.append(state)

    return tuple(states)


def run_ccpl(
    kernel: ISCEKernel,
    initial: OrganismState,
    inputs: Iterable[TransitionInput],
    *,
    source: Intervention = Intervention("body.integrity", -0.20),
    second: Intervention = Intervention("resources.reserve", -0.20),
    mediator_target: str = "interoception.precision",
    outcome_target: str = "attention.focus",
    intervention_tick: int = 0,
) -> dict:
    """Run baseline, sham, single, double and mediator-blocked paired trials.

    Intervention values are bounded state clamps applied at the end of the
    selected transition. The mediation condition then holds the named mediator
    to its paired baseline trajectory for the remainder of the trial. This
    explicit operational definition avoids calling a generic correlation a
    mediation.
    """
    sequence = tuple(inputs)
    if not sequence:
        raise ValueError("CCPL requires at least one transition input")
    if not 0 <= intervention_tick < len(sequence):
        raise ValueError("intervention_tick is outside the input sequence")
    if source.target not in _ALLOWED_TARGETS or second.target not in _ALLOWED_TARGETS:
        raise ValueError("CCPL intervention target is not supported")
    if source.target == second.target:
        raise ValueError("Double intervention requires two distinct targets")
    if mediator_target not in _ALLOWED_TARGETS or outcome_target not in _ALLOWED_TARGETS:
        raise ValueError("CCPL mediator and outcome must be supported state targets")

    fingerprint = kernel.graph_fingerprint
    baseline = _trajectory(kernel, initial, sequence)
    sham = _trajectory(
        kernel, initial, sequence,
        interventions=(Intervention(source.target, 0.0),),
        intervention_tick=intervention_tick,
    )
    single = _trajectory(
        kernel, initial, sequence, interventions=(source,),
        intervention_tick=intervention_tick,
    )
    double = _trajectory(
        kernel, initial, sequence, interventions=(source, second),
        intervention_tick=intervention_tick,
    )
    mediated = _trajectory(
        kernel, initial, sequence, interventions=(source,),
        intervention_tick=intervention_tick,
        mediation_target=mediator_target, baseline=baseline,
    )

    def value(path: tuple[OrganismState, ...]) -> float:
        return _read_target(path[-1], outcome_target)

    base_value = value(baseline)
    single_effect = value(single) - base_value
    mediated_effect = value(mediated) - base_value
    result = {
        "schema": "chimera.ccpl.v1",
        "version": CCPL_VERSION,
        "graph_fingerprint": fingerprint,
        "initial_state_digest": initial.digest(),
        "steps": len(sequence),
        "intervention_tick": intervention_tick,
        "source": {"target": source.target, "delta": source.delta},
        "second": {"target": second.target, "delta": second.delta},
        "mediator_target": mediator_target,
        "outcome_target": outcome_target,
        "conditions": {
            "baseline": [state.to_dict() for state in baseline],
            "sham": [state.to_dict() for state in sham],
            "single": [state.to_dict() for state in single],
            "double": [state.to_dict() for state in double],
            "mediated": [state.to_dict() for state in mediated],
        },
        "summary": {
            "baseline": base_value,
            "sham": value(sham),
            "single": value(single),
            "double": value(double),
            "mediated": value(mediated),
            "single_effect": single_effect,
            "double_effect": value(double) - base_value,
            "mediated_effect": mediated_effect,
            "mediation_attenuation": (
                1.0 - abs(mediated_effect) / abs(single_effect)
                if abs(single_effect) > 1e-12 else None
            ),
            "sham_error": abs(value(sham) - base_value),
        },
    }
    if kernel.graph_fingerprint != fingerprint:
        raise RuntimeError("CCPL run mutated the fixed causal graph")
    return result
