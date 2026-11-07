"""Tests for self-generated construction goals and persistent world changes."""

import os
import tempfile
import unittest
from dataclasses import replace

from chimera.autonomous_agent import AutonomousWorldAgent
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, WorldConfig


class AutonomousAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "agent.sqlite3")
        self.world = RealityEngine(WorldConfig(database=self.path))
        self.organism = OrganismKernel(self.world, "autonomous-test")
        self.agent = AutonomousWorldAgent(self.world, self.organism)

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def test_agent_generates_and_executes_developmental_construction_goals(self):
        first = self.agent.step()
        self.assertEqual(first.goal, "create_shelter")
        self.assertEqual(first.action, "construct_structure")
        self.assertEqual(first.result["part_count"], 6)
        self.assertIn("first_shelter", {
            e.metadata.get("structure_name") for e in self.world.entities()
        })

        second = self.agent.step()
        self.assertEqual(second.goal, "create_workbench")
        self.assertEqual(second.result["part_count"], 5)

        third = self.agent.step()
        self.assertEqual(third.goal, "inspect_world_and_consolidate_memory")
        self.assertEqual(third.action, "observe_and_consolidate")
        self.assertGreater(self.organism.state.self_model.memory_strength, 0.0)
        self.assertTrue(self.world.verify_event_chain())

    def test_agent_recovers_when_energy_is_low(self):
        self.organism.state = replace(
            self.organism.state,
            body=replace(self.organism.state.body, energy=0.2),
        )
        step = self.agent.step()
        self.assertEqual(step.goal, "recover_and_regulate")
        self.assertGreater(self.organism.state.body.energy, 0.2)


if __name__ == "__main__":
    unittest.main()
