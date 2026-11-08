"""Integration tests for the local browser/API application."""

import json
import os
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from chimera.http_server import ChimeraApplication, ChimeraRequestHandler


class BrowserAPIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = ChimeraApplication(os.path.join(self.tmp.name, "world.sqlite3"))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ChimeraRequestHandler)
        self.server.app = self.app
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.app.close()
        self.tmp.cleanup()

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(self.base + path, data=data,
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_health_and_static_client_are_served(self):
        status, health = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(health["ok"])
        with urlopen(self.base + "/", timeout=3) as response:
            html = response.read().decode()
        self.assertIn("PROJECT", html)
        self.assertIn("CHIMERA", html)
        self.assertIn("/api/state", html)
        for tool_name in ("World Builder", "Somatic Core", "Tool Fabricator", "Life Generator", "Movement Lab", "Research Lab"):
            self.assertIn(tool_name, html)

    def test_state_is_read_from_one_runtime_and_world(self):
        status, state = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["world_revision"], state["organism"]["world_revision"])
        self.assertEqual(len(state["toolbox"]), 6)
        self.assertTrue(state["event_chain_valid"])

    def test_tool_action_commits_and_is_visible_in_state(self):
        _, before = self.request("/api/state")
        status, result = self.request("/api/tool", {
            "tool": "world_builder", "action": "create_object",
            "expected_revision": before["world_revision"],
            "arguments": {
                "kind": "api_test_block", "position": [2, 0.5, 0],
                "size": [1, 1, 1], "material": "stone", "dynamic": False
            }
        })
        self.assertEqual(status, 200)
        self.assertTrue(result["result"]["accepted"])
        self.assertEqual(result["state"]["world_revision"], before["world_revision"] + 1)
        self.assertTrue(any(e["kind"] == "api_test_block" for e in result["state"]["entities"]))

    def test_stale_tool_revision_is_rejected_without_mutation(self):
        _, before = self.request("/api/state")
        self.request("/api/tick", {"ticks": 1})
        current = self.app.world.revision()
        status, result = self.request("/api/tool", {
            "tool": "world_builder", "action": "create_object",
            "expected_revision": before["world_revision"],
            "arguments": {
                "kind": "stale_block", "position": [3, 0.5, 0],
                "size": [1, 1, 1], "dynamic": False
            }
        })
        self.assertEqual(status, 409)
        self.assertEqual(result["current_revision"], current)
        self.assertFalse(any(e.kind == "stale_block" for e in self.app.world.entities()))

    def test_runtime_tick_advances_world_and_organism(self):
        status, result = self.request("/api/tick", {"ticks": 2})
        self.assertEqual(status, 200)
        self.assertEqual(result["state"]["runtime_tick"], 2)
        self.assertEqual(result["state"]["organism"]["organism"]["tick"], 2)
        self.assertGreater(result["state"]["world_revision"], 0)

    def test_invalid_tick_count_is_rejected(self):
        status, result = self.request("/api/tick", {"ticks": 121})
        self.assertEqual(status, 400)
        self.assertEqual(result["error"], "action_rejected")


    def test_somatic_candidate_generation_does_not_mutate_world(self):
        package = {
            "label": "Wolf", "persona": "Alert", "dialogue": "I am changing.",
            "critique": "Quadruped morphology.", "sdfScript":
                "vec2 map_object(vec3 p) { return vec2(length(p)-1.0, 1.0); }",
            "color": [0.4, 0.3, 0.2],
            "material": {"roughness": 0.7, "metallic": 0.0, "sssIntensity": 0.8},
        }
        revision = self.app.world.revision()
        with patch("chimera.http_server.generate_morph_package", return_value=package):
            status, result = self.request("/api/somatic/morph", {
                "description": "become a wolf", "current_label": "Genesis"
            })
        self.assertEqual(status, 200)
        self.assertEqual(result["package"]["label"], "Wolf")
        self.assertIsNone(self.app.world.somatic_morphology())
        self.assertEqual(self.app.world.revision(), revision)

    def test_somatic_commit_persists_only_validated_package(self):
        package = {
            "label": "Wolf", "persona": "Alert", "dialogue": "I am changing.",
            "critique": "Quadruped morphology.", "sdfScript":
                "vec2 map_object(vec3 p) { return vec2(length(p)-1.0, 1.0); }",
            "color": [0.4, 0.3, 0.2],
            "material": {"roughness": 0.7, "metallic": 0.0, "sssIntensity": 0.8},
        }
        revision = self.app.world.revision()
        status, result = self.request("/api/somatic/commit", {
            "package": package, "expected_revision": revision
        })
        self.assertEqual(status, 200)
        self.assertEqual(result["state"]["label"], "Wolf")
        self.assertEqual(result["state"]["prevSdfScript"].startswith("vec2 map_object"), True)
        self.assertEqual(result["state"]["sdfScript"], package["sdfScript"])
        self.assertEqual(result["state"]["world_revision"], revision + 1)
        self.assertTrue(self.app.world.verify_event_chain())

    def test_invalid_somatic_package_is_not_committed(self):
        revision = self.app.world.revision()
        status, result = self.request("/api/somatic/commit", {
            "package": {"label": "broken"}, "expected_revision": revision
        })
        self.assertEqual(status, 400)
        self.assertIsNone(self.app.world.somatic_morphology())
        self.assertEqual(self.app.world.revision(), revision)

    def test_visual_refinement_returns_candidate_without_mutation(self):
        package = {
            "label": "Wolf", "persona": "Alert", "dialogue": "I am changing.",
            "critique": "Quadruped morphology.", "sdfScript":
                "vec2 map_object(vec3 p) { return vec2(length(p)-1.0, 1.0); }",
            "color": [0.4, 0.3, 0.2],
            "material": {"roughness": 0.7, "metallic": 0.0, "sssIntensity": 0.8},
        }
        self.request("/api/somatic/commit", {
            "package": package, "expected_revision": self.app.world.revision()
        })
        revision = self.app.world.revision()
        with patch("chimera.http_server.refine_morph_package", return_value=package):
            status, result = self.request("/api/somatic/refine", {
                "iteration": 1, "imageSnapshot": "data:image/png;base64,aGVsbG8="
            })
        self.assertEqual(status, 200)
        self.assertEqual(result["package"]["label"], "Wolf")
        self.assertEqual(self.app.world.revision(), revision)



if __name__ == "__main__":
    unittest.main()
