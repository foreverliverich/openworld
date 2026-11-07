"""Tests for body <-> world-field causal coupling."""

import os
import tempfile
import unittest

from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, WorldConfig


class OrganismKernelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "organism.sqlite3")
        self.world = RealityEngine(WorldConfig(database=self.path))
        self.organism = OrganismKernel(self.world, "test-organism")

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def test_tick_updates_physiology_and_world_fields_atomically(self):
        before_revision = self.world.revision()
        before_energy = self.organism.state.energy
        result = self.organism.tick(
            dt=1.0, action_energy_cost=0.08, mechanical_strain=0.4,
            prediction_error=0.7, novelty=0.8,
            outcome="construction-attempt-observed",
            expected_revision=before_revision,
        )
        self.assertEqual(result.revision, before_revision + 1)
        self.assertLess(self.organism.state.energy, before_energy)
        self.assertGreater(self.organism.state.stress, 0.0)
        local = self.world.field_at(self.organism.state.position.as_tuple())
        self.assertAlmostEqual(local["energy"], self.organism.state.energy)
        self.assertAlmostEqual(local["stress"], self.organism.state.stress)
        self.assertAlmostEqual(local["memory"], self.organism.state.memory_strength)
        self.assertTrue(self.world.verify_event_chain())

    def test_world_fields_feed_back_into_next_physiology_tick(self):
        position = self.organism.state.position.as_tuple()
        self.world.inject_field("stress", position, 0.9,
                                actor_id="environment", radius=0)
        baseline = self.organism.state.stress
        self.organism.tick(dt=1.0, expected_revision=self.world.revision())
        self.assertGreater(self.organism.state.stress, baseline)

    def test_organism_state_survives_runtime_restart(self):
        self.organism.tick(dt=1.0, action_energy_cost=0.1)
        expected = self.organism.state.to_dict()
        self.world.close()
        self.world = RealityEngine(WorldConfig(database=self.path))
        self.organism = OrganismKernel(self.world, "test-organism")
        self.assertEqual(self.organism.state.to_dict(), expected)


if __name__ == "__main__":
    unittest.main()
