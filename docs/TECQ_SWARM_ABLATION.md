# TEC-Q swarm ablation protocol

Run the deterministic comparison from the repository root:

```bash
python -c "import json; from chimera.tecq.experiments import run_swarm_ablation; print(json.dumps(run_swarm_ablation(cell_count=15000, steps=160), indent=2))"
```

The four conditions use the same initial lattice, population, sensory pulse,
damage intervention and tick budget:

1. Independent cells: no bonds or neighborhood coupling.
2. Fixed network: bonds remain fixed; torsion and field diffusion are disabled.
3. Adaptive network: topology adapts; torsion and field diffusion are disabled.
4. Full coupled TEC-Q: adaptive topology, torsion, fields, nervous dynamics,
   swarm intent, metabolism and structural memory.

Outputs include recovery tick, local activation coordination, topology size,
energy/stress/memory/cohesion, prediction error, strain, estimated operation
count, wall time and a deterministic final-state digest. The operation count
is an estimate, not hardware telemetry. Wall time is reported for measurement,
not used as a substitute for equal compute budgets. The experiment does not
assume the full architecture wins; run repeated configurations and inspect
failure/stability as well as averages before making a breakthrough claim.
