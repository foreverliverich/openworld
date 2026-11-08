import base64
import json
import unittest
from unittest.mock import patch

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

    def test_image_part_accepts_png_and_rejects_mime_spoofing(self):
        png = base64.b64encode(b"\\x89PNG\\r\\n\\x1a\\nvalid-image-bytes").decode()
        part = GeminiSceneInterpreter._image_part("data:image/png;base64," + png)
        self.assertEqual(part["inlineData"]["mimeType"], "image/png")
        self.assertEqual(part["inlineData"]["data"], png)
        with self.assertRaises(SceneInterpretationError):
            GeminiSceneInterpreter._image_part("data:image/jpeg;base64," + png)
        with self.assertRaises(SceneInterpretationError):
            GeminiSceneInterpreter._image_part("data:image/png;base64,not-valid-base64!")

    @patch("chimera.scene_interpreter.urllib.request.urlopen")
    def test_image_and_text_are_sent_together_to_gemini(self, urlopen):
        png_bytes = b"\\x89PNG\\r\\n\\x1a\\nvalid-image-bytes"
        png = base64.b64encode(png_bytes).decode()
        graph_payload = {
            "scene_id": "visual-test",
            "objects": [{
                "object_id": "table", "kind": "box",
                "position": [0, 0.5, 0], "size": [1.2, 1, 0.8],
                "material": "wood", "mass": 8, "dynamic": False,
            }],
            "relations": [],
        }
        response = {
            "candidates": [{"content": {"parts": [{"text": json.dumps(graph_payload)}]}}],
        }

        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return json.dumps(response).encode()

        urlopen.return_value = FakeResponse()
        interpreter = GeminiSceneInterpreter(api_key="test-key")
        graph = interpreter.interpret(
            "Describe the visible furniture", scene_id="visual-test",
            image_base64="data:image/png;base64," + png,
        )
        self.assertEqual(graph.objects[0].object_id, "table")
        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        parts = body["contents"][0]["parts"]
        self.assertEqual(parts[0]["inlineData"]["mimeType"], "image/png")
        self.assertEqual(parts[1]["text"], "Describe the visible furniture")

    def test_image_only_interpretation_requires_no_text_prompt(self):
        png = base64.b64encode(b"\\x89PNG\\r\\n\\x1a\\nvalid-image-bytes").decode()
        with patch("chimera.scene_interpreter.urllib.request.urlopen") as urlopen:
            payload = {
                "scene_id": "image-only",
                "objects": [{
                    "object_id": "chair", "kind": "box",
                    "position": [0, 0.5, 0], "size": [0.5, 1, 0.5],
                    "material": "wood", "mass": 3, "dynamic": False,
                }],
                "relations": [],
            }

            class FakeResponse:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def read(self):
                    return json.dumps({
                        "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
                    }).encode()

            urlopen.return_value = FakeResponse()
            graph = GeminiSceneInterpreter(api_key="test-key").interpret(
                "", scene_id="image-only", image_base64="data:image/png;base64," + png,
            )
            self.assertEqual(graph.objects[0].object_id, "chair")
            body = json.loads(urlopen.call_args.args[0].data)
            self.assertIn("visible physical objects", body["contents"][0]["parts"][0]["text"])

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
