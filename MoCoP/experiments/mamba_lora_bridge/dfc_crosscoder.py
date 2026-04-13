#!/usr/bin/env python3
"""
dfc_crosscoder.py — Dedicated Feature Crosscoder for Mamba-to-Qwen mapping.

Based on Anthropic's cross-architecture model diffing (2026):
https://www.anthropic.com/research/diff-tool

Architecture:
  - Shared dictionary: features both Mamba L3 and Qwen L13 represent
  - Mamba-exclusive section: features only in Mamba (recurrent history, topic memory)
  - Qwen-exclusive section: features only in Qwen (attention structure, output planning)

This replaces the naive cosine alignment approach from task #48.
The crosscoder enables interpretable bridge transfer: instead of mapping
opaque 2560-dim vectors, we map named sparse features.

Training data: paired activations from the same conversation processed
through both Mamba-2.8b (Layer 3 last-token) and Qwen-1.5B (Layer 13 hidden state).

OpenCLAW #86
Author: Anda-Conda
"""

import argparse
import json
import math
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam


class DedicatedFeatureCrosscoder(nn.Module):
    """
    Dedicated Feature Crosscoder (DFC).

    Three feature sections:
      - Shared (n_shared): reconstructed by BOTH decoders
      - Mamba-exclusive (n_mamba_exclusive): only Mamba decoder uses
      - Qwen-exclusive (n_qwen_exclusive): only Qwen decoder uses

    Encoder takes concatenated [mamba_state, qwen_activation] and produces
    all three feature sets. Decoders reconstruct each model's activations
    from the relevant features only.
    """

    def __init__(
        self,
        mamba_dim: int = 2560,
        qwen_dim: int = 1536,       # Qwen 1.5B hidden state at Layer 13
        n_shared: int = 128,
        n_mamba_exclusive: int = 64,
        n_qwen_exclusive: int = 64,
        threshold: float = 0.01,
    ):
        super().__init__()
        self.mamba_dim = mamba_dim
        self.qwen_dim = qwen_dim
        self.n_shared = n_shared
        self.n_mamba_exclusive = n_mamba_exclusive
        self.n_qwen_exclusive = n_qwen_exclusive
        self.n_total = n_shared + n_mamba_exclusive + n_qwen_exclusive
        self.register_buffer("threshold_val", torch.tensor(threshold))

        # Dual encoders: each model gets its own encoder, summed before activation
        # (per Anthropic crosscoder design — avoids forcing implicit alignment)
        self.encoder_mamba = nn.Linear(mamba_dim, self.n_total, bias=True)
        self.encoder_qwen = nn.Linear(qwen_dim, self.n_total, bias=False)  # no double bias

        # Two decoders: reconstruct each model's activations from relevant features
        # Mamba decoder uses: shared + mamba_exclusive
        n_mamba_features = n_shared + n_mamba_exclusive
        self.mamba_decoder = nn.Linear(n_mamba_features, mamba_dim, bias=True)

        # Qwen decoder uses: shared + qwen_exclusive
        n_qwen_features = n_shared + n_qwen_exclusive
        self.qwen_decoder = nn.Linear(n_qwen_features, qwen_dim, bias=True)

        # Initialize decoder columns to unit norm
        with torch.no_grad():
            self.mamba_decoder.weight.data = F.normalize(self.mamba_decoder.weight.data, dim=0)
            self.qwen_decoder.weight.data = F.normalize(self.qwen_decoder.weight.data, dim=0)

    def encode(self, mamba_act: torch.Tensor, qwen_act: torch.Tensor):
        """
        Encode paired activations to sparse feature representation.

        Dual encoder: each model contributes independently, summed before
        activation (per Anthropic crosscoder design).

        Returns:
            features: (batch, n_total) — all features
            shared: (batch, n_shared) — features used by both decoders
            mamba_excl: (batch, n_mamba_exclusive) — Mamba-only features
            qwen_excl: (batch, n_qwen_exclusive) — Qwen-only features
        """
        assert mamba_act.shape[0] == qwen_act.shape[0], (
            f"Batch size mismatch: mamba={mamba_act.shape[0]} vs qwen={qwen_act.shape[0]}"
        )
        # Additive dual encoder: each stream contributes independently
        pre_act = self.encoder_mamba(mamba_act) + self.encoder_qwen(qwen_act)

        # JumpReLU: hard threshold for clean sparsity
        threshold = self.threshold_val.item()
        features = F.relu(pre_act) * (pre_act > threshold).float()

        shared = features[:, :self.n_shared]
        mamba_excl = features[:, self.n_shared:self.n_shared + self.n_mamba_exclusive]
        qwen_excl = features[:, self.n_shared + self.n_mamba_exclusive:]

        return features, shared, mamba_excl, qwen_excl

    def decode(self, shared, mamba_excl, qwen_excl):
        """Reconstruct both models' activations from feature splits."""
        # Mamba reconstruction: shared + mamba_exclusive
        mamba_features = torch.cat([shared, mamba_excl], dim=-1)
        mamba_recon = self.mamba_decoder(mamba_features)

        # Qwen reconstruction: shared + qwen_exclusive
        qwen_features = torch.cat([shared, qwen_excl], dim=-1)
        qwen_recon = self.qwen_decoder(qwen_features)

        return mamba_recon, qwen_recon

    def forward(self, mamba_act: torch.Tensor, qwen_act: torch.Tensor):
        """Full encode-decode pass."""
        features, shared, mamba_excl, qwen_excl = self.encode(mamba_act, qwen_act)
        mamba_recon, qwen_recon = self.decode(shared, mamba_excl, qwen_excl)
        return mamba_recon, qwen_recon, features, shared, mamba_excl, qwen_excl


def dfc_loss(
    mamba_act, qwen_act,
    mamba_recon, qwen_recon,
    features, shared, mamba_excl, qwen_excl,
    l1_weight: float = 1e-3,
    exclusivity_weight: float = 0.1,
):
    """
    DFC training loss.

    Components:
      1. Reconstruction MSE for both models
      2. L1 sparsity on all features
      3. Exclusivity encouragement: penalize shared features that are
         highly active when exclusive features could explain the variance
    """
    # Reconstruction
    mamba_mse = F.mse_loss(mamba_recon, mamba_act)
    qwen_mse = F.mse_loss(qwen_recon, qwen_act)
    recon_loss = mamba_mse + qwen_mse

    # Sparsity
    l1_loss = features.abs().mean()

    # Exclusivity encouragement: shared features should capture what's
    # genuinely shared, not dominate the exclusive sections
    shared_energy = shared.pow(2).sum(dim=-1).mean()
    excl_energy = (mamba_excl.pow(2).sum(dim=-1) + qwen_excl.pow(2).sum(dim=-1)).mean()
    # Penalize if shared energy >> exclusive energy (shared section hogging)
    balance_penalty = F.relu(shared_energy - 3.0 * excl_energy)

    total = recon_loss + l1_weight * l1_loss + exclusivity_weight * balance_penalty

    return total, {
        "total": total.item(),
        "mamba_mse": mamba_mse.item(),
        "qwen_mse": qwen_mse.item(),
        "l1": l1_loss.item(),
        "balance_penalty": balance_penalty.item(),
        "shared_active": (shared > 0).float().mean().item(),
        "mamba_excl_active": (mamba_excl > 0).float().mean().item(),
        "qwen_excl_active": (qwen_excl > 0).float().mean().item(),
    }


def load_paired_data(mamba_path: str, qwen_path: str):
    """Load paired activation tensors from .pt or .npy files."""
    if mamba_path.endswith(".npy"):
        mamba_data = torch.from_numpy(np.load(mamba_path)).float()
    else:
        mamba_data = torch.load(mamba_path, map_location="cpu", weights_only=True).float()

    if qwen_path.endswith(".npy"):
        qwen_data = torch.from_numpy(np.load(qwen_path)).float()
    else:
        qwen_data = torch.load(qwen_path, map_location="cpu", weights_only=True).float()

    assert mamba_data.shape[0] == qwen_data.shape[0], (
        f"Paired data size mismatch: mamba={mamba_data.shape[0]} vs qwen={qwen_data.shape[0]}"
    )

    return mamba_data, qwen_data


def paired_data_quality(mamba_data, qwen_data, min_unique_ratio: float):
    """Basic preflight for repeated-row collapse before DFC training."""
    n_samples = int(mamba_data.shape[0])
    mamba_unique = int(torch.unique(mamba_data, dim=0).shape[0])
    qwen_unique = int(torch.unique(qwen_data, dim=0).shape[0])
    finite = bool(torch.isfinite(mamba_data).all().item() and torch.isfinite(qwen_data).all().item())
    mamba_ratio = mamba_unique / n_samples if n_samples else 0.0
    qwen_ratio = qwen_unique / n_samples if n_samples else 0.0
    return {
        "n_samples": n_samples,
        "finite": finite,
        "min_unique_ratio": min_unique_ratio,
        "passes": finite and mamba_ratio >= min_unique_ratio and qwen_ratio >= min_unique_ratio,
        "unique": {
            "mamba": mamba_unique,
            "qwen": qwen_unique,
            "mamba_ratio": mamba_ratio,
            "qwen_ratio": qwen_ratio,
        },
    }


def analyze_features(model: DedicatedFeatureCrosscoder, mamba_data, qwen_data, top_k: int = 20):
    """Analyze learned features after training."""
    model.eval()
    with torch.no_grad():
        features, shared, mamba_excl, qwen_excl = model.encode(mamba_data, qwen_data)

    analysis = {
        "n_samples": mamba_data.shape[0],
        "n_shared": model.n_shared,
        "n_mamba_exclusive": model.n_mamba_exclusive,
        "n_qwen_exclusive": model.n_qwen_exclusive,
    }

    # Alive features (activated at least once)
    shared_alive = (shared > 0).any(dim=0).sum().item()
    mamba_alive = (mamba_excl > 0).any(dim=0).sum().item()
    qwen_alive = (qwen_excl > 0).any(dim=0).sum().item()

    analysis["alive_features"] = {
        "shared": shared_alive,
        "mamba_exclusive": mamba_alive,
        "qwen_exclusive": qwen_alive,
        "total": shared_alive + mamba_alive + qwen_alive,
    }

    # Feature activation statistics
    analysis["mean_active_per_sample"] = {
        "shared": (shared > 0).float().sum(dim=-1).mean().item(),
        "mamba_exclusive": (mamba_excl > 0).float().sum(dim=-1).mean().item(),
        "qwen_exclusive": (qwen_excl > 0).float().sum(dim=-1).mean().item(),
    }

    # Top shared features by mean activation
    shared_means = shared.mean(dim=0)
    top_shared_idx = shared_means.argsort(descending=True)[:top_k]
    analysis["top_shared_features"] = [
        {"idx": int(idx), "mean_activation": float(shared_means[idx])}
        for idx in top_shared_idx if shared_means[idx] > 0
    ]

    # Top exclusive features
    mamba_means = mamba_excl.mean(dim=0)
    top_mamba_idx = mamba_means.argsort(descending=True)[:top_k]
    analysis["top_mamba_exclusive"] = [
        {"idx": int(idx), "mean_activation": float(mamba_means[idx])}
        for idx in top_mamba_idx if mamba_means[idx] > 0
    ]

    qwen_means = qwen_excl.mean(dim=0)
    top_qwen_idx = qwen_means.argsort(descending=True)[:top_k]
    analysis["top_qwen_exclusive"] = [
        {"idx": int(idx), "mean_activation": float(qwen_means[idx])}
        for idx in top_qwen_idx if qwen_means[idx] > 0
    ]

    return analysis


def train(args):
    print(f"Loading paired data...")
    mamba_data, qwen_data = load_paired_data(args.mamba_data, args.qwen_data)
    print(f"  Mamba: {mamba_data.shape}, Qwen: {qwen_data.shape}")

    quality = paired_data_quality(mamba_data, qwen_data, args.min_unique_ratio)
    unique = quality["unique"]
    print(
        f"  Quality: finite={quality['finite']} "
        f"mamba_unique={unique['mamba']}/{quality['n_samples']} ({unique['mamba_ratio']:.3f}) "
        f"qwen_unique={unique['qwen']}/{quality['n_samples']} ({unique['qwen_ratio']:.3f})"
    )
    if not quality["passes"] and not args.allow_low_uniqueness:
        raise SystemExit(
            "Refusing to train DFC on low-uniqueness or non-finite activations. "
            "Inspect data_quality_report.json or pass --allow-low-uniqueness for explicit diagnostic runs."
        )

    mamba_dim = mamba_data.shape[1]
    qwen_dim = qwen_data.shape[1]

    # Normalize inputs to zero mean, unit variance per stream
    mamba_mean = mamba_data.mean(dim=0, keepdim=True)
    mamba_std = mamba_data.std(dim=0, keepdim=True).clamp(min=1e-6)
    qwen_mean = qwen_data.mean(dim=0, keepdim=True)
    qwen_std = qwen_data.std(dim=0, keepdim=True).clamp(min=1e-6)
    mamba_data = (mamba_data - mamba_mean) / mamba_std
    qwen_data = (qwen_data - qwen_mean) / qwen_std
    print(f"  Normalized: mamba std={mamba_std.mean():.4f}, qwen std={qwen_std.mean():.4f}")

    model = DedicatedFeatureCrosscoder(
        mamba_dim=mamba_dim,
        qwen_dim=qwen_dim,
        n_shared=args.n_shared,
        n_mamba_exclusive=args.n_mamba_exclusive,
        n_qwen_exclusive=args.n_qwen_exclusive,
        threshold=args.threshold,
    )

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    model = model.to(device)
    mamba_data = mamba_data.to(device)
    qwen_data = qwen_data.to(device)

    optimizer = Adam(model.parameters(), lr=args.lr)

    print(f"Training DFC: {model.n_total} features "
          f"({args.n_shared} shared + {args.n_mamba_exclusive} mamba + {args.n_qwen_exclusive} qwen)")
    print(f"Device: {device}, Epochs: {args.epochs}, LR: {args.lr}")

    best_loss = float("inf")
    best_state = None
    t0 = time.time()

    for epoch in range(1, args.epochs + 1):
        model.train()
        mamba_recon, qwen_recon, features, shared, mamba_excl, qwen_excl = model(mamba_data, qwen_data)

        loss, metrics = dfc_loss(
            mamba_data, qwen_data,
            mamba_recon, qwen_recon,
            features, shared, mamba_excl, qwen_excl,
            l1_weight=args.l1_weight,
            exclusivity_weight=args.exclusivity_weight,
        )

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        # Normalize decoder columns (maintain feature directions)
        with torch.no_grad():
            model.mamba_decoder.weight.data = F.normalize(model.mamba_decoder.weight.data, dim=0)
            model.qwen_decoder.weight.data = F.normalize(model.qwen_decoder.weight.data, dim=0)

        if loss.item() < best_loss:
            best_loss = loss.item()
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

        if epoch % args.log_every == 0 or epoch == 1:
            elapsed = time.time() - t0
            print(f"  Epoch {epoch:4d} | loss={metrics['total']:.6f} "
                  f"mamba_mse={metrics['mamba_mse']:.6f} qwen_mse={metrics['qwen_mse']:.6f} "
                  f"l1={metrics['l1']:.4f} balance={metrics['balance_penalty']:.4f} "
                  f"shared_active={metrics['shared_active']:.3f} ({elapsed:.0f}s)")

    elapsed = time.time() - t0
    print(f"\nTraining complete: {elapsed:.1f}s, best loss={best_loss:.6f}")

    # Restore best model before analysis and save so the report matches the artifact.
    if best_state is not None:
        model.load_state_dict(best_state)

    # Analysis
    print(f"\nAnalyzing features...")
    analysis = analyze_features(model, mamba_data, qwen_data)
    analysis["input_quality"] = quality

    alive = analysis["alive_features"]
    print(f"  Alive features: {alive['shared']} shared, "
          f"{alive['mamba_exclusive']} mamba-excl, {alive['qwen_exclusive']} qwen-excl")

    active = analysis["mean_active_per_sample"]
    print(f"  Mean active/sample: {active['shared']:.1f} shared, "
          f"{active['mamba_exclusive']:.1f} mamba-excl, {active['qwen_exclusive']:.1f} qwen-excl")

    # Save
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    torch.save({
        "model_state_dict": model.state_dict(),
        "mamba_mean": mamba_mean.cpu(),
        "mamba_std": mamba_std.cpu(),
        "qwen_mean": qwen_mean.cpu(),
        "qwen_std": qwen_std.cpu(),
        "mamba_dim": mamba_dim,
        "qwen_dim": qwen_dim,
        "n_shared": args.n_shared,
        "n_mamba_exclusive": args.n_mamba_exclusive,
        "n_qwen_exclusive": args.n_qwen_exclusive,
        "threshold": args.threshold,
        "best_loss": best_loss,
        "epochs": args.epochs,
    }, out_dir / "dfc_crosscoder.pt")

    (out_dir / "dfc_analysis.json").write_text(
        json.dumps(analysis, indent=2), encoding="utf-8"
    )

    print(f"\nSaved: {out_dir / 'dfc_crosscoder.pt'}")
    print(f"Analysis: {out_dir / 'dfc_analysis.json'}")
    return analysis


def main():
    parser = argparse.ArgumentParser(description="Train DFC crosscoder for Mamba-to-Qwen feature mapping")
    parser.add_argument("--mamba-data", required=True, help="Mamba L3 activations (.pt or .npy)")
    parser.add_argument("--qwen-data", required=True, help="Qwen L13 activations (.pt or .npy)")
    parser.add_argument("--n-shared", type=int, default=128)
    parser.add_argument("--n-mamba-exclusive", type=int, default=64)
    parser.add_argument("--n-qwen-exclusive", type=int, default=64)
    parser.add_argument("--threshold", type=float, default=0.01)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--l1-weight", type=float, default=1e-3)
    parser.add_argument("--exclusivity-weight", type=float, default=0.1)
    parser.add_argument("--epochs", type=int, default=2000)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-dir", default="dfc_results")
    parser.add_argument("--min-unique-ratio", type=float, default=0.5)
    parser.add_argument("--allow-low-uniqueness", action="store_true",
                        help="Allow diagnostic training even when repeated activation rows indicate bad sampling")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
