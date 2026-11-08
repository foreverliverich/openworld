# Browser worker lifecycle

The main Chimera page now exposes explicit **Run organism** and **Pause**
controls. The Run control creates web/runtime-worker.js. The worker schedules
batches of three authoritative POST /api/tick calls, targeting a 100 ms batch
period, and reports each returned frame to the page. The renderer remains a
projection and requestAnimationFrame remains confined to visual rendering.

The worker does not duplicate RealityEngine, ISCE or organism state. The Python
runtime and SQLite database remain authoritative. This is a browser-driven
scheduler for the existing hybrid application, not a browser-resident ISCE
kernel.

Pausing stops new batches; the latest committed state remains in SQLite.
Unloading the page terminates the worker. If the browser is suspended, closed,
or the worker errors, execution stops. Such an interval is paused/dormant, not
continuous organism life. The browser does not promise background execution
when closed.

The UI now shows attention focus/urgency and last-frame sensory salience,
novelty and observation error when the agent reaches its observe/consolidate
phase.

## Verification boundary

Python CI statically verifies worker/API wiring, explicit start/stop controls,
worker disposal and the absence of a worker-side render loop. This does not
replace an actual browser session. Web Worker scheduling, browser suspension,
Three.js rendering, WebGL2 SDF compilation and visual quality still require
real-browser acceptance testing.
