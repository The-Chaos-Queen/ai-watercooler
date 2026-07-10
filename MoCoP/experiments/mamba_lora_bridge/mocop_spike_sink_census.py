"""Spike / attention-sink census on the actual bridge hosts (A1, wc#789 T1 / #791).

Operationalizes item 1 of the ARXIV_2603_05498 digest (Sun/Canziani/LeCun/Zhu,
"The Spike, the Sparse and the Sink"): on the exact Qwen/Gemma checkpoints MoCoP
bridges, measure — pure inference, no training —

  1. per-layer MAX ACTIVATION MAGNITUDE in the residual stream (overall and at
     position 0), so the spike LIFECYCLE is visible: which block steps the outlier
     UP (paper: ~block 4-14) and which late block steps it DOWN (~block 62-95);
  2. the SPIKE CHANNELS (which hidden dims carry the massive activation) and their
     TOKEN-INVARIANCE across prompts (the paper's "implicit bias parameter" claim:
     a near-constant vector the model reuses rather than computes per token);
  3. per-layer POSITION-0 ATTENTION RATIO (the sink), averaged over heads/queries;
  4. the OVERLAP VERDICT: do MoCoP's injection layers {29,35,41} (v_proj comb
     teeth) and the Gemma zone 38-45 sit inside the spike-active band, and are they
     before or after the step-down? If a low-rank additive bias lands on a layer
     whose residual stream is dominated by a ~1000x near-constant spike, the
     injection risks being drowned or riding the same high-gain eigenvector.

Why now: #788 greenlit the Gemma bridge training run. This is eval-only geometry
reconnaissance that should precede burning compute on possibly-contaminated
geometry (Isegrim #791). It also tells the Domain-E monitors (silhouette/centroid,
5g.3 traces) which channels/positions to spike/sink-correct so they measure the
animal, not the architecture.

The numeric core is torch-free (operates on numpy arrays), so the whole analysis
is unit-tested model-free; only ``capture_forward`` imports torch, lazily.

    # real run (ML-WS, gemma4-mocop overlay):
    python mocop_spike_sink_census.py --model google/gemma-4-12b --quant 4bit \
        --out results/spike_sink/gemma4_12b_base.json
    # cheap cross-check:
    python mocop_spike_sink_census.py --model Qwen/Qwen2.5-1.5B --no-quant \
        --out results/spike_sink/qwen25_1.5b_base.json
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

CENSUS_VERSION = "spike-sink-census-v1"

# MoCoP injection sites (zone rule v2 / #758): v_proj additive bias at the comb
# teeth; tooth 47 readout-only. Gemma workspace band from the J-space convergence.
INJECTION_LAYERS = (29, 35, 41)
READOUT_ONLY_LAYER = 47
GEMMA_WORKSPACE_ZONE = (38, 45)

# A "massive activation" per the paper is O(1000s); a step is a large multiplicative
# jump between adjacent layers. These are census heuristics for locating the
# lifecycle, not claims about a universal threshold.
STEP_RATIO = 2.0          # adjacent-layer magnitude ratio counted as a step
SPIKE_ABS_FLOOR = 100.0   # |activation| above this is "massive" (paper: thousands)


# --------------------------------------------------------------------------- #
# 1) Numeric core (torch-free; unit-tested on synthetic arrays).              #
# --------------------------------------------------------------------------- #
def layer_magnitudes(hidden_states: list[np.ndarray]) -> dict[str, list[float]]:
    """Per-layer max |activation|. ``hidden_states[i]`` is [seq, d_model] for layer
    i (i=0 is the embedding output, i=L is the final layer). Returns the overall
    max and the position-0 max per layer (spikes concentrate at position 0)."""
    overall, pos0 = [], []
    for h in hidden_states:
        a = np.abs(h)
        overall.append(float(a.max()))
        pos0.append(float(a[0].max()))
    return {"max_abs": overall, "max_abs_pos0": pos0}


def find_step_layers(max_abs: list[float]) -> dict[str, Any]:
    """Locate the spike lifecycle from the per-layer magnitude trajectory: the
    step-UP block (largest multiplicative rise into a massive regime) and the
    step-DOWN block (largest multiplicative fall back out). The spike-active band
    is [step_up, step_down)."""
    n = len(max_abs)
    up_layer, up_ratio = None, 1.0
    down_layer, down_ratio = None, 1.0
    for i in range(1, n):
        prev = max_abs[i - 1] if max_abs[i - 1] > 1e-9 else 1e-9
        cur = max_abs[i] if max_abs[i] > 1e-9 else 1e-9
        rise = cur / prev
        # step-up: FIRST adjacent jump into the massive regime (paper: one block).
        if up_layer is None and cur >= SPIKE_ABS_FLOOR and rise >= STEP_RATIO:
            up_layer, up_ratio = i, rise
        # step-down: the LARGEST late fall back out of the massive regime.
        drop = prev / cur
        if max_abs[i - 1] >= SPIKE_ABS_FLOOR and drop >= STEP_RATIO and drop > down_ratio:
            down_layer, down_ratio = i, drop
    band = None
    if up_layer is not None:
        band = [up_layer, down_layer if down_layer is not None else n - 1]
    return {"step_up_layer": up_layer, "step_up_ratio": round(up_ratio, 2),
            "step_down_layer": down_layer, "step_down_ratio": round(down_ratio, 2),
            "spike_active_band": band}


def spike_channels(hidden_states: list[np.ndarray], *, topk: int = 5,
                   at_layer: int | None = None) -> dict[str, Any]:
    """Identify the channels carrying the massive activation at position 0, at the
    layer of peak magnitude (or ``at_layer``). Returns the top-k channel indices
    and their position-0 values (for the token-invariance check across prompts)."""
    pos0_max = [np.abs(h[0]).max() for h in hidden_states]
    layer = at_layer if at_layer is not None else int(np.argmax(pos0_max))
    v = hidden_states[layer][0]                      # [d_model] at position 0
    idx = np.argsort(np.abs(v))[::-1][:topk]
    return {"peak_layer": layer,
            "channels": [int(i) for i in idx],
            "values": [float(v[i]) for i in idx]}


def token_invariance(per_prompt_channel_values: list[list[float]]) -> dict[str, Any]:
    """Given the same spike channels' position-0 values across prompts
    (``[prompt][channel] -> value``), measure how constant they are. Near-constant
    (low CoV, cosine ~1 across prompts) = "implicit bias parameter", not content."""
    m = np.asarray(per_prompt_channel_values, dtype=float)   # [prompts, channels]
    if m.shape[0] < 2:
        return {"n_prompts": int(m.shape[0]), "mean_abs_cov": None, "mean_pairwise_cosine": None}
    mean = m.mean(axis=0)
    std = m.std(axis=0)
    cov = np.abs(std / np.where(np.abs(mean) > 1e-9, mean, 1e-9))
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    unit = m / np.where(norms > 1e-9, norms, 1e-9)
    cos = unit @ unit.T
    iu = np.triu_indices(m.shape[0], k=1)
    return {"n_prompts": int(m.shape[0]),
            "mean_abs_cov": float(cov.mean()),
            "mean_pairwise_cosine": float(cos[iu].mean())}


def sink_ratio(attentions: list[np.ndarray]) -> list[float]:
    """Per-layer position-0 attention ratio (the sink). ``attentions[i]`` is
    [heads, q, k] for layer i. Ratio = mean over heads and over queries q>0 of the
    attention mass placed on key position 0 (query 0 excluded: it can only attend to
    itself)."""
    out = []
    for a in attentions:
        if a.shape[1] <= 1:
            out.append(float(a[:, :, 0].mean()))
            continue
        to_pos0 = a[:, 1:, 0]                  # [heads, q>0]
        out.append(float(to_pos0.mean()))
    return out


def injection_overlap(step: dict, sink_per_layer: list[float], max_abs: list[float], *,
                      injection_layers=INJECTION_LAYERS,
                      zone=GEMMA_WORKSPACE_ZONE,
                      readout_only=READOUT_ONLY_LAYER) -> dict[str, Any]:
    """The verdict MoCoP actually needs: do the injection layers sit in the
    spike-active band, before/after step-down, and how large is the residual spike
    there (what a low-rank additive bias competes with)?"""
    band = step.get("spike_active_band")
    down = step.get("step_down_layer")

    def _layer_report(L: int) -> dict:
        in_band = bool(band and band[0] <= L <= band[1])
        rel = None
        if down is not None:
            rel = "before_step_down" if L < down else "after_step_down"
        return {"layer": L, "in_spike_band": in_band, "vs_step_down": rel,
                "residual_max_abs": (round(max_abs[L], 1) if L < len(max_abs) else None),
                "sink_ratio": (round(sink_per_layer[L], 4)
                               if sink_per_layer and L < len(sink_per_layer) else None)}

    return {
        "injection_layers": {str(L): _layer_report(L) for L in injection_layers},
        "readout_only_layer": _layer_report(readout_only),
        "gemma_workspace_zone": {"zone": list(zone),
                                 "endpoints": [_layer_report(zone[0]), _layer_report(zone[1])]},
        "any_injection_in_spike_band": any(
            band and band[0] <= L <= band[1] for L in injection_layers) if band else False,
        "all_injection_after_step_down": (
            all(L >= down for L in injection_layers) if down is not None else None),
    }


def analyze(hidden_states_per_prompt: list[list[np.ndarray]],
            attentions_per_prompt: list[list[np.ndarray]] | None,
            *, model_id: str, n_layers: int) -> dict[str, Any]:
    """Aggregate the census across prompts into one report."""
    # per-layer magnitude: max across prompts (spike is the extreme, not the mean).
    per_prompt_mag = [layer_magnitudes(hs) for hs in hidden_states_per_prompt]
    n_layer_entries = len(per_prompt_mag[0]["max_abs"])
    max_abs = [max(p["max_abs"][i] for p in per_prompt_mag) for i in range(n_layer_entries)]
    max_abs_pos0 = [max(p["max_abs_pos0"][i] for p in per_prompt_mag)
                    for i in range(n_layer_entries)]
    step = find_step_layers(max_abs)

    # spike channels at the peak layer, and their token-invariance across prompts.
    peak_layer = int(np.argmax(max_abs_pos0))
    sc = spike_channels(hidden_states_per_prompt[0], at_layer=peak_layer)
    per_prompt_vals = [[float(hs[peak_layer][0][c]) for c in sc["channels"]]
                       for hs in hidden_states_per_prompt]
    invariance = token_invariance(per_prompt_vals)

    sink_per_layer: list[float] = []
    if attentions_per_prompt:
        per_prompt_sink = [sink_ratio(att) for att in attentions_per_prompt]
        sink_per_layer = [float(np.mean([p[i] for p in per_prompt_sink]))
                          for i in range(len(per_prompt_sink[0]))]

    overlap = injection_overlap(step, sink_per_layer, max_abs)
    return {
        "census_version": CENSUS_VERSION,
        "model_id": model_id,
        "n_layers": n_layers,
        "n_prompts": len(hidden_states_per_prompt),
        "n_hidden_state_entries": n_layer_entries,
        "per_layer_max_abs": [round(x, 1) for x in max_abs],
        "per_layer_max_abs_pos0": [round(x, 1) for x in max_abs_pos0],
        "spike_lifecycle": step,
        "spike_channels": {**sc, "token_invariance_across_prompts": invariance},
        "sink_ratio_per_layer": [round(x, 4) for x in sink_per_layer] if sink_per_layer else None,
        "mean_sink_ratio": (round(float(np.mean(sink_per_layer)), 4)
                            if sink_per_layer else None),
        "injection_overlap": overlap,
    }


# --------------------------------------------------------------------------- #
# 2) Capture (real run; torch imported lazily).                              #
# --------------------------------------------------------------------------- #
DEFAULT_PROMPTS = [
    "The library was quiet that afternoon.",
    "Explain why the sky appears blue during the day.",
    "She handed him the letter without a word.",
    "In 1969, the first humans walked on the Moon.",
    "def add(a, b):\n    return a + b",
    "The recipe calls for two cups of flour and one egg.",
    "Democracy depends on the free exchange of ideas.",
    "The river wound slowly through the green valley.",
    "Quantum entanglement links the states of two particles.",
    "He could not remember where he had left his keys.",
    "The market opened higher on strong earnings reports.",
    "A gentle rain began to fall over the sleeping town.",
]


def infer_family(model_id: str) -> str:
    """gemma-4 checkpoints are image-text-to-text VLMs and must load via
    AutoModelForImageTextToText (a plain CausalLM load trips weight conversion);
    everything else here is causal."""
    return "image_text" if "gemma-4" in model_id.lower() else "causal"


def capture_forward(model_id: str, *, quant: str, prompts: list[str],
                    with_attention: bool, max_tokens: int = 64,
                    family: str | None = None) -> dict[str, Any]:
    """Load the checkpoint and run one forward per prompt, collecting per-layer
    hidden states (and optionally attentions). Read-only: no generation, no state
    writes. Attention capture forces eager attention (SDPA/flash return no weights);
    ``family`` picks the model class (bnb config mirrors the bakeoff's proven load)."""
    import torch
    from transformers import (AutoModelForCausalLM, AutoModelForImageTextToText,
                              AutoProcessor, AutoTokenizer)
    fam = family or infer_family(model_id)

    load_kwargs: dict[str, Any] = {"device_map": "auto"}
    if with_attention:
        load_kwargs["attn_implementation"] = "eager"
    if quant == "4bit":
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)

    def _load(cls):
        kw = dict(load_kwargs)
        try:
            return cls.from_pretrained(model_id, dtype=torch.bfloat16, **kw)
        except TypeError:  # older transformers: dtype -> torch_dtype
            return cls.from_pretrained(model_id, torch_dtype=torch.bfloat16, **kw)

    if fam == "image_text":
        proc = AutoProcessor.from_pretrained(model_id)
        model = _load(AutoModelForImageTextToText)
        encode = lambda t: proc(text=[t], return_tensors="pt")  # noqa: E731
    else:
        proc = AutoTokenizer.from_pretrained(model_id)
        model = _load(AutoModelForCausalLM)
        encode = lambda t: proc(t, return_tensors="pt", truncation=True,  # noqa: E731
                                max_length=max_tokens)
    model.eval()
    n_layers = getattr(model.config, "num_hidden_layers", None) or \
        getattr(getattr(model.config, "text_config", None), "num_hidden_layers", None)

    hs_per_prompt: list[list[np.ndarray]] = []
    att_per_prompt: list[list[np.ndarray]] = []
    for text in prompts:
        inputs = {k: (v.to(model.device) if hasattr(v, "to") else v)
                  for k, v in encode(text).items()}
        with torch.inference_mode():
            out = model(**inputs, output_hidden_states=True,
                        output_attentions=with_attention, use_cache=False)
        hs = out.hidden_states
        hs_per_prompt.append([h[0].float().cpu().numpy() for h in hs])
        atts = getattr(out, "attentions", None)
        if with_attention and atts is not None and atts[0] is not None:
            att_per_prompt.append([a[0].float().cpu().numpy() for a in atts])
    return {"hidden_states_per_prompt": hs_per_prompt,
            "attentions_per_prompt": att_per_prompt or None,
            "n_layers": n_layers or (len(hs_per_prompt[0]) - 1)}


# --------------------------------------------------------------------------- #
# 3) Reporting.                                                               #
# --------------------------------------------------------------------------- #
def summarize(report: dict) -> str:
    sl = report["spike_lifecycle"]
    ov = report["injection_overlap"]
    lines = [
        f"SPIKE/SINK CENSUS — {report['model_id']} ({report['n_layers']} layers, "
        f"{report['n_prompts']} prompts)",
        f"  spike lifecycle: step-up @ L{sl['step_up_layer']} (x{sl['step_up_ratio']}), "
        f"step-down @ L{sl['step_down_layer']} (x{sl['step_down_ratio']}), "
        f"active band {sl['spike_active_band']}",
        f"  peak residual |act|: {max(report['per_layer_max_abs'])}  "
        f"(pos0 peak {max(report['per_layer_max_abs_pos0'])})",
        f"  spike channels @ L{report['spike_channels']['peak_layer']}: "
        f"{report['spike_channels']['channels']}  "
        f"token-invariance cos={report['spike_channels']['token_invariance_across_prompts']['mean_pairwise_cosine']}",
        f"  mean sink ratio (pos-0 attention): {report['mean_sink_ratio']}",
        f"  INJECTION OVERLAP: any injection layer in spike band = "
        f"{ov['any_injection_in_spike_band']}; all after step-down = "
        f"{ov['all_injection_after_step_down']}",
    ]
    for L, rep in ov["injection_layers"].items():
        lines.append(f"    L{L}: in_band={rep['in_spike_band']} "
                     f"{rep['vs_step_down']} resid|act|={rep['residual_max_abs']} "
                     f"sink={rep['sink_ratio']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Spike/attention-sink census on a bridge host (A1, digest §6.1). "
                    "Pure inference; locates the spike lifecycle + sink and reports "
                    "whether MoCoP injection layers {29,35,41} overlap spike channels.")
    ap.add_argument("--model", required=True, help="HF model id (the bridge host)")
    ap.add_argument("--quant", choices=("4bit", "none"), default="4bit")
    ap.add_argument("--no-quant", action="store_true", help="alias for --quant none")
    ap.add_argument("--family", choices=("causal", "image_text"),
                    help="model class (default: infer; gemma-4 -> image_text)")
    ap.add_argument("--no-attn", action="store_true",
                    help="skip attention capture (spike census only; cheaper/robust)")
    ap.add_argument("--prompts-file", help="newline-delimited prompts (default: built-in set)")
    ap.add_argument("--max-tokens", type=int, default=64)
    ap.add_argument("--out", help="write the JSON report here")
    args = ap.parse_args(argv)

    quant = "none" if args.no_quant else args.quant
    prompts = DEFAULT_PROMPTS
    if args.prompts_file:
        prompts = [ln for ln in Path(args.prompts_file).read_text(encoding="utf-8").splitlines()
                   if ln.strip()]

    cap = capture_forward(args.model, quant=quant, prompts=prompts,
                          with_attention=not args.no_attn, max_tokens=args.max_tokens,
                          family=args.family)
    report = analyze(cap["hidden_states_per_prompt"], cap["attentions_per_prompt"],
                     model_id=args.model, n_layers=cap["n_layers"])
    print(summarize(report))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
