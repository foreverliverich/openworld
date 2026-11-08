# Research gate: energy-priced structural learning

Status: **hypothesis and preregistered experiment design; no result claimed**.

## The narrow question

Can a spatially distributed computational organism learn a task while paying an explicit local resource cost for (1) creating or strengthening connections and (2) maintaining them, and does this improve the trade-off between predictive performance, compute expenditure, and recovery compared with strong controls?

This is narrower than "energy controls growth". Developmental Graph Cellular Automata (DGCA) already grow task-useful reservoir topologies. Spatial ATP-gradient models already show how clustered sources and sinks can create nonuniform energy fields. A 2026 review argues that durable plasticity itself creates a local write-throughput bottleneck. The open intersection to test is whether local energy availability should allocate structural writes, and whether the resulting topology reduces future operating cost enough to repay its construction and maintenance.

## Evidence and prior-art boundary

1. Barandiaran & Stovold (2026), *Growing Echo State Networks through Graph-Based Morphogenesis with Developmental Graph Cellular Automata*, Artificial Life, DOI: 10.1162/ARTL.a.486. DGCA can grow reservoirs from graph seeds and outperform typical reservoirs on reported tasks. Therefore graph morphogenesis and task-useful reservoir growth are prior art, not a Chimera novelty claim. https://doi.org/10.1162/ARTL.a.486
2. *Estimating physical conditions supporting gradients of ATP concentration in the eukaryotic cell* (Biophysical Journal, 2026), DOI: 10.1016/j.bpj.2025.06.016. Reaction-diffusion modelling finds that clustered ATP sources/sinks can support spatial concentration differences despite diffusion. This supports testing local resource fields, not assuming a uniform global battery. https://doi.org/10.1016/j.bpj.2025.06.016
3. Lemma et al. (2026), *Patterns of mitochondrial ATP predict tissue folding*, Science Advances 12, eaee6175, DOI: 10.1126/sciadv.aee6175. Spatial ATP/mitochondrial patterns precede and predict tissue folding in the studied systems. This is biological motivation, not evidence that a software graph should obey the same mechanism. https://doi.org/10.1126/sciadv.aee6175
4. Xu, Shen & Yu (2026), *The write-cost bottleneck: energy constraints on continual learning in brains and machines*, Cognitive Neurodynamics, DOI: 10.1007/s11571-026-10508-1. This review frames durable plasticity as a resource-intensive write process. It motivates explicitly pricing topology changes; its quantitative biological estimates must not be transferred to software energy units. https://doi.org/10.1007/s11571-026-10508-1

## Minimal model to test

Use local reserve e_i, local production p_i, consumption c_i, and conservative transport J_ji:

    e_i(t+1) = clip[e_i(t) + p_i - c_i
                    + sum_j J_ji - sum_j J_ij, 0, capacity_i]

A candidate structural write a (add, strengthen, weaken, or remove an edge) has an explicit write cost C_write(a), plus a recurring maintenance cost C_maint(a). It may be admitted only if the local resource budget can pay the write while respecting the reserve floor:

    admit(a) iff e_local - C_write(a) >= e_min

The candidate's utility is measured from held-out task improvement and future operating-cost change, not from the fact that a new edge was created. A practical online eligibility signal can be used to rank candidate writes, but all conditions must receive equal training data and compute budgets. Do not use the unavailable future test label to decide a write.

This is an abstract computational resource model. It is not a proton simulation, ATP simulation, joule meter, or claim of biological equivalence. Proton-motive-force equations are relevant only as a physical reference for electrochemical potential; they are not required in this first software experiment.

## Required controls

Use identical cell counts, initial graph seeds, input streams, readout/training procedure, maximum edge count, total compute budget, and random-seed schedule.

- A — Fixed reservoir: no structural plasticity; no local resource gate.
- B — Morphogenetic reservoir: topology develops using a DGCA-style rule; no resource-priced writes.
- C — Global-budget morphogenesis: same structural rule, but writes draw from one shared scalar reserve.
- D — Local-energy morphogenesis: writes draw from spatially local reserves and local transport; no benefit-aware write selection.
- E — Local-energy, benefit-aware writes: same local reserve field, but structural writes are selected using an online eligibility/utility estimate and pay both write and maintenance costs.

B is essential: it prevents rediscovering DGCA. C separates local gradients from a simple global budget. D separates spatial resource locality from write selection. E tests the actual hypothesis.

## Tasks and protocol

Use at least two task families with different memory demands:

- NARMA-10 or an independently implemented equivalent temporal benchmark.
- Delayed XOR / temporal parity with a predeclared delay.

Add a regime-change phase after initial training and a damage phase that removes a fixed fraction of nodes or edges. Train on one set of seeds and report held-out seeds. Freeze hyperparameters before the final evaluation. Use at least 30 paired seeds for the final comparison; publish every seed, including failures.

Do not tune E more heavily than the controls. Use matched initial states and paired random streams wherever possible. Report confidence intervals and effect sizes, not only a best run.

## Primary outcomes

1. Held-out task error at equal total compute budget.
2. Energy-normalized performance: held-out error per measured/simulated resource unit, with the unit definition stated.
3. Structural write count and cumulative write + maintenance cost.
4. Compute cost per correct prediction.
5. Recovery time and post-damage performance.
6. Topology stability, edge churn, starvation frequency, and reserve conservation.

Report CPU time, operations, bytes moved and GPU time separately where measured. Do not collapse them into joules without target-device calibration.

## Falsification and success criteria

The hypothesis is not supported if E fails to outperform B/C/D on the predeclared energy-performance trade-off, if the result disappears under matched compute budgets, or if the gain depends on one seed/task or unreported tuning.

A promising result requires all of the following:
- E improves the predeclared energy-normalized metric over B and C on both task families, with paired 95% confidence intervals excluding zero.
- Raw task error is not materially worse than the best control (predeclare a 2% relative non-inferiority margin).
- The gain survives regime change and damage tests.
- Ablations show that removing local resource gradients or write/maintenance pricing removes the advantage.
- Resource conservation and deterministic replay tests pass.

Even a positive result would establish a measured engineering result for this benchmark, not consciousness, biological life, general intelligence, or a scientific breakthrough by itself. Novelty would still require a comprehensive prior-art review.

## Integration boundary

Keep this experiment outside ISCE persistence initially. Reuse the existing ComputationalBloodstream as a resource-accounting adapter; do not create a second organism-state owner. Do not modify the 48-byte TEC-Q cell contract or claim a 15,000-cell GPU implementation. First validate the mechanism on a small deterministic CPU benchmark. Integrate only after the experiment passes and a versioned ISCE migration can preserve single ownership.

## Decision

Do not add a new architecture layer or rename the organism. This document defines one falsifiable research gate. The next implementation artifact should be a small executable benchmark plus tests for conservation, write admission, deterministic replay, matched-budget controls, and statistical reporting.
