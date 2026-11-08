import unittest

from chimera.digital_cell import CellObservation, DigitalCell, DigitalCellState
from chimera.isce import ISCEKernel, OrganismState


class DigitalCellTests(unittest.TestCase):
    def setUp(self):
        self.kernel = ISCEKernel()
        self.organism = OrganismState(organism_id="cell-test")

    def test_step_closes_cell_and_isce_transition(self):
        cell = DigitalCell()
        result = cell.step(
            CellObservation(energy_supply=0.9, environmental_stress=0.1, novelty=0.4),
            self.organism, self.kernel,
        )
        self.assertEqual(result.state.tick, 1)
        self.assertEqual(result.organism_state.temporal.tick, 1)
        self.assertEqual(result.organism_state.organism_id, "cell-test")
        self.assertIn(result.action, DigitalCell.ACTIONS)

    def test_action_memory_changes_after_feedback(self):
        cell = DigitalCell()
        before = cell.state.action_values
        for _ in range(8):
            result = cell.step(
                CellObservation(energy_supply=1.0, environmental_stress=0.0),
                self.organism, self.kernel,
            )
            self.organism = result.organism_state
        self.assertNotEqual(cell.state.action_values, before)
        self.assertGreater(cell.state.memory_strength, 0.0)

    def test_homeostatic_gate_forces_rest_when_depleted(self):
        cell = DigitalCell(DigitalCellState(energy=0.1, stress=0.2))
        result = cell.step(
            CellObservation(energy_supply=0.0, environmental_stress=0.0),
            self.organism, self.kernel,
        )
        self.assertEqual(result.action, "rest")

    def test_invalid_observation_and_state_are_rejected(self):
        with self.assertRaises(ValueError):
            CellObservation(energy_supply=2.0, environmental_stress=0.0)
        with self.assertRaises(ValueError):
            DigitalCellState(energy=float("nan"))

    def test_identical_inputs_are_reproducible(self):
        obs = CellObservation(0.7, 0.2, 0.3)
        a, b = DigitalCell(), DigitalCell()
        ra = a.step(obs, self.organism, self.kernel)
        rb = b.step(obs, self.organism, self.kernel)
        self.assertEqual(ra, rb)


if __name__ == "__main__":
    unittest.main()
