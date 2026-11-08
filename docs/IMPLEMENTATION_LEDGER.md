# Chimera implementation ledger

Last verified repository branch: `tecq-causal-morphogenesis`
Repository: `foreverliverich/openworld`

This file is the durable engineering handoff. Update it in the same change as every material implementation or verification result. Do not use conversational summaries as the sole source of project status. The uploaded legacy source/transport audit is maintained in [docs/LEGACY_SOURCE_INTEGRATION_AUDIT.md](LEGACY_SOURCE_INTEGRATION_AUDIT.md). The master source reconciliation is [docs/MASTER_SOURCE_RECONCILIATION_2026-11-07.md](MASTER_SOURCE_RECONCILIATION_2026-11-07.md); the adopted ISCE/V-OMEGA standing decisions and corrections are [docs/ISCE_VOMEGA_STANDING_DECISIONS.md](ISCE_VOMEGA_STANDING_DECISIONS.md).

## Reconciliation checkpoint — 2026-11-07

- Recovered and mapped Somatic Core Stable WHITEPAPER-2, Engine of Latent Language 3.0, uploaded 2025 Python/web sources, the current openworld branch, and the historical V-OMEGA/ISCE standing decisions.
- Binding choices: browser-home hybrid lifecycle; CPU-first deterministic ISCE kernel; kernel-first independent verification then embed; one organism-state owner; measured-cost computational metabolism; CCPL intervention battery; continuous and dormant lifecycle modes must not be conflated.
- ISCE owns the authoritative intrinsic organism state. RealityEngine owns the external world and transactionally persists the ISCE state; OrganismKernel is now a compatibility controller/facade over ISCE, not a second physiology owner.
- Keep Somatic Core body gates P0–P4 separate from V-OMEGA research priorities P1–P4.
- Reconciliation artifacts: MASTER_SOURCE_RECONCILIATION_2026-11-07.md and ISCE_VOMEGA_STANDING_DECISIONS.md.
- Reconciliation and standing-decision documents are present on the current branch. GitHub Actions run [42424720110](https://github.com/foreverliverich/openworld/actions/runs/42424720110) passed the unit-tests job and standard-library test step for commit 2a7fd19f9cbfbd8c56fe39e8dbd5339e86e14192. This is documentation verification only, not evidence that missing body/ISCE/TEC-Q systems have been implemented.
- Next engineering gate: implement the independently testable ISCE state-owner kernel and its deterministic transition/CCPL contract, then migrate current OrganismKernel state into it without adding a third owner. Preserve Somatic Core P0 visual body gate as a protected parallel product requirement. Follow both documents and keep their separate P0–P4 numbering intact. The full historical source-to-code reconciliation is maintained in [docs/MASTER_SOURCE_RECONCILIATION_2026-11-07.md](MASTER_SOURCE_RECONCILIATION_2026-11-07.md); use it as the governing gap map and preserve its P0–P7 gates.

## ISCE V-OMEGA P1 integration gate

The independent kernel has now been integrated into the existing running
organism path.

- `chimera/isce.py`: versioned unified intrinsic state, embodied position,
  fixed signed weighted graph, deterministic transitions, state/input
  validation, intervention API, temporal predecessor digest and viability gate.
- `chimera/organism_kernel.py`: compatibility facade backed exclusively by
  ISCE. No duplicate legacy flat physiology state or separate physiology
  transition law remains.
- `chimera/reality_engine.py`: accepts only complete schema-v1 ISCE writes;
  atomically persists the ISCE state, local morphogenic fields, world revision
  and hash-chained event. Legacy flat payloads remain readable for conversion,
  but cannot be written through the new commit API.
- `chimera/autonomous_agent.py` and `chimera/runtime.py`: read and advance the
  same ISCE state; the runtime and API use the unified spatial anchor.
- Browser/API snapshot keeps former flat organism fields as computed read-only
  aliases. Those values are projections, not additional stored state.
- Legacy database payloads are mapped into the ISCE schema on load and are
  persisted in the new schema on the next successful tick. A production-grade
  migration backup/interruption marker remains open.

Tests now cover deterministic transitions, graph-weight and signed inhibitory
effects, graph invariance, bounded interventions, state schema/range checks,
legacy conversion, legacy-write rejection, restart persistence, failed
revision atomicity, world-field coupling, agent/runtime and HTTP API.

**Verification:** GitHub Actions run
[42426104513](https://github.com/foreverliverich/openworld/actions/runs/42426104513)
passed all 50 standard-library tests after graph/state hardening. The current
ledger/documentation commit also passed CI in run
[42426169592](https://github.com/foreverliverich/openworld/actions/runs/42426169592).

**Gate status: integrated kernel / V-OMEGA P1 partial.** ISCE is now the one
intrinsic state owner in the running Python runtime, and RealityEngine commits
that state atomically. Full ICCR five-condition acceptance, complete causal
closure/commutation, CCPL sham/double/mediation experiments, production
migration interruption recovery, browser worker clock/lifecycle, measured
hardware telemetry and the single governed action gateway remain open.
The seven-node canonical graph remains an explicitly versioned executable
starting model, not proof that the full historical graph has been recovered.

Implementation detail: [ISCE_KERNEL_IMPLEMENTATION.md](ISCE_KERNEL_IMPLEMENTATION.md).

## System ownership invariants

1. `RealityEngine` and its SQLite database are the sole authority for persistent world entities, transforms, physics, fields, revisions and world events.
2. `ISCEOrganismState` and `ISCEKernel` own intrinsic organism state and transitions. `OrganismKernel` is only a compatibility controller; `RealityEngine` stores and atomically commits ISCE state with world-field projections and the event journal.
3. `AutonomousRuntime` owns fixed-step advancement. A browser renderer must never run a second physics simulation or mutate its own copy of world state.
4. `AutonomousWorldAgent` is currently a deterministic baseline policy. It is not a trained general intelligence.
5. LLM/planner outputs, future sensory systems and tool calls must propose typed actions. Governance and `RealityEngine` validate and commit them.
6. Preserve the TEC-Q ABI and seed distinctions. Do not invent a new 48-byte cell layout, merge the 1KB identity seed with SEED2 or the 4KB form genome, or call a compact Fold lossless without its complete external checkpoint.

## Verified code inventory

| Area | Source | Current implementation | Not yet implemented |
|---|---|---|---|
| World authority | `chimera/reality_engine.py` | SQLite WAL, revision checks, atomic structures, AABB collision/support, fixed-step gravity, scalar fields, snapshots, observations, hash-chained events | Articulated/deformable mechanics, fluid/terrain, complete deterministic replay |
| Physiology / ISCE | `chimera/isce.py`, `chimera/organism_kernel.py` | One versioned ISCE state; deterministic fixed-graph transitions; allostasis, interoception, sensorimotor, temporal, self-model, attention, reserve; legacy state conversion; atomic world-field persistence | Full ICCR/CCPL validation, vascular/metabolic transport, tissue repair mechanics, organ-specific physiology, body-derived strain/sensing |
| Agent | `chimera/autonomous_agent.py` | Deterministic shelter/workbench/rest/observe baseline | General goal generation, learned policy, sensory grounding, action selection through executable toolbox |
| Runtime | `chimera/runtime.py` | One clock, physics tick, agent step and observation | Event bus, continuous runtime service, scheduling/multiple organism lifecycle |
| Toolbox | `chimera/toolbox.py` | Six named domains; validated world mutations and inspection | Executable tool drivers, grasp/use/repair/build skills, autonomous capability discovery |
| TEC-Q contract | `chimera/tecq/contract.py`, `docs/tecq-architecture-contract.json` | Machine-readable architecture constraints and boundary tests | Bonded-cell solver, torsional mechanics, phase dynamics, swarm coupling, GPU/WGSL and 15k-cell execution |
| Browser/API integration | `chimera/http_server.py`, `web/index.html` | Added local HTTP API, same-process world/runtime/toolbox, revision-aware mutations, live Three.js projection of committed world entities, physiology dashboard, event inspection, five non-body toolbox forms and the separate Somatic Core SDF interface | Anatomical rig, skin/tissue deformation, camera/sensor embodiment, GPU cell visualization, authentication for non-loopback exposure |
| Seed/Fold | `docs/TECQ-1KB-SEED-FOLD-BLUEPRINT.md` | Contracts and invariants | Original codec recovery, round-trip implementation, full content-addressed checkpoint/wake |

## Browser integration added in this change

Run from repository root:

```bash
python -m chimera.http_server --host 127.0.0.1 --port 8765 --database chimera_world.sqlite3
```

Open `http://127.0.0.1:8765`.

HTTP contract:
- `GET /api/health`: server and current world revision.
- `GET /api/state`: runtime snapshot, complete entity list, toolbox manifest and event-chain status.
- `GET /api/events?after_revision=0&limit=250`: event journal.
- `POST /api/tick` with `{"ticks":1}`: advances the one authoritative runtime.
- `POST /api/tool` with `{"tool":"world_builder","action":"create_object","expected_revision":N,"arguments":{...}}`: executes a validated toolbox action.
- `GET /`: serves the Three.js client.

The HTTP server binds to loopback by default, caps JSON bodies at 1 MiB, serializes mutation requests, uses optimistic revision checks and returns HTTP 409 for stale writes. Do not expose it to a LAN/public interface without authentication, origin policy, CSRF protection and an explicit security review.

The browser's Three.js dependency is loaded from a CDN. The simulation, state, SQLite database and Python API are local. The general world viewport still projects committed non-organism entities as boxes. Creature morphology is handled by the separate Somatic Core WebGL2 SDF renderer and its canonical SDF pair is stored in RealityEngine. This is not a claim that articulated locomotion, deformable tissue mechanics or sensorimotor coupling are complete.

## Verification status

The new API integration test file is `tests/test_http_server.py`. The full suite is configured in `.github/workflows/chimera-tests.yml` to run on branch pushes and pull requests.

**Verified passing:** GitHub Actions run [42422927651](https://github.com/foreverliverich/openworld/actions/runs/42422927651) completed successfully for commit `35e19f74b855049a572f09b7641e2abcf6bd6c23`; the `unit-tests` job and `Run standard-library test suite` step both report success. The authoring environment could not clone the repository directly, so this verification is from the hosted CI runner, not a local execution.

## Next implementation queue (ordered by dependency)

### A. Close causal validation and migration safety\n- Implement CCPL baseline/sham/single/double intervention and mediation harness.\n- Test ICCR physical support, intervention tracking, relabeling invariance, individuation and dynamical closure.\n- Add state-transition commutation and complete causal-closure tests.\n- Add durable migration backup/marker and interrupted-migration recovery tests.\n\n### B. Make the browser application robust
- Confirm CI and fix API integration tests.
- Add a clean shutdown and database path handling.
- Add bounded event polling/deltas rather than repeatedly transferring every entity.
- Add explicit request validation and typed response schemas.
- Add browser tests for object creation, stale revision rejection, tick progression and reload persistence.

### C. Close perception/action connectivity
- Define versioned event envelopes with event ID, causation ID, correlation ID, actor, world revision, simulation time, source subsystem and typed payload.
- Add a sensory adapter that converts committed entity geometry, contacts and world fields into organism-relative sensory channels.
- Add a single action gateway: planner proposal -> capability/permission validation -> revision check -> RealityEngine commit -> observation -> prediction error.
- Route the six toolbox domains through that gateway. A capability label is not executable until it has a tested driver and observable effect.

### D. Replace prototype body representation with actual mechanics
- Establish a versioned anatomy/rig schema and body-part hierarchy.
- Add joint constraints and actuator limits; couple motor commands to physical body state.
- Derive proprioception, collision/strain and movement outcomes from the same mechanics.
- Feed those measurements back to organism physiology and memory.
- Keep renderer as a projection of body state; no display-only motion that disagrees with physics.

### E. Implement TEC-Q without violating the original contract
- Recover the original 48-byte ABI field map from source/history before defining offsets.
- Keep extensions in versioned sidecar/SoA buffers.
- Build a deterministic CPU reference implementation for the 15,000-cell experiment first, including bonds, neighborhoods/spatial hashing, quaternion orientation, angular velocity/torque, energy/stress/memory/cohesion, nervous activation/refractory state and swarm intent.
- Verify conservation/stability bounds, deterministic replay, finite values and causality before adding GPU execution.
- Implement WGSL and explicit CPU-to-GPU staging; do not claim SharedArrayBuffer-to-WebGPU zero-copy.
- Profile memory honestly: 1M cells at 144 bytes/cell is 144,000,000 bytes, above a 128 MiB budget before scratch buffers.

### E. Connect learning and multi-agent cognition
- Implement spatial/episodic memory with source observations and outcome evidence.
- Store action predictions and compare them with actual world results.
- Train or update policies only from attributable experience; add held-out tasks and regression tests.
- Keep slow LLM planning asynchronous and non-authoritative.
- Implement specialist modules as cooperating services over one shared state/event contract, not separate world or organism owners.

### F. Recover and integrate original application sources
- Map the uploaded Flask, FastAPI, WebSocket, morphogenesis and latent-language files to their original runtime roles.
- Resolve the current port/protocol mismatch between the uploaded Three.js WebSocket client and Flask-SocketIO server.
- Reuse existing modules where their contracts fit; do not create parallel replacements.
- For every recovered module, record source path, import graph, state ownership, runtime entry point, dependencies, tests and integration disposition.

## Change log

- Added `chimera/http_server.py`: local HTTP server around the single existing world/organism/agent/runtime/toolbox instance.
- Added `web/index.html`: live Three.js projection of authoritative entities, physiology telemetry, object creation, body prototype creation and event-chain inspection.
- Added `tests/test_http_server.py`: HTTP-level integration tests for health/static serving, state consistency, toolbox commit visibility, stale revision rejection, runtime tick and invalid tick limits.
- GitHub Actions full standard-library suite passed on commit `35e19f74b855049a572f09b7641e2abcf6bd6c23` (run `42422927651`) and the six-domain browser assertions passed on commit `157b5043e803b6061cd8ed36e83182475a40d813` (run [42423064491](https://github.com/foreverliverich/openworld/actions/runs/42423064491)).


## Somatic Core P0 embodiment implementation — 2026-11-07

The protected body requirement has moved from a backlog statement to a connected SDF morphogenesis implementation. The detailed record and run instructions are in [SOMATIC_CORE_IMPLEMENTATION.md](SOMATIC_CORE_IMPLEMENTATION.md).

- chimera/somatic_kernel.py: server-side Gemini morphology generation conditioned on the canonical current SDF/context; API key is never exposed to browser code; structured package and GLSL safety validation.
- chimera/reality_engine.py: canonical SQLite somatic_morphology state containing the previous and current SDF, package metadata, iteration and morph start timestamp. Morph commits advance the world revision and append a hash-chained event.
- chimera/http_server.py: state read, candidate generation and separate commit routes. The browser must compile/link the generated SDF before the durable commit is allowed.
- web/somatic-core.js: WebGL2 raymarcher, A/B SDF blending, BioPBR noise/domain operators, diffusion/fur displacement, pores, subdermal variation, material IDs, soft-light SSS and AO.
- web/somatic.html: dedicated natural-language morphology interface; restores the canonical SDF pair from RealityEngine; supports screenshot-conditioned refinement with a hard ten-iteration cap.
- web/index.html: the rigid primitive Body Forge form is removed from the main UI and replaced with a link to Somatic Core.
- tests/test_somatic_kernel.py, tests/test_somatic_reality.py and expanded tests/test_http_server.py: added package, credential, multimodal image validation, ten-iteration cap, candidate-without-mutation, durable A/B persistence, revision-conflict and event-chain integration tests.

**Important transaction invariant:** model generation is not a world mutation. The candidate SDF is compiled with the current BioPBR library in the browser first. Only after successful compile/link does the browser submit the package and expected world revision for an atomic RealityEngine commit. Compile failure leaves both the displayed program and canonical state unchanged.

**Verification status:** local Python syntax and package-validation smoke checks passed. New automated tests are committed but hosted CI has not yet been confirmed for this implementation. A real WebGL2 browser run and the whitepaper's repeated T1–T7 acceptance suite have not been observed; P0 is therefore **in progress, not certified complete**. Image-conditioned ten-step refinement and pointer-orbit/wheel-zoom camera controls are now implemented; visual-quality verification against live Gemini output and the repeated browser acceptance run remain open. Long-running request cancellation/retry remains open. No articulation, locomotion, GPU particle-count or sentience claims are made.
