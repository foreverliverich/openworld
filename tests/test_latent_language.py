"""Executable acceptance tests for Latent Language 3.0 core contracts."""
import os
import tempfile
import unittest

from chimera.latent_language import (
    CognitiveActionGateway, EncodedObservation, EncoderRegistry, GlobalWorkspace,
    LATENT_DIMENSIONS, LatentLanguageCoordinator, LatentLanguageError,
    LatentState, SceneGraph, SceneObject, SpatialRelation, SpecialistContext,
    SUBSPACE_DIMS,
)
from chimera.reality_engine import RealityEngine, WorldConfig
from chimera.toolbox import ChimeraToolbox


class FixedEncoder:
    encoder_id = "test-fixed-encoder"

    def __init__(self, size, value=0.25, shared_space=None):
        self.size = size
        self.value = value
        self.shared_space = shared_space

    def encode(self, payload):
        return (self.value,) * self.size


class LatentLanguageTests(unittest.TestCase):
    def test_source_defined_dimensions_are_preserved(self):
        self.assertEqual(SUBSPACE_DIMS, {
            "language": 768, "emotion": 128, "cognition": 256,
            "memory": 512, "social": 64, "temporal": 32,
            "visual": 512, "audio": 128, "sensor": 64,
        })
        state = LatentState.empty()
        self.assertEqual(len(state.vector), 2464)
        self.assertEqual(len(state.digest), 64)

    def test_registry_refuses_missing_encoder_and_fuses_confidence(self):
        registry = EncoderRegistry()
        with self.assertRaises(LatentLanguageError):
            registry.encode("image", object(), timestamp=1, confidence=1, source_id="cam")
        registry.register("text", FixedEncoder(768, value=0.8))
        observation = registry.encode(
            "text", "input", timestamp=10, confidence=0.5, source_id="mic-text"
        )
        state = LatentState.empty()
        fused = __import__("chimera.latent_language", fromlist=["MultimodalFusion"]).MultimodalFusion().update(
            state, observation
        )
        self.assertEqual(fused.subspaces["language"][0], 0.4)
        self.assertEqual(fused.updated_at["language"], 10)

    def test_out_of_order_observation_and_unaligned_similarity_are_rejected(self):
        from chimera.latent_language import MultimodalFusion
        fusion = MultimodalFusion()
        state = LatentState.empty()
        newer = EncodedObservation("text", (0.1,) * 768, 5, 1, "a", "enc")
        state = fusion.update(state, newer)
        older = EncodedObservation("text", (0.2,) * 768, 4, 1, "b", "enc")
        with self.assertRaises(LatentLanguageError):
            fusion.update(state, older)
        left = EncodedObservation("image", (0.1,) * 512, 5, 1, "i", "clip-image")
        right = EncodedObservation("text", (0.1,) * 768, 5, 1, "t", "bert")
        with self.assertRaises(LatentLanguageError):
            fusion.aligned_similarity(left, right)

    def test_scene_graph_compiles_relation_and_rejects_invalid_containment(self):
        graph = SceneGraph(
            "test-scene",
            (
                SceneObject("base", "platform", (0, 0.5, 0), (2, 1, 2), dynamic=False),
                SceneObject("lamp", "lamp", (0, 2, 0), (0.3, 0.5, 0.3), dynamic=False),
            ),
            (SpatialRelation("on_top", "lamp", "base", gap=0.0),),
        )
        blueprint = graph.to_blueprint()
        self.assertEqual(blueprint["name"], "test-scene")
        self.assertAlmostEqual(blueprint["parts"][1]["position"][1], 1.25)
        bad = SceneGraph(
            "bad-scene",
            (
                SceneObject("container", "box", (0, 0, 0), (1, 1, 1)),
                SceneObject("oversize", "sphere", (0, 0, 0), (2, 2, 2)),
            ),
            (SpatialRelation("inside", "oversize", "container"),),
        )
        with self.assertRaises(LatentLanguageError):
            bad.to_blueprint()

    def test_global_workspace_competes_deterministically_with_capacity(self):
        from chimera.latent_language import SpecialistProposal
        proposals = [
            SpecialistProposal(
                f"p{i}", f"agent{i}", "candidate", {}, 0.8, 0.8, 0.2, 0.3,
                0.0, 0, ("source",),
            ) for i in range(5)
        ]
        workspace = GlobalWorkspace(capacity=2)
        result = workspace.compete(LatentState.empty(), proposals)
        self.assertEqual(len(result.selected), 2)
        self.assertEqual(len(result.rejected), 3)
        self.assertEqual(result.selected[0].proposal_id, "p0")

    def test_full_pipeline_and_revision_checked_world_action_gateway(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            world = RealityEngine(WorldConfig(database=os.path.join(tmp.name, "latent.sqlite3")))
            toolbox = ChimeraToolbox(world, actor_id="latent-test")
            encoders = EncoderRegistry()
            encoders.register("text", FixedEncoder(768, value=0.15))
            coordinator = LatentLanguageCoordinator(encoders)
            graph = SceneGraph(
                "workspace-scene",
                (
                    SceneObject("platform", "platform", (0, 0.5, 0), (2, 1, 2),
                                material="stone", dynamic=False),
                    SceneObject("marker", "marker", (1.2, 0.5, 0), (0.2, 0.2, 0.2),
                                material="metal", dynamic=False),
                ),
                (SpatialRelation("next_to", "marker", "platform", gap=0.1),),
            )
            context = SpecialistContext(
                timestamp=1.0, world_revision=world.revision(),
                text="Build a small platform scene",
                scene_graph=graph, source_refs=("user:request-1",),
            )
            result = coordinator.cycle(
                [{"modality": "text", "payload": "Build a small platform scene",
                  "source_id": "user:request-1", "timestamp": 1.0}],
                context,
            )
            self.assertEqual(len(result.state.vector), LATENT_DIMENSIONS)
            self.assertGreater(result.state.subspaces["language"][0], 0)
            spatial = next(p for p in result.broadcast.selected if p.specialist == "spatial")
            gateway = CognitiveActionGateway(toolbox, coordinator.workspace)
            committed = gateway.execute(spatial, actor_id="latent-test")
            self.assertTrue(committed["accepted"])
            self.assertEqual(world.revision(), committed["revision"])
            self.assertTrue(world.verify_event_chain())
            world.close()
        finally:
            tmp.cleanup()

    def test_gateway_rejects_unselected_proposal(self):
        from chimera.latent_language import SpecialistProposal
        tmp = tempfile.TemporaryDirectory()
        try:
            world = RealityEngine(WorldConfig(database=os.path.join(tmp.name, "gateway.sqlite3")))
            toolbox = ChimeraToolbox(world)
            workspace = GlobalWorkspace()
            proposal = SpecialistProposal(
                "unselected", "spatial", "world_action",
                {"tool": "world_builder", "action": "create_structure",
                 "arguments": {"blueprint": {"name": "x", "parts": []}}},
                0.9, 0.9, 0.9, 0.9, 0.0, world.revision(), ("source",),
            )
            gateway = CognitiveActionGateway(toolbox, workspace)
            with self.assertRaises(LatentLanguageError):
                gateway.execute(proposal)
            world.close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
