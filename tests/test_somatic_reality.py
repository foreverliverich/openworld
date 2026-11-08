import tempfile
import unittest
from pathlib import Path

from chimera.reality_engine import RealityEngine, RevisionConflict, WorldConfig


def morph(label, script):
    return {
        "label": label,
        "persona": "A living test organism",
        "dialogue": f"I am becoming {label}.",
        "critique": "SDF morphology test package.",
        "sdfScript": script,
        "color": [0.4, 0.3, 0.2],
        "material": {"roughness": 0.7, "metallic": 0.0, "sssIntensity": 0.8},
    }


class SomaticRealityEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp.name) / "somatic.sqlite3")
        self.world = RealityEngine(WorldConfig(database=self.database))

    def tearDown(self):
        self.world.close()
        self.temp.cleanup()

    def test_sdf_pair_is_committed_and_persisted(self):
        initial_revision = self.world.revision()
        first = morph("Wolf", "vec2 map_object(vec3 p) { return vec2(length(p)-1.0, 1.0); }")
        result = self.world.apply_somatic_morphology(
            first, actor_id="test", expected_revision=initial_revision
        )
        self.assertEqual(result.revision, initial_revision + 1)
        state = self.world.somatic_morphology()
        self.assertEqual(state["label"], "Wolf")
        self.assertEqual(state["sdfScript"], first["sdfScript"])
        self.assertGreaterEqual(state["evolutionProgress"], 0.0)
        self.assertLessEqual(state["evolutionProgress"], 1.0)
        self.assertIn("sdHumanoidBase", state["prevSdfScript"])
        self.assertTrue(self.world.verify_event_chain())

    def test_next_morph_preserves_previous_target(self):
        a = morph("Wolf", "vec2 map_object(vec3 p) { return vec2(length(p)-1.0, 1.0); }")
        b = morph("Dragon", "vec2 map_object(vec3 p) { return vec2(length(p)-0.8, 5.0); }")
        self.world.apply_somatic_morphology(a, actor_id="test")
        self.world.apply_somatic_morphology(b, actor_id="test")
        state = self.world.somatic_morphology()
        self.assertEqual(state["prevSdfScript"], a["sdfScript"])
        self.assertEqual(state["sdfScript"], b["sdfScript"])
        self.assertEqual(state["iteration"], 2)

    def test_stale_revision_does_not_commit_morphology(self):
        revision = self.world.revision()
        package = morph("Wolf", "vec2 map_object(vec3 p) { return vec2(length(p)-1.0, 1.0); }")
        self.world.apply_somatic_morphology(package, actor_id="test")
        with self.assertRaises(RevisionConflict):
            self.world.apply_somatic_morphology(
                package, actor_id="test", expected_revision=revision
            )
        self.assertEqual(self.world.somatic_morphology()["iteration"], 1)
        self.assertTrue(self.world.verify_event_chain())

    def test_somatic_state_survives_database_reopen(self):
        first_script = "vec2 map_object(vec3 p) { return vec2(length(p)-1.0, 1.0); }"
        second_script = "vec2 map_object(vec3 p) { return vec2(length(p)-0.8, 5.0); }"
        first = morph("Wolf", first_script)
        second = morph("Dragon", second_script)
        self.world.apply_somatic_morphology(first, actor_id="test")
        self.world.apply_somatic_morphology(second, actor_id="test")
        self.assertTrue(self.world.verify_event_chain())

        self.world.close()
        self.world = RealityEngine(WorldConfig(database=self.database))
        restored = self.world.somatic_morphology()

        self.assertEqual(restored["label"], "Dragon")
        self.assertEqual(restored["prevSdfScript"], first_script)
        self.assertEqual(restored["sdfScript"], second_script)
        self.assertEqual(restored["iteration"], 2)
        self.assertTrue(self.world.verify_event_chain())

if __name__ == "__main__":
    unittest.main()
