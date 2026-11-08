"""Tests for the organism-owned simulation runtime."""

import asyncio
import os
import tempfile
import unittest

from chimera.autonomous_agent import AutonomousWorldAgent
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, WorldConfig
from chimera.runtime import AutonomousRuntime
from chimera.latent_language import GlobalWorkspace, LatentState, SpecialistProposal
from types import SimpleNamespace


class AutonomousRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "runtime.sqlite3")
        self.world = RealityEngine(WorldConfig(database=self.path))
        self.organism = OrganismKernel(self.world, "runtime-organism")
        self.agent = AutonomousWorldAgent(self.world, self.organism)
        self.runtime = AutonomousRuntime(self.world, self.agent)

    async def asyncTearDown(self):
        self.world.close()
        self.tmp.cleanup()

    async def test_state_snapshot_exposes_selected_creative_artifact(self):
        state = LatentState.empty()
        workspace = GlobalWorkspace()
        proposal = SpecialistProposal(
            "creative-test", "creative_generation", "creative_artifact",
            {"title": "Living Canopy", "concept": "A calm garden canopy.",
             "authority": "artifact_only"},
            0.65, 0.75, 0.05, 0.55, 0.0, self.world.revision(),
            ("request:test",),
        )
        workspace.compete(state, [proposal])
        self.runtime.cognition = SimpleNamespace(state=state, workspace=workspace)
        selected = self.runtime.snapshot()["cognition"]["selected"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["proposal_id"], "creative-test")
        self.assertEqual(selected[0]["artifact"]["title"], "Living Canopy")
        self.assertEqual(selected[0]["artifact"]["authority"], "artifact_only")

    async def test_runtime_owns_clock_and_runs_autonomous_lifecycle(self):
        stop = asyncio.Event()
        await self.runtime.run(stop, max_ticks=3)
        snapshot = self.runtime.snapshot()
        self.assertEqual(snapshot["runtime_tick"], 3)
        self.assertAlmostEqual(
            snapshot["simulation_time"], 3 * self.world.config.fixed_dt
        )
        self.assertIn("first_shelter", {
            e.metadata.get("structure_name") for e in self.world.entities()
        })
        self.assertIn("first_workbench", {
            e.metadata.get("structure_name") for e in self.world.entities()
        })
        self.assertEqual(self.organism.state.temporal.tick, 3)


if __name__ == "__main__":
    unittest.main()
