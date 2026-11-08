# Durable action-to-organism causal links

The action gateway now carries the committed RealityEngine action ID into the
subsequent ISCE organism-state commit.

For a governed mutation, the event sequence is:
1. RealityEngine commits the toolbox action and appends its world event.
2. The gateway captures that event's action_id.
3. OrganismKernel commits the updated ISCE state and local field projection,
   with causation_id and correlation_id set to the originating action ID.
4. AgentStep and RuntimeFrame expose the originating action ID to the browser.

The link is stored inside the existing hash-chained organism-tick event payload;
no event table or state schema migration is required. Existing events without
these optional fields remain valid and unchanged.

This makes the causal chain auditable across the two sequential transactions.
It does not make them one atomic transaction. If the organism commit cannot be
reconciled after the world action, the action remains committed and the event
journal identifies the action that still needs reconciliation.
