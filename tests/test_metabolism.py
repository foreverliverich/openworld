import unittest

from chimera.metabolism import (
    CirculationEdge, ComputationalBloodstream, MetabolicCalibration,
    MetabolicState, MetabolismError, OrganSpec, WorkMeasurement,
)


def make_bloodstream():
    organs = [
        OrganSpec("core", capacity=1.0, setpoint=0.65, minimum=0.10),
        OrganSpec("motor", capacity=1.0, setpoint=0.55, minimum=0.10),
        OrganSpec("sensor", capacity=1.0, setpoint=0.55, minimum=0.10),
    ]
    edges = [
        CirculationEdge("core", "motor", 0.8),
        CirculationEdge("core", "sensor", 0.8),
    ]
    calibration = MetabolicCalibration(
        version="test-v1",
        units_per_operation=0.01,
        units_per_cpu_ms=0.0,
        units_per_kib_moved=0.0,
        units_per_gpu_ms=0.0,
    )
    return ComputationalBloodstream(organs, edges, calibration)


class ComputationalBloodstreamTests(unittest.TestCase):
    def setUp(self):
        self.system = make_bloodstream()

    def test_flow_conserves_reserve_and_restores_deficits(self):
        state = self.system.initial_state({
            "core": 0.95, "motor": 0.20, "sensor": 0.20,
        })
        result = self.system.step(state, {}, dt=1.0)
        reserves = result.state.as_dict()
        self.assertGreater(reserves["motor"], 0.20)
        self.assertGreater(reserves["sensor"], 0.20)
        self.assertAlmostEqual(sum(reserves.values()), sum(state.as_dict().values()))
        self.assertAlmostEqual(result.conservation_error, 0.0, places=12)

    def test_starvation_gate_rejects_work_that_would_breach_minimum(self):
        state = self.system.initial_state({"core": 0.12, "motor": 0.55, "sensor": 0.55})
        result = self.system.step(
            state, {"core": WorkMeasurement(operations=3)}
        )
        self.assertEqual(dict(result.admitted)["core"], False)
        self.assertEqual(dict(result.consumed_cost)["core"], 0.0)
        self.assertGreater(result.state.cumulative_unmet_demand, 0.0)
        self.assertAlmostEqual(result.state.as_dict()["core"], 0.12)

    def test_work_is_charged_from_measured_counters_through_versioned_calibration(self):
        state = self.system.initial_state()
        result = self.system.step(
            state,
            {"motor": WorkMeasurement(operations=10, cpu_time_ns=2_000_000)},
        )
        self.assertAlmostEqual(dict(result.requested_cost)["motor"], 0.1)
        self.assertAlmostEqual(result.state.cumulative_consumption, 0.1)

    def test_no_circulation_means_no_cross_organ_transfer(self):
        state = self.system.initial_state({
            "core": 0.95, "motor": 0.20, "sensor": 0.20,
        })
        result = self.system.step(state, {}, circulation_enabled=False)
        self.assertEqual(result.state.as_dict(), state.as_dict())
        self.assertEqual(result.flow_events, ())

    def test_circulation_is_invariant_to_edge_declaration_order(self):
        organs = [
            OrganSpec("core", capacity=1.0, setpoint=0.65, minimum=0.10),
            OrganSpec("motor", capacity=1.0, setpoint=0.55, minimum=0.10),
            OrganSpec("sensor", capacity=1.0, setpoint=0.55, minimum=0.10),
        ]
        edges = [
            CirculationEdge("core", "motor", 0.8),
            CirculationEdge("core", "sensor", 0.8),
        ]
        calibration = MetabolicCalibration(version="order-test-v1")
        forward = ComputationalBloodstream(organs, edges, calibration)
        reverse = ComputationalBloodstream(organs, list(reversed(edges)), calibration)
        initial = {"core": 0.95, "motor": 0.20, "sensor": 0.20}
        a = forward.step(forward.initial_state(initial), {})
        b = reverse.step(reverse.initial_state(initial), {})
        for name, value in a.state.as_dict().items():
            self.assertAlmostEqual(value, b.state.as_dict()[name], places=12)

    def test_work_admission_changes_when_circulation_is_enabled(self):
        state = self.system.initial_state({
            "core": 0.95, "motor": 0.20, "sensor": 0.55,
        })
        demand = {"motor": WorkMeasurement(operations=12)}
        with_flow = self.system.step(state, demand, circulation_enabled=True)
        without_flow = self.system.step(state, demand, circulation_enabled=False)
        self.assertEqual(dict(with_flow.admitted)["motor"], True)
        self.assertEqual(dict(without_flow.admitted)["motor"], False)

    def test_production_is_capacity_limited_and_accounted(self):
        state = self.system.initial_state({"core": 0.95, "motor": 0.55, "sensor": 0.55})
        result = self.system.step(state, {}, production={"core": 0.5})
        self.assertAlmostEqual(result.state.cumulative_production, 0.05)
        self.assertLessEqual(result.state.as_dict()["core"], 1.0)
        self.assertAlmostEqual(result.conservation_error, 0.0, places=12)

    def test_state_above_capacity_is_rejected_and_calibration_is_auditable(self):
        state = self.system.initial_state()
        result = self.system.step(state, {})
        self.assertEqual(result.calibration_version, "test-v1")
        invalid = MetabolicState((
            ("core", 1.01), ("motor", 0.55), ("sensor", 0.55),
        ))
        with self.assertRaises(MetabolismError):
            self.system.step(invalid, {})

    def test_invalid_measurements_and_unknown_organs_rejected(self):
        state = self.system.initial_state()
        with self.assertRaises(MetabolismError):
            self.system.step(state, {"unknown": WorkMeasurement(operations=1)})
        with self.assertRaises(MetabolismError):
            WorkMeasurement(operations=-1)

    def test_deterministic_replay(self):
        state = self.system.initial_state({"core": 0.9, "motor": 0.3, "sensor": 0.4})
        measurements = {"motor": WorkMeasurement(operations=4)}
        first = self.system.step(state, measurements)
        second = self.system.step(state, measurements)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
