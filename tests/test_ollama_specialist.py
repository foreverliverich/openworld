import json
import unittest
from unittest.mock import patch

from chimera.latent_language import (
    EncoderRegistry, LatentLanguageCoordinator, LatentState, SpecialistContext,
)
from chimera.ollama_specialist import (
    OllamaReasoningSpecialist, OllamaSpecialistError,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.payload


def response(content):
    return {"message": {"content": json.dumps(content)}}


class OllamaReasoningSpecialistTests(unittest.TestCase):
    def setUp(self):
        self.text = "Build a stone platform beside the entrance."
        self.output = {
            "intent": "create",
            "summary": "The user requests a stone platform near an entrance.",
            "next_step": "Clarify the desired platform dimensions.",
            "entities": ["stone platform", "entrance"],
            "evidence": "Build a stone platform",
        }

    @patch("chimera.ollama_specialist.urllib.request.urlopen")
    def test_valid_output_becomes_advisory_workspace_proposal(self, urlopen):
        urlopen.return_value = FakeResponse(response(self.output))
        specialist = OllamaReasoningSpecialist("qwen2.5:3b")
        context = SpecialistContext(
            1.0, 4, text=self.text, source_refs=("request:42",),
        )
        proposals = specialist.propose(LatentState.empty(), context)
        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal.kind, "cognitive_reasoning")
        self.assertEqual(proposal.payload["intent"], "create")
        self.assertEqual(proposal.payload["authority"], "advisory_only")
        self.assertNotEqual(proposal.kind, "world_action")
        self.assertIn("request:42", proposal.evidence_refs)
        self.assertTrue(any(ref.startswith("user-text-sha256:") for ref in proposal.evidence_refs))
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/api/chat"))
        body = json.loads(request.data)
        self.assertEqual(body["model"], "qwen2.5:3b")
        self.assertFalse(body["stream"])
        self.assertEqual(body["format"]["type"], "object")

    @patch("chimera.ollama_specialist.urllib.request.urlopen")
    def test_coagent_runs_inside_real_global_workspace_competition(self, urlopen):
        urlopen.return_value = FakeResponse(response(self.output))
        specialist = OllamaReasoningSpecialist("qwen2.5:3b")
        coordinator = LatentLanguageCoordinator(
            EncoderRegistry(), specialists=(specialist,),
        )
        result = coordinator.cycle(
            [], SpecialistContext(1.0, 0, text=self.text, source_refs=("prompt:1",)),
        )
        self.assertEqual(len(result.broadcast.selected), 1)
        self.assertEqual(result.broadcast.selected[0].specialist, "ollama_reasoning")
        self.assertEqual(result.broadcast.selected[0].kind, "cognitive_reasoning")

    @patch("chimera.ollama_specialist.urllib.request.urlopen")
    def test_rejects_unquoted_evidence_and_never_trusts_model_claims(self, urlopen):
        invalid = dict(self.output, evidence="the user wants a weapon")
        urlopen.return_value = FakeResponse(response(invalid))
        specialist = OllamaReasoningSpecialist("qwen2.5:3b")
        with self.assertRaises(OllamaSpecialistError):
            specialist.propose(
                LatentState.empty(), SpecialistContext(1.0, 0, text=self.text),
            )

    @patch("chimera.ollama_specialist.urllib.request.urlopen")
    def test_rejects_attempt_to_return_action_or_unknown_intent(self, urlopen):
        invalid = dict(self.output, intent="world_action")
        urlopen.return_value = FakeResponse(response(invalid))
        specialist = OllamaReasoningSpecialist("qwen2.5:3b")
        with self.assertRaises(OllamaSpecialistError):
            specialist.propose(
                LatentState.empty(), SpecialistContext(1.0, 0, text=self.text),
            )

    @patch("chimera.ollama_specialist.urllib.request.urlopen")
    def test_empty_text_does_not_call_local_model(self, urlopen):
        specialist = OllamaReasoningSpecialist("qwen2.5:3b")
        proposals = specialist.propose(
            LatentState.empty(), SpecialistContext(1.0, 0, text=""),
        )
        self.assertEqual(proposals, ())
        urlopen.assert_not_called()

    def test_constructor_rejects_unsafe_configuration(self):
        with self.assertRaises(ValueError):
            OllamaReasoningSpecialist("")
        with self.assertRaises(ValueError):
            OllamaReasoningSpecialist("model", base_url="file:///etc/passwd")
        with self.assertRaises(ValueError):
            OllamaReasoningSpecialist("model", temperature=1.0)


if __name__ == "__main__":
    unittest.main()
