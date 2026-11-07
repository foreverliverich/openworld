"""ISCE: deterministic, fixed-graph organism state-transition kernel.

ISCE is deliberately independent of RealityEngine and renderers. It owns one
versioned intrinsic state value and advances it through a pure transition
function. Persistence, scheduling, governance and world transactions are
adapters around this kernel, never alternate state owners.

This is a computational causal model; it does not establish consciousness.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Mapping, Optional, Tuple

SCHEMA_VERSION = 1
KERNEL_VERSION = "0.1.0"
_EPS = 1e-12


class ISCEError(ValueError):
    """Invalid state, graph, input or intervention."""


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ISCEError(f"{name} must be finite")
    return value


def _unit(name: str, value: float) -> float:
    value = _finite(name, value)
    if not 0.0 <= value <= 1.0:
        raise ISCEError(f"{name} must be in [0, 1]")
    return value


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class CausalEdge:
    source: str
    target: str
    weight: float

    def __post_init__(self) -> None:
        if not self.source or not self.target:
            raise ISCEError("Causal edge endpoints must be non-empty")
        _finite("edge weight", self.weight)


@dataclass(frozen=True)
class CausalGraph:
    """Immutable structural graph. Runtime state never mutates its topology."""

    nodes: Tuple[str, ...]
    edges: Tuple[CausalEdge, ...]

    def __post_init__(self) -> None:
        if not self.nodes or len(set(self.nodes)) != len(self.nodes):
            raise ISCEError("Graph nodes must be non-empty and unique")
        known = set(self.nodes)
        for edge in self.edges:
            if edge.source not in known or edge.target not in known:
                raise ISCEError("Causal edge references an unknown node")

    @classmethod
    def canonical(cls) -> "CausalGraph":
        # This is the first executable ISCE graph, not a claim that the
        # historical project's complete causal graph has been recovered.
        return cls(
            nodes=("body", "interoception", "sensorimotor", "temporal",
                   "self_model", "attention", "resources"),
            edges=(
                CausalEdge("body", "interoception", 0.80),
                CausalEdge("interoception", "attention", 0.75),
                CausalEdge("sensorimotor", "body", 0.70),
                CausalEdge("sensorimotor", "temporal", 0.55),
                CausalEdge("temporal", "self_model", 0.65),
                CausalEdge("self_model", "attention", 0.60),
                CausalEdge("resources", "body", 0.80),
                CausalEdge("resources", "attention", 0.50),
                CausalEdge("attention", "sensorimotor", 0.45),
            ),
        )

    def fingerprint(self) -> str:
        payload = {
            "nodes": list(self.nodes),
            "edges": [(e.source, e.target, e.weight) for e in self.edges],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BodyState:
    energy: float = 0.85
    stress: float = 0.12
    integrity: float = 1.0
    fatigue: float = 0.0
    allostatic_error: float = 0.0


@dataclass(frozen=True)
class InteroceptiveState:
    hunger: float = 0.15
    pain: float = 0.0
    arousal: float = 0.12
    prediction_error: float = 0.0
    precision: float = 0.5


@dataclass(frozen=True)
class SensorimotorState:
    motor_readiness: float = 0.5
    proprioceptive_error: float = 0.0
    last_action_cost: float = 0.0
    last_action_success: float = 0.5


@dataclass(frozen=True)
class TemporalState:
    tick: int = 0
    organism_time: float = 0.0
    previous_state_digest: str = "genesis"


@dataclass(frozen=True)
class SelfModelState:
    confidence: float = 0.5
    memory_strength: float = 0.0
    curiosity: float = 0.5
    active_goal: Optional[str] = None
    last_outcome: Optional[str] = None


@dataclass(frozen=True)
class AttentionState:
    focus: float = 0.5
    urgency: float = 0.12


@dataclass(frozen=True)
class ResourceState:
    # Simulated internal reserve, not joules or hardware telemetry.
    reserve: float = 1.0
    cumulative_work_units: float = 0.0


@dataclass(frozen=True)
class OrganismState:
    organism_id: str
    body: BodyState = field(default_factory=BodyState)
    interoception: InteroceptiveState = field(default_factory=InteroceptiveState)
    sensorimotor: SensorimotorState = field(default_factory=SensorimotorState)
    temporal: TemporalState = field(default_factory=TemporalState)
    self_model: SelfModelState = field(default_factory=SelfModelState)
    attention: AttentionState = field(default_factory=AttentionState)
    resources: ResourceState = field(default_factory=ResourceState)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.organism_id:
            raise ISCEError("organism_id must be non-empty")
        if self.schema_version != SCHEMA_VERSION:
            raise ISCEError(f"Unsupported state schema: {self.schema_version}")
        if self.temporal.tick < 0 or self.temporal.organism_time < 0:
            raise ISCEError("Temporal counters cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OrganismState":
        data = dict(payload)
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ISCEError("Unsupported or missing organism state schema_version")
        return cls(
            organism_id=str(data["organism_id"]),
            body=BodyState(**data["body"]),
            interoception=InteroceptiveState(**data["interoception"]),
            sensorimotor=SensorimotorState(**data["sensorimotor"]),
            temporal=TemporalState(**data["temporal"]),
            self_model=SelfModelState(**data["self_model"]),
            attention=AttentionState(**data["attention"]),
            resources=ResourceState(**data["resources"]),
            schema_version=int(data["schema_version"]),
        )

    def digest(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TransitionInput:
    dt: float
    action_energy_cost: float = 0.0
    mechanical_strain: float = 0.0
    prediction_error: float = 0.0
    novelty: float = 0.0
    action_success: float = 0.5
    environmental_energy: float = 0.0
    environmental_stress: float = 0.0
    environmental_memory: float = 0.0
    environmental_cohesion: float = 0.0
    resting: bool = False
    outcome: Optional[str] = None
    measured_work_units: float = 0.0

    def validate(self) -> None:
        dt = _finite("dt", self.dt)
        if not 0.0 < dt <= 10.0:
            raise ISCEError("dt must be in (0, 10]")
        if _finite("action_energy_cost", self.action_energy_cost) < 0:
            raise ISCEError("action_energy_cost cannot be negative")
        if _finite("measured_work_units", self.measured_work_units) < 0:
            raise ISCEError("measured_work_units cannot be negative")
        for name in (
            "mechanical_strain", "prediction_error", "novelty", "action_success",
            "environmental_energy", "environmental_stress",
            "environmental_memory", "environmental_cohesion",
        ):
            _unit(name, getattr(self, name))


@dataclass(frozen=True)
class Intervention:
    """Versioned experimental intervention; no graph or weight mutation."""

    target: str
    delta: float

    def __post_init__(self) -> None:
        if self.target not in {
            "body.energy", "body.stress", "body.integrity",
            "interoception.precision", "sensorimotor.motor_readiness",
            "self_model.memory_strength", "attention.focus", "resources.reserve",
        }:
            raise ISCEError(f"Unsupported intervention target: {self.target}")
        _finite("intervention delta", self.delta)


@dataclass(frozen=True)
class TransitionResult:
    state: OrganismState
    graph_fingerprint: str
    intervention: Optional[Intervention]
    state_digest: str


class ISCEKernel:
    """Pure deterministic transition function over one authoritative state."""

    def __init__(self, graph: Optional[CausalGraph] = None,
                 basal_metabolic_rate: float = 0.003,
                 stress_recovery_rate: float = 0.025,
                 fatigue_recovery_rate: float = 0.018):
        self.graph = graph or CausalGraph.canonical()
        self.basal_metabolic_rate = _finite("basal_metabolic_rate", basal_metabolic_rate)
        self.stress_recovery_rate = _finite("stress_recovery_rate", stress_recovery_rate)
        self.fatigue_recovery_rate = _finite("fatigue_recovery_rate", fatigue_recovery_rate)
        if min(self.basal_metabolic_rate, self.stress_recovery_rate,
               self.fatigue_recovery_rate) < 0:
            raise ISCEError("Kernel rates cannot be negative")
        self._graph_fingerprint = self.graph.fingerprint()

    @property
    def graph_fingerprint(self) -> str:
        return self._graph_fingerprint

    def transition(self, state: OrganismState, inputs: TransitionInput,
                   intervention: Optional[Intervention] = None) -> TransitionResult:
        inputs.validate()
        if state.schema_version != SCHEMA_VERSION:
            raise ISCEError("State schema does not match this kernel")
        if intervention is not None and not isinstance(intervention, Intervention):
            raise ISCEError("intervention must be an Intervention")

        b, i, m = state.body, state.interoception, state.sensorimotor
        sm, a, r = state.self_model, state.attention, state.resources
        dt = inputs.dt

        # The internal resource law is distinct from hardware measurements.
        work = inputs.measured_work_units
        reserve = _clamp(r.reserve - work * 0.001 - inputs.action_energy_cost * 0.25
                         + (0.0005 * dt if inputs.resting else 0.0))
        energy = _clamp(
            b.energy - self.basal_metabolic_rate * dt - inputs.action_energy_cost
            - inputs.mechanical_strain * 0.035
            + inputs.environmental_energy * 0.012 * dt
            + (0.025 * dt if inputs.resting else 0.0)
        )
        stress = _clamp(
            b.stress + inputs.mechanical_strain * 0.22
            + inputs.environmental_stress * 0.045 * dt
            + inputs.prediction_error * 0.035
            - (0.05 if inputs.resting else self.stress_recovery_rate) * dt
            - inputs.environmental_cohesion * 0.012 * dt
        )
        fatigue = _clamp(b.fatigue + inputs.mechanical_strain * 0.10 * dt
                         - (0.05 if inputs.resting else self.fatigue_recovery_rate) * dt)
        repair_rate = 0.012 if energy > 0.55 and stress < 0.45 and reserve > 0.1 else 0.0
        damage_rate = max(0.0, inputs.mechanical_strain - 0.72) * 0.025
        integrity = _clamp(b.integrity + (repair_rate - damage_rate) * dt)
        allostatic_error = abs(0.75 - energy) + abs(0.12 - stress)

        smoothed_error = _clamp(0.75 * i.prediction_error + 0.25 * inputs.prediction_error)
        pain = _clamp(i.pain + max(0.0, inputs.mechanical_strain - 0.65) * 0.08
                      - (0.02 * dt if inputs.resting else 0.002 * dt))
        hunger = _clamp(i.hunger + max(0.0, 0.75 - energy) * 0.015 * dt)
        precision = _clamp(i.precision + (1.0 - smoothed_error - i.precision) * 0.05)
        arousal = _clamp(0.7 * i.arousal + 0.3 * stress)

        motor_readiness = _clamp(
            m.motor_readiness + (energy - m.motor_readiness) * 0.08
            - stress * 0.025 - fatigue * 0.02
        )
        proprioceptive_error = _clamp(
            0.7 * m.proprioceptive_error + 0.3 * inputs.mechanical_strain
        )
        memory_strength = _clamp(
            sm.memory_strength + inputs.prediction_error * 0.035
            + inputs.novelty * 0.025 + inputs.environmental_memory * 0.008 * dt
        )
        curiosity = _clamp(sm.curiosity + inputs.novelty * 0.025
                           - 0.004 * dt + inputs.prediction_error * 0.012)
        confidence = _clamp(1.0 - smoothed_error)
        urgency = _clamp(0.65 * a.urgency + 0.35 * (stress + allostatic_error * 0.25))
        focus = _clamp(0.7 * a.focus + 0.3 * (urgency * 0.6 + precision * 0.4))

        next_values: dict[str, float] = {
            "body.energy": energy, "body.stress": stress,
            "body.integrity": integrity,
            "interoception.precision": precision,
            "sensorimotor.motor_readiness": motor_readiness,
            "self_model.memory_strength": memory_strength,
            "attention.focus": focus, "resources.reserve": reserve,
        }
        if intervention is not None:
            next_values[intervention.target] = _clamp(
                next_values[intervention.target] + intervention.delta
            )
        energy, stress, integrity = (next_values["body.energy"],
                                     next_values["body.stress"],
                                     next_values["body.integrity"])
        precision = next_values["interoception.precision"]
        motor_readiness = next_values["sensorimotor.motor_readiness"]
        memory_strength = next_values["self_model.memory_strength"]
        focus = next_values["attention.focus"]
        reserve = next_values["resources.reserve"]

        next_state = OrganismState(
            organism_id=state.organism_id,
            body=BodyState(energy, stress, integrity, fatigue,
                           abs(0.75 - energy) + abs(0.12 - stress)),
            interoception=InteroceptiveState(hunger, pain, arousal,
                                             smoothed_error, precision),
            sensorimotor=SensorimotorState(motor_readiness, proprioceptive_error,
                                           inputs.action_energy_cost,
                                           inputs.action_success),
            temporal=TemporalState(state.temporal.tick + 1,
                                   state.temporal.organism_time + dt,
                                   state.digest()),
            self_model=SelfModelState(confidence, memory_strength, curiosity,
                                      sm.active_goal,
                                      inputs.outcome if inputs.outcome is not None
                                      else sm.last_outcome),
            attention=AttentionState(focus, urgency),
            resources=ResourceState(reserve, r.cumulative_work_units + work),
        )
        if self.graph.fingerprint() != self._graph_fingerprint:
            raise ISCEError("Causal graph changed during transition")
        return TransitionResult(next_state, self._graph_fingerprint,
                                intervention, next_state.digest())

    def can_act(self, state: OrganismState) -> bool:
        return (state.body.energy > 0.12 and state.body.integrity > 0.25
                and state.body.stress < 0.95 and state.resources.reserve > 0.05)
