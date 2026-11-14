"""Seeded TEC-Q swarm ablation with explicit structural recovery checks."""
from __future__ import annotations

import random
import time
from copy import deepcopy
from dataclasses import replace
from typing import Any

from .engine import TECQConfig, TECQEngine, lattice_state


def _coordination(engine: TECQEngine) -> float:
    s = engine.state
    scores = []
    for i, row in enumerate(s.adjacency):
        if not row:
            continue
        total = sum(s.bonds[key].weight for _, key in row)
        if total <= 0:
            continue
        neighbor = sum(s.activation[j] * s.bonds[key].weight for j, key in row) / total
        scores.append(1.0 - min(1.0, abs(s.activation[i] - neighbor)))
    return sum(scores) / len(scores) if scores else 0.0


def _condition(name: str, base: TECQConfig) -> TECQConfig:
    if name == "independent":
        return replace(base, neighbor_radius=base.spacing * .5, topology_interval=0,
                       torsion_k=0.0, field_diffusion=0.0)
    if name == "fixed":
        return replace(base, topology_interval=0, torsion_k=0.0, field_diffusion=0.0)
    if name == "adaptive":
        return replace(base, topology_interval=max(1, base.topology_interval),
                       torsion_k=0.0, field_diffusion=0.0)
    if name == "full":
        return base
    raise ValueError(f"unknown condition: {name}")


def _structural_recovery_fraction(state, damaged_ids: set[int]) -> float:
    """Fraction of damaged cells in a component that also contains an undamaged cell."""
    if not damaged_ids:
        return 1.0
    seen: set[int] = set()
    recovered: set[int] = set()
    for root in range(state.count):
        if root in seen:
            continue
        stack = [root]
        component: set[int] = set()
        seen.add(root)
        while stack:
            node = stack.pop()
            component.add(node)
            for neighbor, _ in state.adjacency[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        if component - damaged_ids:
            recovered.update(component & damaged_ids)
    return len(recovered) / len(damaged_ids)


def _seeded_initial_state(config: TECQConfig, rng: random.Random):
    state = lattice_state(config)
    # Small seeded heterogeneity avoids four identical, perfectly symmetric trials
    # while keeping the same initial condition across all four ablation arms.
    for i in range(state.count):
        state.phase[i] = rng.random() * 6.283185307179586
        state.energy[i] = .88 + .04 * rng.random()
        state.stress[i] = .03 + .04 * rng.random()
        state.memory[i] = .01 * rng.random()
        state.cohesion[i] = .45 + .10 * rng.random()
    return state


def run_swarm_ablation(*, cell_count: int = 512, steps: int = 160,
                       pulse_ticks: int = 12, damage_tick: int = 24,
                       damage_fraction: float = .02, seed: int = 7) -> dict[str, Any]:
    """Compare four architectures under matched initial conditions and tick budgets.

    A seed selects the shared initial heterogeneity and interventions. Repeating a
    seed is deterministic; changing it changes the trial. Tick budgets are matched,
    but hardware work is not: report work estimates and wall time separately.
    """
    if cell_count < 8 or steps < 1 or pulse_ticks < 0 or damage_tick < 0:
        raise ValueError("invalid experiment size or timing")
    if not 0 < damage_fraction <= .25:
        raise ValueError("damage_fraction must be in (0, .25]")
    base = TECQConfig(cell_count=cell_count, seed=seed)
    rng = random.Random(seed)
    shared = _seeded_initial_state(base, rng)
    ids = list(range(cell_count))
    rng.shuffle(ids)
    affected_count = max(1, int(cell_count * .05))
    damaged_count = max(1, int(cell_count * damage_fraction))
    affected_ids = set(ids[:affected_count])
    damaged_ids = set(ids[affected_count:affected_count + damaged_count])
    # Ensure damage does not accidentally target the exact sensory-pulse cohort.
    if not damaged_ids:
        damaged_ids = {ids[-1]}

    results = []
    for name in ("independent", "fixed", "adaptive", "full"):
        cfg = _condition(name, base)
        state = type(shared).from_checkpoint(shared.checkpoint())
        engine = TECQEngine(state, cfg)
        start = time.perf_counter()
        baseline_stress = sum(state.stress) / cell_count
        stable = 0
        recovery_tick = None
        initial_bonds = len(state.bonds)
        for tick in range(steps):
            drive = [1.0 if i in affected_ids and tick < pulse_ticks else 0.0
                     for i in range(cell_count)]
            if tick == damage_tick:
                for i in damaged_ids:
                    state.energy[i] = .25
                    state.stress[i] = .75
                    state.position[i][0] += .12
            metrics = engine.step(drive)
            if tick >= damage_tick:
                structural_fraction = _structural_recovery_fraction(state, damaged_ids)
                recovered = (
                    structural_fraction >= .95
                    and metrics["mean_stress"] <= baseline_stress + .02
                    and metrics["mean_prediction_error"] <= .05
                )
                stable = stable + 1 if recovered else 0
                if stable >= 8 and recovery_tick is None:
                    recovery_tick = tick + 1
        elapsed = time.perf_counter() - start
        metrics = engine.metrics()
        structural_fraction = _structural_recovery_fraction(state, damaged_ids)
        results.append({
            "condition": name,
            "cells": cell_count,
            "steps": steps,
            "initial_bonds": initial_bonds,
            "final_bonds": len(state.bonds),
            "recovery_tick": recovery_tick,
            "structural_recovery_fraction": structural_fraction,
            "coordination_index": _coordination(engine),
            "mean_energy": metrics["mean_energy"],
            "mean_stress": metrics["mean_stress"],
            "mean_memory": metrics["mean_memory"],
            "mean_cohesion": metrics["mean_cohesion"],
            "mean_activation": metrics["mean_activation"],
            "mean_swarm_intent": metrics["mean_swarm_intent"],
            "mean_prediction_error": metrics["mean_prediction_error"],
            "max_strain": metrics["max_strain"],
            "estimated_work_units": engine.isce_projection()["estimated_work_units"],
            "wall_seconds": elapsed,
            "state_digest": metrics["state_digest"],
        })
    return {
        "experiment": "tecq-swarm-ablation-v2",
        "protocol": {
            "cell_count": cell_count,
            "steps": steps,
            "pulse_ticks": pulse_ticks,
            "damage_tick": damage_tick,
            "damage_fraction": damage_fraction,
            "affected_fraction": len(affected_ids) / cell_count,
            "same_initial_state_across_conditions": True,
            "same_tick_budget": True,
            "equal_hardware_compute_budget": False,
            "seed": seed,
            "damaged_cell_ids": sorted(damaged_ids),
            "affected_cell_ids": sorted(affected_ids),
        },
        "results": results,
        "interpretation": (
            "Compare outcomes across conditions and seeds. Structural recovery "
            "requires damaged cells to remain connected to an undamaged cell. "
            "Equal tick budgets are not equal hardware-compute budgets."
        ),
    }
