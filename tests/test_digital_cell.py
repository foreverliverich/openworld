import os
import tempfile
import unittest

from chimera.digital_cell import CellObservation, DigitalCell, DigitalCellState
from chimera.isce import ISCEKernel, OrganismState
from chimera.action_gateway import OrganismActionGateway
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, WorldConfig
from chimera.toolbox import ChimeraToolbox


class DigitalCellTests(unittest.TestCase):
    def setUp(self):
        self.kernel = ISCEKernel()
        self.organism = OrganismState(organism_id="cell-test")

    def test_step_is_proposal_until_commit(self):
        cell = DigitalCell()
        before = cell.state
        result = cell.step(CellObservation(0.9, 0.1, 0.4), self.organism, self.kernel)
        self.assertEqual(cell.state, before)
        self.assertEqual(result.state.tick, 1)
        self.assertEqual(result.organism_state.temporal.tick, 1)
        cell.commit(result)
        self.assertEqual(cell.state, result.state)

    def test_action_memory_changes_after_committed_feedback(self):
        cell, organism = DigitalCell(), self.organism
        before = cell.state.action_values
        for _ in range(8):
            result = cell.step(CellObservation(1.0, 0.0, 0.2), organism, self.kernel)
            organism = result.organism_state
            cell.commit(result)
        self.assertNotEqual(cell.state.action_values, before)
        self.assertGreater(cell.state.memory_strength, 0.0)

    def test_membrane_spike_is_required_for_seek(self):
        cell = DigitalCell(DigitalCellState(energy=0.8, stress=0.0, action_values=(-0.5, 1.0, -0.5)))
        result = cell.step(CellObservation(1.0, 0.0), self.organism, self.kernel)
        self.assertFalse(result.membrane_fired)
        self.assertNotEqual(result.action, "seek")

    def test_spike_allows_seek_when_learned_value_is_high(self):
        cell = DigitalCell(DigitalCellState(energy=0.8, stress=0.0, membrane_potential=0.5, action_values=(-0.5, 1.0, -0.5)))
        result = cell.step(CellObservation(1.0, 0.0), self.organism, self.kernel)
        self.assertTrue(result.membrane_fired)
        self.assertEqual(result.action, "seek")


    def test_refractory_period_suppresses_seek_even_with_high_value(self):
        cell = DigitalCell(DigitalCellState(energy=0.8, stress=0.0, membrane_potential=0.7, refractory_ticks=1, action_values=(-0.5, 1.0, -0.5)))
        result = cell.step(CellObservation(1.0, 0.0), self.organism, self.kernel)
        self.assertFalse(result.membrane_fired)
        self.assertNotEqual(result.action, "seek")

    def test_stale_commit_cannot_overwrite_newer_state(self):
        cell = DigitalCell()
        obs = CellObservation(0.5, 0.2)
        first = cell.step(obs, self.organism, self.kernel)
        second = cell.step(obs, self.organism, self.kernel)
        cell.commit(first)
        with self.assertRaises(ValueError):
            cell.commit(second)
        self.assertEqual(cell.state, first.state)

    def test_homeostatic_gate_forces_rest_when_depleted(self):
        cell = DigitalCell(DigitalCellState(energy=0.1, stress=0.2))
        result = cell.step(CellObservation(0.0, 0.0), self.organism, self.kernel)
        self.assertEqual(result.action, "rest")

    def test_invalid_observation_and_state_are_rejected(self):
        with self.assertRaises(ValueError):
            CellObservation(2.0, 0.0)
        with self.assertRaises(ValueError):
            DigitalCellState(energy=float("nan"))

    def test_cell_executes_seek_through_world_gateway_and_commits_isce(self):
        with tempfile.TemporaryDirectory() as tmp:
            world = RealityEngine(WorldConfig(
                database=os.path.join(tmp, "cell-world.sqlite3")
            ))
            try:
                organism = OrganismKernel(world, "integrated-cell")
                toolbox = ChimeraToolbox(world, actor_id=organism.organism_id)
                gateway = OrganismActionGateway(world, organism, toolbox)
                world.inject_field(
                    "energy", organism.state.position, 0.2,
                    actor_id="environment", radius=0,
                )
                cell = DigitalCell(DigitalCellState(
                    energy=0.2, stress=0.0, membrane_potential=0.7,
                    action_values=(-0.5, 1.0, -0.5),
                ))
                before = world.field_at(organism.state.position)["energy"]
                result = cell.execute(
                    CellObservation(energy_supply=before, environmental_stress=0.0),
                    organism, gateway,
                )
                after = world.field_at(organism.state.position)["energy"]
                self.assertEqual(result["action"], "seek")
                self.assertIsNotNone(result["receipt"])
                self.assertAlmostEqual(before - after, 0.05)
                self.assertEqual(cell.state.tick, 1)
                self.assertEqual(organism.state.temporal.tick, 1)
                self.assertEqual(world.revision(), 3)
                self.assertTrue(world.verify_event_chain())
            finally:
                world.close()

    def test_cell_rest_commits_proposed_isce_state_before_cell_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            world = RealityEngine(WorldConfig(
                database=os.path.join(tmp, "rest-world.sqlite3")
            ))
            try:
                organism = OrganismKernel(world, "resting-cell")
                gateway = OrganismActionGateway(world, organism)
                cell = DigitalCell(DigitalCellState(energy=0.1, stress=0.2))
                result = cell.execute(
                    CellObservation(energy_supply=0.0, environmental_stress=0.0),
                    organism, gateway,
                )
                self.assertEqual(result["action"], "rest")
                self.assertIsNone(result["receipt"])
                self.assertEqual(cell.state.tick, 1)
                self.assertEqual(organism.state.temporal.tick, 1)
                self.assertGreater(cell.state.energy, 0.1)
                self.assertTrue(world.verify_event_chain())
            finally:
                world.close()

    def test_identical_inputs_are_reproducible(self):
        obs = CellObservation(0.7, 0.2, 0.3)
        a, b = DigitalCell(), DigitalCell()
        self.assertEqual(a.step(obs, self.organism, self.kernel), b.step(obs, self.organism, self.kernel))


if __name__ == "__main__":
    unittest.main()
