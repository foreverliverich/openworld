# Grounded world-to-ISCE sensory path

The autonomous agent previously queried RealityEngine but reduced the result to
a hard-coded novelty and prediction-error pair. This adapter replaces that
placeholder with reproducible features derived from the authoritative world.

## Input features

The adapter reads RealityEngine.observe() at the organism's current position:
- visible entity count and total world entity count;
- nearest visible entity distance;
- a stable signature over visible entity IDs and quantized positions;
- local scalar fields supplied by RealityEngine.

It derives bounded proximity, local density and sensory salience. The signature
and visible count are encoded as a compact versioned token in the existing
ISCE self-model last_outcome field. On the next observation, the token provides
the prior count/signature needed to estimate observation surprise and novelty.
No second persistent memory store is introduced.

## ISCE coupling

TransitionInput now includes sensory_salience (appended to preserve existing
positional field compatibility). The urgency equation includes this measured
world-derived input, which then influences attention focus through the existing
ISCE transition. OrganismKernel passes the input without owning a separate
sensory state. The kernel version is now 0.2.0; the persisted state schema
remains version 1.

The autonomous agent uses the adapter in its observe-and-consolidate phase and
returns sensory telemetry with the AgentStep result. Prediction error is the
bounded change in visible entity count relative to the prior observation token;
novelty is based on whether the visible geometry signature changed.

## Limits

This is grounded visual/world-state sensing over the current AABB entity world.
It is not camera vision, touch, hearing, proprioception, contact force or
anatomical sensing. The current engine does not provide a deformable body
sensor model, so mechanical strain remains sourced only from existing
explicit inputs. The novelty and surprise measures are simple count/signature
proxies and should be replaced with richer predictive sensory models as the
world gains articulated mechanics and modalities.
