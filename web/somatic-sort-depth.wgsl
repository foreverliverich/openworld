// Somatic Gaussian depth-key generation.
// Keys sort in ascending uint32 order from farthest to nearest.
// The camera uses a right-handed view matrix; forward depth is -view-space z.
struct Particle {
  position: vec4<f32>,
  velocity: vec4<f32>,
  state: vec4<f32>,
};
struct CameraUniforms {
  view: mat4x4<f32>,
};
@group(0) @binding(0) var<storage, read> particles: array<Particle>;
@group(0) @binding(1) var<storage, read_write> keys: array<u32>;
@group(0) @binding(2) var<storage, read_write> values: array<u32>;
@group(0) @binding(3) var<uniform> camera: CameraUniforms;

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  let index = gid.x;
  if (index >= arrayLength(&particles) ||
      index >= arrayLength(&keys) ||
      index >= arrayLength(&values)) { return; }

  let world = vec4<f32>(particles[index].position.xyz, 1.0);
  let viewPosition = camera.view * world;
  let depth = -viewPosition.z;

  // Reject behind-camera, NaN and negative depths to a deterministic far
  // sentinel. Normal visible depths are finite and non-negative.
  var key = 0u;
  if (depth >= 0.0 && depth <= 3.402823e+38) {
    // Positive IEEE-754 floats have monotonically increasing bit patterns.
    // Bitwise inversion converts ascending depth into far-to-near ordering.
    key = ~bitcast<u32>(depth);
  }
  keys[index] = key;
  values[index] = index;
}
