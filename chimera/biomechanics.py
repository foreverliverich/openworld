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
    tendon_damping: float = 2.5
    activation_tau: float = 0.045
    angular_speed_limit: float = 18.0

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
                    "tendon_stiffness", "tendon_damping", "activation_tau",
                    "angular_speed_limit"):
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
                        -.75, .75, 12.0, 30.0, 4.0),
            SegmentSpec("upper_arm_l", "spine", (-.19,.39,0), (0,-1,0), .31, 2.5, .065,
                        -2.7, 2.7, 45.0, 80.0, 10.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-2.7, -1.9, -2.7), max_rotation_xyz=(2.7, 1.9, 2.7)),
            SegmentSpec("forearm_l", "upper_arm_l", (0,-.31,0), (0,-1,0), .27, 1.5, .052,
                        -2.35, .12, 18.0, 55.0, 8.0),
            SegmentSpec("hand_l", "forearm_l", (0,-.27,0), (0,-1,0), .10, .5, .04,
                        -.85, .85, 3.0, 12.0, 2.0,
                        dof_mask=(True, False, True),
                        min_rotation_xyz=(-.85, 0.0, -.55), max_rotation_xyz=(.85, 0.0, .55)),
            SegmentSpec("upper_arm_r", "spine", (.19,.39,0), (0,-1,0), .31, 2.5, .065,
                        -2.7, 2.7, 45.0, 80.0, 10.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-2.7, -1.9, -2.7), max_rotation_xyz=(2.7, 1.9, 2.7)),
            SegmentSpec("forearm_r", "upper_arm_r", (0,-.31,0), (0,-1,0), .27, 1.5, .052,
                        -2.35, .12, 18.0, 55.0, 8.0),
            SegmentSpec("hand_r", "forearm_r", (0,-.27,0), (0,-1,0), .10, .5, .04,
                        -.85, .85, 3.0, 12.0, 2.0,
                        dof_mask=(True, False, True),
                        min_rotation_xyz=(-.85, 0.0, -.55), max_rotation_xyz=(.85, 0.0, .55)),
            SegmentSpec("thigh_l", "pelvis", (-.10,-.08,0), (0,-1,0), .42, 7.0, .10,
                        -.95, 1.65, 120.0, 220.0, 25.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-.95, -.78, -.72), max_rotation_xyz=(1.65, .78, .72)),
            SegmentSpec("shin_l", "thigh_l", (0,-.42,0), (0,-1,0), .42, 4.0, .075,
                        -2.45, .12, 70.0, 180.0, 20.0),
            SegmentSpec("foot_l", "shin_l", (0,-.42,0), (0,0,1), .20, 1.2, .065,
                        -.65, .65, 15.0, 45.0, 6.0,
                        dof_mask=(True, False, True),
                        min_rotation_xyz=(-.65, 0.0, -.38), max_rotation_xyz=(.65, 0.0, .38)),
            SegmentSpec("thigh_r", "pelvis", (.10,-.08,0), (0,-1,0), .42, 7.0, .10,
                        -.95, 1.65, 120.0, 220.0, 25.0,
                        dof_mask=(True, True, True),
                        min_rotation_xyz=(-.95, -.78, -.72), max_rotation_xyz=(1.65, .78, .72)),
            SegmentSpec("shin_r", "thigh_r", (0,-.42,0), (0,-1,0), .42, 4.0, .075,
                        -2.45, .12, 70.0, 180.0, 20.0),
            SegmentSpec("foot_r", "shin_r", (0,-.42,0), (0,0,1), .20, 1.2, .065,
                        -.65, .65, 15.0, 45.0, 6.0,
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
        return cls(skeleton_version=definition.version, joints=joints)

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
    local_direction: tuple[float, float, float] = (0.0, 1.0, 0.0)


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


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _solve_dense(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Deterministic Gaussian elimination with partial pivoting."""
    n = len(rhs)
    a = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(a[row][column]))
        if abs(a[pivot][column]) < 1e-10:
            raise BiomechanicsError("Articulated mass matrix is singular")
        if pivot != column:
            a[column], a[pivot] = a[pivot], a[column]
        scale = a[column][column]
        for j in range(column, n + 1):
            a[column][j] /= scale
        for row in range(n):
            if row == column:
                continue
            factor = a[row][column]
            if factor == 0.0:
                continue
            for j in range(column, n + 1):
                a[row][j] -= factor * a[column][j]
    return [a[i][n] for i in range(n)]


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
            poses.append(SegmentPose(
                spec.name, origin, end, center, direction, spec.radius,
                world_q, spec.direction,
            ))
        return transforms, tuple(poses)

    def forward_kinematics(self, position: Iterable[float],
                           state: ArticulatedBodyState) -> tuple[SegmentPose, ...]:
        return self._world_transforms(position, state)[1]

    def _dof_layout(self) -> tuple[tuple[str, int], ...]:
        # Root translation is part of the same generalized coordinate vector
        # as the articulated joints. This creates translational/joint coupling
        # in M(q), rather than integrating the pelvis as a separate particle.
        root_dofs = (("__root__", 0), ("__root__", 1), ("__root__", 2))
        joint_dofs = tuple(
            (spec.name, axis)
            for spec in self.skeleton.segments if spec.parent is not None
            for axis, enabled in enumerate(spec.dof_mask) if enabled
        )
        return root_dofs + joint_dofs

    def _mass_matrix_and_gravity(
        self, position: Iterable[float], state: ArticulatedBodyState,
        layout: tuple[tuple[str, int], ...],
    ) -> tuple[list[list[float]], list[float]]:
        """Assemble M(q) and J(q)^T m g from every rigid segment.

        Each segment contributes translational COM Jacobian energy and its
        oriented rod/cylinder inertia tensor. This is a coupled generalized
        mass matrix; it is not a diagonal per-joint inertia approximation.
        """
        transforms, _ = self._world_transforms(position, state)
        coordinates = self._validate_state(state)
        index = {key: i for i, key in enumerate(layout)}
        joint_axes: dict[str, tuple[tuple[float, float, float], ...]] = {}
        joint_origins: dict[str, tuple[float, float, float]] = {}
        for spec in self.skeleton.segments:
            if spec.parent is None:
                continue
            parent_q = transforms[spec.parent][1]
            rx, ry, _ = coordinates[spec.name].rotation_xyz
            qx = _q_axis((1.0, 0.0, 0.0), rx)
            qy = _q_axis((0.0, 1.0, 0.0), ry)
            q_after_x = _q_mul(parent_q, qx)
            q_after_y = _q_mul(q_after_x, qy)
            joint_axes[spec.name] = (
                _q_rotate(parent_q, (1.0, 0.0, 0.0)),
                _q_rotate(q_after_x, (0.0, 1.0, 0.0)),
                _q_rotate(q_after_y, (0.0, 0.0, 1.0)),
            )
            joint_origins[spec.name] = transforms[spec.name][0]

        size = len(layout)
        mass_matrix = [[0.0 for _ in range(size)] for _ in range(size)]
        gravity = [0.0 for _ in range(size)]
        gravity_force = (0.0, -GRAVITY, 0.0)

        for spec in self.skeleton.segments:
            origin, world_q = transforms[spec.name]
            com = _add(origin, _q_rotate(
                world_q, _scale(spec.direction, spec.length * 0.5)
            ))
            segment_axis = _q_rotate(world_q, spec.direction)
            parallel_inertia = 0.5 * spec.mass * spec.radius * spec.radius
            transverse_inertia = spec.mass * (
                spec.length * spec.length / 12.0 + spec.radius * spec.radius / 4.0
            )

            ancestor_names = []
            cursor = spec.name
            while self._specs[cursor].parent is not None:
                ancestor_names.append(cursor)
                cursor = self._specs[cursor].parent

            jacobian_columns = [
                (index[("__root__", axis)], tuple(
                    1.0 if component == axis else 0.0 for component in range(3)
                ), (0.0, 0.0, 0.0))
                for axis in range(3)
            ]
            for joint_name in ancestor_names:
                for axis_index, enabled in enumerate(self._specs[joint_name].dof_mask):
                    if not enabled:
                        continue
                    column_index = index[(joint_name, axis_index)]
                    axis_world = joint_axes[joint_name][axis_index]
                    lever = _sub(com, joint_origins[joint_name])
                    jacobian_columns.append((
                        column_index,
                        _cross(axis_world, lever),
                        axis_world,
                    ))

            for i, linear_i, angular_i in jacobian_columns:
                gravity[i] += spec.mass * _dot(linear_i, gravity_force)
                for j, linear_j, angular_j in jacobian_columns:
                    inertia_angular_j = _add(
                        _scale(angular_j, transverse_inertia),
                        _scale(segment_axis,
                               (parallel_inertia - transverse_inertia)
                               * _dot(angular_j, segment_axis)),
                    )
                    mass_matrix[i][j] += (
                        spec.mass * _dot(linear_i, linear_j)
                        + _dot(angular_i, inertia_angular_j)
                    )

        for i in range(size):
            mass_matrix[i][i] += 1e-6
        return mass_matrix, gravity

    def _coriolis_vector(
        self, position: Iterable[float], state: ArticulatedBodyState,
        layout: tuple[tuple[str, int], ...], base_mass: list[list[float]],
    ) -> list[float]:
        """Compute Christoffel velocity bias from finite-difference dM/dq."""
        count = len(layout)
        qdot = []
        for joint_name, axis_index in layout:
            if joint_name == "__root__":
                qdot.append(state.root_velocity[axis_index])
            else:
                coordinate = next(j for j in state.joints if j.name == joint_name)
                qdot.append(coordinate.angular_velocity_xyz[axis_index])
        if max((abs(value) for value in qdot), default=0.0) < 1e-12:
            return [0.0 for _ in range(count)]
        derivatives = []
        epsilon = 1e-4
        for joint_name, axis_index in layout:
            if joint_name == "__root__":
                derivatives.append([[
                    0.0 for _ in range(count)
                ] for _ in range(count)])
                continue
            changed = []
            joint_spec = self._specs[joint_name]
            coordinate = next(j for j in state.joints if j.name == joint_name)
            current_value = coordinate.rotation_xyz[axis_index]
            low = joint_spec.min_rotation_xyz[axis_index]
            high = joint_spec.max_rotation_xyz[axis_index]
            delta = epsilon if current_value + epsilon <= high else -epsilon
            if current_value + delta < low:
                delta = epsilon
            for joint in state.joints:
                if joint.name != joint_name:
                    changed.append(joint)
                    continue
                rotation = list(joint.rotation_xyz)
                rotation[axis_index] += delta
                changed.append(JointCoordinate(
                    name=joint.name, angle=rotation[0], velocity=joint.velocity,
                    activation=joint.activation, rotation_xyz=tuple(rotation),
                    angular_velocity_xyz=joint.angular_velocity_xyz,
                    tendon_extension_xyz=joint.tendon_extension_xyz,
                    tendon_velocity_xyz=joint.tendon_velocity_xyz,
                ))
            perturbed = ArticulatedBodyState(
                skeleton_version=state.skeleton_version,
                joints=tuple(changed), root_velocity=state.root_velocity,
                contacts=state.contacts, mechanical_strain=state.mechanical_strain,
                proprioceptive_error=state.proprioceptive_error,
                metabolic_work=state.metabolic_work,
            )
            shifted, _ = self._mass_matrix_and_gravity(position, perturbed, layout)
            derivatives.append([
                [(shifted[i][j] - base_mass[i][j]) / delta
                 for j in range(count)]
                for i in range(count)
            ])

        coriolis = [0.0 for _ in range(count)]
        for i in range(count):
            total = 0.0
            for j in range(count):
                for k in range(count):
                    christoffel = 0.5 * (
                        derivatives[k][i][j]
                        + derivatives[j][i][k]
                        - derivatives[i][j][k]
                    )
                    total += christoffel * qdot[j] * qdot[k]
            coriolis[i] = total
        return coriolis

    def _contact_jacobian(
        self, point: tuple[float, float, float], segment_name: str,
        root_position: Iterable[float], state: ArticulatedBodyState,
        layout: tuple[tuple[str, int], ...],
    ) -> tuple[list[float], list[float], list[float]]:
        """World-space point Jacobian for root translation and ancestor joints."""
        transforms, _ = self._world_transforms(root_position, state)
        coordinates = self._validate_state(state)
        index = {key: i for i, key in enumerate(layout)}
        rows = [[0.0 for _ in layout] for _ in range(3)]
        for axis in range(3):
            rows[axis][index[("__root__", axis)]] = 1.0

        cursor = segment_name
        while self._specs[cursor].parent is not None:
            spec = self._specs[cursor]
            parent_q = transforms[spec.parent][1]
            rx, ry, _ = coordinates[cursor].rotation_xyz
            qx = _q_axis((1.0, 0.0, 0.0), rx)
            qy = _q_axis((0.0, 1.0, 0.0), ry)
            q_after_x = _q_mul(parent_q, qx)
            q_after_y = _q_mul(q_after_x, qy)
            axes = (
                _q_rotate(parent_q, (1.0, 0.0, 0.0)),
                _q_rotate(q_after_x, (0.0, 1.0, 0.0)),
                _q_rotate(q_after_y, (0.0, 0.0, 1.0)),
            )
            joint_origin = transforms[cursor][0]
            lever = _sub(point, joint_origin)
            for axis_index, enabled in enumerate(spec.dof_mask):
                if not enabled:
                    continue
                column = index[(cursor, axis_index)]
                linear = _cross(axes[axis_index], lever)
                for component in range(3):
                    rows[component][column] = linear[component]
            cursor = spec.parent
        return rows[0], rows[1], rows[2]

    @staticmethod
    def _row_dot(row: Sequence[float], vector: Sequence[float]) -> float:
        return sum(a * b for a, b in zip(row, vector))

    @staticmethod
    def _closest_points_on_segments(
        p1: tuple[float, float, float], q1: tuple[float, float, float],
        p2: tuple[float, float, float], q2: tuple[float, float, float],
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Return the closest points on two finite 3D line segments."""
        d1, d2, r = _sub(q1, p1), _sub(q2, p2), _sub(p1, p2)
        a, e, f = _dot(d1, d1), _dot(d2, d2), _dot(d2, r)
        epsilon = 1e-12
        if a <= epsilon and e <= epsilon:
            return p1, p2
        if a <= epsilon:
            s = 0.0
            t = _clamp(f / e, 0.0, 1.0)
        else:
            c = _dot(d1, r)
            if e <= epsilon:
                t = 0.0
                s = _clamp(-c / a, 0.0, 1.0)
            else:
                b = _dot(d1, d2)
                denominator = a * e - b * b
                s = _clamp((b * f - c * e) / denominator, 0.0, 1.0) if abs(denominator) > epsilon else 0.0
                t = (b * s + f) / e
                if t < 0.0:
                    t = 0.0
                    s = _clamp(-c / a, 0.0, 1.0)
                elif t > 1.0:
                    t = 1.0
                    s = _clamp((b - c) / a, 0.0, 1.0)
        return _add(p1, _scale(d1, s)), _add(p2, _scale(d2, t))

    def _near_kinematic_ancestor_pair(self, first: str, second: str) -> bool:
        # Ignore a segment and its parent/grandparent: their capsule overlap
        # represents a shared anatomical joint, not a self-collision.
        for descendant, ancestor in ((first, second), (second, first)):
            cursor = descendant
            for _ in range(2):
                parent = self._specs[cursor].parent
                if parent is None:
                    break
                if parent == ancestor:
                    return True
                cursor = parent
        return False

    def _self_collision_constraints(
        self, poses: Sequence[SegmentPose], root_position: Iterable[float],
        state: ArticulatedBodyState, layout: tuple[tuple[str, int], ...],
        *, dt: float,
    ) -> list[dict[str, object]]:
        """Build non-adjacent capsule/capsule constraints for one organism."""
        constraints: list[dict[str, object]] = []
        for first_index, first in enumerate(poses):
            for second in poses[first_index + 1:]:
                if self._near_kinematic_ancestor_pair(first.name, second.name):
                    continue
                point_a, point_b = self._closest_points_on_segments(
                    first.start, first.end, second.start, second.end
                )
                delta = _sub(point_b, point_a)
                distance = math.sqrt(_dot(delta, delta))
                gap = distance - first.radius - second.radius
                if gap >= 0.005:
                    continue
                if distance > 1e-8:
                    normal = _scale(delta, 1.0 / distance)
                else:
                    center_delta = _sub(second.center, first.center)
                    center_length = math.sqrt(_dot(center_delta, center_delta))
                    normal = (
                        _scale(center_delta, 1.0 / center_length)
                        if center_length > 1e-8 else (1.0, 0.0, 0.0)
                    )
                jacobian_a = self._contact_jacobian(
                    point_a, first.name, root_position, state, layout
                )
                jacobian_b = self._contact_jacobian(
                    point_b, second.name, root_position, state, layout
                )
                relative_jacobian = tuple(
                    [jacobian_b[axis][column] - jacobian_a[axis][column]
                     for column in range(len(layout))]
                    for axis in range(3)
                )
                reference = (0.0, 1.0, 0.0) if abs(normal[1]) < 0.9 else (1.0, 0.0, 0.0)
                tangent_1_raw = _cross(normal, reference)
                tangent_1_length = math.sqrt(_dot(tangent_1_raw, tangent_1_raw))
                tangent_1 = _scale(tangent_1_raw, 1.0 / max(1e-12, tangent_1_length))
                tangent_2 = _cross(normal, tangent_1)
                constraints.append({
                    "name": f"self:{first.name}:{second.name}",
                    "gap": gap,
                    "jacobian": relative_jacobian,
                    "normal": normal,
                    "tangent1": tangent_1,
                    "tangent2": tangent_2,
                    "target_normal_speed": max(0.0, -0.2 * gap / dt),
                })
        return constraints

    def _apply_contact_impulses(
        self, mass_matrix: list[list[float]], velocity: list[float],
        contacts: Sequence[dict[str, object]], *, dt: float,
        friction_coefficient: float = 0.75, iterations: int = 10,
    ) -> tuple[list[float], float, float]:
        """Solve unilateral normal and Coulomb-friction impulses by PGS.

        The contact effective masses are computed from M^-1 J^T. Normal
        impulses are non-negative; the two tangential impulses are projected
        onto a circular Coulomb friction cone bounded by mu * normal_impulse.
        """
        if not contacts:
            return velocity, 0.0, 0.0
        prepared = []
        for contact in contacts:
            rows = contact["jacobian"]
            normal = contact.get("normal", (0.0, 1.0, 0.0))
            tangent_1 = contact.get("tangent1", (1.0, 0.0, 0.0))
            tangent_2 = contact.get("tangent2", (0.0, 0.0, 1.0))
            normal_row = [
                sum(normal[axis] * rows[axis][column] for axis in range(3))
                for column in range(len(rows[0]))
            ]
            tangent_x_row = [
                sum(tangent_1[axis] * rows[axis][column] for axis in range(3))
                for column in range(len(rows[0]))
            ]
            tangent_z_row = [
                sum(tangent_2[axis] * rows[axis][column] for axis in range(3))
                for column in range(len(rows[0]))
            ]
            response_n = _solve_dense(mass_matrix, list(normal_row))
            response_x = _solve_dense(mass_matrix, list(tangent_x_row))
            response_z = _solve_dense(mass_matrix, list(tangent_z_row))
            effective_n = self._row_dot(normal_row, response_n)
            effective_x = self._row_dot(tangent_x_row, response_x)
            effective_z = self._row_dot(tangent_z_row, response_z)
            if effective_n <= 1e-10:
                continue
            if effective_x <= 1e-10:
                response_x = [0.0 for _ in velocity]
                effective_x = 1.0
            if effective_z <= 1e-10:
                response_z = [0.0 for _ in velocity]
                effective_z = 1.0
            prepared.append({
                "name": contact["name"], "gap": float(contact["gap"]),
                "target_normal_speed": float(contact.get("target_normal_speed", 0.0)),
                "normal": normal_row, "tx": tangent_x_row, "tz": tangent_z_row,
                "rn": response_n, "rx": response_x, "rz": response_z,
                "en": effective_n, "ex": effective_x, "ez": effective_z,
                "ln": 0.0, "lx": 0.0, "lz": 0.0,
            })

        def apply(response: Sequence[float], impulse_delta: float) -> None:
            if impulse_delta == 0.0:
                return
            for k in range(len(velocity)):
                velocity[k] += response[k] * impulse_delta

        for _ in range(iterations):
            for item in prepared:
                normal_speed = self._row_dot(item["normal"], velocity)
                # Ground contacts use zero normal speed; penetrated self-
                # contacts use bounded Baumgarte separation velocity.
                target_normal_speed = max(
                    0.0, float(item.get("target_normal_speed", 0.0))
                )
                old_normal = item["ln"]
                new_normal = max(
                    0.0, old_normal
                    + (target_normal_speed - normal_speed) / item["en"]
                )
                item["ln"] = new_normal
                apply(item["rn"], new_normal - old_normal)

                speed_x = self._row_dot(item["tx"], velocity)
                speed_z = self._row_dot(item["tz"], velocity)
                old_x, old_z = item["lx"], item["lz"]
                candidate_x = old_x - speed_x / item["ex"]
                candidate_z = old_z - speed_z / item["ez"]
                friction_limit = friction_coefficient * item["ln"]
                magnitude = math.hypot(candidate_x, candidate_z)
                if magnitude > friction_limit and magnitude > 0.0:
                    scale = friction_limit / magnitude
                    candidate_x *= scale
                    candidate_z *= scale
                item["lx"], item["lz"] = candidate_x, candidate_z
                apply(item["rx"], candidate_x - old_x)
                apply(item["rz"], candidate_z - old_z)

        return (
            velocity,
            sum(float(item["ln"]) for item in prepared),
            sum(math.hypot(float(item["lx"]), float(item["lz"])) for item in prepared),
        )

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

        layout = self._dof_layout()
        dof_index = {key: index for index, key in enumerate(layout)}
        actuator_torque = [0.0 for _ in layout]
        tendon_torque_by_dof = [0.0 for _ in layout]
        pending: dict[str, dict[str, object]] = {}
        total_effort = 0.0
        proprioceptive_sum = 0.0
        proprioceptive_axes = 0

        # First compute muscle excitation and series-elastic tendon force for
        # every generalized coordinate. The mass matrix then couples those
        # torques across the entire articulated tree.
        for spec in self.skeleton.segments:
            if spec.parent is None:
                continue
            joint = coordinates[spec.name]
            target = commands.get(spec.name, (0.0, 0.0, 0.0))
            rotation = list(joint.rotation_xyz)
            tendon_extension = list(joint.tendon_extension_xyz)
            tendon_velocity = list(joint.tendon_velocity_xyz)
            axis_activations = []
            for axis_index, enabled in enumerate(spec.dof_mask):
                if not enabled:
                    rotation[axis_index] = 0.0
                    tendon_extension[axis_index] = 0.0
                    tendon_velocity[axis_index] = 0.0
                    continue
                low = spec.min_rotation_xyz[axis_index]
                high = spec.max_rotation_xyz[axis_index]
                target_angle = _clamp(target[axis_index], low, high)
                error = target_angle - rotation[axis_index]
                requested_torque = _clamp(
                    spec.kp * readiness * error
                    - spec.kd * joint.angular_velocity_xyz[axis_index],
                    -spec.torque_limit, spec.torque_limit,
                )
                activation_target = abs(requested_torque) / spec.torque_limit
                activation_alpha = 1.0 - math.exp(-dt / spec.activation_tau)
                activation_axis = _clamp(
                    joint.activation + (activation_target - joint.activation) * activation_alpha,
                    0.0, 1.0,
                )
                width = max(.18, (high - low) * .42)
                force_length = math.exp(-0.5 * (rotation[axis_index] / width) ** 2)
                force_velocity = _clamp(
                    1.0 - .08 * abs(joint.angular_velocity_xyz[axis_index]), .35, 1.0
                )
                capacity = (
                    spec.torque_limit * activation_axis * force_length
                    * force_velocity * math.sqrt(max(.05, energy))
                )
                muscle_torque = _clamp(requested_torque, -capacity, capacity)

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
                transmitted_torque = _clamp(
                    spec.tendon_stiffness * tendon_extension[axis_index]
                    + spec.tendon_damping * tendon_velocity[axis_index],
                    -capacity, capacity,
                )
                index = dof_index[(spec.name, axis_index)]
                actuator_torque[index] = transmitted_torque
                tendon_torque_by_dof[index] = transmitted_torque
                axis_activations.append(activation_axis)
                total_effort += activation_axis * activation_axis * dt
                proprioceptive_sum += abs(target_angle - rotation[axis_index])
                proprioceptive_axes += 1

            pending[spec.name] = {
                "activation": sum(axis_activations) / max(1, len(axis_activations)),
                "tendon_extension": tuple(tendon_extension),
                "tendon_velocity": tuple(tendon_velocity),
            }

        mass_matrix, gravity_vector = self._mass_matrix_and_gravity(root, state, layout)
        coriolis = self._coriolis_vector(root, state, layout, mass_matrix)
        # A commanded root acceleration is converted to a generalized force
        # through the complete mass matrix. This preserves the requested free
        # acceleration while retaining root/joint inertial coupling.
        root_acceleration_vector = [
            acceleration[axis] if name == "__root__" else 0.0
            for name, axis in layout
        ]
        external_generalized_force = [
            sum(mass_matrix[i][j] * root_acceleration_vector[j]
                for j in range(len(layout)))
            for i in range(len(layout))
        ]
        generalized_force = [
            actuator_torque[i] + gravity_vector[i] - coriolis[i]
            + external_generalized_force[i]
            for i in range(len(layout))
        ]
        generalized_acceleration = _solve_dense(mass_matrix, generalized_force)
        updated: dict[str, JointCoordinate] = {}
        total_work = 0.0
        limit_strain = 0.0

        for spec in self.skeleton.segments:
            if spec.parent is None:
                continue
            joint = coordinates[spec.name]
            rotation = list(joint.rotation_xyz)
            angular_velocity = list(joint.angular_velocity_xyz)
            for axis_index, enabled in enumerate(spec.dof_mask):
                if not enabled:
                    rotation[axis_index] = 0.0
                    angular_velocity[axis_index] = 0.0
                    continue
                index = dof_index[(spec.name, axis_index)]
                angular_velocity[axis_index] = (
                    angular_velocity[axis_index] + generalized_acceleration[index] * dt
                ) * math.exp(-.08 * dt)
                speed = spec.angular_speed_limit
                bounded_speed = _clamp(angular_velocity[axis_index], -speed, speed)
                if bounded_speed != angular_velocity[axis_index]:
                    limit_strain += min(
                        1.0, abs(angular_velocity[axis_index] - bounded_speed) / speed
                    )
                    angular_velocity[axis_index] = bounded_speed
                unconstrained = rotation[axis_index] + angular_velocity[axis_index] * dt
                low = spec.min_rotation_xyz[axis_index]
                high = spec.max_rotation_xyz[axis_index]
                rotation[axis_index] = _clamp(unconstrained, low, high)
                impact = abs(unconstrained - rotation[axis_index])
                if impact > 0.0:
                    angular_velocity[axis_index] = 0.0
                    limit_strain += min(1.0, impact * 3.0)
                total_work += abs(
                    tendon_torque_by_dof[index] * angular_velocity[axis_index]
                ) * dt
            actuator = pending[spec.name]
            updated[spec.name] = JointCoordinate(
                name=spec.name, angle=rotation[0], velocity=angular_velocity[0],
                activation=float(actuator["activation"]),
                rotation_xyz=tuple(rotation),
                angular_velocity_xyz=tuple(angular_velocity),
                tendon_extension_xyz=actuator["tendon_extension"],  # type: ignore[arg-type]
                tendon_velocity_xyz=actuator["tendon_velocity"],  # type: ignore[arg-type]
            )

        # Assemble the free generalized velocity from the coupled solve.
        generalized_velocity = []
        for name, axis in layout:
            if name == "__root__":
                value = state.root_velocity[axis] + generalized_acceleration[
                    dof_index[(name, axis)]
                ] * dt
            else:
                value = updated[name].angular_velocity_xyz[axis]
            generalized_velocity.append(value)

        # Predict contact geometry, then solve impulses against the same
        # generalized mass matrix used by the unconstrained articulated solve.
        candidate_root_velocity = tuple(
            _clamp(generalized_velocity[dof_index[("__root__", axis)]], -12.0, 12.0)
            for axis in range(3)
        )
        candidate_root = tuple(
            root[axis] + candidate_root_velocity[axis] * dt for axis in range(3)
        )
        candidate_state = ArticulatedBodyState(
            skeleton_version=self.skeleton.version,
            joints=tuple(updated[s.name] for s in self.skeleton.segments if s.parent is not None),
            root_velocity=candidate_root_velocity,
        )
        candidate_poses = self.forward_kinematics(candidate_root, candidate_state)
        contact_constraints: list[dict[str, object]] = []
        contact_names: list[str] = []
        for segment in candidate_poses:
            endpoint = segment.start if segment.start[1] <= segment.end[1] else segment.end
            bottom = min(segment.start[1], segment.end[1]) - segment.radius
            gap = bottom - self.ground_height
            if gap <= 0.02:
                contact_names.append(segment.name)
                contact_constraints.append({
                    "name": segment.name,
                    "gap": gap,
                    "jacobian": self._contact_jacobian(
                        endpoint, segment.name, candidate_root, candidate_state, layout
                    ),
                    "normal": (0.0, 1.0, 0.0),
                    "tangent1": (1.0, 0.0, 0.0),
                    "tangent2": (0.0, 0.0, 1.0),
                    "target_normal_speed": 0.0,
                })

        contact_constraints.extend(self._self_collision_constraints(
            candidate_poses, candidate_root, candidate_state, layout, dt=dt
        ))
        constrained_velocity, _, _ = self._apply_contact_impulses(
            mass_matrix, generalized_velocity, contact_constraints, dt=dt
        )

        # Constraint impulses alter both root and joint velocities. Reintegrate
        # joint coordinates from the pre-step configuration using the
        # constrained velocities so pose and momentum cannot disagree.
        constrained_joints: dict[str, JointCoordinate] = {}
        for spec in self.skeleton.segments:
            if spec.parent is None:
                continue
            original = coordinates[spec.name]
            actuator = updated[spec.name]
            rotation = list(original.rotation_xyz)
            angular_velocity = list(original.angular_velocity_xyz)
            for axis_index, enabled in enumerate(spec.dof_mask):
                if not enabled:
                    rotation[axis_index] = 0.0
                    angular_velocity[axis_index] = 0.0
                    continue
                index = dof_index[(spec.name, axis_index)]
                angular_velocity[axis_index] = _clamp(
                    constrained_velocity[index],
                    -spec.angular_speed_limit, spec.angular_speed_limit,
                )
                unconstrained = rotation[axis_index] + angular_velocity[axis_index] * dt
                low, high = spec.min_rotation_xyz[axis_index], spec.max_rotation_xyz[axis_index]
                rotation[axis_index] = _clamp(unconstrained, low, high)
                impact = abs(unconstrained - rotation[axis_index])
                if impact > 0.0:
                    angular_velocity[axis_index] = 0.0
                    limit_strain += min(1.0, impact * 3.0)
            constrained_joints[spec.name] = JointCoordinate(
                name=spec.name, angle=rotation[0], velocity=angular_velocity[0],
                activation=actuator.activation, rotation_xyz=tuple(rotation),
                angular_velocity_xyz=tuple(angular_velocity),
                tendon_extension_xyz=actuator.tendon_extension_xyz,
                tendon_velocity_xyz=actuator.tendon_velocity_xyz,
            )

        root_velocity = tuple(
            _clamp(constrained_velocity[dof_index[("__root__", axis)]], -12.0, 12.0)
            for axis in range(3)
        )
        root = [root[axis] + root_velocity[axis] * dt for axis in range(3)]
        provisional_state = ArticulatedBodyState(
            skeleton_version=self.skeleton.version,
            joints=tuple(
                constrained_joints[s.name] for s in self.skeleton.segments
                if s.parent is not None
            ),
            root_velocity=root_velocity,
            contacts=tuple(contact_names),
            mechanical_strain=_clamp(limit_strain, 0.0, 1.0),
            proprioceptive_error=_clamp(
                proprioceptive_sum / max(1, proprioceptive_axes) / 1.2, 0.0, 1.0
            ),
            metabolic_work=state.metabolic_work + total_work,
        )
        final_poses = self.forward_kinematics(root, provisional_state)

        # Split positional stabilization removes residual capsule penetration;
        # the velocity response itself has already been handled by impulses.
        penetration = max(
            0.0,
            max(
                self.ground_height
                - (min(pose.start[1], pose.end[1]) - pose.radius)
                for pose in final_poses
            ),
        )
        if penetration > 0.0:
            root[1] += penetration
        corrected_position = tuple(root)
        final_poses = self.forward_kinematics(corrected_position, provisional_state)
        final_contacts = tuple(
            pose.name for pose in final_poses
            if min(pose.start[1], pose.end[1]) - pose.radius
            <= self.ground_height + 0.012
        )
        corrected_state = ArticulatedBodyState(
            skeleton_version=self.skeleton.version,
            joints=provisional_state.joints,
            root_velocity=provisional_state.root_velocity,
            contacts=final_contacts,
            mechanical_strain=provisional_state.mechanical_strain,
            proprioceptive_error=provisional_state.proprioceptive_error,
            metabolic_work=provisional_state.metabolic_work,
        )
        metabolic_cost = total_work * 0.000015 + total_effort * 0.00008
        work_units = total_work + total_effort
        return BiomechanicsResult(
            corrected_state, corrected_position, final_poses,
            corrected_state.mechanical_strain,
            corrected_state.proprioceptive_error,
            metabolic_cost, work_units, corrected_state.contacts,
        )
