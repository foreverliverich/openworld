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
| Physiology / ISCE | `chimera/isce.py`, `chimera/organism_kernel.py`, `chimera/biomechanics.py` | One versioned ISCE state; deterministic fixed-graph transitions; allostasis, interoception, sensorimotor, temporal, self-model, attention, reserve; versioned 16-segment/15-joint articulated body; PD actuators, hinge limits, gravity loading, root integration, foot/ground contact; body-derived work/strain/proprioception; legacy neutral-articulation migration; atomic world-field persistence | Full ICCR/CCPL validation, vascular/metabolic transport, tissue-level mechanics, coupled multibody constraints, 3D multi-axis joints, self-collision/terrain/friction, body-derived multimodal sensing |
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

**Verification status:** GitHub Actions run [42430631014](https://github.com/foreverliverich/openworld/actions/runs/42430631014) passed the standard-library unit suite and the real Chromium/ANGLE/SwiftShader WebGL2 acceptance job. The browser test verifies SDF entrypoint parsing, shader compile/link, framebuffer output, invalid-candidate rejection without replacing the active program, valid A/B installation and no post-morph WebGL error. The whitepaper's repeated T1–T7 visual-quality suite, live Gemini morphology quality, and long-running request cancellation/retry remain open. P0 is therefore **in progress, not certified complete**. No GPU particle-count or sentience claims are made.


## Articulated biological body mechanics — implementation added

The former body-mechanics backlog has an executable first implementation on branch `articulated-biomechanics`.

- `chimera/biomechanics.py`: versioned `human-3d-1` segment tree (16 rigid segments, 15 joints), three-axis spine/neck/shoulder/hip joints, two-axis wrist/ankle joints, hinge knees/elbows, quaternion-composed forward kinematics, Jacobian-assembled generalized mass matrix, finite-difference Christoffel/Coriolis bias, world-frame gravity projection, deterministic pivoted linear solve, bounded activation/force-length/force-velocity actuators, compliant series-elastic tendon state, joint-specific torque and angular-speed envelopes, all-segment capsule ground contact and <=20ms semi-implicit substeps.
- `chimera/isce.py`: articulation is nested inside the single authoritative `OrganismState`; motor commands and root acceleration enter through validated `TransitionInput`; mechanical strain/work/metabolic cost/proprioception are derived from the solver and coupled into physiology, sensorimotor state, energy and reserve.
- `chimera/organism_kernel.py` forwards revision-checked joint targets and root acceleration into ISCE. `chimera/http_server.py` exposes `GET /api/body/pose` for committed segment/joint transforms and `POST /api/body/actuate` for fixed-step, revision-checked motor commands; invalid joints and stale revisions are rejected.
- `web/index.html` now projects returned segment quaternions and local axes in the Three.js world scene and exposes hip/shoulder three-axis controls plus scalar knee/elbow controls. The UI refreshes from committed body-pose responses; it does not animate a second local physics state.
- Existing RealityEngine persistence remains the only durable organism-state path. Articulation is serialized in the existing schema-v1 organism payload; old schema-v1 payloads without the additive articulation field load with a neutral canonical skeleton.
- `tests/test_biomechanics.py`: coverage for skeleton topology, quaternion kinematics, three-axis actuation, tendon compliance, per-axis limits and speed saturation, mass-matrix symmetry/inter-joint coupling, Coriolis bias, capsule ground contact, root translation, round-trip persistence, invalid commands, sagittal-to-3D migration and ISCE coupling.
- `tests/browser_body_acceptance.py`: launches the local HTTP application in Chromium with ANGLE/SwiftShader, verifies the live Three.js WebGL2 body projection, checks native motor-form validity, submits a three-axis hip command through the UI, and reads the committed pose from the authoritative API.
- Full model assumptions, equations, state contracts, units, verification requirements and remaining limitations are documented in [ARTICULATED_BIOMECHANICS.md](ARTICULATED_BIOMECHANICS.md).

**Verification status:** GitHub Actions run [42433374952](https://github.com/foreverliverich/openworld/actions/runs/42433374952) passed both gates: all **100 standard-library tests** and the real Chromium/ANGLE/SwiftShader Three.js browser acceptance. The browser test verifies the live WebGL2 scene, all 16 segment projections, valid 3D motor controls, a hip abduction command submitted through the UI, and the committed joint pose returned by the application API. The mechanics gate includes quaternion 3D kinematics, compliant tendon state, force-length/force-velocity torque scaling, bounded angular speed, Jacobian-assembled generalized mass matrix, finite-difference Christoffel/Coriolis terms, pivoted linear solve, whole-body capsule ground contact, sagittal-to-3D migration, HTTP/API and ISCE persistence regressions. This is a deterministic rigid-segment articulated model, not a complete biological digital twin. Generalized contact impulses, root degrees of freedom in the mass matrix, self-collision, friction cones, antagonistic muscle pairs, calibrated tissue mechanics, multimodal sensory grounding and high-fidelity skin/SDF deformation remain open.



## Contact-constrained articulated dynamics — 2026-11-07

The next embodiment gate extends the articulated solver from joint-only generalized dynamics plus penalty-style root support to a coupled root-translation/joint system with impulse-based ground constraints.

- `chimera/biomechanics.py`: the generalized coordinate layout now includes world root translation (X/Y/Z) before all enabled joint rotations. Root translational Jacobian columns contribute to the same segment kinetic-energy mass matrix; root/joint inertial cross terms are retained. Gravity and Coriolis terms operate over the expanded coordinate vector. A requested root acceleration is converted through the full mass matrix into generalized force.
- Contact points are selected from the lower endpoint of each segment capsule. Their point Jacobians include root translation and all ancestor rotational coordinates.
- A projected Gauss-Seidel contact solver computes effective masses using `M^-1 J^T`, enforces non-negative unilateral normal impulses, and projects two tangential impulses onto a circular Coulomb friction cone (current coefficient 0.75). Contact impulses update root and joint velocities in the same generalized system; joint coordinates are reintegrated from constrained velocities.
- Residual penetration uses split positional stabilization after the velocity-level constraint solve. The contact model is non-restitutive and ground-plane-only.
- `tests/test_biomechanics.py`: added checks for root translational mass coupling, normal impact response, friction response, and the absence of ground friction while separated.
- `docs/ARTICULATED_BIOMECHANICS.md`: equations, assumptions, contact algorithm, and limitations updated.

**Model boundary:** root translation is now a generalized coordinate; root orientation/angular momentum are still not generalized coordinates. This does not yet implement self-collision, uneven terrain, grasping, multi-body contact, or calibrated friction. The solver remains a deterministic rigid-segment model with approximate anthropometric parameters, not a validated biological simulator.

**Verification:** GitHub Actions run [42438951673](https://github.com/foreverliverich/openworld/actions/runs/42438951673) passed all **103 standard-library tests** and the real Chromium/ANGLE/SwiftShader WebGL2 acceptance job. The test run covered the exact implementation and regression-test commit `cf3758acb6ecf40b79b2c611bd55ef9b17283e76`; the subsequent ledger-only documentation update does not alter executable code.


## Articulated capsule self-collision — 2026-11-07

The generalized contact solver now handles non-adjacent body-segment collisions, not only the ground plane.

- `chimera/biomechanics.py`: added robust closest-point calculations for finite 3D centerline segments, with capsule radii converted into signed separation gaps.
- The collision broad phase evaluates the 16-segment body pair set and excludes parent/child and grandparent/descendant pairs whose overlap represents a shared anatomical joint.
- Each self-contact uses the relative point Jacobian `J_body_B - J_body_A`; root translation cancels naturally for internal collisions.
- Contact normals and a stable orthogonal tangent basis are constructed per collision. The same projected Gauss-Seidel solver enforces non-negative normal impulses and Coulomb-bounded tangential impulses.
- Penetrating self-contacts receive a bounded separation-velocity target. Resulting impulses alter the same authoritative joint/root velocities and are integrated into the actual body state; no renderer-only collision response is used.
- `ArticulatedBodyState.neutral(skeleton)` now preserves the supplied skeleton version, enabling deterministic custom skeleton tests without weakening version validation.
- `tests/test_biomechanics.py`: added a crossing-limb acceptance case that begins with overlapping non-adjacent capsules and verifies the committed body geometry separates after the contact impulse.
- `docs/ARTICULATED_BIOMECHANICS.md`: documented the self-collision model and remaining root-rotation/terrain/grasp limitations.

**Model boundary:** this is rigid capsule self-collision for one articulated organism. It does not yet implement soft-tissue collision, broadphase spatial acceleration, inter-organism collision, grasping, or uneven terrain. The pair search is currently quadratic in the number of body segments and is suitable for the canonical 16-segment skeleton, not an unbounded particle system.

**Verification:** pending hosted CI for this branch. Do not treat this gate as closed until the standard-library suite and real Chromium/WebGL2 acceptance both pass.


## Root attitude and angular-momentum dynamics — 2026-11-08

The articulated generalized system now includes the root's six rigid-body velocity coordinates: world translation X/Y/Z and world angular velocity X/Y/Z, followed by all enabled joint rotations.

- `ArticulatedBodyState` now owns a normalized root orientation quaternion and world-frame root angular velocity. Existing serialized payloads default to identity orientation and zero angular velocity, preserving compatibility.
- Root orientation is composed into the entire forward-kinematic tree.
- Every rigid segment contributes root rotational Jacobian terms to the generalized mass matrix: point velocity from `omega × (COM - root)` and angular velocity about each world axis. Root rotation therefore couples to segment translation, segment inertia, joint motion and gravity.
- The finite-difference mass-matrix derivative perturbs root attitude on SO(3) using a world-axis quaternion increment; generalized velocity includes root angular velocity.
- Root orientation is integrated with a world-frame exponential-map quaternion update. Contact and self-collision impulses act on root angular velocity through the expanded generalized Jacobian.
- Root angular acceleration currently emerges from the coupled dynamics and contact impulses. There is not yet an external root torque/command interface.
- Tests added for world-space root rotation of the kinematic tree, positive rotational inertia and translation/rotation coupling, angular velocity integration, and state serialization round-trip.
- The browser acceptance test continues to validate the existing committed body pose UI. It does not yet provide direct root attitude controls.

**Model boundary:** this is quaternion attitude integration with world-frame generalized angular velocity, not a full Lie-group variational integrator. Independent rigid-body-engine comparisons, external root torque control, uneven terrain, manipulation contacts, soft-tissue collision, and calibrated anthropometry remain open.

**Verification:** pending hosted CI for this branch. Do not close this gate until all standard-library tests and real Chromium/WebGL2 acceptance pass.
