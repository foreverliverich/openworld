# Cognitive goal → Somatic GPU steering seam

This change adopts the useful part of the submitted Python/WebSocket/TypeScript
proposal without introducing a second world-state owner.

## Implemented

- `web/somatic-gpu.js` now exposes `setAttractor(x, y, z, options)` and
  `clearAttractor()`. The 48-byte cell ABI is unchanged.
- The compute uniform grows from 32 to 64 bytes. Goal steering is a bounded
  acceleration, applied before gravity and integration. A near-zero distance
  guard avoids normalizing a zero vector.
- `web/chimera-bridge.js` accepts only schema-v1, explicitly accepted,
  monotonically sequenced goal messages. World revision is retained as
  provenance; it is not confused with the independent goal sequence.
- The browser receiver never writes raw GPU energy/stress into SQLite and never
  treats an LLM proposal as accepted merely because it arrived.

## Message contract

```json
{
  "type": "MACRO_GOAL_UPDATE",
  "schema_version": 1,
  "accepted": true,
  "goal_id": "stable-action-or-goal-id",
  "goal_sequence": 1,
  "organism_id": "chimera",
  "world_revision": 12,
  "target": {"x": 1.0, "y": 1.0, "z": 2.0},
  "steering": {"strength": 1.0, "max_acceleration": 8.0}
}
```

The publisher must emit this only after the existing action gateway / world
validation has accepted the goal. A sequence is monotonic per organism/session.
The world revision remains an optimistic-concurrency provenance value.

## Explicitly not implemented yet

- A running Python WebSocket publisher attached to the existing
  `ChimeraApplication`. The submitted standalone server would otherwise create
  a second process/RealityEngine and could publish proposals from the wrong
  authority.
- A GPU-to-RealityEngine physiological commit. Raw particle aggregates are not
  yet calibrated measurements and must not overwrite ISCE state.
- Worker writes into the same hot fields as GPU compute. CPU workers need
  partitioned ownership or staged command buffers, not unsynchronized writes
  through a SharedArrayBuffer.
- SharedArrayBuffer-to-WebGPU zero-copy. The browser GPU path still uploads
  through `queue.writeBuffer`; SAB is CPU-worker shared memory only.

## Verification boundary

Static contract tests check the ABI, bounded steering, message acceptance and
monotonic sequence guard. A real browser/GPU WebSocket end-to-end test is still
required before calling this a live integrated bridge.
