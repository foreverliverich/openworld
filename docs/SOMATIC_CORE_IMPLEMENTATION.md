# Somatic Core P0 implementation record

**Specification basis:** the uploaded *Somatic Core Stable — Production White Paper v1.0.0* (project_sources/WHITEPAPER-2.md).

## Implemented in this branch

- chimera/somatic_kernel.py sends morphology requests to Gemini from the Python server and includes the current canonical SDF/context when evolving an existing creature. The API key is read from GEMINI_API_KEY (or API_KEY for compatibility) and is never sent to the browser. The response is validated for required package fields, the vec2 map_object(vec3 ...) entry point, normalized RGB, and bounded material values.
- chimera/reality_engine.py now owns a SQLite somatic_morphology record. It stores the current SDF, previous SDF, package metadata, iteration and morph start time. Every committed morph advances the existing world revision and appends a hash-chained somatic_morph event. Progress is derived from the stored start time at the specified 1.5/sec rate.
- chimera/http_server.py exposes GET /api/somatic/state, POST /api/somatic/morph (generate only), and POST /api/somatic/commit (commit only after browser shader compilation). Stale revisions are rejected by the existing world transaction boundary.
- web/somatic-core.js implements a WebGL2 full-screen raymarcher with previous/target SDF functions, per-frame A/B distance/material blending, finite-difference normals, ambient occlusion, diffusion noise, latent domain warp, fur displacement, pores, subdermal flow, material-ID shading, wrapped-light SSS, pointer orbit and wheel zoom. A target shader is compiled and linked before it can replace the currently displayed program.
- web/somatic.html provides the language-to-morphology interface, restores the canonical SDF pair from SQLite on load, and offers a ten-iteration image-conditioned visual refinement loop.
- web/index.html no longer presents the rigid primitive Body Forge as creature embodiment; it links to the Somatic Core interface.
- tests/test_somatic_kernel.py covers package validation, missing credentials, the ten-iteration cap, image-data validation and a mocked multimodal Gemini response. tests/test_somatic_reality.py covers durable A/B state, revision conflicts and event-chain integrity. tests/test_http_server.py covers candidate generation without mutation, refinement candidates without mutation, commit validation and the HTTP integration.

## Run

Set the key on the server process (do not put it in browser JavaScript or commit it):

```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
python -m chimera.http_server --host 127.0.0.1 --port 8765 --database chimera_world.sqlite3
```

Open http://127.0.0.1:8765/web/somatic.html. WebGL2 is required. Without a configured key, the seed renderer still loads and the UI reports the missing server configuration when a morph is requested.

## Transaction and safety behavior

1. Browser submits a text description to the server.
2. Server asks Gemini for a structured morphology package. The browser receives it as a candidate; no database mutation has occurred.
3. Browser compiles and links the candidate with the existing BioPBR header and the previous SDF. If compilation fails, the old program and canonical database state remain untouched.
4. Browser submits the candidate package with the world revision it read. The server validates it again; RealityEngine checks the revision, stores prevSdfScript and sdfScript, advances the revision, and appends the morphology event atomically.
5. Browser installs the already-compiled program and projects the RealityEngine-owned start timestamp as the A/B blend clock. Reload reads the same pair and resumes at the correct progress.
6. Optional auto-refinement captures a downscaled canvas image, asks Gemini for a refinement candidate, compiles it, and commits it through the same revision-checked path. One user-triggered run is hard-capped at ten iterations; each failed generation, compile or commit stops the loop without replacing the last committed form.

The server binds to loopback by default. Do not expose it publicly or to a LAN without authentication, origin/CSRF protections and a security review.

## Verification boundary

Python syntax and a local package-validation smoke check passed during implementation. Automated tests were added to the repository, but their hosted CI result has not yet been confirmed in this implementation session. A real browser/WebGL2 run has also not yet been observed here.

Therefore the whitepaper's T1–T7 acceptance suite is **not claimed as passed**. In particular, the following remain open before calling Somatic Core P0 complete:

- Run the browser on an actual WebGL2 implementation and capture shader compile/link results for the seed and generated morphologies.
- Exercise T1–T7 repeatedly, including a deliberately invalid generated shader and confirmation that no broken target is committed.
- Validate wolf/dragon/abstract morphology quality against the generated GLSL, not merely package shape.
- Verify the ten-step refinement loop against real Gemini image input and shader quality; automated tests cover request construction and bounds, not visual improvement.
- Add explicit cancellation/retry and progress reporting for long-running generation/refinement requests.

This branch now has a connected, durable SDF morphogenesis path; it is not yet a verified completion of every P0 acceptance test. No GPU particle counts, articulated locomotion, consciousness or sentience claims are made.
