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
from chimera.latent_language import (
    EncoderRegistry, LatentLanguageCoordinator, SceneGraph, SceneObject,
)


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


    def test_cognition_endpoint_is_explicitly_disabled_without_model_runtime(self):
        status, result = self.request("/api/cognition", {"text": "hello"})
        self.assertEqual(status, 503)
        self.assertEqual(result["error"], "service_unavailable")

    def test_chimera_application_queues_and_executes_workspace_selected_cognition(self):
        class FixedEncoder:
            encoder_id = "http-test-text"
            def encode(self, payload):
                return (0.2,) * 768

        registry = EncoderRegistry()
        registry.register("text", FixedEncoder())
        coordinator = LatentLanguageCoordinator(registry)
        app = ChimeraApplication(
            os.path.join(self.tmp.name, "cognition-world.sqlite3"),
            cognition=coordinator,
        )
        try:
            queued = app.queue_cognition({
                "text": "Build a platform scene",
                "scene_graph": {
                    "scene_id": "http-scene",
                    "objects": [{
                        "object_id": "platform", "kind": "cube",
                        "position": [20, 0.5, 20], "size": [1, 1, 1],
                        "dynamic": False,
                    }],
                },
            })
            self.assertTrue(queued["queued"])
            frame = app.tick()["frames"][0]
            self.assertIsNotNone(frame["cognition_result"])
            spatial = next(
                proposal for proposal in coordinator.workspace.latest.selected
                if proposal.specialist == "spatial" and proposal.kind == "world_action"
            )
            result = app.execute_cognitive_action({"proposal_id": spatial.proposal_id})
            self.assertTrue(result["result"]["accepted"])
            self.assertTrue(result["result"]["resource_charge"]["charged_before_action"])
            self.assertTrue(app.world.verify_event_chain())
            self.assertGreater(app.state()["cognition"]["workspace_tick"], 0)
        finally:
            app.close()


    def test_semantic_scene_interpreter_is_opt_in(self):
        class FixedEncoder:
            encoder_id = "http-test-text"
            def encode(self, payload):
                return (0.2,) * 768

        registry = EncoderRegistry()
        registry.register("text", FixedEncoder())
        app = ChimeraApplication(
            os.path.join(self.tmp.name, "scene-disabled.sqlite3"),
            cognition=LatentLanguageCoordinator(registry),
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "scene interpretation is disabled"):
                app.queue_cognition({
                    "text": "Build a platform", "interpret_scene": True,
                })
        finally:
            app.close()

    def test_interpreted_scene_enters_workspace_and_world_action_gateway(self):
        class FixedEncoder:
            encoder_id = "http-test-text"
            def encode(self, payload):
                return (0.2,) * 768

        class FixedSceneInterpreter:
            def __init__(self):
                self.calls = []
            def interpret(self, prompt, *, scene_id):
                self.calls.append((prompt, scene_id))
                return SceneGraph(
                    scene_id,
                    (SceneObject(
                        "platform", "box", (20, 0.5, 20), (2, 1, 2),
                        "stone", 20.0, False,
                    ),),
                )

        registry = EncoderRegistry()
        registry.register("text", FixedEncoder())
        coordinator = LatentLanguageCoordinator(registry)
        interpreter = FixedSceneInterpreter()
        app = ChimeraApplication(
            os.path.join(self.tmp.name, "interpreted-scene.sqlite3"),
            cognition=coordinator,
            scene_interpreter=interpreter,
        )
        try:
            queued = app.queue_cognition({
                "request_id": "scene-parse-1",
                "text": "Build a stone platform at the far corner",
                "interpret_scene": True,
            })
            self.assertTrue(queued["queued"])
            self.assertEqual(interpreter.calls[0][0], "Build a stone platform at the far corner")
            frame = app.tick()["frames"][0]
            self.assertIsNotNone(frame["cognition_result"])
            spatial = next(
                proposal for proposal in coordinator.workspace.latest.selected
                if proposal.specialist == "spatial" and proposal.kind == "world_action"
            )
            committed = app.execute_cognitive_action({"proposal_id": spatial.proposal_id})
            self.assertTrue(committed["result"]["accepted"])
            self.assertTrue(any(
                entity["kind"] == "box" for entity in committed["state"]["entities"]
            ))
            self.assertTrue(app.world.verify_event_chain())
        finally:
            app.close()


    def test_image_grounded_scene_interpretation_flows_through_workspace_gateway(self):
        import base64

        class FixedEncoder:
            encoder_id = "http-test-image"
            def encode(self, payload):
                self.payload = payload
                return (0.1,) * 512

        class FixedTextEncoder:
            encoder_id = "http-test-text"
            def encode(self, payload):
                return (0.2,) * 768

        class FixedSceneInterpreter:
            def __init__(self):
                self.calls = []
            def interpret(self, prompt, *, scene_id, image_base64=None):
                self.calls.append((prompt, scene_id, image_base64))
                return SceneGraph(
                    scene_id,
                    (SceneObject(
                        "visible-table", "box", (20, 0.5, 20), (1.2, 1, 0.8),
                        "wood", 8.0, False,
                    ),),
                )

        png = base64.b64encode(b"\x89PNG\r\n\x1a\nvalid-image-bytes").decode()
        image_uri = "data:image/png;base64," + png
        registry = EncoderRegistry()
        registry.register("text", FixedTextEncoder())
        registry.register("image", FixedEncoder())
        coordinator = LatentLanguageCoordinator(registry)
        interpreter = FixedSceneInterpreter()
        app = ChimeraApplication(
            os.path.join(self.tmp.name, "visual-scene.sqlite3"),
            cognition=coordinator,
            scene_interpreter=interpreter,
        )
        try:
            queued = app.queue_cognition({
                "request_id": "visual-scene-1",
                "text": "Build the visible table in the scene",
                "observations": [{
                    "modality": "image",
                    "image_base64": image_uri,
                    "source_id": "camera-frame-1",
                }],
                "interpret_scene": True,
            })
            self.assertTrue(queued["queued"])
            self.assertEqual(interpreter.calls[0][0], "Build the visible table in the scene")
            self.assertEqual(interpreter.calls[0][2], image_uri)
            app.tick()
            spatial = next(
                proposal for proposal in coordinator.workspace.latest.selected
                if proposal.specialist == "spatial" and proposal.kind == "world_action"
            )
            result = app.execute_cognitive_action({"proposal_id": spatial.proposal_id})
            self.assertTrue(result["result"]["accepted"])
            self.assertTrue(any(
                entity["kind"] == "box" for entity in result["state"]["entities"]
            ))
            self.assertTrue(app.world.verify_event_chain())
        finally:
            app.close()

    def test_health_and_static_client_are_served(self):
        status, health = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(health["ok"])
        with urlopen(self.base + "/", timeout=3) as response:
            html = response.read().decode()
        self.assertIn("PROJECT", html)
        self.assertIn("CHIMERA", html)
        self.assertIn("/api/state", html)
        self.assertIn("bodyForm", html)
        self.assertIn("/api/body/pose", html)
        self.assertIn("/api/body/actuate", html)
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



    def test_body_pose_endpoint_returns_authoritative_articulated_segments(self):
        status, body = self.request("/api/body/pose")
        self.assertEqual(status, 200)
        self.assertEqual(body["skeleton_version"], "human-3d-1")
        self.assertEqual(len(body["segments"]), 16)
        self.assertEqual(len(body["joints"]), 15)
        self.assertEqual(body["world_revision"], self.app.world.revision())

    def test_body_actuation_commits_joint_motion_and_physiological_feedback(self):
        _, before = self.request("/api/body/pose")
        _, before_state = self.request("/api/state")
        status, result = self.request("/api/body/actuate", {
            "expected_revision": before["world_revision"],
            "motor_commands": {"thigh_l": 0.55, "shin_l": -0.3},
            "root_acceleration": [0.6, 0.0, 0.0],
        })
        self.assertEqual(status, 200)
        self.assertEqual(result["result"]["revision"], before["world_revision"] + 1)
        joints = {joint["name"]: joint for joint in result["body"]["joints"]}
        self.assertGreater(joints["thigh_l"]["angle"], 0.0)
        self.assertGreater(joints["shin_l"]["activation"], 0.0)
        self.assertGreater(result["body"]["root_position"][0], before["root_position"][0])
        organism = result["state"]["organism"]["organism"]
        before_organism = before_state["organism"]["organism"]
        self.assertGreater(organism["resources"]["cumulative_work_units"], 0.0)
        self.assertGreater(organism["sensorimotor"]["proprioceptive_error"], 0.0)
        self.assertLess(organism["body"]["energy"], before_organism["body"]["energy"])
        self.assertTrue(self.app.world.verify_event_chain())

    def test_body_actuation_accepts_three_axis_joint_targets(self):
        _, before = self.request("/api/body/pose")
        status, result = self.request("/api/body/actuate", {
            "expected_revision": before["world_revision"],
            "motor_commands": {"thigh_l": [0.35, 0.4, -0.25]},
        })
        self.assertEqual(status, 200)
        hip = {joint["name"]: joint for joint in result["body"]["joints"]}["thigh_l"]
        self.assertGreater(abs(hip["rotation_xyz"][1]), 0.0)
        self.assertGreater(abs(hip["rotation_xyz"][2]), 0.0)
        self.assertGreater(abs(hip["tendon_extension_xyz"][1]), 0.0)
        self.assertEqual(len(result["body"]["segments"][0]["orientation"]), 4)

    def test_malformed_three_axis_motor_target_is_rejected(self):
        revision = self.app.world.revision()
        status, result = self.request("/api/body/actuate", {
            "expected_revision": revision,
            "motor_commands": {"thigh_l": [0.2, 0.3]},
        })
        self.assertEqual(status, 400)
        self.assertEqual(self.app.world.revision(), revision)

    def test_invalid_body_command_is_rejected_without_state_mutation(self):
        revision = self.app.world.revision()
        status, result = self.request("/api/body/actuate", {
            "expected_revision": revision,
            "motor_commands": {"tail": 0.5},
        })
        self.assertEqual(status, 400)
        self.assertEqual(self.app.world.revision(), revision)
        self.assertEqual(result["error"], "action_rejected")

    def test_stale_body_actuation_is_rejected_without_mutation(self):
        revision = self.app.world.revision()
        self.request("/api/tick", {"ticks": 1})
        current = self.app.world.revision()
        status, result = self.request("/api/body/actuate", {
            "expected_revision": revision,
            "motor_commands": {"thigh_l": 0.5},
        })
        self.assertEqual(status, 409)
        self.assertEqual(result["current_revision"], current)

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
