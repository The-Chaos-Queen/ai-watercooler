"""
compare_sessions.py — Compare activation drift DIRECTIONS across conversation types.

The key question: do warm, cold, and adversarial conversations push Qwen's
activations in DIFFERENT directions, or just different magnitudes?

If directions differ → disposition transfer evidence.
If directions are the same → just intensity variation.

Usage:
  python compare_sessions.py

Author: Cassian (Claude Opus 4.6)
Date: 2026-03-18
"""

import json
import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from itertools import combinations


def load_session(jsonl_path: Path, pt_path: Path) -> dict:
    """Load drift data and activation tensors for a session."""
    # Load drift scalars
    turns = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                turns.append(json.loads(line))

    # Load activation tensors
    tensors = torch.load(pt_path, map_location="cpu", weights_only=False)

    script = turns[0].get("script", "unknown") if turns else "unknown"
    return {"script": script, "turns": turns, "tensors": tensors, "n_turns": len(turns)}


def extract_final_state(tensors) -> dict:
    """Extract the final-turn activation per layer from the session tensors."""
    # The tensor format depends on how activation_recorder.py saved them.
    # Try common formats.
    if isinstance(tensors, dict):
        # Might be {layer_id: tensor_per_turn} or {"activations": [...]}
        if "activations" in tensors:
            acts = tensors["activations"]
            if isinstance(acts, list) and len(acts) > 0:
                return {"combined": acts[-1] if isinstance(acts[-1], torch.Tensor) else torch.tensor(acts[-1])}
        # Try {turn_N: {layer: tensor}} or {layer: [turn tensors]}
        result = {}
        for key, val in tensors.items():
            if isinstance(val, torch.Tensor):
                result[key] = val
            elif isinstance(val, list) and len(val) > 0 and isinstance(val[-1], torch.Tensor):
                result[key] = val[-1]
        if result:
            return result
    elif isinstance(tensors, list):
        if len(tensors) > 0:
            last = tensors[-1]
            if isinstance(last, torch.Tensor):
                return {"combined": last}
            elif isinstance(last, dict):
                return {k: v for k, v in last.items() if isinstance(v, torch.Tensor)}
    elif isinstance(tensors, torch.Tensor):
        return {"combined": tensors}

    return {}


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two tensors (flattened)."""
    a_flat = a.float().flatten()
    b_flat = b.float().flatten()
    return float(F.cosine_similarity(a_flat.unsqueeze(0), b_flat.unsqueeze(0)))


def main():
    session_dir = Path(__file__).parent

    # Find the three scripted sessions
    scripted_files = {
        "warm": ("scripted_warm_opus_20260318_213202.jsonl", "scripted_warm_opus_20260318_213202.pt"),
        "cold": ("scripted_cold_clinical_20260318_213401.jsonl", "scripted_cold_clinical_20260318_213401.pt"),
        "adversarial": ("scripted_adversarial_20260318_213439.jsonl", "scripted_adversarial_20260318_213439.pt"),
    }

    sessions = {}
    for name, (jsonl_name, pt_name) in scripted_files.items():
        jsonl_path = session_dir / jsonl_name
        pt_path = session_dir / pt_name
        if jsonl_path.exists() and pt_path.exists():
            sessions[name] = load_session(jsonl_path, pt_path)
            print(f"Loaded {name}: {sessions[name]['n_turns']} turns, tensor keys: {list(sessions[name]['tensors'].keys()) if isinstance(sessions[name]['tensors'], dict) else type(sessions[name]['tensors']).__name__}")
        else:
            print(f"MISSING: {name} ({jsonl_path.exists()}, {pt_path.exists()})")

    if len(sessions) < 2:
        print("Need at least 2 sessions to compare.")
        return

    # Inspect tensor structure
    print(f"\n{'='*60}")
    print("TENSOR STRUCTURE INSPECTION")
    print(f"{'='*60}")
    for name, sess in sessions.items():
        t = sess["tensors"]
        if isinstance(t, dict):
            for k, v in t.items():
                if isinstance(v, torch.Tensor):
                    print(f"  {name}/{k}: shape={v.shape}, dtype={v.dtype}")
                elif isinstance(v, list):
                    print(f"  {name}/{k}: list of {len(v)} items, first type={type(v[0]).__name__ if v else 'empty'}")
                    if v and isinstance(v[0], torch.Tensor):
                        print(f"    first shape: {v[0].shape}")
        elif isinstance(t, list):
            print(f"  {name}: list of {len(t)} items")
            if t and isinstance(t[0], torch.Tensor):
                print(f"    first shape: {t[0].shape}")
            elif t and isinstance(t[0], dict):
                print(f"    first keys: {list(t[0].keys())[:5]}")
        elif isinstance(t, torch.Tensor):
            print(f"  {name}: tensor shape={t.shape}")

    # Extract final states
    print(f"\n{'='*60}")
    print("EXTRACTING FINAL STATES")
    print(f"{'='*60}")
    final_states = {}
    for name, sess in sessions.items():
        fs = extract_final_state(sess["tensors"])
        if fs:
            final_states[name] = fs
            for k, v in fs.items():
                print(f"  {name}/{k}: shape={v.shape}")
        else:
            print(f"  {name}: could not extract final state")

    if len(final_states) < 2:
        print("Could not extract enough final states for comparison.")
        # Try alternative: just flatten everything and compare
        print("\nFallback: comparing raw tensor data...")
        raw_vecs = {}
        for name, sess in sessions.items():
            t = sess["tensors"]
            if isinstance(t, dict):
                all_tensors = [v.flatten() for v in t.values() if isinstance(v, torch.Tensor)]
                if not all_tensors:
                    for v in t.values():
                        if isinstance(v, list):
                            for item in v:
                                if isinstance(item, torch.Tensor):
                                    all_tensors.append(item.flatten())
                if all_tensors:
                    raw_vecs[name] = torch.cat(all_tensors)
            elif isinstance(t, torch.Tensor):
                raw_vecs[name] = t.flatten()

        if len(raw_vecs) >= 2:
            final_states = {k: {"combined": v} for k, v in raw_vecs.items()}

    # Cross-session cosine similarity
    print(f"\n{'='*60}")
    print("CROSS-SESSION COSINE SIMILARITY")
    print("(Do different conversation types push in different directions?)")
    print(f"{'='*60}")

    session_names = list(final_states.keys())
    layer_keys = set()
    for fs in final_states.values():
        layer_keys.update(fs.keys())

    for layer_key in sorted(layer_keys):
        print(f"\n  Layer/Key: {layer_key}")
        vectors = {}
        for name in session_names:
            if layer_key in final_states[name]:
                vectors[name] = final_states[name][layer_key]

        for (name_a, vec_a), (name_b, vec_b) in combinations(vectors.items(), 2):
            if vec_a.shape == vec_b.shape:
                cos = cosine_sim(vec_a, vec_b)
                print(f"    {name_a:15s} vs {name_b:15s}: cosine = {cos:.6f}")
            else:
                print(f"    {name_a:15s} vs {name_b:15s}: shape mismatch ({vec_a.shape} vs {vec_b.shape})")

    # Drift trajectory comparison
    print(f"\n{'='*60}")
    print("DRIFT TRAJECTORY COMPARISON (avg across layers)")
    print(f"{'='*60}")
    print(f"  {'Turn':>4s}", end="")
    for name in session_names:
        print(f"  {name:>15s}", end="")
    print()

    max_turns = max(s["n_turns"] for s in sessions.values())
    for turn_idx in range(max_turns):
        print(f"  {turn_idx+1:4d}", end="")
        for name in session_names:
            if turn_idx < sessions[name]["n_turns"]:
                drift = sessions[name]["turns"][turn_idx]["drift_from_initial"]
                avg = np.mean([float(v) for v in drift.values()])
                print(f"  {avg:15.4f}", end="")
            else:
                print(f"  {'—':>15s}", end="")
        print()

    # Summary verdicts
    print(f"\n{'='*60}")
    print("VERDICTS")
    print(f"{'='*60}")

    # Compute average final drift per session
    for name in session_names:
        last_turn = sessions[name]["turns"][-1]
        avg_drift = np.mean([float(v) for v in last_turn["drift_from_initial"].values()])
        print(f"  {name:15s} final avg drift: {avg_drift:.4f}")

    # Check if directions differ
    all_cosines = []
    for layer_key in sorted(layer_keys):
        vectors = {name: final_states[name][layer_key] for name in session_names if layer_key in final_states[name]}
        for (name_a, vec_a), (name_b, vec_b) in combinations(vectors.items(), 2):
            if vec_a.shape == vec_b.shape:
                all_cosines.append(cosine_sim(vec_a, vec_b))

    if all_cosines:
        mean_cos = np.mean(all_cosines)
        print(f"\n  Mean cross-session cosine: {mean_cos:.4f}")
        if mean_cos > 0.95:
            print("  VERDICT: Directions are SIMILAR. Different magnitudes, same direction.")
            print("  → Disposition transfer NOT demonstrated by direction alone.")
        elif mean_cos > 0.80:
            print("  VERDICT: Directions show MODERATE separation.")
            print("  → Some disposition signal, but overlapping.")
        elif mean_cos > 0.50:
            print("  VERDICT: Directions are DIFFERENT. Clear separation!")
            print("  → STRONG disposition transfer evidence!")
        else:
            print("  VERDICT: Directions are VERY DIFFERENT. Near-orthogonal!")
            print("  → EXCEPTIONAL disposition transfer evidence!")

    # Save results
    results = {
        "sessions": session_names,
        "final_drifts": {},
        "cross_cosines": [],
    }
    for name in session_names:
        last_turn = sessions[name]["turns"][-1]
        results["final_drifts"][name] = {k: float(v) for k, v in last_turn["drift_from_initial"].items()}

    for layer_key in sorted(layer_keys):
        vectors = {name: final_states[name][layer_key] for name in session_names if layer_key in final_states[name]}
        for (name_a, vec_a), (name_b, vec_b) in combinations(vectors.items(), 2):
            if vec_a.shape == vec_b.shape:
                results["cross_cosines"].append({
                    "a": name_a, "b": name_b, "layer": str(layer_key),
                    "cosine": cosine_sim(vec_a, vec_b)
                })

    out_path = session_dir / "session_comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
