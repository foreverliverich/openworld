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
variables are experimental controller state only. The caller receives the
new ISCE state and must persist it through the existing OrganismKernel /
RealityEngine path when running inside the application.

## What this closes — and what it does not

This closes the missing *executable coupling seam* between local cell
regulation, action selection, outcome-based memory and organism-level
physiology. It does not yet couple cell actions to actual RealityEngine
geometry, GPU particles, gene expression, tissue mechanics or a camera-derived
sensor. The current environment is supplied as a bounded observation.

## Acceptance gate

Run:

```bash
python -m unittest tests.test_digital_cell tests.test_ccpl
```

Then add a paired experiment with identical initial states and observation
sequences: adaptive cell, frozen-memory ablation and shuffled-outcome sham.
Report cumulative homeostatic error, energy reserve, task reward, and
prediction error. Do not call it learning until the adaptive condition
reproducibly beats both controls across held-out observation sequences.
