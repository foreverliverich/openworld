/* Browser-home scheduler for the authoritative Chimera runtime.
 * The worker schedules fixed batches through the local API; it does not own
 * organism state or physics. Closing/suspending the browser interrupts this
 * scheduler and must not be described as continuous life.
 */
let running = false;
let inFlight = false;
let intervalMs = 100;
let ticksPerBatch = 3;
let timer = null;

function publish(type, extra = {}) {
  self.postMessage({ type, running, ...extra });
}

function stop() {
  running = false;
  if (timer !== null) clearTimeout(timer);
  timer = null;
  publish("paused");
}

async function cycle() {
  if (!running || inFlight) return;
  inFlight = true;
  const started = performance.now();
  try {
    const response = await fetch("/api/tick", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticks: ticksPerBatch }),
      cache: "no-store",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.error || ("HTTP " + response.status));
    }
    publish("tick", {
      payload,
      requestMs: performance.now() - started,
      batchSize: ticksPerBatch,
    });
  } catch (error) {
    running = false;
    publish("error", { message: String(error?.message || error) });
  } finally {
    inFlight = false;
    if (running) {
      const elapsed = performance.now() - started;
      timer = setTimeout(cycle, Math.max(0, intervalMs - elapsed));
    }
  }
}

self.onmessage = event => {
  const message = event.data || {};
  if (message.type === "stop") {
    stop();
    return;
  }
  if (message.type !== "start") return;
  if (running) return;
  intervalMs = Math.max(50, Math.min(2000, Number(message.intervalMs) || 100));
  ticksPerBatch = Math.max(1, Math.min(30, Math.floor(Number(message.ticksPerBatch) || 3)));
  running = true;
  publish("started", { intervalMs, ticksPerBatch });
  cycle();
};
