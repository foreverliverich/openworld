"""Chimera creation toolbox: functional tools over one authoritative RealityEngine.

The toolbox is an application/service layer, not another world simulation. Every
world mutation delegates to RealityEngine so validation, revisions, persistence
and the event journal remain authoritative.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

from .reality_engine import InvalidWorldAction, RealityEngine


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    purpose: str
    actions: tuple[str, ...]
    state_owner: str = "RealityEngine"


class ToolboxError(ValueError):
    pass


class ChimeraToolbox:
    """Six connected tool domains exposed through one validated dispatch surface."""

    def __init__(self, world: RealityEngine, *, actor_id: str = "chimera"):
        self.world = world
        self.actor_id = actor_id
        self._definitions = {
            "body_forge": ToolDefinition(
                "body_forge", "Create a persistent body/anatomy prototype.",
                ("create_body", "inspect_body"),
            ),
            "world_builder": ToolDefinition(
                "world_builder", "Construct and inspect persistent world structures.",
                ("create_object", "create_structure", "harvest_energy", "inspect"),
            ),
            "tool_fabricator": ToolDefinition(
                "tool_fabricator", "Fabricate a persistent tool entity from a declared specification.",
                ("fabricate", "inspect_tool"),
            ),
            "life_generator": ToolDefinition(
                "life_generator", "Instantiate a persistent organism prototype in the world.",
                ("spawn", "inspect_lifeform"),
            ),
            "movement_lab": ToolDefinition(
                "movement_lab", "Move an entity through validated world actions and advance physics.",
                ("move", "advance_physics"),
            ),
            "research_lab": ToolDefinition(
                "research_lab", "Observe world state, fields, event history and snapshots.",
                ("observe", "field_read", "events", "snapshot"),
            ),
        }

    def manifest(self) -> list[dict[str, Any]]:
        return [
            {"name": d.name, "purpose": d.purpose,
             "actions": list(d.actions), "state_owner": d.state_owner}
            for d in self._definitions.values()
        ]

    def execute(
        self,
        tool: str,
        action: str,
        arguments: dict[str, Any],
        *,
        actor_id: str | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        """Execute a named tool action and return a JSON-safe result."""
        if tool not in self._definitions:
            raise ToolboxError(f"Unknown tool '{tool}'")
        if action not in self._definitions[tool].actions:
            raise ToolboxError(f"Unsupported action '{action}' for tool '{tool}'")
        if not isinstance(arguments, dict):
            raise ToolboxError("Tool arguments must be an object")

        actor = actor_id or self.actor_id
        rev = self.world.revision() if expected_revision is None else expected_revision
        handlers: dict[tuple[str, str], Callable[[], dict[str, Any]]] = {
            ("body_forge", "create_body"): lambda: self._create_body(arguments, actor, rev),
            ("body_forge", "inspect_body"): lambda: self._inspect_kind("body", arguments),
            ("world_builder", "create_object"): lambda: self._create_object(arguments, actor, rev),
            ("world_builder", "create_structure"): lambda: self._create_structure(arguments, actor, rev),
            ("world_builder", "harvest_energy"): lambda: self._harvest_energy(arguments, actor, rev),
            ("world_builder", "inspect"): lambda: self._observe(arguments),
            ("tool_fabricator", "fabricate"): lambda: self._fabricate(arguments, actor, rev),
            ("tool_fabricator", "inspect_tool"): lambda: self._inspect_kind("tool", arguments),
            ("life_generator", "spawn"): lambda: self._spawn_lifeform(arguments, actor, rev),
            ("life_generator", "inspect_lifeform"): lambda: self._inspect_kind("organism", arguments),
            ("movement_lab", "move"): lambda: self._move(arguments, actor, rev),
            ("movement_lab", "advance_physics"): lambda: self._advance_physics(arguments, actor, rev),
            ("research_lab", "observe"): lambda: self._observe(arguments),
            ("research_lab", "field_read"): lambda: self._field_read(arguments),
            ("research_lab", "events"): lambda: self._events(arguments),
            ("research_lab", "snapshot"): lambda: self.world.export_snapshot(),
        }
        return handlers[(tool, action)]()

    def _create_object(self, a: dict[str, Any], actor: str, rev: int) -> dict[str, Any]:
        result = self.world.create_primitive(
            kind=self._required_text(a, "kind"),
            position=self._vec(a, "position"),
            size=self._vec(a, "size"),
            actor_id=actor,
            material=str(a.get("material", "default")),
            mass=float(a.get("mass", 1.0)),
            dynamic=bool(a.get("dynamic", True)),
            metadata={"tool_domain": "world_builder", **dict(a.get("metadata", {}))},
            expected_revision=rev,
        )
        return self._result(result)

    def _create_structure(self, a: dict[str, Any], actor: str, rev: int) -> dict[str, Any]:
        blueprint = a.get("blueprint")
        if not isinstance(blueprint, dict):
            raise ToolboxError("create_structure requires a blueprint object")
        blueprint = dict(blueprint)
        blueprint["name"] = str(blueprint.get("name", "player_structure"))
        result = self.world.create_structure(
            blueprint, actor_id=actor, expected_revision=rev
        )
        return self._result(result)

    def _harvest_energy(self, a: dict[str, Any], actor: str, rev: int) -> dict[str, Any]:
        """Consume a bounded amount of local environmental energy into the organism."""
        position = self._vec(a, "position")
        amount = float(a.get("amount", 0.0))
        if not math.isfinite(amount) or not 0.0 < amount <= 0.25:
            raise ToolboxError("harvest amount must be finite and in (0, 0.25]")
        available = self.world.field_at(position)["energy"]
        if available < amount:
            raise ToolboxError("Insufficient environmental energy at harvest position")
        result = self.world.inject_field(
            "energy", position, -amount, actor_id=actor, radius=0,
            expected_revision=rev,
        )
        return {
            "accepted": result.accepted,
            "action": result.action,
            "action_id": result.action_id,
            "entity_id": result.entity_id,
            "revision": result.revision,
            "details": {**result.details, "harvested": amount,
                        "remaining_energy": self.world.field_at(position)["energy"]},
        }

    def _create_body(self, a: dict[str, Any], actor: str, rev: int) -> dict[str, Any]:
        """Create a grounded body prototype; articulated joints are a later body solver."""
        form = self._required_text(a, "form")
        anatomy = a.get("anatomy", {})
        if not isinstance(anatomy, dict):
            raise ToolboxError("anatomy must be an object")
        result = self.world.create_primitive(
            kind="body_prototype",
            position=self._vec(a, "position"),
            size=self._vec(a, "size"),
            actor_id=actor,
            material=str(a.get("material", "organic_composite")),
            mass=float(a.get("mass", 1.0)),
            dynamic=bool(a.get("dynamic", True)),
            metadata={
                "tool_domain": "body_forge",
                "form": form,
                "anatomy": anatomy,
                "articulation_status": "prototype_rigid_body",
            },
            expected_revision=rev,
        )
        return self._result(result)

    def _fabricate(self, a: dict[str, Any], actor: str, rev: int) -> dict[str, Any]:
        name = self._required_text(a, "name")
        capabilities = a.get("capabilities", [])
        if not isinstance(capabilities, list) or not all(isinstance(x, str) for x in capabilities):
            raise ToolboxError("capabilities must be a list of strings")
        result = self.world.create_primitive(
            kind="fabricated_tool",
            position=self._vec(a, "position"),
            size=self._vec(a, "size"),
            actor_id=actor,
            material=str(a.get("material", "default")),
            mass=float(a.get("mass", 1.0)),
            dynamic=bool(a.get("dynamic", True)),
            metadata={
                "tool_domain": "tool_fabricator",
                "tool_name": name,
                "capabilities": capabilities,
                "specification": dict(a.get("specification", {})),
                "execution_status": "world_item_only",
            },
            expected_revision=rev,
        )
        return self._result(result)

    def _spawn_lifeform(self, a: dict[str, Any], actor: str, rev: int) -> dict[str, Any]:
        species = self._required_text(a, "species")
        identity = str(a.get("identity", species))
        genome_ref = a.get("genome_ref")
        result = self.world.create_primitive(
            kind="organism_prototype",
            position=self._vec(a, "position"),
            size=self._vec(a, "size"),
            actor_id=actor,
            material=str(a.get("material", "biomorphic")),
            mass=float(a.get("mass", 1.0)),
            dynamic=bool(a.get("dynamic", True)),
            metadata={
                "tool_domain": "life_generator",
                "species": species,
                "identity": identity,
                "genome_ref": genome_ref,
                "life_status": "embodied_entity_prototype",
                "active_agent_runtime": False,
            },
            expected_revision=rev,
        )
        return self._result(result)

    def _move(self, a: dict[str, Any], actor: str, rev: int) -> dict[str, Any]:
        result = self.world.move_entity(
            self._required_text(a, "entity_id"),
            self._vec(a, "position"),
            actor_id=actor,
            expected_revision=rev,
        )
        return self._result(result)

    def _advance_physics(self, a: dict[str, Any], actor: str, rev: int) -> dict[str, Any]:
        steps = int(a.get("steps", 1))
        if steps < 1 or steps > 1000:
            raise ToolboxError("steps must be between 1 and 1000")
        results = []
        current = rev
        for _ in range(steps):
            result = self.world.step(actor_id=actor, expected_revision=current)
            current = result.revision
            results.append(self._result(result))
        return {"steps": steps, "revision": current, "results": results}

    def _observe(self, a: dict[str, Any]) -> dict[str, Any]:
        center = a.get("center", (0.0, 0.0, 0.0))
        radius = float(a.get("radius", 20.0))
        return self.world.observe(center=center, radius=radius)

    def _field_read(self, a: dict[str, Any]) -> dict[str, Any]:
        position = self._vec(a, "position")
        return {
            "position": position,
            "fields": self.world.field_at(position),
            "revision": self.world.revision(),
        }

    def _events(self, a: dict[str, Any]) -> dict[str, Any]:
        after = int(a.get("after_revision", 0))
        limit = int(a.get("limit", 100))
        return {
            "events": self.world.event_history(after_revision=after, limit=limit),
            "chain_valid": self.world.verify_event_chain(),
            "revision": self.world.revision(),
        }

    def _inspect_kind(self, kind: str, a: dict[str, Any]) -> dict[str, Any]:
        entity_id = a.get("entity_id")
        if entity_id:
            entity = self.world.get_entity(str(entity_id))
            if entity.kind != ("body_prototype" if kind == "body" else
                               "fabricated_tool" if kind == "tool" else "organism_prototype"):
                raise ToolboxError(f"Entity {entity_id} is not a {kind} prototype")
            return {"entity": entity.to_dict(), "revision": self.world.revision()}
        matches = [
            e.to_dict() for e in self.world.entities()
            if e.kind == ("body_prototype" if kind == "body" else
                          "fabricated_tool" if kind == "tool" else "organism_prototype")
        ]
        return {"entities": matches, "count": len(matches), "revision": self.world.revision()}

    @staticmethod
    def _required_text(a: dict[str, Any], key: str) -> str:
        value = a.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ToolboxError(f"'{key}' must be a non-empty string")
        return value.strip()

    @staticmethod
    def _vec(a: dict[str, Any], key: str) -> tuple[float, float, float]:
        value = a.get(key)
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise ToolboxError(f"'{key}' must be a three-component vector")
        result = tuple(float(v) for v in value)
        if not all(math.isfinite(v) for v in result):
            raise ToolboxError(f"'{key}' must contain finite numbers")
        return result

    @staticmethod
    def _result(result: Any) -> dict[str, Any]:
        return {
            "accepted": result.accepted,
            "action": result.action,
            "action_id": result.action_id,
            "entity_id": result.entity_id,
            "revision": result.revision,
            "details": result.details,
        }
