#!/usr/bin/env python3
"""Real Chromium acceptance for the Three.js articulated organism viewer.

Requires Playwright and a Chromium build with ANGLE/SwiftShader WebGL2 support.
The test starts the actual Chimera HTTP application and exercises the browser UI
against the same ISCE/RealityEngine state transaction used by local users.
"""
from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    raise SystemExit("Playwright is required: pip install playwright") from exc

from chimera.http_server import ChimeraApplication, ChimeraHTTPServer


class ArticulatedBodyBrowserAcceptance(unittest.TestCase):
    def test_threejs_pose_projection_and_three_axis_motor_control(self) -> None:
        page_errors: list[str] = []
        with tempfile.TemporaryDirectory(prefix="chimera-body-browser-") as directory:
            app = ChimeraApplication(str(Path(directory) / "body.sqlite3"))
            server = ChimeraHTTPServer(("127.0.0.1", 0), app)
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
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    page.on("pageerror", lambda error: page_errors.append(str(error)))
                    page.goto(
                        f"http://127.0.0.1:{server.server_port}/",
                        wait_until="load",
                        timeout=60000,
                    )
                    page.wait_for_function(
                        """() => {
                          const status = document.querySelector('#bodyStatus')?.textContent || '';
                          return status.includes('human-3d-1') && status.includes('16 segments');
                        }""",
                        timeout=60000,
                    )
                    renderer = page.evaluate(
                        """() => {
                          const canvas = document.querySelector('#scene canvas');
                          const gl = canvas?.getContext('webgl2');
                          return {
                            canvas: !!canvas,
                            width: canvas?.width || 0,
                            height: canvas?.height || 0,
                            version: gl ? gl.getParameter(gl.VERSION) : null
                          };
                        }"""
                    )
                    self.assertTrue(renderer["canvas"], renderer)
                    self.assertGreater(renderer["width"], 0, renderer)
                    self.assertGreater(renderer["height"], 0, renderer)
                    self.assertIn("WebGL 2", renderer["version"] or "", renderer)

                    # Submit a hip abduction target through the visible form.
                    # Check native HTML constraint validation before clicking:
                    # a rejected form would silently suppress the submit event.
                    validity = page.locator('#bodyForm').evaluate(
                        """form => Array.from(form.elements)
                          .filter(element => element.willValidate)
                          .map(element => ({
                            name: element.name,
                            valid: element.validity.valid,
                            message: element.validationMessage
                          }))"""
                    )
                    self.assertTrue(all(item["valid"] for item in validity), validity)
                    # The resulting pose must come back from the authoritative API.
                    page.locator('input[name="thigh_l_y"]').fill("0.45")
                    with page.expect_response(
                        lambda response: response.url.endswith("/api/body/actuate"),
                        timeout=30000,
                    ) as response_info:
                        page.locator('#bodyForm button[type="submit"]').click()
                    body_response = response_info.value
                    response_payload = body_response.json()
                    self.assertEqual(
                        body_response.status, 200,
                        f"body actuation returned {body_response.status}: {response_payload}",
                    )
                    page.wait_for_function(
                        """() => document.querySelector('#log')?.textContent.includes('"actuation"')""",
                        timeout=30000,
                    )
                    action_log = page.locator('#log').inner_text()
                    self.assertIn('"actuation"', action_log, action_log)
                    pose = page.evaluate(
                        """async () => await (await fetch('/api/body/pose')).json()"""
                    )
                    hip = next(joint for joint in pose["joints"] if joint["name"] == "thigh_l")
                    self.assertGreater(abs(hip["rotation_xyz"][1]), 1e-5, pose)
                    self.assertEqual(len(pose["segments"]), 16)
                    self.assertEqual(len(pose["segments"][0]["orientation"]), 4)
                    self.assertEqual(page_errors, [], "Browser JavaScript errors: " + repr(page_errors))
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
                app.close()


if __name__ == "__main__":
    unittest.main()
