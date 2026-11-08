"""Acceptance tests for the ISCE-owned articulated body mechanics."""
import unittest

from chimera.biomechanics import (
    ArticulatedBodyState, BiomechanicsEngine, BiomechanicsError,
    SkeletonDefinition,
)
from chimera.isce import ISCEKernel, OrganismState, TransitionInput


class ArticulatedBodyTests(unittest.TestCase):
    def setUp(self):
        self.engine = BiomechanicsEngine()
        self.state = ArticulatedBodyState.neutral()

    def test_canonical_skeleton_has_complete_parent_ordered_tree(self):
        skeleton = SkeletonDefinition.human()
        self.assertEqual(len(skeleton.segments), 16)
        self.assertEqual(len(self.state.joints), 15)
        self.assertEqual(skeleton.segments[0].name, "pelvis")
        self.assertEqual(len({segment.name for segment in skeleton.segments}), 16)

    def test_forward_kinematics_produces_connected_segment_poses(self):
        poses = {pose.name: pose for pose in self.engine.forward_kinematics((0, 1, 0), self.state)}
        self.assertGreater(poses["head"].end[1], poses["pelvis"].start[1])
        self.assertAlmostEqual(poses["shin_l"].start[1], poses["thigh_l"].end[1], places=6)
        self.assertAlmostEqual(poses["forearm_r"].start[1], poses["upper_arm_r"].end[1], places=6)

    def test_motor_target_changes_joint_state_and_consumes_work(self):
        result = self.engine.step(
            self.state, (0, 1, 0), dt=0.1,
            motor_commands=(("thigh_l", 0.55),),
            motor_readiness=1.0, body_energy=0.9,
        )
        joint = {item.name: item for item in result.state.joints}["thigh_l"]
        self.assertGreater(joint.angle, 0.0)
        self.assertGreater(joint.activation, 0.0)
        self.assertGreater(result.metabolic_cost, 0.0)
        self.assertGreater(result.work_units, 0.0)
        self.assertGreaterEqual(result.proprioceptive_error, 0.0)

    def test_joint_limits_are_hard_constraints(self):
        result = self.engine.step(
            self.state, (0, 1, 0), dt=0.2,
            motor_commands=(("shin_l", -20.0),),
        )
        joint = {item.name: item for item in result.state.joints}["shin_l"]
        spec = self.engine.skeleton.by_name()["shin_l"]
        self.assertGreaterEqual(joint.angle, spec.min_angle)
        self.assertLessEqual(joint.angle, spec.max_angle)

    def test_gravity_and_ground_contact_resolve_without_penetration(self):
        result = self.engine.step(self.state, (0, 1, 0), dt=1.0)
        self.assertTrue(set(result.contacts).issubset({"foot_l", "foot_r"}))
        self.assertTrue(result.contacts)
        self.assertAlmostEqual(result.state.root_velocity[1], 0.0, places=6)
        poses = {pose.name: pose for pose in result.poses}
        for name in result.contacts:
            self.assertGreaterEqual(
                poses[name].start[1] - poses[name].radius,
                self.engine.ground_height - 1e-6,
            )

    def test_root_acceleration_integrates_world_translation(self):
        result = self.engine.step(
            self.state, (0, 4, 0), dt=0.2,
            root_acceleration=(2.0, 9.81, 0.0),
        )
        self.assertGreater(result.position[0], 0.0)
        self.assertAlmostEqual(result.position[1], 4.0, places=5)

    def test_state_round_trip_preserves_every_joint_and_contact(self):
        advanced = self.engine.step(self.state, (0, 1, 0), dt=0.2,
                                    motor_commands=(("upper_arm_l", 0.8),))
        restored = ArticulatedBodyState.from_dict(advanced.state.to_dict())
        self.assertEqual(restored, advanced.state)

    def test_unknown_commands_and_incomplete_states_are_rejected(self):
        with self.assertRaises(BiomechanicsError):
            self.engine.step(self.state, (0, 1, 0), dt=0.02,
                             motor_commands=(("tail", 0.2),))
        incomplete = ArticulatedBodyState(joints=self.state.joints[:-1])
        with self.assertRaises(BiomechanicsError):
            self.engine.forward_kinematics((0, 1, 0), incomplete)

    def test_isce_transition_couples_muscle_work_to_physiology_and_pose(self):
        organism = OrganismState("articulated-test")
        result = ISCEKernel().transition(
            organism,
            TransitionInput(dt=0.1, motor_commands=(("thigh_l", 0.45),)),
        )
        self.assertNotEqual(result.state.articulation, organism.articulation)
        self.assertGreater(result.state.resources.cumulative_work_units, 0.0)
        self.assertLess(result.state.body.energy, organism.body.energy)
        self.assertGreater(result.state.sensorimotor.proprioceptive_error, 0.0)
        restored = OrganismState.from_dict(result.state.to_dict())
        self.assertEqual(restored, result.state)

    def test_old_isce_payloads_migrate_to_neutral_articulation(self):
        old = OrganismState("old").to_dict()
        old.pop("articulation")
        restored = OrganismState.from_dict(old)
        self.assertEqual(restored.articulation, ArticulatedBodyState.neutral())


if __name__ == "__main__":
    unittest.main()
