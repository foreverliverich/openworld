"""Optional PyTorch tests for multimodal alignment training."""
import importlib.util
import os
import tempfile
import unittest

from chimera.latent_training import AlignmentTrainingError, MultimodalProjectionModel
from chimera.latent_language import EncoderRegistry, LatentLanguageCoordinator, SpecialistContext


@unittest.skipUnless(importlib.util.find_spec("torch"), "optional PyTorch extra not installed")
class MultimodalAlignmentTests(unittest.TestCase):
    def test_contrastive_alignment_audio_compression_and_evaluation(self):
        import torch
        generator = torch.Generator().manual_seed(5)
        shared = torch.randn(8, 512, generator=generator)
        pairs = {
            "text": torch.cat((shared, 0.1 * torch.randn(8, 256, generator=generator)), dim=1),
            "image": shared,
            "audio": torch.cat((shared, 0.1 * torch.randn(8, 256, generator=generator)), dim=1),
        }
        validation_generator = torch.Generator().manual_seed(19)
        validation_shared = torch.randn(8, 512, generator=validation_generator)
        validation = {
            "text": torch.cat((validation_shared, 0.1 * torch.randn(8, 256, generator=validation_generator)), dim=1),
            "image": validation_shared,
            "audio": torch.cat((validation_shared, 0.1 * torch.randn(8, 256, generator=validation_generator)), dim=1),
        }
        model = MultimodalProjectionModel(seed=11)
        history = model.fit(pairs, epochs=2, batch_size=8)
        self.assertEqual(len(history), 2)
        metrics = model.evaluate(validation)
        self.assertIn("text_to_image_recall_at_1", metrics)
        self.assertIn("text_to_audio_recall_at_1", metrics)
        self.assertIn("audio_reconstruction_mse", metrics)
        fused = model.fuse_shared(
            {"text": validation["text"], "image": validation["image"],
             "audio": validation["audio"]},
            confidence={"text": 0.9, "image": 0.8, "audio": 0.7},
        )
        self.assertEqual(tuple(fused.shape), (8, 512))
        projected = model.project_audio_slot(validation["audio"])
        self.assertEqual(tuple(projected.shape), (8, 128))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "alignment.pt")
            model.save_checkpoint(path)
            restored = MultimodalProjectionModel(seed=99)
            restored.load_checkpoint(path)
            self.assertEqual(tuple(restored.project_audio_slot(validation["audio"]).shape), (8, 128))
            class FixedEncoder:
                def __init__(self, size, base_encoder_id):
                    self.size = size
                    self.encoder_id = f"test-fixed-{size}"
                    self.base_encoder_id = base_encoder_id
                def encode(self, payload):
                    return (0.1,) * self.size
            registry = EncoderRegistry()
            registry.register("text", FixedEncoder(768, "hf:bert-base-uncased"))
            registry.register("image", FixedEncoder(512, "hf:openai/clip-vit-base-patch32"))
            registry.register("audio", FixedEncoder(128, "hf:facebook/wav2vec2-base"))
            coordinator = LatentLanguageCoordinator(registry, alignment_model=restored)
            cycle = coordinator.cycle(
                [
                    {"modality": "text", "payload": "paired", "timestamp": 3.0,
                     "confidence": 0.9, "source_id": "pair:text"},
                    {"modality": "image", "payload": "paired", "timestamp": 3.0,
                     "confidence": 0.9, "source_id": "pair:image"},
                    {"modality": "audio", "payload": "paired", "timestamp": 3.0,
                     "confidence": 0.9, "source_id": "pair:audio"},
                ],
                SpecialistContext(3.0, 0, source_refs=("paired-example",)),
            )
            self.assertIn(
                "multimodal_fusion",
                {proposal.specialist for proposal in cycle.broadcast.selected},
            )
            self.assertGreater(
                sum(abs(value) for value in cycle.state.subspaces["memory"]), 0.0
            )
        with self.assertRaises(AlignmentTrainingError):
            MultimodalProjectionModel().fit({"text": pairs["text"]})


if __name__ == "__main__":
    unittest.main()
