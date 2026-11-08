"""Static contract checks for the browser worker scheduler.

These checks verify wiring and lifecycle semantics, not real browser execution.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BrowserRuntimeWorkerTests(unittest.TestCase):
    def test_worker_is_present_and_uses_authoritative_tick_api(self):
        worker = (ROOT / "web" / "runtime-worker.js").read_text()
        self.assertIn('fetch("/api/tick"', worker)
        self.assertIn('message.type !== "start"', worker)
        self.assertIn('message.type === "stop"', worker)
        self.assertIn("setTimeout(cycle", worker)

    def test_worker_does_not_own_render_loop_or_duplicate_simulation(self):
        worker = (ROOT / "web" / "runtime-worker.js").read_text()
        self.assertNotIn("requestAnimationFrame", worker)
        self.assertNotIn("RealityEngine", worker)
        self.assertIn("it does not own", worker)

    def test_browser_home_exposes_explicit_start_and_pause_controls(self):
        html = (ROOT / "web" / "index.html").read_text()
        self.assertIn('id="run"', html)
        self.assertIn('id="pause"', html)
        self.assertIn("new Worker('/web/runtime-worker.js')", html)

    def test_browser_explicitly_disposes_worker_on_unload(self):
        html = (ROOT / "web" / "index.html").read_text()
        self.assertIn("beforeunload", html)
        self.assertIn("runtimeWorker?.terminate()", html)


if __name__ == "__main__":
    unittest.main()
