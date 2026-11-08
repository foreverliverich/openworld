"""Organism-owned runtime with optional Latent Language cognition cycles.

The runtime owns the clock. ISCE owns intrinsic organism state; RealityEngine owns
the external world. Latent Language is an ephemeral projection/workspace that
produces proposals, and only its revision-checked gateway can commit those proposals.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import Any, Optional

from .autonomous_agent import AutonomousWorldAgent
from .reality_engine import RealityEngine


@dataclass(frozen=True)
class RuntimeFrame:
    tick: int
    world_revision: int
    simulation_time: float
    physics_result: dict[str, Any]
    agent_result: dict[str, Any]
    observation: dict[str, Any]
    cognition_result: dict[str, Any] | None = None


class AutonomousRuntime:
    def __init__(
        self,
        world: RealityEngine,
        agent: AutonomousWorldAgent,
        *,
        observer_radius: float = 24.0,
        cognition: Any | None = None,
        cognition_gateway: Any | None = None,
    ):
        if agent.world is not world:
            raise ValueError("Runtime and autonomous agent must share one world")
        if cognition_gateway is not None and cognition is None:
            raise ValueError("A cognition gateway requires a cognition coordinator")
        if cognition_gateway is not None and cognition_gateway.workspace is not cognition.workspace:
            raise ValueError("Cognition coordinator and action gateway must share one workspace")
        if cognition_gateway is not None and cognition_gateway.organism is not agent.organism:
            raise ValueError("Cognition gateway must use the runtime's authoritative ISCE organism")
        self.world = world
        self.agent = agent
        self.observer_radius = observer_radius
        self.cognition = cognition
        self.cognition_gateway = cognition_gateway
        self._pending_cognition: list[tuple[list[dict[str, Any]], Any]] = []
        self._pending_feedback: dict[str, float] = {}
        self._tick = 0
        self._running = False

    def queue_cognition_cycle(
        self, observations: list[dict[str, Any]], context: Any
    ) -> None:
        """Queue real encoded sensor inputs for the next organism-owned tick."""
        if self.cognition is None:
            raise RuntimeError("No Latent Language coordinator is configured")
        if not isinstance(observations, list):
            raise ValueError("observations must be a list of modality payload records")
        self._pending_cognition.append((list(observations), context))

    def execute_cognitive_proposal(
        self, proposal: Any, *, actor_id: str = "chimera"
    ) -> dict[str, Any]:
        """Commit a workspace-selected proposal through the sole cognitive gateway."""
        if self.cognition_gateway is None:
            raise RuntimeError("No governed cognitive action gateway is configured")
        return self.cognition_gateway.execute(proposal, actor_id=actor_id)

    def tick(self) -> RuntimeFrame:
        """Advance physics, baseline policy, perception and one queued cognition cycle."""
        physics = self.world.step(
            actor_id="reality-runtime",
            expected_revision=self.world.revision(),
        )
        agent_result = self.agent.step(cognitive_feedback=self._pending_feedback)
        self._pending_feedback = {}
        self._tick += 1
        organism_position = self.agent.organism.state.position
        observation = self.world.observe(
            center=organism_position, radius=self.observer_radius
        )
        cognition_result = None
        if self._pending_cognition:
            observations, context = self._pending_cognition.pop(0)
            context = replace(context, world_revision=self.world.revision())
            cycle = self.cognition.cycle(
                observations, context, dt=self.world.config.fixed_dt,
                organism_state=self.agent.organism.state,
            )
            cognition_result = {
                "state_digest": cycle.state.digest,
                "workspace_tick": cycle.broadcast.tick,
                "selected": [
                    {"proposal_id": p.proposal_id, "specialist": p.specialist,
                     "kind": p.kind, "confidence": p.confidence,
                     "world_revision": p.world_revision}
                    for p in cycle.broadcast.selected
                ],
                "rejected_count": len(cycle.broadcast.rejected),
                "feedback": {
                    "novelty": cycle.feedback.novelty,
                    "prediction_error": cycle.feedback.prediction_error,
                    "modality_novelty": dict(cycle.feedback.modality_novelty),
                },
            }
            self._pending_feedback = {"novelty": cycle.feedback.novelty}
            if cycle.feedback.prediction_error is not None:
                self._pending_feedback["prediction_error"] = cycle.feedback.prediction_error
        return RuntimeFrame(
            tick=self._tick,
            world_revision=observation["revision"],
            simulation_time=observation["simulation_time"],
            physics_result={
                "revision": physics.revision,
                "changes": physics.details["changes"],
            },
            agent_result={
                "goal": agent_result.goal,
                "action": agent_result.action,
                "revision": agent_result.world_revision,
                "result": agent_result.result,
            },
            observation=observation,
            cognition_result=cognition_result,
        )

    async def run(
        self,
        stop_event: asyncio.Event,
        *,
        interval_seconds: Optional[float] = None,
        max_ticks: Optional[int] = None,
    ) -> None:
        """Run autonomously until stopped or max_ticks is reached."""
        interval = interval_seconds or self.world.config.fixed_dt
        if interval <= 0:
            raise ValueError("interval_seconds must be positive")
        if self._running:
            raise RuntimeError("AutonomousRuntime is already running")
        self._running = True
        completed = 0
        try:
            while not stop_event.is_set():
                self.tick()
                completed += 1
                if max_ticks is not None and completed >= max_ticks:
                    break
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            self._running = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "runtime_tick": self._tick,
            "running": self._running,
            "world_revision": self.world.revision(),
            "simulation_time": self.world.simulation_time(),
            "organism": self.agent.organism.snapshot(),
            "observation": self.world.observe(
                center=self.agent.organism.state.position,
                radius=self.observer_radius,
            ),
            "cognition_workspace_tick": (
                self.cognition.workspace.tick if self.cognition is not None else None
            ),
            "pending_cognitive_feedback": dict(self._pending_feedback),
        }
