"""Physiology-governed gateway for committed organism world actions.

Planners propose typed toolbox operations. This gateway enforces organism
viability and reserve admission, commits through the existing RealityEngine
transaction boundary, then records the attributable outcome in ISCE.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .organism_kernel import OrganismKernel
from .reality_engine import RevisionConflict, RealityEngine
from .toolbox import ChimeraToolbox, ToolboxError


class ActionGatewayError(ValueError):
    """A proposed action failed governance or resource admission."""


@dataclass(frozen=True)
class ActionProposal:
    tool: str
    action: str
    arguments: dict[str, Any]
    expected_revision: int
    expected_success: float = 0.5
    novelty: float = 0.0

    def __post_init__(self) -> None:
        if not self.tool or not self.action:
            raise ActionGatewayError("Tool and action names are required")
        if not isinstance(self.arguments, dict):
            raise ActionGatewayError("Action arguments must be an object")
        if self.expected_revision < 0:
            raise ActionGatewayError("Expected revision cannot be negative")
        for name, value in (("expected_success", self.expected_success),
                            ("novelty", self.novelty)):
            if not math.isfinite(float(value)) or not 0.0 <= value <= 1.0:
                raise ActionGatewayError(f"{name} must be in [0, 1]")


@dataclass(frozen=True)
class ActionReceipt:
    tool: str
    action: str
    actor_id: str
    action_id: str
    action_revision: int
    organism_revision: int
    logical_work_units: float
    prediction_error: float
    result: dict[str, Any]


class OrganismActionGateway:
    """Single governed path from an organism proposal to a world commit."""

    ENERGY_PER_WORK_UNIT = 0.0005
    RESERVE_PER_WORK_UNIT = 0.001
    MIN_POST_ACTION_RESERVE = 0.05

    _MUTATING_ACTIONS = {
        ("world_builder", "create_object"),
        ("world_builder", "create_structure"),
        ("tool_fabricator", "fabricate"),
        ("life_generator", "spawn"),
        ("movement_lab", "move"),
        ("movement_lab", "advance_physics"),
    }

    def __init__(
        self,
        world: RealityEngine,
        organism: OrganismKernel,
        toolbox: ChimeraToolbox | None = None,
        *,
        dt: float | None = None,
    ):
        if organism.world is not world:
            raise ValueError("Gateway and organism must share one RealityEngine")
        self.world = world
        self.organism = organism
        self.toolbox = toolbox or ChimeraToolbox(
            world, actor_id=organism.organism_id
        )
        if self.toolbox.world is not world:
            raise ValueError("Gateway and toolbox must share one RealityEngine")
        self.dt = world.config.fixed_dt if dt is None else float(dt)
        if not math.isfinite(self.dt) or not 0.0 < self.dt <= 10.0:
            raise ValueError("Gateway dt must be in (0, 10]")

    @staticmethod
    def _estimated_work(proposal: ActionProposal) -> float:
        pair = (proposal.tool, proposal.action)
        if pair == ("world_builder", "create_structure"):
            blueprint = proposal.arguments.get("blueprint")
            parts = blueprint.get("parts") if isinstance(blueprint, dict) else None
            if not isinstance(parts, list):
                raise ActionGatewayError("Structure proposals require a parts list")
            return float(max(1, len(parts)))
        if pair == ("movement_lab", "advance_physics"):
            steps = proposal.arguments.get("steps", 1)
            if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= 1000:
                raise ActionGatewayError("Physics step proposals require 1..1000 steps")
            return float(steps)
        return 1.0

    @staticmethod
    def _actual_work(proposal: ActionProposal, result: dict[str, Any]) -> float:
        details = result.get("details", {})
        if proposal.action == "create_structure":
            return float(details.get("part_count", 0))
        if proposal.action == "advance_physics":
            return float(result.get("steps", 1))
        return 1.0

    def execute(self, proposal: ActionProposal) -> ActionReceipt:
        if not isinstance(proposal, ActionProposal):
            raise ActionGatewayError("Gateway accepts only ActionProposal values")
        pair = (proposal.tool, proposal.action)
        if pair not in self._MUTATING_ACTIONS:
            raise ActionGatewayError("Action is not enabled for governed mutation")
        if proposal.expected_revision != self.world.revision():
            raise RevisionConflict(
                f"Expected revision {proposal.expected_revision}; "
                f"current revision is {self.world.revision()}"
            )
        if not self.organism.can_act:
            raise ActionGatewayError("Organism viability gate refused the action")

        estimated_work = self._estimated_work(proposal)
        energy_cost = estimated_work * self.ENERGY_PER_WORK_UNIT
        reserve_cost = estimated_work * self.RESERVE_PER_WORK_UNIT
        state = self.organism.state
        if state.resources.reserve - reserve_cost <= self.MIN_POST_ACTION_RESERVE:
            raise ActionGatewayError("Insufficient internal reserve for proposed work")
        if state.body.energy - energy_cost <= 0.12:
            raise ActionGatewayError("Insufficient body energy for proposed work")

        # The toolbox is the only mutation dispatcher. It delegates all
        # persistence, validation and revision checks to RealityEngine.
        result = self.toolbox.execute(
            proposal.tool, proposal.action, dict(proposal.arguments),
            actor_id=self.organism.organism_id,
            expected_revision=proposal.expected_revision,
        )
        actual_work = self._actual_work(proposal, result)
        if actual_work <= 0 or actual_work > estimated_work:
            raise RuntimeError("Committed action returned invalid work accounting")

        prediction_error = abs(1.0 - proposal.expected_success)
        outcome = f"{proposal.tool}.{proposal.action}:committed"
        organism_result = None
        # A concurrent world commit can advance the revision between the
        # action and its organism outcome update. Retry the state commit only;
        # never replay the already-committed world action.
        for _ in range(3):
            try:
                organism_result = self.organism.tick(
                    dt=self.dt,
                    action_energy_cost=actual_work * self.ENERGY_PER_WORK_UNIT,
                    prediction_error=prediction_error,
                    novelty=proposal.novelty,
                    outcome=outcome,
                    measured_work_units=actual_work,
                    action_success=1.0,
                    causation_id=str(result.get("action_id", "")),
                    correlation_id=str(result.get("action_id", "")),
                    expected_revision=self.world.revision(),
                )
                break
            except RevisionConflict:
                continue
        if organism_result is None:
            raise RuntimeError(
                "World action committed but organism accounting could not "
                "be reconciled; inspect the world event journal before retrying"
            )

        return ActionReceipt(
            tool=proposal.tool,
            action=proposal.action,
            actor_id=self.organism.organism_id,
            action_id=str(result.get("action_id", "")),
            action_revision=int(result.get("revision", 0)),
            organism_revision=organism_result.revision,
            logical_work_units=actual_work,
            prediction_error=prediction_error,
            result=result,
        )
