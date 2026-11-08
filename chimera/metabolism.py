"""Measured-cost computational bloodstream prototype (V-OMEGA P2).

This module is intentionally independent of ISCE persistence. It provides a
small, deterministic, testable resource-circulation kernel that can later be
integrated through a versioned ISCE state migration.

Important distinctions:
- WorkMeasurement contains observed counters/timings/bytes.
- MetabolicCalibration maps those measurements into *simulated reserve units*.
- Reserve units are not joules and are not hardware power telemetry.
- The circulation graph is a resource network, not the fixed ISCE causal graph.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class MetabolismError(ValueError):
    """Invalid metabolic state, measurement, graph or transition."""


def _finite_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if value < 0 or value != value or value == float("inf"):
        raise MetabolismError(f"{name} must be finite and non-negative")
    return value


@dataclass(frozen=True)
class OrganSpec:
    name: str
    capacity: float
    setpoint: float
    minimum: float

    def __post_init__(self) -> None:
        if not self.name:
            raise MetabolismError("organ name is required")
        for key in ("capacity", "setpoint", "minimum"):
            _finite_nonnegative(key, getattr(self, key))
        if not self.minimum <= self.setpoint <= self.capacity:
            raise MetabolismError("require minimum <= setpoint <= capacity")


@dataclass(frozen=True)
class CirculationEdge:
    source: str
    target: str
    conductance: float

    def __post_init__(self) -> None:
        if not self.source or not self.target or self.source == self.target:
            raise MetabolismError("circulation edge requires distinct named organs")
        value = _finite_nonnegative("conductance", self.conductance)
        if value > 1.0:
            raise MetabolismError("conductance must be in [0, 1]")


@dataclass(frozen=True)
class WorkMeasurement:
    """Observed work counters; units remain explicit and uncollapsed."""

    operations: int = 0
    cpu_time_ns: int = 0
    bytes_moved: int = 0
    gpu_time_ns: int = 0

    def __post_init__(self) -> None:
        for key in ("operations", "cpu_time_ns", "bytes_moved", "gpu_time_ns"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise MetabolismError(f"{key} must be a non-negative integer")


@dataclass(frozen=True)
class MetabolicCalibration:
    """Versioned conversion from measured counters to simulated reserve units."""

    version: str
    units_per_operation: float = 0.0
    units_per_cpu_ms: float = 0.0
    units_per_kib_moved: float = 0.0
    units_per_gpu_ms: float = 0.0

    def __post_init__(self) -> None:
        if not self.version:
            raise MetabolismError("calibration version is required")
        for key in ("units_per_operation", "units_per_cpu_ms",
                    "units_per_kib_moved", "units_per_gpu_ms"):
            _finite_nonnegative(key, getattr(self, key))

    def cost(self, measurement: WorkMeasurement) -> float:
        return (
            measurement.operations * self.units_per_operation
            + (measurement.cpu_time_ns / 1_000_000.0) * self.units_per_cpu_ms
            + (measurement.bytes_moved / 1024.0) * self.units_per_kib_moved
            + (measurement.gpu_time_ns / 1_000_000.0) * self.units_per_gpu_ms
        )


@dataclass(frozen=True)
class MetabolicState:
    """Immutable reserve state; tuples are sorted by organ name."""

    reserves: tuple[tuple[str, float], ...]
    cumulative_production: float = 0.0
    cumulative_consumption: float = 0.0
    cumulative_unmet_demand: float = 0.0

    def __post_init__(self) -> None:
        names = [name for name, _ in self.reserves]
        if names != sorted(names) or len(names) != len(set(names)):
            raise MetabolismError("reserves must have unique, alphabetically sorted names")
        for name, value in self.reserves:
            if not name:
                raise MetabolismError("reserve organ name cannot be empty")
            _finite_nonnegative(f"reserve[{name}]", value)
        for key in ("cumulative_production", "cumulative_consumption",
                    "cumulative_unmet_demand"):
            _finite_nonnegative(key, getattr(self, key))

    def as_dict(self) -> dict[str, float]:
        return dict(self.reserves)


@dataclass(frozen=True)
class FlowEvent:
    source: str
    target: str
    amount: float


@dataclass(frozen=True)
class MetabolicResult:
    state: MetabolicState
    admitted: tuple[tuple[str, bool], ...]
    requested_cost: tuple[tuple[str, float], ...]
    consumed_cost: tuple[tuple[str, float], ...]
    flow_events: tuple[FlowEvent, ...]
    conservation_error: float


class ComputationalBloodstream:
    """Deterministic reserve circulation and starvation-gated work admission."""

    def __init__(
        self,
        organs: Sequence[OrganSpec],
        edges: Sequence[CirculationEdge],
        calibration: MetabolicCalibration,
    ) -> None:
        self.organs = {o.name: o for o in organs}
        if not self.organs or len(self.organs) != len(organs):
            raise MetabolismError("organs must be non-empty and uniquely named")
        self.edges = tuple(edges)
        for edge in self.edges:
            if edge.source not in self.organs or edge.target not in self.organs:
                raise MetabolismError("circulation edge references unknown organ")
        self.calibration = calibration

    def initial_state(self, reserves: Mapping[str, float] | None = None) -> MetabolicState:
        supplied = dict(reserves or {})
        if set(supplied) - set(self.organs):
            raise MetabolismError("initial reserves contain an unknown organ")
        values = {}
        for name, spec in self.organs.items():
            value = float(supplied.get(name, spec.setpoint))
            _finite_nonnegative(f"initial reserve[{name}]", value)
            if value > spec.capacity:
                raise MetabolismError(f"initial reserve[{name}] exceeds capacity")
            values[name] = value
        return MetabolicState(tuple(sorted(values.items())))

    def step(
        self,
        state: MetabolicState,
        measurements: Mapping[str, WorkMeasurement],
        *,
        dt: float = 1.0,
        production: Mapping[str, float] | None = None,
        circulation_enabled: bool = True,
    ) -> MetabolicResult:
        dt = _finite_nonnegative("dt", dt)
        if dt <= 0:
            raise MetabolismError("dt must be positive")
        current = state.as_dict()
        if set(current) != set(self.organs):
            raise MetabolismError("state organ set does not match this bloodstream")
        if set(measurements) - set(self.organs):
            raise MetabolismError("measurement references unknown organ")
        production = dict(production or {})
        if set(production) - set(self.organs):
            raise MetabolismError("production references unknown organ")

        before_total = sum(current.values())
        produced = 0.0
        for name, amount in production.items():
            amount = _finite_nonnegative(f"production[{name}]", amount)
            accepted = min(amount, self.organs[name].capacity - current[name])
            current[name] += accepted
            produced += accepted

        flows: list[FlowEvent] = []
        if circulation_enabled:
            # Stable edge order makes replay deterministic. Each transfer is
            # bounded by donor surplus above setpoint and receiver deficit.
            for edge in self.edges:
                donor = self.organs[edge.source]
                receiver = self.organs[edge.target]
                surplus = max(0.0, current[edge.source] - donor.setpoint)
                deficit = max(0.0, receiver.setpoint - current[edge.target])
                amount = min(
                    edge.conductance * dt * surplus,
                    deficit,
                    current[edge.source] - donor.minimum,
                    receiver.capacity - current[edge.target],
                )
                amount = max(0.0, amount)
                if amount:
                    current[edge.source] -= amount
                    current[edge.target] += amount
                    flows.append(FlowEvent(edge.source, edge.target, amount))

        requested: dict[str, float] = {}
        consumed: dict[str, float] = {}
        admitted: dict[str, bool] = {}
        unmet = 0.0
        for name in sorted(self.organs):
            measurement = measurements.get(name, WorkMeasurement())
            if not isinstance(measurement, WorkMeasurement):
                raise MetabolismError("measurements must contain WorkMeasurement values")
            cost = self.calibration.cost(measurement)
            requested[name] = cost
            floor = self.organs[name].minimum
            if current[name] - cost >= floor:
                admitted[name] = True
                consumed[name] = cost
                current[name] -= cost
            else:
                admitted[name] = False
                consumed[name] = 0.0
                unmet += cost

        after_total = sum(current.values())
        consumed_total = sum(consumed.values())
        expected_total = before_total + produced - consumed_total
        conservation_error = after_total - expected_total
        next_state = MetabolicState(
            tuple(sorted(current.items())),
            state.cumulative_production + produced,
            state.cumulative_consumption + consumed_total,
            state.cumulative_unmet_demand + unmet,
        )
        return MetabolicResult(
            state=next_state,
            admitted=tuple(sorted(admitted.items())),
            requested_cost=tuple(sorted(requested.items())),
            consumed_cost=tuple(sorted(consumed.items())),
            flow_events=tuple(flows),
            conservation_error=conservation_error,
        )
