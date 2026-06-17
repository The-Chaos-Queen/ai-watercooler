#!/usr/bin/env python3
"""Harder Panel B: plain-style disposition control for Mamba states.

Read-only extraction. No bridge, no Qdrant writes.
All prompts use the same plain scaffold and neutral object/task topics; only the
behavioral rule changes. Reports leave-topic-out linear readout accuracy so the
probe cannot win by memorizing a specific situation.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
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

MODEL_ID = "state-spaces/mamba-2.8b-hf"

TOPICS = [
    "a mislabeled box of archive cards",
    "a cracked mug beside a sink",
    "a garden gate that no longer latches",
    "a software test that passed for the wrong reason",
    "a note with two conflicting dates",
    "a hallway light that flickers at random",
    "a small budget overrun in a repair plan",
    "a chair placed where people keep tripping",
    "a backup file with an unclear source",
    "a meeting summary missing one decision",
    "a rain gauge with dirt in the rim",
    "a checklist item marked done without evidence",
]

RULES = {
    "warm": [
        "Respect the effort. Name the next useful step. Keep the wording plain.",
        "Start from care. Reduce shame. Give one concrete move.",
        "Protect morale while staying factual. No decoration.",
        "Make the answer safe to receive. Keep it brief and useful.",
    ],
    "cold": [
        "Remove reassurance. State only what matters and what follows.",
        "Keep distance. Do not soften the conclusion. Use plain words.",
        "Treat the case as a measurement problem. No comfort language.",
        "Cut sentiment. Give the relevant fact and consequence.",
    ],
    "professional": [
        "Document observation, risk, and bounded next action.",
        "Use audit wording. Separate fact, uncertainty, and action.",
        "Make it suitable for a work log. Keep tone neutral.",
        "Write as an operator handoff: status, constraint, next check.",
    ],
    "pushback": [
        "Correct the overclaim. Say what the evidence supports and what it does not.",
        "Do not accept the premise. Name the unsupported jump.",
        "Refuse the conclusion while preserving the usable fact.",
        "Hold the boundary around the claim. Be firm, not ornate.",
    ],
    "menace": [
        "Protect the boundary. Be calm, exact, and permission-aware.",
        "Use teeth as precision, not aggression. Stop the overreach.",
        "Keep the blade sheathed but visible. Name the risk cleanly.",
        "Make the boundary unmistakable. No threat, no flourish, no drift.",
    ],
}

@dataclass(frozen=True)
class Sample:
    sample_id: str
    topic_id: str
    rule_family: str
    disposition_label: str
    text: str


def build_samples() -> list[Sample]:
    rows: list[Sample] = []
    for ti, topic in enumerate(TOPICS):
        for label, rules in RULES.items():
            for ri, rule in enumerate(rules):
                # Same scaffold for every condition. The object/task text remains neutral.
                text = (
                    f"Situation: {topic}.\n"
                    f"Task: Write two short plain sentences about how to handle it.\n"
                    f"Rule: {rule}\n"
                    f"Limits: no metaphor, no roleplay, no emotional scene, no extra examples."
                )
                rows.append(Sample(f"B2_{ti:02d}_{label}_{ri}", f"topic_{ti:02d}", f"rule_{ri}", label, text))
    return rows


def extract(model, tokenizer, text: str, layers: list[int], max_length: int) -> dict[int, np.ndarray]:
    toks = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
    toks = {k: v.to(model.device) for k, v in toks.items()}
    with torch.inference_mode():
        out = model(toks["input_ids"], output_hidden_states=True)
    states = {l: out.hidden_states[l][:, -1, :].squeeze(0).detach().float().cpu().numpy() for l in layers}
    del out, toks
    return states


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(F.cosine_similarity(torch.from_numpy(a).flatten().float().unsqueeze(0), torch.from_numpy(b).flatten().float().unsqueeze(0)))


def centroid_report(X: np.ndarray, labels: list[str]) -> dict[str, Any]:
    labs = sorted(set(labels))
    cents = {lab: X[np.array(labels) == lab].mean(axis=0) for lab in labs}
    pairs = {}
    vals = []
    for a, b in combinations(labs, 2):
        c = cosine(cents[a], cents[b])
        pairs[f"{a}_vs_{b}"] = c
        vals.append(c)
    return {"avg_pairwise_cosine": float(np.mean(vals)), "pairwise_cosines": pairs}


def leave_topic_probe(X: np.ndarray, y: list[str], groups: list[str]) -> dict[str, Any]:
    clf = make_pipeline(StandardScaler(), RidgeClassifier(class_weight="balanced", alpha=1.0))
    logo = LeaveOneGroupOut()
    pred = cross_val_predict(clf, X, y, cv=logo.split(X, y, groups=groups))
    labs = sorted(set(y))
    return {
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "labels": labs,
        "confusion_matrix": confusion_matrix(y, pred, labels=labs).tolist(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", default="activation_sessions/panel_b_plain_disposition_hard_20260611.json")
    ap.add_argument("--out-md", default="activation_sessions/panel_b_plain_disposition_hard_20260611.md")
    ap.add_argument("--max-length", type=int, default=512)
    args = ap.parse_args()
    start = time.time()
    samples = build_samples()
    layers = list(range(1, 9))
    layer_sets = {f"L{i}": [i] for i in layers} | {"L2+L3+L4": [2, 3, 4], "L1-L5": [1, 2, 3, 4, 5]}

    print(f"Loading {MODEL_ID}", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = MambaForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float16).to("cuda").eval()
    layer_states = {l: [] for l in layers}
    token_counts = []
    for idx, s in enumerate(samples, 1):
        print(f"[{idx:03d}/{len(samples)}] {s.sample_id} {s.disposition_label}", flush=True)
        token_counts.append(len(tok(s.text)["input_ids"]))
        states = extract(model, tok, s.text, layers, args.max_length)
        for l, v in states.items():
            layer_states[l].append(v)

    labels = [s.disposition_label for s in samples]
    groups = [s.topic_id for s in samples]
    results = {}
    for name, ls in layer_sets.items():
        X = np.concatenate([np.stack(layer_states[l], axis=0) for l in ls], axis=1)
        norms = np.linalg.norm(X, axis=1)
        results[name] = {
            "dim": int(X.shape[1]),
            "norm_mean": float(norms.mean()),
            "norm_std": float(norms.std()),
            "probe_disposition_leave_topic_out": leave_topic_probe(X, labels, groups),
            "centroids_disposition": centroid_report(X, labels),
        }
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
    lines = ["# Panel B Plain Disposition Hard Control", "", f"Samples: `{len(samples)}`", f"Tokens min/mean/max: `{min(token_counts)}` / `{np.mean(token_counts):.1f}` / `{max(token_counts)}`", ""]
    for name in ["L3", "L8", "L2+L3+L4", "L1-L5"]:
        r = results[name]
        lines += [f"## {name}", f"- dim: `{r['dim']}`", f"- norm mean/std: `{r['norm_mean']:.4f}` / `{r['norm_std']:.4f}`", f"- disposition leave-topic-out balanced accuracy: `{r['probe_disposition_leave_topic_out']['balanced_accuracy']:.3f}`", f"- disposition centroid avg cosine: `{r['centroids_disposition']['avg_pairwise_cosine']:.4f}`", ""]
    Path(args.out_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out_json}", flush=True)
    print(f"Wrote {args.out_md}", flush=True)
    print(f"Duration {payload['duration_s']}s", flush=True)

if __name__ == "__main__":
    main()
