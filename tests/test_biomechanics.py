"""Acceptance tests for the ISCE-owned articulated body mechanics."""
import unittest

from chimera.biomechanics import (
    ArticulatedBodyState, BiomechanicsEngine, BiomechanicsError,
    SkeletonDefinition, SegmentSpec,
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

    def test_angular_speed_is_bounded_and_overrun_becomes_strain(self):
        from dataclasses import replace
        joints = tuple(
            replace(joint, velocity=25.0, angular_velocity_xyz=(25.0, 0.0, 0.0))
            if joint.name == "hand_l" else joint
            for joint in self.state.joints
        )
        fast_state = ArticulatedBodyState(joints=joints)
        result = self.engine.step(fast_state, (0, 1, 0), dt=0.02)
        joint = {item.name: item for item in result.state.joints}["hand_l"]
        limit = self.engine.skeleton.by_name()["hand_l"].angular_speed_limit
        self.assertLessEqual(max(abs(v) for v in joint.angular_velocity_xyz), limit + 1e-9)
        self.assertGreater(result.mechanical_strain, 0.0)

    def test_gravity_and_ground_contact_resolve_without_penetration(self):
        # Start with the feet intentionally intersecting the ground plane;
        # one fixed substep must resolve the contact without tunnelling.
        result = self.engine.step(self.state, (0, 0.5, 0), dt=0.02)
        self.assertTrue(set(result.contacts).issubset(
            {segment.name for segment in self.engine.skeleton.segments}
        ))
        lowest = min(
            min(pose.start[1], pose.end[1]) - pose.radius
            for pose in result.poses if pose.name in result.contacts
        )
        self.assertTrue(
            result.contacts,
            f"root={result.position}, lowest_capsule_bottom={lowest}, velocity={result.state.root_velocity}",
        )
        self.assertAlmostEqual(result.state.root_velocity[1], 0.0, places=6)
        poses = {pose.name: pose for pose in result.poses}
        for name in result.contacts:
            pose = poses[name]
            self.assertGreaterEqual(
                min(pose.start[1], pose.end[1]) - pose.radius,
                self.engine.ground_height - 1e-6,
            )

    def test_nonadjacent_capsules_receive_self_collision_impulses(self):
        skeleton = SkeletonDefinition("crossing-limbs-1", (
            SegmentSpec(
                "root", None, (0, 0, 0), (0, 1, 0), 0.1, 1.0, 0.05,
                0.0, 1e-6, 1.0, 1.0, 1.0,
            ),
            SegmentSpec(
                "arm_a", "root", (-0.15, 0, 0), (1, 0, 0), 0.3, 1.0, 0.08,
                -1.0, 1.0, 10.0, 20.0, 2.0,
                dof_mask=(False, True, False),
                min_rotation_xyz=(0.0, -1.0, 0.0),
                max_rotation_xyz=(0.0, 1.0, 0.0),
            ),
            SegmentSpec(
                "arm_b", "root", (0, -0.15, 0), (0, 1, 0), 0.3, 1.0, 0.08,
                -1.0, 1.0, 10.0, 20.0, 2.0,
                dof_mask=(True, False, False),
                min_rotation_xyz=(-1.0, 0.0, 0.0),
                max_rotation_xyz=(1.0, 0.0, 0.0),
            ),
        ))
        engine = BiomechanicsEngine(skeleton)
        state = ArticulatedBodyState.neutral(skeleton)
        initial = {pose.name: pose for pose in engine.forward_kinematics((0, 2, 0), state)}
        point_a, point_b = engine._closest_points_on_segments(
            initial["arm_a"].start, initial["arm_a"].end,
            initial["arm_b"].start, initial["arm_b"].end,
        )
        initial_gap = (
            sum((point_a[i] - point_b[i]) ** 2 for i in range(3)) ** 0.5
            - initial["arm_a"].radius - initial["arm_b"].radius
        )
        self.assertLess(initial_gap, 0.0)

        result = engine.step(state, (0, 2, 0), dt=0.02)
        final = {pose.name: pose for pose in result.poses}
        point_a, point_b = engine._closest_points_on_segments(
            final["arm_a"].start, final["arm_a"].end,
            final["arm_b"].start, final["arm_b"].end,
        )
        final_gap = (
            sum((point_a[i] - point_b[i]) ** 2 for i in range(3)) ** 0.5
            - final["arm_a"].radius - final["arm_b"].radius
        )
        self.assertGreater(final_gap, initial_gap)
        joints = {joint.name: joint for joint in result.state.joints}
        self.assertGreater(abs(joints["arm_b"].angular_velocity_xyz[0]), 0.0)

    def test_root_orientation_rotates_the_entire_kinematic_tree(self):
        import math
        orientation = (
            math.cos(math.pi / 4.0), 0.0, 0.0, math.sin(math.pi / 4.0)
        )
        rotated = ArticulatedBodyState(
            joints=self.state.joints, root_orientation=orientation
        )
        poses = {pose.name: pose for pose in self.engine.forward_kinematics((0, 1, 0), rotated)}
        self.assertLess(poses["head"].end[0], -0.5)
        self.assertAlmostEqual(
            sum(value * value for value in rotated.root_orientation), 1.0, places=7
        )

    def test_root_angular_degrees_are_in_the_generalized_mass_matrix(self):
        layout = self.engine._dof_layout()
        self.assertEqual(layout[:6], tuple(
            ("__root__", axis) for axis in range(6)
        ))
        mass, _ = self.engine._mass_matrix_and_gravity(
            (0, 1, 0), self.state, layout
        )
        for axis in range(3, 6):
            self.assertGreater(mass[axis][axis], 0.0)
        # A displaced centre of mass couples root rotation and translation.
        self.assertGreater(
            max(abs(mass[axis][other])
                for axis in range(3) for other in range(3, 6)),
            1e-5,
        )

    def test_root_angular_velocity_updates_quaternion_through_the_solver(self):
        import math
        moving = ArticulatedBodyState(
            joints=self.state.joints,
            root_angular_velocity=(0.0, 0.0, 1.0),
        )
        result = self.engine.step(moving, (0, 3, 0), dt=0.02)
        self.assertNotEqual(result.state.root_orientation, moving.root_orientation)
        self.assertAlmostEqual(
            sum(value * value for value in result.state.root_orientation),
            1.0, places=7,
        )
        self.assertTrue(all(math.isfinite(v) for v in result.state.root_angular_velocity))

    def test_root_angular_velocity_round_trips_through_state_serialization(self):
        state = ArticulatedBodyState(
            joints=self.state.joints,
            root_orientation=(0.9238795325, 0.0, 0.0, 0.3826834324),
            root_angular_velocity=(0.2, -0.3, 0.4),
        )
        restored = ArticulatedBodyState.from_dict(state.to_dict())
        self.assertEqual(restored, state)

    def test_root_translation_is_part_of_the_coupled_mass_matrix(self):
        layout = self.engine._dof_layout()
        self.assertEqual(layout[:3], (
            ("__root__", 0), ("__root__", 1), ("__root__", 2)
        ))
        mass, _ = self.engine._mass_matrix_and_gravity(
            (0, 1, 0), self.state, layout
        )
        total_mass = sum(segment.mass for segment in self.engine.skeleton.segments)
        for axis in range(3):
            self.assertAlmostEqual(mass[axis][axis], total_mass, places=5)
        # Translation and articulation share one kinetic-energy matrix; a
        # torso rotation therefore has a non-zero root-translation cross term.
        spine_x = layout.index(("spine", 0))
        root_z = layout.index(("__root__", 2))
        self.assertGreater(abs(mass[root_z][spine_x]), 1e-6)

    def test_ground_contact_solver_enforces_normal_and_coulomb_impulses(self):
        # Isolate the production contact solver with a known diagonal mass
        # matrix so the unilateral and friction-cone invariants are exact.
        mass = [
            [2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 2.0],
        ]
        velocity = [2.0, -2.0, 0.0]
        contact = {
            "name": "test_contact",
            "gap": -0.01,
            "jacobian": (
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ),
        }
        constrained, normal_impulse, friction_impulse = (
            self.engine._apply_contact_impulses(
                mass, velocity, [contact], dt=0.02
            )
        )
        self.assertGreater(normal_impulse, 0.0)
        self.assertGreater(friction_impulse, 0.0)
        self.assertAlmostEqual(constrained[1], 0.0, places=6)
        self.assertLess(abs(constrained[0]), 2.0)
        self.assertLessEqual(friction_impulse, 0.75 * normal_impulse + 1e-9)

    def test_separated_body_does_not_receive_ground_friction_impulse(self):
        moving = ArticulatedBodyState(
            joints=self.state.joints,
            root_velocity=(2.0, 0.0, 0.0),
        )
        result = self.engine.step(moving, (0, 4, 0), dt=0.02)
        self.assertFalse(result.contacts)
        self.assertAlmostEqual(result.state.root_velocity[0], 2.0, places=6)

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

    def test_quaternion_forward_kinematics_uses_three_axis_joint_orientation(self):
        from dataclasses import replace
        joints = tuple(
            replace(joint, rotation_xyz=(0.0, 0.0, 0.45))
            if joint.name == "thigh_l" else joint
            for joint in self.state.joints
        )
        rotated = ArticulatedBodyState(joints=joints)
        neutral_poses = {p.name: p for p in self.engine.forward_kinematics((0, 1, 0), self.state)}
        rotated_poses = {p.name: p for p in self.engine.forward_kinematics((0, 1, 0), rotated)}
        self.assertNotAlmostEqual(
            neutral_poses["thigh_l"].end[0], rotated_poses["thigh_l"].end[0], places=5
        )
        self.assertNotEqual(rotated_poses["thigh_l"].orientation, (1.0, 0.0, 0.0, 0.0))

    def test_three_axis_motor_targets_drive_hip_abduction_and_rotation(self):
        result = self.engine.step(
            self.state, (0, 1, 0), dt=0.2,
            motor_commands=(("thigh_l", (0.35, 0.42, -0.28)),),
        )
        joint = {item.name: item for item in result.state.joints}["thigh_l"]
        self.assertGreater(abs(joint.rotation_xyz[1]), 1e-4)
        self.assertGreater(abs(joint.rotation_xyz[2]), 1e-4)
        self.assertGreater(abs(joint.tendon_extension_xyz[1]), 0.0)
        self.assertGreater(joint.activation, 0.0)

    def test_three_axis_joint_limits_are_enforced_per_axis(self):
        result = self.engine.step(
            self.state, (0, 1, 0), dt=0.5,
            motor_commands=(("thigh_l", (0.0, 8.0, -8.0)),),
        )
        joint = {item.name: item for item in result.state.joints}["thigh_l"]
        spec = self.engine.skeleton.by_name()["thigh_l"]
        self.assertLessEqual(joint.rotation_xyz[1], spec.max_rotation_xyz[1])
        self.assertGreaterEqual(joint.rotation_xyz[2], spec.min_rotation_xyz[2])

    def test_sagittal_persisted_joint_state_migrates_without_losing_primary_axis(self):
        payload = self.state.to_dict()
        payload["skeleton_version"] = "human-sagittal-1"
        old_joints = []
        for joint in payload["joints"]:
            item = {"name": joint["name"], "angle": 0.0, "velocity": 0.0, "activation": 0.0}
            if item["name"] == "thigh_l":
                item.update(angle=0.23, velocity=-0.14)
            old_joints.append(item)
        payload["joints"] = old_joints
        restored = ArticulatedBodyState.from_dict(payload)
        hip = {joint.name: joint for joint in restored.joints}["thigh_l"]
        self.assertEqual(restored.skeleton_version, "human-3d-1")
        self.assertAlmostEqual(hip.rotation_xyz[0], 0.23)
        self.assertAlmostEqual(hip.angular_velocity_xyz[0], -0.14)
        self.assertEqual(hip.rotation_xyz[1:], (0.0, 0.0))

    def test_disabled_joint_axis_cannot_be_loaded_from_persisted_state(self):
        from dataclasses import replace
        joints = tuple(
            replace(joint, rotation_xyz=(0.0, 0.1, 0.0))
            if joint.name == "shin_l" else joint
            for joint in self.state.joints
        )
        invalid = ArticulatedBodyState(joints=joints)
        with self.assertRaises(BiomechanicsError):
            self.engine.forward_kinematics((0, 1, 0), invalid)

    def test_generalized_mass_matrix_is_symmetric_and_contains_joint_coupling(self):
        layout = self.engine._dof_layout()
        mass, gravity = self.engine._mass_matrix_and_gravity((0, 1, 0), self.state, layout)
        self.assertEqual(len(mass), len(layout))
        self.assertEqual(len(gravity), len(layout))
        for i in range(len(layout)):
            self.assertGreater(mass[i][i], 0.0)
            for j in range(len(layout)):
                self.assertAlmostEqual(mass[i][j], mass[j][i], places=7)
        spine_x = layout.index(("spine", 0))
        shoulder_x = layout.index(("upper_arm_l", 0))
        self.assertGreater(abs(mass[spine_x][shoulder_x]), 1e-5)

    def test_coriolis_bias_is_finite_and_velocity_dependent(self):
        from dataclasses import replace
        joints = tuple(
            replace(joint,
                    rotation_xyz=(0.12, 0.08, -0.05),
                    angular_velocity_xyz=(0.7, -0.35, 0.22))
            if joint.name in {"spine", "thigh_l", "upper_arm_l"} else joint
            for joint in self.state.joints
        )
        moving = ArticulatedBodyState(joints=joints)
        layout = self.engine._dof_layout()
        mass, _ = self.engine._mass_matrix_and_gravity((0, 1, 0), moving, layout)
        bias = self.engine._coriolis_vector((0, 1, 0), moving, layout, mass)
        self.assertEqual(len(bias), len(layout))
        self.assertTrue(all(__import__("math").isfinite(value) for value in bias))
        self.assertGreater(max(abs(value) for value in bias), 1e-8)

    def test_shoulder_motor_torque_couples_into_spinal_dynamics(self):
        result = self.engine.step(
            self.state, (0, 1, 0), dt=0.12,
            motor_commands=(("upper_arm_l", (0.5, 0.2, 0.0)),),
        )
        joints = {joint.name: joint for joint in result.state.joints}
        self.assertNotAlmostEqual(joints["upper_arm_l"].angle, 0.0, places=7)
        self.assertNotAlmostEqual(joints["spine"].angle, 0.0, places=7)

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
