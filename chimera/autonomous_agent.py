"""Autonomous world activity policy for Chimera.

This is a transparent, deterministic baseline policy, not a trained general
intelligence. It demonstrates an organism selecting a self-generated world goal,
constructing a persistent structure, observing its own world, and recording the
outcome through the coupled organism kernel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .organism_kernel import OrganismKernel
from .reality_engine import RealityEngine, WorldResult


@dataclass(frozen=True)
class AgentStep:
    goal: str
    action: str
    world_revision: int
    result: dict[str, Any]


class AutonomousWorldAgent:
    """Goal selector and world-action executor for one persistent organism."""

    def __init__(self, world: RealityEngine, organism: OrganismKernel):
        self.world = world
        self.organism = organism
        if organism.world is not world:
            raise ValueError("Agent and organism kernel must share one RealityEngine")

    @staticmethod
    def _shelter_blueprint() -> dict[str, Any]:
        return {
            "name": "first_shelter",
            "parts": [
                {"kind": "shelter_foundation", "position": [0, 0.5, 0],
                 "size": [6, 1, 6], "material": "stone", "mass": 120},
                {"kind": "shelter_wall", "position": [-2.75, 2.5, 0],
                 "size": [0.5, 3, 5], "material": "wood", "mass": 30},
                {"kind": "shelter_wall", "position": [2.75, 2.5, 0],
                 "size": [0.5, 3, 5], "material": "wood", "mass": 30},
                {"kind": "shelter_wall", "position": [0, 2.5, -2.75],
                 "size": [5, 3, 0.5], "material": "wood", "mass": 30},
                {"kind": "shelter_wall", "position": [0, 2.5, 2.75],
                 "size": [5, 3, 0.5], "material": "wood", "mass": 30},
                {"kind": "shelter_roof", "position": [0, 4.25, 0],
                 "size": [6, 0.5, 6], "material": "wood", "mass": 45},
            ],
        }

    @staticmethod
    def _workbench_blueprint() -> dict[str, Any]:
        parts = []
        for x in (-0.55, 0.55):
            for z in (-0.55, 0.55):
                parts.append({
                    "kind": "workbench_leg",
                    "position": [x, 1.4, z],
                    "size": [0.15, 0.8, 0.15],
                    "material": "wood", "mass": 2,
                })
        parts.append({
            "kind": "workbench_top",
            "position": [0, 1.9, 0],
            "size": [1.5, 0.2, 1.5],
            "material": "wood", "mass": 8,
        })
        return {"name": "first_workbench", "parts": parts}

    def _structures(self) -> set[str]:
        names = set()
        for entity in self.world.entities():
            name = entity.metadata.get("structure_name")
            if name:
                names.add(str(name))
        return names

    def choose_goal(self) -> str:
        """Select the next unmet self-generated developmental objective."""
        structures = self._structures()
        state = self.organism.state
        if "first_shelter" not in structures:
            return "create_shelter" if state.body.energy >= 0.55 else "recover_and_regulate"
        if "first_workbench" not in structures:
            return "create_workbench" if state.body.energy >= 0.35 else "recover_and_regulate"
        return "inspect_world_and_consolidate_memory"

    def step(
        self, dt: float | None = None,
        cognitive_feedback: Mapping[str, float] | None = None,
    ) -> AgentStep:
        """Perform one autonomous cycle, incorporating prior-cycle sensory evidence."""
        dt = self.world.config.fixed_dt if dt is None else float(dt)
        if dt <= 0:
            raise ValueError("dt must be positive")
        feedback = dict(cognitive_feedback or {})
        prediction_error = max(0.0, min(1.0, float(feedback.get("prediction_error", 0.0))))
        novelty_feedback = max(0.0, min(1.0, float(feedback.get("novelty", 0.0))))
        cognitive_action_cost = max(0.0, float(feedback.get("action_energy_cost", 0.0)))
        if not math.isfinite(cognitive_action_cost):
            raise ValueError("cognitive action cost must be finite")
        goal = self.choose_goal()
        self.organism.set_goal(goal)

        if goal == "create_shelter":
            result = self.world.create_structure(
                self._shelter_blueprint(),
                actor_id=self.organism.organism_id,
                expected_revision=self.world.revision(),
            )
            self.organism.tick(
                dt=dt, action_energy_cost=0.12 + cognitive_action_cost, mechanical_strain=0.35,
                prediction_error=max(0.25, prediction_error), novelty=max(0.9, novelty_feedback),
                outcome="shelter_committed",
                expected_revision=result.revision,
            )
            return AgentStep(goal, "construct_structure",
                             self.world.revision(), result.details)

        if goal == "create_workbench":
            result = self.world.create_structure(
                self._workbench_blueprint(),
                actor_id=self.organism.organism_id,
                expected_revision=self.world.revision(),
            )
            self.organism.tick(
                dt=dt, action_energy_cost=0.07 + cognitive_action_cost, mechanical_strain=0.2,
                prediction_error=max(0.2, prediction_error), novelty=max(0.65, novelty_feedback),
                outcome="workbench_committed",
                expected_revision=result.revision,
            )
            return AgentStep(goal, "construct_structure",
                             self.world.revision(), result.details)

        if goal == "recover_and_regulate":
            result = self.organism.tick(
                dt=dt, action_energy_cost=cognitive_action_cost, mechanical_strain=0.0,
                prediction_error=max(0.05, prediction_error), novelty=novelty_feedback,
                outcome="rest_regulation", resting=True,
                expected_revision=self.world.revision(),
            )
            return AgentStep(goal, "rest_regulation",
                             result.revision, result.details)

        observation = self.world.observe(
            center=self.organism.state.position, radius=20.0
        )
        entity_count = observation["entity_count"]
        # A deterministic surprise proxy for this baseline: a change in observed
        # entity count relative to the organism's stored previous outcome.
        previous = self.organism.state.self_model.last_outcome or ""
        novelty = 0.15 if str(entity_count) not in previous else 0.02
        result = self.organism.tick(
            dt=dt, action_energy_cost=0.002 + cognitive_action_cost, mechanical_strain=0.0,
            prediction_error=max(0.08, prediction_error), novelty=max(novelty, novelty_feedback),
            outcome=f"observed_entities:{entity_count}",
            expected_revision=observation["revision"],
        )
        return AgentStep(
            goal, "observe_and_consolidate", result.revision,
            {"entity_count": entity_count,
             "observed_revision": observation["revision"],
             "organism": self.organism.snapshot()},
        )
