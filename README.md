# Chimera Open World — Reality Engine foundation

This repository is the persistent world substrate for Project Chimera. It is not
a chatbot avatar controller and it is not a renderer-owned game scene.

## Core invariant

**The database-backed world state is authoritative.** Cognition proposes edits;
the Reality Engine validates and commits them; physics changes state; perception
reads the committed state; memory can record the resulting observation. Rendering
is a projection of that state and cannot silently invent world changes.

## Current implementation

`chimera/reality_engine.py` is a standard-library Python implementation:

- SQLite WAL persistence with durable transactions.
- Monotonic world revision and optimistic concurrency checks.
- Atomic multi-part structure construction.
- Stable entity IDs, material labels, mass, transforms, dimensions and metadata.
- AABB intersection checks and static support checks.
- Fixed-step gravity and ground/platform contact for dynamic box bodies.
- Four persistent scalar fields: energy, stress, memory and cohesion.
- Local observations, snapshots and a SHA-256 chained event journal.
- `OrganismKernel`: allostatic physiology and compact cognitive variables read
  local fields and atomically write the resulting organism state back into the
  same world revision.

The first physics model is intentionally explicit and bounded: axis-aligned box
colliders, simple gravity and vertical support contacts. It is not a full rigid
body engine, deformable tissue solver, fluid solver or voxel terrain system.
Rapier is a candidate for the next physics adapter; it has not yet been wired in.

## TEC-Q / seed / Fold contract

The canonical integration law is in [docs/TECQ-1KB-SEED-FOLD-BLUEPRINT.md](docs/TECQ-1KB-SEED-FOLD-BLUEPRINT.md), with a machine-readable companion at [docs/tecq-architecture-contract.json](docs/tecq-architecture-contract.json). Executable boundary checks live in `chimera/tecq/contract.py`; run their tests with:

```bash
python -m unittest discover -s tests -p "test_tecq_contract.py" -v
```

These contracts preserve the 48-byte SomaticCell ABI, distinguish the compact identity seed from 4KB form genes and SEED2, and refuse to call a compact fold lossless without a complete external checkpoint. They do not claim that the TEC-Q solver or GPU implementation is complete.

## Quick start

Python 3.10+; no third-party package is required for the core.

```bash
python -m chimera.reality_engine
python -m unittest discover -s tests -v
```

The demo creates a foundation, constructs a supported block and injects a memory
field. It prints an observation and verifies the event hash chain.

## Construction API

A multi-part structure is committed as one transaction. Parts are processed in
blueprint order, so a later part can be supported by an earlier part.

```python
from chimera.reality_engine import RealityEngine, WorldConfig

world = RealityEngine(WorldConfig(database="world.sqlite3"))

result = world.create_structure({
    "name": "organism_shelter",
    "parts": [
        {
            "kind": "foundation",
            "position": [0, 0.5, 0],
            "size": [4, 1, 4],
            "material": "stone",
            "mass": 80,
            "dynamic": False
        },
        {
            "kind": "wall",
            "position": [0, 2.0, -1.5],
            "size": [4, 2, 0.25],
            "material": "wood",
            "mass": 15,
            "dynamic": False
        }
    ]
}, actor_id="chimera", expected_revision=world.revision())

observation = world.observe(center=(0, 1, 0), radius=12)
print(result)
print(observation)
world.close()
```

The example above is a blueprint illustration. The static wall placement must
satisfy the support and non-intersection rules of the current box model; build
and validate each proposed blueprint against the actual world before treating it
as a successful design.

## Creation toolbox

`ChimeraToolbox` exposes the existing six-domain game/toolbox direction through one callable API. It does not create a second world model: every persistent mutation is delegated to the same `RealityEngine` transaction boundary.

| Tool | Working actions in this branch |
|---|---|
| Body Forge | Create and inspect persistent body/anatomy prototypes |
| World Builder | Create objects, atomically build structures, inspect the world |
| Tool Fabricator | Fabricate and inspect persistent tool-item entities with declared capabilities |
| Life Generator | Spawn and inspect organism prototype entities with identity/species/genome references |
| Movement Lab | Move entities through world validation and advance fixed-step physics |
| Research Lab | Observe entities, read local fields, inspect event history and export snapshots |

The first implementation deliberately distinguishes **a world entity** from a fully articulated body, executable tool, or independently running agent. Body prototypes are currently rigid primitive representations; fabricated tools are persistent items whose capabilities are metadata, not yet executable device drivers; Life Generator creates an organism prototype, not a separately scheduled autonomous organism. These are honest extension seams, not simulated completion.

Example:

```python
from chimera import ChimeraToolbox, RealityEngine, WorldConfig

world = RealityEngine(WorldConfig(database="chimera.sqlite3"))
tools = ChimeraToolbox(world, actor_id="player")

result = tools.execute(
    "world_builder", "create_object",
    {
        "kind": "stone",
        "position": [0, 0.5, 0],
        "size": [1, 1, 1],
        "material": "granite",
        "dynamic": False
    }
)
print(result)  # accepted flag, entity ID and committed world revision
world.close()
```

Tool definitions are discoverable with `tools.manifest()`. Every mutation supports an expected world revision; stale plans are rejected instead of overwriting newer state. Run the toolbox tests with:

```bash
python -m unittest discover -s tests -p "test_toolbox.py" -v
```

## Autonomous organism runtime

`OrganismKernel` is the first coupled organism-state mechanism. The local
world fields feed back into energy/stress/memory regulation; the resulting
organism state is then written back into the same spatial field cell. The state
and field write share one SQLite transaction and one world revision.

`AutonomousWorldAgent` supplies a transparent baseline developmental policy:
it detects the absence of a shelter, builds a six-part shelter, then builds a
five-part workbench, then observes the environment and consolidates a memory
signal. Low energy triggers a genuine rest-regulation tick. These are executable
baseline behaviors, not learned general intelligence.

`AutonomousRuntime` owns fixed-step simulation advancement and can run
asynchronously without a renderer:

```python
import asyncio
from chimera import (
    RealityEngine, WorldConfig, OrganismKernel,
    AutonomousWorldAgent, AutonomousRuntime,
)

async def main():
    world = RealityEngine(WorldConfig(database="chimera.sqlite3"))
    organism = OrganismKernel(world, "chimera")
    agent = AutonomousWorldAgent(world, organism)
    runtime = AutonomousRuntime(world, agent)

    stop = asyncio.Event()
    try:
        await runtime.run(stop, max_ticks=300)
        print(runtime.snapshot())
    finally:
        world.close()

asyncio.run(main())
```

The runtime's current developmental policy is intentionally small and
inspectable. The next step is to replace hard-coded milestone selection with
goal formation from the existing latent-language, learning, spatial-memory and
somatic systems, while keeping the same validated world-action boundary.

## Event and state contract

Every accepted mutation:
1. checks the caller's expected revision when supplied;
2. validates the action against current committed entities;
3. commits entity/field changes and an event in the same SQLite transaction;
4. increments the global world revision exactly once.

A rejected action changes neither entities nor revision. This supports causal
auditability and stale-plan rejection. The event journal is hash chained to make
tampering detectable. It is not yet a complete replay engine: field diffusion
and every physics substep are not currently encoded as replay-complete deltas.

## Next integration boundary

The next layer must connect existing Chimera systems without creating a second
source of truth:

- `EnvironmentEngine`: adapter to/from canonical Reality Engine observations.
- `SensoryProcessor`: convert committed observations and events into sensory
  inputs.
- `Somatic physiology`: constrain action selection using energy, stress,
  integrity and repair state.
- `SpatialMemory`: store grounded entities, relations and observed changes.
- `LearningSystem`: store successful/failed construction methods as reusable
  skills with outcome evidence.
- `UnifiedConsciousnessIntegration` / autonomous coordinator: propose goals and
  plans, never write directly to renderer state.
- Three.js frontend: subscribe to revisioned world snapshots/deltas.

Do not run a second physics simulation in the frontend. Do not claim that a
blueprint was built until the Reality Engine has committed it and returned the
new revision.

## Current status and limitations

This is a committed implementation foundation, not yet integrated into the
existing uploaded FastAPI/Flask application. The uploaded code has multiple
runtime entry points and websocket ports; those must be reconciled deliberately
before connecting the frontend. The test suite is committed but has not been
executed in this environment. Run the command above locally and fix any
platform-specific issues before relying on it.

The organism kernel now has a real two-way coupling with local scalar fields:
environmental fields modulate energy/stress/memory regulation, and the organism's
updated physiology is committed back into those fields in the same transaction.
The fields do not yet deform geometry, and the cognitive variables are a compact
state model rather than a trained cognitive architecture. Those are subsequent
research and implementation milestones.
