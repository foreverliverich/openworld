"""Optional PyTorch acceptance tests for learned morphogenetic dynamics."""
import importlib.util
import os
import tempfile
import unittest

from chimera.learned_dynamics import DynamicsTrainingError, TorchMorphogeneticDynamics
from chimera.latent_language import (
    LATENT_DIMENSIONS, EncoderRegistry, LatentLanguageCoordinator, SpecialistContext,
)
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, WorldConfig


@unittest.skipUnless(importlib.util.find_spec("torch"), "optional PyTorch extra not installed")
class LearnedDynamicsTests(unittest.TestCase):
    def test_train_evaluate_checkpoint_and_rk4_evolution(self):
        trajectories = []
        for sequence_id in range(4):
            sequence = []
            for step in range(3):
                sequence.append([
                    0.001 * (index % 17) + 0.002 * step + 0.001 * sequence_id
                    for index in range(LATENT_DIMENSIONS)
                ])
            trajectories.append(sequence)
        model = TorchMorphogeneticDynamics(hidden_dim=32, seed=7)
        with self.assertRaises(DynamicsTrainingError):
            model.evolve(trajectories[0][0])
        history = model.fit(
            trajectories[:3], validation=trajectories[3:], epochs=2, batch_size=4
        )
        self.assertEqual(len(history), 2)
        metrics = model.evaluate(trajectories[3:])
        self.assertGreater(metrics["transition_count"], 0)
        evolved = model.evolve(trajectories[0][0], dt=0.02)
        self.assertEqual(len(evolved), LATENT_DIMENSIONS)
        self.assertTrue(all(-10 <= value <= 10 for value in evolved))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "dynamics.pt")
            model.save_checkpoint(path)
            restored = TorchMorphogeneticDynamics(hidden_dim=32, seed=99)
            restored.load_checkpoint(path)
            self.assertEqual(
                len(restored.evolve(trajectories[0][0], dt=0.02)),
                LATENT_DIMENSIONS,
            )
        with tempfile.TemporaryDirectory() as tmp:
            world = RealityEngine(WorldConfig(database=os.path.join(tmp, "dynamics-isce.sqlite3")))
            organism = OrganismKernel(world, "dynamics-integration")
            coordinator = LatentLanguageCoordinator(EncoderRegistry(), dynamics=restored)
            first = coordinator.cycle(
                [], SpecialistContext(1.0, world.revision()),
                organism_state=organism.state,
            )
            second = coordinator.cycle(
                [], SpecialistContext(1.05, world.revision()), dt=0.05,
                organism_state=organism.state,
            )
            self.assertIsNone(first.feedback.prediction_error)
            self.assertIsNotNone(second.feedback.prediction_error)
            world.close()


if __name__ == "__main__":
    unittest.main()
