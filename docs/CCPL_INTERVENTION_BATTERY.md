# CCPL deterministic intervention battery

This change adds an executable paired-trajectory experiment runner over the
existing ISCE state-transition kernel. It does not add an organism state owner,
change the fixed graph, or alter the existing transition contract.

## Conditions

- **Baseline:** unperturbed ISCE trajectory.
- **Sham:** zero-delta intervention at the same tick.
- **Single:** one bounded post-transition state intervention.
- **Double:** two bounded interventions applied at the same transition boundary.
- **Mediated:** the source intervention is applied, then the named mediator is
  clamped to its paired baseline value for the remainder of the trajectory.

All conditions start from the same immutable state and consume the same ordered
input sequence. The output includes every state in every trajectory, graph
fingerprint, initial digest, final outcome, paired effects, sham error and
mediation attenuation. The graph fingerprint is checked before and after.

## Scope and limitations

This is an operational causal-intervention battery for the current seven-node
ISCE model, not a complete ICCR/CCPL acceptance proof. The mediator clamp is an
explicit experimental intervention, not a claim that the selected mediator is
the only biological path. It does not establish consciousness, human-grain
phenomenology, or biological equivalence. Hardware work units remain separate
from simulated reserve units.

## Run

\`python -m unittest tests.test_ccpl -v\`

The full regression suite remains:

\`python -m unittest discover -s tests -v\`
