import unittest
from chimera.tecq.engine import TECQConfig, TECQEngine, TECQError, TECQState, lattice_state

class TECQEngineTests(unittest.TestCase):
    def test_coupled_state_domains_and_bounds(self):
        c=TECQConfig(cell_count=64,topology_interval=2); s=lattice_state(c); e=TECQEngine(s,c)
        before=s.digest(); r=e.step([0.0]*64)
        self.assertNotEqual(before,r["state_digest"]); self.assertEqual(r["cells"],64)
        for k in TECQState.DOMAINS: self.assertEqual(len(getattr(s,k)),64)
        for k in ("energy","stress","memory","cohesion","activation","swarm_intent","prediction_error"):
            self.assertTrue(all(0<=v<=1 for v in getattr(s,k)))
    def test_adaptive_topology_degree_is_bounded(self):
        c=TECQConfig(cell_count=125,topology_interval=1,topology_on=.4,topology_off=.1)
        s=lattice_state(c); e=TECQEngine(s,c)
        for _ in range(4): e.step([.1]*125)
        self.assertTrue(all(len(row)<=c.max_neighbors for row in s.adjacency))
    def test_checkpoint_round_trip(self):
        c=TECQConfig(cell_count=32); s=lattice_state(c); e=TECQEngine(s,c)
        for _ in range(3): e.step([.05]*32)
        restored=TECQState.from_checkpoint(s.checkpoint())
        self.assertEqual(restored.digest(),s.digest())
    def test_checkpoint_corruption_rejected(self):
        s=lattice_state(TECQConfig(cell_count=16)); p=s.checkpoint(); p["arrays"]["energy"][0]=.1
        with self.assertRaises(TECQError): TECQState.from_checkpoint(p)
    def test_bad_config_and_drive_rejected(self):
        with self.assertRaises(TECQError): TECQConfig(cell_count=1).validate()
        e=TECQEngine(lattice_state(TECQConfig(cell_count=8)))
        with self.assertRaises(TECQError): e.step([float("nan")]*8)
    def test_isce_projection_finite(self):
        c=TECQConfig(cell_count=27); e=TECQEngine(lattice_state(c),c); e.step()
        self.assertTrue(all(v>=0 for v in e.isce_projection().values()))

if __name__=="__main__": unittest.main()
