"""Localize the constant-bias collapse in the cheese codexfix bridge.

CPU-only. Runs 41 REAL recorded Mamba layer-3 states through the bridge
stage by stage and measures where cross-sample variance dies.

Two passes:
  A. FRESH (random-init) compressor   -> architectural floor (is LayerNorm the cap?)
  B. TRAINED compressor + hypernetwork -> the actual deployed collapse

Headline metric per stage: mean off-diagonal pairwise cosine among the 41
samples. ~1.0 == collapsed (all samples map to the same direction).
Secondary: signal/constant ratio = ||std_over_samples|| / ||mean_over_samples||.
Low == output dominated by a constant component (context-blind).
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

D_MODEL = 2560
CONTEXT_DIM = 2048
HIDDEN_DIM = 1024
TARGET_DIMS = [(2048, 256), (2048, 256), (2048, 256), (2048, 256)]  # (in,out) per v_proj head


def mean_pairwise_cosine(x: torch.Tensor) -> float:
    """Mean off-diagonal cosine similarity among rows of (N, D)."""
    xn = F.normalize(x.float(), dim=-1)
    sim = xn @ xn.T
    n = sim.shape[0]
    off = (sim.sum() - sim.diag().sum()) / (n * (n - 1))
    return float(off)


def signal_constant_ratio(x: torch.Tensor) -> float:
    """||std_over_samples|| / ||mean_over_samples||. Low == dominated by a constant."""
    x = x.float()
    std_vec = x.std(dim=0)
    mean_vec = x.mean(dim=0)
    return float(std_vec.norm() / (mean_vec.norm() + 1e-8))


def report(label, x):
    print(f"  {label:<34} cos={mean_pairwise_cosine(x):.4f}  sig/const={signal_constant_ratio(x):.4f}")


def main():
    blob = torch.load(STATES, map_location="cpu", weights_only=False)
    states = blob["states"].float()  # (41, 2560)
    n = states.shape[0]
    print(f"Loaded {n} real Mamba layer-3 states, shape {tuple(states.shape)}")
    print(f"Input state norms: min={states.norm(dim=1).min():.3f} "
          f"max={states.norm(dim=1).max():.3f} mean={states.norm(dim=1).mean():.3f}\n")

    print("INPUT (raw mamba states)")
    report("raw state", states)
    print()

    ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)

    # ---- Pass A: FRESH compressor (architectural floor) ----
    print("=" * 64)
    print("PASS A — FRESH random-init compressor (architectural floor)")
    print("=" * 64)
    fresh = MambaStateCompressor(64, D_MODEL, 1, CONTEXT_DIM, target_layer=3).eval()
    with torch.no_grad():
        a_lin = fresh.projection[0](states)
        a_ln = fresh.projection[1](a_lin)
        a_silu = fresh.projection[2](a_ln)
    report("after Linear", a_lin)
    report("after LayerNorm", a_ln)
    report("after SiLU (context)", a_silu)
    print()

    # ---- Pass B: TRAINED compressor + hypernetwork ----
    print("=" * 64)
    print("PASS B — TRAINED compressor + hypernetwork (deployed bridge)")
    print("=" * 64)
    comp = MambaStateCompressor(64, D_MODEL, 1, CONTEXT_DIM, target_layer=3).eval()
    comp.load_state_dict(ckpt["compressor_state_dict"])
    hyper = ActivationBiasHypernetwork(CONTEXT_DIM, TARGET_DIMS, hidden_dim=HIDDEN_DIM).eval()
    hyper.load_state_dict(ckpt["hypernetwork_state_dict"])

    with torch.no_grad():
        b_lin = comp.projection[0](states)
        b_ln = comp.projection[1](b_lin)
        b_ctx = comp.projection[2](b_ln)
        hb0 = F.silu(hyper.backbone[0](b_ctx))
        hidden = F.silu(hyper.backbone[2](hb0))
        biases = [head(hidden) for head in hyper.bias_heads]

    report("after Linear", b_lin)
    report("after LayerNorm", b_ln)
    report("after SiLU (context)", b_ctx)
    report("after backbone (hidden)", hidden)
    print()
    print("  Per-head bias output (the injected steering vectors):")
    for i, bias in enumerate(biases):
        layer = TARGET_DIMS[i]
        print(f"    head {i} (v_proj L{12+i}, out={layer[1]})")
        report(f"      bias", bias)

    print()
    print("  Bias-head constant-vs-input decomposition:")
    for i, (head, bias) in enumerate(zip(hyper.bias_heads, biases)):
        # output = W @ hidden + b. constant part = b ; input-driven part = W@hidden
        b_const = head.bias.detach()
        wh = (hidden @ head.weight.detach().T)  # (N, out), the input-driven part
        wh_var = wh.std(dim=0).norm()           # cross-sample variation
        wh_mean = wh.mean(dim=0).norm()          # mean of input-driven part
        print(f"    head {i}: ||const b||={b_const.norm():.4f}  "
              f"||mean(W@h)||={wh_mean:.4f}  ||std(W@h)||={wh_var:.4f}  "
              f"-> input-variation/total-output = {wh_var / (biases[i].mean(dim=0).norm()+1e-8):.4f}")


if __name__ == "__main__":
    main()
