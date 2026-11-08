"""Executable Latent Language 3.0 cognition pipeline.

This module implements versioned multimodal state contracts, confidence-aware
fusion, specialist proposals, global-workspace competition, spatial composition,
and a single revision-checked gateway into RealityEngine via ChimeraToolbox.

It intentionally does not pretend that a lexical baseline is a pretrained model,
that a proposal is an action, or that a latent vector is consciousness.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

SUBSPACE_DIMS: dict[str, int] = {
    "language": 768,
    "emotion": 128,
    "cognition": 256,
    "memory": 512,
    "social": 64,
    "temporal": 32,
    "visual": 512,
    "audio": 128,
    "sensor": 64,
}
LATENT_DIMENSIONS = sum(SUBSPACE_DIMS.values())
MODALITY_TO_SUBSPACE = {
    "text": "language", "image": "visual", "audio": "audio", "sensor": "sensor"
}
SCHEMA_VERSION = 1


class LatentLanguageError(ValueError):
    """Invalid latent state, observation, proposal or scene graph."""


def _finite(value: Any, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise LatentLanguageError(f"{name} must be finite")
    return result


def _vector(values: Sequence[float], size: int, name: str) -> tuple[float, ...]:
    if len(values) != size:
        raise LatentLanguageError(f"{name} requires {size} values, received {len(values)}")
    result = tuple(_finite(v, name) for v in values)
    return result


def _unit(value: Any, name: str) -> float:
    result = _finite(value, name)
    if not 0.0 <= result <= 1.0:
        raise LatentLanguageError(f"{name} must be in [0, 1]")
    return result


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        raise LatentLanguageError("Cosine similarity requires equal non-empty vectors")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0.0 or nb == 0.0 else dot / (na * nb)


@dataclass(frozen=True)
class EncodedObservation:
    """An encoder result with time, confidence and provenance attached."""

    modality: str
    embedding: tuple[float, ...]
    timestamp: float
    confidence: float
    source_id: str
    encoder_id: str
    shared_space: str | None = None

    def __post_init__(self) -> None:
        if self.modality not in MODALITY_TO_SUBSPACE:
            raise LatentLanguageError(f"Unsupported modality: {self.modality}")
        subspace = MODALITY_TO_SUBSPACE[self.modality]
        object.__setattr__(self, "embedding", _vector(
            self.embedding, SUBSPACE_DIMS[subspace], f"{self.modality} embedding"
        ))
        object.__setattr__(self, "timestamp", _finite(self.timestamp, "timestamp"))
        object.__setattr__(self, "confidence", _unit(self.confidence, "confidence"))
        if not self.source_id or not self.encoder_id:
            raise LatentLanguageError("Observation source_id and encoder_id are required")


@dataclass(frozen=True)
class LatentState:
    """Ephemeral working representation projected from ISCE; never persisted as organism state."""

    subspaces: Mapping[str, tuple[float, ...]]
    updated_at: Mapping[str, float]
    revision: int = 0
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION or self.revision < 0:
            raise LatentLanguageError("Unsupported latent schema or negative revision")
        if set(self.subspaces) != set(SUBSPACE_DIMS):
            raise LatentLanguageError("Latent state must contain every canonical subspace")
        normalized: dict[str, tuple[float, ...]] = {}
        for name, size in SUBSPACE_DIMS.items():
            normalized[name] = _vector(self.subspaces[name], size, name)
        for name, timestamp in self.updated_at.items():
            if name not in SUBSPACE_DIMS:
                raise LatentLanguageError(f"Unknown timestamp subspace: {name}")
            _finite(timestamp, f"{name}.updated_at")
        object.__setattr__(self, "subspaces", MappingProxyType(normalized))
        object.__setattr__(self, "updated_at", MappingProxyType(dict(self.updated_at)))

    @classmethod
    def empty(cls) -> "LatentState":
        return cls(
            subspaces={name: (0.0,) * size for name, size in SUBSPACE_DIMS.items()},
            updated_at={},
        )

    @property
    def vector(self) -> tuple[float, ...]:
        return tuple(v for name in SUBSPACE_DIMS for v in self.subspaces[name])

    @property
    def digest(self) -> str:
        payload = {
            "schema": self.schema_version, "revision": self.revision,
            "subspaces": {k: list(v) for k, v in self.subspaces.items()},
            "updated_at": dict(self.updated_at),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def write_subspace(
        self, name: str, values: Sequence[float], *, timestamp: float
    ) -> "LatentState":
        if name not in SUBSPACE_DIMS:
            raise LatentLanguageError(f"Unknown subspace: {name}")
        timestamp = _finite(timestamp, "timestamp")
        previous = self.updated_at.get(name)
        if previous is not None and timestamp < previous:
            raise LatentLanguageError(f"Stale update for {name}: {timestamp} < {previous}")
        spaces = dict(self.subspaces)
        spaces[name] = _vector(values, SUBSPACE_DIMS[name], name)
        times = dict(self.updated_at)
        times[name] = timestamp
        return LatentState(spaces, times, self.revision + 1)


class Encoder(Protocol):
    encoder_id: str

    def encode(self, payload: Any) -> Sequence[float]: ...


class EncoderRegistry:
    """Explicit modality-to-encoder registry; there is no random fallback encoder."""

    def __init__(self) -> None:
        self._encoders: dict[str, Encoder] = {}

    def register(self, modality: str, encoder: Encoder) -> None:
        if modality not in MODALITY_TO_SUBSPACE:
            raise LatentLanguageError(f"Unsupported modality: {modality}")
        if not getattr(encoder, "encoder_id", None):
            raise LatentLanguageError("Encoder must expose a stable encoder_id")
        self._encoders[modality] = encoder

    def encode(
        self, modality: str, payload: Any, *, timestamp: float,
        confidence: float, source_id: str,
    ) -> EncodedObservation:
        if modality not in self._encoders:
            raise LatentLanguageError(f"No real encoder registered for modality '{modality}'")
        encoder = self._encoders[modality]
        subspace = MODALITY_TO_SUBSPACE[modality]
        values = encoder.encode(payload)
        return EncodedObservation(
            modality, tuple(values), timestamp, confidence, source_id,
            encoder.encoder_id, getattr(encoder, "shared_space", None),
        )


class MultimodalFusion:
    """Confidence-aware, timestamped concatenative fusion.

    Modalities occupy distinct source-defined subspaces. Cross-modal similarity
    is only computed when both encoders explicitly declare the same aligned space.
    """

    def __init__(self, *, retention_seconds: float = 30.0):
        if retention_seconds <= 0:
            raise LatentLanguageError("retention_seconds must be positive")
        self.retention_seconds = float(retention_seconds)

    def update(self, state: LatentState, observation: EncodedObservation) -> LatentState:
        subspace = MODALITY_TO_SUBSPACE[observation.modality]
        previous_time = state.updated_at.get(subspace)
        if previous_time is not None and observation.timestamp < previous_time:
            raise LatentLanguageError(f"Out-of-order {observation.modality} observation")
        old = state.subspaces[subspace]
        elapsed = self.retention_seconds if previous_time is None else max(
            0.0, observation.timestamp - previous_time
        )
        decay = math.exp(-elapsed / self.retention_seconds)
        alpha = observation.confidence
        # Confidence controls the new evidence; elapsed time controls persistence.
        blended = tuple(
            (alpha * new) + ((1.0 - alpha) * decay * prior)
            for prior, new in zip(old, observation.embedding)
        )
        return state.write_subspace(subspace, blended, timestamp=observation.timestamp)

    @staticmethod
    def aligned_similarity(a: Any, b: Any) -> float:
        if not getattr(a, "shared_space", None) or a.shared_space != getattr(b, "shared_space", None):
            raise LatentLanguageError(
                "Cross-modal comparison requires an explicitly shared encoder space"
            )
        return _cosine(a.embedding, b.embedding)


@dataclass(frozen=True)
class SceneObject:
    object_id: str
    kind: str
    position: tuple[float, float, float]
    size: tuple[float, float, float]
    material: str = "default"
    mass: float = 1.0
    dynamic: bool = True

    def __post_init__(self) -> None:
        if not self.object_id or not self.kind:
            raise LatentLanguageError("Scene objects require object_id and kind")
        object.__setattr__(self, "position", _vector(self.position, 3, "position"))
        object.__setattr__(self, "size", _vector(self.size, 3, "size"))
        if any(v <= 0 for v in self.size) or not math.isfinite(self.mass) or self.mass <= 0:
            raise LatentLanguageError("Scene object dimensions and mass must be finite and positive")


@dataclass(frozen=True)
class SpatialRelation:
    relation: str
    subject: str
    object: str
    gap: float = 0.05

    def __post_init__(self) -> None:
        if self.relation not in {"on_top", "next_to", "inside"}:
            raise LatentLanguageError(f"Unsupported spatial relation: {self.relation}")
        if self.subject == self.object:
            raise LatentLanguageError("A spatial relation cannot target itself")
        if self.gap < 0 or not math.isfinite(self.gap):
            raise LatentLanguageError("Spatial relation gap must be finite and non-negative")


@dataclass(frozen=True)
class SceneGraph:
    scene_id: str
    objects: tuple[SceneObject, ...]
    relations: tuple[SpatialRelation, ...] = ()

    def __post_init__(self) -> None:
        if not self.scene_id or not self.objects:
            raise LatentLanguageError("SceneGraph requires an id and at least one object")
        ids = [item.object_id for item in self.objects]
        if len(ids) != len(set(ids)):
            raise LatentLanguageError("Scene object ids must be unique")
        known = set(ids)
        for relation in self.relations:
            if relation.subject not in known or relation.object not in known:
                raise LatentLanguageError("Spatial relation references an unknown object")

    def to_blueprint(self) -> dict[str, Any]:
        """Compile spatial relations to a RealityEngine structure blueprint."""
        objects = {item.object_id: item for item in self.objects}
        resolved = {key: list(value.position) for key, value in objects.items()}
        # Relations are applied in declared order. Conflicting repeated placements
        # are rejected rather than silently resolved by order-dependent mutation.
        assigned: set[str] = set()
        parent_of: dict[str, str] = {}
        for rel in self.relations:
            parent_of[rel.subject] = rel.object
        for start in parent_of:
            visited: set[str] = set()
            node = start
            while node in parent_of:
                if node in visited:
                    raise LatentLanguageError("Spatial relation graph contains a placement cycle")
                visited.add(node)
                node = parent_of[node]
        for rel in self.relations:
            child, parent = objects[rel.subject], objects[rel.object]
            if rel.subject in assigned:
                raise LatentLanguageError(
                    f"Object {rel.subject} has multiple placement constraints"
                )
            cp, pp = resolved[child.object_id], resolved[parent.object_id]
            if rel.relation == "on_top":
                cp[1] = pp[1] + parent.size[1] / 2 + child.size[1] / 2 + rel.gap
            elif rel.relation == "next_to":
                cp[0] = pp[0] + parent.size[0] / 2 + child.size[0] / 2 + rel.gap
            else:
                if any(child.size[i] + 2.0 * rel.gap > parent.size[i] for i in range(3)):
                    raise LatentLanguageError("Contained object plus clearance exceeds container dimensions")
                raise LatentLanguageError(
                    "RealityEngine's primitive collision model cannot commit nested containment; "
                    "retain this relation in the creative artifact or use a compound-mesh backend"
                )
            assigned.add(rel.subject)
        supported_by_relation = {
            rel.subject for rel in self.relations
            if rel.relation == "on_top" and not objects[rel.object].dynamic
        }
        for item in self.objects:
            if not item.dynamic:
                bottom = resolved[item.object_id][1] - item.size[1] / 2.0
                on_ground = abs(bottom) <= 1e-6
                supported = item.object_id in supported_by_relation
                if not on_ground and not supported:
                    raise LatentLanguageError(
                        f"Static object {item.object_id} must rest on ground or a declared support"
                    )
        for index, left in enumerate(self.objects):
            for right in self.objects[index + 1:]:
                overlap = all(
                    abs(resolved[left.object_id][axis] - resolved[right.object_id][axis])
                    < (left.size[axis] + right.size[axis]) / 2.0 - 1e-6
                    for axis in range(3)
                )
                if overlap:
                    raise LatentLanguageError(
                        f"Scene objects {left.object_id} and {right.object_id} overlap"
                    )
        parts = []
        for item in self.objects:
            parts.append({
                "kind": item.kind, "position": resolved[item.object_id],
                "size": list(item.size), "material": item.material,
                "mass": item.mass, "dynamic": item.dynamic,
                "metadata": {"scene_id": self.scene_id, "object_id": item.object_id},
            })
        return {"name": self.scene_id, "parts": parts}


@dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    text: str
    timestamp: float
    embedding: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.record_id or not self.text:
            raise LatentLanguageError("Memory record requires id and text")
        object.__setattr__(self, "embedding", _vector(
            self.embedding, SUBSPACE_DIMS["language"], "memory embedding"
        ))


@dataclass(frozen=True)
class SpecialistContext:
    timestamp: float
    world_revision: int
    text: str = ""
    scene_graph: SceneGraph | None = None
    memory_records: tuple[MemoryRecord, ...] = ()
    speaker_id: str | None = None
    participant_count: int = 1
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _finite(self.timestamp, "context timestamp")
        if self.world_revision < 0 or self.participant_count < 1:
            raise LatentLanguageError("Invalid specialist context revision/participant count")


@dataclass(frozen=True)
class SpecialistProposal:
    proposal_id: str
    specialist: str
    kind: str
    payload: Mapping[str, Any]
    confidence: float
    salience: float
    urgency: float
    novelty: float
    estimated_cost: float
    world_revision: int
    evidence_refs: tuple[str, ...]
    conflict_key: str | None = None

    def __post_init__(self) -> None:
        if not all((self.proposal_id, self.specialist, self.kind)):
            raise LatentLanguageError("Proposal identity fields are required")
        for name in ("confidence", "salience", "urgency", "novelty"):
            _unit(getattr(self, name), name)
        _unit(self.estimated_cost, "estimated_cost")

        if self.world_revision < 0:
            raise LatentLanguageError("world_revision cannot be negative")


class Specialist(Protocol):
    name: str

    def propose(
        self, state: LatentState, context: SpecialistContext
    ) -> Sequence[SpecialistProposal]: ...


def _stable_id(prefix: str, material: str) -> str:
    return prefix + "-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _proposal_fingerprint(proposal: SpecialistProposal) -> str:
    payload = {
        "id": proposal.proposal_id, "specialist": proposal.specialist,
        "kind": proposal.kind, "payload": proposal.payload,
        "confidence": proposal.confidence, "salience": proposal.salience,
        "urgency": proposal.urgency, "novelty": proposal.novelty,
        "estimated_cost": proposal.estimated_cost,
        "world_revision": proposal.world_revision,
        "evidence_refs": proposal.evidence_refs,
        "conflict_key": proposal.conflict_key,
    }
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=list)
    except (TypeError, ValueError) as exc:
        raise LatentLanguageError("Proposal payload must be JSON-serializable") from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _expand_features(features: Sequence[float], size: int) -> tuple[float, ...]:
    """Deterministic Fourier feature lift; used for symbolic subspaces, not embeddings."""
    output: list[float] = []
    for index in range(size):
        source = features[index % len(features)] if features else 0.0
        output.append(math.tanh(source * (1.0 + (index // max(1, len(features))) * 0.05)))
    return tuple(output)


class EmotionSpecialist:
    """Transparent lexical affect baseline; replaceable by a trained classifier."""

    name = "emotion"

    POSITIVE = {"happy", "love", "great", "excited", "good", "hopeful", "safe"}
    NEGATIVE = {"sad", "angry", "fear", "afraid", "bad", "hurt", "worried"}
    URGENT = {"urgent", "emergency", "danger", "help", "now", "pain"}

    def propose(self, state: LatentState, context: SpecialistContext) -> Sequence[SpecialistProposal]:
        tokens = re.findall(r"[a-z']+", context.text.lower())
        if not tokens:
            return ()
        positive = sum(token in self.POSITIVE for token in tokens)
        negative = sum(token in self.NEGATIVE for token in tokens)
        urgent = sum(token in self.URGENT for token in tokens)
        scale = max(1, len(tokens))
        features = (positive / scale, negative / scale, urgent / scale,
                    (positive - negative) / scale, min(1.0, len(tokens) / 40))
        vector = _expand_features(features, SUBSPACE_DIMS["emotion"])
        confidence = min(0.8, 0.35 + (positive + negative + urgent) / scale)
        proposal = SpecialistProposal(
            _stable_id(self.name, context.text + str(context.timestamp)),
            self.name, "subspace_update",
            {"subspace": "emotion", "vector": vector, "timestamp": context.timestamp,
             "classifier": "lexical-baseline-v1"},
            confidence, 0.35 + min(0.4, (positive + negative) / scale),
            min(1.0, urgent / max(1, scale)), 0.1, 0.0,
            context.world_revision, context.source_refs,
        )
        return (proposal,)


class CognitiveSpecialist:
    """Intent proposal baseline grounded in explicit user verbs, not an LLM claim."""

    name = "cognitive"
    INTENTS = {
        "create": ("create", "make", "build", "construct", "generate"),
        "inspect": ("inspect", "analyze", "look", "observe", "examine"),
        "move": ("move", "walk", "go", "travel", "navigate"),
        "explain": ("explain", "describe", "why", "how", "compare"),
    }

    def propose(self, state: LatentState, context: SpecialistContext) -> Sequence[SpecialistProposal]:
        text = context.text.strip().lower()
        if not text:
            return ()
        tokens = set(re.findall(r"[a-z']+", text))
        matches = [(intent, sum(word in tokens for word in verbs))
                   for intent, verbs in self.INTENTS.items()]
        intent, count = max(matches, key=lambda item: (item[1], item[0]))
        if count == 0:
            return ()
        confidence = min(0.75, 0.4 + 0.12 * count)
        vector = _expand_features(
            [float(count), float(len(tokens)), float(len(text)), float(list(self.INTENTS).index(intent))],
            SUBSPACE_DIMS["cognition"],
        )
        return (SpecialistProposal(
            _stable_id(self.name, text), self.name, "intent",
            {"intent": intent, "vector": vector, "text": context.text},
            confidence, 0.55, 0.2, 0.15, 0.0,
            context.world_revision, context.source_refs,
        ),)


class MemorySpecialist:
    """Read-only retrieval over caller-supplied, ISCE/RealityEngine-backed records."""

    name = "memory"

    def propose(self, state: LatentState, context: SpecialistContext) -> Sequence[SpecialistProposal]:
        if not context.memory_records:
            return ()
        query = state.subspaces["language"]
        ranked = sorted(
            ((_cosine(query, record.embedding), record) for record in context.memory_records),
            key=lambda item: (-item[0], item[1].timestamp, item[1].record_id),
        )
        selected = [(score, record) for score, record in ranked[:5] if score > 0.0]
        if not selected:
            return ()
        weighted = [0.0] * SUBSPACE_DIMS["memory"]
        total = sum(score for score, _ in selected)
        for score, record in selected:
            for i in range(len(weighted)):
                weighted[i] += (score / total) * record.embedding[i]
        return (SpecialistProposal(
            _stable_id(self.name, "|".join(r.record_id for _, r in selected)),
            self.name, "memory_retrieval",
            {"subspace": "memory", "vector": tuple(weighted),
             "records": [{"id": r.record_id, "score": score, "text": r.text}
                         for score, r in selected]},
            min(0.95, max(score for score, _ in selected)), 0.45, 0.1, 0.25,
            0.01, context.world_revision,
            tuple(r.record_id for _, r in selected),
            conflict_key="memory:working-set",
        ),)


class SocialSpecialist:
    """Tracks explicit interaction structure without inferring sensitive traits."""

    name = "social"

    def propose(self, state: LatentState, context: SpecialistContext) -> Sequence[SpecialistProposal]:
        features = (
            min(1.0, context.participant_count / 8),
            1.0 if context.speaker_id else 0.0,
            1.0 if context.participant_count > 1 else 0.0,
        )
        vector = _expand_features(features, SUBSPACE_DIMS["social"])
        return (SpecialistProposal(
            _stable_id(self.name, f"{context.speaker_id}:{context.participant_count}"),
            self.name, "subspace_update",
            {"subspace": "social", "vector": vector, "timestamp": context.timestamp},
            0.65, 0.2, 0.05, 0.05, 0.0, context.world_revision, context.source_refs,
        ),)


class TemporalSpecialist:
    name = "temporal"

    def propose(self, state: LatentState, context: SpecialistContext) -> Sequence[SpecialistProposal]:
        values = []
        for i in range(SUBSPACE_DIMS["temporal"] // 2):
            frequency = 2.0 ** i
            phase = context.timestamp / frequency
            values.extend((math.sin(phase), math.cos(phase)))
        return (SpecialistProposal(
            _stable_id(self.name, str(context.timestamp)), self.name, "subspace_update",
            {"subspace": "temporal", "vector": tuple(values), "timestamp": context.timestamp},
            0.9, 0.3, 0.05, 0.0, 0.0, context.world_revision, context.source_refs,
        ),)


class SpatialSpecialist:
    name = "spatial"

    def propose(self, state: LatentState, context: SpecialistContext) -> Sequence[SpecialistProposal]:
        graph = context.scene_graph
        if graph is None:
            return ()
        try:
            blueprint = graph.to_blueprint()
        except LatentLanguageError as exc:
            return (SpecialistProposal(
                _stable_id(self.name + "-constraint", graph.scene_id + str(exc)),
                self.name, "spatial_constraint_error",
                {"scene_id": graph.scene_id, "reason": str(exc)},
                0.95, 0.55, 0.1, 0.2, 0.0, context.world_revision,
                context.source_refs + (f"scene:{graph.scene_id}",),
                conflict_key=f"scene:{graph.scene_id}",
            ),)
        return (SpecialistProposal(
            _stable_id(self.name, graph.scene_id), self.name, "world_action",
            {"tool": "world_builder", "action": "create_structure",
             "arguments": {"blueprint": blueprint}},
            0.85, 0.8, 0.25, 0.6, 0.2, context.world_revision,
            context.source_refs + (f"scene:{graph.scene_id}",),
            conflict_key=f"scene:{graph.scene_id}",
        ),)


class CreativeSpecialist:
    """Produces grounded text/scene/behavior artifacts; no hidden image model is implied."""

    name = "creative"

    def propose(self, state: LatentState, context: SpecialistContext) -> Sequence[SpecialistProposal]:
        if not context.text.strip() and context.scene_graph is None:
            return ()
        graph = context.scene_graph
        artifact = {
            "kind": "scene" if graph else "concept",
            "prompt": context.text,
            "scene_id": graph.scene_id if graph else None,
            "objects": [
                {"id": obj.object_id, "kind": obj.kind, "position": list(obj.position),
                 "size": list(obj.size), "material": obj.material}
                for obj in graph.objects
            ] if graph else [],
            "relations": [
                {"relation": rel.relation, "subject": rel.subject, "object": rel.object}
                for rel in graph.relations
            ] if graph else [],
            "generator": "structured-creative-composer-v1",
        }
        return (SpecialistProposal(
            _stable_id(self.name, json.dumps(artifact, sort_keys=True)),
            self.name, "creative_artifact", artifact,
            0.7, 0.65, 0.05, 0.55, 0.05, context.world_revision,
            context.source_refs + (("user_prompt",) if context.text else ()),
        ),)


@dataclass(frozen=True)
class WorkspaceBroadcast:
    tick: int
    state_digest: str
    selected: tuple[SpecialistProposal, ...]
    rejected: tuple[SpecialistProposal, ...]
    scores: Mapping[str, float]
    proposal_fingerprints: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "scores", MappingProxyType(dict(self.scores)))
        object.__setattr__(
            self, "proposal_fingerprints",
            MappingProxyType(dict(self.proposal_fingerprints)),
        )


class GlobalWorkspace:
    """Deterministic limited-capacity winner-take-most proposal competition."""

    def __init__(
        self, *, capacity: int = 3, max_per_specialist: int = 1,
        min_score: float = 0.15,
    ):
        if capacity < 1 or max_per_specialist < 1:
            raise LatentLanguageError("Workspace capacity limits must be positive")
        self.capacity = capacity
        self.max_per_specialist = max_per_specialist
        self.min_score = _unit(min_score, "min_score")
        self.tick = 0
        self.latest: WorkspaceBroadcast | None = None

    @staticmethod
    def score(proposal: SpecialistProposal) -> float:
        benefit = (
            0.30 * proposal.salience + 0.25 * proposal.confidence
            + 0.20 * proposal.urgency + 0.15 * proposal.novelty
        )
        return benefit - 0.10 * min(1.0, proposal.estimated_cost)

    def compete(
        self, state: LatentState, proposals: Sequence[SpecialistProposal]
    ) -> WorkspaceBroadcast:
        ids = [proposal.proposal_id for proposal in proposals]
        if len(ids) != len(set(ids)):
            raise LatentLanguageError("Proposal ids must be unique within a workspace cycle")
        ranked = sorted(
            proposals,
            key=lambda p: (-self.score(p), p.specialist, p.proposal_id),
        )
        selected: list[SpecialistProposal] = []
        counts: dict[str, int] = {}
        conflicts: set[str] = set()
        for proposal in ranked:
            if len(selected) >= self.capacity:
                break
            if self.score(proposal) < self.min_score:
                continue
            if counts.get(proposal.specialist, 0) >= self.max_per_specialist:
                continue
            if proposal.conflict_key and proposal.conflict_key in conflicts:
                continue
            selected.append(proposal)
            counts[proposal.specialist] = counts.get(proposal.specialist, 0) + 1
            if proposal.conflict_key:
                conflicts.add(proposal.conflict_key)
        selected_ids = {p.proposal_id for p in selected}
        rejected = tuple(p for p in proposals if p.proposal_id not in selected_ids)
        self.tick += 1
        broadcast = WorkspaceBroadcast(
            self.tick, state.digest, tuple(selected), rejected,
            {p.proposal_id: self.score(p) for p in proposals},
            {p.proposal_id: _proposal_fingerprint(p) for p in proposals},
        )
        self.latest = broadcast
        return broadcast


@dataclass(frozen=True)
class ISCEFeedback:
    """Bounded observations fed into the next authoritative ISCE transition."""

    novelty: float
    prediction_error: float | None
    modality_novelty: Mapping[str, float]

    def __post_init__(self) -> None:
        _unit(self.novelty, "feedback.novelty")
        if self.prediction_error is not None:
            _unit(self.prediction_error, "feedback.prediction_error")
        for name, value in self.modality_novelty.items():
            if name not in MODALITY_TO_SUBSPACE:
                raise LatentLanguageError(f"Unknown feedback modality: {name}")
            _unit(value, f"{name}.novelty")


@dataclass(frozen=True)
class CognitiveCycleResult:
    state: LatentState
    broadcast: WorkspaceBroadcast
    proposals: tuple[SpecialistProposal, ...]
    feedback: ISCEFeedback


class LatentLanguageCoordinator:
    """Coordinates concurrent specialists over an ephemeral ISCE projection."""

    def __init__(
        self, encoders: EncoderRegistry, *,
        specialists: Sequence[Specialist] | None = None,
        fusion: MultimodalFusion | None = None,
        workspace: GlobalWorkspace | None = None,
        dynamics: Any | None = None,
        alignment_model: Any | None = None,
        max_specialist_workers: int = 8,
    ):
        self.encoders = encoders
        self.fusion = fusion or MultimodalFusion()
        self.workspace = workspace or GlobalWorkspace()
        self.specialists = tuple(specialists or (
            EmotionSpecialist(), CognitiveSpecialist(), MemorySpecialist(),
            SocialSpecialist(), TemporalSpecialist(), SpatialSpecialist(),
            CreativeSpecialist(),
        ))
        self.dynamics = dynamics
        self.alignment_model = alignment_model
        if max_specialist_workers < 1:
            raise LatentLanguageError("max_specialist_workers must be positive")
        self.max_specialist_workers = max_specialist_workers
        self.state = LatentState.empty()
        self._previous_cycle_vector: tuple[float, ...] | None = None

    def _run_specialists(self, state: LatentState, context: SpecialistContext):
        if not self.specialists:
            return ()
        workers = min(self.max_specialist_workers, len(self.specialists))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="chimera-specialist") as pool:
            results = list(pool.map(
                lambda specialist: specialist.propose(state, context),
                self.specialists,
            ))
        return tuple(proposal for group in results for proposal in group)

    def cycle(
        self, observations: Sequence[Mapping[str, Any]], context: SpecialistContext,
        *, dt: float = 0.05, organism_state: Any | None = None,
    ) -> CognitiveCycleResult:
        if dt <= 0 or not math.isfinite(dt):
            raise LatentLanguageError("dt must be finite and positive")
        if self.dynamics is not None and (
            not getattr(self.dynamics, "trained", False)
            or not getattr(self.dynamics, "validated", False)
        ):
            raise LatentLanguageError(
                "Configured morphogenetic dynamics must be trained and held-out validated"
            )

        # Work against a local immutable-state candidate. Failed encoders,
        # specialists, dynamics or arbitration cannot partially publish a cycle.
        working_state = (
            project_isce_state(organism_state, timestamp=context.timestamp)
            if organism_state is not None else self.state
        )
        modality_novelty: dict[str, float] = {}
        encoded_by_modality: dict[str, tuple[float, ...]] = {}
        confidence_by_modality: dict[str, float] = {}
        source_by_modality: dict[str, str] = {}
        for item in observations:
            encoded = self.encoders.encode(
                str(item["modality"]), item["payload"],
                timestamp=float(item.get("timestamp", context.timestamp)),
                confidence=float(item.get("confidence", 1.0)),
                source_id=str(item["source_id"]),
            )
            subspace = MODALITY_TO_SUBSPACE[encoded.modality]
            prior = working_state.subspaces[subspace]
            prior_norm = math.sqrt(sum(value * value for value in prior))
            new_norm = math.sqrt(sum(value * value for value in encoded.embedding))
            novelty = encoded.confidence * (
                0.0 if new_norm == 0.0 else (
                    1.0 if prior_norm == 0.0 else max(0.0, min(1.0,
                        0.5 * (1.0 - _cosine(prior, encoded.embedding))))
                )
            )
            modality_novelty[encoded.modality] = max(
                modality_novelty.get(encoded.modality, 0.0), novelty
            )
            encoded_by_modality[encoded.modality] = encoded.embedding
            confidence_by_modality[encoded.modality] = encoded.confidence
            source_by_modality[encoded.modality] = encoded.source_id
            working_state = self.fusion.update(working_state, encoded)

        prediction_error = None
        if self.dynamics is not None and self._previous_cycle_vector is not None and organism_state is not None:
            predicted = self.dynamics.evolve(self._previous_cycle_vector, dt=dt)
            residual = [
                actual - expected
                for actual, expected in zip(working_state.vector, predicted)
            ]
            rms = math.sqrt(sum(value * value for value in residual) / len(residual))
            prediction_error = max(0.0, min(1.0, rms / 2.0))
        novelty_value = (
            sum(modality_novelty.values()) / len(modality_novelty)
            if modality_novelty else 0.0
        )

        generated = self._run_specialists(working_state, context)
        if self.alignment_model is not None:
            validated_modalities = set(
                getattr(self.alignment_model, "validated_modalities", ())
            )
            aligned_modalities = {
                name: [encoded_by_modality[name]]
                for name in ("text", "image", "audio")
                if name in encoded_by_modality
                and name in validated_modalities
                and confidence_by_modality[name] > 0.0
            }
            if len(aligned_modalities) >= 2:
                aligned = self.alignment_model.fuse_encoded_shared(
                    aligned_modalities,
                    {name: confidence_by_modality[name] for name in aligned_modalities},
                )
                aligned_vector = tuple(
                    float(value) for value in aligned[0].detach().cpu().tolist()
                )
                evidence = tuple(source_by_modality[name] for name in aligned_modalities)
                fusion_proposal = SpecialistProposal(
                    _stable_id("multimodal-fusion", "|".join(evidence) + context.timestamp.__str__()),
                    "multimodal_fusion", "subspace_update",
                    {"subspace": "memory", "vector": aligned_vector,
                     "timestamp": context.timestamp, "modalities": tuple(aligned_modalities)},
                    sum(confidence_by_modality[name] for name in aligned_modalities) / len(aligned_modalities),
                    0.7, 0.1, novelty_value, 0.01, context.world_revision,
                    evidence, conflict_key="memory:working-set",
                )
                generated = generated + (fusion_proposal,)
        # Every specialist competes for the bounded global workspace. Only
        # selected proposals are broadcast and allowed to update latent subspaces.
        broadcast = self.workspace.compete(working_state, generated)
        for proposal in broadcast.selected:
            if proposal.kind == "subspace_update":
                subspace = str(proposal.payload["subspace"])
                working_state = working_state.write_subspace(
                    subspace, proposal.payload["vector"],
                    timestamp=float(proposal.payload["timestamp"]),
                )
            elif proposal.kind == "intent":
                working_state = working_state.write_subspace(
                    "cognition", proposal.payload["vector"], timestamp=context.timestamp
                )
            elif proposal.kind == "memory_retrieval":
                working_state = working_state.write_subspace(
                    "memory", proposal.payload["vector"], timestamp=context.timestamp
                )
        if self.dynamics is not None:
            evolved = self.dynamics.evolve(working_state.vector, dt=dt)
            working_state = LatentState(
                {
                    name: tuple(evolved[offset:offset + size])
                    for offset, (name, size) in _offsets()
                },
                {**working_state.updated_at, "language": context.timestamp,
                 "cognition": context.timestamp},
                working_state.revision + 1,
            )
        self.state = working_state
        self._previous_cycle_vector = tuple(working_state.vector)
        feedback = ISCEFeedback(novelty_value, prediction_error, modality_novelty)
        return CognitiveCycleResult(working_state, broadcast, generated, feedback)


def _offsets():
    offset = 0
    for name, size in SUBSPACE_DIMS.items():
        yield offset, (name, size)
        offset += size



def project_isce_state(organism_state: Any, *, timestamp: float | None = None) -> LatentState:
    """Project current ISCE-owned variables into an ephemeral model workspace.

    This projection is disposable: no latent subspace becomes a second durable
    organism state. Sensory embeddings are added only by registered encoders.
    """
    try:
        body = organism_state.body
        intero = organism_state.interoception
        sensorimotor = organism_state.sensorimotor
        temporal = organism_state.temporal
        self_model = organism_state.self_model
        attention = organism_state.attention
        resources = organism_state.resources
    except AttributeError as exc:
        raise LatentLanguageError("organism_state must expose the canonical ISCE partitions") from exc
    now = float(temporal.organism_time) if timestamp is None else _finite(timestamp, "projection timestamp")
    emotion = _expand_features((
        body.stress, body.fatigue, body.allostatic_error,
        intero.hunger, intero.pain, intero.arousal, intero.precision,
    ), SUBSPACE_DIMS["emotion"])
    cognition = _expand_features((
        self_model.confidence, self_model.curiosity, attention.focus,
        attention.urgency, sensorimotor.motor_readiness,
        sensorimotor.proprioceptive_error,
    ), SUBSPACE_DIMS["cognition"])
    memory = _expand_features((
        self_model.memory_strength, float(temporal.tick > 0),
        float(bool(self_model.last_outcome)), resources.reserve,
    ), SUBSPACE_DIMS["memory"])
    temporal_vector = []
    for index in range(SUBSPACE_DIMS["temporal"] // 2):
        phase = now / (2.0 ** index)
        temporal_vector.extend((math.sin(phase), math.cos(phase)))
    spaces = {name: (0.0,) * size for name, size in SUBSPACE_DIMS.items()}
    spaces.update({
        "emotion": emotion, "cognition": cognition, "memory": memory,
        "temporal": tuple(temporal_vector),
    })
    updated = {
        name: now for name in ("emotion", "cognition", "memory", "temporal")
    }
    return LatentState(spaces, updated, revision=0)

class CognitiveActionGateway:
    """Only selected, evidence-bearing, revision-current proposals can mutate world."""

    def __init__(
        self, toolbox: Any, workspace: GlobalWorkspace, organism: Any, *,
        min_confidence: float = 0.65,
    ):
        if organism is None or getattr(organism, "world", None) is not toolbox.world:
            raise LatentLanguageError("Action gateway requires the ISCE organism for resource admission")
        self.toolbox = toolbox
        self.workspace = workspace
        self.organism = organism
        self.min_confidence = _unit(min_confidence, "min_confidence")

    def execute(self, proposal: SpecialistProposal, *, actor_id: str = "chimera") -> dict[str, Any]:
        latest = self.workspace.latest
        if latest is None or proposal.proposal_id not in {
            item.proposal_id for item in latest.selected
        }:
            raise LatentLanguageError("Proposal was not selected by the latest global workspace")
        if latest.proposal_fingerprints.get(proposal.proposal_id) != _proposal_fingerprint(proposal):
            raise LatentLanguageError("Proposal changed after workspace arbitration")
        if proposal.kind != "world_action":
            raise LatentLanguageError("Only world_action proposals can cross the action gateway")
        if proposal.confidence < self.min_confidence:
            raise LatentLanguageError("Proposal confidence is below the action threshold")
        available_reserve = self.organism.state.resources.reserve
        if proposal.estimated_cost > available_reserve:
            raise LatentLanguageError(
                f"Estimated action cost {proposal.estimated_cost:.3f} exceeds "
                f"ISCE reserve {available_reserve:.3f}"
            )
        if not proposal.evidence_refs:
            raise LatentLanguageError("World actions require explicit evidence provenance")
        current_revision = self.toolbox.world.revision()
        if proposal.world_revision != current_revision:
            raise LatentLanguageError(
                f"Stale proposal revision {proposal.world_revision}; world is {current_revision}"
            )
        payload = proposal.payload
        if not isinstance(payload, Mapping):
            raise LatentLanguageError("World action payload must be a mapping")
        tool_name = str(payload.get("tool", ""))
        action_name = str(payload.get("action", ""))
        arguments = payload.get("arguments")
        if not isinstance(arguments, Mapping):
            raise LatentLanguageError("World action arguments must be a mapping")
        allowed = any(
            definition["name"] == tool_name and action_name in definition["actions"]
            for definition in self.toolbox.manifest()
        )
        if not allowed:
            raise LatentLanguageError(f"Toolbox action is not allowlisted: {tool_name}.{action_name}")
        reserve_before = available_reserve
        # Debit the estimated action cost before the world mutation. If the action
        # subsequently fails world validation, the attempt still consumes its
        # estimated compute cost; an action can never commit without its debit.
        charge_result = None
        action_revision = current_revision
        if proposal.estimated_cost > 0.0:
            charge_result = self.organism.tick(
                dt=self.toolbox.world.config.fixed_dt,
                action_energy_cost=proposal.estimated_cost,
                mechanical_strain=0.0,
                prediction_error=0.0,
                novelty=0.0,
                outcome=f"cognitive_action_attempt:{proposal.specialist}",
                expected_revision=current_revision,
            )
            action_revision = charge_result.revision
        result = self.toolbox.execute(
            tool_name, action_name, dict(arguments),
            actor_id=actor_id, expected_revision=action_revision,
        )
        result["resource_charge"] = {
            "estimated_cost": proposal.estimated_cost,
            "reserve_before": reserve_before,
            "reserve_after": self.organism.state.resources.reserve,
            "charge_revision": action_revision if charge_result is not None else None,
            "charged_before_action": charge_result is not None,
        }
        return result
