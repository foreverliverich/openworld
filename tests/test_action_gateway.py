"""Tests for the physiology-governed world action gateway."""
import os
import tempfile
import unittest
from dataclasses import replace

from chimera.action_gateway import (
    ActionGatewayError, ActionProposal, OrganismActionGateway,
)
from chimera.autonomous_agent import AutonomousWorldAgent
from chimera.organism_kernel import OrganismKernel
from chimera.reality_engine import RealityEngine, RevisionConflict, WorldConfig
from chimera.toolbox import ChimeraToolbox


def one_part_blueprint():
    return {
        "name": "gateway_test",
        "parts": [{
            "kind": "foundation", "position": [0, 0.5, 0],
            "size": [1, 1, 1], "material": "stone", "mass": 5,
        }],
    }


class ActionGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = RealityEngine(WorldConfig(
            database=os.path.join(self.tmp.name, "gateway.sqlite3")
        ))
        self.organism = OrganismKernel(self.world, "gateway-organism")
        self.toolbox = ChimeraToolbox(self.world, actor_id=self.organism.organism_id)
        self.gateway = OrganismActionGateway(self.world, self.organism, self.toolbox)

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def proposal(self, **kwargs):
        values = {
            "tool": "world_builder",
            "action": "create_structure",
            "arguments": {"blueprint": one_part_blueprint()},
            "expected_revision": self.world.revision(),
            "expected_success": 0.8,
            "novelty": 0.4,
        }
        values.update(kwargs)
        return ActionProposal(**values)

    def test_successful_commit_is_charged_to_isce(self):
        before = self.organism.state.resources.reserve
        receipt = self.gateway.execute(self.proposal())
        self.assertEqual(receipt.logical_work_units, 1.0)
        self.assertEqual(receipt.action_revision, 1)
        self.assertEqual(receipt.organism_revision, 2)
        self.assertLess(self.organism.state.resources.reserve, before)
        self.assertEqual(self.organism.state.sensorimotor.last_action_success, 1.0)
        self.assertAlmostEqual(receipt.prediction_error, 0.2)
        self.assertEqual(len(self.world.entities()), 1)
        self.assertTrue(self.world.verify_event_chain())

    def test_stale_proposal_is_rejected_without_mutation(self):
        self.world.inject_field("memory", [0, 1, 0], 0.2, actor_id="test")
        before = self.organism.state.digest()
        with self.assertRaises(RevisionConflict):
            self.gateway.execute(self.proposal(expected_revision=0))
        self.assertEqual(len(self.world.entities()), 0)
        self.assertEqual(self.organism.state.digest(), before)

    def test_starvation_gate_rejects_before_world_commit(self):
        self.organism.state = replace(
            self.organism.state,
            resources=replace(self.organism.state.resources, reserve=0.051),
        )
        with self.assertRaises(ActionGatewayError):
            self.gateway.execute(self.proposal())
        self.assertEqual(self.world.revision(), 0)
        self.assertEqual(self.world.entities(), [])

    def test_unsupported_or_read_only_action_rejects(self):
        with self.assertRaises(ActionGatewayError):
            self.gateway.execute(self.proposal(tool="research_lab", action="observe"))
        self.assertEqual(self.world.revision(), 0)

    def test_invalid_blueprint_does_not_charge_or_commit(self):
        before = self.organism.state.digest()
        proposal = self.proposal(arguments={"blueprint": {"name": "empty", "parts": []}})
        with self.assertRaises(Exception):
            self.gateway.execute(proposal)
        self.assertEqual(self.world.revision(), 0)
        self.assertEqual(self.organism.state.digest(), before)

    def test_large_build_is_admitted_by_its_actual_part_count(self):
        blueprint = one_part_blueprint()
        blueprint["parts"] = [
            {**blueprint["parts"][0], "position": [index * 2.0, 0.5, 0]}
            for index in range(6)
        ]
        receipt = self.gateway.execute(self.proposal(arguments={"blueprint": blueprint}))
        self.assertEqual(receipt.logical_work_units, 6.0)
        self.assertEqual(receipt.result["details"]["part_count"], 6)


if __name__ == "__main__":
    unittest.main()
