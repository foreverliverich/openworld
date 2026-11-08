"""Local Ollama-backed reasoning co-agent for the Latent Language workspace.

The model can classify intent and summarize grounded user text. It cannot emit
world actions, tools, code, coordinates, or arbitrary state mutations. Its output
is untrusted JSON, validated before it becomes a low-authority workspace proposal.
"""
from __future__ import annotations

import hashlib
import json
import math
import urllib.error
import urllib.request
from typing import Any, Sequence

from .latent_language import (
    LatentState, SpecialistContext, SpecialistProposal,
)

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
INTENTS = {"create", "inspect", "move", "explain", "converse", "unknown"}
MAX_TEXT_CHARS = 4000
MAX_SUMMARY_CHARS = 500
MAX_NEXT_STEP_CHARS = 200
MAX_ENTITIES = 12
MAX_ENTITY_CHARS = 80


class OllamaSpecialistError(RuntimeError):
    """Local model inference or its output failed validation."""


class OllamaReasoningSpecialist:
    """A bounded local-language co-agent; never an action executor."""

    name = "ollama_reasoning"

    def __init__(
        self, model: str, *, base_url: str = DEFAULT_OLLAMA_URL,
        timeout: float = 30.0, temperature: float = 0.1,
    ) -> None:
        if not isinstance(model, str) or not model.strip() or len(model) > 120:
            raise ValueError("A non-empty Ollama model name is required")
        if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
            raise ValueError("Ollama base_url must be an HTTP(S) URL")
        if not math.isfinite(timeout) or not 0.1 <= timeout <= 180:
            raise ValueError("Ollama timeout must be between 0.1 and 180 seconds")
        if not math.isfinite(temperature) or not 0 <= temperature <= 0.5:
            raise ValueError("Ollama temperature must be between 0 and 0.5")
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.temperature = float(temperature)

    @staticmethod
    def _validate_output(value: Any, original_text: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise OllamaSpecialistError("Ollama output must be a JSON object")
        intent = value.get("intent")
        summary = value.get("summary")
        next_step = value.get("next_step", "")
        entities = value.get("entities", [])
        evidence = value.get("evidence", "")
        if intent not in INTENTS:
            raise OllamaSpecialistError("Ollama returned an unsupported intent")
        if not isinstance(summary, str) or not summary.strip() or len(summary) > MAX_SUMMARY_CHARS:
            raise OllamaSpecialistError("Ollama summary is empty or too long")
        if not isinstance(next_step, str) or len(next_step) > MAX_NEXT_STEP_CHARS:
            raise OllamaSpecialistError("Ollama next_step is invalid or too long")
        if not isinstance(entities, list) or len(entities) > MAX_ENTITIES:
            raise OllamaSpecialistError("Ollama entities must be a list of at most 12 items")
        if any(not isinstance(item, str) or not item.strip() or len(item) > MAX_ENTITY_CHARS
               for item in entities):
            raise OllamaSpecialistError("Ollama entity labels must be short non-empty strings")
        if not isinstance(evidence, str) or len(evidence) > 240:
            raise OllamaSpecialistError("Ollama evidence must be a string of at most 240 characters")
        if evidence and evidence not in original_text:
            raise OllamaSpecialistError("Ollama evidence must be an exact quote from the supplied user text")
        return {
            "intent": intent,
            "summary": summary.strip(),
            "next_step": next_step.strip(),
            "entities": [item.strip() for item in entities],
            "evidence": evidence,
            "model": "ollama:" + "validated",
        }

    def _infer(self, text: str) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS:
            raise OllamaSpecialistError(f"Reasoning input must contain 1..{MAX_TEXT_CHARS} characters")
        schema = {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": sorted(INTENTS)},
                "summary": {"type": "string"},
                "next_step": {"type": "string"},
                "entities": {"type": "array", "items": {"type": "string"}},
                "evidence": {"type": "string"},
            },
            "required": ["intent", "summary", "next_step", "entities", "evidence"],
        }
        system = (
            "You are one specialist in a multi-agent embodied AI workspace. "
            "Analyze only the supplied user text. Return JSON matching the schema. "
            "Use intent=create only for explicit creation/build requests; inspect for "
            "analysis/observation; move for navigation/motion; explain for questions "
            "seeking explanation; converse for ordinary conversation; unknown if unclear. "
            "The summary must be a concise neutral paraphrase. next_step is a suggested "
            "information-gathering step, never an executable command. entities are explicit "
            "named objects or concepts in the text. evidence must be an exact substring "
            "copied from the user text, or empty. Never invent facts. Never return tools, "
            "actions, code, shell commands, coordinates, or claims of authority."
        )
        body = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            "options": {"temperature": self.temperature},
        }
        request = urllib.request.Request(
            self.base_url + "/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            raise OllamaSpecialistError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OllamaSpecialistError(f"Cannot reach local Ollama service: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OllamaSpecialistError("Ollama returned invalid HTTP JSON") from exc
        try:
            raw = result["message"]["content"]
            parsed = json.loads(raw)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise OllamaSpecialistError("Ollama did not return a valid structured message") from exc
        return self._validate_output(parsed, text)

    def propose(
        self, state: LatentState, context: SpecialistContext
    ) -> Sequence[SpecialistProposal]:
        if not context.text.strip():
            return ()
        result = self._infer(context.text)
        digest = hashlib.sha256(context.text.encode("utf-8")).hexdigest()[:20]
        identity = json.dumps(
            {"text": context.text, "model": self.model, "result": result},
            sort_keys=True, separators=(",", ":"),
        )
        proposal_id = "ollama-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        evidence_refs = tuple(context.source_refs) + (f"user-text-sha256:{digest}",)
        payload = {
            **result,
            "provider": "ollama",
            "model": self.model,
            "authority": "advisory_only",
        }
        return (SpecialistProposal(
            proposal_id, self.name, "cognitive_reasoning", payload,
            0.55, 0.45, 0.10, 0.10, 0.0,
            context.world_revision, evidence_refs,
            conflict_key="reasoning:" + digest,
        ),)
