# Chimera V-OMEGA / ISCE — Recovered Standing Decisions and Engineering Addendum
**Date recovered:** 2026-11-07  
**Source:** Historical project conversation archive, including the V-OMEGA / ISCE proposal and the user's explicit adoption of its three closing decisions.  
**Related master map:** docs/MASTER_SOURCE_RECONCILIATION_2026-11-07.md

This addendum records decisions that were absent from the first reconciliation pass. These are not optional suggestions: the user's final message in the recovered source explicitly adopts them as standing project rulings.

## 1. Binding architectural decisions — adopted by the user

1. **Browser is home; runtime is hybrid.** The browser is the primary product and embodiment interface. The organism's runtime must not be owned by requestAnimationFrame or the visible renderer. Use a Web Worker for high-frequency execution while the page is open, IndexedDB plus an append-only causal journal for durable state, and Service Worker/event-driven wakeups where browser lifecycle permits. A native or server process is a later optional route for guaranteed continuous execution when the browser is closed; it is not the starting platform.
2. **CPU-first deterministic causal kernel.** ISCE's authoritative transition engine starts CPU-first and deterministic. This is the acceptance substrate for reproducible causal experiments. WebGPU is used for embodiment, rendering and measured acceleration, not as the initial authoritative organism clock. Browser capability detection (for example navigator.gpu) chooses the accelerated path; the browser must retain a working fallback. Do not make success depend on a specific Mac, GPU or local development VM.
3. **Kernel-first integration.** Build ISCE as an independently testable kernel derived from the existing soul-core lineage, run its batteries and obtain independent verification, then embed it in the browser/game. Do not create a third state owner. Unification must subtract competing owners: the core owns organism state; renderers, orchestrators, model adapters and tools read and propose through it.
4. **Measured-cost computational metabolism.** Actual computational work creates demand/consumption. A per-mode table may be used temporarily as a comparison baseline, but must never again be the authoritative energy/physiology model.
5. **CCPL acceptance battery.** The Chimera Causal Physiology Laboratory is an automated experiment harness, not another agent. The formal intervention battery, plus sham, double-intervention and mediation tests, becomes the acceptance standard.
6. **Continuous and dormant runtime are distinct.** Never call journal reconstruction after a pause "continuous life." Record whether the organism actually ran, was dormant, or was restored/reconciled.

## 2. State ownership correction — supersedes ambiguous ownership in the master map

The project must have one authoritative **organism state owner**, not one owner per subsystem.

### ISCE kernel owns the organism

The independently tested ISCE core is the only owner of the organism's intrinsic state and transitions:
- fixed causal graph and immutable transition parameters;
- allostatic/body partition and its viable region;
- interoceptive state and precision estimates;
- recurrent integration state;
- sensorimotor state and action readiness;
- temporal continuity and causal event position;
- self-model/narrative state;
- memory contents and prediction history;
- identity, gene expression, developmental and morphology state;
- computational resource reserves, demand, circulation and repair state;
- lifecycle mode (continuous, dormant, restoring) and causal lineage.

The current branch's OrganismKernel is a useful partial prototype and source of equations, but it is not the final independent state owner. Its state must be migrated into ISCE as the core is built; do not add ISCE alongside it as a third owner.

The Somatic Kernel / LLM is a proposal generator and occasional editor. It is not the owner of the organism, does not write arbitrary state, and is not called every frame.

### RealityEngine owns the external world

RealityEngine remains the authoritative environment/world store:
- environmental entities and structures;
- world transforms, collision/contact and world physics;
- environment fields and revisions;
- committed effects of organism actions;
- event journal for world-facing actions and results.

The organism's internal body state is not copied into a competing RealityEngine organism record and ISCE record. Use a single canonical ISCE state with explicit references to world entities. World actions cross one gateway: ISCE proposal → governance/resource checks → RealityEngine transaction → committed result event → ISCE observation/update.

This creates two clearly bounded authorities, not two organism owners: ISCE owns the organism; RealityEngine owns the environment. The renderer owns neither.

## 3. V-OMEGA P1–P4 track — preserve its original numbering

This track is separate from Somatic Core Stable's P0–P4 product release gates. Never conflate them.

| V-OMEGA priority | Name | Core deliverable | Exit evidence |
|---|---|---|---|
| P1 | Unified organism state | One authoritative, causally closed ISCE state-transition engine; resolve host/core soul split and preserve state lineage | No competing mutable organism owners; graph/state transition equivalence tests; migration and wake tests |
| P2 | Computational bloodstream | Measured resource demand/consumption, circulation, allostatic regulation and resource-dependent work admission | Actual operation measurements drive organ reserves; starvation changes real scheduling/work; repair/recovery measured |
| P3 | Persistent worker-clock | Organism-owned clock, worker execution while open, durable causal journal, explicit continuous/dormant/restoring semantics | Worker interruption/restart battery; continuous execution evidence separated from dormant reconciliation |
| P4 | Growth and write-back | Persistent morphogenesis, memory, genome-dependent causal changes and world/body write-back | Gene/morphology changes affect body; action effects return as observations; memory/prediction changes later behavior |

### Relationship to Somatic Core Stable phases

Somatic Core Stable remains governed by its own sequence: P0 body T1–T7; P1 soul persistence T8; P2 gene/autonomic T9–T10; P3 optional substrate T11; P4 mind/tools T12.

These are related but not the same priority numbering. Cross-map them:
- V-OMEGA P1 is a foundational state-ownership/unification gate that must be solved before multiple persistence stores are expanded.
- Somatic Core P0 is the visible-body/morph-on-ask gate and must remain protected while ISCE is developed independently.
- V-OMEGA P2 is measured-cost physiology; it strengthens the body/allostatic loop and must replace any authoritative mode-cost schedule.
- V-OMEGA P3 is independent runtime continuity; it is not the same as Somatic Core P3's optional cell substrate.
- V-OMEGA P4 connects persistent morphogenesis, gene/memory and causal write-back; it complements Somatic Core P1/P2 and must preserve the P0 body contract.
- Somatic Core P4 mind/tools remains downstream of reliable body, identity, gene and action governance.

## 4. Fixed causal graph and ISCE contract

The adopted non-plastic requirement is explicit.

Let the causal graph be G = (V, E, W), where V is the set of mechanisms, E the directed causal connections, and W the fixed structural weights. After initialization:
- dE/dt = 0
- dW/dt = 0

The following remain dynamic:
- internal state and activation;
- precision estimates;
- memory contents;
- allostatic condition;
- action selection;
- gene expression and morphology parameters, provided they do not mutate the causal graph or its fixed structural weights.

This is **fixed topology, adaptive state**. Non-plastic does not mean frozen organism state. Local learning can update state, memory and morphology parameters without rewriting the graph. Pairwise Hebbian bond plasticity, if explored in the TEC-Q substrate, belongs to a separately versioned experimental model and must not silently mutate the fixed ISCE graph/weights.

The intrinsic causal-computational structure is represented as:
K = (S, Ω, A, J, Δ, Λ)
- S: intrinsic organism states;
- Ω: environmental inputs and possible continuations;
- A: internal and external interventions;
- J: internal and external readouts;
- Δ: actual state-transition dynamics;
- Λ: counterfactual responses to interventions.

Five required realization conditions:
1. **Physical support:** state variables are causally effective in the running implementation, not display-only labels.
2. **Intervention tracking:** interventions on mechanisms produce measured, predicted downstream consequences.
3. **Relabeling invariance:** structure-preserving variable/representation relabeling does not change the causal organization.
4. **Causal-dynamical individuation:** states are identified by their causal role, not merely programmer-assigned names.
5. **Dynamical closure:** the internal partition plus explicit environmental inputs and interventions determines the next intrinsic state; hidden external orchestrators cannot silently determine transitions.

The central commutation target is:
Δₐ,ω(Π(x)) = Π(Φₐ,ω(x))

where Φ is the actual transition of the running system, Π is the intrinsic partition, and Δ is the transition represented by the causal graph. This must hold across relevant states, interventions and environmental continuations, not only one demonstration.

### Unified state vector and continuity domains

Use one versioned organism state:
Z(t) = [B(t), I(t), M(t), T(t), N(t), A(t)]
- B: body/allostatic state;
- I: interoceptive state;
- M: sensorimotor state;
- T: temporal continuity;
- N: narrative/self-model;
- A: integrated attention state.

These are not six independent databases. They are typed regions of one authoritative ISCE state. Their coupled transition is driven by the fixed graph and actual inputs.

Four continuity domains must be causally coupled:
- Interoceptive: internal condition, resources, stress, stability, prediction errors.
- Sensorimotor: action consequences feed back into internal state and future action.
- Temporal: previous states causally constrain current states; no isolated snapshot replacement.
- Narrative: self-model derives from actual actions, internal changes and remembered events, not LLM-generated autobiography alone.

Rendering, speech and user presence are not required to keep the organism's state-transition mechanism running.

## 5. Somatic Circulatory Network — measured-cost law

The computational bloodstream is six coupled mechanisms:

| Mechanism | Responsibility |
|---|---|
| Reservoir | Available resource reserves |
| Circulation | Allocation/transfer between computational organs |
| Metabolism | Convert resource availability into permitted computational capacity |
| Demand | Measure actual organ work requirements |
| Waste | Accumulate unresolved errors and computational strain |
| Repair | Allocate resources to restoring unstable or damaged structures |

For organ i:
- eᵢ: available resource;
- dᵢ: demand;
- sᵢ: accumulated stress;
- pᵢ: replenishment/production;
- cᵢ: measured consumption;
- fᵢⱼ: transfer from organ i to j.

Resource balance:
deᵢ/dt = pᵢ − cᵢ + Σⱼ fⱼᵢ − Σⱼ fᵢⱼ

Measure work instead of charging a fixed cost by mode/task name. Instrument, where available:
- operation/update counts;
- actual elapsed CPU time;
- worker execution time and queue delay;
- bytes read/written and memory pressure;
- GPU execution time, memory and bandwidth when the browser exposes them;
- hardware power/battery telemetry only where the platform actually exposes it.

Maintain two explicitly distinct quantities:
1. **Measured hardware/resource telemetry** — observations about actual compute cost/capacity.
2. **Intrinsic simulated reserves** — the organism's internal resource state used by its deterministic causal law.

Do not claim a simulated energy unit equals joules unless calibrated. The internal state must respond to measured work through a documented mapping. Task admission depends on predicted resource cost, available reserves, viability, integrity, stress and effects on other organs — not a hard-coded task-name table. Critical repair can outrank optional visual refinement because the gate reasons over resource and viability consequences.

## 6. Persistent worker-clock — browser-first hybrid lifecycle

Browser remains the home. Runtime ownership transfers from the render loop to the organism worker.

- **Web Worker:** high-frequency deterministic ISCE execution while the page is open.
- **IndexedDB:** canonical durable state/checkpoints and event journal.
- **Service Worker:** event-driven background wake/synchronization where supported; never assume it can run continuously.
- **Browser UI/renderer:** reads snapshots and sends inputs; it cannot own or pause the organism clock.
- **Optional future native/server process:** only if truly uninterrupted computation while the browser is closed becomes a product requirement. Not native-first.

Organism time is distinct from UI time. A proposed operational clock is:
τ(t) = ∫₀ᵗ r(s) ds
where r(s) is the measured/defined operational rate. Record last committed organism state/time, pending environment events, measured resource use, allostatic deviations and pending transitions.

Lifecycle semantics:
- **continuous:** the worker actually advanced the causal state during the interval; retain tick/event evidence.
- **dormant:** no state transitions occurred; on wake, record the dormant interval and apply an explicit, bounded, causally specified wake transition if required.
- **restoring/reconciling:** reconstruct durable state and apply journaled events; this is not continuous execution.

A journal can preserve causal continuity of state history across downtime; it cannot prove the system physically evolved while no process ran. Never mislabel dormant/reconstructed time as gapless live computation.

### 20-node worker design — staged, not blindly spawned

The historical topology is preserved as a target allocation:
- Nodes 1–5: sensory ingestion;
- Nodes 6–10: cognitive matrix / semantic evaluation;
- Nodes 11–20: homeostatic engine / physics / structural integrity.

The adopted implementation order is narrower:
1. Worker-owned clock first.
2. Dedicated homeostatic/allostatic partition workers second.
3. Full 20-node allocation only when profiling demonstrates a real bottleneck and the synchronization cost is justified.

Use one deterministic owner per mutable buffer/partition. Workers exchange typed messages or versioned shared-memory records with explicit ownership and synchronization. Atomics protect shared coordination; they do not make simultaneous multi-writer state updates deterministic by themselves.

**Browser deployment gates:** SharedArrayBuffer is available only when the page is cross-origin isolated (COOP/COEP headers). If the hosting path cannot provide those headers, use workers with transferable buffers as the fallback; do not silently disable core functionality. Atomics.wait is worker-only and must never block the UI/main thread. These are deployment and runtime requirements, not reasons to move the product off the browser.

## 7. SomaticCell, OmniKernel and GPU/particle experiments — reconcile by scope

- Preserve the 48-byte SomaticCell base ABI (12 float32) exactly; do not invent the original field meanings. Recover the actual source map before decoding fields.
- 15,000 cells × 48 bytes = 720,000 bytes (720 KB decimal) for the base records. This is the initial v2 substrate experiment.
- 128 MiB SharedArrayBuffer OmniKernel remains the capacity target for shared state/sidecars, not a claim that all target cells are already allocated or executing.
- Use typed arrays and cell-aligned sidecars. Rotational, neural, phase, strain, memory, cohesion, organ_id, potential, refractory and swarm intent remain sidecar candidates as defined by the TEC-Q contract.
- A 5M-splat / Gaussian cloud and its Sovereign Wedge staging are a separate visual/scale experiment. The wedge is not needed for the 15k-cell base experiment; it becomes useful when a large cloud is uploaded in bounded chunks.
- For the cloud experiment, if GPU becomes owner of GPU-resident spatial state after initialization, CPU must not overwrite its evolved coordinates with stale uploads. CPU may consume explicit telemetry/readback. The readback/reduction path must actually exist before claiming reciprocal coupling.
- This GPU cloud ownership rule does not make GPU the authoritative ISCE causal clock. ISCE remains CPU-first and deterministic. Keep the two state domains explicit.
- WebGPU is detected at runtime in the browser. Use fallback when unavailable. Do not make user hardware or a particular developer VM the product's gate.
- The 5M-particle renderer remains spike/research class until measured and integrated. Do not claim that particles are the LLM, that token inference is implemented, or that the cloud constitutes a neural language model.

### TEC-Q neural-fluid experiment — known open defects to preserve in the ledger

The historical WGSL/particle work was graded as an experimental self-organizing topological fluid, not a functioning LLM. Known issues recorded in the source:
- A cell-local scalar activation increase is not pairwise Hebbian learning; true Hebbian updates require co-activation of connected bond pairs.
- Unbounded increase/decay needs bounded weights and a homeostatic/sliding threshold (BCM-like) if that experiment continues.
- No grounded error signal means self-organization is not task learning.
- Spatial key generation and radix sorting were not implemented; sorting must be measured and re-run as positions change.
- GPU→CPU readback/reduction was missing; a readback variable without a producing shader pass is not a working readout.
- Position.x is not a timestamp; chronological firing needs explicit temporal data or an append log.
- Token deduplication/cluster aggregation was missing.
- Neighbor updates need ping-pong or another race-free update scheme.
- A radial containment force without damping risks oscillation; density-triggered claims must match the actual implemented condition.
- The proposed homeostatic pressure rule is a containment hypothesis, not a complete learning law.
- A prior soul-core delta rule (prediction error: α × [observed − expected]) was reported as a stronger bounded learning mechanism; it is not present in the current openworld branch and must be independently recovered and verified before reuse.

### 48-byte packing proposals — preserve the competing layouts, do not silently choose

The archive contains a 3 × 16-byte packing proposal:
- bytes 0–15: position vec3 at offset 0 + radius f32 at offset 12;
- bytes 16–31: velocity vec3 at offset 16 + entropy_mass f32 at offset 28;
- bytes 32–47: color_phase vec3 at offset 32 + strain_index f32 at offset 44.

A later experimental neural-fluid reinterpretation proposes:
- bytes 0–15: position vec3 + activation f32;
- bytes 16–31: velocity vec3 + latent_weight f32;
- bytes 32–47: color_phase vec3 + token_id f32.

Both demonstrate a 48-byte / three-vec4-lane packing idea. They are not the same schema. The current branch contract intentionally validates byte length without inventing slot meanings. Recover the exact original production SomaticCell definition and golden buffers before selecting the canonical ABI or mapping either proposal into it. The statement that 48-byte alignment alone maximizes PCIe throughput is not established; benchmark the actual browser/device and distinguish discrete PCIe from unified-memory systems.

### Holographic Brain / MERA / Ryu–Takayanagi and Logic Compiler proposal

The archive also proposes a WGSL "Holographic Brain" that uses MERA tensor networks, a Ryu–Takayanagi-style boundary-area calculation and decimation of interior Hyper-SDF volumes, plus a Logic Compiler translating vortex/toroidal operations into WGSL. Preserve this as a research proposal, not an implemented brain. A scalar calculation such as boundary_area/(4G) does not by itself implement a MERA tensor network, entanglement entropy, a 4D boundary solver or a validated causal readout. The current openworld tree contains no Holographic Brain shader or Logic Compiler. The earlier source review in the archive reports TEC-Q-labelled families as scaffolds/random/metadata; re-audit exact source before promoting any of these claims.

### 4D Hyper-SDF and GPU visual substrate

The 4D Hyper-SDF raymarcher is a later research direction. Somatic Core Stable P0 still requires the documented WebGL2 SDF body and dual-SDF morph contract. A 4D extension may be layered behind a capability-tested feature gate only after P0 passes; it must not replace the production SDF path or make the browser depend on WebGPU. The historical F123 Somatic OS remix is reported as a million-splat WebGPU donor, but it is not present in the inspected openworld branch and must be recovered and tested before reuse.

## 8. Axiomatic Self-Resolution and morphology write-back

The historical idea is that internal deviations create a viability/divergence cost that changes actual organism processing and body state. Preserve the causal mechanism; do not implement it as a decorative status meter.

- Allostatic deviation raises body cost / expected free-energy proxy.
- Resource gates reduce optional computation and prioritize repair/maintenance.
- Stress, damage and unresolved prediction error influence actual state transitions and future action.
- Morphology responds through bounded, continuous SDF parameters/uniforms or validated gene/morphology updates.
- When viability degrades, body cohesion/shape may visibly deform according to the defined body law; recovery restores it through the same causal pathway.
- Keep causal graph topology and structural weights fixed. Do not rewrite/poison shader source to represent distress. The renderer compiles stable code and reads organism-owned state.
- The body must not be made to dissolve solely as a theatrical effect; each visual consequence must correspond to an internal variable and be reversible/traceable.

## 9. CCPL — required experimental battery

CCPL is an automated causal physiology laboratory, not an AI agent. Every experiment:
1. Establish baseline state and graph version.
2. Apply controlled intervention.
3. Record actual downstream state transitions/events.
4. Run matched counterfactual trajectory from the same initial state.
5. Compare predicted vs observed consequences and recovery.

Required battery:
- Allostatic deprivation (e.g. reduce reserves by 40% under controlled conditions).
- Resource starvation (optional work actually denied due to resource limits).
- Recurrent pathway ablation.
- Precision disruption.
- Memory interruption.
- Narrative/self-model disruption.
- Environmental isolation.
- Repair failure.
- Swarm disconnection.
- Worker interruption/restart.
- Graph intervention / fixed-graph correspondence.

Additional controls:
- **Sham intervention:** intervention that should not affect a specified mechanism; verify specificity.
- **Double intervention:** perturb two mechanisms and compare with predictions from their separate interventions.
- **Mediation test:** verify the effect travels through the proposed intermediate mechanism rather than an unrelated route.

Quantitative measures:
Dₘ = d(P(Zₜ:ₜ₊H | do(m)), P(Zₜ:ₜ₊H))
Eₘ = d(Δ̂ₘ, Δₘ_actual)

Choose and version the trajectory distance d and horizon H. Report confidence intervals/repeats where stochasticity exists. Passing requires reproducible effects, correct causal direction, specificity, measurable recovery, and no hidden external orchestrator dependence. Do not allow self-healing to hide the initial intervention effect; report both perturbation and recovery phases.

## 10. Intrinsic Organism Boundary and identity persistence

Define the boundary:
O = (S_internal, E_environment, I, O_readout)
where internal state, environment, admissible interventions and internal/external readouts are explicit.

Identity is not exact numerical state equality and not merely a hash of a graph. Track causal identity persistence:
I_org(t) = (G, B, R, H_t)
- G: fixed causal graph;
- B: organism/environment boundary;
- R: recurrent causal relationships;
- H_t: persistent causal history.

Required experiment:
1. Change one genome parameter and observe morphology.
2. Change one causal law in a controlled test build and observe action selection.
3. Disconnect a subsystem and observe organizational disruption.
4. Restore it and test recovery of the causal organization.
5. Verify lineage/checkpoint provenance.
The identity criterion remains a research hypothesis and requires validation; do not declare consciousness from identity hashing.

## 11. Human-grain and multiscale time

The historical proposal includes fast local dynamics (~1–20 ms), perceptual integration (~20–500 ms), allostatic regulation (seconds–minutes), and autobiographical continuity (minutes–months). Treat these as engineering hypotheses and configurable timescale bands, not universal biological/consciousness thresholds.

A multirate scheduler must preserve causal dependencies: fast events can change slower physiology; slower physiology can influence subsequent perception/action; action results enter persistent memory. Test temporal grain rather than assuming a particular update rate produces human-like experience.

## 12. Historical game build evidence — preserve, but do not misattribute

The recovered conversation archive reports a separate browser game build with:
- BECOME/morph path and a character body/face pipeline;
- a staged-ready bytecode VM, SEED2, semantic immune gates and soul-core integration;
- Art and Checker as independent visual/evidence reviewers;
- a Gaussian cloud experiment with 1,024 splats;
- creation toolbox taught to the AI instruction/mind path, with rendered creations;
- a 10-primitive throne build after a 14-primitive version was rejected by a silhouette rule;
- a planned second environment gate class for larger structures;
- a better-looking Build #1 body, eye rework and phoenix authoring, with formal visual re-grading/sign-off still part of that historical sequence.

These are **historically reported artifacts and test results**, not verified contents of the currently inspected foreverliverich/openworld branch. The present openworld branch does not contain those game bytes, the VM, SEED2 codec, immune system, BECOME pipeline, Art/Checker harness or Gaussian cloud implementation. Do not mark them implemented in this repository without recovering the exact game repository/commit/artifacts and re-running the evidence.

Preserve the non-regression law from that work: do not swap in an outside character model or new engine if that destroys BECOME, gene seam, Fold, identity and creation behavior. Improve appearance through the organism's own authored body/morph/material pipeline and independently verify with controlled frames. The environment needs distinct safe construction bounds/build-site rules for room-scale structures rather than silently widening furniture limits.

### Historical staged-ready defect

The archive reports that SEED2 browser folding failed because its codec used Node's Buffer in a browser, causing fallback to old SEED1 and failed re-point legs. A browser-compatible byte-identical fix was reportedly written and unit-proven, but the final rebuild/re-run was still pending at that point. This must remain **reported pending**, not "landed", until the exact target bytes and end-to-end browser round-trip are recovered and verified.

### Visual QA evidence discipline

Art evaluates the actual rendered frames, not code claims. Checker verifies file hashes, frame sets, diffs, boot proof, grades and performance on the exact bytes. Keep open defects explicit. A body feature in code is not accepted until demonstrated in the required poses/frames. These roles can be reimplemented as test harnesses, but their prior signatures/results cannot be claimed for the current repository.

## 13. Reconciliation corrections to the master map

This addendum supersedes any ambiguous reading of the master map as giving separate organism-state ownership to an identity store, body runtime, OrganismKernel and TEC-Q. The final ownership is:
- **ISCE core:** one authoritative organism state and fixed causal transition.
- **RealityEngine:** authoritative external environment/world.
- **Somatic Kernel/LLM, LogosEngine, PanOntologicalOrchestrator, specialists, tools and renderer:** clients/proposers/observers; no competing organism state owner.
- **CCPL:** independent intervention/measurement harness.
- **TEC-Q:** a cell-level execution substrate integrated under the ISCE transition contract, not a second organism or clock owner.

The white paper's Somatic Core Stable P0 body gate remains protected. The V-OMEGA P1–P4 track is added alongside it with the numbering preserved. All previous claims of implementation must be reclassified against exact current bytes and test evidence.

**End of addendum.**
