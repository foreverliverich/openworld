# Organism action gateway

The existing RealityEngine remains the sole world authority and ISCE remains
the sole intrinsic organism-state owner. This gateway connects the two without
introducing a second state store.

## Path

1. A planner submits an ActionProposal with a named toolbox operation and the
   world revision it observed.
2. The gateway checks the operation allowlist, exact revision, ISCE viability,
   body energy and internal reserve admission.
3. The existing ChimeraToolbox validates the arguments and dispatches the
   operation to RealityEngine.
4. RealityEngine commits the world mutation and appends its existing
   hash-chained event.
5. The gateway measures logical work from the committed operation (for example,
   the number of structure parts) and updates ISCE with cost, prediction error,
   novelty, action success and outcome.
6. The receipt reports both the world-action revision and the subsequent
   organism-state revision.

The autonomous agent's shelter and workbench construction now use this path.
Rest/regulation remains an intrinsic organism transition, not a world mutation.

## Resource accounting

Logical work units are deterministic operation counts. They are not CPU cycles,
GPU time, joules or hardware telemetry. Current admission/charge coefficients
are explicit calibration parameters:
- energy cost: 0.0005 per logical work unit;
- reserve cost: 0.001 per logical work unit;
- minimum post-action reserve: greater than 0.05.

These values are prototype simulation units and must be calibrated against
measured runtime cost before being interpreted as physical metabolism.

## Failure semantics

A stale proposal is rejected before mutation. A non-viable or under-resourced
organism is refused before mutation. The toolbox and RealityEngine retain their
existing validation and transaction semantics.

The world action and the subsequent ISCE outcome update are two sequential
transactions, not one cross-database atomic transaction. If concurrent writes
prevent organism accounting after the world commit, the gateway does not replay
the action; it raises an explicit reconciliation error and the durable world
event remains the source evidence. A future version should combine the action
result and organism update in one RealityEngine transaction or add a durable
outbox/reconciliation worker.

## Verification

The tests cover successful charging, action-success/prediction-error recording,
stale revision rejection, starvation refusal, unsupported operations,
invalid blueprint rejection and work proportional to committed part count.
The existing autonomous-agent construction regression also runs through the
gateway. CI is the verification source; see the implementation ledger.
