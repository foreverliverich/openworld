"""Couple TEC-Q cell dynamics to the single authoritative ISCE/world tick."""
from __future__ import annotations
from typing import Optional

from .engine import TECQEngine, TECQState, TECQError


class TECQOrganismAdapter:
    """Advance TEC-Q, project its physiology into ISCE, and commit atomically.

    TEC-Q sidecar state is checkpointed before each coupled step. If the
    authoritative ISCE/RealityEngine transaction rejects, TEC-Q is restored so
    the two layers cannot silently advance on different logical ticks.
    """
    def __init__(self, engine: TECQEngine, organism):
        if not isinstance(engine, TECQEngine):
            raise TECQError("engine must be a TECQEngine")
        if not callable(getattr(organism, "tick", None)):
            raise TECQError("organism must expose the authoritative tick API")
        self.engine = engine
        self.organism = organism

    def tick(self, *, external_drive: Optional[list[float]] = None,
             dt: Optional[float] = None, expected_revision: Optional[int] = None) -> dict:
        before = self.engine.state.checkpoint()
        try:
            metrics = self.engine.step(external_drive)
            feedback = self.engine.isce_projection()
            result = self.organism.tick(
                dt=self.engine.config.dt if dt is None else dt,
                mechanical_strain=metrics["max_strain"],
                prediction_error=feedback["prediction_error"],
                novelty=feedback["novelty"],
                environmental_feedback={
                    "energy": feedback["environmental_energy"],
                    "stress": feedback["environmental_stress"],
                    "memory": feedback["environmental_memory"],
                    "cohesion": feedback["environmental_cohesion"],
                },
                expected_revision=expected_revision,
            )
        except Exception:
            self.engine.state = TECQState.from_checkpoint(before)
            raise
        return {
            "tecq": metrics,
            "organism": self.organism.snapshot(),
            "world_revision": result.revision,
            "tecq_checkpoint_digest": self.engine.state.digest(),
        }
