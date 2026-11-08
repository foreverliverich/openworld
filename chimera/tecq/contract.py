"""Executable architecture contracts for Chimera's 1KB seed, TEC-Q and Fold.

This module deliberately validates boundaries without inventing undocumented binary
layouts. It is a contract layer, not a replacement physics engine or a codec.
"""

from __future__ import annotations

import base64
import hashlib
import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence

IDENTITY_SEED_MAX_BYTES = 1024
SOMATIC_CELL_ABI_BYTES = 48
TECQ_INITIAL_CELL_TARGET = 15_000
TECQ_SCALE_CELL_TARGET = 1_000_000
OMNIKERNEL_SAB_TARGET_BYTES = 128 * 1024 * 1024
GPU_POOL_TARGET_BYTES = 128 * 1024 * 1024
GPU_EXTENDED_STATE_BYTES_PER_CELL = 144
WORKER_POOL_TARGET = 20
VORTEX_PHASE_SCHEDULE = (1, 2, 4, 8, 7, 5)

# The full checkpoint must carry these state domains for a lossless TEC-Q wake.
LOSSLESS_CHECKPOINT_DOMAINS = (
    "cell_abi",
    "cell_extensions",
    "bond_topology",
    "torsion_state",
    "morphogenetic_fields",
    "nervous_state",
    "swarm_state",
    "sensor_readout_state",
    "physiology_state",
    "developmental_state",
    "world_revision",
)


class ContractViolation(ValueError):
    """An architecture invariant or serialization boundary was violated."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class IdentitySeed:
    """Opaque compact identity payload; its internal 1KB layout is format-owned elsewhere.

    The contract caps the payload at 1,024 bytes but does not reinterpret its fields.
    A future decoder must be versioned and must preserve unknown bytes.
    """

    version: str
    payload: bytes

    def __post_init__(self) -> None:
        if not self.version or not self.version.strip():
            raise ContractViolation("Identity seed version is required")
        if not isinstance(self.payload, bytes):
            raise ContractViolation("Identity seed payload must be immutable bytes")
        if not 0 < len(self.payload) <= IDENTITY_SEED_MAX_BYTES:
            raise ContractViolation(
                f"Identity seed must contain 1..{IDENTITY_SEED_MAX_BYTES} bytes; "
                f"received {len(self.payload)}"
            )

    @property
    def digest(self) -> str:
        return sha256_hex(self.payload)

    @property
    def encoded(self) -> str:
        return base64.urlsafe_b64encode(self.payload).decode("ascii").rstrip("=")


@dataclass(frozen=True)
class StateArtifact:
    """Content-addressed external artifact required to reconstruct large state."""

    uri: str
    sha256: str
    byte_length: int

    def __post_init__(self) -> None:
        if not self.uri.strip():
            raise ContractViolation("Artifact URI must not be empty")
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise ContractViolation("Artifact sha256 must be 64 lowercase hexadecimal characters")
        if self.byte_length < 1:
            raise ContractViolation("Artifact byte_length must be positive")


@dataclass(frozen=True)
class FoldDescriptor:
    """Portable fold metadata; never misrepresents a digest as recoverable state.

    'portable' preserves identity plus deterministic reconstruction inputs.
    'lossless' additionally requires an external checkpoint containing every
    LOSSLESS_CHECKPOINT_DOMAINS entry. The compact token is a locator, not magic
    entropy compression.
    """

    codec: str
    codec_version: str
    mode: str
    identity_seed: IdentitySeed
    checkpoint: Optional[StateArtifact] = None
    checkpoint_domains: tuple[str, ...] = ()
    reconstruction_recipe_version: Optional[str] = None
    deterministic_seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.codec not in {"SEED2", "TECQ-FOLD"}:
            raise ContractViolation(f"Unsupported fold codec: {self.codec}")
        if not self.codec_version:
            raise ContractViolation("Fold codec version is required")
        if self.mode not in {"portable", "lossless"}:
            raise ContractViolation("Fold mode must be 'portable' or 'lossless'")
        if self.mode == "lossless":
            if self.checkpoint is None:
                raise ContractViolation("Lossless fold requires an external full-state checkpoint")
            missing = set(LOSSLESS_CHECKPOINT_DOMAINS) - set(self.checkpoint_domains)
            if missing:
                raise ContractViolation(
                    "Lossless fold omits required state domains: " + ", ".join(sorted(missing))
                )
        if self.mode == "portable" and not self.reconstruction_recipe_version:
            raise ContractViolation("Portable fold requires a versioned reconstruction recipe")

    def manifest(self) -> dict:
        return {
            "format": "chimera-fold-descriptor",
            "format_version": 1,
            "codec": self.codec,
            "codec_version": self.codec_version,
            "mode": self.mode,
            "identity_seed": {
                "version": self.identity_seed.version,
                "payload_base64url": self.identity_seed.encoded,
                "sha256": self.identity_seed.digest,
                "byte_length": len(self.identity_seed.payload),
            },
            "checkpoint": None if self.checkpoint is None else {
                "uri": self.checkpoint.uri,
                "sha256": self.checkpoint.sha256,
                "byte_length": self.checkpoint.byte_length,
            },
            "checkpoint_domains": list(self.checkpoint_domains),
            "reconstruction_recipe_version": self.reconstruction_recipe_version,
            "deterministic_seed": self.deterministic_seed,
        }


@dataclass(frozen=True)
class MemoryBudgetReport:
    cell_count: int
    base_abi_bytes: int
    extended_gpu_bytes: int
    sab_capacity_bytes: int
    gpu_capacity_bytes: int

    @property
    def base_cell_buffer_bytes(self) -> int:
        return self.cell_count * self.base_abi_bytes

    @property
    def gpu_state_bytes(self) -> int:
        return self.cell_count * self.extended_gpu_bytes

    @property
    def gpu_fits(self) -> bool:
        return self.gpu_state_bytes <= self.gpu_capacity_bytes

    @property
    def sab_fits_for_base_cells(self) -> bool:
        return self.base_cell_buffer_bytes <= self.sab_capacity_bytes

    @property
    def gpu_overage_bytes(self) -> int:
        return max(0, self.gpu_state_bytes - self.gpu_capacity_bytes)

    def as_dict(self) -> dict:
        return {
            "cell_count": self.cell_count,
            "base_cell_buffer_bytes": self.base_cell_buffer_bytes,
            "extended_gpu_state_bytes": self.gpu_state_bytes,
            "sab_capacity_bytes": self.sab_capacity_bytes,
            "gpu_capacity_bytes": self.gpu_capacity_bytes,
            "gpu_fits": self.gpu_fits,
            "sab_fits_for_base_cells": self.sab_fits_for_base_cells,
            "gpu_overage_bytes": self.gpu_overage_bytes,
        }


def memory_budget(
    cell_count: int,
    *,
    base_abi_bytes: int = SOMATIC_CELL_ABI_BYTES,
    extended_gpu_bytes: int = GPU_EXTENDED_STATE_BYTES_PER_CELL,
    sab_capacity_bytes: int = OMNIKERNEL_SAB_TARGET_BYTES,
    gpu_capacity_bytes: int = GPU_POOL_TARGET_BYTES,
) -> MemoryBudgetReport:
    values = (cell_count, base_abi_bytes, extended_gpu_bytes,
              sab_capacity_bytes, gpu_capacity_bytes)
    if any(not isinstance(v, int) or v <= 0 for v in values):
        raise ContractViolation("Memory budget inputs must be positive integers")
    return MemoryBudgetReport(
        cell_count, base_abi_bytes, extended_gpu_bytes,
        sab_capacity_bytes, gpu_capacity_bytes,
    )


def validate_somatic_cell_buffer(raw: bytes, *, expected_cells: Optional[int] = None) -> int:
    """Validate the preserved 48-byte ABI without guessing its undocumented slot meanings."""
    if not isinstance(raw, bytes):
        raise ContractViolation("SomaticCell ABI buffer must be bytes")
    if len(raw) % SOMATIC_CELL_ABI_BYTES:
        raise ContractViolation(
            f"SomaticCell buffer length {len(raw)} is not divisible by "
            f"{SOMATIC_CELL_ABI_BYTES}"
        )
    count = len(raw) // SOMATIC_CELL_ABI_BYTES
    if expected_cells is not None and count != expected_cells:
        raise ContractViolation(f"Expected {expected_cells} cells, received {count}")
    return count


def validate_soa_extensions(extensions: Mapping[str, Sequence[float]], cell_count: int) -> None:
    """Every sidecar array is cell-aligned; the base 48-byte ABI is never widened in place."""
    if cell_count < 1:
        raise ContractViolation("cell_count must be positive")
    required = {
        "orientation_xyzw",       # 4 floats/cell
        "angular_velocity_xyz",   # 3 floats/cell
        "activation",             # 1 float/cell
        "phase",                  # 1 float/cell
        "strain",                 # 1 float/cell
        "memory",                 # 1 float/cell
        "cohesion",               # 1 float/cell
        "organ_id",               # integer-valued sidecar
        "potential",              # 1 float/cell
        "refractory",              # 1 float/cell
        "swarm_intent",            # 1 float/cell
    }
    missing = required - set(extensions)
    if missing:
        raise ContractViolation("Missing TEC-Q sidecar arrays: " + ", ".join(sorted(missing)))
    for name, values in extensions.items():
        if len(values) != cell_count:
            raise ContractViolation(
                f"Sidecar '{name}' has {len(values)} entries; expected {cell_count}"
            )
        for index, value in enumerate(values):
            if isinstance(value, (int, float)) and not math.isfinite(float(value)):
                raise ContractViolation(f"Non-finite value in '{name}' at cell {index}")


def validate_bond_edges(
    edges: Iterable[tuple[int, int, float]],
    cell_count: int,
) -> tuple[tuple[int, int, float], ...]:
    """Canonical undirected bond list with finite positive rest lengths."""
    if cell_count < 1:
        raise ContractViolation("cell_count must be positive")
    canonical = []
    seen = set()
    for a, b, rest_length in edges:
        if not (0 <= a < cell_count and 0 <= b < cell_count):
            raise ContractViolation(f"Bond endpoint out of range: {(a, b)}")
        if a == b:
            raise ContractViolation("Self-bonds are forbidden")
        if not math.isfinite(rest_length) or rest_length <= 0:
            raise ContractViolation("Bond rest length must be finite and positive")
        edge = (min(a, b), max(a, b))
        if edge in seen:
            raise ContractViolation(f"Duplicate undirected bond: {edge}")
        seen.add(edge)
        canonical.append((edge[0], edge[1], float(rest_length)))
    return tuple(sorted(canonical))


def normalize_quaternion_xyzw(q: Sequence[float], *, tolerance: float = 1e-6) -> tuple[float, float, float, float]:
    """Normalize a true rotational state; reject zero/non-finite quaternions."""
    if len(q) != 4:
        raise ContractViolation("Quaternion must have four components in xyzw order")
    values = tuple(float(v) for v in q)
    if not all(math.isfinite(v) for v in values):
        raise ContractViolation("Quaternion components must be finite")
    norm = math.sqrt(sum(v * v for v in values))
    if norm <= tolerance:
        raise ContractViolation("Quaternion norm is too close to zero")
    return tuple(v / norm for v in values)


def validate_phase_schedule(schedule: Sequence[int] = VORTEX_PHASE_SCHEDULE) -> tuple[int, ...]:
    """Preserve the named six-phase schedule as an empirical candidate, not a physics law."""
    result = tuple(int(v) for v in schedule)
    if len(result) != 6 or len(set(result)) != 6:
        raise ContractViolation("TEC-Q phase candidate must contain six distinct states")
    if result != VORTEX_PHASE_SCHEDULE:
        raise ContractViolation(
            "The canonical candidate is [1, 2, 4, 8, 7, 5]; alternatives belong in experiments"
        )
    return result


def phase_experiment_baselines() -> tuple[str, ...]:
    """Mandatory controls before attributing value to the canonical phase schedule."""
    return (
        "canonical_1_2_4_8_7_5",
        "uniform_six_state_cycle",
        "randomized_six_state_schedule",
        "learned_schedule",
        "sinusoidal_phase_coupling",
        "phase_coupling_disabled",
    )


def quaternion_is_valid(q: Sequence[float], *, tolerance: float = 1e-3) -> bool:
    try:
        normalized = normalize_quaternion_xyzw(q)
    except (ContractViolation, TypeError, ValueError):
        return False
    norm = math.sqrt(sum(v * v for v in q))
    return abs(norm - 1.0) <= tolerance and len(normalized) == 4
