"""Local HTTP application that connects Chimera's canonical runtime to the browser.

Run with: python -m chimera.http_server
The HTTP layer is deliberately thin: RealityEngine remains the sole world-state
owner; this module only exposes validated reads/actions and serves the client.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .somatic_kernel import generate_morph_package
from urllib.parse import parse_qs, urlparse

from . import (
    AutonomousRuntime,
    AutonomousWorldAgent,
    ChimeraToolbox,
    InvalidWorldAction,
    OrganismKernel,
    RealityEngine,
    RevisionConflict,
    ToolboxError,
    WorldConfig,
)

MAX_BODY_BYTES = 1_048_576
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"


class ChimeraApplication:
    """Owns exactly one world, organism, agent, runtime and toolbox."""

    def __init__(self, database: str = "chimera_world.sqlite3"):
        self.world = RealityEngine(WorldConfig(database=database))
        self.organism = OrganismKernel(self.world, "chimera")
        self.agent = AutonomousWorldAgent(self.world, self.organism)
        self.runtime = AutonomousRuntime(self.world, self.agent)
        self.toolbox = ChimeraToolbox(self.world, actor_id="player")
        self._mutation_lock = threading.RLock()

    def state(self) -> dict[str, Any]:
        # A single API response must describe one committed revision, not a
        # mixture of pre- and post-mutation reads from concurrent HTTP workers.
        with self._mutation_lock:
            snapshot = self.runtime.snapshot()
            snapshot["entities"] = [entity.to_dict() for entity in self.world.entities()]
            snapshot["toolbox"] = self.toolbox.manifest()
            snapshot["event_chain_valid"] = self.world.verify_event_chain()
            return snapshot

    def tick(self, count: int = 1) -> dict[str, Any]:
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 120:
            raise ValueError("ticks must be an integer between 1 and 120")
        frames = []
        with self._mutation_lock:
            for _ in range(count):
                frame = self.runtime.tick()
                frames.append({
                    "tick": frame.tick,
                    "world_revision": frame.world_revision,
                    "simulation_time": frame.simulation_time,
                    "physics_result": frame.physics_result,
                    "agent_result": frame.agent_result,
                })
        return {"frames": frames, "state": self.state()}

    def execute_tool(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = ("tool", "action")
        if any(not isinstance(payload.get(key), str) for key in required):
            raise ValueError("tool and action must be strings")
        arguments = payload.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        expected = payload.get("expected_revision")
        if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool)):
            raise ValueError("expected_revision must be an integer")
        with self._mutation_lock:
            result = self.toolbox.execute(
                payload["tool"], payload["action"], arguments,
                actor_id=str(payload.get("actor_id", "player")),
                expected_revision=expected,
            )
        return {"result": result, "state": self.state()}

    def events(self, after_revision: int = 0, limit: int = 250) -> dict[str, Any]:
        with self._mutation_lock:
            return {
                "events": self.world.event_history(after_revision=after_revision, limit=limit),
                "revision": self.world.revision(),
                "chain_valid": self.world.verify_event_chain(),
            }

    def close(self) -> None:
        self.world.close()


class ChimeraRequestHandler(BaseHTTPRequestHandler):
    server_version = "ChimeraLocal/0.1"

    @property
    def app(self) -> ChimeraApplication:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[chimera-http] " + fmt % args)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValueError("request body exceeds 1 MiB")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("request JSON must be an object")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                return self._json(200, {
                    "ok": True, "engine": "RealityEngine",
                    "revision": self.app.world.revision(),
                })
            if parsed.path == "/api/state":
                return self._json(200, self.app.state())
            if parsed.path == "/api/events":
                query = parse_qs(parsed.query)
                after = int(query.get("after_revision", ["0"])[0])
                limit = int(query.get("limit", ["250"])[0])
                if after < 0 or not 1 <= limit <= 1000:
                    raise ValueError("after_revision must be >= 0 and limit must be 1..1000")
                return self._json(200, self.app.events(after, limit))
            if parsed.path == "/":
                return self._static("index.html")
            if parsed.path.startswith("/web/"):
                return self._static(parsed.path.removeprefix("/web/"))
            return self._json(404, {"error": "not_found", "path": parsed.path})
        except (ValueError, TypeError) as exc:
            return self._json(400, {"error": "invalid_request", "message": str(exc)})

    def _static(self, relative: str) -> None:
        root = WEB_ROOT.resolve()
        target = (root / relative).resolve()
        if root not in target.parents or not target.is_file():
            return self._json(404, {"error": "asset_not_found"})
        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith(("text/", "application/javascript")) else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            if self.path == "/api/somatic/morph":
                description = payload.get("description")
                current_label = payload.get("current_label", "")
                if not isinstance(description, str) or not isinstance(current_label, str):
                    raise ValueError("description and current_label must be strings")
                package = generate_morph_package(description, current_label)
                return self._json(200, {"package": package})
            if self.path == "/api/tick":
                return self._json(200, self.app.tick(payload.get("ticks", 1)))
            if self.path == "/api/tool":
                return self._json(200, self.app.execute_tool(payload))
            return self._json(404, {"error": "not_found", "path": self.path})
        except RevisionConflict as exc:
            return self._json(409, {"error": "revision_conflict", "message": str(exc),
                                    "current_revision": self.app.world.revision()})
        except (ToolboxError, InvalidWorldAction, ValueError, TypeError, KeyError,
                json.JSONDecodeError) as exc:
            return self._json(400, {"error": "action_rejected", "message": str(exc),
                                    "current_revision": self.app.world.revision()})
        except Exception as exc:
            return self._json(500, {"error": "internal_error", "message": str(exc)})


class ChimeraHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], app: ChimeraApplication):
        self.app = app
        super().__init__(address, ChimeraRequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Chimera world and browser client")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind to loopback by default; do not expose publicly without authentication")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database", default="chimera_world.sqlite3")
    args = parser.parse_args()
    app = ChimeraApplication(args.database)
    server = ChimeraHTTPServer((args.host, args.port), app)
    print(f"Chimera running at http://{args.host}:{args.port}")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStopping Chimera...")
    finally:
        server.server_close()
        app.close()


if __name__ == "__main__":
    main()
