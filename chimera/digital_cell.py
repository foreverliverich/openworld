"""Minimal closed-loop digital-cell experiment coupled to the ISCE kernel.

This is an experimental controller, not a second organism state owner. ISCE
continues to own the organism state; RealityEngine remains the persistence and
world authority. The cell carries only local membrane, reserve and learned
action-value state so the mechanism can be tested independently.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Literal

from .isce import ISCEKernel, OrganismState, TransitionInput

Action = Literal["rest", "seek", "inspect"]


def _unit(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return value


@dataclass(frozen=True)
class CellObservation:
    energy_supply: float
    environmental_stress: float
    novelty: float = 0.0

    def __post_init__(self) -> None:
        _unit(self.energy_supply, "energy_supply")
        _unit(self.environmental_stress, "environmental_stress")
        _unit(self.novelty, "novelty")


@dataclass(frozen=True)
class DigitalCellState:
    energy: float = 0.8
    stress: float = 0.1
    membrane_potential: float = 0.0
    refractory_ticks: int = 0
    action_values: tuple[float, float, float] = (0.0, 0.0, 0.0)
    previous_action: Action | None = None
    previous_prediction: float = 0.0
    memory_strength: float = 0.0
    tick: int = 0

    def __post_init__(self) -> None:
        for name in ("energy", "stress", "memory_strength"):
            _unit(getattr(self, name), name)
        if not math.isfinite(self.membrane_potential):
            raise ValueError("membrane_potential must be finite")
        if self.refractory_ticks < 0 or self.tick < 0:
            raise ValueError("cell counters cannot be negative")
        if len(self.action_values) != 3 or not all(
            math.isfinite(float(v)) and -1.0 <= float(v) <= 1.0
            for v in self.action_values
        ):
            raise ValueError("action_values must be three finite values in [-1, 1]")


@dataclass(frozen=True)
class CellStep:
    source_tick: int
    state: DigitalCellState
    organism_state: OrganismState
    action: Action
    reward: float
    prediction_error: float
    membrane_fired: bool


class DigitalCell:
    """A deterministic homeostatic cell with a tiny reward-prediction memory.

    The three action values are learned local memory, not genome edits. The
    membrane variable is a leaky integrate-and-fire gate with a short refractory
    period. All values are bounded and the transition is reproducible.
    """

    ACTIONS: tuple[Action, ...] = ("rest", "seek", "inspect")

    def __init__(
        self,
        state: DigitalCellState | None = None,
        *,
        learning_rate: float = 0.12,
        membrane_threshold: float = 0.65,
        refractory_period: int = 2,
    ):
        self.state = state or DigitalCellState()
        self.learning_rate = _unit(learning_rate, "learning_rate")
        if not math.isfinite(membrane_threshold) or membrane_threshold <= 0:
            raise ValueError("membrane_threshold must be positive and finite")
        if refractory_period < 0:
            raise ValueError("refractory_period cannot be negative")
        self.membrane_threshold = membrane_threshold
        self.refractory_period = refractory_period

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    def commit(self, result: CellStep) -> None:
        """Publish a proposed step after its paired ISCE/world commit succeeds."""
        if not isinstance(result, CellStep):
            raise TypeError("commit requires a CellStep")
        if result.source_tick != self.state.tick or result.state.tick != self.state.tick + 1:
            raise ValueError("stale or invalid cell step")
        self.state = result.state

    def step(
        self,
        observation: CellObservation,
        organism_state: OrganismState,
        organism_kernel: ISCEKernel,
        *,
        dt: float = 0.1,
    ) -> CellStep:
        if not isinstance(observation, CellObservation):
            raise TypeError("observation must be CellObservation")
        if not isinstance(organism_state, OrganismState):
            raise TypeError("organism_state must be ISCE OrganismState")
        if not math.isfinite(dt) or not 0.0 < dt <= 10.0:
            raise ValueError("dt must be in (0, 10]")

        old = self.state
        # Interoceptive drive integrates energy deficit and external stress.
        drive = self._clamp(
            (0.75 - old.energy) * 0.8
            + observation.environmental_stress * 0.55
            + observation.novelty * 0.15
        )
        potential = max(0.0, old.membrane_potential * 0.72 + drive * 0.42)
        refractory = max(0, old.refractory_ticks - 1)
        fired = refractory == 0 and potential >= self.membrane_threshold

        # Homeostatic gating changes the action scores; learned values bias,
        # but cannot override, severe energy/stress constraints.
        values = old.action_values
        scores = [
            values[0] + max(0.0, 0.55 - old.energy) * 0.9
                    + old.stress * 0.25,
            values[1] + observation.energy_supply * 0.8
                    - observation.environmental_stress * 0.7
                    + observation.novelty * 0.1,
            values[2] + observation.novelty * 0.45
                    + old.memory_strength * 0.1,
        ]
        if old.energy < 0.18 or old.stress > 0.85:
            action_index = 0
        else:
            # Refractory state suppresses active seeking. Outside refractoriness,
            # a membrane spike is required for the metabolically active action.
            eligible = (0, 2) if refractory > 0 else ((0, 1, 2) if fired else (0, 2))
            action_index = max(eligible, key=lambda idx: (scores[idx], -idx))
        action = self.ACTIONS[action_index]

        energy, stress = old.energy, old.stress
        prediction_error = 0.0
        reward = 0.0
        if action == "rest":
            energy = self._clamp(energy + 0.10 + 0.08 * observation.energy_supply)
            stress = self._clamp(stress - 0.12)
            reward = 0.65 * (energy - old.energy) + 0.35 * (old.stress - stress)
        elif action == "seek":
            gain = 0.18 * observation.energy_supply
            stress_cost = 0.10 * observation.environmental_stress
            energy = self._clamp(energy + gain - 0.025)
            stress = self._clamp(stress + stress_cost)
            reward = 0.7 * (energy - old.energy) - 0.3 * (stress - old.stress)
        else:  # inspect
            stress = self._clamp(stress - 0.035 * observation.novelty)
            reward = 0.12 * observation.novelty
        reward = self._clamp(0.5 + reward, 0.0, 1.0) - 0.5

        prediction_error = reward - old.action_values[action_index]
        learned = list(values)
        learned[action_index] = self._clamp(
            learned[action_index] + self.learning_rate * prediction_error,
            -1.0, 1.0,
        )
        memory = self._clamp(
            old.memory_strength * 0.995
            + abs(prediction_error) * 0.04
            + observation.novelty * 0.015
        )
        next_cell = DigitalCellState(
            energy=energy,
            stress=stress,
            membrane_potential=0.0 if fired else potential,
            refractory_ticks=self.refractory_period if fired else refractory,
            action_values=tuple(learned),
            previous_action=action,
            previous_prediction=old.action_values[action_index],
            memory_strength=memory,
            tick=old.tick + 1,
        )

        # Feed cell-level evidence into the one existing intrinsic state owner.
        # This is a pure transition; persistence remains the caller's job.
        organism_result = organism_kernel.transition(
            organism_state,
            TransitionInput(
                dt=dt,
                prediction_error=self._clamp(abs(prediction_error)),
                novelty=observation.novelty,
                environmental_energy=observation.energy_supply,
                environmental_stress=observation.environmental_stress,
                sensory_salience=self._clamp(drive),
                action_success=self._clamp(0.5 + reward),
                outcome=f"cell:{action}:reward={reward:.6f}",
                measured_work_units=1.0,
                resting=(action == "rest"),
                mechanical_strain=0.0 if action != "seek" else 0.05,
            ),
        ).state
        return CellStep(
            source_tick=old.tick,
            state=next_cell,
            organism_state=organism_result,
            action=action,
            reward=reward,
            prediction_error=prediction_error,
            membrane_fired=fired,
        )
