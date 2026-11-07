"""Causally coupled organism physiology/cognition/world-field kernel.

This is a computational organism model, not a claim of biological consciousness.
Its state is persisted by RealityEngine in the same transaction as local field
updates, making organism/world coupling inspectable and restart-safe.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Optional

from .reality_engine import RealityEngine, Vec3, WorldResult


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class OrganismState:
    organism_id: str
    position: Vec3
    energy: float = 0.85
    stress: float = 0.12
    integrity: float = 1.0
    fatigue: float = 0.0
    memory_strength: float = 0.0
    curiosity: float = 0.5
    prediction_error: float = 0.0
    confidence: float = 0.5
    allostatic_error: float = 0.0
    age_seconds: float = 0.0
    tick: int = 0
    active_goal: Optional[str] = None
    last_outcome: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["position"] = asdict(self.position)
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "OrganismState":
        data = dict(value)
        data["position"] = Vec3(**data["position"])
        return cls(**data)


class OrganismKernel:
    """Minimal allostatic + cognitive + morphogenic coupling mechanism."""

    def __init__(
        self,
        world: RealityEngine,
        organism_id: str = "chimera",
        initial_position: tuple[float, float, float] = (0.0, 1.0, 0.0),
        *,
        basal_metabolic_rate: float = 0.003,
        stress_recovery_rate: float = 0.025,
        fatigue_recovery_rate: float = 0.018,
    ):
        self.world = world
        self.organism_id = organism_id
        self.basal_metabolic_rate = basal_metabolic_rate
        self.stress_recovery_rate = stress_recovery_rate
        self.fatigue_recovery_rate = fatigue_recovery_rate
        persisted = world.get_organism_state()
        if persisted is not None:
            if persisted["organism_id"] != organism_id:
                raise ValueError("World already contains a different organism identity")
            self.state = OrganismState.from_dict(persisted)
        else:
            self.state = OrganismState(
                organism_id=organism_id,
                position=Vec3.from_value(initial_position),
            )

    @property
    def can_act(self) -> bool:
        s = self.state
        return s.energy > 0.12 and s.integrity > 0.25 and s.stress < 0.95

    def set_goal(self, goal: Optional[str]) -> None:
        self.state.active_goal = goal

    def relocate(self, position: tuple[float, float, float]) -> None:
        self.state.position = Vec3.from_value(position)

    def tick(
        self,
        *,
        dt: float,
        action_energy_cost: float = 0.0,
        mechanical_strain: float = 0.0,
        prediction_error: float = 0.0,
        novelty: float = 0.0,
        outcome: Optional[str] = None,
        resting: bool = False,
        expected_revision: Optional[int] = None,
    ) -> WorldResult:
        """
        Advance one organism tick.

        Inputs are measured/estimated signals from the action, body and world
        model. The kernel uses the local world fields as inputs and writes the
        resulting physiology/cognitive trace back into those same fields.
        """
        values = (dt, action_energy_cost, mechanical_strain,
                  prediction_error, novelty)
        if not all(math.isfinite(float(v)) for v in values):
            raise ValueError("Organism tick inputs must be finite")
        if dt <= 0 or dt > 10:
            raise ValueError("dt must be in (0, 10]")
        if action_energy_cost < 0:
            raise ValueError("action_energy_cost cannot be negative")
        if not 0 <= mechanical_strain <= 1:
            raise ValueError("mechanical_strain must be in [0, 1]")
        if not 0 <= prediction_error <= 1 or not 0 <= novelty <= 1:
            raise ValueError("prediction_error and novelty must be in [0, 1]")

        s = self.state
        local = self.world.field_at(s.position.as_tuple())

        # External morphogenic fields are not decorative: they modulate internal
        # regulation and memory/learning state on this tick.
        energy = _clamp(
            s.energy
            - self.basal_metabolic_rate * dt
            - action_energy_cost
            - mechanical_strain * 0.035
            + local["energy"] * 0.012 * dt
            + (0.025 * dt if resting else 0.0)
        )
        stress = _clamp(
            s.stress
            + mechanical_strain * 0.22
            + local["stress"] * 0.045 * dt
            + prediction_error * 0.035
            - (0.05 if resting else self.stress_recovery_rate) * dt
            - local["cohesion"] * 0.012 * dt
        )
        fatigue = _clamp(
            s.fatigue + mechanical_strain * 0.10 * dt
            - (0.05 if resting else self.fatigue_recovery_rate) * dt
        )

        repair_rate = 0.012 if energy > 0.55 and stress < 0.45 else 0.0
        damage_rate = max(0.0, mechanical_strain - 0.72) * 0.025
        integrity = _clamp(s.integrity + repair_rate * dt - damage_rate * dt)

        memory_strength = _clamp(
            s.memory_strength
            + prediction_error * 0.035
            + novelty * 0.025
            + local["memory"] * 0.008 * dt
        )
        curiosity = _clamp(s.curiosity + novelty * 0.025 - 0.004 * dt
                           + prediction_error * 0.012)
        smoothed_error = _clamp(0.75 * s.prediction_error + 0.25 * prediction_error)
        confidence = _clamp(1.0 - smoothed_error)
        allostatic_error = abs(0.75 - energy) + abs(0.12 - stress)

        next_state = OrganismState(
            organism_id=s.organism_id,
            position=s.position,
            energy=energy,
            stress=stress,
            integrity=integrity,
            fatigue=fatigue,
            memory_strength=memory_strength,
            curiosity=curiosity,
            prediction_error=smoothed_error,
            confidence=confidence,
            allostatic_error=allostatic_error,
            age_seconds=s.age_seconds + dt,
            tick=s.tick + 1,
            active_goal=s.active_goal,
            last_outcome=outcome if outcome is not None else s.last_outcome,
        )

        # The world fields are the spatial projection of the organism's internal
        # condition. This creates a two-way coupling: field -> physiology above;
        # physiology -> field here. Geometry is not yet altered by these fields.
        field_values = {
            "energy": energy,
            "stress": stress,
            "memory": memory_strength,
            "cohesion": _clamp(integrity * (1.0 - 0.5 * fatigue)),
        }

        result = self.world.commit_organism_tick(
            next_state.to_dict(),
            field_values,
            actor_id=self.organism_id,
            expected_revision=(self.world.revision()
                               if expected_revision is None else expected_revision),
        )
        self.state = next_state
        return result

    def snapshot(self) -> dict[str, Any]:
        return {
            "organism": self.state.to_dict(),
            "can_act": self.can_act,
            "world_revision": self.world.revision(),
        }
