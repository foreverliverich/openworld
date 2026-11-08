import unittest

from chimera.scene_interpreter import GeminiSceneInterpreter, SceneInterpretationError


class SceneInterpreterValidationTests(unittest.TestCase):
    def test_valid_scene_graph_is_typed_and_compilable(self):
        graph = GeminiSceneInterpreter._parse_graph({
            "scene_id": "test-platform",
            "objects": [{
                "object_id": "platform", "kind": "box",
                "position": [0, 0.5, 0], "size": [2, 1, 2],
                "material": "stone", "mass": 20, "dynamic": False,
            }],
            "relations": [],
        }, "fallback")
        self.assertEqual(graph.scene_id, "test-platform")
        blueprint = graph.to_blueprint()
        self.assertEqual(blueprint["parts"][0]["kind"], "box")
        self.assertEqual(blueprint["parts"][0]["position"], [0.0, 0.5, 0.0])

    def test_static_object_must_be_grounded_or_supported(self):
        with self.assertRaises(SceneInterpretationError):
            GeminiSceneInterpreter._parse_graph({
                "objects": [{
                    "object_id": "floating", "kind": "box",
                    "position": [0, 4, 0], "size": [1, 1, 1],
                    "material": "stone", "mass": 1, "dynamic": False,
                }],
                "relations": [],
            }, "fallback")

    def test_overlapping_scene_is_rejected_before_world_mutation(self):
        with self.assertRaises(SceneInterpretationError):
            GeminiSceneInterpreter._parse_graph({
                "objects": [
                    {"object_id": "a", "kind": "box", "position": [0, 0.5, 0],
                     "size": [1, 1, 1], "material": "stone", "mass": 1, "dynamic": False},
                    {"object_id": "b", "kind": "box", "position": [0.2, 0.5, 0],
                     "size": [1, 1, 1], "material": "stone", "mass": 1, "dynamic": True},
                ],
                "relations": [],
            }, "fallback")

    def test_relation_cycle_and_unsupported_containment_are_rejected(self):
        base = {
            "objects": [
                {"object_id": "a", "kind": "box", "position": [0, 0.5, 0],
                 "size": [1, 1, 1], "material": "stone", "mass": 1, "dynamic": False},
                {"object_id": "b", "kind": "box", "position": [2, 0.5, 0],
                 "size": [1, 1, 1], "material": "stone", "mass": 1, "dynamic": False},
            ],
        }
        with self.assertRaises(SceneInterpretationError):
            GeminiSceneInterpreter._parse_graph({
                **base, "relations": [
                    {"relation": "on_top", "subject": "a", "object": "b", "gap": 0.05},
                    {"relation": "on_top", "subject": "b", "object": "a", "gap": 0.05},
                ],
            }, "cycle")
        with self.assertRaises(SceneInterpretationError):
            GeminiSceneInterpreter._parse_graph({
                **base, "relations": [
                    {"relation": "inside", "subject": "a", "object": "b", "gap": 0.05},
                ],
            }, "containment")

    def test_scene_identifier_is_safe_for_world_metadata(self):
        with self.assertRaises(SceneInterpretationError):
            GeminiSceneInterpreter._parse_graph({
                "scene_id": "../escape",
                "objects": [{
                    "object_id": "ground", "kind": "box",
                    "position": [0, 0.5, 0], "size": [1, 1, 1],
                    "material": "stone", "mass": 1, "dynamic": False,
                }],
            }, "fallback")

    def test_object_count_and_extent_are_bounded(self):
        with self.assertRaises(SceneInterpretationError):
            GeminiSceneInterpreter._parse_graph({
                "objects": [{
                    "object_id": "far", "kind": "box", "position": [500, 0.5, 0],
                    "size": [1, 1, 1], "material": "stone", "mass": 1, "dynamic": False,
                }],
            }, "bounds")
        with self.assertRaises(SceneInterpretationError):
            GeminiSceneInterpreter._parse_graph({
                "objects": [
                    {"object_id": f"o{i}", "kind": "box", "position": [i * 2, 0.5, 0],
                     "size": [1, 1, 1], "material": "stone", "mass": 1, "dynamic": True}
                    for i in range(33)
                ],
            }, "capacity")


if __name__ == "__main__":
    unittest.main()
