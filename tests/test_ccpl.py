"""Regression tests for the paired ISCE causal intervention battery."""
import unittest

from chimera.ccpl import run_ccpl
from chimera.isce import ISCEKernel, Intervention, OrganismState, TransitionInput


class CCPLTests(unittest.TestCase):
    def setUp(self):
        self.kernel = ISCEKernel()
        self.initial = OrganismState("ccpl-subject")
        self.inputs = tuple(
            TransitionInput(
                dt=0.5, action_energy_cost=0.002,
                prediction_error=0.12, novelty=0.08,
                action_success=0.7, environmental_stress=0.03,
            )
            for _ in range(12)
        )

    def run_battery(self):
        return run_ccpl(self.kernel, self.initial, self.inputs)

    def test_sham_matches_baseline(self):
        result = self.run_battery()
        self.assertAlmostEqual(result["summary"]["sham_error"], 0.0, places=12)

    def test_single_intervention_changes_trajectory(self):
        result = self.run_battery()
        self.assertNotEqual(
            result["conditions"]["single"][-1],
            result["conditions"]["baseline"][-1],
        )

    def test_double_intervention_is_applied_in_same_tick(self):
        result = self.run_battery()
        self.assertNotEqual(
            result["conditions"]["double"][-1],
            result["conditions"]["single"][-1],
        )

    def test_mediator_block_attenuates_downstream_effect(self):
        result = self.run_battery()
        self.assertGreater(
            abs(result["summary"]["single_effect"]),
            abs(result["summary"]["mediated_effect"]),
        )

    def test_repeated_runs_are_bitwise_deterministic(self):
        self.assertEqual(self.run_battery(), self.run_battery())

    def test_graph_fingerprint_is_unchanged(self):
        before = self.kernel.graph_fingerprint
        self.run_battery()
        self.assertEqual(self.kernel.graph_fingerprint, before)

    def test_invalid_intervention_targets_reject(self):
        with self.assertRaises(ValueError):
            run_ccpl(
                self.kernel, self.initial, self.inputs,
                source=Intervention("unknown.target", 0.1),
            )

    def test_double_intervention_requires_distinct_targets(self):
        with self.assertRaises(ValueError):
            run_ccpl(
                self.kernel, self.initial, self.inputs,
                source=Intervention("body.energy", 0.1),
                second=Intervention("body.energy", 0.2),
            )

    def test_input_sequence_and_intervention_tick_are_validated(self):
        with self.assertRaises(ValueError):
            run_ccpl(self.kernel, self.initial, ())
        with self.assertRaises(ValueError):
            run_ccpl(self.kernel, self.initial, self.inputs, intervention_tick=99)


if __name__ == "__main__":
    unittest.main()
