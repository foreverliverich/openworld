# ISCE kernel implementation — first executable gate

## Scope
This change adds an independent CPU-first deterministic transition kernel at
`chimera/isce.py`. It does not yet migrate persistence from
`OrganismKernel`, and it does not claim the historical complete graph has
been recovered. The first canonical graph is an explicit, versioned starting
model whose topology and weights are fingerprinted and checked on transitions.

## Implemented
- Versioned, serializable intrinsic state with body/allostatic,
  interoceptive, sensorimotor, temporal, self-model, attention and resource
  partitions in one immutable state value.
- Immutable directed causal graph with fixed edge weights and fingerprint.
- Pure deterministic transition function with finite/range validation.
- Explicit measured-work input kept separate from simulated reserve units.
- Bounded intervention API for CCPL experiments; interventions cannot mutate
  graph topology or weights.
- Temporal tick, organism time and previous-state digest.
- Viability/action gate derived from intrinsic state.
- Unit tests for determinism, serialization, temporal coupling, graph invariance,
  intervention effects and invalid inputs.

## Not yet implemented
- SQLite/IndexedDB persistence adapter and atomic journal commit.
- Migration of current `OrganismKernel` state into ISCE.
- Full ICCR five-condition acceptance suite and commutation tests over the
  complete recovered mechanism set.
- CCPL sham, double-intervention and mediation harness.
- Measured hardware telemetry adapters/calibration.
- Runtime worker clock, lifecycle semantics and governance/action gateway.

## Verification
Run: `python -m unittest discover -s tests -v`.

The test suite in this commit is the acceptance evidence for this first gate.
Do not mark V-OMEGA P1 complete until migration, sole-owner enforcement,
persistence/restart and broader causal-closure tests pass.
