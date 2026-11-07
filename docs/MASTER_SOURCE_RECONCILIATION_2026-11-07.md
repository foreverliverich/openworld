# Chimera / Somatic OS — Master Source-to-Implementation Reconciliation
**Reconciliation date:** 2026-11-07  
**Repository:** foreverliverich/openworld  
**Branch inspected:** tecq-causal-morphogenesis  
**Branch head inspected:** 12c74a3c52963f9fc9f35007f03d022bf8b58e66  
**Draft PR:** https://github.com/foreverliverich/openworld/pull/2

## 1. Executive result

The project is not one missing feature. It is several generations of architecture, code, research and product requirements that have not been joined by executable contracts.

Four source lineages are now reconciled:

1. **Somatic Core Stable — WHITEPAPER-2.md (2026-08-06):** the production body contract: language-to-GLSL SDF generation, continuous dual-SDF morphing, BioPBR/Diffusion, soft biological shading, visual refinement, persistence, gene spine, and deferred substrate/mind layers.
2. **TEC-Q / Somatic OS / OmniKernel:** bonded-cell physical-computational substrate: preserved 48-byte ABI, bond topology, real rotational/torsional mechanics, vortex-phase candidate, swarm intent, spatial hashing, four morphogenetic fields, nervous sidecars, multiscale coupling, workers and GPU execution.
3. **Engine of Latent Language 3.0 (2025-06 PDF) and embodied-consciousness Python sources:** multimodal latent fusion, continuous morphogenetic state, specialist/co-agent coordination, spatial composition, creative generation, memory, learning, embodiment and 3D field/mesh experiments.
4. **Chimera RealityEngine branch (2026-11):** coherent Python world/runtime spine with SQLite authority, transactions, events, scalar fields, minimal allostatic organism state, deterministic baseline agent, toolbox and local browser/API.

The current branch has a working world substrate and connected browser/API slice. It does **not** contain the Somatic Core Stable production body. It does **not** execute the TEC-Q solver. It does **not** connect the older multimodal/embodiment modules. Current visible world entities are primitive box projections; the organism physiology panel is telemetry, not an articulated animal.

**Principal reconciliation decision:** preserve one authoritative organism/world state and one production body contract. Use Somatic Core Stable SDF as the first reliable visible organism; keep RealityEngine as authoritative persistent world/action state; connect them through versioned causal interfaces. TEC-Q is the deeper cell substrate behind an opt-in integration gate until its CPU reference solver is stable and the SDF body acceptance suite remains green. Latent Language 3.0 supplies multimodal interpretation, spatial reasoning and specialist proposals; it does not own a competing world or overwrite the body directly.

This is a source reconciliation, not a claim that every historical source tree has been recovered. Missing dependencies must be recovered from full repository/history before their internals can be faithfully integrated.

## 2. Source inventory and disposition

### 2.1 Somatic Core Stable — WHITEPAPER-2.md

This is the strongest explicit production build law for the visible organism.

| Historical requirement | Current branch status | Required implementation |
|---|---|---|
| User intent returns structured package with mandatory non-empty GLSL sdfScript | Missing | Typed Somatic Kernel contract; reject empty/invalid packages |
| Previous and next SDF coexist; evolutionProgress in [0,1] blends every frame | Missing | Dual-SDF body state and frame-driven morph clock |
| WebGL2 full-screen raymarcher, normals, shading and camera framing | Missing | Production GLSLCanvas |
| Full BioPBR GLSL header | Missing | Implement all required helpers, not a stub |
| Diffusion Engine: four-octave noise, rotated offsets, latent domain warp, fur displacement | Missing | Implement and test in GLSL |
| Metamorphosis ops: taper, bulge, symmetry, finite repetition, bend, inflate, asymmetry, smooth union/subtraction | Missing | Stable documented GLSL vocabulary |
| Humanoid base SDF and material IDs 1–5 | Missing | Base anatomy and shared kernel/shader material contract |
| SSS, pores, subdermal flow and soft-skin roughness | Missing | Real shading paths, not metallic/plastic material |
| Kernel generates/refines structured morph packages; snapshot supports visual critique | Missing | Schema validation, history, refinement and visible errors |
| Failed shader compile falls back rather than black screen | Missing | Last-good program and safe fallback |
| Valid genesis SDF | Missing | Initial body with SSS material |
| Chat → kernel → engine apply → continuous visual blend | Missing | End-to-end morph path |
| Bounded auto-refinement with snapshots | Missing | Implement after base morph works |
| IndexedDB soul persistence, localStorage fallback | Missing | P1 after P0 |
| Gene spine 32 or 64 floats, documented indices and bounded local mutation | Missing | Choose/version layout; do not conflate with 1KB seed |
| Autonomic audio/pointer/idle micro-loop | Missing | Uniform/parameter updates, no shader compile every frame |
| Somatic OS particle substrate, Adam, Blelloch, binary checkpoints | Contract/research only | Optional flag-off substrate after P0; augment, never replace SDF |
| RIGHT PATH tools/agents | Partial in separate Python branch | Mind layer after body + soul + gene |
| T1–T7 and T8–T12 acceptance suites | Missing | Executable browser, shader and integration tests |

**Non-negotiable body contract C1–C5:**
- C1: user intent → model returns GLSL sdfScript and related fields.
- C2: old and new SDFs coexist; evolutionProgress blends continuously.
- C3: fragment shader contains complete metamorphosis + Diffusion + SSS/skin library.
- C4: kernel is required to use supported library functions.
- C5: no feature ships if it breaks morph-on-ask, blending, visible surface detail or fallback rendering.

**Part I order is binding:** types → BioPBR → genesis → body RealityEngine/evolution clock → Somatic Kernel → GLSLCanvas → chat → app shell → T1–T7. Do not put particles, agent orchestration or GPU-scale work ahead of a passing P0 body.

**Part II gates:** P0 = T1–T7; P1 = Soul persistence/T8; P2 = gene spine + autonomic/T9–T10; P3 = optional substrate/T11; P4 = mind/tools/T12. Particle-primary product requires a new versioned white paper and new success test.

### 2.2 TEC-Q / Somatic OS / OmniKernel

The branch contains chimera/tecq/contract.py and docs/tecq-architecture-contract.json. These are validation contracts, not a functioning solver.

| Requirement | Current status | Required executable implementation |
|---|---|---|
| 15,000 bonded-cell initial experiment | Not executed | Deterministic CPU reference solver and reproducible benchmark |
| 1,000,000-cell scale target | Goal only | Profiled GPU path with measured memory and throughput |
| 48-byte SomaticCell ABI (12 float32) | Byte-length validation only | Recover original slot map before decoding; never invent offsets |
| Versioned SoA sidecars | Alignment validation only | Allocate, update, checkpoint and test sidecars |
| Bond topology/rest lengths | Bond-list validation only | Force evaluation, bond lifecycle and stability tests |
| Spatial hashing/dynamic local neighborhoods | Missing solver | Deterministic neighbor construction; compare against brute force |
| True torsion/rotational DOFs | Quaternion normalization only | Quaternion integration, angular velocity, torque and constraints |
| Vortex candidate [1,2,4,8,7,5] | Schedule validation and controls listed | Implement as experiment; compare uniform, randomized, learned, sinusoidal and disabled controls |
| Swarm intent modulation | Sidecar name/contract only | Distributed local intent exchange with measurable effect |
| Energy, stress, memory, cohesion fields | RealityEngine has scalar lattice fields; no TEC-Q cell coupling | Sample/interpolate and update cell-local fields with explicit units/bounds |
| Nervous layer: organ_id, potential, activation, refractory | Required sidecars listed | Neural state transitions and refractory dynamics coupled to sensors/motors |
| Organ centers core/motor/sensor | Architectural requirement | Explicit organ assignment, interfaces and activation tests |
| 128 MiB SharedArrayBuffer OmniKernel | Contract constant/budget validation | Real allocation, worker protocol, capacity checks and lifecycle |
| 20 Web Workers | Goal only | Worker pool with deterministic partitioning, backpressure and failure recovery |
| WebGPU/WGSL | Not implemented | GPU kernels, dispatch, staging, device-loss recovery and CPU/GPU parity |
| Radix sorting/GPU staging | Not implemented | Measured implementation where neighbor workload justifies it |
| Fast mechanical, neural/phase, physiological, slow morphogenetic clocks | Not coupled | Explicit multirate scheduler with bounded synchronization/reproducibility |

**ABI rule:** preserve 48 bytes exactly. The base record remains opaque until the original field map is recovered. Extend through separately versioned, cell-aligned SoA buffers. Current contract sidecars name orientation_xyzw, angular_velocity_xyz, activation, phase, strain, memory, cohesion, organ_id, potential, refractory and swarm_intent. Never widen the base record.

**Physics rule:** torsion must be real rotational mechanics. A decorative sine wave or scalar rotation animation is not a substitute for quaternion orientation, angular velocity, torque and constraints.

**Scientific rule:** the six-state vortex sequence is a candidate schedule, not established physical law. Run control baselines and report measurable task outcomes. Do not infer biological truth, consciousness or sentience from a phase pattern.

**Memory rule:** 1M × 144 bytes = 144,000,000 bytes, exceeding 128 MiB (134,217,728 bytes) before scratch, staging, topology and checkpoints. The 48-byte base alone is 48 MB at 1M cells, but extended state must be budgeted separately. SharedArrayBuffer to WebGPU is not zero-copy; implement and measure explicit staging.

### 2.3 Engine of Latent Language 3.0

**Source:** Engine of Latent Language 3.0: Continuous Multimodal Morphogenetic AI Architecture PDF, uploaded 2025-06-11.

The source specifies:
- Unified text, image, audio and sensor latent representations.
- Original 1,760-dimensional subspace composition: language 768, emotion 128, cognition 256, memory 512, social 64, temporal 32; expanded with visual/sensory modalities.
- Continuous morphogenetic state evolution, including Neural ODE/recurrent and local field dynamics.
- 3D compositional intelligence: semantic descriptions become spatial structures/scenes.
- Coordinated specialist/co-agents with global workspace/synchronization.
- Memory store and creative generation for text, image, 3D scenes and behavior.
- Modular encoders/model choices such as Transformers, CLIP/ViT, audio encoders, PyTorch, NumPy/JAX, Chroma/FAISS, Blender/Unity and generative models.

**Current status:** the PDF is an architecture proposal, not executable implementation. ultimate_embodied_consciousness.py imports intended modules, but those module packages are not in the upload set. The current Chimera branch has no multimodal encoder, unified latent state, global workspace, specialist bus, creative generator or grounded spatial reasoning implementation.

**Integration rule:** modality encoders produce timestamped, confidence-bearing observations; latent dynamics produce versioned state/proposal objects; specialists produce typed proposals with provenance; the shared action gateway validates and commits. They do not create a second world database, mutate RealityEngine directly or bypass C1–C5. The 1,760-dimensional layout is historical, not permission to silently redefine ANIMA_DIMENSIONS=384 or any newer latent width. Every representation width must be versioned.

### 2.4 Uploaded Python/web source files (2025-06-10/11)

| Source | What is actually present | Reconciliation |
|---|---|---|
| consciousness_morphogenesis.py | NumPy 32×32×32 field, gradients/forces, density conversion, fractal geometry, crystallization and mesh extraction | Preserve as experimental field/mesh adapter. Not a bonded-cell solver, articulated body or RealityEngine owner. Define units/frame/coupling before connecting. |
| consciousness_shaping_engine.py | Flask-SocketIO loop around field/mesh generator; emits vertices/faces/formation_metrics | Preserve experiment; do not run as competing world authority. Wildcard CORS, hard-coded secret and 0.0.0.0 binding must be corrected before exposure. |
| ultimate_embodied_consciousness.py | Wrapper for latent language, morphogenesis, embodiment, memory, multimodal space and spatial memory; raw WebSocket server | Imports missing src.modules packages. Visualization output is activations + metrics, not geometry/parameters expected by original HTML. Its main() starts ConsciousnessOrchestrator directly, not this class's .run(); do not assume its WebSocket starts. |
| app.py | Flask + Flask-SocketIO app; chat, consciousness/avatar events, thought stream and system initialization | Depends on missing modules.* and src.modules.*. Logging opens logs/app.log before logs directory is created in main path. Port configurable; sample says 7002, code default 3000. Avatar /avatar contract unverified because AvatarServer source is missing. |
| run.py | FastAPI app, raw WebSocket /ws, status/error endpoints and manager | Imports missing module tree. Module-level manager schedules asyncio tasks outside a running event loop: startup defect. Requires config.json, but only example config supplied. |
| index.html (legacy) | Three.js visualizer expects geometry.data.attributes, index and parameters | Connects raw WebSocket at 8765. Does not match Flask-SocketIO at 8002, FastAPI /ws, or UltimateEmbodiedConsciousness activations/metrics. Not a working client for those producers. |
| config.example.json | Server, Ollama, consciousness, orchestration, latent-space and storage settings | Server port 7002 and WebSocket port 7002 collide if both configured services start. Example is not config.json required by run.py. |
| config.py | ANIMA_DIMENSIONS = 384 | Separate constant, not JSON runtime loader. Keep dimension explicit/versioned. |
| Brain.py | Small PyTorch MLP | Standalone network; no demonstrated training/inference integration. |
| train.py | PyTorch distributed loop, DDP, CUDA AMP, W&B, dataset/config/optimization imports | Requires missing src.data, src.modules, src.utils and GPU/NCCL launch. Not runnable from supplied files. |
| sys_monitor.py | psutil system metrics | Standalone diagnostics; no event bridge/adaptation integration. |
| intents.json | Static greeting/time/date/search/play map | Not a goal planner, embodied policy or tool driver. |
| requirements.txt | websockets, numpy, openai, sentence-transformers, torch, aiosqlite, psutil | Omits visible Flask, Flask-SocketIO, Flask-CORS, FastAPI, Uvicorn, W&B, PyYAML and tqdm imports. Not a complete dependency manifest. |
| ai-desktop-agent.code-workspace | Workspace settings | Does not supply missing source packages. |
| Contributors.md | Minimal contributor note | No implementation specification identified. |

Uploaded top-level Python files passed syntax compilation in the earlier audit. That proves parseability only, not importability, dependency completeness, startup, protocol compatibility or functional behavior.

### 2.5 Current openworld branch

| Module | Verified behavior | Missing / limitation |
|---|---|---|
| chimera/reality_engine.py | SQLite WAL authority; entities; revisions; optimistic concurrency; transactions; AABB collision/support; fixed-step gravity/contact; four scalar field lattice; snapshots/observations; hash-chained event journal | No articulated/deformable body, soft tissue, fluid, terrain, neural or cell solver; full deterministic replay not established |
| chimera/organism_kernel.py | Persisted energy, stress, integrity, fatigue, memory_strength, curiosity, prediction_error, confidence, allostatic_error, age and goal; field-to-physiology and physiology-to-field coupling in atomic world commit | No body-derived strain, organ physiology, transport, sensory transduction, tissue repair or actual memory retrieval/learning model |
| chimera/autonomous_agent.py | Deterministic policy: build shelter, build workbench, rest/regulate, observe and record outcome | Not general planner/learned agent; fixed blueprints and hand-coded novelty proxy; no real sensing, locomotion, grasping or toolbox execution |
| chimera/runtime.py | One fixed-step owner: physics → agent step → observation; async run loop | No event bus, multirate scheduler, organism lifecycle manager or causal replay |
| chimera/toolbox.py | Six domains: Body Forge, World Builder, Tool Fabricator, Life Generator, Movement Lab, Research Lab; validated creation/inspection/movement through RealityEngine | Body/tool/life outputs mostly metadata/prototypes; no articulated body, executable driver, autonomous construction skill or real research-agent loop |
| chimera/http_server.py | Local HTTP API; shared runtime/world/toolbox; lock-protected requests; health/state/events/tick/tool routes | Not full product UI; no WebGL2 SDF body, WebGPU solver, remote auth or streaming sensory/action contract |
| web/index.html | Three.js projection of committed entities, physiology display, six toolbox domains | Box entities are projections; physiology is not animal anatomy; Three.js from CDN; no morph-on-language SDF pipeline |
| chimera/tecq/contract.py | Contracts for 1KB identity seed, Fold descriptor, 48-byte ABI validation, sidecar alignment, bond-edge validation, quaternion normalization, phase schedule, memory budget | Validation only; no cell allocation/solver/force integration/phase update/swarm/nervous/GPU compute |
| docs/TECQ-1KB-SEED-FOLD-BLUEPRINT.md | Architectural separation and checkpoint rules | Not original codecs or runtime persistence |
| Tests | Python unit/API/contract tests and GitHub Actions | Do not test SDF rendering, shader compilation, browser morph, visual quality, TEC-Q mechanics, multimodal integration or closed-loop embodiment |

## 3. One coherent target architecture

The project needs one organism with cooperating layers, not multiple applications each claiming to own the consciousness or body.

### 3.1 Authority and state ownership

1. **RealityEngine:** sole durable world authority — entities, transforms, contacts, terrain/world revision, action commits, event journal and snapshots.
2. **Organism Identity Store:** sole durable identity/genome/soul authority — identity seed, versioned genome, SDF body scripts/alleles, persona, lineage and reset semantics. It references world checkpoints; it does not duplicate world authority.
3. **Somatic Body Runtime:** sole authoritative visible-body representation for v1 — current/previous SDF, morphology package, material parameters and morph clock. Renderer is a projection, not a separate body database.
4. **TEC-Q Substrate:** owns cell-level physical-computational state only when enabled — base ABI, topology, sidecars, fields, nervous state, phase and swarm. It exchanges versioned coupling records with body/runtime; it does not become a competing world database.
5. **OrganismKernel / Allostatic Controller:** owns physiological setpoints, energy/stress/fatigue/integrity, regulation and homeostatic constraints. Inputs must eventually be measured from body/world events, not fabricated constants.
6. **Perception / Latent Language:** owns encoders, modality alignment, latent trajectories and interpretation proposals. It does not commit world mutations.
7. **Cognition / Specialists / Agent:** owns goals, plans, predictions, episodic/procedural learning and proposals. It cannot bypass governance.
8. **Governance / Action Gateway:** only route from proposal to effect: validate identity/capability/permission, resource/safety constraints and expected revision; commit through RealityEngine; record result and causation.
9. **Renderer / Game UI:** reads versioned snapshots/interpolation; never owns physics, physiology or persistent identity.

### 3.2 Causal loop — must become an executable end-to-end test

world + body state → sensors/contact/proprioception/audio/vision → sensory transduction + confidence + timestamps → latent fusion/nervous activity/local reflexes → goals + prediction + action proposal → governance/capability/resource gate → body actuators/TEC-Q mechanics/world action → committed RealityEngine event + body result → observation of actual result → prediction error + episodic/procedural memory → allostatic update + gene/development update → next state/renderer snapshot.

No link is complete merely because a class or API route exists. Each edge needs an integration test demonstrating measurable cause and effect.

### 3.3 Canonical event envelope

Implement a versioned event contract before adding disconnected services. Minimum fields:
- schema_version, event_id, event_type
- tick, simulation_time, wall_time
- world_revision_before, world_revision_after
- actor_id, source_subsystem, target_subsystem
- correlation_id, causation_id, optional parent_event_id
- capabilities/authorization context and action provenance
- typed payload with coordinate frame, units, confidence and validity interval where relevant
- deterministic sequence/order key

The event log must support replay of accepted transitions and attribution of outcomes. Rejected proposals are inspectable but cannot mutate world state. LLM calls are asynchronous proposals, never authoritative tick owners.

## 4. Identity, genome, morphology, memory and Fold — keep distinct

| Artifact | Meaning | Size/format constraint | Owns |
|---|---|---|---|
| 1KB Identity Seed | Compact generative identity anchor | Exactly 1,024 bytes; versioned and hashed | Identity continuity / initial generative bias |
| Developmental Form Genome | Expanded developmental parameter genome | 1,024 float32 values = 4,096 bytes where this project contract applies | Body-plan and developmental controls |
| Somatic Core Gene Spine | Local morphology control vector | White paper allows 32 or 64 floats; choose/version one; 64 float32 = 256 bytes | Local SDF template parameters / allele weights |
| SEED2 | Separate versioned compact encoding | Preserve original codec; per-form gene segments 1–32 values, form IDs 0–5 | Form-segment encoding; not identity seed replacement |
| Learned Morphology | Current/previous SDF, material package, allele/parameter values | Hash and version generated packages | Current visible body form |
| Developmental State | Cell topology, tissue/organ development, morphogenetic history | Full versioned checkpoint domains | How organism reached current structure |
| Temporary Condition | Energy, stress, fatigue, damage, activation, refractory, pose | Runtime state; checkpoint according to Fold mode | Transient physiology/body condition |
| Memory | Episodic events, procedural policy, semantic associations, prediction history | Separate schemas and retention policy | Experience and learned behavior |
| Lineage | Parent identity, seed derivation, mutations, generation, provenance | Immutable lineage records | Ancestry/reproducibility |
| Fold | Portable identity/reconstruction descriptor or lossless checkpoint locator | Lossless requires external content-addressed complete checkpoint | Transport, preservation and wake/reconstruction |

**Never merge:** 1KB identity seed ≠ 4KB developmental genome ≠ 32/64-float gene spine ≠ SEED2 ≠ Fold checkpoint. A compact Fold token is not arbitrary-state compression. Lossless Fold requires cell ABI, cell extensions, bond topology, torsion, fields, nervous state, swarm, sensors/readout, physiology, development and world revision, plus hashes/integrity.

## 5. Conflict resolutions and non-regression rules

| Apparent conflict | Resolution |
|---|---|
| WHITEPAPER says WebGL2 SDF first; TEC-Q wants WebGPU/cells | WebGL2 SDF is P0 visible-body path. TEC-Q CPU solver then WebGPU are gated substrate work. TEC-Q may be developed in isolation but cannot replace SDF or block morph-on-ask. |
| Python RealityEngine vs white paper TypeScript RealityEngine | Keep one durable world authority. Python RealityEngine is current candidate because it owns SQLite transactions/runtime. Build TypeScript WebGL2 body/client connected through typed API; no second TypeScript world database. Authority migration requires explicit plan/parity tests. |
| Legacy Flask/FastAPI/Socket.IO/raw WebSocket vs new local HTTP server | One production server lifecycle. Preserve legacy modules as adapters/research; migrate capabilities behind one API/event contract. |
| NumPy 32³ field vs TEC-Q cell fields | Treat as field-generation experiment/adapter. Define units, spatial frame, interpolation and coupling before connecting. Not the TEC-Q solver. |
| 1,760-dim Latent Language vs ANIMA_DIMENSIONS=384 vs newer latent widths | Version each representation and provide explicit encoders/projections. Never silently reshape/concatenate incompatible spaces. |
| White paper 32/64 gene vector vs 1,024-float developmental genome | Separate artifacts with explicit expansion/mapping. |
| 48-byte ABI vs larger rotational/neural state | Preserve ABI; use versioned SoA sidecars; recover original field map before decoding base slots. |
| Vortex schedule vs established physics | Experimental candidate only; compare baselines and publish results. |
| Consciousness terminology vs evidence | Preserve project terminology, describe implementation operationally. No sentience, biological consciousness or quantum claims without evidence. |
| Feature expansion vs body contract | C1–C5/T1–T7 are regression gates. If a new layer breaks the creature, it is not shippable. |

## 6. Implementation roadmap and exit criteria

### P0 — Somatic Core Stable production body (highest product priority)

Implement the actual browser creature path:
- Typed MorphPackage, MaterialDescriptor, SomaticBodyState, WorldMetrics, message/error schemas.
- Complete BioPBR GLSL: noise/hash/fbm, metamorphosis ops, Diffusion Engine, humanoid base, material IDs, SSS, pores, subdermal flow and roughness.
- Valid genesis SDF.
- WebGL2 raymarch canvas with dual-SDF A/B compilation, stable signature, u_evolution, camera, normals, shading and last-good fallback.
- Somatic Kernel returns schema-validated structured JSON; mandatory valid non-empty sdfScript; model output is validated before executable shader use.
- Chat request updates old/new body and visibly blends; errors appear in UI.
- Snapshot/refine loop capped at 10 iterations; snapshot supplied for critique; no LLM call every frame.
- Browser acceptance tests T1–T7.

**P0 exit:** repeatedly request distinct morphologies (including “become a wolf”); observe non-black-screen continuous SDF blend with diffusion detail and soft material response; intentionally break GLSL and verify fallback. Retain screenshot/video, compile logs and test output. No marketing counts.

### P1 — Soul persistence

- IndexedDB SomaticCoreSoul/store soul; localStorage fallback somatic-core-soul-v1.
- Save version, timestamps, label/persona, current and previous SDF, material/color, capped messages, optional gene and morph progress.
- Debounced asynchronous save after successful morph/refine.
- Boot validates/hydrates same creature with completed morph progress.
- Explicit reset seed only clears identity/body checkpoint.
- T8 reload round-trip verifies same SDF hash and label.

### P2 — Gene spine and autonomic loop

- Choose either 32- or 64-float version; document every index and clamp values.
- Implement one expansion strategy first: parameter expansion into stable SDF template (white paper preference) OR allele blending.
- Keep free-form SDF generation for hard morphology changes.
- Local bounded mutation with a real fitness gate.
- Audio/pointer/idle reflexes drive uniforms/parameters, not shader recompilation every frame.
- T9 local offline gene step; T10 hard ask still produces visible morph.

### P3 — TEC-Q CPU reference substrate

- Recover original ABI field map and original source before assigning meanings.
- Allocate exactly 48-byte base cells; extensions in sidecars.
- Start at 15,000 cells, deterministic seed/order.
- Implement bond topology/forces, spatial hashing, quaternion orientation, angular velocity/torque, stress/strain, energy/memory/cohesion, nervous activation/potential/refractory, organ IDs and swarm intent.
- Implement all four fields with units and boundary conditions.
- Implement candidate vortex schedule and six required controls.
- Multirate stepping: mechanical substep; neural/phase update; physiology; slow development/topology.
- Add stability, finite-value, energy/constraint, topology, determinism, ablation and task tests.
- Bridge SDF surface/body to substrate through explicit sampling/projection; no hidden second body state.
- T11 flag-off exactly preserves P0; flag-on does not break morph, skin or fallback.

### P4 — TEC-Q GPU and scale

- 128 MiB SAB target with actual allocation/bounds checks; 20-worker target with measured partitioning.
- WGSL compute and explicit staging; CPU/GPU parity tests.
- Spatial sort/radix only where measured profiling supports it.
- Budget base cells, sidecars, bonds, scratch, staging, readback and checkpoints.
- Profile 15k, intermediate scale, then 1M. Report throughput, latency, GPU/CPU memory, worker overhead and numeric drift.
- Device-loss/restart and checkpoint recovery.
- Never claim 1M support from constants or allocation intent.

### P5 — Embodied sensorimotor and allostatic closure

- Versioned anatomy/rig schema, hierarchical body parts, joints, limits, muscle/actuator model and contact.
- Sensor channels: vision/raycast, touch/contact, proprioception, audio and internal physiology; each with units, coordinate frame, timestamp and confidence.
- Sensor → transduction → nervous/goal/action → governance → actuator → physics → contact/proprioception → prediction error → memory/physiology.
- Body-derived strain/damage; actual energy expenditure; resource-limited action gate; rest/recovery/repair.
- Organ centers core/motor/sensor; local reflex plus long-range coordination.
- Closed-loop tasks: stand/balance, reach/grasp, locomote, avoid obstacle, manipulate object, respond to damage/energy depletion, recover/rest. Define measurable thresholds and deterministic scenes.
- Renderer depicts authoritative rig/cell state; no decorative animation that disagrees with mechanics.

### P6 — Latent Language 3.0 / cognition / creative intelligence

- Recover missing original module trees/model configs.
- Implement modality adapters and versioned latent spaces.
- Global workspace/specialist coordination with bounded async tasks and provenance.
- Spatial reasoning maps descriptions to grounded entities/relations/blueprints.
- Memory is source- and outcome-grounded; predictions link proposed action to observed consequence.
- Learning updates only from attributable experience and has held-out regression tasks.
- Creative generators output assets/scene proposals through validated import paths.
- LLM outputs remain proposals; action gateway commits only validated typed actions.

### P7 — Tool ecosystem / game progression / Fold

Make all six toolbox domains executable:
- Body Forge: actual SDF/anatomy package and validated body transition.
- World Builder: transactional construction with physics/support.
- Tool Fabricator: real tool item plus tested driver/interaction.
- Life Generator: actual organism initialization with identity, body, physiology, nervous and memory state.
- Movement Lab: actuator/rig mechanics, locomotion and measured results.
- Research Lab: evidence retrieval, controlled experiments, causal/event inspection.

Build game progression on real capabilities: exploration, construction, crafting, tool use, organism evolution and interactions. Implement original 1KB/SEED2 codecs only after source recovery and golden test vectors. Implement full checkpoint/hash manifest, portable Fold and lossless Fold with all domains. T12 verifies identity survives sleep/restore while morph-on-ask remains intact.

## 7. Required test architecture

1. **Unit:** schemas, numeric bounds, SDF transforms, GLSL helpers, genome expansion, codec golden vectors, ABI/sidecars, quaternion/torque, field updates.
2. **Deterministic simulation:** same seed + inputs → same events/state within declared tolerance.
3. **Integration:** kernel → package → body state → shader compile → visible blend; physiology ↔ fields; cell solver ↔ body adapter; sensor → action → world event → observation.
4. **Browser/E2E:** boot, morph, refine, fallback, persistence, reset, controls, no console/WebGL errors.
5. **Scientific controls:** phase schedule vs baselines, torsion on/off, swarm on/off, field coupling on/off, spatial hash vs brute force.
6. **Performance:** frame time, shader compile time, CPU/GPU memory, worker overhead, cell throughput, event payload size.
7. **Regression:** P0 T1–T7 run on every renderer, kernel, body-state, substrate-bridge or UI change.

Static string assertions do not prove WebGL execution. A test passes only with observed output and retained evidence.

## 8. First implementation queue

1. Create apps/somatic-core (or equivalent) with Vite/React/TypeScript/WebGL2, typed contracts, BioPBR, genesis SDF, dual-SDF GLSLCanvas, Somatic Kernel adapter and T1–T7 tests. Keep secrets out of client bundles.
2. Add versioned MorphPackage endpoint/adapter to existing Python service. Python RealityEngine remains sole persistent world authority; SDF package and identity store have explicit ownership.
3. Add Soul persistence T8 and gene/autonomic T9–T10 only after P0 is green.
4. Implement TEC-Q CPU reference in chimera/tecq/solver behind feature flag; no GPU first. Preserve original ABI bytes and test sidecars.
5. Add canonical causal event envelope and single action gateway before integrating cognition/tools.
6. Recover missing source trees and codecs from all accessible repository branches/history before replacing old modules. Record exact commit/path/hash and preserve source lineage.
7. Add browser E2E/performance evidence; update this document and IMPLEMENTATION_LEDGER with each verified result.

## 9. Missing-source recovery list

These source roots are imported by uploaded files but were not present in the supplied upload set or inspected branch tree. Absence here does not prove they never existed elsewhere.

- modules/
- src/modules/
- src/utils/
- src/data/
- templates/
- static/
- AvatarServer implementation and /avatar protocol
- original Somatic OS 6 / New 2 / RIGHT PATH 47 source trees referenced by WHITEPAPER-2
- original 1KB identity seed encoder/decoder, SEED2 codec, Fold codec and golden test vectors
- original 48-byte SomaticCell field map and production WGSL/worker sources
- original Somatic Core Stable source implementation, if separate from WHITEPAPER-2

Before asking for re-upload, inspect all repository branches, tags, commits, releases, archives, connected project files and Library sources. Do not replace missing modules with invented interfaces.

## 10. Operational truth at audit time

- Branch head: 12c74a3c52963f9fc9f35007f03d022bf8b58e66.
- PR #2 was open, draft and reported mergeable/clean at inspection. This is a snapshot, not a future-state guarantee.
- Previously recorded Actions successes: run 42422927651 for commit 35e19f74b855049a572f09b7641e2abcf6bd6c23; run 42423064491 for commit 157b5043e803b6061cd8ed36e83182475a40d813. They do not prove the current head passed a fresh run or that WebGL morph behavior works.
- Uploaded Python syntax compilation does not prove missing imports resolve.
- No full browser/WebGL manual run is claimed.
- No biological sentience, consciousness, quantum behavior or biological equivalence is claimed.

## 11. Change-control law

Every PR states: source document/section implemented; owning module and state ownership; invariants preserved; tests and exact evidence; remaining gaps/unverified items; and regression status for prior acceptance tests.

No “complete”, “living”, “sentient”, “million cells”, “full embodiment” or “lossless Fold” claim without corresponding measured implementation and tests. Project terminology can remain ambitious; implementation status must remain literal.

**End of reconciliation.**
