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

    def test_rejects_unbounded_shader_loop(self):
        value = package()
        value["sdfScript"] = "vec2 map_object(vec3 p) { while(true) { p.x += 1.0; } return vec2(length(p), 1.0); }"
        with self.assertRaises(ValueError):
            _validate_package(value)

    def test_rejects_non_constant_loop_bound(self):
        value = package()
        value["sdfScript"] = "vec2 map_object(vec3 p) { for(int i=0;i<MAX_STEPS;i++){p.x+=0.0;} return vec2(length(p),1.0); }"
        with self.assertRaises(ValueError):
            _validate_package(value)

    def test_accepts_bounded_shader_loop(self):
        value = package()
        value["sdfScript"] = "vec2 map_object(vec3 p) { for(int i=0;i<5;i++){p.x+=0.001;} return vec2(length(p)-1.0,1.0); }"
        self.assertEqual(_validate_package(value)["label"], "Wolf")

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
        refined = package()
        refined["sdfScript"] = "vec2 map_object(vec3 p) { return vec2(length(p)-0.8, 1.0); }"
        body = {"candidates": [{"content": {"parts": [{"text": json.dumps(refined)}]}}]}
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

    def test_refinement_rejects_unchanged_sdf(self):
        body = {"candidates": [{"content": {"parts": [{"text": json.dumps(package())}]}}]}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(body).encode()
        state = {"sdfScript": package()["sdfScript"], "label": "Wolf"}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("chimera.somatic_kernel.urllib.request.urlopen", return_value=Response()):
                with self.assertRaisesRegex(RuntimeError, "unchanged SDF"):
                    refine_morph_package(state, 1)

    def test_generation_receives_current_sdf_context(self):
        body = {"candidates": [{"content": {"parts": [{"text": json.dumps(package())}]}}]}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(body).encode()
        current_script = "vec2 map_object(vec3 p) { return vec2(length(p)-0.9, 1.0); }"
        def fake_open(request, timeout):
            sent = json.loads(request.data)
            prompt = sent["contents"][0]["parts"][0]["text"]
            self.assertIn(current_script, prompt)
            self.assertIn("preserving identity", prompt)
            return Response()
        context = {"label": "Seed", "sdfScript": current_script, "color": [0.5, 0.4, 0.3]}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("chimera.somatic_kernel.urllib.request.urlopen", side_effect=fake_open):
                result = generate_morph_package("become a wolf", "Seed", context)
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
