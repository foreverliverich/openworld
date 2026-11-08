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


## Spectral audio coupling (first executable bridge)

`web/somatic-audio.js` reads local WebAudio FFT magnitudes and separates
bass (20–250 Hz), mids (250–2,000 Hz), and treble (2,000–12,000 Hz). The
bands are smoothed and passed to the GPU as bounded controls. The shader maps
bass to vertical force, mids to radial force, and treble to tangential force;
a configurable spatial wave produces a visible physical ripple response.
The existing 48-byte cell ABI is unchanged; the uniform block is now 112 bytes.

Usage: create a bridge from a MediaStream or audio element, call `resume()`
from a user gesture, and call `update()` once per animation frame. Call
`dispose()` to disconnect. MediaStream audio is not routed to speakers by
default. The bridge does not record or transmit audio.

This is a controllable spectral force coupling, not a validated acoustic or
cymatic tissue model. It has not yet been browser/GPU tested; no sound-pressure
calibration, material resonance model, or hardware benchmark is claimed.


## Gaussian sort — stage 1: camera-space depth keys

`web/somatic-sort-depth.wgsl` generates one 32-bit key and original particle
index per input particle. It uses right-handed camera-space forward depth
(`-viewPosition.z`), not Euclidean camera distance. For finite nonnegative
IEEE-754 depths, bit patterns are monotonic; inverting those bits makes an
ascending unsigned-integer sort produce far-to-near order.

This is only the key-generation stage. It does not sort, allocate ping-pong
buffers, build histograms, scan bucket offsets, or scatter. The complete
stable radix pipeline remains unimplemented. The caller must supply a
right-handed view matrix and matching storage buffers. Invalid/behind-camera
depths receive key zero and therefore sort after visible far-to-near keys.


## Gaussian radix sorting — first complete GPU sort path

`web/somatic-gpu-sort.js` adds a GPU-resident 4-bit LSD radix pipeline over
the existing SomaticGPU page buffers. It generates camera-space depth keys,
then performs eight histogram → bucket-prefix → scatter rounds, ping-ponging
key and original-index buffers. It returns the sorted original-index buffer
without reading keys or indices back to the CPU. Access it from an existing
simulation with `const sorter = await somatic.createRadixSorter()`, then call
`sorter.sort(viewMatrix)` after each camera update.

The implementation uses per-workgroup atomic bucket counters. This guarantees
unique scatter destinations but does **not** preserve input order for equal
keys; ties may be reordered. The prefix stage currently uses one 16-thread
workgroup with a serial loop over all workgroups per bucket. That is simple
and auditable for an initial implementation, but may become the bottleneck at
large populations and should be replaced by a hierarchical scan after GPU
benchmarking.

The sorter allocates four full-size 32-bit arrays plus histogram/offset
scratch. It checks storage-binding limits and fails explicitly if the
population cannot fit; it does not yet implement multi-level paging of the
sort arrays. At five million particles this is roughly 80 MB for key/index
ping-pong buffers plus about 2.5 MB of histogram/offset scratch. The
original 48-byte particle ABI is unchanged. This produces an index buffer;
a Gaussian splat draw pipeline and renderer integration are still separate
work. No five-million-particle performance or watchdog claim is made.


### Prefix-scan improvement

The initial single-workgroup serial scan has been replaced with a hierarchical
scan: each 256-group tile computes local exclusive prefixes in parallel,
then a compact block-prefix stage computes bucket and tile bases. Scatter
combines both levels. This removes the serial loop over every workgroup from
the critical scatter-prefix path. Equal-key ordering remains intentionally
unstable because local bucket ranks use atomics.
