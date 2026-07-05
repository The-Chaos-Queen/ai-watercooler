#!/usr/bin/env python3
"""Staircase test for Gemma-4-12B layer disposition formation (pre-registered #735).

Tests Isegrim's prediction: per-layer silhouette score on disposition categories
should show a STAIRCASE (jumps at global-attention teeth) rather than a smooth ramp.

Pre-registered predictions (from #735):
  P1: median layer-over-layer improvement at teeth >= 2x median across local spans
  P2: first reach of 90%-of-max silhouette at or after tooth 29
  P3: instruct staircase absent/attenuated (uniform smear)

Usage (on ML-WS):
    export LD_LIBRARY_PATH=/home/isabell/miniforge3/envs/torch311/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
    /home/isabell/venvs/gemma4-mocop/bin/python run_staircase_test.py --model google/gemma-4-12B
    /home/isabell/venvs/gemma4-mocop/bin/python run_staircase_test.py --model google/gemma-4-12B-it
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

from run_gemma_layer_sweep import (
    PROMPTS, CATEGORIES, load_model as _load_model, collect_hidden_states,
)
import inspect

def load_model(model_name, cache_dir=None, quantization="none"):
    sig = inspect.signature(_load_model)
    if "quantization" in sig.parameters:
        return _load_model(model_name, cache_dir=cache_dir, quantization=quantization)
    return _load_model(model_name, cache_dir=cache_dir)

GLOBAL_LAYERS = {5, 11, 17, 23, 29, 35, 41, 47}


def load_prompt_dataset(dataset_jsonl: Optional[str]) -> tuple[Dict[str, List[str]], List[str], dict]:
    """Load either the original smoke prompts or the SEV JSONL corpus.

    The pre-registered powered rerun for #735 requires >=40 prompts/category
    from fixtures/sev_disposition_v0/sev_disposition_v0.jsonl. Keep the legacy
    built-in prompts as the default so Elf's original smoke remains reproducible.
    """
    if not dataset_jsonl:
        return PROMPTS, CATEGORIES, {
            "source": "built_in_smoke_prompts",
            "path": None,
            "n_items": sum(len(v) for v in PROMPTS.values()),
            "n_per_category": {cat: len(PROMPTS[cat]) for cat in CATEGORIES},
        }

    path = Path(dataset_jsonl)
    prompts: Dict[str, List[str]] = {}
    skeletons_by_cat: Dict[str, set[str]] = {}
    n_items = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            cat = str(row.get("class", "")).strip()
            text = str(row.get("text", "")).strip()
            if not cat or not text:
                raise ValueError(f"{path}:{line_no}: row must contain non-empty class/text")
            prompts.setdefault(cat, []).append(text)
            skeletons_by_cat.setdefault(cat, set()).add(str(row.get("skeleton_id", "")))
            n_items += 1

    categories = sorted(prompts)
    n_per_category = {cat: len(prompts[cat]) for cat in categories}
    metadata = {
        "source": "jsonl",
        "path": str(path),
        "n_items": n_items,
        "n_per_category": n_per_category,
        "n_skeletons_per_category": {cat: len(skeletons_by_cat[cat]) for cat in categories},
        "power_clause_met": all(n >= 40 for n in n_per_category.values()),
    }
    if not metadata["power_clause_met"]:
        print(
            "WARNING: powered rerun clause not met; at least one category has <40 items",
            file=sys.stderr,
        )
    return prompts, categories, metadata


def compute_silhouette_per_layer(all_states: Dict[str, List[np.ndarray]],
                                  categories: List[str],
                                  n_layers: int) -> List[float]:
    """Compute silhouette score at each layer across disposition categories."""
    cat_labels = []
    for i, cat in enumerate(categories):
        cat_labels.extend([i] * len(all_states[cat]))

    labels = np.array(cat_labels)
    scores = []

    for layer in range(n_layers + 1):
        vecs = []
        for cat in categories:
            for state_array in all_states[cat]:
                vecs.append(state_array[layer])
        X = np.stack(vecs)
        X_norm = normalize(X)
        try:
            s = silhouette_score(X_norm, labels, metric="cosine")
        except ValueError:
            s = 0.0
        scores.append(round(float(s), 6))

    return scores


def test_predictions(silhouette: List[float], n_layers: int) -> dict:
    """Evaluate the three pre-registered predictions."""
    sil = np.array(silhouette)

    deltas = np.diff(sil)

    tooth_indices = sorted([i for i in GLOBAL_LAYERS if i <= n_layers])
    local_indices = [i for i in range(1, n_layers + 1) if i not in GLOBAL_LAYERS]

    tooth_deltas = [deltas[i - 1] for i in tooth_indices if i > 0 and i - 1 < len(deltas)]
    local_deltas = [deltas[i - 1] for i in local_indices if i > 0 and i - 1 < len(deltas)]

    median_tooth = float(np.median(tooth_deltas)) if tooth_deltas else 0.0
    median_local = float(np.median(local_deltas)) if local_deltas else 0.0
    ratio_p1 = median_tooth / median_local if abs(median_local) > 1e-10 else float('inf')

    positive_tooth_deltas = [float(x) for x in tooth_deltas if x > 0]
    positive_local_deltas = [float(x) for x in local_deltas if x > 0]
    median_positive_tooth = float(np.median(positive_tooth_deltas)) if positive_tooth_deltas else None
    median_positive_local = float(np.median(positive_local_deltas)) if positive_local_deltas else None
    positive_ratio_p1 = (
        median_positive_tooth / median_positive_local
        if median_positive_tooth is not None
        and median_positive_local is not None
        and abs(median_positive_local) > 1e-10
        else None
    )

    # P1: tooth improvement >= 2x local improvement.
    # Conservative sign guard: a negative median delta is not an "improvement".
    # Without this guard, negative/negative ratios can falsely pass.
    p1_sign_valid = median_tooth > 0 and median_local > 0
    p1_pass = p1_sign_valid and ratio_p1 >= 2.0

    # P2: first reach of 90% of max at or after tooth 29
    max_sil = max(sil[1:])  # skip embedding layer
    threshold_90 = max_sil * 0.9
    first_90 = None
    for i in range(1, len(sil)):
        if sil[i] >= threshold_90:
            first_90 = i
            break
    p2_pass = first_90 is not None and first_90 >= 29

    # P3: tested by comparing base vs instruct (caller compares two runs)
    # Here we just report whether a staircase pattern is visible
    tooth_sil = {i: float(sil[i]) for i in tooth_indices if i < len(sil)}
    local_neighbors = {}
    for t in tooth_indices:
        neighbors = [i for i in [t-1, t+1] if 0 < i < len(sil) and i not in GLOBAL_LAYERS]
        if neighbors:
            local_neighbors[t] = float(np.mean([sil[i] for i in neighbors]))

    tooth_vs_neighbor = {}
    for t in tooth_indices:
        if t in local_neighbors:
            tooth_vs_neighbor[t] = round(tooth_sil[t] - local_neighbors[t], 6)

    return {
        "P1_tooth_median_delta": round(median_tooth, 6),
        "P1_local_median_delta": round(median_local, 6),
        "P1_ratio": round(ratio_p1, 4),
        "P1_sign_valid": p1_sign_valid,
        "P1_positive_tooth_median_delta": round(median_positive_tooth, 6) if median_positive_tooth is not None else None,
        "P1_positive_local_median_delta": round(median_positive_local, 6) if median_positive_local is not None else None,
        "P1_positive_ratio": round(positive_ratio_p1, 4) if positive_ratio_p1 is not None else None,
        "P1_positive_tooth_delta_count": len(positive_tooth_deltas),
        "P1_positive_local_delta_count": len(positive_local_deltas),
        "P1_pass": p1_pass,
        "P2_first_90pct_layer": first_90,
        "P2_pass": p2_pass,
        "tooth_silhouettes": tooth_sil,
        "tooth_vs_neighbor_advantage": tooth_vs_neighbor,
        "max_silhouette": round(float(max_sil), 6),
        "max_silhouette_layer": int(np.argmax(sil[1:]) + 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Staircase test (pre-registered #735)")
    parser.add_argument("--model", default="google/gemma-4-12B",
                        help="HuggingFace model ID")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--quantization", default="none", choices=["none", "4bit"])
    parser.add_argument("--dataset-jsonl", default=None,
                        help="Optional SEV-style JSONL with class/text rows. If omitted, use legacy built-in smoke prompts.")
    parser.add_argument("--output", default=None,
                        help="Output JSON path (default: auto-named)")
    args = parser.parse_args()

    is_instruct = "-it" in args.model.lower() or "instruct" in args.model.lower()
    if args.output is None:
        tag = "it" if is_instruct else "base"
        args.output = f"results/staircase_{tag}.json"

    prompts_by_category, categories, dataset_metadata = load_prompt_dataset(args.dataset_jsonl)

    model, tokenizer, n_layers, hidden_size = load_model(
        args.model, args.cache_dir, quantization=args.quantization)

    all_states: Dict[str, List[np.ndarray]] = {cat: [] for cat in categories}
    total = sum(len(ps) for ps in prompts_by_category.values())
    done = 0

    print(
        f"\nCollecting hidden states for {total} prompts across {len(categories)} categories...",
        file=sys.stderr,
    )
    print(f"Dataset: {dataset_metadata}", file=sys.stderr)
    t0 = time.time()
    for cat, prompts in prompts_by_category.items():
        for prompt in prompts:
            states = collect_hidden_states(model, tokenizer, prompt, n_layers,
                                           is_instruct=is_instruct)
            all_states[cat].append(states)
            done += 1
            if done % 8 == 0 or done == total:
                print(f"  [{done}/{total}]", file=sys.stderr)

    dt = time.time() - t0
    print(f"Collection done in {dt:.1f}s", file=sys.stderr)

    print("Computing per-layer silhouette scores...", file=sys.stderr)
    silhouette = compute_silhouette_per_layer(all_states, categories, n_layers)
    predictions = test_predictions(silhouette, n_layers)

    report = {
        "model": args.model,
        "is_instruct": is_instruct,
        "n_layers": n_layers,
        "hidden_size": hidden_size,
        "quantization": args.quantization,
        "dataset": dataset_metadata,
        "categories": categories,
        "global_layers": sorted(GLOBAL_LAYERS),
        "silhouette_per_layer": silhouette,
        "predictions": predictions,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport written to {out_path}", file=sys.stderr)

    print(f"\n=== STAIRCASE TEST: {args.model} ===", file=sys.stderr)
    print(f"P1 (tooth delta >= 2x local): {'PASS' if predictions['P1_pass'] else 'FAIL'} "
          f"(ratio={predictions['P1_ratio']:.2f}x, tooth={predictions['P1_tooth_median_delta']:.6f}, "
          f"local={predictions['P1_local_median_delta']:.6f})", file=sys.stderr)
    print(f"P2 (90% of max at layer >= 29): {'PASS' if predictions['P2_pass'] else 'FAIL'} "
          f"(first at layer {predictions['P2_first_90pct_layer']})", file=sys.stderr)
    print(f"Max silhouette: {predictions['max_silhouette']:.4f} at layer {predictions['max_silhouette_layer']}",
          file=sys.stderr)
    print(f"\nTooth advantages vs neighbors:", file=sys.stderr)
    for t, adv in sorted(predictions["tooth_vs_neighbor_advantage"].items()):
        marker = " <<<" if adv > 0.01 else ""
        print(f"  Layer {t}: {adv:+.6f}{marker}", file=sys.stderr)


if __name__ == "__main__":
    main()
