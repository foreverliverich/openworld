# Chimera implementation ledger

Last verified repository branch: `research/ccpl-causal-battery` (based on `tecq-causal-morphogenesis`)
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

- chimera/somatic_kernel.py: server-side Gemini morphology generation conditioned on the canonical current SDF/context; API key is never exposed to browser code; structured package, bounded-loop/host-resource GLSL safety validation and no-op SDF rejection.
- chimera/reality_engine.py: canonical SQLite somatic_morphology state containing the previous and current SDF, package metadata, iteration and morph start timestamp. Morph commits advance the world revision and append a hash-chained event.
- chimera/http_server.py: state read, candidate generation and separate commit routes. The browser must compile/link the generated SDF before the durable commit is allowed.
- web/somatic-core.js: WebGL2 raymarcher, A/B SDF blending, BioPBR noise/domain operators, diffusion/fur displacement, pores, subdermal variation, material IDs, soft-light SSS and AO.
- web/somatic.html: dedicated natural-language morphology interface; restores the canonical SDF pair from RealityEngine; supports screenshot-conditioned refinement with a hard ten-iteration cap.
- web/index.html: the rigid primitive Body Forge form is removed from the main UI and replaced with a link to Somatic Core.
- tests/test_somatic_kernel.py, tests/test_somatic_reality.py and expanded tests/test_http_server.py: added package, credential, multimodal image validation, ten-iteration cap, no-op SDF rejection, candidate-without-mutation, durable A/B persistence, revision-conflict and event-chain integration tests.

**Important transaction invariant:** model generation is not a world mutation. The candidate SDF is compiled with the current BioPBR library in the browser first. Only after successful compile/link does the browser submit the package and expected world revision for an atomic RealityEngine commit. Compile failure leaves both the displayed program and canonical state unchanged.

**Verification status:** local Python syntax and package-validation smoke checks passed. New automated tests are committed but hosted CI has not yet been confirmed for this implementation. A real WebGL2 browser run and the whitepaper's repeated T1–T7 acceptance suite have not been observed; local headless Chromium could not initialize EGL/SwiftShader in this environment. P0 is therefore **in progress, not certified complete**. Image-conditioned ten-step refinement and pointer-orbit/wheel-zoom camera controls are now implemented; visual-quality verification against live Gemini output and the repeated browser acceptance run remain open. Long-running request cancellation/retry remains open. No articulation, locomotion, GPU particle-count or sentience claims are made.


## CCPL intervention battery — 2026-11-08

Added chimera/ccpl.py and tests/test_ccpl.py on the isolated research/ccpl-causal-battery branch.

- Runs paired deterministic trajectories from one immutable ISCE initial state and one identical ordered input sequence.
- Includes baseline, zero-delta sham, single intervention, simultaneous double intervention and mediator-clamped conditions.
- Records full state trajectories, initial-state digest, fixed-graph fingerprint, final outcome effects, sham error and mediation attenuation.
- Interventions are bounded state clamps at a defined transition boundary; the causal graph and structural weights remain unchanged.
- Default experiment perturbs body integrity, then resource reserve, and tests whether the interoceptive precision path mediates a downstream attention change.
- The experiment harness is separate from the organism state owner and does not alter runtime behavior or persistence schema.

**Verification status:** tests have been added but have not yet been executed by hosted CI. The authoring environment could not reach GitHub for a local clone. The workflow now includes research/** push branches so the isolated research branch will run the same Python 3.11 regression suite. Do not mark CCPL or ICCR acceptance complete until the hosted run passes and the experiment's expected causal effects are confirmed.

Details: CCPL_INTERVENTION_BATTERY.md.


## Governed organism action path — 2026-11-08

Added chimera/action_gateway.py and tests/test_action_gateway.py. AutonomousWorldAgent now routes shelter and workbench construction through OrganismActionGateway and the existing ChimeraToolbox; it no longer writes those structures directly to RealityEngine. OrganismKernel.tick accepts a backward-compatible action_success input and persists it through the existing ISCE sensorimotor partition.

- The gateway accepts typed ActionProposal values and enforces a fixed mutation allowlist.
- It rejects stale world revisions, non-viable organisms and insufficient energy/reserve before dispatch.
- It delegates validation and mutation to the existing toolbox/RealityEngine path; no new world or organism state owner is introduced.
- It measures deterministic logical work from the committed operation (e.g. actual structure part count), charges prototype ISCE reserve/energy units, and records success, prediction error, novelty and outcome.
- The action event and organism outcome update are sequential transactions, not a cross-database atomic transaction. A reconciliation error is explicit; the committed action is never replayed automatically.
- Logical work units are operation counts, not hardware cycles, joules or measured GPU/CPU time.

**Verification:** GitHub Actions run 42511093047 passed the complete Python 3.11 standard-library suite: 90 tests in 6.507 seconds, including all six action-gateway tests, nine CCPL tests and the existing autonomous-agent/runtime regressions. CCPL tests confirm deterministic replay, sham=baseline, intervention effects, same-boundary double intervention, mediator attenuation and invariant graph fingerprint. This verifies the software contracts exercised by the tests; it does not establish full ICCR, biological metabolism or consciousness.

Details: ACTION_GATEWAY.md and CCPL_INTERVENTION_BATTERY.md.


## Grounded sensory feedback — 2026-11-08

Added chimera/sensory.py and tests/test_sensory.py. The autonomous agent's observe/consolidate step now converts authoritative RealityEngine observations into visible-entity count, nearest distance, proximity, local density, stable geometry signature, bounded observation surprise, novelty and sensory salience. The compact versioned observation token is stored in the existing ISCE self-model last_outcome field; no second memory store is added.

- ISCE TransitionInput gains sensory_salience at the end of the dataclass to preserve positional compatibility. It is validated in [0,1] and contributes to the existing urgency/focus transition.
- OrganismKernel passes the sensory input through; ISCE kernel version is bumped to 0.2.0 while persisted state schema remains version 1.
- AutonomousWorldAgent exposes the measured sensory values in its step result and records the token through the existing ISCE state commit.
- This is world-state visual sensing over the current AABB entity scene, not camera vision, touch, hearing, proprioception or anatomical sensing. The count/signature surprise measure is an initial grounded proxy, not a complete predictive perception system.

Details: SENSORY_GROUNDING.md. Verification for the latest combined commit is pending hosted CI.


## Browser-home worker scheduler — 2026-11-08

Added web/runtime-worker.js and explicit Run organism / Pause controls to web/index.html. The worker schedules three authoritative POST /api/tick calls per 100 ms batch and reports committed frames to the page. The browser now displays attention focus/urgency and last-frame grounded sensory salience, novelty and observation error.

- The worker does not own ISCE or RealityEngine state; the existing Python runtime and SQLite database remain authoritative.
- requestAnimationFrame remains visual-only. The worker uses a bounded, non-overlapping setTimeout loop and stops on errors, explicit pause or page unload.
- Browser suspension/closure interrupts execution. These periods are paused/dormant, not continuous organism life. No background execution guarantee is claimed.
- Python CI statically verifies worker/API wiring, start/stop controls, disposal and no worker render loop. It does not replace real-browser Web Worker, Three.js or WebGL2 acceptance.

**Verification:** GitHub Actions run 42511589801 passed 100 Python 3.11 standard-library tests in 5.810 seconds. This includes the CCPL, action-gateway, sensory adapter, browser-worker wiring and existing project regressions. Actual browser/WebGL2 execution remains unverified.

Details: BROWSER_WORKER_LIFECYCLE.md.


## Durable action-to-organism causal links — 2026-11-08

The action gateway now carries the RealityEngine action_id into the following ISCE organism-tick event as causation_id and correlation_id. RealityEngine stores these references in the existing hash-chained event payload; AgentStep and RuntimeFrame expose the originating action_id. This creates an auditable link between an external world mutation and the organism's measured outcome update without adding a second event store or changing the database schema.

The world action and organism update remain sequential transactions. The causal link makes a partial failure detectable; it does not make the pair atomic and does not auto-replay the committed world action.

**Verification:** GitHub Actions run 42511781699 passed 100 Python 3.11 standard-library tests in 5.792 seconds. The action gateway test verifies that the organism-tick event causation_id/correlation_id match the preceding world action_id, while the event hash chain remains valid. The autonomous-agent regression verifies action IDs are preserved through AgentStep.

Details: CAUSAL_ACTION_LINKS.md.


## Somatic GPU hot path — 2026-11-08

Added `web/somatic-gpu.js`, an opt-in WebGPU compute module, plus `tests/test_somatic_gpu_contract.py`. The Somatic Core page exposes a 65,536-cell start/stop control. The kernel preserves the 48-byte / three-vec4 ABI, pages buffers according to the actual adapter limits, uploads initial cell state once, and keeps simulation state GPU-resident between explicit diagnostic readbacks.

Implemented in this slice: semi-implicit Euler integration, gravity, horizontal ground contact, restitution, tangential friction and bounded stress-dependent energy drain. The kernel validates dt and disposal, checks shader compilation, and has explicit teardown. It is intentionally not wired as a replacement for RealityEngine's authoritative world state.

Not implemented: inter-cell broadphase/contact, joints, torsion, bonded-cell learning, Rapier, deformable SDF contact, high-count performance claims or continuous background execution. The 5M-cell example is not adopted; 240 MB of cell data alone may exceed per-binding limits and would require paging plus device-specific performance measurement. `queue.writeBuffer` is a host-to-GPU upload, not zero-copy. See `docs/SOMATIC_GPU_HOT_PATH.md`.


## Cognitive-goal → Somatic GPU steering seam

- Adopted the useful transport/actuation idea from the submitted WebSocket and
  TypeScript bridge, while retaining the current 48-byte SomaticCell ABI.
- `web/somatic-gpu.js` now accepts a bounded attractor target through a
  64-byte uniform block. Goal acceleration is capped and zero-distance safe;
  no arbitrary harmonic/vortex forces were introduced.
- `web/chimera-bridge.js` accepts only schema-v1 messages explicitly marked
  accepted, with a monotonically increasing goal sequence and separate world
  revision provenance. It does not commit GPU physiology to SQLite.
- Added static contract tests and `docs/COGNITIVE_GOAL_GPU_BRIDGE.md`.
- Not yet implemented: Python WebSocket publisher wired into the existing
  application/action gateway, browser/GPU end-to-end validation, worker
  ownership protocol, or calibrated GPU telemetry commits. The standalone
  Python server in the proposal is not used because it could create a second
  RealityEngine authority.


## Browser cross-origin isolation prerequisite

- `chimera/http_server.py` now emits COOP `same-origin`, COEP `require-corp`
  and CORP `same-site` from the common `end_headers()` path, covering API,
  static and error responses.
- `tests/test_http_server.py` checks these headers on API, root HTML and 404
  responses.
- This enables the browser isolation prerequisite for `SharedArrayBuffer`;
  it does not make SharedArrayBuffer directly GPU-bindable and does not add
  zero-copy CPU/GPU sharing.
- COEP can block cross-origin subresources that do not opt in. The current
  Three.js import map uses unpkg; browser validation must confirm that CDN
  module responses satisfy CORS/COEP or move Three.js to same-origin hosting.
- The current app has a Three.js world renderer and a separate WebGL2 Somatic
  Core page plus an opt-in WebGPU compute test. It does not yet have the
  proposed two-canvas fused renderer, shared camera contract, Gaussian splat
  renderer, or a GPU draw pipeline. Camera matrix synchronization is therefore
  deferred until a real GPU renderer consumes those matrices.
- The proposed 64-byte OmniKernel and 20-worker matrix remain unadopted: they
  conflict with the existing 48-byte GPU cell ABI and lack an ownership /
  synchronization protocol. Preserve the 48-byte ABI until a measured,
  tested migration is justified.


## Watchdog-aware GPU dispatch update

- `web/somatic-gpu.js` now rotates through bounded contiguous cell ranges
  instead of dispatching every cell on every frame. Default scheduling target:
  five rotating slices, hard-capped at 262,144 processed cells per frame.
- WGSL uses a base-cell offset in the existing 64-byte parameter block; the
  48-byte cell ABI is unchanged.
- The final range does not wrap within one command submission, preventing
  multiple writes to a reused page uniform before its dispatches execute.
- Static contract coverage added in `tests/test_somatic_gpu_contract.py`.
- This is a scheduling safeguard, not a verified TDR bypass. Per-cell update
  frequency is lower than display refresh when the population exceeds the
  per-frame budget; physical time equivalence is not yet solved.
- Radix depth sorting / ping-pong splat buffers, AxiomScript/NCA, 16-float
  latent gene decoding, spectral audio-to-body coupling and a Gaussian splat
  renderer remain unimplemented in this branch. No recovered legacy source
  for these exact named modules has yet been merged into this execution path.


## 2026-11-08 — local spectral audio bridge
- Added `web/somatic-audio.js`: WebAudio FFT band extraction (bass/mids/treble), smoothing, explicit lifecycle, local-only processing and bounded GPU coupling.
- Extended the WebGPU uniform block from 64 to 112 bytes while preserving the 48-byte cell ABI. Shader maps bass to vertical, mids to radial and treble to tangential bounded forces.
- Added static contract tests and usage/limitations documentation.
- Status: source changes committed in this branch; browser audio permission, WebAudio playback, WGSL compilation, physical response and GPU timing remain unverified. This is not the historical AxiomScript/NCA, Gaussian sorter, or TDR bypass.


## 2026-11-08 — Gaussian depth-key stage
- Added `web/somatic-sort-depth.wgsl`: GPU camera-space depth key generation and original-index output.
- Uses finite nonnegative right-handed view depth and monotonic positive IEEE-754 bit ordering, inverted for far-to-near ascending uint sort.
- Added static source-contract test and documented exact scope.
- Not implemented: radix histograms, hierarchical prefix scan, stable local rank/scatter, ping-pong orchestration, splat draw pipeline, or five-million-element benchmark. User-provided scatter pseudocode is not accepted as complete because the required prefix-scan/rank stages are absent.


## 2026-11-08 — first complete GPU radix-sort pipeline
- Added `web/somatic-gpu-sort.js`: camera-space depth-key generation from existing SomaticGPU pages; eight 4-bit LSD passes; per-workgroup histograms; per-bucket/group prefix offsets; atomic local scatter; key/index ping-pong; sorted index GPU buffer output.
- Integrated through `SomaticGPU.createRadixSorter()`; existing simulation API, 48-byte cell ABI, physics and audio path remain intact.
- Added static source-contract tests and limitations documentation.
- Known constraints: unstable ordering for equal depth keys; prefix scan is serial per bucket across workgroups and may bottleneck; all global key/index buffers must fit storage-binding limits; no splat draw pipeline; no actual browser/GPU validation or 5M benchmark yet.


## 2026-11-08 — hierarchical radix prefix refinement
- Replaced the single-workgroup serial per-bucket prefix loop with 256-group tiled local scans plus a compact block-prefix stage.
- Added explicit maximum storage-buffer and workgroup-dispatch limit checks.
- Preserves the existing histogram/scatter/ping-pong API and original SomaticCell ABI.
- Still requires WGSL compilation and GPU benchmark; atomic local rank means equal-depth tie ordering is not stable.


## Digital-cell integration gate — 2026-11-08

- Added `chimera/digital_cell.py`: a small deterministic cell controller with
  bounded energy/stress, leaky membrane potential, refractory gating, three
  actions, reward-prediction memory and a pure transition into ISCE.
- Added `tests/test_digital_cell.py` for state bounds, deterministic behavior,
  action-memory updates, depleted-energy gating and ISCE tick coupling.
- Added `docs/DIGITAL_CELL_EXPERIMENT.md` with scope and a paired adaptive /
  frozen-memory / shuffled-outcome acceptance protocol.
- This is an experiment seam, not a production cell population, gene-expression
  system, tissue model or proof of learning. Environment observations are
  supplied by the caller; no RealityEngine sensor or GPU coupling is claimed.
- Verification is pending until the branch CI runs the new tests.
