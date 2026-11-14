import unittest

from chimera.tecq.experiments import run_swarm_ablation


class TECQExperimentTests(unittest.TestCase):
    def test_same_seed_repeats_same_simulation(self):
        a = run_swarm_ablation(cell_count=32, steps=12, pulse_ticks=3, damage_tick=4, seed=7)
        b = run_swarm_ablation(cell_count=32, steps=12, pulse_ticks=3, damage_tick=4, seed=7)
        self.assertEqual(
            [x["condition"] for x in a["results"]],
            ["independent", "fixed", "adaptive", "full"],
        )
        self.assertEqual(
            [x["state_digest"] for x in a["results"]],
            [x["state_digest"] for x in b["results"]],
        )
        self.assertTrue(a["protocol"]["same_initial_state_across_conditions"])
        self.assertTrue(a["protocol"]["same_tick_budget"])
        self.assertFalse(a["protocol"]["equal_hardware_compute_budget"])
        self.assertTrue(all(x["cells"] == 32 for x in a["results"]))

    def test_different_seeds_change_the_trial(self):
        a = run_swarm_ablation(cell_count=32, steps=12, pulse_ticks=3, damage_tick=4, seed=7)
        b = run_swarm_ablation(cell_count=32, steps=12, pulse_ticks=3, damage_tick=4, seed=8)
        self.assertNotEqual(
            [x["state_digest"] for x in a["results"]],
            [x["state_digest"] for x in b["results"]],
        )
        self.assertNotEqual(
            a["protocol"]["damaged_cell_ids"],
            b["protocol"]["damaged_cell_ids"],
        )

    def test_disconnected_independent_cells_cannot_claim_structural_recovery(self):
        result = run_swarm_ablation(
            cell_count=32, steps=12, pulse_ticks=3, damage_tick=4, seed=7
        )
        independent = result["results"][0]
        self.assertEqual(independent["initial_bonds"], 0)
        self.assertEqual(independent["structural_recovery_fraction"], 0.0)
        self.assertIsNone(independent["recovery_tick"])


if __name__ == "__main__":
    unittest.main()
