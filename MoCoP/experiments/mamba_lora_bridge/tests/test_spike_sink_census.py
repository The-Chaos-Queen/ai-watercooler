"""Model-free tests for the spike/sink census analysis core (A1, #789/#791).

The numeric core is torch-free, so these validate the census on SYNTHETIC
activations with a planted spike lifecycle and a planted attention sink — no model
load. Only ``capture_forward`` needs torch and is exercised on ML-WS, not here.

    python -m pytest tests/test_spike_sink_census.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mocop_spike_sink_census import (  # noqa: E402
    analyze,
    find_step_layers,
    injection_overlap,
    layer_magnitudes,
    sink_ratio,
    spike_channels,
    token_invariance,
)


def make_hidden_states(n_layers, d_model, *, spike_channel, spike_value,
                       up=4, down=10, seq=6, rng=None):
    """A synthetic residual stream: ordinary O(1) activations everywhere, with a
    massive activation planted on ``spike_channel`` at position 0 for layers
    [up, down) — the paper's step-up / persist / step-down lifecycle."""
    rng = rng or np.random.default_rng(0)
    hs = []
    for L in range(n_layers + 1):  # +1 for the embedding output
        h = rng.standard_normal((seq, d_model)).astype(np.float32)
        if up <= L < down:
            h[0, spike_channel] = spike_value
        hs.append(h)
    return hs


def test_layer_magnitudes_tracks_spike():
    hs = make_hidden_states(12, 64, spike_channel=7, spike_value=3000.0)
    mag = layer_magnitudes(hs)
    assert max(mag["max_abs_pos0"]) >= 3000.0
    # a layer outside [4,10) has no planted spike -> small magnitude
    assert mag["max_abs_pos0"][0] < 100.0


def test_find_step_layers_locates_lifecycle():
    hs = make_hidden_states(16, 64, spike_channel=3, spike_value=2500.0, up=4, down=11)
    step = find_step_layers(layer_magnitudes(hs)["max_abs"])
    assert step["step_up_layer"] == 4
    assert step["step_down_layer"] == 11
    assert step["spike_active_band"] == [4, 11]


def test_spike_channels_identifies_planted_channel():
    hs = make_hidden_states(12, 128, spike_channel=42, spike_value=4000.0)
    sc = spike_channels(hs, topk=3)
    assert sc["channels"][0] == 42
    assert abs(sc["values"][0]) >= 4000.0


def test_token_invariance_near_constant_is_high_cosine():
    # same big channel value across prompts -> cosine ~1, low CoV (implicit bias)
    vals = [[3000.0, 12.0, -8.0], [3010.0, 9.0, -7.0], [2990.0, 11.0, -9.0]]
    inv = token_invariance(vals)
    assert inv["mean_pairwise_cosine"] > 0.999
    assert inv["mean_abs_cov"] < 0.1


def test_sink_ratio_detects_planted_sink():
    # 2 layers, 2 heads, 5 queries, 5 keys. Layer 0: all mass on key 0 (pure sink);
    # layer 1: uniform (no sink).
    sink = np.zeros((2, 5, 5), dtype=np.float32); sink[:, :, 0] = 1.0
    uniform = np.full((2, 5, 5), 0.2, dtype=np.float32)
    ratios = sink_ratio([sink, uniform])
    assert ratios[0] == pytest.approx(1.0)
    assert ratios[1] == pytest.approx(0.2, abs=1e-5)


def test_injection_overlap_flags_band_membership():
    # spike band [4,11); injection layers {29,35,41} are OUTSIDE -> not in band
    step = {"spike_active_band": [4, 11], "step_down_layer": 11}
    max_abs = [1.0] * 48
    ov = injection_overlap(step, [], max_abs)
    assert ov["any_injection_in_spike_band"] is False
    assert ov["all_injection_after_step_down"] is True    # 29,35,41 all > 11
    # and the reverse: a band that swallows the injection layers
    step2 = {"spike_active_band": [5, 40], "step_down_layer": 40}
    ov2 = injection_overlap(step2, [], max_abs)
    assert ov2["any_injection_in_spike_band"] is True     # 29,35 in [5,40]


def test_analyze_end_to_end_synthetic():
    d = 64
    prompts_hs = [make_hidden_states(16, d, spike_channel=9, spike_value=2000.0 + 5 * k,
                                     rng=np.random.default_rng(k)) for k in range(4)]
    # planted sink on 17 attention layers (== len(hidden_states)-1 not required here)
    atts = []
    for _ in range(4):
        layers = []
        for _L in range(16):
            a = np.full((2, 5, 5), 0.1, dtype=np.float32); a[:, :, 0] = 0.6
            layers.append(a)
        atts.append(layers)
    report = analyze(prompts_hs, atts, model_id="synthetic/test", n_layers=16)
    assert report["census_version"] == "spike-sink-census-v1"
    assert report["spike_lifecycle"]["step_up_layer"] == 4
    assert report["spike_channels"]["channels"][0] == 9
    assert report["spike_channels"]["token_invariance_across_prompts"]["mean_pairwise_cosine"] > 0.99
    assert report["mean_sink_ratio"] is not None and report["mean_sink_ratio"] > 0.5


def test_analyze_without_attention():
    prompts_hs = [make_hidden_states(12, 32, spike_channel=1, spike_value=1500.0)]
    report = analyze(prompts_hs, None, model_id="synthetic/noattn", n_layers=12)
    assert report["sink_ratio_per_layer"] is None
    assert report["mean_sink_ratio"] is None
    assert report["spike_lifecycle"]["step_up_layer"] is not None
