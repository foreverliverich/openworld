"""Compatibility-facing organism controller backed exclusively by ISCE.

There is no independent legacy physiology state in this module. The public
OrganismKernel name is retained for callers, but its only mutable organism
state is the versioned ISCEOrganismState committed through RealityEngine.
"""
from __future__ import annotations

import math
from typing import Optional

from .isce import (
    AttentionState, BodyState, ISCEKernel, InteroceptiveState,
    OrganismState as ISCEOrganismState, ResourceState, SelfModelState,
    SensorimotorState, TemporalState, TransitionInput,
)
from .reality_engine import RealityEngine, Vec3, WorldResult


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class OrganismKernel:
    """ISCE-backed controller preserving the established runtime API.

    Legacy persisted payloads are read once and converted in memory. The next
    successful organism tick writes the complete ISCE state into the existing
    transactional organism-state row, preserving organism identity, location,
    age/tick, physiology, memory and goal provenance.
    """

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
        self.kernel = ISCEKernel(
            basal_metabolic_rate=basal_metabolic_rate,
            stress_recovery_rate=stress_recovery_rate,
            fatigue_recovery_rate=fatigue_recovery_rate,
        )
        persisted = world.get_organism_state()
        self._migration_pending = False
        if persisted is not None:
            if persisted.get("organism_id") != organism_id:
                raise ValueError("World already contains a different organism identity")
            if persisted.get("schema_version") == 1 and "body" in persisted:
                self.state = ISCEOrganismState.from_dict(persisted)
            else:
                self.state = self._migrate_legacy_payload(persisted, initial_position)
                self._migration_pending = True
        else:
            self.state = ISCEOrganismState(
                organism_id=organism_id,
                position=tuple(float(v) for v in initial_position),
            )

    @staticmethod
    def _migrate_legacy_payload(
        value: dict, initial_position: tuple[float, float, float]
    ) -> ISCEOrganismState:
        """Map the old flat physiology payload into the unified ISCE schema."""
        raw_position = value.get("position", initial_position)
        position = Vec3.from_value(raw_position).as_tuple()
        energy = _unit(value.get("energy", 0.85))
        stress = _unit(value.get("stress", 0.12))
        integrity = _unit(value.get("integrity", 1.0))
        fatigue = _unit(value.get("fatigue", 0.0))
        prediction_error = _unit(value.get("prediction_error", 0.0))
        confidence = _unit(value.get("confidence", 1.0 - prediction_error))
        memory = _unit(value.get("memory_strength", 0.0))
        tick = max(0, int(value.get("tick", 0)))
        age = max(0.0, float(value.get("age_seconds", 0.0)))
        return ISCEOrganismState(
            organism_id=str(value["organism_id"]),
            position=position,
            body=BodyState(
                energy=energy, stress=stress, integrity=integrity,
                fatigue=fatigue,
                allostatic_error=_unit(value.get("allostatic_error", 0.0)),
            ),
            interoception=InteroceptiveState(
                arousal=stress, prediction_error=prediction_error,
                precision=confidence,
            ),
            sensorimotor=SensorimotorState(
                motor_readiness=energy,
            ),
            temporal=TemporalState(
                tick=tick, organism_time=age,
                previous_state_digest="legacy-import",
            ),
            self_model=SelfModelState(
                confidence=confidence, memory_strength=memory,
                curiosity=_unit(value.get("curiosity", 0.5)),
                active_goal=value.get("active_goal"),
                last_outcome=value.get("last_outcome"),
            ),
            attention=AttentionState(
                focus=confidence, urgency=stress,
            ),
            resources=ResourceState(),
        )

    @property
    def can_act(self) -> bool:
        return self.kernel.can_act(self.state)

    def set_goal(self, goal: Optional[str]) -> None:
        self.state = self.state.with_goal(goal)

    def relocate(self, position: tuple[float, float, float]) -> None:
        self.state = self.state.at_position(Vec3.from_value(position).as_tuple())

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
        measured_work_units: float = 0.0,
        motor_commands: tuple[tuple[str, float], ...] = (),
        root_acceleration: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> WorldResult:
        position = self.state.position
        local = self.world.field_at(position)
        transition_input = TransitionInput(
            dt=dt,
            action_energy_cost=action_energy_cost,
            mechanical_strain=mechanical_strain,
            prediction_error=prediction_error,
            novelty=novelty,
            environmental_energy=_unit(local["energy"]),
            environmental_stress=_unit(local["stress"]),
            environmental_memory=_unit(local["memory"]),
            environmental_cohesion=_unit(local["cohesion"]),
            resting=resting,
            outcome=outcome,
            measured_work_units=measured_work_units,
            motor_commands=motor_commands,
            root_acceleration=root_acceleration,
        )
        transition = self.kernel.transition(self.state, transition_input)
        next_state = transition.state
        field_values = {
            "energy": next_state.body.energy,
            "stress": next_state.body.stress,
            "memory": next_state.self_model.memory_strength,
            "cohesion": _unit(
                next_state.body.integrity * (1.0 - 0.5 * next_state.body.fatigue)
            ),
        }
        result = self.world.commit_organism_tick(
            next_state.to_dict(),
            field_values,
            actor_id=self.organism_id,
            expected_revision=(
                self.world.revision()
                if expected_revision is None else expected_revision
            ),
        )
        # Publish the next in-memory state only after the durable transaction
        # commits. A failed optimistic write leaves the prior state authoritative.
        self.state = next_state
        self._migration_pending = False
        return result

    def snapshot(self) -> dict:
        # Compatibility projection for existing browser/API clients. These
        # aliases are derived on read; ISCE remains the only stored state.
        state = self.state
        organism = state.to_dict()
        organism.update({
            "position": {
                "x": state.position[0], "y": state.position[1],
                "z": state.position[2],
            },
            "energy": state.body.energy,
            "stress": state.body.stress,
            "integrity": state.body.integrity,
            "fatigue": state.body.fatigue,
            "memory_strength": state.self_model.memory_strength,
            "curiosity": state.self_model.curiosity,
            "prediction_error": state.interoception.prediction_error,
            "confidence": state.self_model.confidence,
            "allostatic_error": state.body.allostatic_error,
            "age_seconds": state.temporal.organism_time,
            "tick": state.temporal.tick,
            "active_goal": state.self_model.active_goal,
            "last_outcome": state.self_model.last_outcome,
        })
        return {
            "organism": organism,
            "can_act": self.can_act,
            "world_revision": self.world.revision(),
            "kernel_version": "isce/0.1.0",
            "migration_pending": self._migration_pending,
        }


# Backwards-compatible public type name; it is the ISCE state, not a second schema.
OrganismState = ISCEOrganismState
