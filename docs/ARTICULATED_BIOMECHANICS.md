# Articulated biomechanics — implementation contract

**Implementation:** `chimera/biomechanics.py`  
**State owner:** `ISCEOrganismState` in `chimera/isce.py`  
**Persistence owner:** `RealityEngine`'s existing transactional organism-state row  
**Model version:** `human-sagittal-1`  
**Units:** metres, kilograms, seconds, radians, newtons, newton-metres

## 1. What is now executable

This implementation replaces the former statement that the organism had physiology without articulated mechanics. It provides a deterministic, versioned human segment tree; joint coordinates; forward kinematics; bounded PD muscle actuators; gravity loading; semi-implicit joint integration; joint-limit impacts; root translation; unilateral foot/ground contact; effort/work accounting; and proprioceptive error.

The canonical tree contains 16 segments and 15 actuated hinge coordinates:

- axial: pelvis, spine, neck, head
- left arm: upper arm, forearm, hand
- right arm: upper arm, forearm, hand
- left leg: thigh, shin, foot
- right leg: thigh, shin, foot

Every non-root segment has exactly one parent. The skeleton validator rejects duplicate names, missing parents, non-parent-first order, and multiple roots. The runtime rejects missing/duplicate joint coordinates, incompatible skeleton versions, unknown actuator names, non-finite commands and out-of-range initial joint angles.

The segment mass and length values are an explicit approximate human-sized parameterization, not an anthropometric claim about a particular person. They are versioned with the skeleton and must be calibrated against measured motion data before any clinical, biomechanical or high-fidelity human claim.

## 2. State ownership and persistence

Articulation is a nested immutable value inside the existing ISCE organism state:

- joint angle, angular velocity and muscle activation per joint
- root linear velocity
- active ground-contact feet
- current mechanical strain and proprioceptive error
- accumulated mechanical work

No second organism object, database table, renderer-owned pose or parallel physiology state is introduced. `OrganismState.to_dict()` serializes articulation with the other intrinsic partitions; the existing RealityEngine organism-state transaction commits it atomically with world-field projections and the event hash.

The schema version remains 1 because this is an additive, defaulted field. Existing schema-v1 payloads without articulation load with the canonical neutral skeleton. New payloads persist the complete articulation. A future incompatible skeleton or state change must use an explicit migration/version rather than silently reinterpreting joint order.

## 3. Actuator and joint dynamics

Motor commands are pairs `(joint_name, target_angle_radians)`. Each joint is a bounded hinge with a torque limit, proportional gain and derivative damping.

For a joint coordinate (q), target (q^*), angular velocity (dot q), and motor readiness (r):

[
\tau_{motor}=\operatorname{clamp}(K_p r(q^*-q)-K_d\dot q,-\tau_{max},\tau_{max})
]

The solver estimates distal subtree mass and effective hinge inertia, applies a gravity load based on the accumulated sagittal angle, and integrates with semi-implicit Euler at internal steps no larger than 20 ms:

[
\ddot q = \frac{\tau_{motor}+\tau_{gravity}}{I_{effective}}
]

[
\dot q_{n+1}=(\dot q_n+\ddot q\,h)e^{-0.08h},\qquad
q_{n+1}=\operatorname{clamp}(q_n+\dot q_{n+1}h,q_{min},q_{max})
]

Crossing a joint limit clamps the coordinate, removes outward velocity and contributes to mechanical strain. Motor effort and positive mechanical work are accumulated and returned to ISCE as simulated work units and metabolic cost. These are model quantities, not measured hardware energy or calibrated biological calories.

## 4. Root motion and ground contact

The root receives explicit world-frame acceleration and gravity. Root velocity is integrated semi-implicitly and bounded to 12 m/s per axis. Feet are evaluated from the same forward-kinematic pose used for contact; a unilateral ground plane corrects foot penetration, cancels downward root velocity while supported and applies horizontal damping while feet are in contact.

This is a deterministic ground-contact model for a single articulated organism. It is not yet a general-purpose rigid-body constraint solver: it does not implement self-collision, foot friction cones, contact manifolds, momentum-conserving impact impulses, uneven terrain, or full coupled articulated-body equations.

## 5. ISCE coupling

Every `ISCEKernel.transition` now advances mechanics before physiology:

1. Validate the current canonical articulation.
2. Integrate muscle/joint dynamics and root motion.
3. Derive mechanical strain, proprioceptive error, metabolic cost and work.
4. Feed derived strain into energy, stress, fatigue, damage and pain transitions.
5. Feed proprioceptive error into the sensorimotor partition.
6. Feed mechanical cost/work into body energy and resource reserve.
7. Commit the resulting root position and articulated state in the same next ISCE value.

A failed RealityEngine optimistic commit still cannot publish the speculative next state because the existing OrganismKernel only updates its in-memory state after the durable world transaction succeeds.

## 6. Public solver surface

- `SkeletonDefinition.human()`: immutable canonical topology and segment parameters.
- `ArticulatedBodyState.neutral()`: complete neutral joint state.
- `BiomechanicsEngine.forward_kinematics(position, state)`: world-space segment poses.
- `BiomechanicsEngine.step(state, position, dt, motor_commands, root_acceleration, motor_readiness, body_energy)`: deterministic mechanics transition and derived sensor/metabolic outputs.
- `TransitionInput.motor_commands`: typed target joint coordinates.
- `TransitionInput.root_acceleration`: typed external root acceleration.
- `OrganismState.articulation`: authoritative intrinsic articulation.

## 7. Required regression coverage

`tests/test_biomechanics.py` covers tree validity, connected forward kinematics, motor response/work, hard joint limits, gravity/ground contact, root translation, state round-trip, invalid commands/state rejection, old-state neutral migration, and coupling of mechanical work/proprioception into ISCE physiology.

The existing organism-kernel persistence/restart tests also exercise the expanded ISCE payload through the same SQLite state row and event-chain contract.

## 8. Explicit remaining work

This closes the first executable articulated-body gate, not all embodiment. Remaining engineering work includes:

- multi-axis 3D joints and quaternion rigid-segment transforms
- coupled articulated-body dynamics (mass matrix, Coriolis/centrifugal terms and constraint impulses)
- self-collision, terrain collision, friction cones and grasp/contact mechanics
- antagonistic muscle pairs, tendon compliance, force-length/force-velocity curves, fatigue and recovery at muscle level
- sensor observations from actual segment/contact geometry and camera/audio/touch modalities
- a single governed action gateway that translates planner intent into validated motor targets
- a renderer adapter that projects the authoritative articulated pose without inventing display-only motion
- calibration against reference motion capture and quantitative gait/pose benchmarks

Do not describe this model as a complete human simulator, anatomically accurate digital twin, medical model, or evidence of sentience. It is a real deterministic articulated mechanics subsystem integrated into ISCE with clearly stated approximations and testable contracts.
