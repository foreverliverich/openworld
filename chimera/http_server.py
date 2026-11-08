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
import uuid
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .somatic_kernel import generate_morph_package, refine_morph_package, validate_morph_package
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
from .latent_language import (
    CognitiveActionGateway,
    LatentLanguageCoordinator,
    MemoryRecord,
    SceneGraph,
    SceneObject,
    SpatialRelation,
    SpecialistContext,
)
from .latent_runtime import build_latent_language
from .scene_interpreter import GeminiSceneInterpreter, SceneInterpretationError

MAX_BODY_BYTES = 12 * 1_048_576
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"


class ChimeraApplication:
    """Owns exactly one world, organism, agent, runtime and toolbox."""

    def __init__(
        self, database: str = "chimera_world.sqlite3", *,
        cognition: LatentLanguageCoordinator | None = None,
        enable_latent_language: bool = False,
        alignment_checkpoint: str | None = None,
        dynamics_checkpoint: str | None = None,
        text_model_id: str = "bert-base-uncased",
        image_model_id: str = "openai/clip-vit-base-patch32",
        audio_model_id: str = "facebook/wav2vec2-base",
        sensor_calibration: dict[str, tuple[float, float]] | None = None,
        device: str = "cpu",
        scene_interpreter: Any | None = None,
        enable_scene_interpreter: bool = False,
        ollama_model: str | None = None,
        ollama_base_url: str = "http://127.0.0.1:11434",
        ollama_timeout: float = 30.0,
        trajectory_log: str | None = None,
        trajectory_organism_id: str = "chimera",
    ):
        if cognition is not None and enable_latent_language:
            raise ValueError("Pass a coordinator or enable model loading, not both")
        if not enable_latent_language and (
            alignment_checkpoint or dynamics_checkpoint or ollama_model or trajectory_log
        ):
            raise ValueError("Model checkpoints, Ollama and trajectory logging require --enable-latent-language")
        self.world = RealityEngine(WorldConfig(database=database))
        self.organism = OrganismKernel(self.world, "chimera")
        self.agent = AutonomousWorldAgent(self.world, self.organism)
        self.toolbox = ChimeraToolbox(self.world, actor_id="player")
        if scene_interpreter is not None and enable_scene_interpreter:
            raise ValueError("Pass a scene interpreter or enable the Gemini scene interpreter, not both")
        self.scene_interpreter = (
            scene_interpreter or (GeminiSceneInterpreter() if enable_scene_interpreter else None)
        )
        self.cognition = cognition
        cognition_gateway = None
        if enable_latent_language:
            self.cognition, cognition_gateway = build_latent_language(
                self.toolbox, self.organism,
                alignment_checkpoint=alignment_checkpoint,
                dynamics_checkpoint=dynamics_checkpoint,
                text_model_id=text_model_id,
                image_model_id=image_model_id,
                audio_model_id=audio_model_id,
                sensor_calibration=sensor_calibration,
                device=device,
                ollama_model=ollama_model,
                ollama_base_url=ollama_base_url,
                ollama_timeout=ollama_timeout,
                trajectory_log=trajectory_log,
                trajectory_organism_id=trajectory_organism_id,
            )
        elif self.cognition is not None:
            cognition_gateway = CognitiveActionGateway(
                self.toolbox, self.cognition.workspace, self.organism
            )
        self.runtime = AutonomousRuntime(
            self.world, self.agent,
            cognition=self.cognition,
            cognition_gateway=cognition_gateway,
        )
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
                    "cognition_result": frame.cognition_result,
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


    def queue_cognition(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Queue text, image, audio and calibrated sensor evidence for the next tick."""
        if self.cognition is None:
            raise RuntimeError("Latent Language is disabled; start with --enable-latent-language")
        if not isinstance(payload, dict):
            raise ValueError("cognition payload must be an object")
        text = payload.get("text", "")
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        observations = payload.get("observations", [])
        if not isinstance(observations, list):
            raise ValueError("observations must be a list")
        request_id = payload.get("request_id")
        if request_id is None:
            request_id = f"cognition-{self.world.revision()}-{uuid.uuid4().hex[:12]}"
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id must be a non-empty string")

        normalized_observations: list[dict[str, Any]] = []
        seen_text = False
        scene_image_base64: str | None = None
        for index, item in enumerate(observations):
            if not isinstance(item, dict):
                raise ValueError(f"observations[{index}] must be an object")
            modality = item.get("modality")
            if modality not in {"text", "image", "audio", "sensor"}:
                raise ValueError(f"Unsupported modality at observations[{index}]")
            if not self.cognition.encoders.supports(modality):
                raise ValueError(f"No configured {modality} encoder; configure its pretrained model/checkpoint first")
            source_id = item.get("source_id", f"{request_id}:{modality}:{index}")
            if not isinstance(source_id, str) or not source_id:
                raise ValueError("observation source_id must be a non-empty string")
            confidence = item.get("confidence", 1.0)
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise ValueError("observation confidence must be numeric")
            record: dict[str, Any] = {
                "modality": modality,
                "payload": item.get("payload"),
                "confidence": float(confidence),
                "source_id": source_id,
            }
            if "timestamp" in item:
                record["timestamp"] = float(item["timestamp"])
            if modality == "image":
                image_value = item.get("image_base64")
                if image_value is None and isinstance(item.get("payload"), dict):
                    image_value = item["payload"].get("image_base64")
                if image_value is not None:
                    if scene_image_base64 is not None:
                        raise ValueError("Only one image may be used for a single scene interpretation")
                    scene_image_base64 = image_value
                    record["payload"] = {"image_base64": image_value}
            if modality == "audio":
                audio_payload = item.get("payload", {})
                if not isinstance(audio_payload, dict):
                    audio_payload = {}
                if "audio_f32_base64" in item:
                    audio_payload = {
                        "audio_f32_base64": item["audio_f32_base64"],
                        "sampling_rate": item.get("sampling_rate"),
                    }
                elif "audio" in item:
                    audio_payload = {
                        "audio": item["audio"],
                        "sampling_rate": item.get("sampling_rate"),
                    }
                record["payload"] = audio_payload
            if modality == "text":
                if not isinstance(record["payload"], str):
                    raise ValueError("text observation payload must be a string")
                if not text:
                    text = record["payload"]
                seen_text = True
            normalized_observations.append(record)

        if text and not seen_text:
            normalized_observations.append({
                "modality": "text", "payload": text, "confidence": 1.0,
                "source_id": f"{request_id}:text",
            })
        if not normalized_observations:
            raise ValueError("At least one text or modality observation is required")
        missing_encoders = sorted({
            item["modality"] for item in normalized_observations
            if not self.cognition.encoders.supports(item["modality"])
        })
        if missing_encoders:
            raise ValueError(f"No configured encoders for modalities: {', '.join(missing_encoders)}")
        alignment_pair = payload.get("alignment_pair", False)
        if not isinstance(alignment_pair, bool):
            raise ValueError("alignment_pair must be boolean")
        present_modalities = {item["modality"] for item in normalized_observations}
        if alignment_pair and not {"text", "image"}.issubset(present_modalities):
            raise ValueError(
                "alignment_pair requires a text caption and image observation in the same cognition cycle"
            )

        scene_graph = None
        scene_data = payload.get("scene_graph")
        interpret_scene = payload.get("interpret_scene", False)
        if not isinstance(interpret_scene, bool):
            raise ValueError("interpret_scene must be boolean")
        if scene_data is not None and interpret_scene:
            raise ValueError("Provide scene_graph or interpret_scene, not both")
        if interpret_scene:
            if self.scene_interpreter is None:
                raise RuntimeError(
                    "Semantic scene interpretation is disabled; start with --enable-scene-interpreter"
                )
            if not text.strip() and scene_image_base64 is None:
                raise ValueError("interpret_scene requires text or a base64 image observation")
            if scene_image_base64 is None:
                scene_graph = self.scene_interpreter.interpret(text, scene_id=request_id)
            else:
                scene_graph = self.scene_interpreter.interpret(
                    text, scene_id=request_id, image_base64=scene_image_base64,
                )
        if scene_data is not None:
            if not isinstance(scene_data, dict):
                raise ValueError("scene_graph must be an object")
            objects_data = scene_data.get("objects", [])
            relations_data = scene_data.get("relations", [])
            if not isinstance(objects_data, list) or not isinstance(relations_data, list):
                raise ValueError("scene_graph objects and relations must be lists")
            objects = tuple(SceneObject(
                object_id=item["object_id"],
                kind=item["kind"],
                position=tuple(item["position"]),
                size=tuple(item["size"]),
                material=item.get("material", "default"),
                dynamic=item.get("dynamic", True),
                mass=float(item.get("mass", 1.0)),
            ) for item in objects_data)
            relations = tuple(SpatialRelation(
                relation=item["relation"],
                subject=item["subject"],
                object=item["object"],
                gap=float(item.get("gap", 0.05)),
            ) for item in relations_data)
            scene_graph = SceneGraph(str(scene_data.get("scene_id", request_id)), objects, relations)

        memory_records_data = payload.get("memory_records", [])
        if not isinstance(memory_records_data, list):
            raise ValueError("memory_records must be a list")
        memory_records = tuple(MemoryRecord(
            record_id=item["record_id"],
            text=item["text"],
            embedding=tuple(item["embedding"]),
            timestamp=float(item["timestamp"]),
        ) for item in memory_records_data)

        speaker_id = payload.get("speaker_id", "user")
        participant_count = payload.get("participant_count", 1)
        if not isinstance(speaker_id, str):
            raise ValueError("speaker_id must be a string")
        if isinstance(participant_count, bool) or not isinstance(participant_count, int) or participant_count < 1:
            raise ValueError("participant_count must be a non-negative integer")
        source_refs = payload.get("source_refs", [])
        if not isinstance(source_refs, list) or any(not isinstance(ref, str) for ref in source_refs):
            raise ValueError("source_refs must be a list of strings")
        source_refs = tuple(source_refs) + tuple(
            item["source_id"] for item in normalized_observations
        )
        context = SpecialistContext(
            timestamp=self.world.simulation_time(),
            world_revision=self.world.revision(),
            text=text,
            scene_graph=scene_graph,
            memory_records=memory_records,
            speaker_id=speaker_id,
            participant_count=participant_count,
            source_refs=source_refs,
            alignment_pair=alignment_pair,
        )
        with self._mutation_lock:
            self.runtime.queue_cognition_cycle(normalized_observations, context)
            return {
                "queued": True,
                "request_id": request_id,
                "queue_depth": len(self.runtime._pending_cognition),
                "world_revision": self.world.revision(),
                "modalities": sorted({item["modality"] for item in normalized_observations}),
            }

    def execute_cognitive_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("cognitive action payload must be an object")
        proposal_id = payload.get("proposal_id")
        actor_id = payload.get("actor_id", "player")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError("proposal_id must be a non-empty string")
        if not isinstance(actor_id, str):
            raise ValueError("actor_id must be a string")
        with self._mutation_lock:
            result = self.runtime.execute_selected_proposal(proposal_id, actor_id=actor_id)
            return {"result": result, "state": self.state()}

    def body_pose(self) -> dict[str, Any]:
        with self._mutation_lock:
            state = self.organism.state
            poses = self.organism.kernel.biomechanics.forward_kinematics(
                state.position, state.articulation
            )
            return {
                "world_revision": self.world.revision(),
                "skeleton_version": state.articulation.skeleton_version,
                "root_position": state.position,
                "root_velocity": state.articulation.root_velocity,
                "contacts": state.articulation.contacts,
                "joints": [asdict(joint) for joint in state.articulation.joints],
                "segments": [asdict(pose) for pose in poses],
            }

    def actuate_body(self, payload: dict[str, Any]) -> dict[str, Any]:
        commands = payload.get("motor_commands", {})
        if not isinstance(commands, dict):
            raise ValueError("motor_commands must be an object of joint-name to target-radian values")
        root_acceleration = payload.get("root_acceleration", (0.0, 0.0, 0.0))
        if not isinstance(root_acceleration, (list, tuple)) or len(root_acceleration) != 3:
            raise ValueError("root_acceleration must contain three world-frame values")
        expected = payload.get("expected_revision")
        if not isinstance(expected, int) or isinstance(expected, bool):
            raise ValueError("expected_revision is required and must be an integer")
        parsed_commands = []
        for name, target in commands.items():
            if isinstance(target, (int, float)):
                parsed = float(target)
            elif isinstance(target, (list, tuple)) and len(target) == 3:
                parsed = tuple(float(value) for value in target)
            else:
                raise ValueError(
                    f"motor target {name} must be a number or a three-element radians vector"
                )
            parsed_commands.append((str(name), parsed))
        motor_commands = tuple(parsed_commands)
        with self._mutation_lock:
            result = self.organism.tick(
                dt=self.world.config.fixed_dt,
                motor_commands=motor_commands,
                root_acceleration=tuple(float(v) for v in root_acceleration),
                expected_revision=expected,
                outcome="explicit_body_actuation",
            )
            return {
                "result": {"revision": result.revision, "action": result.action},
                "body": self.body_pose(),
                "state": self.state(),
            }

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
            if parsed.path == "/api/somatic/state":
                return self._json(200, {
                    "state": self.app.world.somatic_morphology(),
                    "world_revision": self.app.world.revision(),
                })
            if parsed.path == "/api/state":
                return self._json(200, self.app.state())
            if parsed.path == "/api/body/pose":
                return self._json(200, self.app.body_pose())
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
                current_state = self.app.world.somatic_morphology()
                package = generate_morph_package(description, current_label, current_state)
                return self._json(200, {"package": package})
            if self.path == "/api/somatic/refine":
                state = self.app.world.somatic_morphology()
                if state is None:
                    raise ValueError("Create a morphology before requesting refinement")
                iteration = payload.get("iteration")
                package = refine_morph_package(
                    state, iteration, payload.get("imageSnapshot")
                )
                return self._json(200, {"package": package, "iteration": iteration})
            if self.path == "/api/somatic/commit":
                expected = payload.get("expected_revision")
                if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool)):
                    raise ValueError("expected_revision must be an integer")
                package = validate_morph_package(payload.get("package"))
                result = self.app.world.apply_somatic_morphology(
                    package, actor_id="somatic-kernel", expected_revision=expected
                )
                return self._json(200, {
                    "result": {"revision": result.revision, **result.details},
                    "state": self.app.world.somatic_morphology(),
                })
            if self.path == "/api/cognition":
                return self._json(202, self.app.queue_cognition(payload))
            if self.path == "/api/cognition/execute":
                return self._json(200, self.app.execute_cognitive_action(payload))
            if self.path == "/api/body/actuate":
                return self._json(200, self.app.actuate_body(payload))
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
        except RuntimeError as exc:
            return self._json(503, {"error": "service_unavailable", "message": str(exc)})
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
    parser.add_argument("--enable-latent-language", action="store_true",
                        help="Load real pretrained modality encoders and enable cognition endpoints")
    parser.add_argument("--enable-scene-interpreter", action="store_true",
                        help="Enable Gemini natural-language-to-validated-3D-scene parsing")
    parser.add_argument("--ollama-model", default=None,
                        help="Optional local Ollama model tag to add as an advisory reasoning co-agent")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434",
                        help="Local Ollama HTTP base URL")
    parser.add_argument("--ollama-timeout", type=float, default=30.0,
                        help="Maximum seconds for one Ollama reasoning request")
    parser.add_argument("--latent-trajectory-log", default=None,
                        help="Optional append-only JSONL path for derived latent training snapshots")
    parser.add_argument("--trajectory-organism-id", default="chimera",
                        help="Stable organism label for trajectory dataset records")
    parser.add_argument("--alignment-checkpoint", default=None,
                        help="Validated multimodal projection checkpoint")
    parser.add_argument("--dynamics-checkpoint", default=None,
                        help="Validated morphogenetic dynamics checkpoint")
    parser.add_argument("--text-model", default="bert-base-uncased")
    parser.add_argument("--image-model", default="openai/clip-vit-base-patch32")
    parser.add_argument("--audio-model", default="facebook/wav2vec2-base")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--sensor-calibration", default=None,
                        help="JSON mapping of 64 sensor channel names to [low, high] ranges")
    args = parser.parse_args()
    calibration = None
    if args.sensor_calibration:
        with open(args.sensor_calibration, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            parser.error("--sensor-calibration must contain a JSON object")
        calibration = {name: (float(bounds[0]), float(bounds[1]))
                       for name, bounds in raw.items()}
    app = ChimeraApplication(
        args.database,
        enable_latent_language=args.enable_latent_language,
        alignment_checkpoint=args.alignment_checkpoint,
        dynamics_checkpoint=args.dynamics_checkpoint,
        text_model_id=args.text_model,
        image_model_id=args.image_model,
        audio_model_id=args.audio_model,
        sensor_calibration=calibration,
        device=args.device,
        enable_scene_interpreter=args.enable_scene_interpreter,
        ollama_model=args.ollama_model,
        ollama_base_url=args.ollama_url,
        ollama_timeout=args.ollama_timeout,
        trajectory_log=args.latent_trajectory_log,
        trajectory_organism_id=args.trajectory_organism_id,
    )
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
