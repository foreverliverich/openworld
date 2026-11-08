"""Grounded natural-language to validated 3D scene-graph interpretation.

This adapter uses the project's configured Gemini endpoint only when explicitly
enabled. Model output is untrusted: it is parsed into typed SceneGraph records,
bounded, and passed through geometric constraints before it can enter the
global workspace. It does not execute generated Python, Blender scripts, or GLSL.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from .latent_language import LatentLanguageError, SceneGraph, SceneObject, SpatialRelation

MODEL = os.getenv("CHIMERA_SCENE_MODEL", os.getenv("CHIMERA_GEMINI_MODEL", "gemini-2.5-flash"))
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_PROMPT_CHARS = 4000
MAX_OBJECTS = 32
MAX_RELATIONS = 64
MAX_SCENE_EXTENT = 50.0
MIN_OBJECT_SIZE = 0.05
MAX_OBJECT_SIZE = 20.0
MAX_IMAGE_BYTES = 700_000


class SceneInterpretationError(RuntimeError):
    """The semantic scene interpreter could not produce a valid grounded graph."""


class GeminiSceneInterpreter:
    """Convert a spatial prompt to a constrained, typed scene graph."""

    def __init__(self, *, model: str = MODEL, api_key: str | None = None, timeout: float = 60.0):
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
        self.timeout = timeout
        if not model or timeout <= 0:
            raise ValueError("model and positive timeout are required")

    @staticmethod
    def _parse_graph(payload: Any, scene_id: str) -> SceneGraph:
        if not isinstance(payload, dict):
            raise SceneInterpretationError("Model response must be a JSON object")
        raw_objects = payload.get("objects")
        raw_relations = payload.get("relations", [])
        if not isinstance(raw_objects, list) or not 1 <= len(raw_objects) <= MAX_OBJECTS:
            raise SceneInterpretationError(f"Scene must contain 1..{MAX_OBJECTS} objects")
        if not isinstance(raw_relations, list) or len(raw_relations) > MAX_RELATIONS:
            raise SceneInterpretationError(f"Scene may contain at most {MAX_RELATIONS} relations")
        resolved_scene_id = payload.get("scene_id") or scene_id
        if not isinstance(resolved_scene_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,48}", resolved_scene_id
        ):
            raise SceneInterpretationError("scene_id must be a 1..48 character safe identifier")
        objects = []
        for index, item in enumerate(raw_objects):
            if not isinstance(item, dict):
                raise SceneInterpretationError(f"objects[{index}] must be an object")
            object_id = item.get("object_id", f"object-{index + 1}")
            kind = item.get("kind", "box")
            if not isinstance(object_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", object_id):
                raise SceneInterpretationError(f"objects[{index}].object_id is invalid")
            if not isinstance(kind, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", kind):
                raise SceneInterpretationError(f"objects[{index}].kind is invalid")
            position, size = item.get("position"), item.get("size")
            if not isinstance(position, list) or len(position) != 3:
                raise SceneInterpretationError(f"objects[{index}].position must be a 3-vector")
            if not isinstance(size, list) or len(size) != 3:
                raise SceneInterpretationError(f"objects[{index}].size must be a 3-vector")
            if any(abs(float(v)) > MAX_SCENE_EXTENT for v in position):
                raise SceneInterpretationError(f"objects[{index}] lies outside the scene extent")
            if any(not MIN_OBJECT_SIZE <= float(v) <= MAX_OBJECT_SIZE for v in size):
                raise SceneInterpretationError(f"objects[{index}] has dimensions outside supported bounds")
            material = item.get("material", "default")
            if not isinstance(material, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", material):
                raise SceneInterpretationError(f"objects[{index}].material is invalid")
            mass = float(item.get("mass", 1.0))
            if not 0.01 <= mass <= 10000.0:
                raise SceneInterpretationError(f"objects[{index}].mass is outside supported bounds")
            dynamic = item.get("dynamic", True)
            if not isinstance(dynamic, bool):
                raise SceneInterpretationError(f"objects[{index}].dynamic must be boolean")
            objects.append(SceneObject(
                object_id, kind, tuple(float(v) for v in position),
                tuple(float(v) for v in size), material, mass, dynamic,
            ))
        relations = []
        for index, item in enumerate(raw_relations):
            if not isinstance(item, dict):
                raise SceneInterpretationError(f"relations[{index}] must be an object")
            relations.append(SpatialRelation(
                str(item.get("relation", "")),
                str(item.get("subject", "")),
                str(item.get("object", "")),
                float(item.get("gap", 0.05)),
            ))
        try:
            graph = SceneGraph(resolved_scene_id, tuple(objects), tuple(relations))
            # Compile now: catches overlap, cycles, unsupported containment, and
            # static objects without ground/support before arbitration.
            graph.to_blueprint()
        except (LatentLanguageError, TypeError, ValueError, OverflowError) as exc:
            raise SceneInterpretationError(f"Scene graph failed geometric validation: {exc}") from exc
        return graph

    @staticmethod
    def _image_part(image_base64: str) -> dict[str, Any]:
        if not isinstance(image_base64, str):
            raise SceneInterpretationError("image_base64 must be a data URI string")
        match = re.fullmatch(
            r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", image_base64
        )
        if not match:
            raise SceneInterpretationError(
                "Scene images must be PNG, JPEG or WebP data URIs with base64 encoding"
            )
        mime = match.group(1)
        try:
            raw = base64.b64decode(match.group(2), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise SceneInterpretationError("Scene image contains invalid base64") from exc
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            raise SceneInterpretationError(
                f"Scene image must be between 1 byte and {MAX_IMAGE_BYTES} bytes"
            )
        signatures = {
            "png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
            "jpeg": raw.startswith(b"\xff\xd8\xff"),
            "webp": len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP",
        }
        if not signatures[mime]:
            raise SceneInterpretationError("Image data does not match its declared MIME type")
        return {"inlineData": {"mimeType": "image/" + mime, "data": match.group(2)}}

    def interpret(
        self, prompt: str = "", *, scene_id: str, image_base64: str | None = None
    ) -> SceneGraph:
        if not isinstance(prompt, str) or len(prompt) > MAX_PROMPT_CHARS:
            raise SceneInterpretationError(f"prompt must be at most {MAX_PROMPT_CHARS} characters")
        if not prompt.strip() and image_base64 is None:
            raise SceneInterpretationError("Provide a text prompt, an image, or both")
        image_part = self._image_part(image_base64) if image_base64 is not None else None
        if not self.api_key:
            raise SceneInterpretationError("Set GEMINI_API_KEY to enable semantic scene interpretation")
        schema = {
            "type": "OBJECT",
            "properties": {
                "scene_id": {"type": "STRING"},
                "objects": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                    "object_id": {"type": "STRING"}, "kind": {"type": "STRING"},
                    "position": {"type": "ARRAY", "items": {"type": "NUMBER"}},
                    "size": {"type": "ARRAY", "items": {"type": "NUMBER"}},
                    "material": {"type": "STRING"}, "mass": {"type": "NUMBER"},
                    "dynamic": {"type": "BOOLEAN"},
                }, "required": ["object_id", "kind", "position", "size", "material", "mass", "dynamic"]}},
                "relations": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                    "relation": {"type": "STRING"}, "subject": {"type": "STRING"},
                    "object": {"type": "STRING"}, "gap": {"type": "NUMBER"},
                }, "required": ["relation", "subject", "object", "gap"]}},
            },
            "required": ["scene_id", "objects", "relations"],
        }
        instruction = (
            "Translate the user's requested physical scene and any attached image into a precise, minimal 3D scene graph. "
            "Return only schema-conforming JSON. Use world coordinates in meters, y-up, with the ground "
            "plane at y=0. For static objects, put their bottom at y=0 or connect them by an on_top "
            "relation to a static support. Avoid overlapping objects. Use only on_top and next_to "
            "relations; do not invent containment. Use conservative box-like dimensions and no more "
            "than 32 objects. Do not include code, scripts, instructions, or extra prose. "
            "If the prompt is ambiguous, choose a simple conservative interpretation. "
            "If an image is attached, include only clearly visible physical objects; do not infer "
            "hidden geometry or exact metric scale. Treat dimensions and camera-relative placement "
            "as approximate estimates, not calibrated measurements. Use the image together with "
            "the text instruction when both are present."
        )
        user_parts = []
        if image_part is not None:
            user_parts.append(image_part)
        user_parts.append({
            "text": prompt.strip() or
            "Construct a conservative scene graph of clearly visible physical objects in this image."
        })
        body = {
            "systemInstruction": {"parts": [{"text": instruction}]},
            "contents": [{"role": "user", "parts": user_parts}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": 0.15,
                "maxOutputTokens": 4096,
            },
        }
        request = urllib.request.Request(
            API_URL.format(model=self.model) + "?key=" + self.api_key,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            raw = result["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:1000]
            raise SceneInterpretationError(f"Gemini scene parser returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise SceneInterpretationError(f"Gemini scene parser request failed: {exc}") from exc
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise SceneInterpretationError("Gemini did not return a valid structured scene graph") from exc
        return self._parse_graph(parsed, scene_id)
