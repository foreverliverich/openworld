"""Tests for world-grounded sensory evidence and persistence tokens."""
import os
import tempfile
import unittest

from chimera.reality_engine import RealityEngine, WorldConfig
from chimera.sensory import capture_sensory_evidence


class SensoryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = RealityEngine(WorldConfig(
            database=os.path.join(self.tmp.name, "sensory.sqlite3")
        ))

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def test_empty_world_has_zero_salience_and_valid_first_token(self):
        evidence = capture_sensory_evidence(self.world, (0, 1, 0))
        self.assertEqual(evidence.visible_count, 0)
        self.assertEqual(evidence.salience, 0.0)
        self.assertEqual(evidence.prediction_error, 0.0)
        self.assertTrue(evidence.memory_token.startswith("sense1:0:"))

    def test_repeated_observation_has_zero_surprise_and_low_novelty(self):
        first = capture_sensory_evidence(self.world, (0, 1, 0))
        second = capture_sensory_evidence(
            self.world, (0, 1, 0), previous_token=first.memory_token
        )
        self.assertEqual(second.prediction_error, 0.0)
        self.assertEqual(second.novelty, 0.02)

    def test_new_entity_changes_signature_and_prediction(self):
        first = capture_sensory_evidence(self.world, (0, 1, 0))
        self.world.create_primitive(
            "nearby", (1, 1, 0), (0.5, 0.5, 0.5),
            actor_id="test", dynamic=True,
        )
        second = capture_sensory_evidence(
            self.world, (0, 1, 0), previous_token=first.memory_token
        )
        self.assertEqual(second.visible_count, 1)
        self.assertEqual(second.prediction_error, 1.0)
        self.assertEqual(second.novelty, 0.15)
        self.assertGreater(second.salience, 0.0)

    def test_closer_objects_increase_proximity_salience(self):
        far = self.world.create_primitive(
            "far", (10, 1, 0), (0.5, 0.5, 0.5),
            actor_id="test", dynamic=True,
        )
        far_evidence = capture_sensory_evidence(self.world, (0, 1, 0), radius=20)
        self.world.remove_entity(far.entity_id, actor_id="test")
        self.world.create_primitive(
            "near", (1, 1, 0), (0.5, 0.5, 0.5),
            actor_id="test", dynamic=True,
        )
        near_evidence = capture_sensory_evidence(self.world, (0, 1, 0), radius=20)
        self.assertGreater(near_evidence.salience, far_evidence.salience)

    def test_identical_world_observations_are_deterministic(self):
        self.world.create_primitive(
            "stable", (2, 1, 0), (0.5, 0.5, 0.5),
            actor_id="test", dynamic=True,
        )
        first = capture_sensory_evidence(self.world, (0, 1, 0))
        second = capture_sensory_evidence(self.world, (0, 1, 0))
        self.assertEqual(first.memory_token, second.memory_token)
        self.assertEqual(first.salience, second.salience)


if __name__ == "__main__":
    unittest.main()
