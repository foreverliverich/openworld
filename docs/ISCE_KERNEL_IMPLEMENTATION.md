# ISCE kernel implementation — integrated state-owner gate

## Scope and ownership

`chimera/isce.py` defines the versioned CPU-first deterministic intrinsic
organism state and transition law. `OrganismKernel` in
`chimera/organism_kernel.py` is now a compatibility-facing controller around
that kernel; it no longer contains a second flat physiology state or a second
transition implementation.

The authoritative intrinsic state is `ISCEOrganismState`. The authoritative
external world remains `RealityEngine`. RealityEngine stores and transactionally
commits the serialized ISCE value together with its local morphogenic field
projection and hash-chained event. It is a persistence/world boundary, not a
competing organism physiology owner.

The runtime and baseline agent now read and advance the same ISCE state. The
browser/API snapshot retains legacy flat field names as computed read-only
projections; those aliases are not stored and cannot become a second owner.

## Implemented

- Versioned, immutable intrinsic state with embodied position, body/allostasis,
  interoception, sensorimotor state, temporal continuity, self-model/memory,
  attention and internal resource reserve.
- Input/state finite and range validation; unsupported schema versions reject.
- Fixed seven-partition causal graph with immutable tuple-backed topology,
  signed edge weights and a structural fingerprint.
- Weighted incoming graph activations participate in the state-transition
  equations across body, interoception, sensorimotor, temporal, self-model and
  attention pathways.
- Deterministic pure transition function; identical state/input pairs produce
  identical next states and digests.
- Bounded interventions for controlled causal experiments; graph topology and
  weights cannot be changed by an intervention.
- Explicit temporal tick, organism time and predecessor-state digest.
- Simulated reserve/work accounting remains distinct from actual hardware
  telemetry; no joule equivalence is claimed.
- `OrganismKernel` compatibility façade routes state updates through ISCE and
  only publishes its next in-memory state after the SQLite transaction commits.
- Legacy flat persisted organism payloads are read and converted into ISCE on
  load; the next successful tick writes the complete schema-v1 state. New
  persistence writes reject legacy flat payloads.
- Runtime and autonomous agent now use ISCE partitions; browser/API legacy
  snapshot aliases are derived from ISCE at read time.
- RealityEngine atomically commits ISCE state, local fields, revision and
  hash-chained event. Failed optimistic writes leave the in-memory ISCE state
  unchanged.

## Tests

`tests/test_isce.py` covers determinism, serialization, temporal predecessor
linkage, fixed graph fingerprint, causal edge-weight effects, inhibitory
(signed) edges, intervention propagation, state range checks, canonical graph
schema and viability gating.

`tests/test_organism_kernel.py` covers ISCE-backed physiology/world-field
coupling, durable restart, legacy payload migration, rejection of legacy
writes and failed-revision atomicity.

`tests/test_autonomous_agent.py`, `tests/test_runtime.py` and
`tests/test_http_server.py` exercise the migrated agent/runtime/browser API
against the same ISCE state owner.

## Still open — do not mark V-OMEGA P1 complete

- Full ICCR five-condition acceptance suite and commutation tests over the
  recovered mechanism set.
- CCPL experiment runner with baseline, sham, single/double intervention,
  mediation and counterfactual trajectory comparisons.
- Complete causal-closure audit; the current canonical graph is the first
  executable graph, not proof that the full historical ISCE graph is recovered.
- Explicit versioned event envelope with causation/correlation IDs and replay
  contract beyond the existing RealityEngine hash-chained journal.
- Atomic migration marker/backup strategy for production databases, and
  restart tests across an interrupted migration boundary.
- Measured hardware telemetry adapters and calibrated cost model.
- Browser Worker-owned clock, IndexedDB/browser journal and explicit
  continuous/dormant/reconciled lifecycle semantics. Current deployed runtime
  is the Python process/runtime, not the final browser-home hybrid scheduler.
- Single action gateway, governance/resource admission and full sensory/body
  mechanics integration.

## Verification

Run locally with:

```bash
python -m unittest discover -s tests -v
```

The CI workflow on the branch is the authoritative verification record. A
passing test suite establishes these code contracts only; it does not establish
sentience, biological equivalence, full causal closure or a complete embodied
animal body.
