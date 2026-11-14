"""TEC-Q integration contracts and validation helpers."""

from .contract import (
    IDENTITY_SEED_MAX_BYTES,
    SOMATIC_CELL_ABI_BYTES,
    TECQ_INITIAL_CELL_TARGET,
    TECQ_SCALE_CELL_TARGET,
    OMNIKERNEL_SAB_TARGET_BYTES,
    GPU_POOL_TARGET_BYTES,
    GPU_EXTENDED_STATE_BYTES_PER_CELL,
    WORKER_POOL_TARGET,
    VORTEX_PHASE_SCHEDULE,
    LOSSLESS_CHECKPOINT_DOMAINS,
    ContractViolation,
    IdentitySeed,
    StateArtifact,
    FoldDescriptor,
    memory_budget,
    validate_somatic_cell_buffer,
    validate_soa_extensions,
    validate_bond_edges,
    normalize_quaternion_xyzw,
    validate_phase_schedule,
    phase_experiment_baselines,
)

from .engine import TECQConfig, TECQEngine, TECQError, TECQState, Bond, lattice_state
from .integration import TECQOrganismAdapter

__all__ = [name for name in globals() if not name.startswith("_")]
