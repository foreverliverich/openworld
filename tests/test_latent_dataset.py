import json
import os
import tempfile
import unittest

from chimera.latent_dataset import (
    LatentDatasetError,
    LatentTrajectoryRecorder,
    load_alignment_sessions,
    load_trajectory_dataset,
    load_trajectory_sessions,
    merge_alignment_sessions,
    split_named_sessions,
    split_trajectory_sessions,
)
from chimera.latent_language import (
    EncoderRegistry,
    LatentLanguageCoordinator,
    SpecialistContext,
)
from chimera.latent_language import LATENT_DIMENSIONS


class LatentDatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "latent.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def record_modality(modality, dimension, *, value=0.1, training_dimension=None):
        training_dimension = training_dimension or dimension
        return {
            "embedding": [value] * dimension,
            "training_embedding": [value + 0.01] * training_dimension,
            "confidence": 0.9,
            "source_id": f"source-{modality}",
            "encoder_id": f"encoder-{modality}",
            "shared_space": None,
        }

    def append_session(self, trajectory_id, *, alignment=False, audio=False, dt=0.05):
        recorder = LatentTrajectoryRecorder(
            self.path, organism_id="test-organism", trajectory_id=trajectory_id,
        )
        for index in range(2):
            modalities = {}
            if alignment:
                modalities = {
                    "text": self.record_modality("text", 768, value=0.1 + index * 0.01),
                    "image": self.record_modality("image", 512, value=0.2 + index * 0.01),
                }
                if audio:
                    modalities["audio"] = self.record_modality(
                        "audio", 128, value=0.3, training_dimension=768,
                    )
            recorder.record(
                latent_vector=[0.01 * index + 0.001 * n for n in range(LATENT_DIMENSIONS)],
                latent_state_digest=f"state-{trajectory_id}-{index}",
                timestamp=float(index), sample_dt=dt, world_revision=index,
                modality_embeddings=modalities, alignment_pair=alignment,
                selected_proposal_ids=(f"proposal-{index}",),
            )

    def test_recorder_writes_chain_verified_latent_trajectories(self):
        self.append_session("session-a")
        sessions, sample_dt = load_trajectory_dataset(self.path)
        self.assertEqual(set(sessions), {"session-a"})
        self.assertEqual(len(sessions["session-a"]), 2)
        self.assertEqual(len(sessions["session-a"][0]), LATENT_DIMENSIONS)
        self.assertAlmostEqual(sample_dt, 0.05)

    def test_validation_split_is_by_whole_session_not_adjacent_rows(self):
        for session in ("a", "b", "c", "d", "e"):
            self.append_session(session)
        sessions = load_trajectory_sessions(self.path)
        train, validation = split_trajectory_sessions(sessions, seed="fixed")
        self.assertGreaterEqual(len(train), 1)
        self.assertGreaterEqual(len(validation), 1)
        self.assertEqual(len(train) + len(validation), len(sessions))
        train_named, validation_named = split_named_sessions(
            {key: {"payload": value} for key, value in sessions.items()},
            seed="fixed",
        )
        self.assertFalse(set(train_named) & set(validation_named))
        self.assertEqual(set(train_named) | set(validation_named), set(sessions))

    def test_alignment_capture_requires_explicitly_paired_text_and_image(self):
        recorder = LatentTrajectoryRecorder(self.path, trajectory_id="bad-pair")
        with self.assertRaises(LatentDatasetError):
            recorder.record(
                latent_vector=[0.0] * LATENT_DIMENSIONS,
                latent_state_digest="state", timestamp=0.0, sample_dt=0.05,
                world_revision=0,
                modality_embeddings={"text": self.record_modality("text", 768)},
                alignment_pair=True,
            )

    def test_alignment_loader_only_uses_explicit_pairs_and_keeps_audio_768d(self):
        self.append_session("pair-a", alignment=True, audio=True)
        self.append_session("pair-b", alignment=True, audio=True)
        sessions = load_alignment_sessions(self.path, include_audio=True)
        merged = merge_alignment_sessions(sessions)
        self.assertEqual(len(merged["text"]), 4)
        self.assertEqual(len(merged["image"]), 4)
        self.assertEqual(len(merged["audio"]), 4)
        self.assertEqual(len(merged["audio"][0]), 768)

    def test_alignment_loader_rejects_unpaired_audio_rows(self):
        self.append_session("pair-a", alignment=True, audio=True)
        self.append_session("pair-b", alignment=True, audio=False)
        with self.assertRaises(LatentDatasetError):
            load_alignment_sessions(self.path, include_audio=True)

    def test_dataset_rejects_modified_latent_vector_digest(self):
        self.append_session("tampered")
        with open(self.path, "r", encoding="utf-8") as handle:
            record = json.loads(handle.readline())
            second = handle.readline()
        record["latent_vector"][0] = 99.0
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
            handle.write(second)
        with self.assertRaises(LatentDatasetError):
            load_trajectory_sessions(self.path)

    def test_dataset_requires_consistent_runtime_integration_step(self):
        self.append_session("dt-a", dt=0.05)
        self.append_session("dt-b", dt=0.04)
        with self.assertRaises(LatentDatasetError):
            load_trajectory_dataset(self.path)

    def test_coordinator_records_successful_cycle_and_aligned_embeddings(self):
        class FixedEncoder:
            def __init__(self, encoder_id, dimension):
                self.encoder_id = encoder_id
                self.dimension = dimension
            def encode(self, payload):
                return (0.1,) * self.dimension

        registry = EncoderRegistry()
        registry.register("text", FixedEncoder("text-v1", 768))
        registry.register("image", FixedEncoder("image-v1", 512))
        recorder = LatentTrajectoryRecorder(self.path, trajectory_id="cycle-session")
        coordinator = LatentLanguageCoordinator(
            registry, trajectory_recorder=recorder,
        )
        result = coordinator.cycle(
            [
                {"modality": "text", "payload": "A caption describing the image",
                 "source_id": "caption-1"},
                {"modality": "image", "payload": b"image",
                 "source_id": "image-1"},
            ],
            SpecialistContext(
                1.0, 7, text="A caption describing the image",
                source_refs=("caption-1", "image-1"), alignment_pair=True,
            ),
        )
        # One cycle is insufficient for training, but the raw aligned pair is recorded.
        with open(self.path, "r", encoding="utf-8") as handle:
            record = json.loads(handle.readline())
        self.assertTrue(record["alignment_pair"])
        self.assertEqual(len(record["modalities"]["text"]["training_embedding"]), 768)
        self.assertEqual(len(record["modalities"]["image"]["training_embedding"]), 512)
        self.assertEqual(record["latent_state_digest"], result.state.digest)

    def test_failed_dataset_append_does_not_publish_latent_cycle(self):
        class FixedEncoder:
            encoder_id = "text-v1"
            def encode(self, payload):
                return [0.1] * 768

        class FailingRecorder:
            def record(self, **kwargs):
                raise LatentDatasetError("simulated durable append failure")

        registry = EncoderRegistry()
        registry.register("text", FixedEncoder())
        coordinator = LatentLanguageCoordinator(
            registry, trajectory_recorder=FailingRecorder(),
        )
        before = coordinator.state.digest
        with self.assertRaises(LatentDatasetError):
            coordinator.cycle(
                [{"modality": "text", "payload": "test", "source_id": "test-source"}],
                SpecialistContext(1.0, 0, text="test", source_refs=("test-source",)),
            )
        self.assertEqual(coordinator.state.digest, before)

    def test_registry_preserves_raw_audio_training_features(self):
        class AudioEncoder:
            encoder_id = "audio-runtime-projected"
            def encode_with_training_input(self, payload):
                return ([0.2] * 128, [0.3] * 768)

        registry = EncoderRegistry()
        registry.register("audio", AudioEncoder())
        encoded = registry.encode(
            "audio", {"waveform": "not-read-by-fake"}, timestamp=1.0,
            confidence=0.8, source_id="audio-1",
        )
        self.assertEqual(len(encoded.embedding), 128)
        self.assertEqual(len(encoded.training_embedding), 768)


if __name__ == "__main__":
    unittest.main()
