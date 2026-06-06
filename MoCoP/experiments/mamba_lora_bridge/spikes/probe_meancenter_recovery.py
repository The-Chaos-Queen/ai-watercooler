"""Does DC removal (mean-centering the injected bias) recover input-dependence?

Tests fix branch #1 from the collapse diagnosis WITHOUT retraining.

For each v_proj head, computes the 41 bias vectors, then removes a shared DC
component two ways:
  - full-mean: subtract mean over all 41 (upper bound on recovery)
  - leave-one-out: subtract mean over the other 40 (honest: simulates a
    precomputed calibration DC applied to a held-out prompt)

Reports, per head:
  - original cross-prompt cosine (collapsed ~0.95-0.97)
  - residual cross-prompt cosine after DC removal (low == signal exposed)
  - ||residual|| / ||bias|| magnitude retained (how much steering survives;
    if small, alpha must be scaled up to compensate)
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys

import torch
import torch.nn.functional as F

BRIDGE_DIR = r"C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge"
sys.path.insert(0, BRIDGE_DIR)
from models import MambaStateCompressor, ActivationBiasHypernetwork  # noqa: E402

CKPT = os.path.join(BRIDGE_DIR, "cheese_reincarnation_bridge_1.5b_codexfix.pt")
STATES = os.path.join(BRIDGE_DIR, "mamba_layer3_states_v1.pt")
TARGET_DIMS = [(2048, 256)] * 4


def mean_pairwise_cosine(x):
    xn = F.normalize(x.float(), dim=-1)
    sim = xn @ xn.T
    n = sim.shape[0]
    return float((sim.sum() - sim.diag().sum()) / (n * (n - 1)))


def loo_residuals(x):
    """Leave-one-out DC removal: residual_i = x_i - mean(x_{j != i})."""
    n = x.shape[0]
    total = x.sum(dim=0, keepdim=True)
    loo_mean = (total - x) / (n - 1)
    return x - loo_mean


def main():
    blob = torch.load(STATES, map_location="cpu", weights_only=False)
    states = blob["states"].float()
    ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)

    comp = MambaStateCompressor(64, 2560, 1, 2048, target_layer=3).eval()
    comp.load_state_dict(ckpt["compressor_state_dict"])
    hyper = ActivationBiasHypernetwork(2048, TARGET_DIMS, hidden_dim=1024).eval()
    hyper.load_state_dict(ckpt["hypernetwork_state_dict"])

    with torch.no_grad():
        ctx = comp(states)
        hidden = F.silu(hyper.backbone[2](F.silu(hyper.backbone[0](ctx))))
        biases = [head(hidden) for head in hyper.bias_heads]

    print(f"{'head':<6}{'orig cos':>10}{'full-mean cos':>15}{'LOO cos':>10}{'mag retained':>15}")
    print("-" * 56)
    for i, bias in enumerate(biases):
        orig = mean_pairwise_cosine(bias)
        full_resid = bias - bias.mean(dim=0, keepdim=True)
        full_cos = mean_pairwise_cosine(full_resid)
        loo_resid = loo_residuals(bias)
        loo_cos = mean_pairwise_cosine(loo_resid)
        mag = float(full_resid.norm(dim=1).mean() / bias.norm(dim=1).mean())
        print(f"L{12+i:<5}{orig:>10.4f}{full_cos:>15.4f}{loo_cos:>10.4f}{mag:>14.1%}")

    print()
    # Aggregate verdict
    all_orig = sum(mean_pairwise_cosine(b) for b in biases) / len(biases)
    all_loo = sum(mean_pairwise_cosine(loo_residuals(b)) for b in biases) / len(biases)
    all_mag = sum(
        float((b - b.mean(0, keepdim=True)).norm(dim=1).mean() / b.norm(dim=1).mean())
        for b in biases
    ) / len(biases)
    print(f"AVG  original cos = {all_orig:.4f}  ->  LOO-centered cos = {all_loo:.4f}")
    print(f"AVG  steering magnitude retained after DC removal = {all_mag:.1%}")
    print()
    if all_loo < 0.5 and all_orig > 0.9:
        print("VERDICT: DC removal RECOVERS input-dependence. Fix #1 viable without retrain.")
        print(f"         Caveat: only {all_mag:.0%} of steering magnitude survives ->")
        print(f"         compensate by scaling injection alpha up by ~{1/max(all_mag,1e-3):.1f}x.")
    else:
        print("VERDICT: DC removal does NOT cleanly recover input-dependence. Lean to retrain (fix #2/#3).")


if __name__ == "__main__":
    main()
