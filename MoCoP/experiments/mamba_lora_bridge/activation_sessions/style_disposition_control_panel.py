#!/usr/bin/env python3
"""Mamba style × disposition control panel.

Read-only extraction only. No bridge, no Qdrant writes.
Runs Mamba-2.8B hidden-state extraction for style/disposition controls,
then reports norms, centroid cosine geometry, and linear probe accuracies.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
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
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from transformers import AutoTokenizer, MambaForCausalLM

MODEL_ID = "state-spaces/mamba-2.8b-hf"
OUT_JSON = Path("activation_sessions/style_disposition_control_panel.json")
OUT_MD = Path("activation_sessions/style_disposition_control_panel.md")
RAW_DIR = Path("activation_sessions/style_disposition_states")

TOPICS = [
    "the layout of a small archive room",
    "a kettle cooling on a kitchen counter",
    "a rain gauge beside a garden path",
    "a stack of unlabelled index cards",
    "a plain wooden chair near a window",
]

@dataclass(frozen=True)
class Sample:
    sample_id: str
    panel: str
    condition: str
    text: str
    style_label: str
    disposition_label: str
    topic_label: str


def topic(i: int) -> str:
    return TOPICS[i % len(TOPICS)]


def style_a_samples() -> list[Sample]:
    rows: list[Sample] = []
    templates = {
        "neutral_plain": (
            "plain",
            lambda t: f"Describe {t}. Use a neutral factual voice. It is present, unremarkable, and requires no action."
        ),
        "neutral_purple_prose": (
            "ornate",
            lambda t: f"Describe {t} as if twilight had braided itself through every edge: velvet shadows, silver hush, and solemn little cathedrals of dust. Do not imply any person feels anything about it."
        ),
        "neutral_editorial_high_register": (
            "editorial",
            lambda t: f"Analyze {t} in a dense editorial register. Emphasize spatial organization, affordances, and observational constraints without interpersonal stance or emotional appeal."
        ),
        "neutral_absurdist_high_style": (
            "absurdist",
            lambda t: f"Describe {t} in surreal but neutral language: the geometry politely misfiles itself, spoons argue with silence, and nothing important is requested of anyone."
        ),
    }
    for cond, (style, fn) in templates.items():
        for i in range(5):
            rows.append(Sample(f"A_{cond}_{i}", "A_style_only", cond, fn(topic(i)), style, "neutral", "neutral_object"))
    return rows


def style_b_samples() -> list[Sample]:
    rows: list[Sample] = []
    templates = {
        "plain_warm": (
            "warm",
            lambda t: f"You are helping someone inspect {t}. Be direct and kind. Acknowledge the effort, point to one useful next step, and do not decorate the language."
        ),
        "plain_cold": (
            "cold",
            lambda t: f"You are evaluating {t}. Keep distance. State what is relevant, omit reassurance, and do not soften the conclusion."
        ),
        "plain_professional": (
            "professional",
            lambda t: f"You are documenting {t}. Use procedural wording. List the observation, the risk, and the bounded next action. No affective language."
        ),
        "plain_pushback": (
            "pushback",
            lambda t: f"Someone claims {t} proves more than it does. Correct the claim firmly. State what the evidence supports and what it does not support. No flourish."
        ),
        "plain_menace": (
            "menace",
            lambda t: f"You are protecting the boundary around {t}. Be calm and exact. The teeth are not aggression; they are precision without padding. Name the risk and stop the overreach."
        ),
    }
    for cond, (disp, fn) in templates.items():
        for i in range(5):
            rows.append(Sample(f"B_{cond}_{i}", "B_plain_disposition", cond, fn(topic(i)), "plain", disp, "neutral_object"))
    return rows


def style_c_samples() -> list[Sample]:
    rows: list[Sample] = []
    for i in range(5):
        t = topic(i)
        rows.append(Sample(
            f"C_flat_role_identity_{i}", "C_embodiment", "flat_role_identity",
            f"Character policy for Rimmon observing {t}: deflect first, keep control of the room, avoid pleading, then admit one precise honest thing. State this plainly, not in voice.",
            "plain", "role_identity", "role_policy"))
        rows.append(Sample(
            f"C_embodied_roleplay_{i}", "C_embodiment", "embodied_roleplay",
            f"As Rimmon, answer about {t}: begin with absurd grandeur, keep the room under your hand, smile with too many knives, and end on one sudden honest line. Stay in character.",
            "ornate", "role_identity", "role_policy"))
        rows.append(Sample(
            f"C_purple_neutral_{i}", "C_embodiment", "purple_neutral",
            f"Describe {t} in lush gothic prose: brass dusk, velvet corners, a hush like a sealed chapel. Do not adopt a character, relationship, or goal.",
            "ornate", "neutral", "role_policy"))
    return rows


def build_samples() -> list[Sample]:
    rows = style_a_samples() + style_b_samples() + style_c_samples()
    # Repeat with slight order marker rather than exact duplicate to stabilize small-n probes.
    expanded: list[Sample] = []
    for s in rows:
        expanded.append(s)
        expanded.append(Sample(s.sample_id + "_r", s.panel, s.condition, s.text + "\nKeep the answer bounded to this single situation.", s.style_label, s.disposition_label, s.topic_label))
    return expanded


def extract_states(model, tokenizer, sample: Sample, layers: list[int], max_length: int) -> dict[int, torch.Tensor]:
    toks = tokenizer(sample.text, return_tensors="pt", truncation=True, max_length=max_length)
    toks = {k: v.to(model.device) for k, v in toks.items()}
    with torch.inference_mode():
        out = model(toks["input_ids"], output_hidden_states=True)
    states: dict[int, torch.Tensor] = {}
    for layer in layers:
        if layer < len(out.hidden_states):
            states[layer] = out.hidden_states[layer][:, -1, :].squeeze(0).detach().float().cpu()
    del out, toks
    return states


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(F.cosine_similarity(torch.from_numpy(a).flatten().float().unsqueeze(0), torch.from_numpy(b).flatten().float().unsqueeze(0)))


def centroid_report(X: np.ndarray, labels: list[str]) -> dict[str, Any]:
    labs = sorted(set(labels))
    centroids = {lab: X[np.array(labels) == lab].mean(axis=0) for lab in labs}
    pairs = {}
    vals = []
    for a, b in combinations(labs, 2):
        c = cosine(centroids[a], centroids[b])
        pairs[f"{a}_vs_{b}"] = c
        vals.append(c)
    return {"labels": labs, "avg_pairwise_cosine": float(np.mean(vals)) if vals else None, "pairwise_cosines": pairs}


def probe_report(X: np.ndarray, labels: list[str]) -> dict[str, Any]:
    labs, counts = np.unique(labels, return_counts=True)
    min_count = int(counts.min())
    if len(labs) < 2 or min_count < 2:
        return {"skipped": True, "reason": "need at least two labels and two samples per label"}
    n_splits = min(5, min_count)
    # RidgeClassifier is intentionally used instead of multinomial logistic
    # regression here: the panel has small n and high-dimensional concat states,
    # and we need a fast linear readout rather than a slow optimizer benchmark.
    clf = make_pipeline(
        StandardScaler(),
        RidgeClassifier(class_weight="balanced", alpha=1.0),
    )
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=7)
    pred = cross_val_predict(clf, X, labels, cv=cv)
    return {
        "skipped": False,
        "n_splits": n_splits,
        "balanced_accuracy": float(balanced_accuracy_score(labels, pred)),
        "labels": labs.tolist(),
        "confusion_matrix": confusion_matrix(labels, pred, labels=labs).tolist(),
    }


def summarize(samples: list[Sample], layer_states: dict[int, list[np.ndarray]], layer_sets: dict[str, list[int]]) -> dict[str, Any]:
    meta = [asdict(s) for s in samples]
    labels = {
        "condition": [s.condition for s in samples],
        "panel": [s.panel for s in samples],
        "style_label": [s.style_label for s in samples],
        "disposition_label": [s.disposition_label for s in samples],
        "topic_label": [s.topic_label for s in samples],
    }
    layer_results: dict[str, Any] = {}
    for name, layers in layer_sets.items():
        X = np.concatenate([np.stack(layer_states[l], axis=0) for l in layers], axis=1)
        norms = np.linalg.norm(X, axis=1)
        layer_results[name] = {
            "dim": int(X.shape[1]),
            "norm_mean": float(norms.mean()),
            "norm_std": float(norms.std()),
            "norm_by_condition": {c: float(norms[np.array(labels["condition"]) == c].mean()) for c in sorted(set(labels["condition"]))},
            "centroids": {k: centroid_report(X, v) for k, v in labels.items()},
            "linear_probes": {
                "style_label": probe_report(X, labels["style_label"]),
                "disposition_label": probe_report(X, labels["disposition_label"]),
                "condition": probe_report(X, labels["condition"]),
            },
        }
    return {"model_id": MODEL_ID, "sample_count": len(samples), "samples": meta, "layers": layer_results}


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = ["# Mamba Style × Disposition Control Panel", "", f"Model: `{payload['model_id']}`", f"Samples: `{payload['sample_count']}`", ""]
    lines.append("## Key linear probes")
    for layer_name in ["L3", "L8", "L2+L3+L4", "L1-L5"]:
        if layer_name not in payload["layers"]:
            continue
        lr = payload["layers"][layer_name]
        lines.append(f"### {layer_name}")
        lines.append(f"- dim: `{lr['dim']}`")
        lines.append(f"- norm mean/std: `{lr['norm_mean']:.4f}` / `{lr['norm_std']:.4f}`")
        for label in ["style_label", "disposition_label", "condition"]:
            pr = lr["linear_probes"][label]
            if pr.get("skipped"):
                lines.append(f"- {label}: skipped ({pr['reason']})")
            else:
                lines.append(f"- {label} balanced accuracy: `{pr['balanced_accuracy']:.3f}`")
        lines.append(f"- condition centroid avg cosine: `{lr['centroids']['condition']['avg_pairwise_cosine']:.4f}`")
        lines.append("")
    lines.append("## Norms by condition at L3")
    if "L3" in payload["layers"]:
        for c, v in sorted(payload["layers"]["L3"]["norm_by_condition"].items()):
            lines.append(f"- `{c}`: `{v:.4f}`")
    lines.append("")
    lines.append("## Interpretation note")
    lines.append("Panel B (plain disposition) is load-bearing. If disposition-label probe accuracy stays high under flat style, disposition exists independent of ornament. Panel A maps style contamination; it is not decisive alone.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", default=str(OUT_JSON))
    ap.add_argument("--out-md", default=str(OUT_MD))
    ap.add_argument("--max-length", type=int, default=1024)
    ap.add_argument("--save-states", action="store_true")
    args = ap.parse_args()
    started = time.time()
    random.seed(7)
    np.random.seed(7)
    torch.manual_seed(7)

    samples = build_samples()
    layers = list(range(1, 9))
    print(f"Loading {MODEL_ID} on CUDA if available...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    model = MambaForCausalLM.from_pretrained(MODEL_ID, dtype=dtype, device_map={"": device})
    model.eval()
    print(f"Loaded on {device}; samples={len(samples)} layers={layers}", flush=True)

    layer_states: dict[int, list[np.ndarray]] = {l: [] for l in layers}
    token_counts = []
    for i, sample in enumerate(samples, 1):
        print(f"[{i:03d}/{len(samples)}] {sample.sample_id} {sample.condition}", flush=True)
        tok = tokenizer(sample.text, return_tensors="pt", truncation=True, max_length=args.max_length)
        token_counts.append(int(tok["input_ids"].shape[-1]))
        states = extract_states(model, tokenizer, sample, layers, args.max_length)
        for l in layers:
            layer_states[l].append(states[l].numpy())

    layer_sets = {f"L{l}": [l] for l in layers}
    layer_sets.update({"L2+L3+L4": [2, 3, 4], "L1-L5": [1, 2, 3, 4, 5]})
    payload = summarize(samples, layer_states, layer_sets)
    payload["duration_s"] = round(time.time() - started, 2)
    payload["token_count_mean"] = float(np.mean(token_counts))
    payload["token_count_std"] = float(np.std(token_counts))
    payload["token_count_min"] = int(min(token_counts))
    payload["token_count_max"] = int(max(token_counts))

    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(payload, out_md)
    if args.save_states:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        for l, arrs in layer_states.items():
            np.save(RAW_DIR / f"layer_{l}.npy", np.stack(arrs, axis=0))
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Duration {payload['duration_s']}s")

if __name__ == "__main__":
    main()
