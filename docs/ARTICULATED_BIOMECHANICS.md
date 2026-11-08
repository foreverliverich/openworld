# Articulated biomechanics — implementation contract

**Implementation:** `chimera/biomechanics.py`  
**State owner:** `ISCEOrganismState` in `chimera/isce.py`  
**Persistence owner:** `RealityEngine`'s existing transactional organism-state row  
**Model version:** `human-3d-1` (migrates `human-sagittal-1` state)  
**Units:** metres, kilograms, seconds, radians, newtons, newton-metres

## 1. What is now executable

This implementation provides a deterministic, versioned human segment tree; scalar hinge and multi-axis joint coordinates; quaternion-composed 3D forward kinematics; bounded PD muscle excitation; activation dynamics; a compliant series-elastic tendon stage; force-length/force-velocity capacity scaling; gravity torque from world-space lever arms; semi-implicit joint integration; per-axis limits; root translation; unilateral foot/ground contact; effort/work accounting; and proprioceptive error.

The canonical tree contains 16 rigid segments and 15 actuated joints. Spine, neck, shoulders and hips are three-axis; wrists and ankles are two-axis; knees and elbows are single-axis hinges. Local XYZ Euler components are composed into normalized quaternions for forward kinematics:

- axial: pelvis, spine, neck, head
- left arm: upper arm, forearm, hand
- right arm: upper arm, forearm, hand
- left leg: thigh, shin, foot
- right leg: thigh, shin, foot

Every non-root segment has exactly one parent. The skeleton validator rejects duplicate names, missing parents, non-parent-first order, and multiple roots. The runtime rejects missing/duplicate joint coordinates, incompatible skeleton versions, unknown actuator names, non-finite commands and out-of-range initial joint angles.

The segment mass and length values are an explicit approximate human-sized parameterization, not an anthropometric claim about a particular person. They are versioned with the skeleton and must be calibrated against measured motion data before any clinical, biomechanical or high-fidelity human claim.

## 2. State ownership and persistence

Articulation is a nested immutable value inside the existing ISCE organism state:

- local XYZ rotation and angular velocity per joint, with legacy X-axis angle/velocity aliases
- muscle activation plus per-axis tendon extension and tendon velocity
- root linear velocity
- active ground-contact feet
- current mechanical strain and proprioceptive error
- accumulated mechanical work

No second organism object, database table, renderer-owned pose or parallel physiology state is introduced. `OrganismState.to_dict()` serializes articulation with the other intrinsic partitions; the existing RealityEngine organism-state transaction commits it atomically with world-field projections and the event hash.

The organism schema version remains 1 because articulation is still an additive nested field. Existing schema-v1 payloads without articulation load with the neutral canonical body. Persisted `human-sagittal-1` articulation is explicitly migrated to `human-3d-1`: prior scalar angle and velocity are preserved on local X, Y/Z components and tendon state start at zero. Unknown skeleton versions are not silently rewritten. The skeleton version remains stored in the articulation payload.

## 3. Actuator and joint dynamics

A motor command may be a scalar (legacy X-axis target) or a three-element XYZ radians vector. Each enabled axis computes a bounded PD torque request:

\[
\tau_{request,i}=\operatorname{clamp}(K_p r(q_i^*-q_i)-K_d\dot q_i,-\tau_{max},\tau_{max})
\]

Activation follows a first-order response with the segment's activation time constant. Available torque is scaled by a Gaussian force-length factor around neutral, a bounded force-velocity factor, activation, and the square root of normalized body energy:

\[
\tau_{capacity}=\tau_{max}\,a\,f_l(q)\,f_v(\dot q)\sqrt{E}
\]

The compliant tendon stage uses a stable first-order series-elastic response: tendon extension relaxes toward the muscle-torque/stiffness target with a 25 ms time constant, and transmitted torque is the spring term plus tendon damping. The model then integrates each enabled rotational component with semi-implicit Euler at internal steps no larger than 20 ms.

The three local Euler components are currently integrated independently; their composed orientation is a quaternion. This is 3D kinematic articulation with per-axis approximate dynamics, not a fully coupled quaternion rigid-body integrator. Gravity loading is calculated from the distal subtree's approximate mass and a world-space lever arm: \(\mathbf r\times\mathbf F\) is transformed into the parent joint frame. Effective inertia remains a diagonal subtree approximation, not a full articulated mass matrix.

Per-axis limits clamp the coordinate, remove outward velocity and contribute to mechanical strain. Work and effort are returned to ISCE as simulated quantities, not measured hardware energy or calibrated biological calories.

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

- coupled articulated-body dynamics (full generalized mass matrix, Coriolis/centrifugal terms, recursive Newton–Euler or equivalent solver, and constraint impulses)
- self-collision, terrain collision, friction cones and grasp/contact mechanics
- antagonistic agonist/antagonist muscle pairs, pennation and physiological cross-sectional area, tendon slack/strain calibration, muscle-level fatigue and recovery
- sensor observations from actual segment/contact geometry and camera/audio/touch modalities
- a single governed action gateway that translates planner intent into validated motor targets
- higher-fidelity skin/soft-tissue deformation that binds the segmented Three.js projection to the Somatic Core SDF surface without inventing display-only motion
- calibration against reference motion capture and quantitative gait/pose benchmarks

Do not describe this model as a complete human simulator, anatomically accurate digital twin, medical model, or evidence of sentience. It is a real deterministic articulated mechanics subsystem integrated into ISCE with clearly stated approximations and testable contracts.

## 9. Runtime/API control

The solver is reachable through the existing single-process HTTP application; this is not a disconnected test-only function.

- `GET /api/body/pose` returns the current committed skeleton version, root transform/velocity, contact feet, all joint coordinates and all 16 world-space segment poses.
- `POST /api/body/actuate` accepts a required `expected_revision`, a `motor_commands` object mapping canonical joint names to scalar X-axis targets or three-element XYZ radians vectors, and optional `root_acceleration` as three world-frame components. It advances exactly one configured fixed timestep through the same OrganismKernel → ISCE → RealityEngine transaction.
- Unknown joints, non-finite values, malformed vectors and stale revisions are rejected before the next state is published. The response includes the committed body pose and canonical state snapshot.

Example request body:

```json
{
  "expected_revision": 12,
  "motor_commands": {
    "thigh_l": [0.55, 0.2, -0.1],
    "shin_l": -0.3
  },
  "root_acceleration": [0.6, 0.0, 0.0]
}
```

The caller must obtain the current revision from `GET /api/body/pose` or `GET /api/state` and send it unchanged. This is an explicit motor-target interface, not yet a high-level gait planner or an authorization/governance layer for autonomous actions.

The main browser world scene now calls the pose endpoint and projects the returned world-space segment quaternions and local segment axes as connected cylinder-and-joint geometry. The motor-control panel exposes hip flexion/abduction/axial rotation and shoulder flexion/abduction/axial rotation, plus scalar knee/elbow controls and optional horizontal root acceleration. The scene updates only from committed pose responses; it does not own a second physics state. This remains a rigid-segment projection, not a deforming skin mesh or the Somatic Core raymarched SDF renderer.
