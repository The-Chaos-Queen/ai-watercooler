"""
train_sae.py — Train a Sparse Autoencoder on Mamba Layer 3 hidden states.

Decomposes the 2560-dim hidden states into overcomplete sparse features,
revealing which directions in Mamba's state space correspond to interpretable
concepts (disposition, topic, formality, etc.).

Architecture: JumpReLU SAE (per Gemma Scope / Rajamanickam et al.)
  encoder: x -> ReLU(W_enc @ (x - b_dec) + b_enc) * (pre_act > threshold)
  decoder: z -> W_dec @ z + b_dec
  loss: reconstruction MSE + L1 sparsity penalty

Task #44 in OpenCLAW.

Author: Purple (Claude Opus 4.6)
Date: 2026-03-25
"""

import argparse
import json
import math
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam


class SparseAutoencoder(nn.Module):
    """
    JumpReLU Sparse Autoencoder.

    Overcomplete: latent_dim >> input_dim.
    Sparse: L1 penalty encourages few active features per input.
    JumpReLU: hard threshold on pre-activations for cleaner sparsity.
    """

    def __init__(self, input_dim: int, latent_dim: int, threshold: float = 0.01):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.threshold = threshold

        # Encoder
        self.W_enc = nn.Linear(input_dim, latent_dim, bias=True)

        # Decoder (tied bias to encoder for reconstruction centering)
        self.W_dec = nn.Linear(latent_dim, input_dim, bias=True)

        # Initialize decoder columns to unit norm (features as directions)
        with torch.no_grad():
            self.W_dec.weight.data = F.normalize(self.W_dec.weight.data, dim=0)

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Encode input to sparse latent representation.

        Returns:
            z: sparse activations (batch, latent_dim)
            pre_act: pre-threshold activations for analysis
        """
        # Center input around decoder bias
        x_centered = x - self.W_dec.bias
        pre_act = self.W_enc(x_centered)

        # JumpReLU: ReLU + hard threshold
        z = F.relu(pre_act) * (pre_act > self.threshold).float()
        return z, pre_act

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode sparse latents back to input space."""
        return self.W_dec(z)

    def forward(self, x: torch.Tensor) -> dict:
        """Full forward pass with all diagnostics."""
        z, pre_act = self.encode(x)
        x_hat = self.decode(z)

        return {
            "x_hat": x_hat,
            "z": z,
            "pre_act": pre_act,
            "sparsity": (z > 0).float().mean(dim=-1),  # fraction of active features per sample
            "n_active": (z > 0).float().sum(dim=-1),    # number of active features per sample
        }


def reconstruction_loss(x: torch.Tensor, x_hat: torch.Tensor) -> torch.Tensor:
    """Mean squared error per sample, averaged over batch."""
    return ((x - x_hat) ** 2).sum(dim=-1).mean()


def sparsity_loss(z: torch.Tensor) -> torch.Tensor:
    """L1 penalty on latent activations."""
    return z.abs().sum(dim=-1).mean()


def train_sae(
    states: torch.Tensor,
    latent_dim: int = 8192,
    threshold: float = 0.01,
    l1_coeff: float = 5e-3,
    lr: float = 1e-3,
    epochs: int = 500,
    batch_size: int = 0,  # 0 = full batch
    log_every: int = 50,
    normalize_inputs: bool = True,
) -> tuple[SparseAutoencoder, dict]:
    """
    Train a sparse autoencoder on collected Mamba states.

    Args:
        states: (N, d_model) tensor of hidden states
        latent_dim: overcomplete latent dimension (typically 2-8x input_dim)
        threshold: JumpReLU threshold
        l1_coeff: sparsity penalty weight
        lr: learning rate
        epochs: training epochs
        batch_size: 0 for full-batch (recommended for small N)
        log_every: print every N epochs
        normalize_inputs: center and scale inputs before training

    Returns:
        trained SAE model, training history dict
    """
    n_samples, input_dim = states.shape
    print(f"Training SAE: {n_samples} samples, input_dim={input_dim}, latent_dim={latent_dim}")
    print(f"Overcompleteness ratio: {latent_dim / input_dim:.1f}x")
    print(f"L1 coefficient: {l1_coeff}, threshold: {threshold}, LR: {lr}")

    # Normalize
    if normalize_inputs:
        mean = states.mean(dim=0)
        std = states.std(dim=0).clamp(min=1e-8)
        states_norm = (states - mean) / std
    else:
        mean = torch.zeros(input_dim)
        std = torch.ones(input_dim)
        states_norm = states

    # Model
    sae = SparseAutoencoder(input_dim, latent_dim, threshold=threshold)

    optimizer = Adam(sae.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=lr * 0.01)

    if batch_size <= 0:
        batch_size = n_samples

    history = {
        "recon_loss": [],
        "sparse_loss": [],
        "total_loss": [],
        "avg_active_features": [],
        "avg_sparsity": [],
    }

    t_start = time.time()

    for epoch in range(1, epochs + 1):
        # Shuffle
        perm = torch.randperm(n_samples)
        epoch_recon = 0.0
        epoch_sparse = 0.0
        epoch_total = 0.0
        epoch_active = 0.0
        epoch_sparsity = 0.0
        n_batches = 0

        for i in range(0, n_samples, batch_size):
            batch = states_norm[perm[i:i + batch_size]]
            out = sae(batch)

            loss_recon = reconstruction_loss(batch, out["x_hat"])
            loss_sparse = sparsity_loss(out["z"])
            loss_total = loss_recon + l1_coeff * loss_sparse

            optimizer.zero_grad()
            loss_total.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(sae.parameters(), 1.0)

            optimizer.step()

            # Re-normalize decoder columns to unit norm (important for interpretability)
            with torch.no_grad():
                sae.W_dec.weight.data = F.normalize(sae.W_dec.weight.data, dim=0)

            epoch_recon += loss_recon.item()
            epoch_sparse += loss_sparse.item()
            epoch_total += loss_total.item()
            epoch_active += out["n_active"].mean().item()
            epoch_sparsity += out["sparsity"].mean().item()
            n_batches += 1

        # Average over batches
        epoch_recon /= n_batches
        epoch_sparse /= n_batches
        epoch_total /= n_batches
        epoch_active /= n_batches
        epoch_sparsity /= n_batches

        history["recon_loss"].append(epoch_recon)
        history["sparse_loss"].append(epoch_sparse)
        history["total_loss"].append(epoch_total)
        history["avg_active_features"].append(epoch_active)
        history["avg_sparsity"].append(epoch_sparsity)

        scheduler.step()

        if epoch % log_every == 0 or epoch == 1:
            print(
                f"  Epoch {epoch:4d}/{epochs} | "
                f"recon={epoch_recon:.6f} sparse={epoch_sparse:.4f} "
                f"total={epoch_total:.6f} | "
                f"active={epoch_active:.1f}/{latent_dim} ({epoch_sparsity:.4f})"
            )

    elapsed = time.time() - t_start
    print(f"\nTraining complete in {elapsed:.1f}s")

    # Store normalization params for inference
    sae.input_mean = mean
    sae.input_std = std

    return sae, history


def analyze_features(sae: SparseAutoencoder, states: torch.Tensor, metadata: list[dict]):
    """
    Analyze which features activate for which inputs.

    Returns a feature activation matrix and per-feature statistics.
    """
    # Normalize inputs the same way as training
    states_norm = (states - sae.input_mean) / sae.input_std

    with torch.no_grad():
        out = sae(states_norm)
        z = out["z"]  # (N, latent_dim)

    n_samples, latent_dim = z.shape

    # Per-feature statistics
    feature_stats = []
    for f_idx in range(latent_dim):
        activations = z[:, f_idx]
        active_mask = activations > 0

        if active_mask.sum() == 0:
            continue  # dead feature

        active_indices = active_mask.nonzero(as_tuple=True)[0].tolist()
        active_prompts = [metadata[i]["prompt_preview"] for i in active_indices]

        feature_stats.append({
            "feature_idx": f_idx,
            "n_active": int(active_mask.sum()),
            "activation_mean": float(activations[active_mask].mean()),
            "activation_max": float(activations[active_mask].max()),
            "active_fraction": float(active_mask.float().mean()),
            "active_prompts": active_prompts[:5],  # top 5 for readability
        })

    # Sort by selectivity (features that activate for few samples are more interesting)
    feature_stats.sort(key=lambda f: f["n_active"])

    alive = len(feature_stats)
    dead = latent_dim - alive
    print(f"\nFeature Analysis:")
    print(f"  Alive features: {alive}/{latent_dim} ({100*alive/latent_dim:.1f}%)")
    print(f"  Dead features: {dead}/{latent_dim} ({100*dead/latent_dim:.1f}%)")

    if feature_stats:
        activations_per = [f["n_active"] for f in feature_stats]
        print(f"  Activations per alive feature — min: {min(activations_per)}, "
              f"median: {sorted(activations_per)[len(activations_per)//2]}, "
              f"max: {max(activations_per)}")

    # Show most selective features (activate for fewest samples)
    print(f"\n  Top 10 most selective features:")
    for f in feature_stats[:10]:
        print(f"    Feature {f['feature_idx']:5d}: active for {f['n_active']:2d}/{n_samples} samples "
              f"(mean act={f['activation_mean']:.4f})")
        for p in f["active_prompts"][:3]:
            print(f"      -> {p}")

    # Show most universal features (activate for most samples)
    print(f"\n  Top 5 most universal features:")
    for f in feature_stats[-5:]:
        print(f"    Feature {f['feature_idx']:5d}: active for {f['n_active']:2d}/{n_samples} samples")

    return z, feature_stats


def main():
    parser = argparse.ArgumentParser(description="Train SAE on Mamba Layer 3 states.")
    parser.add_argument("--input", type=str, default="mamba_layer3_states_v1.pt",
                        help="Path to collected states .pt file")
    parser.add_argument("--output", type=str, default="sae_mamba_layer3.pt",
                        help="Path to save trained SAE")
    parser.add_argument("--latent-dim", type=int, default=8192,
                        help="SAE latent dimension (overcomplete)")
    parser.add_argument("--threshold", type=float, default=0.01,
                        help="JumpReLU threshold")
    parser.add_argument("--l1-coeff", type=float, default=5e-3,
                        help="L1 sparsity penalty")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--log-every", type=int, default=50)
    parser.add_argument("--analyze", action="store_true",
                        help="Run feature analysis after training")
    args = parser.parse_args()

    # Load states
    data = torch.load(args.input, map_location="cpu", weights_only=False)
    states = data["states"].float()
    metadata = data["metadata"]
    config = data["config"]

    print(f"Loaded {states.shape[0]} states of dim {states.shape[1]}")
    print(f"Source: {config['model_id']}, Layer {config['target_layer']}")

    # Train
    sae, history = train_sae(
        states,
        latent_dim=args.latent_dim,
        threshold=args.threshold,
        l1_coeff=args.l1_coeff,
        lr=args.lr,
        epochs=args.epochs,
        log_every=args.log_every,
    )

    # Save
    save_dict = {
        "model_state_dict": sae.state_dict(),
        "input_mean": sae.input_mean,
        "input_std": sae.input_std,
        "config": {
            "input_dim": sae.input_dim,
            "latent_dim": sae.latent_dim,
            "threshold": sae.threshold,
            "l1_coeff": args.l1_coeff,
            "lr": args.lr,
            "epochs": args.epochs,
            "n_training_samples": states.shape[0],
            "source_model": config["model_id"],
            "source_layer": config["target_layer"],
            "date": "2026-03-25",
            "author": "Purple",
        },
        "history": history,
    }
    torch.save(save_dict, args.output)
    print(f"\nSaved SAE to {args.output}")

    # Analyze
    if args.analyze:
        z, feature_stats = analyze_features(sae, states, metadata)

        # Save analysis
        analysis_path = Path(args.output).with_suffix(".analysis.json")
        analysis = {
            "n_samples": states.shape[0],
            "latent_dim": sae.latent_dim,
            "alive_features": len(feature_stats),
            "dead_features": sae.latent_dim - len(feature_stats),
            "features": feature_stats[:50],  # top 50 most selective
        }
        with open(analysis_path, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"Feature analysis saved to {analysis_path}")


if __name__ == "__main__":
    main()
