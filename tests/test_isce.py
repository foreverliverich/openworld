"""ISCE deterministic transition, invariance and intervention tests."""
import unittest

from chimera.isce import (
    CausalGraph, ISCEError, ISCEKernel, Intervention, OrganismState,
    TransitionInput,
)


class ISCEKernelTests(unittest.TestCase):
    def setUp(self):
        self.kernel = ISCEKernel()
        self.initial = OrganismState("isce-test")
        self.inputs = TransitionInput(
            dt=1.0, action_energy_cost=0.08, mechanical_strain=0.4,
            prediction_error=0.7, novelty=0.8, action_success=0.9,
            environmental_energy=0.2, environmental_stress=0.3,
            environmental_memory=0.1, environmental_cohesion=0.4,
            measured_work_units=12.0, outcome="observed-construction",
        )

    def test_transition_is_deterministic(self):
        a = self.kernel.transition(self.initial, self.inputs)
        b = self.kernel.transition(self.initial, self.inputs)
        self.assertEqual(a.state.to_dict(), b.state.to_dict())
        self.assertEqual(a.state_digest, b.state_digest)

    def test_graph_topology_and_weights_remain_fixed(self):
        before = self.kernel.graph_fingerprint
        state = self.initial
        for _ in range(20):
            state = self.kernel.transition(
                state, TransitionInput(dt=0.1, novelty=0.2)
            ).state
        self.assertEqual(before, self.kernel.graph_fingerprint)
        self.assertEqual(before, self.kernel.graph.fingerprint())

    def test_state_serialization_round_trip(self):
        result = self.kernel.transition(self.initial, self.inputs)
        restored = OrganismState.from_dict(result.state.to_dict())
        self.assertEqual(restored, result.state)

    def test_temporal_causality_links_previous_state(self):
        first = self.kernel.transition(self.initial, self.inputs).state
        second = self.kernel.transition(first, self.inputs).state
        self.assertEqual(first.digest(), second.temporal.previous_state_digest)
        self.assertEqual(second.temporal.tick, 2)
        self.assertAlmostEqual(second.temporal.organism_time, 2.0)

    def test_intervention_has_specific_downstream_effect_without_graph_change(self):
        baseline = self.kernel.transition(self.initial, self.inputs)
        intervention = Intervention("body.stress", 0.4)
        perturbed = self.kernel.transition(self.initial, self.inputs, intervention)
        self.assertGreater(perturbed.state.body.stress,
                           baseline.state.body.stress)
        self.assertGreater(perturbed.state.attention.urgency,
                           baseline.state.attention.urgency)
        self.assertEqual(perturbed.graph_fingerprint,
                         baseline.graph_fingerprint)

    def test_invalid_intervention_and_nonfinite_inputs_rejected(self):
        with self.assertRaises(ISCEError):
            Intervention("graph.edge", 1.0)
        with self.assertRaises(ISCEError):
            self.kernel.transition(self.initial, TransitionInput(dt=float("nan")))

    def test_viability_gate_uses_intrinsic_state(self):
        self.assertTrue(self.kernel.can_act(self.initial))
        depleted = self.kernel.transition(
            self.initial, TransitionInput(dt=10.0, action_energy_cost=1.0)
        ).state
        self.assertFalse(self.kernel.can_act(depleted))

    def test_graph_rejects_unknown_edges(self):
        from chimera.isce import CausalEdge
        with self.assertRaises(ISCEError):
            CausalGraph(("a",), (CausalEdge("a", "missing", 1.0),))


if __name__ == "__main__":
    unittest.main()
