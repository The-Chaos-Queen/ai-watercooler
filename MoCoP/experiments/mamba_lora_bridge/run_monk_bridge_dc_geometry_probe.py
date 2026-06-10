#!/usr/bin/env python3
"""Bridge DC-removal geometry/dose probe.

Raw metrics only. No behavior, no Qdrant, no chat server changes.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import torch
import torch.nn.functional as F

from models import ActivationBiasHypernetwork, MambaStateCompressor

TARGET_DIMS = [(2048, 256)] * 4
ALPHAS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2]


def mean_pairwise_cosine(x: torch.Tensor) -> float:
    xn = F.normalize(x.float(), dim=-1)
    sim = xn @ xn.T
    n = sim.shape[0]
    if n <= 1:
        return 0.0
    return float((sim.sum() - sim.diag().sum()) / (n * (n - 1)))


def loo_residuals(x: torch.Tensor) -> torch.Tensor:
    n = x.shape[0]
    total = x.sum(dim=0, keepdim=True)
    loo_mean = (total - x) / max(n - 1, 1)
    return x - loo_mean


def tensor_stats(x: torch.Tensor) -> dict:
    norms = x.float().norm(dim=1)
    return {
        "mean_norm": float(norms.mean()),
        "std_norm": float(norms.std()),
        "min_norm": float(norms.min()),
        "max_norm": float(norms.max()),
        "mean_pairwise_cosine": mean_pairwise_cosine(x),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge", default="cheese_reincarnation_bridge_1.5b_codexfix.pt")
    parser.add_argument("--states", default="mamba_layer3_states_v1.pt")
    parser.add_argument("--output", default="results/monk_variable_probe_20260606/bridge_dc_geometry.json")
    args = parser.parse_args()

    states_blob = torch.load(args.states, map_location="cpu", weights_only=False)
    states = states_blob["states"].float()
    ckpt = torch.load(args.bridge, map_location="cpu", weights_only=False)

    comp = MambaStateCompressor(64, 2560, 1, 2048, target_layer=3).eval()
    comp.load_state_dict(ckpt["compressor_state_dict"])
    hyper = ActivationBiasHypernetwork(2048, TARGET_DIMS, hidden_dim=1024).eval()
    hyper.load_state_dict(ckpt["hypernetwork_state_dict"])

    with torch.no_grad():
        ctx = comp(states)
        hidden = F.silu(hyper.backbone[2](F.silu(hyper.backbone[0](ctx))))
        biases = [head(hidden).float() for head in hyper.bias_heads]

    heads = []
    for idx, bias in enumerate(biases):
        full_resid = bias - bias.mean(dim=0, keepdim=True)
        loo_resid = loo_residuals(bias)
        retained = float(full_resid.norm(dim=1).mean() / bias.norm(dim=1).mean())
        per_alpha = []
        for alpha in ALPHAS:
            scaled = alpha * full_resid
            per_alpha.append({"alpha": alpha, **tensor_stats(scaled)})
        heads.append(
            {
                "head": f"L{12 + idx}:v_proj",
                "original": tensor_stats(bias),
                "full_mean_centered": tensor_stats(full_resid),
                "leave_one_out_centered": tensor_stats(loo_resid),
                "magnitude_retained_fraction": retained,
                "compensating_alpha_factor": (1.0 / retained) if retained > 1e-9 else None,
                "per_alpha_full_mean_centered": per_alpha,
            }
        )

    aggregate = {
        "original_mean_pairwise_cosine_avg": sum(h["original"]["mean_pairwise_cosine"] for h in heads) / len(heads),
        "full_mean_centered_pairwise_cosine_avg": sum(h["full_mean_centered"]["mean_pairwise_cosine"] for h in heads) / len(heads),
        "loo_centered_pairwise_cosine_avg": sum(h["leave_one_out_centered"]["mean_pairwise_cosine"] for h in heads) / len(heads),
        "magnitude_retained_fraction_avg": sum(h["magnitude_retained_fraction"] for h in heads) / len(heads),
    }
    aggregate["compensating_alpha_factor_avg"] = 1.0 / max(aggregate["magnitude_retained_fraction_avg"], 1e-9)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bridge": args.bridge,
        "states": args.states,
        "state_count": int(states.shape[0]),
        "alphas": ALPHAS,
        "aggregate": aggregate,
        "heads": heads,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "aggregate": aggregate}, indent=2))


if __name__ == "__main__":
    main()
