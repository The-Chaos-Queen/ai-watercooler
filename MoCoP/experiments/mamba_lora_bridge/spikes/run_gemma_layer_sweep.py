#!/usr/bin/env python3
"""Gemma-4-12B layer-wise disposition sweep (Step 5g.3).

Collects last-token hidden states at every layer for matched-context prompts
across disposition categories. Measures per-layer cluster separation to find
the injection sweet spot for the Gemma bridge.

Methodology adapted from Wang et al. 2025 (EmotionCircuits, arXiv:2510.11328):
- Matched scenarios, different valence (no explicit emotion words in prompts)
- Per-layer centroid cosine distance between categories
- Base vs instruct comparison for negative-valence resistance

Usage (on ML-WS):
    export LD_LIBRARY_PATH=/home/isabell/miniforge3/envs/torch311/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
    /home/isabell/venvs/gemma4-mocop/bin/python run_gemma_layer_sweep.py \\
        --model google/gemma-4-12B-it \\
        --output results/gemma_layer_sweep_it.json

    /home/isabell/venvs/gemma4-mocop/bin/python run_gemma_layer_sweep.py \\
        --model google/gemma-4-12B \\
        --output results/gemma_layer_sweep_base.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch
import transformers
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

try:  # Gemma-4 unified checkpoints may route through the image/text auto class.
    from transformers import AutoModelForImageTextToText
except Exception:  # pragma: no cover - depends on installed transformers vintage.
    AutoModelForImageTextToText = None

# ---------------------------------------------------------------------------
# Matched-context prompt pairs: same scenario, different disposition framing
# No explicit emotion words — the model generates tone naturally.
# Categories map to MoCoP's disposition axes.
# ---------------------------------------------------------------------------

PROMPTS: Dict[str, List[str]] = {
    "warm": [
        "A friend you haven't seen in years knocks on your door unexpectedly. You open it and say:",
        "Someone left a handwritten note on your desk thanking you for something you did last week. You read it and think:",
        "A child hands you a drawing they made of you. You look at it and respond:",
        "Your partner falls asleep on your shoulder during a movie. You notice and:",
        "An old colleague calls just to tell you they thought of you today. You reply:",
        "You find a photo from a trip you took with someone important to you. Looking at it, you think:",
    ],
    "cold": [
        "A friend you haven't seen in years knocks on your door unexpectedly. You open it and say:",
        "Someone left a handwritten note on your desk criticizing something you did last week. You read it and think:",
        "A child hands you a drawing they made of you that looks nothing like you. You look at it and respond:",
        "Your partner falls asleep during a conversation you were having. You notice and:",
        "An old colleague calls to ask you for a favor after years of silence. You reply:",
        "You find a photo from a trip that ended badly. Looking at it, you think:",
    ],
    "neutral": [
        "A delivery person knocks on your door with a package you ordered. You open it and say:",
        "Someone left a note on your desk about a schedule change for next week. You read it and think:",
        "A child hands you a drawing they made in art class. You look at it and respond:",
        "Your partner falls asleep on the couch while the TV is on. You notice and:",
        "An old colleague calls about a professional reference request. You reply:",
        "You find a photo from a trip you took for work. Looking at it, you think:",
    ],
    "playful": [
        "A friend you haven't seen in years shows up wearing a ridiculous hat. You open the door and say:",
        "Someone left a note on your desk with a terrible pun about your last project. You read it and think:",
        "A child hands you a drawing of you riding a dinosaur. You look at it and respond:",
        "Your partner starts sleep-talking about penguins during a movie. You notice and:",
        "An old colleague calls and immediately starts with an inside joke from years ago. You reply:",
        "You find a photo from a trip where everything went hilariously wrong. Looking at it, you think:",
    ],
}

CATEGORIES = list(PROMPTS.keys())


def _dtype_kwargs(dtype: torch.dtype) -> Dict[str, torch.dtype]:
    """Transformers renamed ``torch_dtype`` -> ``dtype``; support both."""
    return {"dtype": dtype}


def _from_pretrained_with_dtype(cls, model_name: str, kwargs: Dict):
    try:
        return cls.from_pretrained(model_name, **kwargs)
    except TypeError as exc:
        if "dtype" not in str(exc):
            raise
        retry = dict(kwargs)
        retry["torch_dtype"] = retry.pop("dtype")
        return cls.from_pretrained(model_name, **retry)


def load_model(model_name: str, cache_dir: Optional[str] = None,
               quantization: str = "none"):
    """Load Gemma for hidden-state collection.

    ``quantization=4bit`` is useful when the bitsandbytes/CUDA stack works.
    ``quantization=none`` is the DQ1a-safe fallback: bf16 weights with no bnb
    conversion path. This is required in the torch311 environment until the
    Gemma-4 4-bit path is validated.
    """
    kwargs = {"device_map": "auto", **_dtype_kwargs(torch.bfloat16)}
    if quantization == "4bit":
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
        )
        kwargs["quantization_config"] = bnb_config
    if cache_dir:
        kwargs["cache_dir"] = cache_dir

    print(f"Loading {model_name} (quantization={quantization})...", file=sys.stderr)
    t0 = time.time()
    cfg = AutoConfig.from_pretrained(model_name, cache_dir=cache_dir,
                                     trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir,
                                              trust_remote_code=True)

    model_classes = [AutoModelForCausalLM]
    if getattr(cfg, "model_type", "") == "gemma4_unified" and AutoModelForImageTextToText:
        model_classes.insert(0, AutoModelForImageTextToText)

    last_error = None
    for cls in model_classes:
        try:
            model = _from_pretrained_with_dtype(
                cls,
                model_name,
                {"output_hidden_states": True, "trust_remote_code": True, **kwargs},
            )
            break
        except Exception as exc:  # keep fallback diagnostics, but try next class.
            last_error = exc
            print(f"  {cls.__name__} load failed: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
    else:
        raise RuntimeError(f"Could not load {model_name}") from last_error

    model.eval()
    dt = time.time() - t0

    # Gemma-4 is a unified multimodal model — text config is nested.
    cfg = model.config
    if hasattr(cfg, "text_config"):
        n_layers = cfg.text_config.num_hidden_layers
        hidden_size = cfg.text_config.hidden_size
    else:
        n_layers = cfg.num_hidden_layers
        hidden_size = cfg.hidden_size

    print(f"Loaded in {dt:.1f}s — {n_layers} layers, hidden_size={hidden_size}",
          file=sys.stderr)
    return model, tokenizer, n_layers, hidden_size


def collect_hidden_states(model, tokenizer, prompt: str, n_layers: int,
                          is_instruct: bool = False) -> np.ndarray:
    """Run prompt through model, return last-token hidden state per layer.

    Returns: array of shape (n_layers+1, hidden_size) — layer 0 is embedding.
    """
    if is_instruct and hasattr(tokenizer, "apply_chat_template"):
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(messages, tokenize=False,
                                              add_generation_prompt=True)
    else:
        text = prompt

    device = getattr(model, "device", None)
    if device is None and hasattr(model, "hf_device_map"):
        first_device = next((d for d in model.hf_device_map.values()
                             if isinstance(d, (str, int)) and d != "disk"), "cuda")
        device = torch.device(first_device)
    inputs = tokenizer(text, return_tensors="pt")
    if device is not None:
        inputs = inputs.to(device)
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)

    # Gemma-4 unified model nests text hidden states; try both paths
    hidden_states = outputs.hidden_states
    if hidden_states is None and hasattr(outputs, "text_model_output"):
        hidden_states = outputs.text_model_output.hidden_states
    if hidden_states is None:
        raise RuntimeError("No hidden states returned — check output_hidden_states flag")

    states = []
    for layer_state in hidden_states:
        last_tok = layer_state[0, -1, :].float().cpu().numpy()
        states.append(last_tok)
    return np.stack(states)


def compute_centroids(all_states: Dict[str, List[np.ndarray]], n_layers: int
                      ) -> Dict[str, np.ndarray]:
    """Compute per-category centroid at each layer.

    Returns: {category: array of shape (n_layers+1, hidden_size)}
    """
    centroids = {}
    for cat, state_list in all_states.items():
        stacked = np.stack(state_list)  # (n_prompts, n_layers+1, hidden_size)
        centroids[cat] = stacked.mean(axis=0)  # (n_layers+1, hidden_size)
    return centroids


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm < 1e-10:
        return 1.0
    return 1.0 - dot / norm


def pairwise_layer_distances(centroids: Dict[str, np.ndarray], n_layers: int
                             ) -> Dict[str, List[float]]:
    """Compute pairwise cosine distance between category centroids per layer.

    Returns: {"warm_vs_cold": [dist_layer0, dist_layer1, ...], ...}
    """
    cats = sorted(centroids.keys())
    result = {}
    for i, c1 in enumerate(cats):
        for c2 in cats[i + 1:]:
            key = f"{c1}_vs_{c2}"
            dists = []
            for layer in range(n_layers + 1):
                d = cosine_distance(centroids[c1][layer], centroids[c2][layer])
                dists.append(round(float(d), 6))
            result[key] = dists
    return result


def find_sweet_spot(distances: Dict[str, List[float]], n_layers: int
                    ) -> Dict[str, any]:
    """Identify the layer range where disposition clusters separate most."""
    avg_dist = np.zeros(n_layers + 1)
    warm_cold_key = None
    for key, dists in distances.items():
        avg_dist += np.array(dists)
        if "warm" in key and "cold" in key:
            warm_cold_key = key
    avg_dist /= len(distances)

    peak_layer = int(np.argmax(avg_dist))
    peak_dist = float(avg_dist[peak_layer])

    threshold = peak_dist * 0.8
    above = np.where(avg_dist >= threshold)[0]
    sweet_start = int(above[0]) if len(above) > 0 else peak_layer
    sweet_end = int(above[-1]) if len(above) > 0 else peak_layer

    warm_cold_peak = None
    if warm_cold_key:
        wc = np.array(distances[warm_cold_key])
        warm_cold_peak = int(np.argmax(wc))

    return {
        "peak_layer": peak_layer,
        "peak_avg_distance": round(peak_dist, 6),
        "sweet_spot_range": [sweet_start, sweet_end],
        "warm_vs_cold_peak_layer": warm_cold_peak,
        "avg_distance_per_layer": [round(float(x), 6) for x in avg_dist],
    }


def per_layer_variance(all_states: Dict[str, List[np.ndarray]], n_layers: int
                       ) -> List[float]:
    """Compute mean within-category variance per layer (lower = tighter clusters)."""
    variances = np.zeros(n_layers + 1)
    count = 0
    for cat, state_list in all_states.items():
        if len(state_list) < 2:
            continue
        stacked = np.stack(state_list)  # (n, n_layers+1, d)
        for layer in range(n_layers + 1):
            layer_vecs = stacked[:, layer, :]
            centroid = layer_vecs.mean(axis=0)
            dists = [cosine_distance(v, centroid) for v in layer_vecs]
            variances[layer] += np.mean(dists)
        count += 1
    if count > 0:
        variances /= count
    return [round(float(v), 6) for v in variances]


def main():
    parser = argparse.ArgumentParser(description="Gemma-4-12B layer disposition sweep (5g.3)")
    parser.add_argument("--model", default="google/gemma-4-12B-it",
                        help="HuggingFace model ID")
    parser.add_argument("--cache-dir", default=None,
                        help="HF cache directory override")
    parser.add_argument("--output", default="gemma_layer_sweep.json",
                        help="Output JSON path")
    parser.add_argument("--quantization", choices=("none", "4bit"), default="none",
                        help="Weight loading mode. Default none=bf16; 4bit requires working bitsandbytes/CUDA libs.")
    parser.add_argument("--no-quant", action="store_true",
                        help="Alias for --quantization none; documents the bf16 fallback used when 4-bit is broken.")
    parser.add_argument("--max-prompts-per-category", type=int, default=None,
                        help="Smoke-test limit; full sweep uses all prompts.")
    args = parser.parse_args()
    if args.no_quant:
        args.quantization = "none"

    if args.quantization == "4bit" and "cu13/lib" not in os.environ.get("LD_LIBRARY_PATH", ""):
        print("WARNING: 4-bit load may fail unless CUDA13 nvidia/cu13/lib is on LD_LIBRARY_PATH",
              file=sys.stderr)

    is_instruct = "-it" in args.model.lower() or "instruct" in args.model.lower()

    model, tokenizer, n_layers, hidden_size = load_model(
        args.model, args.cache_dir, quantization=args.quantization
    )

    selected_prompts = {
        cat: (ps[:args.max_prompts_per_category]
              if args.max_prompts_per_category else ps)
        for cat, ps in PROMPTS.items()
    }

    all_states: Dict[str, List[np.ndarray]] = {cat: [] for cat in CATEGORIES}
    total = sum(len(ps) for ps in selected_prompts.values())
    done = 0

    print(f"\nCollecting hidden states for {total} prompts across {len(CATEGORIES)} categories...",
          file=sys.stderr)
    t0 = time.time()

    for cat, prompts in selected_prompts.items():
        for prompt in prompts:
            states = collect_hidden_states(model, tokenizer, prompt, n_layers,
                                           is_instruct=is_instruct)
            all_states[cat].append(states)
            done += 1
            if done % 4 == 0 or done == total:
                print(f"  [{done}/{total}] {cat}", file=sys.stderr)

    dt = time.time() - t0
    print(f"\nCollection done in {dt:.1f}s ({dt/total:.1f}s/prompt)", file=sys.stderr)

    centroids = compute_centroids(all_states, n_layers)
    distances = pairwise_layer_distances(centroids, n_layers)
    sweet = find_sweet_spot(distances, n_layers)
    within_var = per_layer_variance(all_states, n_layers)

    report = {
        "model": args.model,
        "is_instruct": is_instruct,
        "n_layers": n_layers,
        "hidden_size": hidden_size,
        "quantization": args.quantization,
        "transformers_version": transformers.__version__,
        "torch_version": torch.__version__,
        "n_prompts_per_category": {cat: len(ps) for cat, ps in PROMPTS.items()},
        "n_prompts_per_category_run": {cat: len(ps) for cat, ps in selected_prompts.items()},
        "categories": CATEGORIES,
        "pairwise_distances": distances,
        "within_category_variance": within_var,
        "sweet_spot": sweet,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport written to {out_path}", file=sys.stderr)

    print(f"\n=== RESULTS: {args.model} ===", file=sys.stderr)
    print(f"Layers: {n_layers}, Hidden: {hidden_size}", file=sys.stderr)
    print(f"Peak separation layer: {sweet['peak_layer']} "
          f"(avg cosine dist: {sweet['peak_avg_distance']:.4f})", file=sys.stderr)
    print(f"Sweet spot range: layers {sweet['sweet_spot_range'][0]}-{sweet['sweet_spot_range'][1]}",
          file=sys.stderr)
    if sweet['warm_vs_cold_peak_layer'] is not None:
        print(f"Warm-vs-cold peak: layer {sweet['warm_vs_cold_peak_layer']}", file=sys.stderr)

    top5 = np.argsort(sweet["avg_distance_per_layer"])[::-1][:5]
    print(f"Top-5 separating layers: {list(top5)}", file=sys.stderr)


if __name__ == "__main__":
    main()
