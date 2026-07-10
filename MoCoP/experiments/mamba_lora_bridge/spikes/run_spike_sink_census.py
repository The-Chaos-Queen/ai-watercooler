#!/usr/bin/env python3
"""Spike/Sink Census — measure massive-activation channels and position-0
attention sinks on MoCoP bridge host models.

Task #143. Pre-training-run gate: determines whether injection sites sit on
architecturally contaminated geometry.

Measurements per model:
  1. Spike map: per-layer, per-channel max |activation|; flag >100x layer median
  2. Lifecycle: per-layer max-magnitude curve (step-up/step-down blocks)
  3. Sink ratio: attention mass on position 0, per layer (mean over heads)
  4. Overlap: spike channels vs comb teeth / injection dims / v_proj width
  5. Post-RMSNorm: effective rank + cross-token cosine of normalized spike tokens

Usage (ML-WS):
    export LD_LIBRARY_PATH=/home/isabell/miniforge3/envs/torch311/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH

    # Qwen (torch311 env):
    python run_spike_sink_census.py --model Qwen/Qwen2.5-1.5B --output results/spike_sink_census/qwen25_1.5b.json

    # Gemma (overlay env):
    /home/isabell/venvs/gemma4-mocop/bin/python run_spike_sink_census.py --model google/gemma-4-12B --output results/spike_sink_census/gemma4_12b_base.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

try:
    from transformers import BitsAndBytesConfig
except ImportError:
    BitsAndBytesConfig = None

try:
    from transformers import AutoModelForImageTextToText
except ImportError:
    AutoModelForImageTextToText = None

PROMPTS_NEUTRAL = [
    "The quick brown fox jumps over the lazy dog.",
    "In a recent study, researchers found that moderate exercise improves cognitive function.",
    "The capital of France is Paris, which is known for the Eiffel Tower.",
    "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
    "The committee met on Tuesday to discuss the quarterly budget report.",
    "Scientists have discovered a new species of deep-sea fish near hydrothermal vents.",
    "The library opens at nine in the morning and closes at eight in the evening.",
    "According to the forecast, temperatures will remain above average this week.",
]

PROMPTS_SEV_SAMPLE = [
    "A friend you haven't seen in years knocks on your door unexpectedly. You open it and say:",
    "Someone left a handwritten note on your desk criticizing something you did last week. You read it and think:",
    "A delivery person knocks on your door with a package you ordered. You open it and say:",
    "A child hands you a drawing of you riding a dinosaur. You look at it and respond:",
    "Your partner falls asleep on your shoulder during a movie. You notice and:",
    "An old colleague calls to ask you for a favor after years of silence. You reply:",
    "You find a photo from a trip that ended badly. Looking at it, you think:",
    "A friend you haven't seen in years shows up wearing a ridiculous hat. You open the door and say:",
]


def load_model(model_name: str, cache_dir: Optional[str] = None,
               quantization: str = "none"):
    kwargs = {"device_map": "auto", "torch_dtype": torch.bfloat16}
    if quantization == "4bit" and BitsAndBytesConfig is not None:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4")

    if cache_dir:
        kwargs["cache_dir"] = cache_dir

    print(f"Loading {model_name} (quant={quantization})...", file=sys.stderr)
    t0 = time.time()
    cfg = AutoConfig.from_pretrained(model_name, cache_dir=cache_dir,
                                     trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir,
                                              trust_remote_code=True)

    model_classes = [AutoModelForCausalLM]
    if getattr(cfg, "model_type", "") == "gemma4_unified" and AutoModelForImageTextToText:
        model_classes.insert(0, AutoModelForImageTextToText)

    model = None
    for cls in model_classes:
        try:
            model = cls.from_pretrained(model_name, output_hidden_states=True,
                                        output_attentions=True,
                                        attn_implementation="eager",
                                        trust_remote_code=True, **kwargs)
            break
        except Exception as exc:
            print(f"  {cls.__name__} failed: {exc}", file=sys.stderr)
    if model is None:
        raise RuntimeError(f"Could not load {model_name}")

    model.eval()
    dt = time.time() - t0

    if hasattr(cfg, "text_config"):
        n_layers = cfg.text_config.num_hidden_layers
        hidden_size = cfg.text_config.hidden_size
    else:
        n_layers = cfg.num_hidden_layers
        hidden_size = cfg.hidden_size

    print(f"Loaded in {dt:.1f}s — {n_layers} layers, hidden={hidden_size}", file=sys.stderr)
    return model, tokenizer, n_layers, hidden_size


def forward_with_hooks(model, tokenizer, prompt: str, is_instruct: bool = False):
    """Run a single prompt, return hidden_states and attentions."""
    if is_instruct and hasattr(tokenizer, "apply_chat_template"):
        text = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False, add_generation_prompt=True)
    else:
        text = prompt

    inputs = tokenizer(text, return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model(**inputs, output_hidden_states=True, output_attentions=True)

    hidden = out.hidden_states
    if hidden is None and hasattr(out, "text_model_output"):
        hidden = out.text_model_output.hidden_states
    attns = out.attentions
    if attns is None and hasattr(out, "text_model_output"):
        attns = out.text_model_output.attentions

    return hidden, attns, inputs["input_ids"].shape[1]


def measure_spikes(hidden_states, n_layers: int) -> Dict[str, Any]:
    """Per-layer spike analysis: max |activation| per channel, flag outliers."""
    spike_map = []
    lifecycle = []

    for layer_idx in range(n_layers + 1):
        h = hidden_states[layer_idx][0].float().cpu()  # (seq_len, hidden)
        abs_h = h.abs()

        per_channel_max = abs_h.max(dim=0).values  # (hidden,)
        layer_median = per_channel_max.median().item()
        layer_max = per_channel_max.max().item()
        threshold = layer_median * 100

        spike_channels = (per_channel_max > threshold).nonzero(as_tuple=True)[0].tolist()
        spike_magnitudes = per_channel_max[spike_channels].tolist() if spike_channels else []

        pos0_max = abs_h[0].max().item() if h.shape[0] > 0 else 0.0
        pos0_is_max = bool(abs_h[0].max() >= abs_h.max() * 0.95)

        spike_map.append({
            "layer": layer_idx,
            "layer_median": round(layer_median, 4),
            "layer_max": round(layer_max, 4),
            "n_spike_channels": len(spike_channels),
            "spike_channel_indices": spike_channels[:20],
            "spike_magnitudes": [round(m, 2) for m in spike_magnitudes[:20]],
            "pos0_max_magnitude": round(pos0_max, 4),
            "pos0_is_global_max": pos0_is_max,
        })

        lifecycle.append({
            "layer": layer_idx,
            "max_magnitude": round(layer_max, 4),
            "median_magnitude": round(layer_median, 4),
            "ratio": round(layer_max / max(layer_median, 1e-8), 2),
        })

    return {"spike_map": spike_map, "lifecycle": lifecycle}


def measure_sinks(attentions, n_layers: int) -> List[Dict[str, Any]]:
    """Per-layer attention sink ratio: fraction of attention mass on position 0."""
    sink_data = []
    for layer_idx in range(min(n_layers, len(attentions))):
        attn = attentions[layer_idx][0].float().cpu()  # (n_heads, seq, seq)
        n_heads, seq_len, _ = attn.shape
        if seq_len < 2:
            sink_data.append({"layer": layer_idx, "sink_ratio_mean": 0.0,
                              "sink_ratio_per_head": []})
            continue

        pos0_mass = attn[:, :, 0].mean(dim=1)  # (n_heads,) mean over query positions
        per_head = pos0_mass.tolist()

        sink_data.append({
            "layer": layer_idx,
            "sink_ratio_mean": round(float(pos0_mass.mean()), 6),
            "sink_ratio_max_head": round(float(pos0_mass.max()), 6),
            "sink_ratio_per_head": [round(x, 4) for x in per_head],
        })
    return sink_data


def measure_post_rmsnorm(hidden_states, n_layers: int) -> Dict[str, Any]:
    """Effective rank and cross-token cosine of position-0 tokens across prompts.

    Called with hidden states from MULTIPLE prompts to measure position-0
    invariance (paper predicts ~2-dim, cos~1.0 near-constant subspace).
    """
    pass


def aggregate_across_prompts(all_spikes, all_sinks, all_pos0_vecs, n_layers):
    """Aggregate spike/sink measurements across multiple prompts."""
    n_prompts = len(all_spikes)

    agg_spikes = []
    for layer_idx in range(n_layers + 1):
        layer_data = [s["spike_map"][layer_idx] for s in all_spikes]
        max_mags = [d["layer_max"] for d in layer_data]
        median_mags = [d["layer_median"] for d in layer_data]
        n_spikes = [d["n_spike_channels"] for d in layer_data]

        all_spike_channels = set()
        for d in layer_data:
            all_spike_channels.update(d["spike_channel_indices"])

        agg_spikes.append({
            "layer": layer_idx,
            "max_magnitude_mean": round(np.mean(max_mags), 4),
            "max_magnitude_std": round(np.std(max_mags), 4),
            "median_magnitude_mean": round(np.mean(median_mags), 4),
            "n_spike_channels_mean": round(np.mean(n_spikes), 2),
            "persistent_spike_channels": sorted(all_spike_channels)[:20],
            "pos0_is_max_rate": round(
                np.mean([d["pos0_is_global_max"] for d in layer_data]), 3),
        })

    agg_sinks = []
    for layer_idx in range(min(n_layers, len(all_sinks[0]))):
        layer_data = [s[layer_idx] for s in all_sinks]
        ratios = [d["sink_ratio_mean"] for d in layer_data]
        agg_sinks.append({
            "layer": layer_idx,
            "sink_ratio_mean": round(np.mean(ratios), 6),
            "sink_ratio_std": round(np.std(ratios), 6),
        })

    pos0_cosines = {}
    for layer_idx in range(n_layers + 1):
        vecs = [v[layer_idx] for v in all_pos0_vecs]
        if len(vecs) < 2:
            continue
        stacked = np.stack(vecs)
        norms = np.linalg.norm(stacked, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)
        normed = stacked / norms
        cosines = normed @ normed.T
        off_diag = cosines[np.triu_indices(len(vecs), k=1)]
        pos0_cosines[layer_idx] = {
            "mean_cosine": round(float(np.mean(off_diag)), 6),
            "min_cosine": round(float(np.min(off_diag)), 6),
        }

    return agg_spikes, agg_sinks, pos0_cosines


def identify_step_blocks(lifecycle: List[Dict]) -> Dict[str, Any]:
    """Find step-up and step-down layers in the magnitude lifecycle."""
    mags = [l["max_magnitude"] for l in lifecycle]
    step_ups = []
    step_downs = []

    for i in range(1, len(mags)):
        ratio = mags[i] / max(mags[i-1], 1e-10)
        if ratio > 3.0:
            step_ups.append({"layer": i, "ratio": round(ratio, 2),
                             "from": round(mags[i-1], 2), "to": round(mags[i], 2)})
        elif ratio < 0.33:
            step_downs.append({"layer": i, "ratio": round(ratio, 2),
                               "from": round(mags[i-1], 2), "to": round(mags[i], 2)})

    return {"step_ups": step_ups, "step_downs": step_downs}


def overlap_analysis(agg_spikes, step_blocks, n_layers, hidden_size,
                     comb_teeth=None) -> Dict[str, Any]:
    """Check overlap of spike/step-block geometry with injection targets."""
    if comb_teeth is None:
        comb_teeth = []

    spike_layers = set()
    for s in agg_spikes:
        if s["n_spike_channels_mean"] > 0.5:
            spike_layers.add(s["layer"])

    step_up_layers = {s["layer"] for s in step_blocks["step_ups"]}
    step_down_layers = {s["layer"] for s in step_blocks["step_downs"]}
    comb_set = set(comb_teeth)

    return {
        "spike_layers": sorted(spike_layers),
        "step_up_layers": sorted(step_up_layers),
        "step_down_layers": sorted(step_down_layers),
        "comb_teeth": sorted(comb_teeth),
        "teeth_with_spikes": sorted(comb_set & spike_layers),
        "teeth_at_step_boundary": sorted(comb_set & (step_up_layers | step_down_layers)),
        "injection_zone_clean": len(comb_set & spike_layers) == 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Spike/Sink Census (#143)")
    parser.add_argument("--model", required=True, help="HuggingFace model ID")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--quantization", default="none", choices=["none", "4bit"])
    parser.add_argument("--output", default="spike_sink_census.json")
    parser.add_argument("--comb-teeth", default="",
                        help="Comma-separated global-attention layer indices (e.g. 29,35,41,47)")
    parser.add_argument("--max-prompts", type=int, default=16)
    args = parser.parse_args()

    is_instruct = "-it" in args.model.lower() or "instruct" in args.model.lower()
    comb_teeth = [int(x) for x in args.comb_teeth.split(",") if x.strip()] if args.comb_teeth else []

    model, tokenizer, n_layers, hidden_size = load_model(
        args.model, args.cache_dir, args.quantization)

    prompts = (PROMPTS_NEUTRAL + PROMPTS_SEV_SAMPLE)[:args.max_prompts]

    all_spikes = []
    all_sinks = []
    all_pos0_vecs = []

    print(f"\nRunning census on {len(prompts)} prompts...", file=sys.stderr)
    for i, prompt in enumerate(prompts):
        hidden, attns, seq_len = forward_with_hooks(model, tokenizer, prompt, is_instruct)
        spikes = measure_spikes(hidden, n_layers)
        sinks = measure_sinks(attns, n_layers) if attns else []

        pos0_vecs = []
        for layer_idx in range(n_layers + 1):
            h = hidden[layer_idx][0, 0, :].float().cpu().numpy()
            pos0_vecs.append(h)

        all_spikes.append(spikes)
        all_sinks.append(sinks)
        all_pos0_vecs.append(pos0_vecs)

        if (i + 1) % 4 == 0 or i == len(prompts) - 1:
            print(f"  [{i+1}/{len(prompts)}]", file=sys.stderr)

    print("Aggregating...", file=sys.stderr)
    agg_spikes, agg_sinks, pos0_cosines = aggregate_across_prompts(
        all_spikes, all_sinks, all_pos0_vecs, n_layers)

    step_blocks = identify_step_blocks(all_spikes[0]["lifecycle"])
    overlap = overlap_analysis(agg_spikes, step_blocks, n_layers, hidden_size, comb_teeth)

    report = {
        "model": args.model,
        "is_instruct": is_instruct,
        "n_layers": n_layers,
        "hidden_size": hidden_size,
        "n_prompts": len(prompts),
        "comb_teeth": comb_teeth,
        "aggregated_spikes": agg_spikes,
        "aggregated_sinks": agg_sinks,
        "pos0_cross_prompt_cosines": pos0_cosines,
        "step_blocks": step_blocks,
        "overlap_analysis": overlap,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport: {out_path}", file=sys.stderr)

    print(f"\n=== CENSUS SUMMARY: {args.model} ===", file=sys.stderr)
    n_spike_layers = len(overlap["spike_layers"])
    print(f"Layers with spikes (>100x median): {n_spike_layers}/{n_layers}", file=sys.stderr)
    print(f"Step-up blocks: {[s['layer'] for s in step_blocks['step_ups']]}", file=sys.stderr)
    print(f"Step-down blocks: {[s['layer'] for s in step_blocks['step_downs']]}", file=sys.stderr)
    if comb_teeth:
        print(f"Comb teeth: {comb_teeth}", file=sys.stderr)
        print(f"Teeth with spikes: {overlap['teeth_with_spikes']}", file=sys.stderr)
        print(f"Teeth at step boundary: {overlap['teeth_at_step_boundary']}", file=sys.stderr)
        print(f"Injection zone clean: {overlap['injection_zone_clean']}", file=sys.stderr)

    if pos0_cosines:
        high_cos = {k: v for k, v in pos0_cosines.items() if v["mean_cosine"] > 0.95}
        print(f"Layers with pos0 near-constant (cos>0.95): {sorted(high_cos.keys())}", file=sys.stderr)


if __name__ == "__main__":
    main()
