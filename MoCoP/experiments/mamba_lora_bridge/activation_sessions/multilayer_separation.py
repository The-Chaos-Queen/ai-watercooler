"""
multilayer_separation.py — Compare Layer 3 alone vs Layers 2-4 concat
for disposition separation at Mamba last-token hidden states.

RESEARCH_BACKLOG item #2: Is the signal really localized to Layer 3,
or do adjacent layers add non-redundant information?

Tests:
  - Layer 2 alone, Layer 3 alone, Layer 4 alone
  - Concat Layers 2-3, Layers 3-4, Layers 2-4
  - Concat Layers 1-5 (wider net)

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


def extract_multilayer(model, tokenizer, text, layers=(1, 2, 3, 4, 5)):
    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
    with torch.no_grad():
        outputs = model(tokens["input_ids"], output_hidden_states=True)

    hs = outputs.hidden_states  # tuple of (n_layers+1) tensors
    # Extract last-token hidden state at each requested layer
    per_layer = {}
    for layer in layers:
        if layer < len(hs):
            per_layer[layer] = hs[layer][:, -1, :].squeeze(0)  # (d_model,)
    return per_layer


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

    probe_layers = [1, 2, 3, 4, 5, 6, 7, 8]
    all_per_layer = {}

    print(f"\nExtracting last-token at layers {probe_layers}...")
    for name, text in conversations.items():
        print(f"  {name}...", end=" ", flush=True)
        per_layer = extract_multilayer(model, tokenizer, text, layers=probe_layers)
        all_per_layer[name] = per_layer
        print("done")

    # Build representations to test
    configs = {}

    # Single layers
    for layer in probe_layers:
        label = f"L{layer}"
        configs[label] = {name: all_per_layer[name][layer] for name in conversations}

    # Concatenations
    concat_sets = [
        ("L2+L3", [2, 3]),
        ("L3+L4", [3, 4]),
        ("L2+L3+L4", [2, 3, 4]),
        ("L1-L5", [1, 2, 3, 4, 5]),
        ("L2-L6", [2, 3, 4, 5, 6]),
    ]
    for label, layer_list in concat_sets:
        reps = {}
        for name in conversations:
            vecs = [all_per_layer[name][l] for l in layer_list if l in all_per_layer[name]]
            reps[name] = torch.cat(vecs, dim=0)
        configs[label] = reps

    # Compare
    pairs = list(combinations(conversations.keys(), 2))

    print(f"\n{'='*70}")
    print("MULTI-LAYER SEPARATION COMPARISON (last-token, Mamba Layer 3 +/- neighbors)")
    print(f"{'='*70}")
    print(f"\n{'Config':<12}  {'dim':>6} ", end="")
    for a, b in pairs:
        print(f"  {a[:4]}v{b[:4]:>4}", end="")
    print(f"  {'avg':>8}")
    print("-" * 70)

    results = {}
    for label, reps in configs.items():
        dim = reps[list(reps.keys())[0]].shape[0]
        cosines = []
        print(f"{label:<12}  {dim:>6} ", end="")
        for a, b in pairs:
            c = cosine_sim(reps[a], reps[b])
            cosines.append(c)
            print(f"  {c:>8.4f}", end="")
        avg = sum(cosines) / len(cosines)
        print(f"  {avg:>8.4f}")
        results[label] = {"dim": dim, "avg": avg,
                          "cosines": {f"{a}_vs_{b}": c for (a, b), c in zip(pairs, cosines)}}

    # Ranking
    print(f"\n{'='*70}")
    print("RANKING (lower avg cosine = better separation)")
    print(f"{'='*70}")
    ranked = sorted(results.items(), key=lambda x: x[1]["avg"])
    for i, (label, data) in enumerate(ranked):
        marker = " <-- BEST" if i == 0 else ""
        print(f"  {i+1}. {label:<12} dim={data['dim']:>6}  avg={data['avg']:.4f}{marker}")

    best = ranked[0]
    l3_avg = results.get("L3", {}).get("avg", 999)
    print(f"\n  Best: {best[0]} (avg cosine {best[1]['avg']:.4f})")
    print(f"  Layer 3 alone: avg cosine {l3_avg:.4f}")

    if best[0] == "L3":
        print("  CONCLUSION: Layer 3 alone is optimal. No concat helps.")
    elif best[1]["avg"] < l3_avg * 0.8:
        print(f"  CONCLUSION: {best[0]} is meaningfully better than L3 alone.")
        print(f"  Consider updating MambaStateCompressor to multi-layer concat.")
    else:
        diff_pct = (1 - best[1]["avg"] / l3_avg) * 100 if l3_avg > 0 else 0
        print(f"  CONCLUSION: {best[0]} is {diff_pct:.0f}% better but adds {best[1]['dim'] - 2560} dims.")
        print(f"  Marginal gain may not justify the complexity.")

    out_path = session_dir / "multilayer_separation.json"
    with open(out_path, "w") as f:
        json.dump({"results": results, "best": best[0], "probe_layers": probe_layers}, f, indent=2)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
