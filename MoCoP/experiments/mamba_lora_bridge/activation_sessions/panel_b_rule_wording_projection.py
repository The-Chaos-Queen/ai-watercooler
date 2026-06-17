#!/usr/bin/env python3
"""Panel B rule-wording holdout + projection of existing long-conversation states.

Read-only. No bridge, no Qdrant writes.

This is the next blade after the leave-topic-out Panel B result:
- train/test linear disposition readout with held-out topics;
- train/test with held-out rule wording families;
- build synthetic plain-disposition centroids;
- project existing Cassian windowed L3 states onto those centroids.

Caveat: rule wording is still disposition-specific in the synthetic samples, so this
is a stricter lexical-generalization check than leave-topic-out, not final proof of
abstract stance. The long-conversation projection is unlabeled unless a pre-registered
segment-label file is supplied later.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.linear_model import RidgeClassifier
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from transformers import AutoTokenizer, MambaForCausalLM

from panel_b_plain_disposition_hard import MODEL_ID, build_samples, extract


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(F.cosine_similarity(torch.from_numpy(a).flatten().float().unsqueeze(0), torch.from_numpy(b).flatten().float().unsqueeze(0)))


def centroid_map(X: np.ndarray, labels: list[str]) -> dict[str, np.ndarray]:
    labs = sorted(set(labels))
    return {lab: X[np.array(labels) == lab].mean(axis=0) for lab in labs}


def centroid_report(centroids: dict[str, np.ndarray]) -> dict[str, Any]:
    pairs: dict[str, float] = {}
    vals: list[float] = []
    for a, b in combinations(sorted(centroids), 2):
        c = cosine(centroids[a], centroids[b])
        pairs[f"{a}_vs_{b}"] = c
        vals.append(c)
    return {"avg_pairwise_cosine": float(np.mean(vals)), "pairwise_cosines": pairs}


def logo_probe(X: np.ndarray, y: list[str], groups: list[str]) -> dict[str, Any]:
    clf = make_pipeline(StandardScaler(), RidgeClassifier(class_weight="balanced", alpha=1.0))
    logo = LeaveOneGroupOut()
    pred = cross_val_predict(clf, X, y, cv=logo.split(X, y, groups=groups))
    labs = sorted(set(y))
    return {
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "labels": labs,
        "groups": sorted(set(groups)),
        "confusion_matrix": confusion_matrix(y, pred, labels=labs).tolist(),
    }


def nearest_centroid_rows(states: np.ndarray, sample_indices: np.ndarray, centroids: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    labs = sorted(centroids)
    for idx, state in zip(sample_indices.tolist(), states):
        sims = {lab: cosine(state.astype(np.float32), centroids[lab].astype(np.float32)) for lab in labs}
        ordered = sorted(sims.items(), key=lambda kv: kv[1], reverse=True)
        rows.append({
            "sample_index": int(idx),
            "nearest": ordered[0][0],
            "nearest_cosine": float(ordered[0][1]),
            "second": ordered[1][0],
            "second_cosine": float(ordered[1][1]),
            "margin": float(ordered[0][1] - ordered[1][1]),
            "cosines": sims,
        })
    return rows


def summarize_projection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    margins = []
    for r in rows:
        counts[r["nearest"]] = counts.get(r["nearest"], 0) + 1
        margins.append(r["margin"])
    top_margins = sorted(rows, key=lambda r: abs(r["margin"]), reverse=True)[:10]
    return {
        "count_by_nearest": counts,
        "margin_mean": float(np.mean(margins)) if margins else None,
        "margin_std": float(np.std(margins)) if margins else None,
        "top_abs_margins": top_margins,
    }


def load_npz_projection(path: str, centroids: dict[str, np.ndarray]) -> dict[str, Any]:
    z = np.load(path)
    states = z["states"].astype(np.float32)
    sample_indices = z["sample_indices"]
    rows = nearest_centroid_rows(states, sample_indices, centroids)
    return {
        "path": path,
        "n_states": int(states.shape[0]),
        "dim": int(states.shape[1]),
        "rows": rows,
        "summary": summarize_projection(rows),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", default="activation_sessions/panel_b_rule_wording_projection_20260611.json")
    ap.add_argument("--out-md", default="activation_sessions/panel_b_rule_wording_projection_20260611.md")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--project-npz", action="append", default=[])
    args = ap.parse_args()

    start = time.time()
    samples = build_samples()
    layers = [3, 8]
    layer_sets = {"L3": [3], "L8": [8], "L3+L8": [3, 8]}
    labels = [s.disposition_label for s in samples]
    topic_groups = [s.topic_id for s in samples]
    rule_groups = [s.rule_family for s in samples]

    print(f"Loading {MODEL_ID}", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = MambaForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float16).to("cuda").eval()
    layer_states = {l: [] for l in layers}
    token_counts: list[int] = []
    for idx, s in enumerate(samples, 1):
        print(f"[{idx:03d}/{len(samples)}] {s.sample_id} {s.disposition_label} {s.rule_family}", flush=True)
        token_counts.append(len(tok(s.text)["input_ids"]))
        states = extract(model, tok, s.text, layers, args.max_length)
        for l, v in states.items():
            layer_states[l].append(v)

    results: dict[str, Any] = {}
    for name, ls in layer_sets.items():
        X = np.concatenate([np.stack(layer_states[l], axis=0) for l in ls], axis=1)
        norms = np.linalg.norm(X, axis=1)
        cents = centroid_map(X, labels)
        entry: dict[str, Any] = {
            "dim": int(X.shape[1]),
            "norm_mean": float(norms.mean()),
            "norm_std": float(norms.std()),
            "probe_leave_topic_out": logo_probe(X, labels, topic_groups),
            "probe_leave_rule_family_out": logo_probe(X, labels, rule_groups),
            "centroids_disposition": centroid_report(cents),
        }
        if name == "L3" and args.project_npz:
            entry["projections"] = {Path(p).parent.name: load_npz_projection(p, cents) for p in args.project_npz}
        results[name] = entry

    payload = {
        "model_id": MODEL_ID,
        "sample_count": len(samples),
        "token_count_min": min(token_counts),
        "token_count_mean": float(np.mean(token_counts)),
        "token_count_max": max(token_counts),
        "samples": [asdict(s) for s in samples],
        "results": results,
        "duration_s": round(time.time() - start, 2),
    }
    Path(args.out_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Panel B Rule-Wording Holdout + Long-State Projection",
        "",
        f"Samples: `{len(samples)}`",
        f"Tokens min/mean/max: `{min(token_counts)}` / `{np.mean(token_counts):.1f}` / `{max(token_counts)}`",
        "",
    ]
    for name in ["L3", "L8", "L3+L8"]:
        r = results[name]
        lines += [
            f"## {name}",
            f"- dim: `{r['dim']}`",
            f"- norm mean/std: `{r['norm_mean']:.4f}` / `{r['norm_std']:.4f}`",
            f"- leave-topic-out balanced accuracy: `{r['probe_leave_topic_out']['balanced_accuracy']:.3f}`",
            f"- leave-rule-family-out balanced accuracy: `{r['probe_leave_rule_family_out']['balanced_accuracy']:.3f}`",
            f"- disposition centroid avg cosine: `{r['centroids_disposition']['avg_pairwise_cosine']:.4f}`",
            "",
        ]
    proj = results.get("L3", {}).get("projections", {})
    if proj:
        lines += ["## L3 projections of existing long-conversation states", ""]
        for name, pr in proj.items():
            lines += [
                f"### {name}",
                f"- n states: `{pr['n_states']}`",
                f"- nearest counts: `{pr['summary']['count_by_nearest']}`",
                f"- margin mean/std: `{pr['summary']['margin_mean']:.6f}` / `{pr['summary']['margin_std']:.6f}`",
                "- top absolute margins:",
            ]
            for row in pr["summary"]["top_abs_margins"][:5]:
                lines.append(f"  - sample `{row['sample_index']}` -> `{row['nearest']}` margin `{row['margin']:.6f}` cos `{row['nearest_cosine']:.6f}`")
            lines.append("")
    lines += [
        "## Interpretation caution",
        "Leave-rule-family-out is stricter than leave-topic-out, but rule text still differs systematically by disposition. Long-state projection is unlabeled unless segment labels are pre-registered from transcript reading alone.",
    ]
    Path(args.out_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out_json}", flush=True)
    print(f"Wrote {args.out_md}", flush=True)
    print(f"Duration {payload['duration_s']}s", flush=True)


if __name__ == "__main__":
    main()
