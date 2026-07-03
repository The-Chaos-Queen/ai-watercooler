"""CPU-only unit tests for the OpenCLAW #127 DC-removal + RMS-scaling bridge injection.

Tiny synthetic fixtures, no model load. These exercise the two locked operations:

  Op 1 (DC removal): in the bias-apply step, subtract the precomputed cross-context mean
        vector in the raw pre-alpha space (reincarnated_inference.apply_bridge_adjustments).
  Op 2 (RMS-scaling): at the injection site, treat the bias as a direction and rescale it
        to alpha*RMS(output) per row (models.DynamicLoRALinear.forward).

The alpha coupling is the load-bearing invariant: alpha is applied EITHER in the apply
step (fixed path) OR at injection via _bias_alpha (rms path), never both.

Marked `gpu` only because it imports torch (the repo's convention for torch-importing
suites, see conftest.py); it needs no CUDA and runs entirely on CPU. Run with:

    python -m pytest tests/test_dc_rms_inject.py -m gpu -v
"""
from __future__ import annotations

import os

# Handle torch/OMP double-init conflicts before importing torch (mirrors the other
# torch-importing suites and spikes/precompute_dc_vectors.py).
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
from pathlib import Path

import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

pytestmark = pytest.mark.gpu

# Tests live in tests/; the modules live one level up. Inject the parent so
# `from models import ...` resolves without a conftest.py (mirrors test_lesson_memory.py).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from models import DynamicLoRALinear  # noqa: E402  (after sys.path injection)


# ---------- helpers ----------

def _make_dynamic_linear(in_features: int, out_features: int) -> DynamicLoRALinear:
    base = nn.Linear(in_features, out_features)
    base.eval()
    layer = DynamicLoRALinear(base)
    layer.eval()
    return layer


def _mean_pairwise_cosine(x: torch.Tensor) -> float:
    xn = F.normalize(x.float(), dim=-1)
    sim = xn @ xn.T
    n = sim.shape[0]
    return float((sim.sum() - sim.diag().sum()) / (n * (n - 1)))


# ---------- 1. DC subtraction geometry ----------

def test_dc_subtraction_drops_cross_context_cosine_and_retains_small_magnitude():
    """shared_DC + small per-context residual: subtracting the cross-context mean drops
    mean-pairwise-cosine from >0.9 to <0.2 while retaining only a small magnitude fraction.

    Mirrors spikes/precompute_dc_vectors.py: dc = b.mean(dim=0); resid = b - dc.
    """
    torch.manual_seed(0)
    dim, n_ctx = 256, 8
    shared_dc = torch.randn(dim)                 # dominant shared "DC" component
    residuals = torch.randn(n_ctx, dim) * 0.17   # small per-context residual (~17%)
    biases = shared_dc.unsqueeze(0) + residuals  # collapsed near-constant biases

    orig_cos = _mean_pairwise_cosine(biases)

    dc = biases.mean(dim=0)                       # cross-context mean == the DC vector
    resid = biases - dc.unsqueeze(0)
    post_cos = _mean_pairwise_cosine(resid)
    mag_frac = float(resid.norm(dim=-1).mean() / biases.norm(dim=-1).mean())

    assert orig_cos > 0.9, orig_cos
    assert post_cos < 0.2, post_cos
    assert mag_frac < 0.3, mag_frac


# ---------- 2. Flag-off no-op ----------

def test_flag_off_forward_is_byte_identical_to_baseline():
    """With _rms_scale=False (the default), the activation-bias forward is exactly
    output + broadcast(bias) — byte-identical to the pre-flag behavior."""
    torch.manual_seed(0)
    layer = _make_dynamic_linear(in_features=8, out_features=4)
    assert layer._rms_scale is False          # default from __init__
    assert layer._bias_alpha == 1.0

    bias = torch.randn(4, dtype=torch.float16)
    layer.set_activation_bias(bias)
    assert layer._rms_scale is False          # set_activation_bias must not touch config

    x = torch.randn(2, 3, 8)
    out = layer(x)

    base = layer.base_layer(x)
    expected = base + layer._broadcast_output_tensor(bias, base)
    assert torch.equal(out, expected)


# ---------- 3. RMS math ----------

def test_rms_scaling_sets_per_row_norm_and_preserves_direction():
    """_rms_scale=True, _bias_alpha=a: the injected delta has per-row norm ~= a*RMS(output)
    and its direction matches the original bias (cosine ~1)."""
    torch.manual_seed(0)
    in_f, out_f, a = 8, 16, 3.0
    layer = _make_dynamic_linear(in_f, out_f)

    raw_bias = torch.randn(out_f, dtype=torch.float16)
    layer.set_activation_bias(raw_bias)
    layer._rms_scale = True
    layer._bias_alpha = a

    x = torch.randn(2, 5, in_f)
    out_no_bias = layer.base_layer(x)         # forward's `output` (no lora set)
    out = layer(x)
    delta = (out - out_no_bias).float()       # the injected bias contribution

    rms = out_no_bias.float().pow(2).mean(dim=-1, keepdim=True).sqrt()
    expected_norm = (a * rms).squeeze(-1)     # [batch, seq]
    assert torch.allclose(delta.norm(dim=-1), expected_norm, rtol=1e-2, atol=1e-2)

    raw_dir = F.normalize(raw_bias.float(), dim=-1)
    delta_dir = F.normalize(delta.reshape(-1, out_f), dim=-1)
    cos = delta_dir @ raw_dir
    assert torch.all(cos > 0.999), float(cos.min())


# ---------- 4. Alpha exclusivity (apply path) ----------

def test_apply_path_alpha_exclusivity():
    """apply_bridge_adjustments: rms on stores the UNSCALED bias (magnitude independent of
    alpha) with _bias_alpha==alpha; rms off stores the alpha-scaled bias."""
    from reincarnated_inference import apply_bridge_adjustments  # lazy: pulls transformers

    torch.manual_seed(0)
    out_f, n_layers = 6, 3
    layers = [_make_dynamic_linear(4, out_f) for _ in range(n_layers)]
    raws = [torch.randn(1, out_f) for _ in range(n_layers)]  # default mode: list of [1,out]

    # rms OFF, alpha=0.5 -> stored == (0.5 * raw) fp16, _rms_scale False
    apply_bridge_adjustments(
        patched_layers=layers, bridge_adjustments=raws,
        bridge_mode="activation_bias", alpha=0.5, rms_scale=False,
    )
    for layer, raw in zip(layers, raws):
        assert layer._rms_scale is False
        assert torch.equal(layer._dynamic_bias, (0.5 * raw.squeeze(0)).to(torch.float16))

    # rms ON, alpha=2 -> stored == raw fp16 (UNSCALED), _bias_alpha==2, _rms_scale True
    apply_bridge_adjustments(
        patched_layers=layers, bridge_adjustments=raws,
        bridge_mode="activation_bias", alpha=2.0, rms_scale=True,
    )
    stored_a2 = []
    for layer, raw in zip(layers, raws):
        assert layer._rms_scale is True
        assert layer._bias_alpha == 2.0
        assert torch.equal(layer._dynamic_bias, raw.squeeze(0).to(torch.float16))
        stored_a2.append(layer._dynamic_bias.clone())

    # rms ON, alpha=8 -> stored bias UNCHANGED vs alpha=2 (magnitude independent of alpha)
    apply_bridge_adjustments(
        patched_layers=layers, bridge_adjustments=raws,
        bridge_mode="activation_bias", alpha=8.0, rms_scale=True,
    )
    for layer, prev in zip(layers, stored_a2):
        assert layer._bias_alpha == 8.0
        assert torch.equal(layer._dynamic_bias, prev)

    # flipping rms back off restores the alpha-scaled fixed path (config is not sticky)
    apply_bridge_adjustments(
        patched_layers=layers, bridge_adjustments=raws,
        bridge_mode="activation_bias", alpha=0.5, rms_scale=False,
    )
    for layer, raw in zip(layers, raws):
        assert layer._rms_scale is False
        assert torch.equal(layer._dynamic_bias, (0.5 * raw.squeeze(0)).to(torch.float16))


# ---------- 5. dtype / shape ----------

def test_bias_dtype_fp16_and_broadcast_over_batch_seq():
    """fp16 bias, upcast for exact assert, broadcasting over [batch, seq, dim] and [batch, dim]."""
    torch.manual_seed(0)
    in_f, out_f = 8, 5
    layer = _make_dynamic_linear(in_f, out_f)

    bias = torch.randn(out_f, dtype=torch.float16)
    layer.set_activation_bias(bias)
    assert layer._dynamic_bias.dtype == torch.float16

    x3 = torch.randn(4, 7, in_f)
    out3 = layer(x3)
    assert out3.shape == (4, 7, out_f)
    expected3 = layer.base_layer(x3) + bias.float().view(1, 1, -1)
    assert torch.allclose(out3, expected3, atol=1e-3)

    x2 = torch.randn(4, in_f)
    out2 = layer(x2)
    assert out2.shape == (4, out_f)
    expected2 = layer.base_layer(x2) + bias.float().view(1, -1)
    assert torch.allclose(out2, expected2, atol=1e-3)


# ---------- 6. DC removal through the apply path (Op 1 placement) ----------

def test_apply_path_dc_removal_subtracts_vector_before_alpha():
    """dc_remove=True subtracts dc_vectors[i] (the loaded VECTOR) in the raw pre-alpha space,
    then applies alpha in the fixed path: stored == (alpha * (raw - dc)) fp16."""
    from reincarnated_inference import apply_bridge_adjustments

    torch.manual_seed(1)
    out_f, n_layers = 6, 4
    layers = [_make_dynamic_linear(4, out_f) for _ in range(n_layers)]
    raws = [torch.randn(1, out_f) for _ in range(n_layers)]
    dcs = [torch.randn(out_f, dtype=torch.float16) for _ in range(n_layers)]

    apply_bridge_adjustments(
        patched_layers=layers, bridge_adjustments=raws, bridge_mode="activation_bias",
        alpha=1.0, dc_remove=True, dc_vectors=dcs, rms_scale=False,
    )
    for layer, raw, dc in zip(layers, raws, dcs):
        expected = ((raw.squeeze(0) - dc.to(raw.dtype)) * 1.0).to(torch.float16)
        assert torch.equal(layer._dynamic_bias, expected)

    # dc_remove + rms: stored is the UNSCALED (raw - dc), _bias_alpha carries alpha
    apply_bridge_adjustments(
        patched_layers=layers, bridge_adjustments=raws, bridge_mode="activation_bias",
        alpha=4.0, dc_remove=True, dc_vectors=dcs, rms_scale=True,
    )
    for layer, raw, dc in zip(layers, raws, dcs):
        assert layer._rms_scale is True and layer._bias_alpha == 4.0
        assert torch.equal(layer._dynamic_bias, (raw.squeeze(0) - dc.to(raw.dtype)).to(torch.float16))


def test_apply_path_dc_vector_count_mismatch_raises():
    """The guard: len(dc_vectors) must equal the number of patched target layers."""
    from reincarnated_inference import apply_bridge_adjustments

    layers = [_make_dynamic_linear(4, 6) for _ in range(4)]
    raws = [torch.randn(1, 6) for _ in range(4)]
    dcs_wrong = [torch.randn(6, dtype=torch.float16) for _ in range(2)]  # only 2, need 4

    with pytest.raises(ValueError):
        apply_bridge_adjustments(
            patched_layers=layers, bridge_adjustments=raws, bridge_mode="activation_bias",
            alpha=1.0, dc_remove=True, dc_vectors=dcs_wrong,
        )

    with pytest.raises(ValueError):
        apply_bridge_adjustments(
            patched_layers=layers, bridge_adjustments=raws, bridge_mode="activation_bias",
            alpha=1.0, dc_remove=True, dc_vectors=None,
        )
