import unittest
from chimera.tecq.experiments import run_swarm_ablation


class TECQExperimentTests(unittest.TestCase):
    def test_ablation_is_deterministic_except_for_wall_clock(self):
        a=run_swarm_ablation(cell_count=32,steps=12,pulse_ticks=3,damage_tick=4)
        b=run_swarm_ablation(cell_count=32,steps=12,pulse_ticks=3,damage_tick=4)
        self.assertEqual([x["condition"] for x in a["results"]],
                         ["independent","fixed","adaptive","full"])
        self.assertEqual([x["state_digest"] for x in a["results"]],
                         [x["state_digest"] for x in b["results"]])
        self.assertFalse(a["protocol"]["hardware_work_measured"])
        self.assertTrue(all(x["cells"]==32 for x in a["results"]))


if __name__=="__main__": unittest.main()
