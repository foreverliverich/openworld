"""Optional PyTorch tests for multimodal alignment training."""
import importlib.util
import unittest

from chimera.latent_training import AlignmentTrainingError, MultimodalProjectionModel


@unittest.skipUnless(importlib.util.find_spec("torch"), "optional PyTorch extra not installed")
class MultimodalAlignmentTests(unittest.TestCase):
    def test_contrastive_alignment_audio_compression_and_evaluation(self):
        import torch
        generator = torch.Generator().manual_seed(5)
        pairs = {
            "text": torch.randn(4, 768, generator=generator),
            "image": torch.randn(4, 512, generator=generator),
            "audio": torch.randn(4, 768, generator=generator),
        }
        model = MultimodalProjectionModel(seed=11)
        history = model.fit(pairs, epochs=1, batch_size=4)
        self.assertEqual(len(history), 1)
        metrics = model.evaluate(pairs)
        self.assertIn("text_to_image_recall_at_1", metrics)
        self.assertIn("text_to_audio_recall_at_1", metrics)
        self.assertIn("audio_reconstruction_mse", metrics)
        projected = model.project_audio_slot(pairs["audio"])
        self.assertEqual(tuple(projected.shape), (4, 128))
        with self.assertRaises(AlignmentTrainingError):
            MultimodalProjectionModel().fit({"text": pairs["text"]})


if __name__ == "__main__":
    unittest.main()
