"""
Chimera Reality Engine — persistent, transactional world substrate.

Standard-library implementation. The SQLite database is authoritative; renderers
and agent planners are clients of this state, never its owners.

Implemented:
- revisioned world state and optimistic concurrency
- atomic world-edit transactions and append-only event journal
- primitive construction, movement, removal
- AABB collision and support validation
- deterministic fixed-step gravity/contact simulation
- persistent morphogenic scalar fields (energy, stress, memory, cohesion)
- snapshots, grounded observations, and tamper-evident event history

This is a deliberately bounded first substrate: axis-aligned box colliders and a
regular field lattice. It does not claim deformable-body, fluid, or full terrain
physics. Those can be added without changing the transaction/event contract.
"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional


ENGINE_VERSION = "0.1.0"
FIELD_NAMES = ("energy", "stress", "memory", "cohesion")
EPSILON = 1e-7


class WorldError(RuntimeError):
    """Base class for rejected or failed world operations."""


class RevisionConflict(WorldError):
    """The caller planned against a stale world revision."""


class InvalidWorldAction(WorldError):
    """The requested edit violates world invariants."""


class EntityNotFound(WorldError):
    """An entity ID does not exist."""


class ActionType(str, Enum):
    CREATE = "create"
    MOVE = "move"
    REMOVE = "remove"
    FIELD_INJECT = "field_inject"
    PHYSICS_STEP = "physics_step"
    ORGANISM_TICK = "organism_tick"
    SOMATIC_MORPH = "somatic_morph"


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.x, self.y, self.z)):
            raise ValueError("Vector components must be finite")

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @classmethod
    def from_value(cls, value: Iterable[float] | dict[str, float]) -> "Vec3":
        """Normalize tuple/list coordinates and persisted {x, y, z} vectors.

        OrganismState serializes Vec3 as a named mapping for durable JSON
        storage; accepting that representation here keeps the database and
        runtime vector contracts consistent without changing the stored schema.
        """
        if isinstance(value, dict):
            try:
                x, y, z = value["x"], value["y"], value["z"]
            except KeyError as exc:
                raise ValueError("Vector mappings require x, y and z") from exc
        else:
            try:
                x, y, z = value
            except (TypeError, ValueError) as exc:
                raise ValueError("A vector must contain exactly three components") from exc
        return cls(float(x), float(y), float(z))


@dataclass(frozen=True)
class WorldConfig:
    database: str = "chimera_world.sqlite3"
    bounds_min: Vec3 = Vec3(-64.0, 0.0, -64.0)
    bounds_max: Vec3 = Vec3(64.0, 128.0, 64.0)
    gravity: float = 9.81
    fixed_dt: float = 1.0 / 30.0
    max_entities: int = 100_000
    contact_tolerance: float = 0.025
    field_cell_size: float = 1.0
    field_diffusion: float = 0.08
    field_decay: float = 0.002


@dataclass(frozen=True)
class Entity:
    entity_id: str
    kind: str
    position: Vec3
    size: Vec3
    mass: float
    material: str
    dynamic: bool
    velocity: Vec3
    creator_id: str
    created_at: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in ("position", "size", "velocity"):
            result[key] = asdict(getattr(self, key))
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        return cls(
            entity_id=str(data["entity_id"]),
            kind=str(data["kind"]),
            position=Vec3(**data["position"]),
            size=Vec3(**data["size"]),
            mass=float(data["mass"]),
            material=str(data["material"]),
            dynamic=bool(data["dynamic"]),
            velocity=Vec3(**data["velocity"]),
            creator_id=str(data["creator_id"]),
            created_at=float(data["created_at"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class WorldResult:
    action_id: str
    revision: int
    action: str
    entity_id: Optional[str]
    accepted: bool
    details: dict[str, Any]


class RealityEngine:
    """
    Canonical world state and transactional action boundary.

    All public mutations execute under a SQLite write transaction. Each accepted
    mutation increments the global revision and records a durable event in the
    same transaction. A failed validation leaves both unchanged.
    """

    def __init__(self, config: Optional[WorldConfig] = None):
        self.config = config or WorldConfig()
        self._lock = threading.RLock()
        self._db = sqlite3.connect(
            self.config.database, check_same_thread=False, isolation_level=None
        )
        self._db.row_factory = sqlite3.Row
        self._configure_database()
        self._initialize_schema()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _configure_database(self) -> None:
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA busy_timeout=5000")

    def _initialize_schema(self) -> None:
        self._db.executescript("""
        CREATE TABLE IF NOT EXISTS world_meta (
            singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
            revision INTEGER NOT NULL,
            simulation_time REAL NOT NULL
        );
        INSERT OR IGNORE INTO world_meta(singleton, revision, simulation_time)
        VALUES(1, 0, 0.0);

        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS world_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id TEXT NOT NULL UNIQUE,
            revision INTEGER NOT NULL,
            simulation_time REAL NOT NULL,
            action_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            entity_id TEXT,
            payload TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS organism_state (
            singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
            payload TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS somatic_morphology (
            singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
            payload TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS field_cells (
            ix INTEGER NOT NULL,
            iy INTEGER NOT NULL,
            iz INTEGER NOT NULL,
            energy REAL NOT NULL DEFAULT 0,
            stress REAL NOT NULL DEFAULT 0,
            memory REAL NOT NULL DEFAULT 0,
            cohesion REAL NOT NULL DEFAULT 0,
            PRIMARY KEY(ix, iy, iz)
        );

        CREATE INDEX IF NOT EXISTS idx_events_revision
        ON world_events(revision);
        """)

    def _transaction(self):
        return self._db

    def _begin(self) -> None:
        self._db.execute("BEGIN IMMEDIATE")

    def _commit(self) -> None:
        self._db.execute("COMMIT")

    def _rollback(self) -> None:
        if self._db.in_transaction:
            self._db.execute("ROLLBACK")

    def revision(self) -> int:
        row = self._db.execute(
            "SELECT revision FROM world_meta WHERE singleton=1"
        ).fetchone()
        return int(row["revision"])

    def simulation_time(self) -> float:
        row = self._db.execute(
            "SELECT simulation_time FROM world_meta WHERE singleton=1"
        ).fetchone()
        return float(row["simulation_time"])

    def _check_revision(self, expected_revision: Optional[int]) -> int:
        current = self.revision()
        if expected_revision is not None and expected_revision != current:
            raise RevisionConflict(
                f"Expected revision {expected_revision}; current revision is {current}"
            )
        return current

    def _load_entities(self) -> list[Entity]:
        rows = self._db.execute(
            "SELECT payload FROM entities ORDER BY entity_id"
        ).fetchall()
        return [Entity.from_dict(json.loads(row["payload"])) for row in rows]

    def get_entity(self, entity_id: str) -> Entity:
        row = self._db.execute(
            "SELECT payload FROM entities WHERE entity_id=?", (entity_id,)
        ).fetchone()
        if row is None:
            raise EntityNotFound(entity_id)
        return Entity.from_dict(json.loads(row["payload"]))

    def entities(self) -> list[Entity]:
        with self._lock:
            return self._load_entities()

    @staticmethod
    def _aabb(entity: Entity) -> tuple[float, float, float, float, float, float]:
        p, s = entity.position, entity.size
        hx, hy, hz = s.x / 2.0, s.y / 2.0, s.z / 2.0
        return (p.x-hx, p.y-hy, p.z-hz, p.x+hx, p.y+hy, p.z+hz)

    @staticmethod
    def _overlaps(a: Entity, b: Entity, tolerance: float = 0.0) -> bool:
        ax0, ay0, az0, ax1, ay1, az1 = RealityEngine._aabb(a)
        bx0, by0, bz0, bx1, by1, bz1 = RealityEngine._aabb(b)
        return (
            ax0 < bx1 - tolerance and ax1 > bx0 + tolerance
            and ay0 < by1 - tolerance and ay1 > by0 + tolerance
            and az0 < bz1 - tolerance and az1 > bz0 + tolerance
        )

    def _validate_bounds(self, entity: Entity) -> None:
        x0, y0, z0, x1, y1, z1 = self._aabb(entity)
        lo, hi = self.config.bounds_min, self.config.bounds_max
        if (x0 < lo.x or y0 < lo.y - self.config.contact_tolerance
                or z0 < lo.z or x1 > hi.x or y1 > hi.y or z1 > hi.z):
            raise InvalidWorldAction("Entity would extend outside world bounds")

    def _validate_geometry(self, entity: Entity) -> None:
        if entity.size.x <= 0 or entity.size.y <= 0 or entity.size.z <= 0:
            raise InvalidWorldAction("Primitive dimensions must all be positive")
        if entity.mass <= 0 or not math.isfinite(entity.mass):
            raise InvalidWorldAction("Mass must be finite and greater than zero")
        self._validate_bounds(entity)

    def _has_support(self, entity: Entity, others: list[Entity]) -> bool:
        bottom = self._aabb(entity)[1]
        if abs(bottom - self.config.bounds_min.y) <= self.config.contact_tolerance:
            return True
        ex0, _, ez0, ex1, _, ez1 = self._aabb(entity)
        for other in others:
            ox0, _, oz0, ox1, oy1, oz1 = self._aabb(other)
            horizontal_overlap = (
                min(ex1, ox1) - max(ex0, ox0) > self.config.contact_tolerance
                and min(ez1, oz1) - max(ez0, oz0) > self.config.contact_tolerance
            )
            if horizontal_overlap and abs(bottom - oy1) <= self.config.contact_tolerance:
                return True
        return False

    def _validate_placement(self, candidate: Entity, entities: list[Entity],
                            ignore_id: Optional[str] = None) -> None:
        self._validate_geometry(candidate)
        others = [e for e in entities if e.entity_id != ignore_id]
        for other in others:
            if self._overlaps(candidate, other, self.config.contact_tolerance * 0.1):
                raise InvalidWorldAction(f"Placement intersects entity {other.entity_id}")
        # Dynamic bodies may be spawned airborne and then resolve contacts
        # through the fixed-step physics integrator. Static construction must
        # have support at commit time.
        if not candidate.dynamic and not self._has_support(candidate, others):
            raise InvalidWorldAction(
                "Static construction is unsupported; place it on the ground or on a supporting entity"
            )

    def _event_hash(self, previous_hash: str, event_body: dict[str, Any]) -> str:
        import hashlib
        canonical = json.dumps(event_body, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256((previous_hash + canonical).encode("utf-8")).hexdigest()

    def _append_event(self, action_id: str, revision: int, action_type: ActionType,
                      actor_id: str, entity_id: Optional[str],
                      payload: dict[str, Any]) -> None:
        previous = self._db.execute(
            "SELECT event_hash FROM world_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else "GENESIS"
        sim_time = self.simulation_time()
        body = {
            "action_id": action_id, "revision": revision,
            "simulation_time": sim_time, "action_type": action_type.value,
            "actor_id": actor_id, "entity_id": entity_id, "payload": payload,
        }
        event_hash = self._event_hash(previous_hash, body)
        self._db.execute("""
            INSERT INTO world_events(action_id, revision, simulation_time,
                action_type, actor_id, entity_id, payload, previous_hash, event_hash)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (action_id, revision, sim_time, action_type.value, actor_id,
              entity_id, json.dumps(payload, sort_keys=True), previous_hash, event_hash))

    def _advance_revision(self) -> int:
        self._db.execute(
            "UPDATE world_meta SET revision=revision+1 WHERE singleton=1"
        )
        return self.revision()

    def _store_entity(self, entity: Entity) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO entities(entity_id,payload) VALUES(?,?)",
            (entity.entity_id, json.dumps(entity.to_dict(), sort_keys=True)),
        )

    def create_primitive(
        self, kind: str, position: Iterable[float], size: Iterable[float],
        *, actor_id: str, material: str = "default", mass: float = 1.0,
        dynamic: bool = True, metadata: Optional[dict[str, Any]] = None,
        expected_revision: Optional[int] = None,
    ) -> WorldResult:
        action_id, entity_id = str(uuid.uuid4()), str(uuid.uuid4())
        now = time.time()
        candidate = Entity(
            entity_id=entity_id, kind=str(kind),
            position=Vec3.from_value(position), size=Vec3.from_value(size),
            mass=float(mass), material=str(material), dynamic=bool(dynamic),
            velocity=Vec3(0.0, 0.0, 0.0), creator_id=str(actor_id),
            created_at=now, metadata=dict(metadata or {}),
        )
        with self._lock:
            self._begin()
            try:
                self._check_revision(expected_revision)
                current = self._load_entities()
                if len(current) >= self.config.max_entities:
                    raise InvalidWorldAction("World entity capacity reached")
                self._validate_placement(candidate, current)
                self._store_entity(candidate)
                revision = self._advance_revision()
                self._append_event(action_id, revision, ActionType.CREATE, actor_id,
                                   entity_id, {"entity": candidate.to_dict()})
                self._commit()
                return WorldResult(action_id, revision, ActionType.CREATE.value,
                                   entity_id, True, {"entity": candidate.to_dict()})
            except Exception:
                self._rollback()
                raise

    def create_structure(
        self, blueprint: dict[str, Any], *, actor_id: str,
        expected_revision: Optional[int] = None,
    ) -> WorldResult:
        """
        Commit a multi-part construction as one world transaction.

        Blueprint format:
        {
          "name": "shelter",
          "parts": [
            {"kind":"foundation", "position":[0,0.5,0],
             "size":[4,1,4], "material":"stone", "mass":80,
             "dynamic":False, "metadata":{}}
          ]
        }

        Parts are validated in listed order, so later parts may be supported by
        earlier parts. No partial structure is committed on failure.
        """
        name = str(blueprint.get("name", "constructed_structure"))
        parts = blueprint.get("parts")
        if not isinstance(parts, list) or not parts:
            raise InvalidWorldAction("A structure blueprint requires a non-empty parts list")
        if len(parts) > 10_000:
            raise InvalidWorldAction("Structure blueprint exceeds 10000 parts")

        action_id = str(uuid.uuid4())
        structure_id = str(uuid.uuid4())
        now = time.time()
        candidates: list[Entity] = []
        for index, part in enumerate(parts):
            try:
                entity = Entity(
                    entity_id=str(uuid.uuid4()),
                    kind=str(part["kind"]),
                    position=Vec3.from_value(part["position"]),
                    size=Vec3.from_value(part["size"]),
                    mass=float(part.get("mass", 1.0)),
                    material=str(part.get("material", "default")),
                    dynamic=bool(part.get("dynamic", False)),
                    velocity=Vec3(0.0, 0.0, 0.0),
                    creator_id=str(actor_id),
                    created_at=now,
                    metadata={**dict(part.get("metadata", {})),
                              "structure_id": structure_id,
                              "part_index": index,
                              "structure_name": name},
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise InvalidWorldAction(
                    f"Invalid structure part at index {index}: {exc}"
                ) from exc
            candidates.append(entity)

        with self._lock:
            self._begin()
            try:
                self._check_revision(expected_revision)
                existing = self._load_entities()
                if len(existing) + len(candidates) > self.config.max_entities:
                    raise InvalidWorldAction("World entity capacity would be exceeded")
                staged = list(existing)
                for candidate in candidates:
                    self._validate_placement(candidate, staged)
                    staged.append(candidate)
                for candidate in candidates:
                    self._store_entity(candidate)
                revision = self._advance_revision()
                payload = {
                    "structure_id": structure_id,
                    "name": name,
                    "parts": [part.to_dict() for part in candidates],
                    "part_count": len(candidates),
                }
                self._append_event(action_id, revision, ActionType.CREATE,
                                   actor_id, structure_id, payload)
                self._commit()
                return WorldResult(
                    action_id, revision, "create_structure", structure_id, True,
                    {"name": name, "part_count": len(candidates),
                     "entity_ids": [part.entity_id for part in candidates]},
                )
            except Exception:
                self._rollback()
                raise

    def move_entity(
        self, entity_id: str, position: Iterable[float], *, actor_id: str,
        expected_revision: Optional[int] = None,
    ) -> WorldResult:
        action_id = str(uuid.uuid4())
        with self._lock:
            self._begin()
            try:
                self._check_revision(expected_revision)
                old = self.get_entity(entity_id)
                candidate = Entity(
                    entity_id=old.entity_id, kind=old.kind,
                    position=Vec3.from_value(position), size=old.size,
                    mass=old.mass, material=old.material, dynamic=old.dynamic,
                    velocity=Vec3(0.0, 0.0, 0.0), creator_id=old.creator_id,
                    created_at=old.created_at, metadata=old.metadata,
                )
                self._validate_placement(candidate, self._load_entities(), ignore_id=entity_id)
                self._store_entity(candidate)
                revision = self._advance_revision()
                self._append_event(action_id, revision, ActionType.MOVE, actor_id,
                                   entity_id, {"before": old.to_dict(),
                                               "after": candidate.to_dict()})
                self._commit()
                return WorldResult(action_id, revision, ActionType.MOVE.value,
                                   entity_id, True, {"position": asdict(candidate.position)})
            except Exception:
                self._rollback()
                raise

    def remove_entity(
        self, entity_id: str, *, actor_id: str,
        expected_revision: Optional[int] = None,
    ) -> WorldResult:
        action_id = str(uuid.uuid4())
        with self._lock:
            self._begin()
            try:
                self._check_revision(expected_revision)
                old = self.get_entity(entity_id)
                self._db.execute("DELETE FROM entities WHERE entity_id=?", (entity_id,))
                revision = self._advance_revision()
                self._append_event(action_id, revision, ActionType.REMOVE, actor_id,
                                   entity_id, {"removed": old.to_dict()})
                self._commit()
                return WorldResult(action_id, revision, ActionType.REMOVE.value,
                                   entity_id, True, {"removed": True})
            except Exception:
                self._rollback()
                raise

    def inject_field(
        self, field: str, position: Iterable[float], amount: float, *,
        actor_id: str, radius: int = 1,
        expected_revision: Optional[int] = None,
    ) -> WorldResult:
        if field not in FIELD_NAMES:
            raise InvalidWorldAction(f"Unknown field '{field}'")
        if not math.isfinite(amount) or radius < 0 or radius > 16:
            raise InvalidWorldAction("Invalid field amount or radius")
        p = Vec3.from_value(position)
        cell = self.config.field_cell_size
        center = (round(p.x / cell), round(p.y / cell), round(p.z / cell))
        action_id = str(uuid.uuid4())
        changed = []
        with self._lock:
            self._begin()
            try:
                self._check_revision(expected_revision)
                for ix in range(center[0]-radius, center[0]+radius+1):
                    for iy in range(center[1]-radius, center[1]+radius+1):
                        for iz in range(center[2]-radius, center[2]+radius+1):
                            distance = math.sqrt((ix-center[0])**2 +
                                                 (iy-center[1])**2 +
                                                 (iz-center[2])**2)
                            if distance > radius + EPSILON:
                                continue
                            weight = 1.0 if radius == 0 else max(0.0, 1.0-distance/(radius+1))
                            row = self._db.execute(
                                "SELECT * FROM field_cells WHERE ix=? AND iy=? AND iz=?",
                                (ix, iy, iz)).fetchone()
                            values = {name: (float(row[name]) if row else 0.0)
                                      for name in FIELD_NAMES}
                            before = values[field]
                            values[field] = max(-1.0, min(1.0, before + amount*weight))
                            self._db.execute("""
                                INSERT INTO field_cells(ix,iy,iz,energy,stress,memory,cohesion)
                                VALUES(?,?,?,?,?,?,?)
                                ON CONFLICT(ix,iy,iz) DO UPDATE SET
                                  energy=excluded.energy, stress=excluded.stress,
                                  memory=excluded.memory, cohesion=excluded.cohesion
                            """, (ix, iy, iz, values["energy"], values["stress"],
                                  values["memory"], values["cohesion"]))
                            changed.append({"cell": [ix, iy, iz],
                                            "field": field, "before": before,
                                            "after": values[field]})
                revision = self._advance_revision()
                payload = {"field": field, "center": center, "amount": amount,
                           "radius": radius, "changed_cells": changed}
                self._append_event(action_id, revision, ActionType.FIELD_INJECT,
                                   actor_id, None, payload)
                self._commit()
                return WorldResult(action_id, revision, ActionType.FIELD_INJECT.value,
                                   None, True, payload)
            except Exception:
                self._rollback()
                raise

    def somatic_morphology(self) -> Optional[dict[str, Any]]:
        """Read the canonical A/B SDF pair and derive morph progress from its start time."""
        with self._lock:
            row = self._db.execute(
                "SELECT payload FROM somatic_morphology WHERE singleton=1"
            ).fetchone()
            if row is None:
                return None
            state = json.loads(row["payload"])
            started = float(state.get("morph_started_at", 0.0))
            state["evolutionProgress"] = min(1.0, max(0.0, (time.time() - started) * 1.5))
            state["world_revision"] = self.revision()
            return state

    def apply_somatic_morphology(
        self, package: dict[str, Any], *, actor_id: str,
        expected_revision: Optional[int] = None,
    ) -> WorldResult:
        """Atomically replace the current SDF while retaining the previous SDF for A/B morphing."""
        required = {"label", "persona", "dialogue", "critique", "sdfScript", "color", "material"}
        if not isinstance(package, dict) or not required.issubset(package):
            raise InvalidWorldAction("Somatic package is missing required fields")
        script = package["sdfScript"]
        if not isinstance(script, str) or not 40 <= len(script) <= 24000:
            raise InvalidWorldAction("Somatic SDF must contain 40..24000 characters")
        if not isinstance(package["color"], list) or len(package["color"]) != 3:
            raise InvalidWorldAction("Somatic color must contain three channels")
        action_id = str(uuid.uuid4())
        with self._lock:
            self._begin()
            try:
                self._check_revision(expected_revision)
                row = self._db.execute(
                    "SELECT payload FROM somatic_morphology WHERE singleton=1"
                ).fetchone()
                previous = json.loads(row["payload"])["sdfScript"] if row else (
                    "vec2 map_object(vec3 p){vec2 h=sdHumanoidBase(p);"
                    "vec3 q=p-vec3(0.,.35,0.);"
                    "float armL=sdCapsule(q,vec3(-.28,.12,0.),vec3(-.48,-.35,0.),.095);"
                    "float armR=sdCapsule(q,vec3(.28,.12,0.),vec3(.48,-.35,0.),.095);"
                    "float legL=sdCapsule(p,vec3(-.16,-.42,0.),vec3(-.19,-.95,.02),.12);"
                    "float legR=sdCapsule(p,vec3(.16,-.42,0.),vec3(.19,-.95,.02),.12);"
                    "float d=smin(h.x,armL,.09);d=smin(d,armR,.09);"
                    "d=smin(d,legL,.1);d=smin(d,legR,.1);"
                    "vec3 w=opLatentWarp(p,.012);d=opFur(d,w,2.8,.006);"
                    "return vec2(d,1.);}"
                )
                state = {
                    "label": str(package["label"])[:200],
                    "persona": str(package["persona"])[:2000],
                    "dialogue": str(package["dialogue"])[:2000],
                    "critique": str(package["critique"])[:2000],
                    "prevSdfScript": previous,
                    "sdfScript": script,
                    "color": package["color"],
                    "material": package["material"],
                    "iteration": int(json.loads(row["payload"]).get("iteration", 0) + 1) if row else 1,
                    "morph_started_at": time.time(),
                }
                self._db.execute(
                    "INSERT INTO somatic_morphology(singleton,payload) VALUES(1,?) "
                    "ON CONFLICT(singleton) DO UPDATE SET payload=excluded.payload",
                    (json.dumps(state, sort_keys=True),),
                )
                revision = self._advance_revision()
                self._append_event(
                    action_id, revision, ActionType.SOMATIC_MORPH, actor_id, None,
                    {"label": state["label"], "iteration": state["iteration"],
                     "previous_sdf": previous, "target_sdf": script,
                     "color": state["color"], "material": state["material"]},
                )
                self._commit()
                return WorldResult(
                    action_id, revision, ActionType.SOMATIC_MORPH.value, None, True,
                    {"label": state["label"], "iteration": state["iteration"],
                     "evolutionProgress": 0.0},
                )
            except Exception:
                self._rollback()
                raise

    def field_at(self, position: Iterable[float]) -> dict[str, float]:
        p = Vec3.from_value(position)
        cell = self.config.field_cell_size
        key = (round(p.x/cell), round(p.y/cell), round(p.z/cell))
        row = self._db.execute(
            "SELECT * FROM field_cells WHERE ix=? AND iy=? AND iz=?", key
        ).fetchone()
        return {name: float(row[name]) if row else 0.0 for name in FIELD_NAMES}

    def _integrate_entity(self, entity: Entity, dt: float,
                          entities: list[Entity]) -> Entity:
        if not entity.dynamic:
            return entity
        vy = entity.velocity.y - self.config.gravity * dt
        proposed = Vec3(entity.position.x,
                        entity.position.y + entity.velocity.y*dt
                        - 0.5*self.config.gravity*dt*dt,
                        entity.position.z)
        candidate = Entity(
            entity_id=entity.entity_id, kind=entity.kind, position=proposed,
            size=entity.size, mass=entity.mass, material=entity.material,
            dynamic=True, velocity=Vec3(entity.velocity.x, vy, entity.velocity.z),
            creator_id=entity.creator_id, created_at=entity.created_at,
            metadata=entity.metadata,
        )
        x0, y0, z0, x1, y1, z1 = self._aabb(candidate)
        ground = self.config.bounds_min.y
        if y0 <= ground:
            candidate = Entity(
                entity_id=candidate.entity_id, kind=candidate.kind,
                position=Vec3(candidate.position.x,
                               ground + candidate.size.y/2.0,
                               candidate.position.z),
                size=candidate.size, mass=candidate.mass,
                material=candidate.material, dynamic=candidate.dynamic,
                velocity=Vec3(0.0, 0.0, 0.0),
                creator_id=candidate.creator_id,
                created_at=candidate.created_at, metadata=candidate.metadata,
            )
            return candidate
        # Resolve downward landing on the highest supporting horizontal surface.
        old_bottom = self._aabb(entity)[1]
        best_top = None
        for other in entities:
            if other.entity_id == entity.entity_id:
                continue
            ox0, _, oz0, ox1, oy1, oz1 = self._aabb(other)
            horizontal = (min(x1, ox1)-max(x0, ox0) > self.config.contact_tolerance
                          and min(z1, oz1)-max(z0, oz0) > self.config.contact_tolerance)
            if horizontal and vy <= 0 and old_bottom >= oy1-self.config.contact_tolerance and y0 <= oy1:
                best_top = oy1 if best_top is None else max(best_top, oy1)
        if best_top is not None:
            candidate = Entity(
                entity_id=candidate.entity_id, kind=candidate.kind,
                position=Vec3(candidate.position.x,
                               best_top + candidate.size.y/2.0,
                               candidate.position.z),
                size=candidate.size, mass=candidate.mass,
                material=candidate.material, dynamic=candidate.dynamic,
                velocity=Vec3(0.0, 0.0, 0.0),
                creator_id=candidate.creator_id,
                created_at=candidate.created_at, metadata=candidate.metadata,
            )
        return candidate

    def step(self, *, actor_id: str = "runtime",
             expected_revision: Optional[int] = None) -> WorldResult:
        """Advance one deterministic fixed simulation step and persist the result."""
        action_id = str(uuid.uuid4())
        dt = self.config.fixed_dt
        with self._lock:
            self._begin()
            try:
                self._check_revision(expected_revision)
                before = self._load_entities()
                updated = []
                for entity in before:
                    updated.append(self._integrate_entity(entity, dt, before))
                for entity in updated:
                    self._store_entity(entity)
                self._db.execute(
                    "UPDATE world_meta SET simulation_time=simulation_time+? WHERE singleton=1",
                    (dt,))
                self._diffuse_fields()
                revision = self._advance_revision()
                changes = [
                    {"entity_id": old.entity_id,
                     "from": asdict(old.position), "to": asdict(new.position),
                     "velocity": asdict(new.velocity)}
                    for old, new in zip(before, updated)
                    if old.position != new.position or old.velocity != new.velocity
                ]
                self._append_event(action_id, revision, ActionType.PHYSICS_STEP,
                                   actor_id, None, {"dt": dt, "changes": changes})
                self._commit()
                return WorldResult(action_id, revision, ActionType.PHYSICS_STEP.value,
                                   None, True, {"dt": dt, "changes": changes,
                                                "simulation_time": self.simulation_time()})
            except Exception:
                self._rollback()
                raise

    def _diffuse_fields(self) -> None:
        rows = self._db.execute("SELECT * FROM field_cells").fetchall()
        if not rows:
            return
        current = {(r["ix"], r["iy"], r["iz"]):
                   {n: float(r[n]) for n in FIELD_NAMES} for r in rows}
        updates = {}
        diffusion, decay = self.config.field_diffusion, self.config.field_decay
        for key, values in current.items():
            neighbors = [current[k] for k in (
                (key[0]+1,key[1],key[2]), (key[0]-1,key[1],key[2]),
                (key[0],key[1]+1,key[2]), (key[0],key[1]-1,key[2]),
                (key[0],key[1],key[2]+1), (key[0],key[1],key[2]-1)
            ) if k in current]
            next_values = {}
            for name in FIELD_NAMES:
                mean = (sum(n[name] for n in neighbors)/len(neighbors)
                        if neighbors else values[name])
                value = values[name] + diffusion*(mean-values[name])
                value *= (1.0-decay)
                next_values[name] = max(-1.0, min(1.0, value))
            updates[key] = next_values
        for (ix,iy,iz), v in updates.items():
            self._db.execute("""
                UPDATE field_cells SET energy=?,stress=?,memory=?,cohesion=?
                WHERE ix=? AND iy=? AND iz=?
            """, (v["energy"],v["stress"],v["memory"],v["cohesion"],ix,iy,iz))

    def get_organism_state(self) -> Optional[dict[str, Any]]:
        """Read the persisted organism state, if one has been initialized."""
        row = self._db.execute(
            "SELECT payload FROM organism_state WHERE singleton=1"
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def commit_organism_tick(
        self, state: dict[str, Any], field_values: dict[str, float], *,
        actor_id: str, expected_revision: Optional[int] = None,
    ) -> WorldResult:
        """Atomically commit the single versioned ISCE state and local fields."""
        required = {"organism_id", "schema_version", "position", "body",
                    "interoception", "sensorimotor", "temporal",
                    "self_model", "attention", "resources"}
        if not required.issubset(state) or state.get("schema_version") != 1:
            raise InvalidWorldAction(
                "Only complete schema-v1 ISCE organism states may be committed"
            )
        if set(field_values) - set(FIELD_NAMES):
            raise InvalidWorldAction("Organism tick contains an unknown field")
        for name, value in field_values.items():
            if not math.isfinite(float(value)) or not -1.0 <= float(value) <= 1.0:
                raise InvalidWorldAction(f"Invalid normalized field value: {name}")
        position = Vec3.from_value(state["position"])
        cell_size = self.config.field_cell_size
        cell = (round(position.x/cell_size), round(position.y/cell_size),
                round(position.z/cell_size))
        action_id = str(uuid.uuid4())
        with self._lock:
            self._begin()
            try:
                self._check_revision(expected_revision)
                previous = self.get_organism_state()
                self._db.execute(
                    "INSERT INTO organism_state(singleton,payload) VALUES(1,?) "
                    "ON CONFLICT(singleton) DO UPDATE SET payload=excluded.payload",
                    (json.dumps(state, sort_keys=True),),
                )
                existing = self._db.execute(
                    "SELECT * FROM field_cells WHERE ix=? AND iy=? AND iz=?", cell
                ).fetchone()
                values = {name: (float(existing[name]) if existing else 0.0)
                          for name in FIELD_NAMES}
                values.update({name: float(value) for name, value in field_values.items()})
                self._db.execute("""
                    INSERT INTO field_cells(ix,iy,iz,energy,stress,memory,cohesion)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(ix,iy,iz) DO UPDATE SET
                      energy=excluded.energy, stress=excluded.stress,
                      memory=excluded.memory, cohesion=excluded.cohesion
                """, (cell[0], cell[1], cell[2], values["energy"], values["stress"],
                      values["memory"], values["cohesion"]))
                revision = self._advance_revision()
                payload = {
                    "organism_state_before": previous,
                    "organism_state_after": state,
                    "field_cell": cell,
                    "field_values": values,
                }
                self._append_event(action_id, revision, ActionType.ORGANISM_TICK,
                                   actor_id, str(state.get("organism_id", actor_id)), payload)
                self._commit()
                return WorldResult(action_id, revision, ActionType.ORGANISM_TICK.value,
                                   str(state.get("organism_id", actor_id)), True,
                                   {"state": state, "field_values": values, "cell": cell})
            except Exception:
                self._rollback()
                raise

    def observe(self, center: Iterable[float] = (0, 0, 0),
                radius: float = 20.0) -> dict[str, Any]:
        """Return a grounded local observation from authoritative world state."""
        c = Vec3.from_value(center)
        if radius < 0 or not math.isfinite(radius):
            raise ValueError("radius must be finite and non-negative")
        with self._lock:
            visible = []
            for entity in self._load_entities():
                dx = entity.position.x-c.x
                dy = entity.position.y-c.y
                dz = entity.position.z-c.z
                distance = math.sqrt(dx*dx+dy*dy+dz*dz)
                if distance <= radius:
                    visible.append({**entity.to_dict(), "distance": distance})
            return {
                "engine_version": ENGINE_VERSION,
                "revision": self.revision(),
                "simulation_time": self.simulation_time(),
                "observer_position": asdict(c),
                "entities": sorted(visible, key=lambda item: item["distance"]),
                "fields_at_observer": self.field_at(c.as_tuple()),
                "entity_count": len(self._load_entities()),
            }

    def event_history(self, after_revision: int = 0,
                      limit: int = 1000) -> list[dict[str, Any]]:
        if limit < 1 or limit > 100_000:
            raise ValueError("limit must be between 1 and 100000")
        rows = self._db.execute("""
            SELECT * FROM world_events WHERE revision>? ORDER BY sequence LIMIT ?
        """, (after_revision, limit)).fetchall()
        return [{
            "sequence": int(r["sequence"]), "action_id": r["action_id"],
            "revision": int(r["revision"]), "simulation_time": float(r["simulation_time"]),
            "action_type": r["action_type"], "actor_id": r["actor_id"],
            "entity_id": r["entity_id"], "payload": json.loads(r["payload"]),
            "previous_hash": r["previous_hash"], "event_hash": r["event_hash"],
        } for r in rows]

    def verify_event_chain(self) -> bool:
        previous = "GENESIS"
        rows = self._db.execute(
            "SELECT * FROM world_events ORDER BY sequence"
        ).fetchall()
        for row in rows:
            body = {
                "action_id": row["action_id"], "revision": int(row["revision"]),
                "simulation_time": float(row["simulation_time"]),
                "action_type": row["action_type"], "actor_id": row["actor_id"],
                "entity_id": row["entity_id"], "payload": json.loads(row["payload"]),
            }
            expected = self._event_hash(previous, body)
            if row["previous_hash"] != previous or row["event_hash"] != expected:
                return False
            previous = expected
        return True

    def export_snapshot(self) -> dict[str, Any]:
        with self._lock:
            fields = [dict(row) for row in self._db.execute(
                "SELECT * FROM field_cells ORDER BY ix,iy,iz").fetchall()]
            return {
                "format": "chimera-world-snapshot",
                "version": 1,
                "engine_version": ENGINE_VERSION,
                "revision": self.revision(),
                "simulation_time": self.simulation_time(),
                "entities": [e.to_dict() for e in self._load_entities()],
                "fields": fields,
            }

    def import_snapshot(self, snapshot: dict[str, Any], *,
                        actor_id: str = "snapshot-import") -> WorldResult:
        if snapshot.get("format") != "chimera-world-snapshot" or snapshot.get("version") != 1:
            raise InvalidWorldAction("Unsupported world snapshot format")
        entities = [Entity.from_dict(item) for item in snapshot.get("entities", [])]
        if len(entities) > self.config.max_entities:
            raise InvalidWorldAction("Snapshot exceeds entity capacity")
        for i, entity in enumerate(entities):
            self._validate_geometry(entity)
            for other in entities[:i]:
                if self._overlaps(entity, other, self.config.contact_tolerance*0.1):
                    raise InvalidWorldAction("Snapshot contains intersecting entities")
        action_id = str(uuid.uuid4())
        with self._lock:
            self._begin()
            try:
                self._db.execute("DELETE FROM entities")
                self._db.execute("DELETE FROM field_cells")
                for entity in entities:
                    self._store_entity(entity)
                for f in snapshot.get("fields", []):
                    self._db.execute("""
                        INSERT INTO field_cells(ix,iy,iz,energy,stress,memory,cohesion)
                        VALUES(?,?,?,?,?,?,?)
                    """, (int(f["ix"]),int(f["iy"]),int(f["iz"]),
                          float(f["energy"]),float(f["stress"]),
                          float(f["memory"]),float(f["cohesion"])))
                self._db.execute(
                    "UPDATE world_meta SET simulation_time=? WHERE singleton=1",
                    (float(snapshot.get("simulation_time", 0.0)),))
                revision = self._advance_revision()
                self._append_event(action_id, revision, ActionType.CREATE, actor_id,
                                   None, {"snapshot_import": True,
                                          "source_revision": snapshot.get("revision"),
                                          "entity_count": len(entities)})
                self._commit()
                return WorldResult(action_id, revision, "snapshot_import", None,
                                   True, {"entity_count": len(entities)})
            except Exception:
                self._rollback()
                raise


def create_demo_world(database: str = ":memory:") -> RealityEngine:
    """Create a small stable world that exercises actual construction and physics."""
    engine = RealityEngine(WorldConfig(database=database))
    rev = engine.revision()
    base = engine.create_primitive(
        "foundation", (0, 0.5, 0), (4, 1, 4), actor_id="demo-organism",
        material="stone", mass=80, dynamic=False, expected_revision=rev,
    )
    engine.create_primitive(
        "wall_block", (0, 1.5, 0), (2, 1, 2), actor_id="demo-organism",
        material="stone", mass=30, dynamic=False, expected_revision=base.revision,
    )
    engine.inject_field("memory", (0, 1, 0), 0.7, actor_id="demo-organism",
                        radius=2, expected_revision=engine.revision())
    return engine


if __name__ == "__main__":
    world = create_demo_world()
    print(json.dumps(world.observe(center=(0, 1, 0), radius=10), indent=2))
    print("Event chain valid:", world.verify_event_chain())
    world.close()
