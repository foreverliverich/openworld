"""Deterministic TEC-Q swarm ablation experiment; reports evidence, never conclusions."""
from __future__ import annotations
import time
from dataclasses import replace
from typing import Any

from .engine import TECQConfig, TECQEngine, lattice_state


def _coordination(engine: TECQEngine) -> float:
    s=engine.state; scores=[]
    for i,row in enumerate(s.adjacency):
        if not row: continue
        total=sum(s.bonds[key].weight for _,key in row)
        if total<=0: continue
        neighbor=sum(s.activation[j]*s.bonds[key].weight for j,key in row)/total
        scores.append(1.0-min(1.0,abs(s.activation[i]-neighbor)))
    return sum(scores)/len(scores) if scores else 0.0


def _condition(name: str, base: TECQConfig) -> TECQConfig:
    if name=="independent":
        return replace(base,neighbor_radius=base.spacing*.5,topology_interval=0,
                       torsion_k=0.0,field_diffusion=0.0)
    if name=="fixed":
        return replace(base,topology_interval=0,torsion_k=0.0,field_diffusion=0.0)
    if name=="adaptive":
        return replace(base,topology_interval=max(1,base.topology_interval),
                       torsion_k=0.0,field_diffusion=0.0)
    if name=="full":
        return base
    raise ValueError(f"unknown condition: {name}")


def run_swarm_ablation(*, cell_count: int=512, steps: int=160,
                       pulse_ticks: int=12, damage_tick: int=24,
                       damage_fraction: float=.02, seed: int=7) -> dict[str, Any]:
    """Run four architectures with identical population, drive and tick budget."""
    if cell_count<8 or steps<1 or pulse_ticks<0 or damage_tick<0:
        raise ValueError("invalid experiment size or timing")
    if not 0<damage_fraction<=.25:
        raise ValueError("damage_fraction must be in (0, .25]")
    base=TECQConfig(cell_count=cell_count,seed=seed)
    affected=max(1,int(cell_count*.05))
    damaged=max(1,int(cell_count*damage_fraction))
    results=[]
    for name in ("independent","fixed","adaptive","full"):
        cfg=_condition(name,base); state=lattice_state(cfg); engine=TECQEngine(state,cfg)
        start=time.perf_counter(); baseline_stress=sum(state.stress)/cell_count
        stable=0; recovery_tick=None; initial_bonds=len(state.bonds)
        for tick in range(steps):
            drive=[1.0 if i<affected and tick<pulse_ticks else 0.0
                   for i in range(cell_count)]
            if tick==damage_tick:
                for i in range(damaged):
                    state.energy[i]=.25; state.stress[i]=.75
                    state.position[i][0]+=.12
            metrics=engine.step(drive)
            if tick>=damage_tick:
                recovered=(metrics["mean_stress"]<=baseline_stress+.02
                           and metrics["mean_prediction_error"]<=.05)
                stable=stable+1 if recovered else 0
                if stable>=8 and recovery_tick is None:
                    recovery_tick=tick+1
        elapsed=time.perf_counter()-start
        metrics=engine.metrics()
        results.append({
            "condition":name,"cells":cell_count,"steps":steps,
            "initial_bonds":initial_bonds,"final_bonds":len(state.bonds),
            "recovery_tick":recovery_tick,"coordination_index":_coordination(engine),
            "mean_energy":metrics["mean_energy"],"mean_stress":metrics["mean_stress"],
            "mean_memory":metrics["mean_memory"],"mean_cohesion":metrics["mean_cohesion"],
            "mean_activation":metrics["mean_activation"],
            "mean_swarm_intent":metrics["mean_swarm_intent"],
            "mean_prediction_error":metrics["mean_prediction_error"],
            "max_strain":metrics["max_strain"],
            "estimated_work_units":engine.isce_projection()["estimated_work_units"],
            "wall_seconds":elapsed,"state_digest":metrics["state_digest"],
        })
    return {
        "experiment":"tecq-swarm-ablation-v1",
        "protocol":{"cell_count":cell_count,"steps":steps,"pulse_ticks":pulse_ticks,
                    "damage_tick":damage_tick,"damage_fraction":damage_fraction,
                    "affected_fraction":.05,"same_tick_budget":True,
                    "hardware_work_measured":False,"seed":seed},
        "results":results,
        "interpretation":"Compare measured outcomes; this harness does not presume the full system wins.",
    }
