import os
import tempfile
import unittest

from chimera.tecq.engine import TECQConfig, TECQEngine, lattice_state
from chimera.tecq.integration import TECQOrganismAdapter
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, RevisionConflict, WorldConfig


class TECQOrganismIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = RealityEngine(WorldConfig(database=os.path.join(self.tmp.name, "world.sqlite3")))
        self.organism = OrganismKernel(self.world, "tecq-test")
        config = TECQConfig(cell_count=64)
        self.engine = TECQEngine(lattice_state(config), config)
        self.adapter = TECQOrganismAdapter(self.engine, self.organism)

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def test_cell_physiology_flows_through_isce_and_world_commit(self):
        revision = self.world.revision()
        result = self.adapter.tick(external_drive=[.1] * 64, expected_revision=revision)
        self.assertEqual(result["world_revision"], revision + 1)
        self.assertEqual(self.engine.state.tick, 1)
        self.assertEqual(self.organism.state.temporal.tick, 1)
        self.assertEqual(result["tecq_checkpoint_digest"], self.engine.state.digest())
        self.assertEqual(self.world.get_organism_state()["schema_version"], 1)
        self.assertTrue(self.world.verify_event_chain())

    def test_rejected_world_commit_rolls_back_tecq_tick(self):
        before = self.engine.state.digest()
        with self.assertRaises(RevisionConflict):
            self.adapter.tick(external_drive=[.2] * 64, expected_revision=-1)
        self.assertEqual(self.engine.state.digest(), before)
        self.assertEqual(self.organism.state.temporal.tick, 0)

    def test_environmental_feedback_is_validated(self):
        with self.assertRaises(ValueError):
            self.organism.tick(dt=.01, environmental_feedback={"unknown": .5})
        with self.assertRaises(ValueError):
            self.organism.tick(dt=.01, environmental_feedback={"energy": float("nan")})


if __name__ == "__main__":
    unittest.main()
