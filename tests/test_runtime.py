"""Tests for the organism-owned simulation runtime."""

import asyncio
import os
import tempfile
import unittest

from chimera.autonomous_agent import AutonomousWorldAgent
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, WorldConfig
from chimera.runtime import AutonomousRuntime


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
