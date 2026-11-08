"""Trainable Neural-ODE-style morphogenetic dynamics for Latent Language 3.0.

No random/untrained dynamics are ever applied to the live latent state. A model
must pass training and checkpoint validation before evolve() is enabled.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence

from .latent_language import LATENT_DIMENSIONS, LatentLanguageError


class DynamicsTrainingError(RuntimeError):
    pass


def _load_torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise DynamicsTrainingError(
            "Morphogenetic training requires PyTorch. Install the 'latent' extra."
        ) from exc
    return torch, nn


class TorchMorphogeneticDynamics:
    """Learn d(z)/dt from recorded latent trajectories and integrate with RK4."""

    def __init__(
        self, *, state_dim: int = LATENT_DIMENSIONS, hidden_dim: int = 512,
        max_derivative: float = 2.0, seed: int = 17, device: str = "cpu",
    ):
        torch, nn = _load_torch()
        if state_dim != LATENT_DIMENSIONS:
            raise DynamicsTrainingError(
                f"State dimension must match Latent Language schema ({LATENT_DIMENSIONS})"
            )
        if hidden_dim < 32 or max_derivative <= 0:
            raise DynamicsTrainingError("Invalid hidden_dim or max_derivative")
        torch.manual_seed(seed)
        self.torch = torch
        self.device = device
        self.state_dim = state_dim
        self.hidden_dim = hidden_dim
        self.max_derivative = float(max_derivative)
        self.model = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, state_dim),
        ).to(device)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=2e-4, weight_decay=1e-5)
        self.trained = False
        self.training_history: list[dict[str, float]] = []

    def _tensor_sequences(self, sequences: Sequence[Sequence[Sequence[float]]]):
        torch = self.torch
        if not sequences:
            raise DynamicsTrainingError("At least one trajectory is required")
        pairs = []
        for sequence in sequences:
            if len(sequence) < 2:
                continue
            for state, next_state in zip(sequence[:-1], sequence[1:]):
                if len(state) != self.state_dim or len(next_state) != self.state_dim:
                    raise DynamicsTrainingError("Trajectory state has incorrect dimensionality")
                if not all(math.isfinite(float(v)) for v in state) or not all(
                    math.isfinite(float(v)) for v in next_state
                ):
                    raise DynamicsTrainingError("Trajectory contains non-finite values")
                pairs.append((state, next_state))
        if not pairs:
            raise DynamicsTrainingError("Trajectories must contain at least one transition")
        x = torch.tensor([p[0] for p in pairs], dtype=torch.float32, device=self.device)
        y = torch.tensor([p[1] for p in pairs], dtype=torch.float32, device=self.device)
        if float(x.abs().max().item()) > 10.0 or float(y.abs().max().item()) > 10.0:
            raise DynamicsTrainingError("Latent training values must be bounded to [-10, 10]")
        return x, y

    def _derivative(self, state):
        return self.torch.tanh(self.model(state)) * self.max_derivative

    def fit(
        self, trajectories: Sequence[Sequence[Sequence[float]]], *,
        validation: Sequence[Sequence[Sequence[float]]] | None = None,
        epochs: int = 20, batch_size: int = 16, learning_rate: float = 2e-4,
    ) -> list[dict[str, float]]:
        if epochs < 1 or batch_size < 1 or learning_rate <= 0:
            raise DynamicsTrainingError("Invalid training hyperparameters")
        torch = self.torch
        x, y = self._tensor_sequences(trajectories)
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=learning_rate, weight_decay=1e-5
        )
        history = []
        for epoch in range(epochs):
            self.model.train()
            order = torch.randperm(x.shape[0], device=self.device)
            total = 0.0
            count = 0
            for start in range(0, x.shape[0], batch_size):
                indices = order[start:start + batch_size]
                xb, yb = x[indices], y[indices]
                derivative = self._derivative(xb)
                # One-step Euler prediction is the training target for the learned
                # continuous vector field. Smoothness and bounded-energy penalties
                # discourage explosive trajectories.
                predicted = xb + derivative * 0.05
                prediction_loss = torch.mean((predicted - yb) ** 2)
                smoothness = torch.mean(derivative ** 2)
                energy_penalty = torch.mean(torch.relu(
                    torch.linalg.vector_norm(predicted, dim=1) -
                    torch.linalg.vector_norm(xb, dim=1) - 0.25
                ) ** 2)
                loss = prediction_loss + 1e-3 * smoothness + 1e-2 * energy_penalty
                self.optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                total += float(loss.detach().cpu())
                count += 1
            metrics = {"epoch": float(epoch + 1), "train_loss": total / max(1, count)}
            if validation:
                metrics.update({f"validation_{k}": v for k, v in self.evaluate(validation).items()})
            history.append(metrics)
        self.training_history.extend(history)
        self.trained = True
        return history

    def evaluate(
        self, trajectories: Sequence[Sequence[Sequence[float]]]
    ) -> dict[str, float]:
        torch = self.torch
        x, y = self._tensor_sequences(trajectories)
        self.model.eval()
        with torch.inference_mode():
            derivative = self._derivative(x)
            predicted = x + derivative * 0.05
            mse = torch.mean((predicted - y) ** 2)
            derivative_rms = torch.sqrt(torch.mean(derivative ** 2))
            norm_growth = torch.mean(
                torch.linalg.vector_norm(predicted, dim=1) -
                torch.linalg.vector_norm(x, dim=1)
            )
        return {
            "one_step_mse": float(mse.cpu()),
            "derivative_rms": float(derivative_rms.cpu()),
            "mean_norm_growth": float(norm_growth.cpu()),
            "transition_count": float(x.shape[0]),
        }

    def evolve(self, vector: Sequence[float], *, dt: float = 0.05) -> tuple[float, ...]:
        if not self.trained:
            raise DynamicsTrainingError("Untrained morphogenetic dynamics cannot drive live state")
        if len(vector) != self.state_dim or not 0 < dt <= 0.25 or not math.isfinite(dt):
            raise DynamicsTrainingError("Invalid state vector or integration step")
        torch = self.torch
        state = torch.tensor(vector, dtype=torch.float32, device=self.device).reshape(1, -1)
        if not bool(torch.isfinite(state).all().item()):
            raise DynamicsTrainingError("Cannot evolve a non-finite latent state")
        self.model.eval()
        with torch.inference_mode():
            # Classical fourth-order Runge-Kutta over the learned vector field.
            k1 = self._derivative(state)
            k2 = self._derivative(state + 0.5 * dt * k1)
            k3 = self._derivative(state + 0.5 * dt * k2)
            k4 = self._derivative(state + dt * k3)
            result = state + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
            result = torch.clamp(result, -10.0, 10.0)
        return tuple(float(v) for v in result[0].cpu().tolist())

    def save_checkpoint(self, path: str | Path) -> None:
        if not self.trained:
            raise DynamicsTrainingError("Cannot save an untrained dynamics checkpoint")
        self.torch.save({
            "schema_version": 1, "state_dim": self.state_dim,
            "hidden_dim": self.hidden_dim, "max_derivative": self.max_derivative,
            "model": self.model.state_dict(),
            "training_history": self.training_history,
        }, str(path))

    def load_checkpoint(self, path: str | Path) -> None:
        checkpoint = self.torch.load(str(path), map_location=self.device, weights_only=True)
        if checkpoint.get("schema_version") != 1 or checkpoint.get("state_dim") != self.state_dim:
            raise DynamicsTrainingError("Checkpoint schema/state dimension mismatch")
        if checkpoint.get("hidden_dim") != self.hidden_dim:
            raise DynamicsTrainingError("Checkpoint hidden dimension mismatch")
        self.model.load_state_dict(checkpoint["model"], strict=True)
        self.training_history = list(checkpoint.get("training_history", []))
        self.trained = True
