import tempfile
import unittest
from pathlib import Path

from chimera import ChimeraToolbox, RealityEngine, WorldConfig
from chimera.toolbox import ToolboxError


class ChimeraToolboxTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = str(Path(self.temp_dir.name) / "world.sqlite3")
        self.world = RealityEngine(WorldConfig(database=database))
        self.tools = ChimeraToolbox(self.world, actor_id="test-agent")

    def tearDown(self):
        self.world.close()
        self.temp_dir.cleanup()

    def test_manifest_exposes_six_tool_domains(self):
        names = {item["name"] for item in self.tools.manifest()}
        self.assertEqual(names, {
            "body_forge", "world_builder", "tool_fabricator",
            "life_generator", "movement_lab", "research_lab",
        })

    def test_world_builder_commits_to_authoritative_world(self):
        result = self.tools.execute(
            "world_builder", "create_object",
            {"kind": "stone", "position": [0, 0.5, 0],
             "size": [1, 1, 1], "dynamic": False},
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["revision"], self.world.revision())
        self.assertEqual(len(self.world.entities()), 1)
        self.assertTrue(self.world.verify_event_chain())

    def test_body_forge_creates_inspectable_body_prototype(self):
        result = self.tools.execute(
            "body_forge", "create_body",
            {"form": "quadruped", "position": [0, 2, 0],
             "size": [1.5, 1, 2], "anatomy": {"limbs": 4}},
        )
        entity_id = result["entity_id"]
        inspected = self.tools.execute(
            "body_forge", "inspect_body", {"entity_id": entity_id},
        )
        self.assertEqual(inspected["entity"]["metadata"]["form"], "quadruped")
        self.assertEqual(inspected["entity"]["metadata"]["anatomy"]["limbs"], 4)

    def test_fabricator_and_life_generator_create_persistent_entities(self):
        tool = self.tools.execute(
            "tool_fabricator", "fabricate",
            {"name": "probe", "position": [0, 2, 0],
             "size": [0.2, 0.2, 0.5], "capabilities": ["measure"]},
        )
        life = self.tools.execute(
            "life_generator", "spawn",
            {"species": "digital_fly", "position": [2, 2, 0],
             "size": [0.5, 0.3, 0.7], "genome_ref": "genome:test"},
        )
        self.assertEqual(
            self.world.get_entity(tool["entity_id"]).metadata["execution_status"],
            "world_item_only",
        )
        organism = self.world.get_entity(life["entity_id"])
        self.assertFalse(organism.metadata["active_agent_runtime"])
        self.assertEqual(organism.metadata["species"], "digital_fly")

    def test_movement_lab_and_research_lab_are_connected(self):
        created = self.tools.execute(
            "world_builder", "create_object",
            {"kind": "marker", "position": [0, 3, 0],
             "size": [0.2, 0.2, 0.2], "dynamic": True},
        )
        moved = self.tools.execute(
            "movement_lab", "move",
            {"entity_id": created["entity_id"], "position": [1, 3, 0]},
        )
        self.assertTrue(moved["accepted"])
        observation = self.tools.execute(
            "research_lab", "observe", {"center": [1, 3, 0], "radius": 2},
        )
        self.assertEqual(observation["entity_count"], 1)
        events = self.tools.execute("research_lab", "events", {"limit": 10})
        self.assertTrue(events["chain_valid"])
        self.assertGreaterEqual(len(events["events"]), 2)

    def test_revision_conflict_is_not_silently_accepted(self):
        stale = self.world.revision()
        self.world.create_primitive(
            "first", [0, 0.5, 0], [1, 1, 1],
            actor_id="external", dynamic=False,
        )
        with self.assertRaises(Exception):
            self.tools.execute(
                "world_builder", "create_object",
                {"kind": "stale", "position": [3, 0.5, 0],
                 "size": [1, 1, 1], "dynamic": False},
                expected_revision=stale,
            )

    def test_unknown_tool_action_is_rejected(self):
        with self.assertRaises(ToolboxError):
            self.tools.execute("body_forge", "teleport", {})


if __name__ == "__main__":
    unittest.main()
