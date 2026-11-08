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
        mask = tuple(bool(v) for v in self.dof_mask)
        if len(mask) != 3:
            raise BiomechanicsError("dof_mask must contain three axis flags")
        object.__setattr__(self, "dof_mask", mask)
        low = self.min_rotation_xyz or (self.min_angle, 0.0, 0.0)
        high = self.max_rotation_xyz or (self.max_angle, 0.0, 0.0)
        low, high = _vec3("minimum joint rotation", low), _vec3("maximum joint rotation", high)
        for axis_index, enabled in enumerate(mask):
            if low[axis_index] > high[axis_index]:
                raise BiomechanicsError("Joint rotation lower limit must not exceed upper limit")
            if not enabled and (abs(low[axis_index]) > 1e-9 or abs(high[axis_index]) > 1e-9):
                raise BiomechanicsError("Disabled joint axes must have zero limits")
        object.__setattr__(self, "min_rotation_xyz", low)
        object.__setattr__(self, "max_rotation_xyz", high)
        for key in ("length", "mass", "radius", "torque_limit", "kp", "kd",
                    "tendon_stiffness", "tendon_damping", "activation_tau"):
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
                        -.55, .55, 180.0, 420.0, 42.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-.55, -.32, -.32), max_rotation_xyz=(.55, .32, .32)),
            SegmentSpec("neck", "spine", (0,.48,0), (0,1,0), .12, 1.5, .07,
                        -.65, .65, 35.0, 80.0, 8.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-.65, -.45, -.45), max_rotation_xyz=(.65, .45, .45)),
            SegmentSpec("head", "neck", (0,.12,0), (0,1,0), .25, 5.0, .12,
                        -.75, .75, 45.0, 90.0, 9.0),
            SegmentSpec("upper_arm_l", "spine", (-.19,.39,0), (0,-1,0), .31, 2.5, .065,
                        -2.7, 2.7, 65.0, 120.0, 12.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-2.7, -1.9, -2.7), max_rotation_xyz=(2.7, 1.9, 2.7)),
            SegmentSpec("forearm_l", "upper_arm_l", (0,-.31,0), (0,-1,0), .27, 1.5, .052,
                        -2.35, .12, 38.0, 90.0, 9.0),
            SegmentSpec("hand_l", "forearm_l", (0,-.27,0), (0,-1,0), .10, .5, .04,
                        -.85, .85, 12.0, 30.0, 3.0,
                        dof_mask=(True, False, True),
                        min_rotation_xyz=(-.85, 0.0, -.55), max_rotation_xyz=(.85, 0.0, .55)),
            SegmentSpec("upper_arm_r", "spine", (.19,.39,0), (0,-1,0), .31, 2.5, .065,
                        -2.7, 2.7, 65.0, 120.0, 12.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-2.7, -1.9, -2.7), max_rotation_xyz=(2.7, 1.9, 2.7)),
            SegmentSpec("forearm_r", "upper_arm_r", (0,-.31,0), (0,-1,0), .27, 1.5, .052,
                        -2.35, .12, 38.0, 90.0, 9.0),
            SegmentSpec("hand_r", "forearm_r", (0,-.27,0), (0,-1,0), .10, .5, .04,
                        -.85, .85, 12.0, 30.0, 3.0,
                        dof_mask=(True, False, True),
                        min_rotation_xyz=(-.85, 0.0, -.55), max_rotation_xyz=(.85, 0.0, .55)),
            SegmentSpec("thigh_l", "pelvis", (-.10,-.08,0), (0,-1,0), .42, 7.0, .10,
                        -.95, 1.65, 180.0, 360.0, 38.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-.95, -.78, -.72), max_rotation_xyz=(1.65, .78, .72)),
            SegmentSpec("shin_l", "thigh_l", (0,-.42,0), (0,-1,0), .42, 4.0, .075,
                        -2.45, .12, 120.0, 280.0, 28.0),
            SegmentSpec("foot_l", "shin_l", (0,-.42,0), (0,0,1), .20, 1.2, .065,
                        -.65, .65, 32.0, 90.0, 9.0,
                        dof_mask=(True, False, True),
                        min_rotation_xyz=(-.65, 0.0, -.38), max_rotation_xyz=(.65, 0.0, .38)),
            SegmentSpec("thigh_r", "pelvis", (.10,-.08,0), (0,-1,0), .42, 7.0, .10,
                        -.95, 1.65, 180.0, 360.0, 38.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-.95, -.78, -.72), max_rotation_xyz=(1.65, .78, .72)),
            SegmentSpec("shin_r", "thigh_r", (0,-.42,0), (0,-1,0), .42, 4.0, .075,
                        -2.45, .12, 120.0, 280.0, 28.0),
            SegmentSpec("foot_r", "shin_r", (0,-.42,0), (0,0,1), .20, 1.2, .065,
                        -.65, .65, 32.0, 90.0, 9.0,
                        dof_mask=(True, False, True),
                        min_rotation_xyz=(-.65, 0.0, -.38), max_rotation_xyz=(.65, 0.0, .38)),
        ))

    def by_name(self) -> dict[str, SegmentSpec]:
        return {segment.name: segment for segment in self.segments}


@dataclass(frozen=True)
class JointCoordinate:
    name: str
    angle: float = 0.0
    velocity: float = 0.0
    activation: float = 0.0
    rotation_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    tendon_extension_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    tendon_velocity_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if not self.name:
            raise BiomechanicsError("Joint coordinate name cannot be empty")
        angle, velocity = _finite("angle", self.angle), _finite("velocity", self.velocity)
        rotation = _vec3("rotation_xyz", self.rotation_xyz)
        angular_velocity = _vec3("angular_velocity_xyz", self.angular_velocity_xyz)
        tendon_extension = _vec3("tendon_extension_xyz", self.tendon_extension_xyz)
        tendon_velocity = _vec3("tendon_velocity_xyz", self.tendon_velocity_xyz)
        if rotation == (0.0, 0.0, 0.0) and angle != 0.0:
            rotation = (angle, 0.0, 0.0)
        elif abs(rotation[0] - angle) > 1e-7:
            angle = rotation[0]
        if angular_velocity == (0.0, 0.0, 0.0) and velocity != 0.0:
            angular_velocity = (velocity, 0.0, 0.0)
        elif abs(angular_velocity[0] - velocity) > 1e-7:
            velocity = angular_velocity[0]
        object.__setattr__(self, "angle", angle)
        object.__setattr__(self, "velocity", velocity)
        object.__setattr__(self, "rotation_xyz", rotation)
        object.__setattr__(self, "angular_velocity_xyz", angular_velocity)
        object.__setattr__(self, "tendon_extension_xyz", tendon_extension)
        object.__setattr__(self, "tendon_velocity_xyz", tendon_velocity)
        activation = _finite("activation", self.activation)
        if not 0.0 <= activation <= 1.0:
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
        source_version = str(payload.get("skeleton_version", "human-sagittal-1"))
        joints = []
        for raw in payload.get("joints", ()):  # type: ignore[assignment]
            item = dict(raw)  # type: ignore[arg-type]
            if "rotation_xyz" not in item:
                item["rotation_xyz"] = (float(item.get("angle", 0.0)), 0.0, 0.0)
                item["angular_velocity_xyz"] = (float(item.get("velocity", 0.0)), 0.0, 0.0)
            joints.append(JointCoordinate(**item))
        return cls(
            skeleton_version=SKELETON_VERSION if source_version == "human-sagittal-1" else source_version,
            joints=tuple(joints),
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
    orientation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)


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


Quaternion = tuple[float, float, float, float]


def _q_mul(a: Quaternion, b: Quaternion) -> Quaternion:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw*bw - ax*bx - ay*by - az*bz,
        aw*bx + ax*bw + ay*bz - az*by,
        aw*by - ax*bz + ay*bw + az*bx,
        aw*bz + ax*by - ay*bx + az*bw,
    )


def _q_conjugate(q: Quaternion) -> Quaternion:
    return (q[0], -q[1], -q[2], -q[3])


def _q_normalize(q: Quaternion) -> Quaternion:
    norm = math.sqrt(sum(v*v for v in q))
    if norm < 1e-12:
        raise BiomechanicsError("Quaternion norm cannot be zero")
    return tuple(v / norm for v in q)  # type: ignore[return-value]


def _q_axis(axis: tuple[float, float, float], angle: float) -> Quaternion:
    half = angle * 0.5
    sine = math.sin(half)
    return (math.cos(half), axis[0]*sine, axis[1]*sine, axis[2]*sine)


def _q_from_euler_xyz(rotation: tuple[float, float, float]) -> Quaternion:
    qx = _q_axis((1.0, 0.0, 0.0), rotation[0])
    qy = _q_axis((0.0, 1.0, 0.0), rotation[1])
    qz = _q_axis((0.0, 0.0, 1.0), rotation[2])
    return _q_normalize(_q_mul(_q_mul(qx, qy), qz))


def _q_rotate(q: Quaternion, vector: tuple[float, float, float]) -> tuple[float, float, float]:
    pure = (0.0, vector[0], vector[1], vector[2])
    rotated = _q_mul(_q_mul(q, pure), _q_conjugate(q))
    return (rotated[1], rotated[2], rotated[3])


def _add(a: tuple[float,float,float], b: tuple[float,float,float]) -> tuple[float,float,float]:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def _sub(a: tuple[float,float,float], b: tuple[float,float,float]) -> tuple[float,float,float]:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _scale(v: tuple[float,float,float], amount: float) -> tuple[float,float,float]:
    return (v[0]*amount, v[1]*amount, v[2]*amount)


def _cross(a: tuple[float,float,float], b: tuple[float,float,float]) -> tuple[float,float,float]:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


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
            for axis_index, value in enumerate(coordinate.rotation_xyz):
                low = spec.min_rotation_xyz[axis_index]
                high = spec.max_rotation_xyz[axis_index]
                if value < low - 1e-6 or value > high + 1e-6:
                    raise BiomechanicsError(f"Joint {name} axis {axis_index} is outside its anatomical range")
                if not spec.dof_mask[axis_index] and abs(value) > 1e-7:
                    raise BiomechanicsError(f"Joint {name} uses a disabled rotational axis")
        return coordinates

    def _world_transforms(self, position: Iterable[float], state: ArticulatedBodyState):
        root = _vec3("root position", position)
        coordinates = self._validate_state(state)
        transforms: dict[str, tuple[tuple[float, float, float], Quaternion]] = {}
        poses: list[SegmentPose] = []
        for spec in self.skeleton.segments:
            if spec.parent is None:
                origin, parent_q = root, (1.0, 0.0, 0.0, 0.0)
                world_q = parent_q
            else:
                parent_origin, parent_q = transforms[spec.parent]
                origin = _add(parent_origin, _q_rotate(parent_q, spec.offset))
                local_q = _q_from_euler_xyz(coordinates[spec.name].rotation_xyz)
                world_q = _q_normalize(_q_mul(parent_q, local_q))
            end = _add(origin, _q_rotate(world_q, _scale(spec.direction, spec.length)))
            center = _add(origin, _scale(_sub(end, origin), .5))
            direction = _scale(_sub(end, origin), 1.0/spec.length)
            transforms[spec.name] = (origin, world_q)
            poses.append(SegmentPose(spec.name, origin, end, center, direction, spec.radius, world_q))
        return transforms, tuple(poses)

    def forward_kinematics(self, position: Iterable[float],
                           state: ArticulatedBodyState) -> tuple[SegmentPose, ...]:
        return self._world_transforms(position, state)[1]

    def step(self, state: ArticulatedBodyState, position: Iterable[float], *,
             dt: float, motor_commands: Sequence[tuple[str, object]] = (),
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
             dt: float, motor_commands: Sequence[tuple[str, object]] = (),
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
        commands: dict[str, tuple[float, float, float]] = {}
        for name, raw_target in motor_commands:
            if name in commands:
                raise BiomechanicsError(f"Duplicate motor command for {name}")
            if name not in self._specs or self._specs[name].parent is None:
                raise BiomechanicsError(f"Unknown or non-actuated joint: {name}")
            if isinstance(raw_target, (int, float)):
                target = (_finite(f"motor target {name}", raw_target), 0.0, 0.0)
            else:
                target = _vec3(f"motor target {name}", raw_target)  # type: ignore[arg-type]
            commands[name] = target

        current_transforms, _ = self._world_transforms(root, state)
        updated: dict[str, JointCoordinate] = {}
        total_work = 0.0
        total_effort = 0.0
        limit_strain = 0.0
        proprioceptive_sum = 0.0
        proprioceptive_axes = 0

        for spec in self.skeleton.segments:
            if spec.parent is None:
                continue
            joint = coordinates[spec.name]
            target = commands.get(spec.name, (0.0, 0.0, 0.0))
            rotation = list(joint.rotation_xyz)
            angular_velocity = list(joint.angular_velocity_xyz)
            tendon_extension = list(joint.tendon_extension_xyz)
            tendon_velocity = list(joint.tendon_velocity_xyz)

            # Gravity torque is computed as r x F in world coordinates and
            # transformed into the parent joint frame. This gives the ball
            # joints real out-of-plane loading instead of a sagittal-only term.
            parent_q = current_transforms[spec.parent][1]
            world_q = current_transforms[spec.name][1]
            subtree_mass = self._subtree_mass[spec.name]
            lever_local = _scale(spec.direction, max(.04, spec.length * .52))
            lever_world = _q_rotate(world_q, lever_local)
            gravity_world = _cross(lever_world, (0.0, -subtree_mass * GRAVITY, 0.0))
            gravity_local = _q_rotate(_q_conjugate(parent_q), gravity_world)

            enabled_axes = sum(1 for enabled in spec.dof_mask if enabled)
            axis_activations = []
            for axis_index, enabled in enumerate(spec.dof_mask):
                if not enabled:
                    rotation[axis_index] = 0.0
                    angular_velocity[axis_index] = 0.0
                    tendon_extension[axis_index] = 0.0
                    tendon_velocity[axis_index] = 0.0
                    continue

                low = spec.min_rotation_xyz[axis_index]
                high = spec.max_rotation_xyz[axis_index]
                target_angle = _clamp(target[axis_index], low, high)
                error = target_angle - rotation[axis_index]
                requested_torque = (
                    spec.kp * readiness * error
                    - spec.kd * angular_velocity[axis_index]
                )
                requested_torque = _clamp(
                    requested_torque, -spec.torque_limit, spec.torque_limit
                )
                activation_target = abs(requested_torque) / spec.torque_limit
                activation_alpha = 1.0 - math.exp(-dt / spec.activation_tau)
                activation_axis = joint.activation + (
                    activation_target - joint.activation
                ) * activation_alpha
                activation_axis = _clamp(activation_axis, 0.0, 1.0)

                # Hill-inspired active force scaling: force falls away from
                # the joint's neutral/optimal angle and with shortening speed.
                width = max(.18, (high - low) * .42)
                force_length = math.exp(-0.5 * (rotation[axis_index] / width) ** 2)
                force_velocity = _clamp(
                    1.0 - .08 * abs(angular_velocity[axis_index]), .35, 1.0
                )
                capacity = spec.torque_limit * activation_axis * force_length * force_velocity * math.sqrt(max(.05, energy))
                muscle_torque = _clamp(requested_torque, -capacity, capacity)

                # Series-elastic tendon: a stable first-order compliant element
                # transmits muscle torque rather than applying it directly.
                tendon_target = muscle_torque / spec.tendon_stiffness
                tendon_target -= (
                    spec.tendon_damping * tendon_velocity[axis_index]
                    / spec.tendon_stiffness
                )
                tendon_alpha = 1.0 - math.exp(-dt / .025)
                old_extension = tendon_extension[axis_index]
                tendon_extension[axis_index] += (
                    tendon_target - old_extension
                ) * tendon_alpha
                tendon_velocity[axis_index] = (
                    tendon_extension[axis_index] - old_extension
                ) / dt
                tendon_torque = _clamp(
                    spec.tendon_stiffness * tendon_extension[axis_index]
                    + spec.tendon_damping * tendon_velocity[axis_index],
                    -capacity, capacity,
                )

                inertia_scale = (1.0, .78, .78)[axis_index]
                inertia = max(
                    .025, subtree_mass * spec.length * spec.length
                    * .36 * inertia_scale
                )
                joint_acceleration = (
                    tendon_torque + gravity_local[axis_index]
                ) / inertia
                angular_velocity[axis_index] = (
                    angular_velocity[axis_index] + joint_acceleration * dt
                ) * math.exp(-.08 * dt)
                unconstrained = (
                    rotation[axis_index] + angular_velocity[axis_index] * dt
                )
                rotation[axis_index] = _clamp(unconstrained, low, high)
                impact = abs(unconstrained - rotation[axis_index])
                if impact > 0.0:
                    angular_velocity[axis_index] = 0.0
                    limit_strain += min(1.0, impact * 3.0)
                axis_activations.append(activation_axis)
                work = abs(tendon_torque * angular_velocity[axis_index]) * dt
                total_work += work
                total_effort += activation_axis * activation_axis * dt
                proprioceptive_sum += abs(target_angle - rotation[axis_index])
                proprioceptive_axes += 1

            activation = sum(axis_activations) / max(1, enabled_axes)
            updated[spec.name] = JointCoordinate(
                name=spec.name,
                angle=rotation[0],
                velocity=angular_velocity[0],
                activation=_clamp(activation, 0.0, 1.0),
                rotation_xyz=tuple(rotation),
                angular_velocity_xyz=tuple(angular_velocity),
                tendon_extension_xyz=tuple(tendon_extension),
                tendon_velocity_xyz=tuple(tendon_velocity),
            )

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
                proprioceptive_sum / max(1, proprioceptive_axes) / 1.2,
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
