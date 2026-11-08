# Digital cell experiment — first integrated loop

Status: experimental implementation; not a biological cell model and not a
claim of learning transfer or emergent intelligence.

## What is now executable

`chimera.digital_cell.DigitalCell` implements a deliberately small local
controller with:

- bounded energy and stress regulation;
- leaky membrane-potential integration that causally gates active seeking;
- refractory suppression of active actions;
- pure step proposals with explicit commit, so failed world persistence cannot silently advance cell state;
- three actions (rest, seek, inspect);
- a bounded reward-prediction memory for action values;
- deterministic action selection and explicit prediction error;
- a pure transition into the existing ISCE kernel on every cell step.

ISCE remains the single intrinsic organism-state owner. The cell's local
variables are experimental controller state only. `DigitalCell.execute()`
now reads a caller-supplied observation, proposes a cell and ISCE transition,
routes a seek action through `OrganismActionGateway` to consume energy from
the authoritative RealityEngine field, commits the exact proposed ISCE state,
and advances local cell memory only after persistence succeeds. Rest and
inspect also commit their proposed ISCE state before local cell memory advances.

The new `world_builder.harvest_energy` action is bounded, revision-checked,
event-journaled, and subject to the existing organism viability/resource gate.
It does not create energy: it subtracts energy from the local environment.

## What this closes — and what it does not

This closes a first *single-cell world-action loop*: a cell decision can
consume a real persistent environmental field through the governed gateway,
and its matching ISCE transition is committed before local memory advances.
The integration tests cover a seek action that depletes the world energy field
and a rest action that commits the proposed organism state.

It does not yet establish adaptive survival advantage, long-horizon stability,
learning transfer, or population-level emergence. The environment observation
is still supplied by the caller; camera/touch/hearing sensing, GPU particle
coupling, gene expression and tissue mechanics are not part of this path.

## Acceptance gate

Run:

```bash
python -m unittest tests.test_digital_cell tests.test_ccpl
```

The current tests are contract tests for one-step integration, not the paired
survival experiment. Next acceptance gate: run matched long-horizon episodes
with identical initial world/organism states under adaptive memory, frozen
memory, and shuffled feedback. Change the location/time of environmental energy
availability after the initial phase. Report survival ticks, minimum/mean body
energy, cumulative homeostatic error, harvested field energy, action success,
and prediction error. Do not claim learning advantage until adaptive memory
reproducibly beats both controls on held-out schedules.
