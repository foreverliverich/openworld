#!/usr/bin/env python3
"""Train/evaluate latent morphogenetic dynamics from captured organism sessions."""
from __future__ import annotations

import argparse
import json

from chimera.latent_dataset import load_trajectory_sessions, split_trajectory_sessions
from chimera.learned_dynamics import TorchMorphogeneticDynamics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="JSONL path from --latent-trajectory-log")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", default="chimera-v1")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--sample-dt", type=float, default=0.05)
    parser.add_argument("--hidden-dim", type=int, default=512)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()

    sessions = load_trajectory_sessions(args.dataset)
    train, validation = split_trajectory_sessions(
        sessions, validation_fraction=args.validation_fraction, seed=args.seed,
    )
    model = TorchMorphogeneticDynamics(
        hidden_dim=args.hidden_dim, device=args.device,
    )
    history = model.fit(
        train, validation=validation, epochs=args.epochs,
        batch_size=args.batch_size, learning_rate=args.learning_rate,
        sample_dt=args.sample_dt,
    )
    metrics = model.evaluate(validation, dt=args.sample_dt)
    model.save_checkpoint(args.checkpoint)
    print(json.dumps({
        "checkpoint": args.checkpoint,
        "trajectory_sessions": len(sessions),
        "train_sessions": len(train),
        "validation_sessions": len(validation),
        "train_samples": sum(len(sequence) for sequence in train),
        "validation_samples": sum(len(sequence) for sequence in validation),
        "final_epoch": history[-1],
        "held_out_metrics": metrics,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
