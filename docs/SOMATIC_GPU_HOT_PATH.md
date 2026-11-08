# Somatic GPU hot path (first executable slice)

`web/somatic-gpu.js` implements an opt-in WebGPU compute path used by `web/somatic.html`. It preserves the established 48-byte cell ABI:

- `position: vec4<f32>` — xyz position and mass
- `velocity: vec4<f32>` — xyz velocity and cohesion
- `state: vec4<f32>` — energy, stress, phi seed and resonance tag

The shader performs semi-implicit Euler integration, gravity, a horizontal ground contact plane, normal restitution, tangential friction and bounded stress-dependent energy drain. Zero-length normalization and unbounded delta time are avoided.

## Memory and execution

The host initializes cells once, uploads each page once, then the simulation state remains in GPU storage. Page size is selected from the actual adapter's `maxStorageBufferBindingSize` and `maxBufferSize` limits. The default test run uses 65,536 cells and 16 MiB maximum pages. There is no per-frame GPU readback. An explicit stop action performs readback for diagnostics.

This is **not zero-copy**: `queue.writeBuffer` uploads host memory to GPU memory. It is GPU-resident after initialization. It does not assume that SharedArrayBuffer can be bound directly as WebGPU storage.

## What this slice does not claim

- No inter-cell collision, broadphase, joints, torsion or deformable-body solver.
- No bonded-cell graph, synaptic learning or 5-million-cell benchmark.
- No Rapier integration yet.
- No 432 Hz / phi / vortex displacement forces; those values are not evidence of physical laws.
- No production benchmark on a real browser/GPU has been recorded yet.

The browser control is deliberately opt-in and separate from the existing SDF renderer. This keeps the current canonical RealityEngine and WebGL2 morphology renderer intact while the GPU substrate is validated. The next physical milestone is a separate contact/bond pass with conservation and stability tests, not increasing the particle count.

## Watchdog-aware rotating dispatch

The compute step no longer dispatches every cell in one frame. It rotates
through contiguous global cell ranges, with a five-frame target and a hard
per-frame cap of 262,144 cells by default. The cap is configurable at creation.
Each dispatch carries a base-cell offset, so pages can be traversed without
copying or reading the full population back to the CPU. The final partial range
does not wrap within one command submission, avoiding reuse of a page uniform
for two different offsets in the same submission.

This is a bounded-work scheduling safeguard, **not a proven TDR bypass**:
actual safe budgets depend on adapter, browser, shader complexity and other
GPU work. The current shader has no rendering pass, sorting, NCA or audio
coupling. Rotating subsets also means an individual cell is updated less often
than the display frame rate; this changes effective per-cell simulation
frequency and must be accounted for before treating it as physically
time-equivalent. No five-million-cell benchmark or watchdog test has been run.
