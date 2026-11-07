"""Executable tests for the Chimera Reality Engine.

Run from repository root:
    python -m unittest discover -s tests -v
"""

import os
import tempfile
import unittest

from chimera.reality_engine import (
    InvalidWorldAction,
    RealityEngine,
    RevisionConflict,
    WorldConfig,
)


class RealityEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "world.sqlite3")
        self.world = RealityEngine(WorldConfig(database=self.path))

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def test_atomic_supported_structure_creation(self):
        result = self.world.create_structure({
            "name": "two-part-test",
            "parts": [
                {"kind": "foundation", "position": [0, 0.5, 0],
                 "size": [4, 1, 4], "material": "stone", "mass": 20},
                {"kind": "upper-block", "position": [0, 1.5, 0],
                 "size": [2, 1, 2], "material": "stone", "mass": 5},
            ],
        }, actor_id="test-agent", expected_revision=0)
        self.assertEqual(result.details["part_count"], 2)
        self.assertEqual(self.world.revision(), 1)
        self.assertEqual(len(self.world.entities()), 2)
        self.assertTrue(self.world.verify_event_chain())

    def test_structure_failure_commits_nothing(self):
        with self.assertRaises(InvalidWorldAction):
            self.world.create_structure({
                "name": "invalid",
                "parts": [
                    {"kind": "floating", "position": [0, 10, 0],
                     "size": [1, 1, 1]},
                ],
            }, actor_id="test-agent", expected_revision=0)
        self.assertEqual(self.world.revision(), 0)
        self.assertEqual(self.world.entities(), [])
        self.assertEqual(self.world.event_history(), [])

    def test_optimistic_revision_rejects_stale_write(self):
        self.world.create_primitive(
            "grounded", [0, 0.5, 0], [1, 1, 1],
            actor_id="test-agent", dynamic=False, expected_revision=0,
        )
        with self.assertRaises(RevisionConflict):
            self.world.create_primitive(
                "stale", [3, 0.5, 0], [1, 1, 1],
                actor_id="test-agent", dynamic=False, expected_revision=0,
            )
        self.assertEqual(self.world.revision(), 1)

    def test_interpenetration_is_rejected(self):
        self.world.create_primitive(
            "base", [0, 0.5, 0], [2, 1, 2],
            actor_id="test-agent", dynamic=False,
        )
        with self.assertRaises(InvalidWorldAction):
            self.world.create_primitive(
                "overlap", [0, 0.5, 0], [1, 1, 1],
                actor_id="test-agent", dynamic=False,
            )
        self.assertEqual(len(self.world.entities()), 1)

    def test_dynamic_body_falls_and_contacts_ground(self):
        result = self.world.create_primitive(
            "falling", [0, 5, 0], [1, 1, 1],
            actor_id="test-agent", dynamic=True,
        )
        for _ in range(120):
            self.world.step(expected_revision=self.world.revision())
        entity = self.world.get_entity(result.entity_id)
        self.assertAlmostEqual(entity.position.y, 0.5, places=5)
        self.assertAlmostEqual(entity.velocity.y, 0.0, places=5)

    def test_field_injection_persists_and_diffuses(self):
        self.world.inject_field("memory", [0, 2, 0], 0.8,
                                actor_id="test-agent", radius=0)
        self.assertAlmostEqual(self.world.field_at([0, 2, 0])["memory"], 0.8)
        self.world.step()
        self.assertGreater(self.world.field_at([0, 2, 0])["memory"], 0.0)
        self.assertTrue(self.world.verify_event_chain())

    def test_database_reopen_preserves_authoritative_state(self):
        created = self.world.create_primitive(
            "persistent", [0, 0.5, 0], [1, 1, 1],
            actor_id="test-agent", dynamic=False,
        )
        expected_revision = self.world.revision()
        self.world.close()
        self.world = RealityEngine(WorldConfig(database=self.path))
        self.assertEqual(self.world.revision(), expected_revision)
        self.assertEqual(self.world.get_entity(created.entity_id).kind, "persistent")
        self.assertTrue(self.world.verify_event_chain())


if __name__ == "__main__":
    unittest.main()
