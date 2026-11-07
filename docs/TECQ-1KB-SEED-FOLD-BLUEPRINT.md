# Chimera: 1KB Identity Seed × TEC-Q × Fold
## Canonical engineering blueprint and gap-resolution record

**Status:** architecture contract v1.0, committed on branch `tecq-causal-morphogenesis`  
**Purpose:** preserve the original ambition while preventing incompatible formats, untestable claims, duplicated state, and rebuild-from-memory drift.

This document is the governing integration contract for the compact identity seed, TEC-Q (Topological Entanglement Cognition), the Fold/SEED2 lifecycle, Somatic OS, and RealityEngine. It is not a claim that the complete organism is already implemented. Every item is marked as an existing artifact, a verified mechanism, a contract decision, a target, or an open implementation task.

---

## 0. Governing thesis

The system is one persistent computational organism with three complementary lifecycle mechanisms:

1. **1KB identity seed — genesis and identity.** A compact, versioned starting artifact. It establishes the organism's generative identity and reconstruction inputs. Its byte layout is opaque until the authoritative seed codec is recovered; no developer may invent offsets or reinterpret unknown bytes.
2. **TEC-Q — embodied computation and development.** A spatial, bonded, physically coupled computational substrate. Its mechanics, torsion, topology, local neighborhoods, phase, swarm intent, morphogenetic fields, nervous dynamics, sensors, memory, and readout must participate in one coupled update.
3. **Fold / SEED2 — continuity and portability.** A versioned serialization/handoff layer that preserves identity and selected lived/developmental state. A compact token can identify or regenerate large state; it cannot losslessly contain arbitrary high-entropy state that exceeds its information capacity.

Somatic OS supplies physiological constraints and regulation. RealityEngine owns authoritative world state, revisioning, durable transactions, and event history. Rendering is a projection, not a second authority.

### The lifecycle

```text
1KB identity seed + versioned developmental recipe
                    |
                    v
             Genesis / reconstruction
                    |
                    v
     TEC-Q body + Somatic OS + RealityEngine
                    |
       perception / action / computation
                    |
       adaptation / structural memory
                    |
       validated developmental checkpoint
                    |
                    v
              Fold / SEED2
                    |
      portable identity + checkpoint reference
                    |
                    v
        wake / validate / reconstruct
                    |
                    +------> continued development
```

**Non-negotiable:** do not collapse the seed, genome, SEED2 fold, TEC-Q checkpoint, and world snapshot into one vaguely named "soul blob." They have different jobs, different sizes, and different compatibility rules.

---

## 1. Vocabulary and data ownership

| Artifact | Owns | Does not own |
|---|---|---|
| 1KB identity seed | compact identity/genesis bytes, seed version, seed digest | full body state, all memories, all world entities |
| Developmental genome / form genes | generative parameters and heritable morphology | current runtime state or complete lived history |
| SEED2 | its documented identity/tissue/mutation/skill/immune/drive/gene/law fields and its own compatibility rules | undocumented TEC-Q arrays or a 15,000-cell checkpoint |
| TEC-Q checkpoint | exact computational-body state needed to resume or reproduce TEC-Q | authoritative external world state unless explicitly included |
| RealityEngine snapshot | world entities, fields, simulation time and revision | private model weights or unrecorded GPU buffers |
| Fold descriptor | codec/version, seed, hashes, artifact references, reconstruction recipe | the payload bytes behind a URI |
| Somatic OS state | energy, stress, integrity, fatigue, repair, allostatic state and interoceptive signals | proof of biological metabolism |
| Renderer state | visual projection and interpolation | authority to mutate organism/world state |

### Names are not interchangeable

The audit corpus contains at least three distinct gene-like representations:

- A compact identity seed described by the project as 1 KB. Its exact authoritative binary schema was not found in the files reviewed here.
- A **1,024-float form-seed vector**, which is 4,096 bytes at float32. The audit explicitly rejects describing this as entropy compression or a 500,000:1 compression result. It is generative parameterization.
- The SEED2 v3 excerpt carries per-form kept genes of 1–32 quantized values on a 1/255 grid, for supported form IDs 0–5. That is not the same format as the 1,024-float vector.

**Decision:** preserve all three as separate versioned artifacts until a documented adapter proves a conversion. No implicit cast, truncation, or rename is allowed.

---

## 2. What the source corpus actually establishes

### 2.1 Existing / reported mechanisms

The project handoff and audit describe these as present in source or previously measured:

- SEED2 codec with dual-read support for versions 2 and 3, checksums, canonical base64url, optional extension segments, kept genes, and learned laws.
- A SEED2 VM and a separate mutation dictionary / bytecode data dependency.
- A 48-byte SomaticCell physiology ABI.
- COOP/COEP headers, worker-side Atomics, and GPU-resident buffers in a separate implementation corpus.
- BodyController rollback and scar recording as the required gate for AI-authored form/shader changes.
- A 1,024-float form-seed vector.
- A RealityEngine implementation in this repository with SQLite WAL, transactions, world revisions, event hashing, primitive box physics, four scalar fields, observations, snapshots, and an organism kernel that couples physiology to local fields.

The SEED2 handoff reports measured tests and round trips. Those figures are **source-reported**, not independently rerun or verified in this repository. The actual codec's dependencies and original tests must be imported from their authoritative source before production integration.

### 2.2 Not established by the reviewed source

- The exact 1KB identity-seed byte layout and its canonical decoder.
- The original TEC-Q implementation source and exact 48-byte SomaticCell field offsets.
- A working end-to-end integration of the 1KB seed, TEC-Q, SEED2, Somatic OS and RealityEngine.
- A deformable bonded-cell solver, quaternion torsion solver, or complete TEC-Q GPU compute pipeline in the current `openworld` repository.
- A demonstrated 15,000-cell integrated TEC-Q experiment or a measured 1-million-cell runtime.
- A proof that a 117-character SEED2 string can contain an arbitrary 15,000-cell physical-computational state.
- Biological consciousness, sentience, quantum computation, or matter creation.

No implementation or benchmark may be labelled complete solely because its name appears in a document or because an earlier handoff reports it.

---

## 3. Hard problems, impossibility boundaries, and resolutions

### 3.1 Can a 1KB seed contain the whole organism?

**No, not if "whole organism" means arbitrary exact runtime state.** A 1,024-byte payload has 8,192 bits before metadata. It cannot losslessly encode an unconstrained, much larger state space.

**Resolution — generative seed, not magic compression:**

- Keep the identity seed at a maximum of 1,024 payload bytes under its own versioned codec.
- Treat it as a compact identity and developmental starting point.
- Use a versioned deterministic reconstruction recipe and deterministic seed for reproducible genesis.
- Store learned genome deltas and large state in separate artifacts.
- Use hashes and content-addressed references in the fold descriptor.
- If a state cannot be regenerated exactly, it must be stored in a lossless checkpoint or explicitly marked as lossy.

The executable contract in `chimera/tecq/contract.py` enforces the 1,024-byte maximum without guessing the internal layout.

### 3.2 Can a tiny Fold string preserve 15,000 bonded cells exactly?

**Not by itself, unless the state is highly constrained and regenerable.** A hash proves identity of bytes; it does not reconstruct bytes. A pointer identifies an artifact; it does not contain the artifact.

**Resolution — two explicit Fold modes:**

- `portable`: carries identity seed, codec/version, deterministic reconstruction recipe and seed. It promises reproducible regeneration only to the extent that the recipe and inputs are deterministic and complete.
- `lossless`: carries the identity seed plus a content-addressed external checkpoint. The checkpoint must include all required TEC-Q domains: base cell ABI, sidecars, bond topology, torsion, fields, nervous state, swarm, sensors/readout, physiology, developmental state and world revision.

The fold descriptor refuses a lossless claim when the checkpoint or any required state domain is missing. The compact token is a handoff manifest, not an entropy-compression miracle.

### 3.3 Is the 1KB seed the 1,024-float genome?

No. At float32, 1,024 values occupy 4,096 bytes. The audit explicitly says this vector is a form-generation parameterization, not entropy compression. The SEED2 excerpt has yet another smaller per-form gene segment.

**Resolution:** three separately versioned formats and explicit adapters. Never truncate the 4KB vector into 1KB or claim the 1KB seed already stores it.

### 3.4 Does 128MB support one million 144-byte GPU cells?

No. The arithmetic is:

- 1,000,000 × 144 bytes = 144,000,000 bytes (about 137.3 MiB).
- 128 MiB = 134,217,728 bytes.
- The extended state exceeds a 128 MiB pool by 9,782,272 bytes (about 9.33 MiB), before alignment, staging, sort buffers, or transient allocations.

At the 48-byte base ABI alone, one million cells are 48,000,000 bytes. At 15,000 cells, the 144-byte extended state is 2,160,000 bytes.

**Resolution:**

- Keep the 128 MiB SharedArrayBuffer OmniKernel target separate from GPU allocations.
- Treat the 128 MiB GPU pool as a budget to validate, not an assumed capacity.
- Preserve the 1-million-cell scale target.
- Either reduce/partition the GPU state, use multiple buffers/passes, or require a larger device budget. Measure actual adapter limits and reserve space for sort/staging/working buffers.
- The executable memory-budget function reports the overage instead of silently claiming a fit.

### 3.5 Is SharedArrayBuffer zero-copy with WebGPU?

The reviewed audit explicitly rejects the zero-copy GPU-from-SAB claim. SharedArrayBuffer is CPU shared memory; a WebGPU GPUBuffer is a distinct resource with its own mapping and synchronization rules.

**Resolution:** use an explicit transfer boundary: worker-owned shared staging data → validated/batched copy → GPU buffer upload or mapped staging buffer → compute passes → readback only where required. Optimize copies by batching and minimizing readback; do not call it zero-copy.

COOP/COEP remains a deployment requirement for cross-origin-isolated SharedArrayBuffer use. Atomics waiting belongs in workers, not the browser main thread.

### 3.6 What is the status of the vortex sequence [1,2,4,8,7,5]?

The audit explicitly rejects "vortex math" as a validated physical law. That does **not** require deleting the sequence from TEC-Q.

**Resolution:** preserve [1,2,4,8,7,5] as the canonical candidate six-state phase schedule. It may influence phase gating or update order only through a mathematically defined, dimensionally valid implementation. It is a hypothesis to test, not a proof of exotic arithmetic, non-Euclidean physics, or superior cognition.

Required controls:
- canonical six-state sequence;
- uniform six-state cycle;
- randomized six-state schedule;
- learned schedule;
- sinusoidal phase coupling;
- phase coupling disabled.

Compare memory capacity, nonlinear processing, separation, robustness, task performance, stability and resource cost under identical inputs and initial conditions. If it loses, report the result; retain the sequence in the experiment record without pretending it won.

### 3.7 How can the 48-byte ABI gain torsion and nervous state without breaking old code?

The source confirms a 48-byte SomaticCell ABI, but the exact field offsets were not available in the audited source excerpt. Reinterpreting or widening it would risk silent corruption.

**Resolution:**

- Preserve every existing 48-byte record byte-for-byte.
- Treat the base ABI as opaque until its canonical field map and version/hash are recovered.
- Put quaternion orientation, angular velocity, activation, phase, strain, memory, cohesion, organ ID, potential, refractory state and swarm intent in aligned sidecar Structure-of-Arrays buffers.
- Every sidecar must have exactly one entry per cell and a versioned schema.
- Introduce a new ABI only through a deliberate version migration with dual-read, migration tests and rollback.

The new contract validates the 48-byte record count and sidecar alignment; it does not invent the base ABI's undocumented slot meanings.

### 3.8 How do we prevent the subsystems becoming disconnected feature lists?

Every simulation tick must be a coupled transaction with an explicit dependency order:

1. Read authoritative world revision and committed observations.
2. Update sensors and nervous input potentials.
3. Discover local neighbors using spatial hashing plus bond topology.
4. Evaluate bond mechanics, rotational/torsional error and constraints.
5. Propagate phase and swarm intent through permitted links.
6. Update energy, stress, memory and cohesion fields.
7. Apply allostatic constraints to permitted actions and plasticity.
8. Compute local activation and memory updates.
9. Evaluate candidate topology changes behind causal intervention and rollback gates.
10. Compute readout and task metrics.
11. Commit a versioned state delta and event to the authoritative world/checkpoint boundary.
12. Render only the committed revision.

Mechanical force coupling and signal coupling are separate parameter families. A physical bond does not automatically imply a communication edge.

### 3.9 How do we prove structural memory is real?

A structure changing after input is not sufficient.

**Resolution:** run paired, same-seed/same-input interventions:

- intact topology;
- sham intervention;
- selected bond/region ablation;
- restored bond/region;
- randomized topology with matched degree/weight;
- no-plasticity baseline.

For task k, estimate contribution using a loss difference such as:

[
I_{ij}^{(k)} = mathbb{E}[L_k(\text{ablated }ij)-L_k(\text{control})]
]

Use sampled edge groups and hierarchical screening at 15k cells; do not attempt exhaustive single-edge ablation across every edge at scale. Preserve a structure as learned memory only when capability gains survive held-out trials and a later wake/reconstruction test.

### 3.10 How do we stop adaptation destroying identity or learned capability?

**Resolution:** separate identity invariants from mutable phenotype and acquired memory.

- Identity seed is immutable unless an explicit identity migration is authorized.
- Genome/form genes mutate under bounded, versioned rules.
- Topology and physical parameters may adapt under stability and resource constraints.
- Acquired memory is checkpointed separately from inherited developmental parameters.
- Candidate changes are evaluated in a developmental branch.
- Promote only after benchmark and regression gates pass.
- Keep the last-known-good phenotype and rollback/scar record.
- Fold records lineage and checkpoint hashes so a descendant is not confused with the same individual state.

The same organism can preserve identity while changing morphology; a descendant can inherit developmental information without inheriting every personal episode. Those are separate semantics.

---

## 4. TEC-Q subsystem contract

TEC-Q remains the core embodied computational substrate. The following are retained, not discarded:

- 3D bonded-cell substrate.
- Initial experimental target: 15,000 cells.
- Long-range scale target: 1,000,000 cells.
- Existing 48-byte SomaticCell ABI.
- Torsional rotational degrees of freedom.
- Canonical candidate phase schedule [1,2,4,8,7,5].
- Swarm intent modulation and distributed coordination.
- Spatial hashing and dynamic local neighborhoods.
- Morphogenetic fields: energy, stress, memory, cohesion.
- Recursive emergence and distributed activation/memory.
- Nervous layer: organ_id, potential, activation, refractory.
- Organ centers: core, motor, sensor.
- 128 MiB SharedArrayBuffer OmniKernel target.
- 20-worker pool target, subject to hardware benchmarking.
- COOP/COEP isolation and worker-safe Atomics.
- GPU compute, WGSL, radix sorting and staged buffer transfer.

### 4.1 Cell state decomposition

**Base ABI:** 48 bytes per cell, preserved exactly and treated as opaque until its canonical source is recovered.

**Sidecar state:** separate SoA buffers for quaternion orientation, angular velocity, activation, phase, strain, memory, cohesion, organ identity, nervous potential/refractory state, and swarm intent.

**Bond state:** canonical edge list, rest geometry, stiffness/damping, mechanical constraints, rotational rest relation and communication permissions.

**Field state:** energy, stress, memory and cohesion; fields influence local dynamics and are influenced by committed organism activity.

No conflation of material mass, latent weight, strain, token IDs, or organ IDs into the wrong numeric slot. Every semantic field has a declared dtype, unit, range, and version.

### 4.2 Torsion is actual rotational dynamics

Use normalized quaternions and relative orientation error, not a decorative sinusoid. A candidate bond energy is:

[
e_{ij}^{\theta}=\operatorname{Log}(q_i^{-1}q_jq_{ij}^{* -1})
]

[
E_{ij}^{\theta}=\frac{1}{2}(e_{ij}^{\theta})^T K_{ij}^{\theta}e_{ij}^{\theta}
]

Torque follows from the derivative of total rotational energy with respect to orientation. Integrate angular velocity and quaternion orientation with a stable, tested scheme. Define units and sign conventions. Test conservation/dissipation behavior under isolated conditions before coupling to plasticity.

The Python contract currently normalizes and validates quaternions; it is not yet a torsion solver.

### 4.3 Multi-timescale coupling

Retain distinct but coupled timescales:

- Fast: collision, vibration, bond strain, torsional motion.
- Intermediate: activation, phase, local memory, swarm messages.
- Physiological: energy, fatigue, stress, repair and action gating.
- Slow: topology, sensor placement, morphology and developmental branching.

The solver must state its integrator, timestep, substeps, stiffness bounds and stability criteria. Do not use arbitrary Euler updates for stiff mechanical modes. A slower developmental controller may propose changes, but those changes enter through validated topology transactions.

### 4.4 Spatial hashing

Use spatial bins for candidate proximity, then filter by distance, bond membership, relative orientation, velocity, strain, material/organ boundaries and communication permissions. GPU radix sorting is an implementation target. Keep a deterministic CPU reference for correctness tests; it is not a substitute for the GPU implementation.

### 4.5 Swarm intent

Swarm intent is not merely a neighbor average. It is a distributed signal with:
- source organ and source cell;
- intent class / goal channel;
- magnitude and confidence;
- phase and timestamp;
- permitted propagation edges;
- resource and stress constraints;
- decay, refractory and conflict resolution.

It must influence local activation and candidate actions, while being constrained by fields, nervous state, physical feasibility and allostasis.

### 4.6 Morphogenetic fields

Energy, stress, memory and cohesion are first-class state variables. They must:
- influence cell and bond dynamics;
- receive contributions from activity, strain, damage, learning and repair;
- have defined diffusion, decay, units, bounds and boundary conditions;
- be observable and checkpointable;
- remain causally connected to organism behavior.

The current RealityEngine fields do not deform geometry. That remains an explicit integration task, not a completed capability.

---

## 5. Fold and reconstruction protocol

### 5.1 Preserve the existing SEED2 contract

The supplied SEED2 excerpt describes versioned core bytes, dual-read v2/v3 behavior, checksums, canonical base64url, optional name/program/hardening/gene/law extension segments, and loud refusal for malformed or unrepresentable values.

Do not silently change:
- frozen species identity;
- mutation dictionary ordering;
- version-specific mutation bit width;
- extension flag meanings or segment ordering;
- gene quantization grid;
- law channel order [CRAFT, FORM, NERVE, VIGIL, WARMTH];
- old-reader compatibility behavior.

The excerpt imports `bytecode-data.js` and `dictionary-data.js`. Those exact dependencies are part of the codec and must travel with it. Do not copy a partial codec into Chimera and claim the Fold is integrated.

### 5.2 TEC-Q fold is a higher-level envelope

The new `FoldDescriptor` contract is an envelope around the seed and checkpoint artifacts. It does not mutate SEED2's bytes.

For a lossless wake, the checkpoint must include:
- 48-byte base cell ABI bytes;
- all sidecar arrays;
- bond graph and rest constraints;
- quaternion/torsional state;
- field buffers;
- nervous state and organ mapping;
- swarm state and pending messages;
- sensor configuration and readout configuration;
- physiological state;
- developmental genome/topology and last-good version;
- authoritative world revision and reconstruction engine/schema versions.

External artifacts are identified by URI, byte length and SHA-256. Verify hashes before loading. A missing or mismatched artifact is a failed wake, not a silent reset.

### 5.3 Wake sequence

1. Parse descriptor and validate format/version.
2. Validate seed length and digest.
3. Resolve checkpoint artifacts and verify every digest.
4. Validate engine, codec, ABI and shader compatibility.
5. Reconstruct seed/genome state in an isolated staging organism.
6. Load TEC-Q state and verify cell counts, sidecar alignment, topology references and numeric finiteness.
7. Reconstruct RealityEngine state or bind to its declared revision.
8. Run invariants and a short deterministic calibration trial.
9. Compare expected state digests / tolerance metrics.
10. Promote staging state to active organism only if every gate passes.
11. Otherwise preserve current live state and emit a structured wake failure with the exact failed gate.

### 5.4 Identity and continuity

Record separate digests for:
- identity seed;
- developmental genome;
- phenotype/topology;
- acquired memory;
- full TEC-Q checkpoint;
- world snapshot;
- codec and engine versions.

A matching identity digest is not proof of matching lived state. A matching checkpoint digest is not proof of identical future behavior if engine/shader versions differ. The wake report must state which dimensions of continuity passed.

---

## 6. Runtime architecture and authority

RealityEngine remains the authority for committed world state. TEC-Q becomes a versioned subsystem whose outputs are proposed and committed through an adapter. It must not create a second RealityEngine, second world clock, or renderer-owned truth.

### Ownership boundaries

- **Seed service:** parse/validate identity seed and expose typed identity metadata only after schema is known.
- **Genome service:** versioned gene vectors, bounds, mutation and developmental recipe.
- **TEC-Q runtime:** cell/bond/field/nervous/swarm dynamics and computational readout.
- **Somatic OS:** physiological constraints, action permissions, fatigue, repair and interoception.
- **RealityEngine:** authoritative world entities, fields, revision, transactions and event journal.
- **Fold service:** checkpoint manifest, artifact integrity, compatibility and wake orchestration.
- **Mind/LLM:** proposes structured goals, plans, critiques or bounded genome deltas; never directly writes GPU buffers or bypasses validation.
- **Renderer:** subscribes to committed snapshots/deltas and interpolates visuals.

### Coupled tick transaction

A TEC-Q tick consumes a specific world revision and emits a typed delta. If the world revision changes before commit, reject or re-plan. The physics, physiology, topology and memory changes must be committed as one coherent versioned transition or staged so partial commits cannot masquerade as a complete tick.

The current RealityEngine event journal is tamper-evident but its README explicitly says it is not yet a replay-complete engine. Full deterministic replay requires logging all nondeterministic inputs, RNG states, solver versions, shader versions, timestep/substeps and state deltas.

---

## 7. Causal learning, computational phenotype and evaluation

Define the computational phenotype as:

[
\mathcal P_t=(G_t,\Theta_t,S_t,I_t,M_t)
]

where:
- (G_t): topology and bonds;
- (Theta_t): mechanical, torsional, phase and coupling parameters;
- (S_t): sensors and readout;
- (I_t): input encoding;
- (M_t): persistent and short-term memory state.

A capability is established only through a complete path:

[
\text{input encoding}
\rightarrow \text{TEC-Q evolution}
\rightarrow \text{sensor/readout}
\rightarrow \text{task output}
\rightarrow \text{measured score}
\rightarrow \text{adaptation}
]

### Required metrics

- Task accuracy / reward and held-out generalization.
- Linear and nonlinear memory capacity.
- Nonlinear information-processing capacity.
- Kernel rank / separation and generalization rank.
- Robustness to noise, damage and perturbation.
- Causal attribution accuracy for ablated structures.
- Adaptation time and energy/resource cost.
- Capability retention after structural change and after Fold/wake.
- Numerical stability, constraint violation and recovery/rollback rate.
- Sensor/readout information accessibility versus a full-state oracle diagnostic.

### Baselines

At minimum compare:
- fixed random reservoir;
- fixed topology TEC-Q;
- adaptive topology without torsion;
- torsion without phase schedule;
- canonical phase schedule versus all controls in §3.6;
- swarm intent disabled versus enabled;
- no-plasticity versus plasticity;
- fixed sensors versus sensor morphogenesis;
- CPU reference versus GPU implementation;
- intact versus ablated/sham interventions.

A full-state oracle is a diagnostic ceiling, not the deployed readout. If the oracle performs well and the real sensors do not, the information exists in the simulation but is inaccessible to the organism.

### Causal adaptation gate

Do not strengthen a connection because it correlates with activity alone. Candidate topology changes require:
1. controlled intervention or a justified sampled approximation;
2. matched sham/control;
3. held-out task improvement;
4. stability and allostatic safety;
5. capability-retention check;
6. rollback path and scar record;
7. a checkpoint that records the exact phenotype and benchmark.

---

## 8. Resource, worker and GPU execution contracts

- 128 MiB SharedArrayBuffer target is a CPU shared-memory budget.
- GPU buffers are separately budgeted against actual adapter/device limits.
- The 20-worker target is a pool target, not a mandate to create 20 busy workers on every device. Measure throughput, contention and latency; configure the pool.
- SharedArrayBuffer use requires cross-origin isolation headers (COOP/COEP).
- Atomics wait/sleep belongs in workers; keep the main thread responsive.
- GPU data transfer is explicit. Do not advertise zero-copy SAB-to-GPU.
- WGSL kernels require bounds checks, finite-state checks, deterministic initialization and explicit dispatch sizing.
- Radix sort requires separate scratch/scan buffers and a memory budget.
- GPU device loss must restore from the last validated checkpoint and replay only deterministic logged inputs.
- Do not allocate the full million-cell state until the measured memory report fits with headroom.

---

## 9. Uploaded-code audit: concrete integration gaps

The uploaded Python/HTML corpus is not currently a single runnable application:

1. `app.py` imports many `src.modules.*` packages that are not present in the uploaded file set. It configures a FileHandler for `logs/app.log` before ensuring the logs directory exists. It also creates a Flask/SocketIO runtime.
2. `run.py` is a separate FastAPI runtime. It requires `config.json` and imports multiple `modules.*` packages absent from the uploaded file set. The upload contains `config.example.json`, not the required live config.
3. `train.py` imports missing project modules plus `wandb`, `yaml` and `tqdm`, which are not listed in the uploaded requirements. It unconditionally initializes NCCL distributed training and assumes CUDA/local-rank environment variables. Cleanup is not protected by a top-level `finally`.
4. `ultimate_embodied_consciousness.py` imports multiple missing `src.modules.*` packages. Its fusion reduces heterogeneous subspaces to scalar means; that is not a dimensionally coherent unified representation and cannot substantiate the claimed cognition.
5. `consciousness_morphogenesis.py` creates procedural scalar fields and mesh data, but its "consciousness-to-matter" and "quantum coherence" naming does not mean it creates physical matter or performs quantum computation. It injects random noise, so deterministic replay requires an explicit RNG state.
6. `consciousness_shaping_engine.py` contains a frontend placeholder for an initial consciousness form. It is a visualization/prototype surface, not evidence of an integrated embodied substrate.
7. The uploaded requirements do not include the Flask/FastAPI/SocketIO stack used by the two app entry points, and the source tree containing their imported modules is absent from the upload.
8. The 48-byte ABI and `globalGenome.ts` source were not included in the uploaded files. The audit says the globalGenome allocation was 16 MB rather than the stated 128 MB and half the particle pool was unseeded; source must be recovered before patching.
9. The current `openworld` repository README says its RealityEngine is not yet integrated into the uploaded Flask/FastAPI app. Its current physics is box-body gravity/contact, not deformable tissue or torsion. Its event journal is not replay-complete.

**Resolution:** do not merge the Flask and FastAPI entry points by guesswork. First recover the missing source tree, choose one canonical application/runtime, normalize dependency and configuration management, then integrate TEC-Q behind a tested adapter. The current RealityEngine remains the world authority.

---

## 10. Repository implementation status

### Committed by this blueprint change

- `chimera/tecq/contract.py`: executable validation contracts for opaque 1KB identity payloads, portable/lossless fold descriptors, checkpoint domains, 48-byte cell buffer length, SoA sidecar alignment, bond edge integrity, quaternion normalization, phase-schedule preservation, and resource budgeting.
- `chimera/tecq/__init__.py`: public exports.
- `tests/test_tecq_contract.py`: unit tests for the contract invariants.

### Not yet implemented by this change

- The canonical 1KB seed decoder and field schema.
- Import of the original SEED2 codec and its exact bytecode/mutation dependencies.
- Actual TEC-Q cell/bond/torsion/field/nervous/swarm solver.
- GPU WGSL kernels and radix sorting.
- 15,000-cell integrated benchmark.
- Full checkpoint storage, hashing, wake and rollback.
- Sensor morphogenesis and causal topology-learning loop.
- Replay-complete RealityEngine journal.
- Flask/FastAPI runtime consolidation.

The contract tests have been added but must be run in the repository environment before they can be called passing. No runtime or GPU performance claims are made here.

---

## 11. Ordered build plan and exit gates

### Gate 0 — recover canonical formats and source
- Recover exact 1KB seed source, schema, tests and compatibility history.
- Recover 48-byte SomaticCell field map and version/hash.
- Recover original TEC-Q code, `globalGenome.ts`, WGSL shaders, worker code and benchmark harness.
- Recover complete SEED2 codec, `bytecode-data.js`, `dictionary-data.js`, VM spec and test suite.
- Inventory duplicate app entry points and missing imports.

**Exit:** all source artifacts are identified, checksummed, versioned and mapped to owners. No guessed schema.

### Gate 1 — canonical data contracts
- Implement seed decoder/encoder against recovered authoritative spec.
- Import SEED2 unchanged behind an adapter.
- Implement versioned TEC-Q checkpoint schema and content-addressed artifacts.
- Keep 48-byte ABI immutable; add sidecars.
- Validate migrations and malformed/corrupt inputs.

**Exit:** round-trip, compatibility, corruption, unknown-extension and migration tests pass.

### Gate 2 — deterministic CPU reference
- Implement cell state, bond graph, spatial hash, quaternion torsion, phase, swarm, fields and nervous layer.
- Couple physiological state and action gating.
- Log RNG, solver version, timestep and all state transitions.
- Add finite-state, stability, energy/dissipation and topology invariant tests.

**Exit:** deterministic 15,000-cell reference experiment runs, checkpoints and wakes with declared tolerance.

### Gate 3 — GPU implementation
- Port the validated kernels to WGSL.
- Implement spatial binning/radix sort and bounded neighbor lists.
- Implement staged SAB-to-GPU transfer.
- Add device limits, memory headroom, device-loss recovery and CPU/GPU parity tests.

**Exit:** measured 15,000-cell GPU run passes parity and resource gates. No 1M claim yet.

### Gate 4 — causal computation and adaptation
- Define tasks and real sensor/readout paths.
- Establish conventional reservoir and fixed-topology baselines.
- Run phase, torsion, swarm, sensor and topology ablations.
- Promote only structures that improve held-out capability without unacceptable instability or forgetting.

**Exit:** benchmark report includes controls, negative results, causal attribution and reproducible seeds.

### Gate 5 — Fold/wake and lineage
- Checkpoint all required domains.
- Create portable and lossless fold descriptors.
- Verify content hashes and compatibility on wake.
- Run same-host and cross-host reconstruction tests.
- Separate identity continuity, memory continuity, phenotype continuity and lineage.

**Exit:** lossless wake matches the declared state digest; portable wake reports regeneration equivalence and its tolerances honestly.

### Gate 6 — organism integration
- Connect TEC-Q adapter to RealityEngine revisions and Somatic OS constraints.
- Make all mutations pass validation, transactional commit, rollback and scar recording.
- Consolidate application runtime and frontend subscriptions.

**Exit:** end-to-end organism can perceive, act, adapt, checkpoint, wake and continue without split-brain state.

---

## 12. Permanent engineering laws

1. Never delete an original TEC-Q subsystem to make a demo easier.
2. Never turn a target into a measured result by repeating it in documentation.
3. Never call a hash, URI, or seed a lossless checkpoint.
4. Never call 1,024 float32 genes a 1KB payload.
5. Never widen the 48-byte ABI silently.
6. Never call SAB-to-GPU transfer zero-copy.
7. Never treat the vortex phase sequence as established physics; preserve it as an experimental candidate.
8. Never claim computation without encoding, substrate evolution, accessible readout and task measurement.
9. Never promote a structural adaptation without causal controls, held-out capability and rollback.
10. Never let renderer, LLM, or frontend become a competing world-state authority.
11. Never fold unknown data away silently; reject, preserve as an extension, or explicitly report loss.
12. Every new mechanism requires code, tests, benchmark, schema/version and a documented owner.

**This document is the integration law. New research can extend it through versioned amendments; it must not silently overwrite existing contracts.**
