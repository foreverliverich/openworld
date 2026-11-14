# TEC-Q swarm ablation protocol

Run a seeded comparison from the repository root:

```bash
python -c "import json; from chimera.tecq.experiments import run_swarm_ablation; print(json.dumps(run_swarm_ablation(cell_count=512, steps=160, seed=7), indent=2))"
```

The four conditions receive the same seeded initial state, sensory-pulse cohort,
damage cohort, population and simulation-tick budget:

1. Independent cells: no bonds or neighborhood coupling.
2. Fixed network: bonds remain fixed; torsion and field diffusion are disabled.
3. Adaptive network: topology adapts; torsion and field diffusion are disabled.
4. Full coupled TEC-Q: adaptive topology, torsion, fields, nervous dynamics,
   swarm intent, metabolism and structural memory.

The seed controls initial heterogeneity and intervention cohorts. Repeating the
same seed reproduces the same simulation; changing the seed changes the trial.
The four conditions share one initial state within each trial.

Recovery now has a structural gate: a damaged cell counts as structurally
recovered only when its connected component also contains at least one
undamaged cell. Thus an isolated independent cell cannot pass network recovery
merely because global stress and prediction-error averages fall.

Outputs include recovery tick, structural recovery fraction, local activation
coordination, topology size, energy/stress/memory/cohesion, prediction error,
strain, estimated operation count, wall time and a final-state digest. The
operation count is an estimate, not hardware telemetry.

**Important limitation:** the experiment matches simulation ticks, not actual
hardware compute. Different conditions perform different amounts of work.
Wall time and estimated work are reported separately; a true equal-compute
comparison requires a defined operation or hardware-time budget and stopping
each condition at that budget. Do not interpret this as a compute-normalized
win. Run multiple distinct seeds and report distributions, not just one run.
The experiment does not presume the full architecture wins.
