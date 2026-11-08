"""Deterministic articulated-body mechanics for the ISCE organism.

The canonical skeleton is a fixed, versioned kinematic tree. Joint state is
intrinsic organism state; this module is a pure transition solver and owns no
persistence, wall clock, renderer state, or second organism identity.

The solver uses semi-implicit Euler integration of bounded hinge coordinates,
PD muscle actuators, subtree effective inertia, gravity loading, joint-limit
impacts, and unilateral foot/ground contact. It is intentionally a compact
single-body rigid-segment model, not a claim of deformable tissue or a
general-purpose multibody constraint solver.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Optional, Sequence, Tuple


SKELETON_VERSION = "human-3d-1"
GRAVITY = 9.81


class BiomechanicsError(ValueError):
    """Invalid skeleton, articulation state, or motor command."""


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise BiomechanicsError(f"{name} must be finite")
    return value


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _vec3(name: str, value: Iterable[float]) -> tuple[float, float, float]:
    try:
        result = tuple(_finite(name, v) for v in value)
    except (TypeError, ValueError) as exc:
        raise BiomechanicsError(f"{name} must contain three finite values") from exc
    if len(result) != 3:
        raise BiomechanicsError(f"{name} must contain exactly three values")
    return result  # type: ignore[return-value]


@dataclass(frozen=True)
class SegmentSpec:
    name: str
    parent: Optional[str]
    offset: tuple[float, float, float]
    direction: tuple[float, float, float]
    length: float
    mass: float
    radius: float
    min_angle: float
    max_angle: float
    torque_limit: float
    kp: float
    kd: float
    axis: tuple[float, float, float] = (1.0, 0.0, 0.0)
    dof_mask: tuple[bool, bool, bool] = (True, False, False)
    min_rotation_xyz: Optional[tuple[float, float, float]] = None
    max_rotation_xyz: Optional[tuple[float, float, float]] = None
    tendon_stiffness: float = 1200.0
    tendon_damping: float = 18.0
    activation_tau: float = 0.045

    def __post_init__(self) -> None:
        if not self.name:
            raise BiomechanicsError("Segment names cannot be empty")
        object.__setattr__(self, "offset", _vec3("segment offset", self.offset))
        object.__setattr__(self, "direction", _vec3("segment direction", self.direction))
        object.__setattr__(self, "axis", _vec3("joint axis", self.axis))
        for key in ("length", "mass", "radius", "torque_limit", "kp", "kd"):
            value = _finite(key, getattr(self, key))
            if value <= 0:
                raise BiomechanicsError(f"{key} must be positive")
        if not self.min_angle < self.max_angle:
            raise BiomechanicsError("Joint lower limit must be below upper limit")
        norm = math.sqrt(sum(v*v for v in self.direction))
        axis_norm = math.sqrt(sum(v*v for v in self.axis))
        if abs(norm - 1.0) > 1e-5 or abs(axis_norm - 1.0) > 1e-5:
            raise BiomechanicsError("Segment direction and joint axis must be unit vectors")


@dataclass(frozen=True)
class SkeletonDefinition:
    version: str
    segments: tuple[SegmentSpec, ...]

    def __post_init__(self) -> None:
        names = [segment.name for segment in self.segments]
        if not names or len(names) != len(set(names)):
            raise BiomechanicsError("Skeleton segment names must be non-empty and unique")
        known = set(names)
        roots = [segment for segment in self.segments if segment.parent is None]
        if len(roots) != 1:
            raise BiomechanicsError("Skeleton must have exactly one root segment")
        for segment in self.segments:
            if segment.parent is not None and segment.parent not in known:
                raise BiomechanicsError(f"Unknown parent segment: {segment.parent}")
        seen: set[str] = set()
        for segment in self.segments:
            if segment.parent is not None and segment.parent not in seen:
                raise BiomechanicsError("Segments must be ordered parent before child")
            seen.add(segment.name)

    @classmethod
    def human(cls) -> "SkeletonDefinition":
        # Segment lengths are in metres; masses are approximate kg distributions.
        # Joint coordinates are sagittal-plane hinge coordinates in radians.
        return cls(SKELETON_VERSION, (
            SegmentSpec("pelvis", None, (0,0,0), (0,-1,0), .18, 8.0, .12,
                        0.0, 0.0 + 1e-6, 1.0, 1.0, 1.0),
            SegmentSpec("spine", "pelvis", (0,.04,0), (0,1,0), .48, 18.0, .16,
                        -.55, .55, 180.0, 420.0, 42.0),
            SegmentSpec("neck", "spine", (0,.48,0), (0,1,0), .12, 1.5, .07,
                        -.65, .65, 35.0, 80.0, 8.0),
            SegmentSpec("head", "neck", (0,.12,0), (0,1,0), .25, 5.0, .12,
                        -.75, .75, 45.0, 90.0, 9.0),
            SegmentSpec("upper_arm_l", "spine", (-.19,.39,0), (0,-1,0), .31, 2.5, .065,
                        -2.7, 2.7, 65.0, 120.0, 12.0),
            SegmentSpec("forearm_l", "upper_arm_l", (0,-.31,0), (0,-1,0), .27, 1.5, .052,
                        -2.35, .12, 38.0, 90.0, 9.0),
            SegmentSpec("hand_l", "forearm_l", (0,-.27,0), (0,-1,0), .10, .5, .04,
                        -.85, .85, 12.0, 30.0, 3.0),
            SegmentSpec("upper_arm_r", "spine", (.19,.39,0), (0,-1,0), .31, 2.5, .065,
                        -2.7, 2.7, 65.0, 120.0, 12.0),
            SegmentSpec("forearm_r", "upper_arm_r", (0,-.31,0), (0,-1,0), .27, 1.5, .052,
                        -2.35, .12, 38.0, 90.0, 9.0),
            SegmentSpec("hand_r", "forearm_r", (0,-.27,0), (0,-1,0), .10, .5, .04,
                        -.85, .85, 12.0, 30.0, 3.0),
            SegmentSpec("thigh_l", "pelvis", (-.10,-.08,0), (0,-1,0), .42, 7.0, .10,
                        -.95, 1.65, 180.0, 360.0, 38.0),
            SegmentSpec("shin_l", "thigh_l", (0,-.42,0), (0,-1,0), .42, 4.0, .075,
                        -2.45, .12, 120.0, 280.0, 28.0),
            SegmentSpec("foot_l", "shin_l", (0,-.42,0), (0,0,1), .20, 1.2, .065,
                        -.65, .65, 32.0, 90.0, 9.0),
            SegmentSpec("thigh_r", "pelvis", (.10,-.08,0), (0,-1,0), .42, 7.0, .10,
                        -.95, 1.65, 180.0, 360.0, 38.0),
            SegmentSpec("shin_r", "thigh_r", (0,-.42,0), (0,-1,0), .42, 4.0, .075,
                        -2.45, .12, 120.0, 280.0, 28.0),
            SegmentSpec("foot_r", "shin_r", (0,-.42,0), (0,0,1), .20, 1.2, .065,
                        -.65, .65, 32.0, 90.0, 9.0),
        ))

    def by_name(self) -> dict[str, SegmentSpec]:
        return {segment.name: segment for segment in self.segments}


@dataclass(frozen=True)
class JointCoordinate:
    name: str
    angle: float = 0.0
    velocity: float = 0.0
    activation: float = 0.0

    def __post_init__(self) -> None:
        if not self.name:
            raise BiomechanicsError("Joint coordinate name cannot be empty")
        for key in ("angle", "velocity", "activation"):
            _finite(key, getattr(self, key))
        if not 0.0 <= self.activation <= 1.0:
            raise BiomechanicsError("Muscle activation must be in [0, 1]")


@dataclass(frozen=True)
class ArticulatedBodyState:
    skeleton_version: str = SKELETON_VERSION
    joints: tuple[JointCoordinate, ...] = ()
    root_velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    contacts: tuple[str, ...] = ()
    mechanical_strain: float = 0.0
    proprioceptive_error: float = 0.0
    metabolic_work: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "joints", tuple(self.joints))
        object.__setattr__(self, "root_velocity", _vec3("root_velocity", self.root_velocity))
        object.__setattr__(self, "contacts", tuple(self.contacts))
        names = [joint.name for joint in self.joints]
        if len(names) != len(set(names)):
            raise BiomechanicsError("Joint coordinates must be unique")
        for key in ("mechanical_strain", "proprioceptive_error"):
            value = _finite(key, getattr(self, key))
            if not 0.0 <= value <= 1.0:
                raise BiomechanicsError(f"{key} must be in [0, 1]")
        if _finite("metabolic_work", self.metabolic_work) < 0:
            raise BiomechanicsError("metabolic_work cannot be negative")

    @classmethod
    def neutral(cls, skeleton: Optional[SkeletonDefinition] = None) -> "ArticulatedBodyState":
        definition = skeleton or SkeletonDefinition.human()
        joints = tuple(
            JointCoordinate(segment.name)
            for segment in definition.segments if segment.parent is not None
        )
        return cls(joints=joints)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ArticulatedBodyState":
        if not payload:
            return cls.neutral()
        joints = tuple(
            JointCoordinate(**dict(item)) for item in payload.get("joints", ())  # type: ignore[arg-type]
        )
        return cls(
            skeleton_version=str(payload.get("skeleton_version", SKELETON_VERSION)),
            joints=joints,
            root_velocity=tuple(payload.get("root_velocity", (0.0,0.0,0.0))),  # type: ignore[arg-type]
            contacts=tuple(payload.get("contacts", ())),  # type: ignore[arg-type]
            mechanical_strain=float(payload.get("mechanical_strain", 0.0)),
            proprioceptive_error=float(payload.get("proprioceptive_error", 0.0)),
            metabolic_work=float(payload.get("metabolic_work", 0.0)),
        )


def initial_articulated_body_state() -> ArticulatedBodyState:
    return ArticulatedBodyState.neutral()


@dataclass(frozen=True)
class SegmentPose:
    name: str
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    center: tuple[float, float, float]
    direction: tuple[float, float, float]
    radius: float


@dataclass(frozen=True)
class BiomechanicsResult:
    state: ArticulatedBodyState
    position: tuple[float, float, float]
    poses: tuple[SegmentPose, ...]
    mechanical_strain: float
    proprioceptive_error: float
    metabolic_cost: float
    work_units: float
    contacts: tuple[str, ...]


def _rotation_x(angle: float, vector: tuple[float, float, float]) -> tuple[float,float,float]:
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = vector
    return (x, c*y - s*z, s*y + c*z)


def _add(a: tuple[float,float,float], b: tuple[float,float,float]) -> tuple[float,float,float]:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def _scale(v: tuple[float,float,float], amount: float) -> tuple[float,float,float]:
    return (v[0]*amount, v[1]*amount, v[2]*amount)


class BiomechanicsEngine:
    """Pure articulated-body transition solver with deterministic contacts."""

    def __init__(self, skeleton: Optional[SkeletonDefinition] = None,
                 *, ground_height: float = 0.0, contact_stiffness: float = 900.0,
                 contact_damping: float = 65.0):
        self.skeleton = skeleton or SkeletonDefinition.human()
        self.ground_height = _finite("ground_height", ground_height)
        self.contact_stiffness = _finite("contact_stiffness", contact_stiffness)
        self.contact_damping = _finite("contact_damping", contact_damping)
        if min(self.contact_stiffness, self.contact_damping) <= 0:
            raise BiomechanicsError("Contact stiffness and damping must be positive")
        self._specs = self.skeleton.by_name()
        self._children: dict[str, list[str]] = {name: [] for name in self._specs}
        for segment in self.skeleton.segments:
            if segment.parent:
                self._children[segment.parent].append(segment.name)
        self._subtree_mass: dict[str, float] = {}
        for segment in reversed(self.skeleton.segments):
            self._subtree_mass[segment.name] = segment.mass + sum(
                self._subtree_mass[child] for child in self._children[segment.name]
            )

    def _validate_state(self, state: ArticulatedBodyState) -> dict[str, JointCoordinate]:
        if state.skeleton_version != self.skeleton.version:
            raise BiomechanicsError(
                f"State skeleton {state.skeleton_version} does not match {self.skeleton.version}"
            )
        expected = {s.name for s in self.skeleton.segments if s.parent is not None}
        coordinates = {joint.name: joint for joint in state.joints}
        if set(coordinates) != expected:
            raise BiomechanicsError("Articulation state must contain every canonical joint exactly once")
        for name, coordinate in coordinates.items():
            spec = self._specs[name]
            if coordinate.angle < spec.min_angle - 1e-6 or coordinate.angle > spec.max_angle + 1e-6:
                raise BiomechanicsError(f"Joint {name} is outside its anatomical range")
        return coordinates

    def forward_kinematics(self, position: Iterable[float],
                           state: ArticulatedBodyState) -> tuple[SegmentPose, ...]:
        root = _vec3("root position", position)
        coordinates = self._validate_state(state)
        transforms: dict[str, tuple[tuple[float,float,float], float]] = {}
        poses: list[SegmentPose] = []
        for spec in self.skeleton.segments:
            if spec.parent is None:
                origin, parent_angle = root, 0.0
                angle = 0.0
            else:
                parent_origin, parent_angle = transforms[spec.parent]
                origin = _add(parent_origin, _rotation_x(parent_angle, spec.offset))
                angle = parent_angle + coordinates[spec.name].angle
            end = _add(origin, _rotation_x(angle, _scale(spec.direction, spec.length)))
            center = _add(origin, _scale(_add(end, _scale(origin, -1.0)), .5))
            direction = _scale(_add(end, _scale(origin, -1.0)), 1.0/spec.length)
            transforms[spec.name] = (origin, angle)
            poses.append(SegmentPose(spec.name, origin, end, center, direction, spec.radius))
        return tuple(poses)

    def step(self, state: ArticulatedBodyState, position: Iterable[float], *,
             dt: float, motor_commands: Sequence[tuple[str, float]] = (),
             root_acceleration: Iterable[float] = (0.0, 0.0, 0.0),
             motor_readiness: float = 1.0, body_energy: float = 1.0) -> BiomechanicsResult:
        """Advance arbitrary ISCE time steps using stable <=20ms substeps."""
        dt = _finite("dt", dt)
        if not 0.0 < dt <= 10.0:
            raise BiomechanicsError("Biomechanics dt must be in (0, 10] seconds")
        count = max(1, math.ceil(dt / 0.02))
        sub_dt = dt / count
        current_state = state
        current_position = _vec3("root position", position)
        total_cost = 0.0
        total_work = 0.0
        result: Optional[BiomechanicsResult] = None
        for _ in range(count):
            result = self._step_once(
                current_state, current_position, dt=sub_dt,
                motor_commands=motor_commands,
                root_acceleration=root_acceleration,
                motor_readiness=motor_readiness, body_energy=body_energy,
            )
            current_state = result.state
            current_position = result.position
            total_cost += result.metabolic_cost
            total_work += result.work_units
        assert result is not None
        return BiomechanicsResult(
            state=result.state, position=result.position, poses=result.poses,
            mechanical_strain=result.mechanical_strain,
            proprioceptive_error=result.proprioceptive_error,
            metabolic_cost=total_cost, work_units=total_work,
            contacts=result.contacts,
        )

    def _step_once(self, state: ArticulatedBodyState, position: Iterable[float], *,
             dt: float, motor_commands: Sequence[tuple[str, float]] = (),
             root_acceleration: Iterable[float] = (0.0, 0.0, 0.0),
             motor_readiness: float = 1.0, body_energy: float = 1.0) -> BiomechanicsResult:
        dt = _finite("dt", dt)
        if not 0.0 < dt <= 0.02 + 1e-9:
            raise BiomechanicsError("Internal biomechanics substep exceeds 20ms")
        readiness = _clamp(_finite("motor_readiness", motor_readiness), 0.0, 1.0)
        energy = _clamp(_finite("body_energy", body_energy), 0.0, 1.0)
        root = list(_vec3("root position", position))
        acceleration = _vec3("root_acceleration", root_acceleration)
        coordinates = self._validate_state(state)
        commands: dict[str, float] = {}
        for name, target in motor_commands:
            if name in commands:
                raise BiomechanicsError(f"Duplicate motor command for {name}")
            if name not in self._specs or self._specs[name].parent is None:
                raise BiomechanicsError(f"Unknown or non-actuated joint: {name}")
            commands[name] = _finite(f"motor target {name}", target)

        updated: dict[str, JointCoordinate] = {}
        torque_by_joint: dict[str, float] = {}
        total_work = 0.0
        total_effort = 0.0
        limit_strain = 0.0
        for spec in self.skeleton.segments:
            if spec.parent is None:
                continue
            joint = coordinates[spec.name]
            target = _clamp(commands.get(spec.name, 0.0), spec.min_angle, spec.max_angle)
            # With no explicit target the joint is actively stabilized at neutral.
            error = target - joint.angle
            requested_torque = (spec.kp * readiness * error
                                - spec.kd * joint.velocity)
            torque = _clamp(requested_torque, -spec.torque_limit, spec.torque_limit)
            subtree_mass = self._subtree_mass[spec.name]
            lever = max(.04, spec.length * .52)
            inertia = max(.025, subtree_mass * spec.length * spec.length * .36)
            parent_angle = 0.0
            parent = spec.parent
            while parent is not None:
                if parent in coordinates:
                    parent_angle += coordinates[parent].angle
                parent = self._specs[parent].parent
            gravity_torque = -subtree_mass * GRAVITY * lever * math.sin(parent_angle + joint.angle)
            acceleration_q = (torque + gravity_torque) / inertia
            velocity = (joint.velocity + acceleration_q * dt) * math.exp(-.08 * dt)
            unconstrained = joint.angle + velocity * dt
            angle = _clamp(unconstrained, spec.min_angle, spec.max_angle)
            impact = abs(unconstrained-angle)
            if impact > 0.0:
                velocity = 0.0
                limit_strain += min(1.0, impact * 3.0)
            activation = _clamp(abs(torque) / spec.torque_limit, 0.0, 1.0)
            updated[spec.name] = JointCoordinate(spec.name, angle, velocity, activation)
            torque_by_joint[spec.name] = torque
            work = abs(torque * velocity) * dt
            total_work += work
            total_effort += activation * activation * dt

        next_state = ArticulatedBodyState(
            skeleton_version=self.skeleton.version,
            joints=tuple(updated[s.name] for s in self.skeleton.segments if s.parent is not None),
            root_velocity=state.root_velocity,
            contacts=state.contacts,
            mechanical_strain=state.mechanical_strain,
            proprioceptive_error=state.proprioceptive_error,
            metabolic_work=state.metabolic_work,
        )
        velocity = list(next_state.root_velocity)
        velocity[0] += acceleration[0] * dt
        velocity[1] += (acceleration[1] - GRAVITY) * dt
        velocity[2] += acceleration[2] * dt
        velocity = [_clamp(v, -12.0, 12.0) for v in velocity]
        root = [root[i] + velocity[i] * dt for i in range(3)]
        poses = self.forward_kinematics(root, next_state)
        by_name = {pose.name: pose for pose in poses}
        contact_names: list[str] = []
        penetration = 0.0
        for foot_name in ("foot_l", "foot_r"):
            foot = by_name[foot_name]
            bottom = foot.start[1] - foot.radius
            penetration = max(penetration, self.ground_height - bottom)
            if bottom <= self.ground_height + .012:
                contact_names.append(foot_name)
        contact_force = 0.0
        if penetration > 0.0:
            root[1] += penetration
            contact_force = penetration * self.contact_stiffness
        if contact_names and velocity[1] < 0.0:
            contact_force += -velocity[1] * self.contact_damping
            velocity[1] = 0.0
        if contact_names:
            velocity[0] *= math.exp(-2.5*dt)
            velocity[2] *= math.exp(-2.5*dt)
        corrected_position = tuple(root)
        corrected_state = ArticulatedBodyState(
            skeleton_version=self.skeleton.version,
            joints=next_state.joints,
            root_velocity=tuple(velocity),
            contacts=tuple(contact_names),
            mechanical_strain=_clamp(limit_strain + contact_force / 5000.0, 0.0, 1.0),
            proprioceptive_error=_clamp(
                sum(abs(commands.get(name, 0.0)-updated[name].angle)
                    for name in updated) / max(1, len(updated)) / 1.2,
                0.0, 1.0,
            ),
            metabolic_work=state.metabolic_work + total_work,
        )
        final_poses = self.forward_kinematics(corrected_position, corrected_state)
        metabolic_cost = (total_work * 0.000015 + total_effort * 0.00008)
        work_units = total_work + total_effort
        return BiomechanicsResult(
            corrected_state, corrected_position, final_poses,
            corrected_state.mechanical_strain,
            corrected_state.proprioceptive_error,
            metabolic_cost, work_units, corrected_state.contacts,
        )
