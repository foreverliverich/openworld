# Chimera implementation ledger

Last verified repository branch: `tecq-causal-morphogenesis`
Repository: `foreverliverich/openworld`

This file is the durable engineering handoff. Update it in the same change as every material implementation or verification result. Do not use conversational summaries as the sole source of project status. The uploaded legacy source/transport audit is maintained in [docs/LEGACY_SOURCE_INTEGRATION_AUDIT.md](LEGACY_SOURCE_INTEGRATION_AUDIT.md). The master source reconciliation is [docs/MASTER_SOURCE_RECONCILIATION_2026-11-07.md](MASTER_SOURCE_RECONCILIATION_2026-11-07.md); the adopted ISCE/V-OMEGA standing decisions and corrections are [docs/ISCE_VOMEGA_STANDING_DECISIONS.md](ISCE_VOMEGA_STANDING_DECISIONS.md). Follow both documents and keep their separate P0–P4 numbering intact. The full historical source-to-code reconciliation is maintained in [docs/MASTER_SOURCE_RECONCILIATION_2026-11-07.md](MASTER_SOURCE_RECONCILIATION_2026-11-07.md); use it as the governing gap map and preserve its P0–P7 gates.

## System ownership invariants

1. `RealityEngine` and its SQLite database are the sole authority for persistent world entities, transforms, physics, fields, revisions and world events.
2. `OrganismKernel` is the sole owner of the persisted organism physiology/cognitive state currently implemented. Its state and local morphogenic field write are committed atomically through `RealityEngine`.
3. `AutonomousRuntime` owns fixed-step advancement. A browser renderer must never run a second physics simulation or mutate its own copy of world state.
4. `AutonomousWorldAgent` is currently a deterministic baseline policy. It is not a trained general intelligence.
5. LLM/planner outputs, future sensory systems and tool calls must propose typed actions. Governance and `RealityEngine` validate and commit them.
6. Preserve the TEC-Q ABI and seed distinctions. Do not invent a new 48-byte cell layout, merge the 1KB identity seed with SEED2 or the 4KB form genome, or call a compact Fold lossless without its complete external checkpoint.

## Verified code inventory

| Area | Source | Current implementation | Not yet implemented |
|---|---|---|---|
| World authority | `chimera/reality_engine.py` | SQLite WAL, revision checks, atomic structures, AABB collision/support, fixed-step gravity, scalar fields, snapshots, observations, hash-chained events | Articulated/deformable mechanics, fluid/terrain, complete deterministic replay |
| Physiology | `chimera/organism_kernel.py` | Persisted energy, stress, integrity, fatigue, memory-strength, curiosity, prediction error, confidence and allostatic error; two-way local field coupling | Vascular/metabolic transport, tissue repair mechanics, organ-specific physiology, body-derived strain/sensing |
| Agent | `chimera/autonomous_agent.py` | Deterministic shelter/workbench/rest/observe baseline | General goal generation, learned policy, sensory grounding, action selection through executable toolbox |
| Runtime | `chimera/runtime.py` | One clock, physics tick, agent step and observation | Event bus, continuous runtime service, scheduling/multiple organism lifecycle |
| Toolbox | `chimera/toolbox.py` | Six named domains; validated world mutations and inspection | Executable tool drivers, grasp/use/repair/build skills, autonomous capability discovery |
| TEC-Q contract | `chimera/tecq/contract.py`, `docs/tecq-architecture-contract.json` | Machine-readable architecture constraints and boundary tests | Bonded-cell solver, torsional mechanics, phase dynamics, swarm coupling, GPU/WGSL and 15k-cell execution |
| Browser/API integration | `chimera/http_server.py`, `web/index.html` | Added local HTTP API, same-process world/runtime/toolbox, revision-aware mutations, live Three.js projection of committed entities, physiology dashboard, event inspection and browser forms for all six toolbox domains | Anatomical rig, skin/tissue deformation, camera/sensor embodiment, GPU cell visualization, authentication for non-loopback exposure |
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

The browser's Three.js dependency is loaded from a CDN. The simulation, state, SQLite database and Python API are local. The visible objects are box-geometry projections of committed world entities. The current organism display is physiology telemetry, not a claim that a complete articulated animal body is implemented.

## Verification status

The new API integration test file is `tests/test_http_server.py`. The full suite is configured in `.github/workflows/chimera-tests.yml` to run on branch pushes and pull requests.

**Verified passing:** GitHub Actions run [42422927651](https://github.com/foreverliverich/openworld/actions/runs/42422927651) completed successfully for commit `35e19f74b855049a572f09b7641e2abcf6bd6c23`; the `unit-tests` job and `Run standard-library test suite` step both report success. The authoring environment could not clone the repository directly, so this verification is from the hosted CI runner, not a local execution.

## Next implementation queue (ordered by dependency)

### A. Make the browser application robust
- Confirm CI and fix API integration tests.
- Add a clean shutdown and database path handling.
- Add bounded event polling/deltas rather than repeatedly transferring every entity.
- Add explicit request validation and typed response schemas.
- Add browser tests for object creation, stale revision rejection, tick progression and reload persistence.

### B. Close perception/action connectivity
- Define versioned event envelopes with event ID, causation ID, correlation ID, actor, world revision, simulation time, source subsystem and typed payload.
- Add a sensory adapter that converts committed entity geometry, contacts and world fields into organism-relative sensory channels.
- Add a single action gateway: planner proposal -> capability/permission validation -> revision check -> RealityEngine commit -> observation -> prediction error.
- Route the six toolbox domains through that gateway. A capability label is not executable until it has a tested driver and observable effect.

### C. Replace prototype body representation with actual mechanics
- Establish a versioned anatomy/rig schema and body-part hierarchy.
- Add joint constraints and actuator limits; couple motor commands to physical body state.
- Derive proprioception, collision/strain and movement outcomes from the same mechanics.
- Feed those measurements back to organism physiology and memory.
- Keep renderer as a projection of body state; no display-only motion that disagrees with physics.

### D. Implement TEC-Q without violating the original contract
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
