"""
token_window_separation.py — Compare last-1 vs last-N token pooling
for disposition separation at Mamba Layer 3.

Tests: last-1, last-4, last-10, last-16, last-32, full-mean
Aggregation: mean of the last N tokens (not attention-weighted)

Author: Anda-Conda
Date: 2026-03-26
"""

import json
import os
import torch
import torch.nn.functional as F
from pathlib import Path
from itertools import combinations

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def load_conversation_text(pt_path):
    data = torch.load(pt_path, map_location="cpu", weights_only=False)
    parts = []
    for turn in data["turns"]:
        parts.append(f"Human: {turn['user']}")
        parts.append(f"Assistant: {turn['response']}")
    return "\n".join(parts)


def cosine_sim(a, b):
    a_flat = a.flatten().float()
    b_flat = b.flatten().float()
    return float(F.cosine_similarity(a_flat.unsqueeze(0), b_flat.unsqueeze(0)))


def extract_window_representations(model, tokenizer, text, target_layer=3, windows=(1, 4, 10, 16, 32)):
    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
    input_ids = tokens["input_ids"]
    seq_len = input_ids.shape[1]

    with torch.no_grad():
        outputs = model(input_ids, output_hidden_states=True)

    hidden = outputs.hidden_states[target_layer]  # (1, seq_len, d_model)

    reps = {}
    for w in windows:
        actual_w = min(w, seq_len)
        if actual_w == 1:
            vec = hidden[:, -1, :].squeeze(0)  # last token
        else:
            vec = hidden[:, -actual_w:, :].mean(dim=1).squeeze(0)  # mean of last N
        reps[f"last_{w}"] = vec

    # Full mean for reference
    reps["full_mean"] = hidden.mean(dim=1).squeeze(0)

    return reps, seq_len


def main():
    session_dir = Path(__file__).parent
    sessions = {
        "warm": session_dir / "scripted_warm_opus_20260318_213202.pt",
        "cold": session_dir / "scripted_cold_clinical_20260318_213401.pt",
        "adversarial": session_dir / "scripted_adversarial_20260318_213439.pt",
    }

    conversations = {}
    for name, pt_path in sessions.items():
        conversations[name] = load_conversation_text(pt_path)
        print(f"Loaded {name}: {len(conversations[name])} chars")

    print("\nLoading Mamba-2.8B on CPU...")
    from transformers import AutoTokenizer, MambaForCausalLM
    model_id = "state-spaces/mamba-2.8b-hf"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = MambaForCausalLM.from_pretrained(model_id, dtype=torch.float32)
    model.eval()

    windows = [1, 4, 10, 16, 32]
    all_reps = {}

    print("\nExtracting Layer 3 representations...")
    for name, text in conversations.items():
        print(f"  {name}...", end=" ", flush=True)
        reps, seq_len = extract_window_representations(model, tokenizer, text, windows=windows)
        all_reps[name] = reps
        print(f"done (seq_len={seq_len})")

    # Compare
    window_labels = [f"last_{w}" for w in windows] + ["full_mean"]
    pairs = list(combinations(conversations.keys(), 2))

    print(f"\n{'='*70}")
    print("TOKEN WINDOW SEPARATION COMPARISON (Layer 3)")
    print(f"{'='*70}")
    print(f"\n{'Window':<12} ", end="")
    for a, b in pairs:
        print(f"  {a[:4]}v{b[:4]:>4}", end="")
    print(f"  {'avg':>8}")
    print("-" * 60)

    results = {}
    for label in window_labels:
        cosines = []
        print(f"{label:<12} ", end="")
        for a, b in pairs:
            va = all_reps[a].get(label)
            vb = all_reps[b].get(label)
            if va is not None and vb is not None:
                c = cosine_sim(va, vb)
                cosines.append(c)
                print(f"  {c:>8.4f}", end="")
            else:
                print(f"  {'N/A':>8}", end="")
        avg = sum(cosines) / len(cosines) if cosines else 0
        print(f"  {avg:>8.4f}")
        results[label] = {"cosines": {f"{a}_vs_{b}": c for (a, b), c in zip(pairs, cosines)}, "avg": avg}

    # Find best
    print(f"\n{'='*70}")
    print("RANKING (lower avg cosine = better separation)")
    print(f"{'='*70}")
    ranked = sorted(results.items(), key=lambda x: x[1]["avg"])
    for i, (label, data) in enumerate(ranked):
        marker = " <-- BEST" if i == 0 else ""
        print(f"  {i+1}. {label:<12}  avg={data['avg']:.4f}{marker}")

    best_label = ranked[0][0]
    best_avg = ranked[0][1]["avg"]
    last1_avg = results.get("last_1", {}).get("avg", 999)
    print(f"\n  Best window: {best_label} (avg cosine {best_avg:.4f})")
    if best_label == "last_1":
        print("  CONCLUSION: Last single token is already optimal. No window helps.")
    elif best_avg < last1_avg * 0.8:
        print(f"  CONCLUSION: {best_label} is meaningfully better than last_1 ({best_avg:.4f} vs {last1_avg:.4f}).")
        print(f"  Consider switching MambaStateCompressor to trailing-window extraction.")
    else:
        print(f"  CONCLUSION: {best_label} is marginally better but not decisively ({best_avg:.4f} vs {last1_avg:.4f}).")
        print(f"  Probably not worth the complexity. Stick with last-1.")

    out_path = session_dir / "token_window_separation.json"
    with open(out_path, "w") as f:
        json.dump({"windows": windows, "results": results, "best": best_label}, f, indent=2)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
