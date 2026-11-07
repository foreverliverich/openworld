"""Organism-owned autonomous runtime for the Chimera world.

The runtime, not the renderer, owns simulation advancement. Each tick advances
physics, runs one autonomous world decision, commits the organism's coupled
physiology/cognitive state, and emits a grounded snapshot.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
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


class AutonomousRuntime:
    def __init__(
        self,
        world: RealityEngine,
        agent: AutonomousWorldAgent,
        *,
        observer_radius: float = 24.0,
    ):
        if agent.world is not world:
            raise ValueError("Runtime and autonomous agent must share one world")
        self.world = world
        self.agent = agent
        self.observer_radius = observer_radius
        self._tick = 0
        self._running = False

    def tick(self) -> RuntimeFrame:
        """Advance one complete physics → goal → action → learning cycle."""
        physics = self.world.step(
            actor_id="reality-runtime",
            expected_revision=self.world.revision(),
        )
        agent_result = self.agent.step()
        self._tick += 1
        organism_position = self.agent.organism.state.position
        observation = self.world.observe(
            center=organism_position, radius=self.observer_radius
        )
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
        }
