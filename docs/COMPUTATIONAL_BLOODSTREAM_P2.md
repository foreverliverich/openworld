# V-OMEGA P2 — Computational Bloodstream Prototype

Status: **implemented as an isolated deterministic prototype; not yet integrated into ISCE**.

## Why this module exists

The current ISCE state has one aggregate reserve and cumulative work counter. The
adopted V-OMEGA P2 decision requires measured work demand, resource circulation,
starvation-gated admission, and explicit separation between observed hardware
telemetry and simulated intrinsic reserves.

`chimera/metabolism.py` implements the first testable resource-flow kernel
without creating a second organism state owner. It is an experiment adapter:
the canonical ISCE state remains authoritative until a versioned migration is
designed and tested.

## State and laws

For organ (i), reserve is (e_i), production is (p_i), measured/calibrated
consumption is (c_i), and directed transfer is (f_{ij}):

```
e_i(t+1) = e_i(t) + p_i - c_i
           + sum_j f_ji - sum_j f_ij
```

Transfers are conservative. They are bounded by donor surplus above its
setpoint, receiver deficit below its setpoint, edge conductance, and both
organs' capacity/minimum constraints.

Work requests are admitted only if the organ can pay the calibrated cost while
remaining at or above its minimum reserve. Rejected work consumes no reserve
and increments unmet demand. This is a named, inspectable starvation gate.

## Two different units

`WorkMeasurement` preserves operation counts, CPU nanoseconds, bytes moved and
GPU nanoseconds as separate observed quantities. A versioned
`MetabolicCalibration` maps these into simulated reserve units. Those units
are not joules, watts, battery percentage or hardware energy telemetry.
Calibration must be measured on the target runtime and versioned before
production use.

## Acceptance tests

Run:

```bash
python -m unittest discover -s tests -p "test_metabolism.py" -v
```

Tests cover reserve conservation, deterministic replay, capacity bounds,
work-cost calibration, starvation rejection, and the causal effect of enabling
or disabling circulation on work admission.

## Prior-art boundary

This prototype is not claimed as novel. Relevant existing work already covers
important pieces of the problem:

- Xie et al., *Energy as a Common Currency for Understanding Embodied
  Evolution* (2026), argues for open-system energy accounting that evaluates
  both action and persistence rather than task score alone:
  https://doi.org/10.34133/cbsystems.0680
- Solé et al., *Fundamental Constraints to the Logic of Living Systems*
  (2024), connects thermodynamic constraints, self-maintenance, information,
  development and living organization:
  https://doi.org/10.1098/rsfs.2024.0010
- Parzych and Daymude, *Adaptive Self-Organization in Anonymous Dynamic
  Networks* (DISC 2026), gives formal distributed self-organization results
  under changing local signals and dynamic topology:
  https://doi.org/10.4230/LIPIcs.DISC.2026.27
- *Neural Cellular Automata: From Cells to Pixels* (SIGGRAPH 2026) advances
  local self-organizing morphogenesis with an implicit decoder:
  https://doi.org/10.1145/3799902.3811053

Therefore the resource balance law, local flow, starvation and self-organization
are not breakthrough claims by themselves. The unresolved Chimera question is
whether measured computational demand, local reserve circulation, allostatic
viability and developmental substrate changes can be joined in one causally
closed running organism, and whether that joint mechanism yields a measurable
capability or persistence advantage over strong separated-component baselines.
That claim requires experiments; it is not established by this prototype.

## Open research gates

1. Integrate the resource state into ISCE with an explicit schema version and
   single-owner migration; do not persist a competing organism state.
2. Add time-windowed measured telemetry adapters for CPU, worker queues, bytes,
   and optional GPU timing.
3. Calibrate on browser and Python runtimes; do not transfer coefficients
   blindly between devices.
4. Run randomized task schedules and sham/double/mediation interventions.
5. Compare circulation against aggregate-reserve, no-circulation, and
   demand-proportional baselines.
6. Test recovery, resource hoarding, deadlock, starvation fairness and
   oscillatory flow.
7. Only then connect the resource network to TEC-Q cell neighborhoods.

This is a mechanistic P2 prototype, not evidence of consciousness, biological
equivalence or scientific novelty.
