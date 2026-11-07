"""Integration tests for the local browser/API application."""

import json
import os
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

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
        self.assertIn("PROJECT CHIMERA", html)
        self.assertIn("/api/state", html)

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
        self.assertEqual(result["error"], "invalid_request")


if __name__ == "__main__":
    unittest.main()
