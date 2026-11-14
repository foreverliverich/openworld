# TEC-Q coupled runtime

This branch adds an executable coupled TEC-Q cell engine and wires it into
the existing organism-owned AutonomousRuntime. It does not create a second
world or intrinsic-state owner. TEC-Q aggregates are passed through the existing
OrganismKernel facade into the authoritative ISCE TransitionInput, then
RealityEngine commits the ISCE state and world fields transactionally.

## Included

- Stable cell IDs and structure-of-arrays sidecars for position, velocity,
  quaternion orientation, angular velocity, energy, stress, memory, cohesion,
  neural potential/activation/refractory state, swarm intent, phase, strain,
  prediction error and organ ownership.
- Spatial-hash neighbor discovery and degree-bounded undirected bonds.
- Hysteretic adaptive bond weighting and topology rewiring.
- Equal-and-opposite spring forces, damping, angular coupling and quaternion
  integration.
- Phase coupling and diffusive energy/stress/memory/cohesion fields.
- Leaky integrate-and-fire nervous dynamics with refractory gating.
- Local swarm-intent consensus modulated by prediction error and viability.
- Metabolic depletion, repair/cohesion feedback and ISCE aggregate projection.
- Transactional adapter that restores the TEC-Q checkpoint if the ISCE/world
  commit rejects.
- Optional AutonomousRuntime integration; TEC-Q advances before the agent's
  single ISCE tick and its field/prediction feedback enters that same tick.
- Versioned exact checkpoint/restore guarded by SHA-256 state digest.

## ABI and integration invariants

The 48-byte SomaticCell ABI is intentionally opaque: this code does not guess
or redefine its field offsets. Dynamic state is kept in sidecar arrays. The
identity seed, form genome, SEED2 and TEC-Q checkpoint remain separate artifacts.
TEC-Q does not write ISCE or RealityEngine directly.

## Verification status

Unit tests are included under tests/test_tecq_engine.py,
tests/test_tecq_integration.py and tests/test_tecq_runtime.py. CI verification
is required before merge. The current solver is the CPU reference backend, not
a measured 15,000-cell speed claim. A production WebGPU/WGSL backend,
CPU/GPU parity, full CCPL/ICCR experiments and measured 15k/1M-cell benchmarks
remain open.