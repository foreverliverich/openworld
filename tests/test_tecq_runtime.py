import os
import tempfile
import unittest

from chimera.autonomous_agent import AutonomousWorldAgent
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, WorldConfig
from chimera.runtime import AutonomousRuntime
from chimera.tecq.engine import TECQConfig, TECQEngine, lattice_state


class TECQRuntimeTests(unittest.TestCase):
    def test_runtime_advances_tecq_and_commits_feedback_through_isce(self):
        with tempfile.TemporaryDirectory() as tmp:
            world = RealityEngine(WorldConfig(database=os.path.join(tmp, "runtime.sqlite3")))
            try:
                organism = OrganismKernel(world, "runtime-tecq")
                agent = AutonomousWorldAgent(world, organism)
                config = TECQConfig(cell_count=64)
                engine = TECQEngine(lattice_state(config), config)
                runtime = AutonomousRuntime(world, agent, tecq_engine=engine)
                frame = runtime.tick()
                self.assertEqual(frame.tecq_result["tick"], 1)
                self.assertEqual(engine.state.tick, 1)
                self.assertEqual(organism.state.temporal.tick, 1)
                self.assertEqual(frame.world_revision, world.revision())
                self.assertIsNotNone(runtime.snapshot()["tecq"])
            finally:
                world.close()


if __name__ == "__main__":
    unittest.main()
