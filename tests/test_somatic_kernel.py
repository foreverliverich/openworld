import json
import os
import unittest
from unittest.mock import patch

from chimera.somatic_kernel import _validate_package, generate_morph_package, refine_morph_package


def package():
    return {
        "label": "Wolf",
        "persona": "An alert forest predator",
        "dialogue": "My body is changing.",
        "critique": "Quadruped anatomy with a muzzle and digitigrade limbs.",
        "sdfScript": "vec2 map_object(vec3 p) { return vec2(length(p)-1.0, 1.0); }",
        "color": [0.42, 0.31, 0.24],
        "material": {"roughness": 0.72, "metallic": 0.0, "sssIntensity": 0.8},
    }


class SomaticKernelValidationTests(unittest.TestCase):
    def test_accepts_complete_package(self):
        result = _validate_package(package())
        self.assertEqual(result["label"], "Wolf")

    def test_rejects_missing_sdf(self):
        value = package()
        value["sdfScript"] = ""
        with self.assertRaises(ValueError):
            _validate_package(value)

    def test_rejects_wrong_function_signature(self):
        value = package()
        value["sdfScript"] = "float map_object(vec3 p) { return length(p); }"
        with self.assertRaises(ValueError):
            _validate_package(value)

    def test_rejects_shader_entrypoint(self):
        value = package()
        value["sdfScript"] = "vec2 map_object(vec3 p) { void main() {} return vec2(1.); }"
        with self.assertRaises(ValueError):
            _validate_package(value)

    def test_rejects_non_normalized_color(self):
        value = package()
        value["color"] = [1.2, 0.0, 0.0]
        with self.assertRaises(ValueError):
            _validate_package(value)

    def test_rejects_invalid_material(self):
        value = package()
        value["material"]["roughness"] = 2.0
        with self.assertRaises(ValueError):
            _validate_package(value)

    def test_missing_api_key_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Set GEMINI_API_KEY"):
                generate_morph_package("become a wolf")

    def test_refinement_enforces_ten_iteration_cap(self):
        with self.assertRaises(ValueError):
            refine_morph_package({"sdfScript": package()["sdfScript"]}, 11)

    def test_refinement_rejects_invalid_image_snapshot(self):
        with self.assertRaises(ValueError):
            refine_morph_package({"sdfScript": package()["sdfScript"]}, 1, "data:text/html;base64,PHNjcmlwdD4=")

    def test_refinement_sends_multimodal_snapshot_and_validates_result(self):
        body = {"candidates": [{"content": {"parts": [{"text": json.dumps(package())}]}}]}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(body).encode()
        def fake_open(request, timeout):
            sent = json.loads(request.data)
            self.assertEqual(sent["contents"][0]["parts"][1]["inlineData"]["mimeType"], "image/png")
            return Response()
        snapshot = "data:image/png;base64,aGVsbG8="
        state = {"sdfScript": package()["sdfScript"], "label": "Wolf"}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("chimera.somatic_kernel.urllib.request.urlopen", side_effect=fake_open):
                result = refine_morph_package(state, 1, snapshot)
        self.assertEqual(result["label"], "Wolf")

    def test_sends_prompt_to_gemini_and_validates_response(self):
        body = {"candidates": [{"content": {"parts": [{"text": json.dumps(package())}]}}]}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(body).encode()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("chimera.somatic_kernel.urllib.request.urlopen", return_value=Response()):
                result = generate_morph_package("become a wolf", "Genesis")
        self.assertEqual(result["label"], "Wolf")

if __name__ == "__main__":
    unittest.main()
