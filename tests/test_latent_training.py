"""Optional PyTorch tests for multimodal alignment training."""
import importlib.util
import os
import tempfile
import unittest

from chimera.latent_training import AlignmentTrainingError, MultimodalProjectionModel


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
        projected = model.project_audio_slot(validation["audio"])
        self.assertEqual(tuple(projected.shape), (8, 128))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "alignment.pt")
            model.save_checkpoint(path)
            restored = MultimodalProjectionModel(seed=99)
            restored.load_checkpoint(path)
            self.assertEqual(tuple(restored.project_audio_slot(validation["audio"]).shape), (8, 128))
        with self.assertRaises(AlignmentTrainingError):
            MultimodalProjectionModel().fit({"text": pairs["text"]})


if __name__ == "__main__":
    unittest.main()
