"""Server-side Gemini morphology compiler for Somatic Core.

The API key never reaches the browser. Model output is treated as untrusted GLSL:
the renderer compiles it in an isolated WebGL program and retains the last good form.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

MODEL = os.getenv("CHIMERA_GEMINI_MODEL", "gemini-2.5-flash")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_DESCRIPTION = 2000
REQUIRED_FIELDS = {"label", "persona", "dialogue", "critique", "sdfScript", "color", "material"}

SYSTEM_INSTRUCTION = r"""
You are SomaticKernel, a production GLSL signed-distance-field creature morphologist.
Return only one JSON object with fields label, persona, dialogue, critique, sdfScript,
color (three floats 0..1), material ({roughness, metallic, sssIntensity}).
sdfScript MUST be a complete GLSL function: vec2 map_object(vec3 p) { ... return vec2(distance, materialId); }
It is compiled after the BioPBR library. Use the available functions:
sdHumanoidBase(vec3)->vec2, sdSphere(vec3,float), sdCapsule(vec3,vec3,vec3,float),
sdEllipsoid(vec3,vec3), smin(float,float,float), smax(float,float,float),
opTaper(inout vec3,float), opBulge(inout vec3,float), opBend(inout vec3,float),
opInflate(inout vec3,float), opAsymmetry(inout vec3,float), opLatentWarp(vec3,float),
opFur(float,vec3,float,float), diffusion_noise(vec3), getSkinPores(vec3),
getSubdermalFlow(vec3), preintegratedSSS(vec3,vec3,vec3,float).
Material IDs: 1 skin, 2 mucosa, 3 tongue, 4 eye, 5 bone/teeth/chitin.
For ordinary mammals, build coherent torso, head, muzzle, four legs and tail from capsules,
ellipsoids and smooth unions. For humanoids, start from sdHumanoidBase. Use domain warping
and diffusion detail so the form is organic rather than stacked primitive toy geometry.
Keep the creature centered near origin, approximately 2 units tall, bounded within radius 1.5.
Distance must be a signed distance estimate in world units; do not use loops with unbounded
iteration, texture calls, uniforms, structs, main(), precision declarations or #version.
No prose outside JSON. Never omit sdfScript. Output syntactically valid GLSL ES 3.00.
"""

def _validate_package(package: Any) -> dict[str, Any]:
    if not isinstance(package, dict) or not REQUIRED_FIELDS.issubset(package):
        raise ValueError("Gemini response is missing required morphology package fields")
    script = package["sdfScript"]
    if not isinstance(script, str) or len(script) < 40 or len(script) > 24000:
        raise ValueError("sdfScript must be a non-empty GLSL function under 24 KB")
    if not re.search(r"\bvec2\s+map_object\s*\(\s*vec3\s+\w+\s*\)", script):
        raise ValueError("sdfScript must define vec2 map_object(vec3 p)")
    if any(token in script for token in ("#version", "void main", "gl_FragColor", "layout(")):
        raise ValueError("sdfScript contains a forbidden shader entry point or directive")
    color = package["color"]
    if not isinstance(color, list) or len(color) != 3 or any(
        not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 1 for v in color
    ):
        raise ValueError("color must be three normalized RGB values")
    material = package["material"]
    if not isinstance(material, dict):
        raise ValueError("material must be an object")
    for key in ("roughness", "metallic", "sssIntensity"):
        value = material.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
            raise ValueError(f"material.{key} must be between 0 and 1")
    for key in ("label", "persona", "dialogue", "critique"):
        if not isinstance(package[key], str):
            raise ValueError(f"{key} must be a string")
        package[key] = package[key][:2000]
    return package

def generate_morph_package(description: str, current_label: str = "") -> dict[str, Any]:
    description = description.strip()
    if not description or len(description) > MAX_DESCRIPTION:
        raise ValueError(f"description must contain 1..{MAX_DESCRIPTION} characters")
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY on the server.")
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text":
            f"Transform the current creature ({current_label or 'genesis form'}) into: {description}. "
            "Return the complete target SDF package. Preserve biological coherence."}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.35,
            "maxOutputTokens": 8192
        }
    }
    request = urllib.request.Request(
        API_URL.format(model=MODEL) + "?key=" + api_key,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"Gemini API returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Gemini request failed: {exc}") from exc
    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        package = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini did not return a valid structured morphology package") from exc
    return _validate_package(package)


def validate_morph_package(package: Any) -> dict[str, Any]:
    """Public validation boundary for packages returned to the browser for shader compilation."""
    return _validate_package(package)
