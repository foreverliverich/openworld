#!/usr/bin/env python3
"""Real Chromium/WebGL2 acceptance smoke test for Somatic Core.

Requires: pip install playwright; python -m playwright install chromium
The CI job enables Chromium's software WebGL implementation (ANGLE/SwiftShader).
"""
from __future__ import annotations

import functools
import json
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:  # fail loudly when the acceptance dependency is missing
    raise SystemExit("Playwright is required: pip install playwright") from exc

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass


class SomaticWebGLAcceptance(unittest.TestCase):
    def test_seed_morph_compile_render_and_failed_candidate_atomicity(self) -> None:
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--enable-webgl",
                        "--ignore-gpu-blocklist",
                        "--use-gl=angle",
                        "--use-angle=swiftshader",
                        "--enable-unsafe-swiftshader",
                    ],
                )
                page = browser.new_page(viewport={"width": 900, "height": 700})
                page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="load")
                page.set_content(
                    """<!doctype html><html><body style="margin:0">
                    <canvas id="body" width="320" height="240"
                      style="width:320px;height:240px"></canvas>
                    <pre id="result">running</pre></body></html>"""
                )
                page.add_script_tag(url=f"http://127.0.0.1:{server.server_port}/web/somatic-core.js", type="module")
                result = page.evaluate("""async () => {
                  const {SomaticRenderer, GENESIS} = await import('/web/somatic-core.js');
                  const canvas = document.getElementById('body');
                  const renderer = new SomaticRenderer(canvas);
                  const gl = renderer.gl;
                  if (!gl || !gl.getParameter(gl.VERSION).includes('WebGL 2')) {
                    throw new Error('A real WebGL2 context was not created');
                  }
                  await new Promise(resolve => setTimeout(resolve, 350));
                  gl.finish();
                  const pixels = new Uint8Array(canvas.width * canvas.height * 4);
                  gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
                  let litPixels = 0;
                  for (let i = 0; i < pixels.length; i += 4) {
                    if (pixels[i] > 18 || pixels[i+1] > 25 || pixels[i+2] > 35) litPixels++;
                  }
                  if (litPixels < 100) throw new Error('Seed renderer produced no meaningful visible pixels');
                  const originalProgram = renderer.program;
                  let rejected = false;
                  try {
                    renderer.prepare({sdfScript:'vec2 map_object(vec3 p) { return vec2(this is invalid, 1.0); }'});
                  } catch (_) { rejected = true; }
                  if (!rejected) throw new Error('Invalid GLSL candidate was not rejected');
                  if (renderer.program !== originalProgram) throw new Error('Failed candidate replaced active program');
                  const target = 'vec2 map_object(vec3 p) { return vec2(length(p-vec3(0.0,0.2,0.0))-0.6, 1.0); }';
                  const prepared = renderer.prepare({sdfScript:target});
                  if (!prepared) throw new Error('Valid target SDF did not compile and link');
                  renderer.commitPrepared(prepared, {
                    prevSdfScript: GENESIS, sdfScript: target, evolutionProgress: 0.35,
                    morph_started_at: Date.now()/1000, color:[0.7,0.4,0.3],
                    material:{roughness:0.6, metallic:0, sssIntensity:0.8}
                  });
                  if (renderer.a !== GENESIS || renderer.b !== target) {
                    throw new Error('A/B SDF programs were not installed together');
                  }
                  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                  gl.finish();
                  const glError = gl.getError();
                  if (glError !== gl.NO_ERROR) throw new Error('WebGL error after morph commit: '+glError);
                  return {webgl:gl.getParameter(gl.VERSION), renderer:'pass', litPixels,
                    invalidCandidateRejected:rejected, validTargetCompiled:true,
                    activeProgramPreserved:true, abPairInstalled:true, glError};
                }""")
                browser.close()
            self.assertEqual(result["renderer"], "pass", json.dumps(result))
            self.assertTrue(result["invalidCandidateRejected"])
            self.assertTrue(result["validTargetCompiled"])
            self.assertTrue(result["activeProgramPreserved"])
            self.assertTrue(result["abPairInstalled"])
            self.assertEqual(result["glError"], 0)
            print("Somatic WebGL2 acceptance:", json.dumps(result, sort_keys=True))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
