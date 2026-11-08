"""Local Ollama creative generation as a bounded, non-executing workspace specialist.

Generated artifacts are proposals only. They cannot invoke tools, mutate ISCE,
construct world geometry, or bypass the revision-checked action gateway.
"""
from __future__ import annotations

import hashlib
import json
import math
import urllib.error
import urllib.request
from typing import Any, Sequence

from .latent_language import LatentState, SpecialistContext, SpecialistProposal

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
MAX_CREATIVE_PROMPT_CHARS = 5000
MAX_RESPONSE_BYTES = 32 * 1024
MAX_TITLE_CHARS = 120
MAX_CONCEPT_CHARS = 1800
MAX_ELEMENTS = 12
MAX_ELEMENT_NAME_CHARS = 80
MAX_ELEMENT_DETAIL_CHARS = 400
MAX_VARIATIONS = 4
MAX_VARIATION_CHARS = 320
MAX_STYLE_TAGS = 8
MAX_STYLE_TAG_CHARS = 40
MAX_CONSTRAINTS = 12
MAX_CONSTRAINT_CHARS = 160
ARTIFACT_TYPES = {
    "character_concept", "environment_concept", "object_concept",
    "story_seed", "visual_direction", "scene_variation",
}


class OllamaCreativeError(RuntimeError):
    """Local creative inference or its generated artifact failed validation."""


class OllamaCreativeSpecialist:
    """Produces bounded original creative briefs, never executable world actions."""

    name = "creative_generation"

    def __init__(
        self, model: str, *, base_url: str = DEFAULT_OLLAMA_URL,
        timeout: float = 45.0, temperature: float = 0.7,
    ) -> None:
        if not isinstance(model, str) or not model.strip() or len(model) > 120:
            raise ValueError("A non-empty Ollama creative model name is required")
        if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
            raise ValueError("Ollama base_url must be an HTTP(S) URL")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0.1 <= timeout <= 180:
            raise ValueError("Ollama creative timeout must be between 0.1 and 180 seconds")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not math.isfinite(temperature) or not 0.2 <= temperature <= 1.2:
            raise ValueError("Ollama creative temperature must be between 0.2 and 1.2")
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.temperature = float(temperature)
        self.last_error: str | None = None

    @staticmethod
    def _bounded_text(value: Any, *, label: str, maximum: int, required: bool = True) -> str:
        if not isinstance(value, str) or (required and not value.strip()) or len(value) > maximum:
            raise OllamaCreativeError(f"{label} must be a {'non-empty ' if required else ''}string up to {maximum} characters")
        return value.strip()

    @classmethod
    def _validate_output(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise OllamaCreativeError("Creative output must be a JSON object")
        required_fields = {
            "artifact_type", "title", "concept", "elements",
            "variations", "style_tags", "preserved_constraints",
        }
        if set(value) != required_fields:
            raise OllamaCreativeError(
                "Creative output must contain exactly the declared artifact fields"
            )
        artifact_type = value.get("artifact_type")
        if not isinstance(artifact_type, str) or artifact_type not in ARTIFACT_TYPES:
            raise OllamaCreativeError("Creative output has an unsupported artifact_type")
        title = cls._bounded_text(value.get("title"), label="title", maximum=MAX_TITLE_CHARS)
        concept = cls._bounded_text(value.get("concept"), label="concept", maximum=MAX_CONCEPT_CHARS)
        elements = value.get("elements", [])
        if not isinstance(elements, list) or len(elements) > MAX_ELEMENTS:
            raise OllamaCreativeError(f"elements must be a list of at most {MAX_ELEMENTS} items")
        clean_elements = []
        for index, item in enumerate(elements):
            if not isinstance(item, dict) or set(item) != {"name", "detail"}:
                raise OllamaCreativeError(
                    f"elements[{index}] must contain exactly name and detail"
                )
            clean_elements.append({
                "name": cls._bounded_text(
                    item.get("name"), label=f"elements[{index}].name",
                    maximum=MAX_ELEMENT_NAME_CHARS,
                ),
                "detail": cls._bounded_text(
                    item.get("detail"), label=f"elements[{index}].detail",
                    maximum=MAX_ELEMENT_DETAIL_CHARS,
                ),
            })
        variations = value.get("variations", [])
        if not isinstance(variations, list) or len(variations) > MAX_VARIATIONS:
            raise OllamaCreativeError(f"variations must be a list of at most {MAX_VARIATIONS} items")
        clean_variations = [
            cls._bounded_text(item, label=f"variations[{index}]", maximum=MAX_VARIATION_CHARS)
            for index, item in enumerate(variations)
        ]
        style_tags = value.get("style_tags", [])
        if not isinstance(style_tags, list) or len(style_tags) > MAX_STYLE_TAGS:
            raise OllamaCreativeError(f"style_tags must be a list of at most {MAX_STYLE_TAGS} items")
        clean_tags = [
            cls._bounded_text(item, label=f"style_tags[{index}]", maximum=MAX_STYLE_TAG_CHARS)
            for index, item in enumerate(style_tags)
        ]
        constraints = value.get("preserved_constraints", [])
        if not isinstance(constraints, list) or len(constraints) > MAX_CONSTRAINTS:
            raise OllamaCreativeError(
                f"preserved_constraints must be a list of at most {MAX_CONSTRAINTS} items"
            )
        clean_constraints = [
            cls._bounded_text(
                item, label=f"preserved_constraints[{index}]",
                maximum=MAX_CONSTRAINT_CHARS,
            )
            for index, item in enumerate(constraints)
        ]
        return {
            "artifact_type": artifact_type,
            "title": title,
            "concept": concept,
            "elements": clean_elements,
            "variations": clean_variations,
            "style_tags": clean_tags,
            "preserved_constraints": clean_constraints,
        }

    def _infer(self, prompt: str) -> dict[str, Any]:
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_CREATIVE_PROMPT_CHARS:
            raise OllamaCreativeError(
                f"Creative prompt must contain 1..{MAX_CREATIVE_PROMPT_CHARS} characters"
            )
        schema = {
            "type": "object",
            "properties": {
                "artifact_type": {"type": "string", "enum": sorted(ARTIFACT_TYPES)},
                "title": {"type": "string"},
                "concept": {"type": "string"},
                "elements": {
                    "type": "array", "maxItems": MAX_ELEMENTS,
                    "items": {"type": "object", "properties": {
                        "name": {"type": "string"}, "detail": {"type": "string"},
                    }, "required": ["name", "detail"]},
                },
                "variations": {"type": "array", "maxItems": MAX_VARIATIONS, "items": {"type": "string"}},
                "style_tags": {"type": "array", "maxItems": MAX_STYLE_TAGS, "items": {"type": "string"}},
                "preserved_constraints": {
                    "type": "array", "maxItems": MAX_CONSTRAINTS, "items": {"type": "string"},
                },
            },
            "required": [
                "artifact_type", "title", "concept", "elements",
                "variations", "style_tags", "preserved_constraints",
            ],
        }
        system = (
            "You are a creative design specialist inside an embodied AI workspace. "
            "Generate one original, useful creative brief from the user's request. "
            "Preserve explicit constraints and distinguish invented creative choices "
            "from facts. Return only JSON matching the supplied schema. Do not return "
            "tools, actions, code, scripts, shell commands, API calls, executable "
            "instructions, world coordinates, physics parameters, or claims that you "
            "changed the environment. Your output is a proposal for a human or other "
            "specialist to review, never an instruction to execute."
        )
        body = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
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
                raw_response = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw_response) > MAX_RESPONSE_BYTES:
                    raise OllamaCreativeError("Ollama creative response exceeds the 32 KiB limit")
                result = json.loads(raw_response.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            raise OllamaCreativeError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OllamaCreativeError(f"Cannot reach local Ollama service: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OllamaCreativeError("Ollama returned invalid HTTP JSON") from exc
        try:
            parsed = json.loads(result["message"]["content"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise OllamaCreativeError("Ollama did not return a valid structured creative artifact") from exc
        return self._validate_output(parsed)

    def propose(
        self, state: LatentState, context: SpecialistContext
    ) -> Sequence[SpecialistProposal]:
        prompt = context.text.strip()
        if context.scene_graph is not None:
            graph = context.scene_graph
            scene_context = {
                "scene_id": graph.scene_id,
                "objects": [
                    {"id": item.object_id, "kind": item.kind, "material": item.material}
                    for item in graph.objects
                ],
                "relations": [
                    {"relation": item.relation, "subject": item.subject, "object": item.object}
                    for item in graph.relations
                ],
            }
            prompt = (prompt + "\n\nValidated scene context:\n" +
                      json.dumps(scene_context, sort_keys=True))
        if not prompt:
            return ()
        try:
            artifact = self._infer(prompt)
            self.last_error = None
        except OllamaCreativeError as exc:
            self.last_error = str(exc)[:500]
            return ()
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:20]
        artifact = {
            **artifact,
            "generator": "ollama",
            "model": self.model,
            "authority": "artifact_only",
            "source_prompt_sha256": digest,
        }
        identity = json.dumps(
            {"model": self.model, "artifact": artifact},
            sort_keys=True, separators=(",", ":"),
        )
        proposal_id = "creative-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        return (SpecialistProposal(
            proposal_id, self.name, "creative_artifact", artifact,
            0.65, 0.75, 0.05, 0.55, 0.0,
            context.world_revision,
            tuple(context.source_refs) + (f"creative-prompt-sha256:{digest}",),
            conflict_key="creative:" + digest,
        ),)
