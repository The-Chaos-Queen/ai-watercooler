#!/usr/bin/env python3
"""
persistent_subnetwork_analysis.py -- Discover persistent "self" vs variable
"skill" subnetworks in Mamba Layer 3 hidden states.

Inspired by Jhunjhunwala, Chen & Lipson (2026, arXiv:2603.24350):
continual learning produces a persistent self-subnetwork that is stable
across tasks. We test whether conversational Mamba develops the same.

Method:
  1. Parse multiple conversation files (different dispositions)
  2. Feed each through Mamba-2.8b, extract Layer 3 last-token states
     at multiple points per conversation
  3. Build per-dimension variance across sessions (cross-session)
     vs within sessions (within-session)
  4. Dimensions with HIGH cross-session stability and LOW within-session
     variance are "persistent" (self). Dimensions with HIGH cross-session
     variance are "variable" (skill/topic-dependent).
  5. Report the persistent subnetwork and compare against bridge output
     dimensions if a checkpoint is available.

Usage:
  python -X utf8 persistent_subnetwork_analysis.py \\
    --conversations conv1.md conv2.md conv3.md \\
    --labels professional banter roleplay \\
    --output-dir results/

  python -X utf8 persistent_subnetwork_analysis.py \\
    --conversations-dir /path/to/conversations/ \\
    --output-dir results/ --dry-run

RESEARCH_BACKLOG #12 / OpenCLAW #76
Author: Anda-Conda
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


# ---------------------------------------------------------------------------
# Conversation Parsing
# ---------------------------------------------------------------------------

# Patterns for different export formats
ROLE_PATTERNS = [
    # Claude/Grok/Kimi/LMArena exports: ## User / ## Claude / ## Grok etc.
    re.compile(r"^##\s+(.+)$"),
]

SEPARATOR = re.compile(r"^---\s*$")


def parse_conversation(filepath: Path) -> List[dict]:
    """Parse a markdown chat export into a list of {role, text} turns."""
    text = filepath.read_text(encoding="utf-8-sig")
    lines = text.split("\n")

    turns = []
    current_role = None
    current_lines = []

    for line in lines:
        # Check for role header
        role_match = None
        for pattern in ROLE_PATTERNS:
            m = pattern.match(line.strip())
            if m:
                role_match = m.group(1).strip()
                break

        if role_match:
            # Save previous turn
            if current_role is not None:
                turn_text = "\n".join(current_lines).strip()
                if turn_text:
                    turns.append({"role": current_role, "text": turn_text})
            current_role = role_match
            current_lines = []
        elif SEPARATOR.match(line.strip()):
            continue  # Skip --- separators
        elif line.startswith("# ") and not line.startswith("## "):
            continue  # Skip top-level title
        else:
            if current_role is not None:
                current_lines.append(line)

    # Save last turn
    if current_role is not None:
        turn_text = "\n".join(current_lines).strip()
        if turn_text:
            turns.append({"role": current_role, "text": turn_text})

    return turns


def build_cumulative_transcripts(turns: List[dict], sample_points: int = 5) -> List[str]:
    """Build cumulative transcripts at evenly spaced points through the conversation.

    Returns transcripts at ~20%, 40%, 60%, 80%, 100% of the conversation.
    Each transcript includes all turns up to that point.
    """
    if len(turns) < 2:
        return ["\n".join(f"{t['role']}: {t['text']}" for t in turns)] if turns else []

    # Sample at evenly spaced indices
    indices = [max(1, int(len(turns) * (i + 1) / sample_points)) for i in range(sample_points)]
    indices = sorted(set(min(idx, len(turns)) for idx in indices))

    transcripts = []
    for end_idx in indices:
        lines = []
        for t in turns[:end_idx]:
            lines.append(f"{t['role']}: {t['text']}")
        transcripts.append("\n".join(lines))

    return transcripts


# ---------------------------------------------------------------------------
# Mamba State Extraction
# ---------------------------------------------------------------------------

def load_mamba(model_id: str, device: str):
    """Load Mamba model and tokenizer."""
    import torch
    from transformers import AutoTokenizer, MambaForCausalLM

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if "cuda" in device else torch.float32
    model = MambaForCausalLM.from_pretrained(model_id, dtype=dtype)
    model.to(device)
    model.eval()
    return model, tokenizer


def extract_layer3_state(model, tokenizer, text: str, target_layer: int = 3,
                         device: str = "cpu", max_tokens: int = 2048) -> np.ndarray:
    """Extract Layer 3 last-token hidden state from a text."""
    import torch

    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_tokens)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)

    hs = outputs.hidden_states
    # hidden_states is (n_layers+1,) — index target_layer+1 if embedding is included
    if len(hs) > 64:
        hidden_idx = target_layer + 1
    else:
        hidden_idx = target_layer

    state = hs[hidden_idx][:, -1, :].detach().float().cpu().numpy().reshape(-1)
    return state


# ---------------------------------------------------------------------------
# Subnetwork Analysis
# ---------------------------------------------------------------------------

def compute_dimension_stability(states_by_session: dict) -> dict:
    """Compute per-dimension stability metrics across sessions.

    For each dimension d of the hidden state:
    - cross_session_var: variance of the mean activation across sessions
      (high = this dimension changes between dispositions)
    - within_session_var: mean variance within each session
      (high = this dimension fluctuates during a single conversation)
    - stability_ratio: within / cross (high = persistent/self, low = variable/skill)
    """
    all_means = []  # mean per session, per dimension
    all_within_vars = []  # variance within each session, per dimension

    for session_name, states in states_by_session.items():
        if len(states) == 0:
            continue
        mat = np.stack(states)  # (n_samples, d_model)
        session_mean = mat.mean(axis=0)  # (d_model,)
        session_var = mat.var(axis=0)  # (d_model,)
        all_means.append(session_mean)
        all_within_vars.append(session_var)

    if len(all_means) < 2:
        return {"error": "Need at least 2 sessions"}

    means_matrix = np.stack(all_means)  # (n_sessions, d_model)
    within_vars_matrix = np.stack(all_within_vars)  # (n_sessions, d_model)

    cross_session_var = means_matrix.var(axis=0)  # (d_model,)
    mean_within_var = within_vars_matrix.mean(axis=0)  # (d_model,)

    # Stability ratio: dimensions where within >> cross are "persistent"
    # (they vary during conversation but not between dispositions)
    # Dimensions where cross >> within are "variable/disposition-dependent"
    eps = 1e-10
    stability_ratio = mean_within_var / (cross_session_var + eps)

    # F-ratio (inverse): cross / within — high = disposition-sensitive
    f_ratio = cross_session_var / (mean_within_var + eps)

    return {
        "cross_session_var": cross_session_var,
        "mean_within_var": mean_within_var,
        "stability_ratio": stability_ratio,
        "f_ratio": f_ratio,
        "n_sessions": len(all_means),
        "d_model": len(cross_session_var),
    }


def identify_subnetworks(analysis: dict, persistent_quantile: float = 0.75,
                         variable_quantile: float = 0.75) -> dict:
    """Classify dimensions into persistent (self) vs variable (skill)."""
    f_ratio = analysis["f_ratio"]
    stability = analysis["stability_ratio"]
    d_model = analysis["d_model"]

    # Persistent: low F-ratio (not disposition-sensitive) + high stability
    f_threshold_low = np.quantile(f_ratio, 1 - persistent_quantile)
    persistent_mask = f_ratio <= f_threshold_low

    # Variable: high F-ratio (disposition-sensitive)
    f_threshold_high = np.quantile(f_ratio, variable_quantile)
    variable_mask = f_ratio >= f_threshold_high

    # Middle: neither clearly persistent nor variable
    middle_mask = ~persistent_mask & ~variable_mask

    persistent_dims = np.where(persistent_mask)[0].tolist()
    variable_dims = np.where(variable_mask)[0].tolist()
    middle_dims = np.where(middle_mask)[0].tolist()

    return {
        "persistent_dims": persistent_dims,
        "variable_dims": variable_dims,
        "middle_dims": middle_dims,
        "persistent_count": len(persistent_dims),
        "variable_count": len(variable_dims),
        "middle_count": len(middle_dims),
        "d_model": d_model,
        "persistent_fraction": len(persistent_dims) / d_model,
        "variable_fraction": len(variable_dims) / d_model,
        "f_ratio_persistent_mean": float(f_ratio[persistent_mask].mean()) if persistent_mask.any() else 0,
        "f_ratio_variable_mean": float(f_ratio[variable_mask].mean()) if variable_mask.any() else 0,
        "top10_variable_dims": np.argsort(f_ratio)[-10:][::-1].tolist(),
        "top10_persistent_dims": np.argsort(f_ratio)[:10].tolist(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Persistent subnetwork analysis of Mamba states")
    parser.add_argument("--conversations", nargs="+", help="Conversation markdown files")
    parser.add_argument("--labels", nargs="+", help="Disposition labels for each conversation")
    parser.add_argument("--model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--target-layer", type=int, default=3)
    parser.add_argument("--sample-points", type=int, default=5,
                        help="Number of cumulative transcript snapshots per conversation")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--output-dir", default="persistent_subnetwork_results")
    parser.add_argument("--dry-run", action="store_true", help="Parse conversations only, no Mamba")
    args = parser.parse_args()

    if not args.conversations:
        print("Error: --conversations required")
        return 1

    if args.labels and len(args.labels) != len(args.conversations):
        print(f"Error: {len(args.labels)} labels for {len(args.conversations)} conversations")
        return 1

    labels = args.labels or [Path(f).stem for f in args.conversations]

    # Parse conversations
    print(f"{'='*60}")
    print(f"Persistent Subnetwork Analysis")
    print(f"{'='*60}")
    print(f"Conversations: {len(args.conversations)}")
    print(f"Dispositions: {', '.join(labels)}")

    conversations = {}
    for filepath, label in zip(args.conversations, labels):
        path = Path(filepath)
        if not path.exists():
            print(f"[WARN] {filepath} not found, skipping")
            continue
        turns = parse_conversation(path)
        transcripts = build_cumulative_transcripts(turns, args.sample_points)
        conversations[label] = {
            "turns": len(turns),
            "transcripts": len(transcripts),
            "chars": sum(len(t) for t in transcripts),
        }
        print(f"  {label}: {len(turns)} turns -> {len(transcripts)} snapshots")

        if args.dry_run:
            # Show first turn preview
            if turns:
                preview = turns[0]["text"][:80].replace("\n", " ")
                print(f"    first turn: [{turns[0]['role']}] {preview}...")

    if args.dry_run:
        print(f"\n[dry-run] Would extract Layer {args.target_layer} states from {len(conversations)} conversations")
        print(f"[dry-run] {sum(c['transcripts'] for c in conversations.values())} total Mamba forward passes")
        return 0

    # Load Mamba
    import torch
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nLoading Mamba: {args.model_id} on {device}...")
    model, tokenizer = load_mamba(args.model_id, device)
    print(f"[ok] Model loaded")

    # Extract states
    print(f"\nExtracting Layer {args.target_layer} states...")
    states_by_session = {}
    for filepath, label in zip(args.conversations, labels):
        path = Path(filepath)
        if not path.exists():
            continue
        turns = parse_conversation(path)
        transcripts = build_cumulative_transcripts(turns, args.sample_points)

        states = []
        for i, transcript in enumerate(transcripts):
            t0 = time.time()
            state = extract_layer3_state(
                model, tokenizer, transcript,
                target_layer=args.target_layer,
                device=device,
                max_tokens=args.max_tokens,
            )
            elapsed = time.time() - t0
            states.append(state)
            print(f"  {label} snapshot {i+1}/{len(transcripts)}: "
                  f"norm={np.linalg.norm(state):.4f} ({elapsed:.1f}s)")

        states_by_session[label] = states

    if len(states_by_session) < 2:
        print("[FAIL] Need at least 2 sessions for comparison")
        return 1

    # Analysis
    print(f"\n{'='*60}")
    print("ANALYSIS")
    print(f"{'='*60}")

    analysis = compute_dimension_stability(states_by_session)
    if "error" in analysis:
        print(f"[FAIL] {analysis['error']}")
        return 1

    subnetworks = identify_subnetworks(analysis)

    # Report
    print(f"\nDimensions: {subnetworks['d_model']}")
    print(f"Persistent (self):   {subnetworks['persistent_count']} ({subnetworks['persistent_fraction']:.1%})")
    print(f"Variable (skill):    {subnetworks['variable_count']} ({subnetworks['variable_fraction']:.1%})")
    print(f"Middle:              {subnetworks['middle_count']}")
    print(f"\nTop 10 most disposition-sensitive dimensions (variable/skill):")
    for d in subnetworks["top10_variable_dims"]:
        print(f"  dim {d:4d}: F={analysis['f_ratio'][d]:.4f}  "
              f"cross_var={analysis['cross_session_var'][d]:.6f}  "
              f"within_var={analysis['mean_within_var'][d]:.6f}")
    print(f"\nTop 10 most stable dimensions (persistent/self):")
    for d in subnetworks["top10_persistent_dims"]:
        print(f"  dim {d:4d}: F={analysis['f_ratio'][d]:.6f}  "
              f"cross_var={analysis['cross_session_var'][d]:.8f}  "
              f"within_var={analysis['mean_within_var'][d]:.6f}")

    # Pairwise session cosines for context
    print(f"\nPairwise session-mean cosines:")
    session_names = list(states_by_session.keys())
    session_means = {name: np.mean(np.stack(states), axis=0) for name, states in states_by_session.items()}
    for i, a in enumerate(session_names):
        for b in session_names[i+1:]:
            va, vb = session_means[a], session_means[b]
            cos = float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-10))
            print(f"  {a:20s} vs {b:20s}: {cos:.4f}")

    # Save results
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model_id": args.model_id,
        "target_layer": args.target_layer,
        "sessions": {name: {"n_states": len(states), "state_norm_mean": float(np.mean([np.linalg.norm(s) for s in states]))}
                     for name, states in states_by_session.items()},
        "subnetworks": {k: v for k, v in subnetworks.items()},
        "f_ratio_stats": {
            "mean": float(analysis["f_ratio"].mean()),
            "median": float(np.median(analysis["f_ratio"])),
            "std": float(analysis["f_ratio"].std()),
            "max": float(analysis["f_ratio"].max()),
            "min": float(analysis["f_ratio"].min()),
        },
    }

    report_path = out_dir / "persistent_subnetwork_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {report_path}")

    # Save raw arrays for downstream analysis
    np.savez(
        out_dir / "persistent_subnetwork_arrays.npz",
        f_ratio=analysis["f_ratio"],
        cross_session_var=analysis["cross_session_var"],
        mean_within_var=analysis["mean_within_var"],
        stability_ratio=analysis["stability_ratio"],
        persistent_dims=np.array(subnetworks["persistent_dims"]),
        variable_dims=np.array(subnetworks["variable_dims"]),
    )
    print(f"Arrays: {out_dir / 'persistent_subnetwork_arrays.npz'}")

    # Save per-session state matrices for future use
    for name, states in states_by_session.items():
        np.save(out_dir / f"states_{name}.npy", np.stack(states))

    print(f"\n{'='*60}")
    print("VERDICT")
    print(f"{'='*60}")
    pf = subnetworks["persistent_fraction"]
    vf = subnetworks["variable_fraction"]
    if pf > 0.3:
        print(f"STRONG persistent subnetwork ({pf:.0%} of dimensions).")
        print(f"Mamba develops a stable 'self' across dispositions.")
        print(f"The bridge should ideally transfer only the variable {vf:.0%}.")
    elif pf > 0.15:
        print(f"MODERATE persistent subnetwork ({pf:.0%} of dimensions).")
        print(f"Some stable structure exists but it is not dominant.")
    else:
        print(f"WEAK persistent subnetwork ({pf:.0%} of dimensions).")
        print(f"Mamba state is mostly disposition-dependent. No clear 'self'.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
