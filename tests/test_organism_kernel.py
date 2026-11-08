"""Tests for ISCE-owned organism state and world-field causal coupling."""

import json
import os
import tempfile
import unittest

from chimera.isce import OrganismState as ISCEOrganismState
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import InvalidWorldAction, RealityEngine, WorldConfig


class OrganismKernelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "organism.sqlite3")
        self.world = RealityEngine(WorldConfig(database=self.path))
        self.organism = OrganismKernel(self.world, "test-organism")

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def test_tick_updates_isce_physiology_and_world_fields_atomically(self):
        before_revision = self.world.revision()
        before_energy = self.organism.state.body.energy
        result = self.organism.tick(
            dt=1.0, action_energy_cost=0.08, mechanical_strain=0.4,
            prediction_error=0.7, novelty=0.8,
            outcome="construction-attempt-observed",
            expected_revision=before_revision,
        )
        self.assertEqual(result.revision, before_revision + 1)
        self.assertLess(self.organism.state.body.energy, before_energy)
        self.assertGreater(self.organism.state.body.stress, 0.0)
        persisted = self.world.get_organism_state()
        self.assertEqual(persisted["schema_version"], 1)
        self.assertIn("body", persisted)
        self.assertEqual(ISCEOrganismState.from_dict(persisted), self.organism.state)
        local = self.world.field_at(self.organism.state.position)
        self.assertAlmostEqual(local["energy"], self.organism.state.body.energy)
        self.assertAlmostEqual(local["stress"], self.organism.state.body.stress)
        self.assertAlmostEqual(
            local["memory"], self.organism.state.self_model.memory_strength
        )
        self.assertTrue(self.world.verify_event_chain())

    def test_world_fields_feed_back_into_next_isce_transition(self):
        position = self.organism.state.position
        self.world.inject_field("stress", position, 0.9,
                                actor_id="environment", radius=0)
        baseline = self.organism.state.body.stress
        self.organism.tick(dt=1.0, expected_revision=self.world.revision())
        self.assertGreater(self.organism.state.body.stress, baseline)

    def test_isce_state_survives_runtime_restart(self):
        self.organism.set_goal("build shelter")
        self.organism.tick(dt=1.0, action_energy_cost=0.1)
        expected = self.organism.state.to_dict()
        self.world.close()
        self.world = RealityEngine(WorldConfig(database=self.path))
        self.organism = OrganismKernel(self.world, "test-organism")
        self.assertEqual(self.organism.state.to_dict(), expected)
        self.assertIsInstance(self.organism.state, ISCEOrganismState)

    def test_legacy_flat_state_migrates_into_isce_on_next_tick(self):
        legacy = {
            "organism_id": "test-organism",
            "position": {"x": 3.0, "y": 1.5, "z": -2.0},
            "energy": 0.61, "stress": 0.31, "integrity": 0.82,
            "fatigue": 0.2, "memory_strength": 0.44, "curiosity": 0.7,
            "prediction_error": 0.25, "confidence": 0.75,
            "allostatic_error": 0.12, "age_seconds": 19.0, "tick": 7,
            "active_goal": "legacy-goal", "last_outcome": "legacy-outcome",
        }
        # Simulate a database created by the pre-ISCE release. Legacy
        # payloads are readable for migration but rejected by new write APIs.
        self.world._db.execute(
            "INSERT INTO organism_state(singleton,payload) VALUES(1,?)",
            (json.dumps(legacy, sort_keys=True),),
        )
        with self.assertRaises(InvalidWorldAction):
            self.world.commit_organism_tick(
                legacy, {"energy": 0.61, "stress": 0.31, "memory": 0.44,
                         "cohesion": 0.74},
                actor_id="test-organism",
            )
        migrated = OrganismKernel(self.world, "test-organism")
        self.assertTrue(migrated.snapshot()["migration_pending"])
        self.assertEqual(migrated.state.temporal.tick, 7)
        self.assertEqual(migrated.state.position, (3.0, 1.5, -2.0))
        self.assertAlmostEqual(migrated.state.body.energy, 0.61)
        self.assertAlmostEqual(migrated.state.self_model.memory_strength, 0.44)
        migrated.tick(dt=0.5, expected_revision=self.world.revision())
        persisted = self.world.get_organism_state()
        self.assertEqual(persisted["schema_version"], 1)
        self.assertAlmostEqual(persisted["position"][0], 3.0)
        self.assertAlmostEqual(persisted["position"][2], -2.0)
        # The migrated body now participates in real gravity/contact during
        # the first committed ISCE tick instead of retaining a display-only
        # floating position.
        self.assertGreater(persisted["position"][1], 0.0)
        self.assertLess(persisted["position"][1], 1.5)
        self.assertTrue(
            persisted["articulation"]["contacts"],
            f"migrated position={persisted['position']}, articulation={persisted['articulation']}",
        )
        self.assertFalse(migrated.snapshot()["migration_pending"])
        self.assertTrue(self.world.verify_event_chain())

    def test_failed_revision_does_not_publish_uncommitted_state(self):
        before = self.organism.state
        stale_revision = self.world.revision() - 1
        from chimera.reality_engine import RevisionConflict
        with self.assertRaises(RevisionConflict):
            self.organism.tick(dt=1.0, expected_revision=stale_revision)
        self.assertEqual(self.organism.state, before)


if __name__ == "__main__":
    unittest.main()
