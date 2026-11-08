#!/usr/bin/env python3
"""Train/evaluate paired multimodal projection heads from explicitly aligned cycles."""
from __future__ import annotations

import argparse
import json

from chimera.latent_dataset import (
    load_alignment_sessions, merge_alignment_sessions, split_named_sessions,
)
from chimera.latent_training import MultimodalProjectionModel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="JSONL path from --latent-trajectory-log")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", default="chimera-alignment-v1")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--include-audio", action="store_true",
                        help="Require raw 768-D audio features for every selected paired cycle")
    parser.add_argument("--text-model", default="bert-base-uncased")
    parser.add_argument("--image-model", default="openai/clip-vit-base-patch32")
    parser.add_argument("--audio-model", default="facebook/wav2vec2-base")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()

    sessions = load_alignment_sessions(args.dataset, include_audio=args.include_audio)
    train_sessions, validation_sessions = split_named_sessions(
        sessions, validation_fraction=args.validation_fraction, seed=args.seed,
    )
    train_pairs = merge_alignment_sessions(train_sessions)
    validation_pairs = merge_alignment_sessions(validation_sessions)
    manifest = {
        "text": f"hf:{args.text_model}",
        "image": f"hf:{args.image_model}",
        "audio": f"hf:{args.audio_model}",
    }
    model = MultimodalProjectionModel(
        device=args.device, encoder_manifest=manifest,
    )
    history = model.fit(
        train_pairs, epochs=args.epochs, batch_size=args.batch_size,
        learning_rate=args.learning_rate, temperature=args.temperature,
    )
    metrics = model.evaluate(validation_pairs)
    model.save_checkpoint(args.checkpoint)
    print(json.dumps({
        "checkpoint": args.checkpoint,
        "paired_sessions": len(sessions),
        "train_sessions": len(train_sessions),
        "validation_sessions": len(validation_sessions),
        "train_pairs": len(train_pairs["text"]),
        "validation_pairs": len(validation_pairs["text"]),
        "audio_trained": "audio" in train_pairs,
        "final_epoch": history[-1],
        "held_out_metrics": metrics,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
