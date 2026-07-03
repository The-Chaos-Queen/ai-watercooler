"""Precompute cross-context DC calibration vectors for the --dc-remove bridge flag.

The #517/#518 diagnosis: the bridge's per-context bias collapses to a near-constant
vector (cross-context pairwise cosine ~0.96). The "DC" is the MEAN bias vector across
contexts. Subtracting it exposes the ~17%-magnitude context-sensitive residual
(cosine ~0.10). This script computes that DC per target layer from the calibration
state set and saves it, so the runtime can subtract it in the raw (pre-alpha) space:

    injected = alpha * (raw_bias - DC)

Runs on CPU (compressor + hypernet only; no Mamba encoder, no Qwen). Mirrors
spikes/probe_meancenter_recovery.py so the DC lands in the validated geometry, and
double-checks that the hypernet forward equals the probe's manual reconstruction so
the saved DC lives in the same space that apply_bridge_adjustments injects.
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

BRIDGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRIDGE_DIR))
from models import MambaStateCompressor, ActivationBiasHypernetwork  # noqa: E402

CKPT = BRIDGE_DIR / "cheese_reincarnation_bridge_1.5b_codexfix.pt"
STATES = BRIDGE_DIR / "mamba_layer3_states_v1.pt"
OUT = BRIDGE_DIR / "dc_calibration_v1.pt"
TARGET_DIMS = [(2048, 256)] * 4
TARGET_LAYERS = [12, 13, 14, 15]
PROJ = "v_proj"


def mean_pairwise_cosine(x: torch.Tensor) -> float:
    xn = F.normalize(x.float(), dim=-1)
    sim = xn @ xn.T
    n = sim.shape[0]
    return float((sim.sum() - sim.diag().sum()) / (n * (n - 1)))


def main() -> None:
    blob = torch.load(STATES, map_location="cpu", weights_only=False)
    states = blob["states"].float()
    ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)

    comp = MambaStateCompressor(64, 2560, 1, 2048, target_layer=3).eval()
    comp.load_state_dict(ckpt["compressor_state_dict"])
    hyper = ActivationBiasHypernetwork(2048, TARGET_DIMS, hidden_dim=1024).eval()
    hyper.load_state_dict(ckpt["hypernetwork_state_dict"])

    with torch.no_grad():
        ctx = comp(states)
        biases_fwd = hyper(ctx)  # runtime API: one [N, dim] tensor per target layer
        # Manual reconstruction (matches probe_meancenter_recovery.py).
        hidden = F.silu(hyper.backbone[2](F.silu(hyper.backbone[0](ctx))))
        biases_manual = [head(hidden) for head in hyper.bias_heads]

    n_calib = int(states.shape[0])
    print(f"calibration states: {n_calib}")

    # Consistency: runtime forward vs the diagnosis-validated manual path. If these
    # diverge, the precomputed DC would not match what the runtime injects.
    print("\nforward-vs-manual max|diff| per layer:")
    for i, (bf, bm) in enumerate(zip(biases_fwd, biases_manual)):
        print(f"  L{TARGET_LAYERS[i]}: {float((bf - bm).abs().max()):.3e}")

    biases = list(biases_fwd)
    dc_vectors = [b.mean(dim=0).to(torch.float16) for b in biases]  # cross-context mean, raw space

    print(f"\n{'layer':<8}{'orig cos':>10}{'post-DC cos':>14}{'mag retained':>15}")
    print("-" * 47)
    reproduced = True
    for i, b in enumerate(biases):
        orig = mean_pairwise_cosine(b)
        resid = b - b.mean(dim=0, keepdim=True)
        post = mean_pairwise_cosine(resid)
        mag = float(resid.norm(dim=1).mean() / b.norm(dim=1).mean())
        print(f"L{TARGET_LAYERS[i]:<7}{orig:>10.4f}{post:>14.4f}{mag:>14.1%}")
        if not (orig > 0.9 and post < 0.5):
            reproduced = False

    torch.save(
        {
            "dc_vectors": dc_vectors,  # list[fp16 tensor], one per target layer, raw pre-alpha space
            "target_layers": TARGET_LAYERS,
            "proj": PROJ,
            "target_dims": TARGET_DIMS,
            "n_calib": n_calib,
            "source_ckpt": CKPT.name,
            "source_states": STATES.name,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "cross-context mean bias (raw, pre-alpha) for --dc-remove; subtract before alpha multiply",
        },
        OUT,
    )
    print()
    print(f"saved {len(dc_vectors)} DC vectors -> {OUT.name}")
    print("GEOMETRY REPRODUCED" if reproduced else "WARNING: geometry did NOT reproduce diagnosis")


if __name__ == "__main__":
    main()
