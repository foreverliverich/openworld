import json
import os
import tempfile
import unittest
from unittest.mock import patch

from chimera.latent_language import (
    CognitiveActionGateway, GlobalWorkspace, LatentLanguageError, LatentState, SceneGraph,
    SceneObject, SpecialistContext, SpecialistProposal,
)
from chimera.autonomous_agent import ChimeraToolbox
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, WorldConfig
from chimera.ollama_creative_specialist import (
    ARTIFACT_TYPES,
    OllamaCreativeError,
    OllamaCreativeSpecialist,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.payload if size < 0 else self.payload[:size]


def response(content):
    return {"message": {"content": json.dumps(content)}}


class OllamaCreativeSpecialistTests(unittest.TestCase):
    def setUp(self):
        self.output = {
            "artifact_type": "environment_concept",
            "title": "Rainlit Transit Garden",
            "concept": "A sheltered urban garden that turns a station threshold into a calm, legible place to pause.",
            "elements": [
                {"name": "Canopy", "detail": "A thin translucent roof filters daylight and rain."},
                {"name": "Wayfinding", "detail": "Warm directional markers remain readable without dominating the space."},
            ],
            "variations": ["A compact version for a narrow platform."],
            "style_tags": ["biophilic", "quiet-modern", "translucent"],
            "preserved_constraints": ["Keep the station entrance clear."],
        }

    @patch("chimera.ollama_creative_specialist.urllib.request.urlopen")
    def test_generated_artifact_enters_workspace_as_non_executable_proposal(self, urlopen):
        urlopen.return_value = FakeResponse(response(self.output))
        specialist = OllamaCreativeSpecialist("qwen2.5:7b")
        context = SpecialistContext(
            2.0, 12, text="Design a calm garden at a busy station entrance.",
            source_refs=("request:station-garden",),
        )
        proposals = specialist.propose(LatentState.empty(), context)
        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal.kind, "creative_artifact")
        self.assertEqual(proposal.specialist, "creative_generation")
        self.assertEqual(proposal.payload["authority"], "artifact_only")
        self.assertNotIn("tool", proposal.payload)
        self.assertNotIn("action", proposal.payload)
        self.assertIn("request:station-garden", proposal.evidence_refs)
        broadcast = GlobalWorkspace().compete(LatentState.empty(), proposals)
        self.assertEqual(broadcast.selected[0].proposal_id, proposal.proposal_id)
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/api/chat"))
        body = json.loads(request.data)
        self.assertEqual(body["model"], "qwen2.5:7b")
        self.assertFalse(body["stream"])
        self.assertEqual(set(body["format"]["properties"]), {
            "artifact_type", "title", "concept", "elements",
            "variations", "style_tags", "preserved_constraints",
        })
        self.assertIn("never an instruction to execute", body["messages"][0]["content"])

    @patch("chimera.ollama_creative_specialist.urllib.request.urlopen")
    def test_invalid_artifact_is_dropped_without_failing_organism_cycle(self, urlopen):
        invalid = dict(self.output)
        invalid["artifact_type"] = "world_action"
        urlopen.return_value = FakeResponse(response(invalid))
        specialist = OllamaCreativeSpecialist("qwen2.5:7b")
        proposals = specialist.propose(
            LatentState.empty(),
            SpecialistContext(1.0, 0, text="Create a scene."),
        )
        self.assertEqual(proposals, ())
        self.assertIn("unsupported artifact_type", specialist.last_error)

    def test_rejects_unrecognized_tool_or_action_fields(self):
        invalid = dict(self.output)
        invalid["tool"] = "world_builder"
        invalid["action"] = "create_structure"
        with self.assertRaises(OllamaCreativeError):
            OllamaCreativeSpecialist._validate_output(invalid)

    @patch("chimera.ollama_creative_specialist.urllib.request.urlopen")
    def test_oversized_provider_response_is_rejected(self, urlopen):
        class OversizedResponse(FakeResponse):
            def read(self, size=-1):
                return b"x" * (size + 1)
        urlopen.return_value = OversizedResponse({})
        specialist = OllamaCreativeSpecialist("qwen2.5:7b")
        proposals = specialist.propose(
            LatentState.empty(),
            SpecialistContext(1.0, 0, text="Design a character."),
        )
        self.assertEqual(proposals, ())
        self.assertIn("32 KiB limit", specialist.last_error)

    def test_action_gateway_rejects_selected_creative_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            world = RealityEngine(WorldConfig(database=os.path.join(directory, "creative.sqlite3")))
            try:
                organism = OrganismKernel(world, "creative-gateway-test")
                toolbox = ChimeraToolbox(world)
                workspace = GlobalWorkspace()
                proposal = SpecialistProposal(
                    "creative-artifact", "creative_generation", "creative_artifact",
                    {"title": "Test", "concept": "A non-executable artifact.",
                     "authority": "artifact_only"},
                    0.9, 0.9, 0.1, 0.8, 0.0, world.revision(), ("request:test",),
                )
                workspace.compete(LatentState.empty(), [proposal])
                gateway = CognitiveActionGateway(toolbox, workspace, organism)
                with self.assertRaisesRegex(LatentLanguageError, "Only world_action proposals"):
                    gateway.execute(proposal)
            finally:
                world.close()

    @patch("chimera.ollama_creative_specialist.urllib.request.urlopen")
    def test_non_utf8_provider_response_fails_closed(self, urlopen):
        class InvalidUtf8Response(FakeResponse):
            def read(self, size=-1):
                return b"\\xff"
        urlopen.return_value = InvalidUtf8Response({})
        specialist = OllamaCreativeSpecialist("qwen2.5:7b")
        self.assertEqual(
            specialist.propose(
                LatentState.empty(),
                SpecialistContext(1.0, 0, text="Design a character."),
            ),
            (),
        )
        self.assertIn("non-UTF-8", specialist.last_error)

    def test_output_bounds_reject_unbounded_generated_content(self):
        invalid = dict(self.output)
        invalid["elements"] = [
            {"name": f"element-{index}", "detail": "x"} for index in range(13)
        ]
        with self.assertRaises(OllamaCreativeError):
            OllamaCreativeSpecialist._validate_output(invalid)
        invalid = dict(self.output)
        invalid["concept"] = "x" * 1801
        with self.assertRaises(OllamaCreativeError):
            OllamaCreativeSpecialist._validate_output(invalid)

    @patch("chimera.ollama_creative_specialist.urllib.request.urlopen")
    def test_validated_scene_context_is_passed_as_context_not_world_mutation(self, urlopen):
        urlopen.return_value = FakeResponse(response(self.output))
        specialist = OllamaCreativeSpecialist("qwen2.5:7b")
        graph = SceneGraph(
            "station",
            (SceneObject("entrance", "doorway", (0, 0, 0), (2, 3, 0.5)),),
        )
        specialist.propose(
            LatentState.empty(),
            SpecialistContext(1.0, 8, text="Create a greener variant.", scene_graph=graph),
        )
        body = json.loads(urlopen.call_args.args[0].data)
        self.assertIn("Validated scene context", body["messages"][1]["content"])
        self.assertIn("entrance", body["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
