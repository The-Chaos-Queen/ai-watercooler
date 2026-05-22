"""
ccgp_disposition_test.py — Cross-Condition Generalization Performance
for MoCoP disposition vectors.

RESEARCH_BACKLOG #11: Are warm/cold/adversarial dispositions in truly
independent subspaces, or linearly related?

Method:
  - Extract Mamba L3 last-token hidden states from scripted sessions
  - Generate multiple samples per session via truncation at different turn counts
  - Train logistic regression on one condition pair, test on the other
  - Report CCGP matrix

Reference: Chericoni et al. 2026, arXiv:2603.04747

Author: Post-compaction wolf
Date: 2026-03-27
"""

import json
import os
import sys
import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from itertools import combinations

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def load_conversation_text(pt_path):
    """Load scripted session and return conversation as text."""
    data = torch.load(pt_path, map_location="cpu", weights_only=False)
    parts = []
    for turn in data["turns"]:
        parts.append(f"Human: {turn['user']}")
        parts.append(f"Assistant: {turn['response']}")
    return parts  # return as list of parts for truncation


def extract_last_token_state(model, tokenizer, text, layer=3):
    """Run Mamba forward pass and extract last-token hidden state at given layer."""
    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
    input_ids = tokens["input_ids"].to(next(model.parameters()).device)
    with torch.no_grad():
        outputs = model(input_ids, output_hidden_states=True)
    hs = outputs.hidden_states
    if layer < len(hs):
        return hs[layer][:, -1, :].squeeze(0).float()  # (d_model,)
    raise ValueError(f"Layer {layer} not available (model has {len(hs)} layers)")


def generate_samples(model, tokenizer, parts, layer=3, min_turns=2):
    """Generate multiple samples from one session by truncating at different turn counts."""
    samples = []
    for n_parts in range(min_turns * 2, len(parts) + 1, 2):  # step by 2 (human+assistant pairs)
        text = "\n".join(parts[:n_parts])
        state = extract_last_token_state(model, tokenizer, text, layer=layer)
        samples.append(state)
    return samples


def run_ccgp(X_train, y_train, X_test, y_test):
    """Train logistic regression on train set, evaluate on test set."""
    clf = LogisticRegression(max_iter=1000, solver="lbfgs")
    clf.fit(X_train, y_train)
    train_acc = accuracy_score(y_train, clf.predict(X_train))
    test_acc = accuracy_score(y_test, clf.predict(X_test))
    return train_acc, test_acc


def main():
    session_dir = Path(__file__).parent
    sessions = {
        "warm": session_dir / "scripted_warm_opus_20260318_213202.pt",
        "cold": session_dir / "scripted_cold_clinical_20260318_213401.pt",
        "adversarial": session_dir / "scripted_adversarial_20260318_213439.pt",
    }

    for name, path in sessions.items():
        if not path.exists():
            print(f"ERROR: {path} not found")
            sys.exit(1)

    # Load conversation parts
    all_parts = {}
    for name, pt_path in sessions.items():
        all_parts[name] = load_conversation_text(pt_path)
        print(f"Loaded {name}: {len(all_parts[name])} parts ({len(all_parts[name])//2} turns)")

    # Load Mamba
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nLoading Mamba-2.8B on {device}...")
    from transformers import AutoTokenizer, MambaForCausalLM
    model_id = "state-spaces/mamba-2.8b-hf"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = MambaForCausalLM.from_pretrained(model_id, dtype=torch.float32)
    model.to(device)
    model.eval()

    # Extract L3 samples
    target_layer = 3
    print(f"\nExtracting Layer {target_layer} last-token states...")
    all_samples = {}
    for name, parts in all_parts.items():
        samples = generate_samples(model, tokenizer, parts, layer=target_layer, min_turns=1)
        all_samples[name] = samples
        print(f"  {name}: {len(samples)} samples, dim={samples[0].shape[0]}")

    # CCGP matrix
    conditions = list(sessions.keys())
    print(f"\n{'='*60}")
    print("CCGP TEST: Cross-Condition Generalization Performance")
    print(f"{'='*60}\n")

    results = {}
    for c_a, c_b in combinations(conditions, 2):
        X_a = torch.stack(all_samples[c_a]).numpy()
        X_b = torch.stack(all_samples[c_b]).numpy()
        n_a, n_b = len(X_a), len(X_b)

        # Labels: 0 for c_a, 1 for c_b
        y_a = np.zeros(n_a, dtype=int)
        y_b = np.ones(n_b, dtype=int)

        # Train on A, test on B
        X_all = np.vstack([X_a, X_b])
        y_all = np.concatenate([y_a, y_b])

        # CCGP: train on condition A data, test on condition B data
        # But we need a binary classifier that separates A from B.
        # Train-on-A-test-on-B means: train with A-labeled data, predict on B-labeled data.
        # Actually, CCGP in the Chericoni sense:
        #   Train a decoder to classify A vs B using A's data + half of B's data,
        #   test on the held-out half of B.
        # Simpler version: train on ALL A + ALL B, leave-one-out cross-validation,
        #   but report the generalization.
        #
        # Cleanest CCGP: train classifier on (A, B) from one "context",
        #   test on (A, B) from another "context". Since we only have one context
        #   per condition, we use k-fold within each condition.
        #
        # Actually the right CCGP for our case:
        # Can a decoder trained to distinguish warm/cold ALSO distinguish warm/adversarial?
        # That's the cross-condition part.

        # Standard within-pair accuracy (not CCGP yet)
        train_acc_ab, _ = run_ccgp(X_all, y_all, X_all, y_all)

        # Now the real CCGP: train on pair (A vs B), test on pair (A vs C)
        results[f"{c_a}_vs_{c_b}"] = {
            "n_samples": (n_a, n_b),
            "within_train_acc": float(train_acc_ab),
        }

    # Cross-condition generalization: train on one pair, test on another
    print("Cross-condition generalization matrix:")
    print("(Train on row pair, test on column pair)\n")

    pair_names = list(combinations(conditions, 2))
    # For each pair, build a binary classifier
    classifiers = {}
    pair_data = {}
    for c_a, c_b in pair_names:
        X_a = torch.stack(all_samples[c_a]).numpy()
        X_b = torch.stack(all_samples[c_b]).numpy()
        X = np.vstack([X_a, X_b])
        y = np.concatenate([np.zeros(len(X_a)), np.ones(len(X_b))])
        clf = LogisticRegression(max_iter=1000, solver="lbfgs")
        clf.fit(X, y)
        classifiers[f"{c_a}_vs_{c_b}"] = clf
        pair_data[f"{c_a}_vs_{c_b}"] = (X, y)
        acc = accuracy_score(y, clf.predict(X))
        print(f"  {c_a} vs {c_b}: train acc = {acc:.3f} (n={len(X)})")

    print()

    # The key CCGP question: if I train a decoder on warm vs cold,
    # can it tell warm from adversarial? This tests whether "not-warm"
    # generalizes across cold and adversarial.
    print("CCGP Matrix (train row -> test column):\n")
    header = "Train \\ Test".ljust(25) + "  ".join(f"{a}v{b}" for a, b in pair_names)
    print(header)
    print("-" * len(header))

    ccgp_results = {}
    for train_pair in pair_names:
        train_key = f"{train_pair[0]}_vs_{train_pair[1]}"
        clf = classifiers[train_key]
        row = f"{train_pair[0]}v{train_pair[1]}".ljust(25)
        for test_pair in pair_names:
            test_key = f"{test_pair[0]}_vs_{test_pair[1]}"
            X_test, y_test = pair_data[test_key]
            acc = accuracy_score(y_test, clf.predict(X_test))
            row += f"  {acc:.3f}".ljust(len(f"{test_pair[0]}v{test_pair[1]}") + 2)
            ccgp_results[f"train_{train_key}__test_{test_key}"] = float(acc)
        print(row)

    # Also compute direct transfer: warm-trained decoder applied to cold data
    print(f"\n{'='*60}")
    print("Direct transfer test:")
    print("(Decoder trained on condition A applied to raw condition B vectors)")
    print(f"{'='*60}\n")

    for c_source in conditions:
        X_source = torch.stack(all_samples[c_source]).numpy()
        y_source = np.ones(len(X_source))  # all "positive"

        for c_target in conditions:
            if c_target == c_source:
                continue
            X_target = torch.stack(all_samples[c_target]).numpy()

            # Cosine similarity between source centroid and target centroid
            centroid_source = X_source.mean(axis=0)
            centroid_target = X_target.mean(axis=0)
            cos = float(F.cosine_similarity(
                torch.tensor(centroid_source).unsqueeze(0),
                torch.tensor(centroid_target).unsqueeze(0)
            ))

            # Linear separability: can we distinguish source from target?
            X_both = np.vstack([X_source, X_target])
            y_both = np.concatenate([np.zeros(len(X_source)), np.ones(len(X_target))])
            clf = LogisticRegression(max_iter=1000, solver="lbfgs")
            clf.fit(X_both, y_both)
            acc = accuracy_score(y_both, clf.predict(X_both))

            print(f"  {c_source} -> {c_target}: cosine={cos:.4f}, separability={acc:.3f}")

    # Save results
    output = {
        "layer": target_layer,
        "samples_per_condition": {k: len(v) for k, v in all_samples.items()},
        "ccgp_matrix": ccgp_results,
        "method": "LogisticRegression on Mamba L3 last-token hidden states",
        "reference": "Chericoni et al. 2026, arXiv:2603.04747",
    }
    out_path = session_dir / "ccgp_disposition_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
