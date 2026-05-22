"""
multilayer_probe.py — Probe whether multi-layer concat or trailing-token windows
improve disposition separation over single Layer 3 last-token.

Probe 2: Layer 3 alone vs Layers 2+3+4 concatenated (last-token each)
Probe 3: Last-1 token vs last-4 vs last-8 vs last-16 (Layer 3 only)

Author: Purple (Claude Opus 4.6)
Date: 2026-03-26
"""

import json
import os
import torch
import torch.nn.functional as F
from pathlib import Path
from itertools import combinations

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def load_conversation_text(pt_path: Path) -> str:
    data = torch.load(pt_path, map_location="cpu", weights_only=False)
    parts = []
    for turn in data["turns"]:
        parts.append(f"Human: {turn['user']}")
        parts.append(f"Assistant: {turn['response']}")
    return "\n".join(parts)


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    return float(F.cosine_similarity(a.flatten().unsqueeze(0), b.flatten().unsqueeze(0)))


def extract_multilayer(model, tokenizer, text, layers, max_length=2048, trailing_k=1):
    """
    Extract hidden states from multiple layers, optionally using trailing-k tokens.

    Returns dict of {config_name: tensor} for each requested extraction.
    """
    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
    input_ids = tokens["input_ids"]
    if next(model.parameters()).device.type != "cpu":
        input_ids = input_ids.to(next(model.parameters()).device)

    with torch.no_grad():
        outputs = model(input_ids, output_hidden_states=True)

    hs = outputs.hidden_states
    n_layers = model.config.num_hidden_layers
    # Offset: index 0 = embedding, index 1 = layer 0
    offset = 1 if len(hs) == n_layers + 1 else 0

    results = {}

    # --- Probe 2: Single vs multi-layer (last token) ---
    for layer_idx in layers:
        h = hs[layer_idx + offset]  # (1, seq, d_model)
        results[f"L{layer_idx}_last1"] = h[:, -1, :].squeeze(0).cpu().float()

    # Concat layers 2+3+4
    if all(l + offset < len(hs) for l in [2, 3, 4]):
        concat = torch.cat([
            hs[2 + offset][:, -1, :],
            hs[3 + offset][:, -1, :],
            hs[4 + offset][:, -1, :],
        ], dim=-1).squeeze(0).cpu().float()
        results["L2_3_4_concat_last1"] = concat

    # --- Probe 3: Trailing token windows (Layer 3 only) ---
    h3 = hs[3 + offset]  # (1, seq, d_model)
    seq_len = h3.shape[1]

    for k in [1, 4, 8, 16]:
        if k > seq_len:
            continue
        window = h3[:, -k:, :]  # (1, k, d_model)
        # Mean over trailing window (not full mean-pool — just the last k)
        results[f"L3_last{k}_mean"] = window.mean(dim=1).squeeze(0).cpu().float()

    return results


def print_separation(name, reps):
    """Print pairwise cosine for a representation across warm/cold/adversarial."""
    names = list(reps.keys())
    cosines = {}
    for (a, va), (b, vb) in combinations(reps.items(), 2):
        cos = cosine_sim(va, vb)
        cosines[f"{a}_vs_{b}"] = cos
    avg = sum(cosines.values()) / len(cosines) if cosines else 999

    print(f"  {name:30s} | dim={reps[names[0]].shape[0]:6d} | "
          f"w/c={cosines.get(f'{names[0]}_vs_{names[1]}', 0):.4f} "
          f"w/a={cosines.get(f'{names[0]}_vs_{names[2]}', 0):.4f} "
          f"c/a={cosines.get(f'{names[1]}_vs_{names[2]}', 0):.4f} "
          f"| avg={avg:.4f}")
    return cosines, avg


def main():
    session_dir = Path(__file__).parent
    sessions = {
        "warm": session_dir / "scripted_warm_opus_20260318_213202.pt",
        "cold": session_dir / "scripted_cold_clinical_20260318_213401.pt",
        "adversarial": session_dir / "scripted_adversarial_20260318_213439.pt",
    }

    conversations = {}
    for name, pt_path in sessions.items():
        text = load_conversation_text(pt_path)
        conversations[name] = text
        print(f"Loaded {name}: {len(text)} chars")

    print("\nLoading Mamba-2.8B...")
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = "state-spaces/mamba-2.8b-hf"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype)
    if device != "cpu":
        model = model.to(device)
    model.eval()
    print(f"Loaded on {device}")

    # Extract all representations
    print("\nExtracting representations...")
    all_reps = {}
    for name, text in conversations.items():
        print(f"  {name}...", end=" ", flush=True)
        reps = extract_multilayer(model, tokenizer, text, layers=[2, 3, 4, 5])
        all_reps[name] = reps
        print(f"done ({len(reps)} configs)")

    # --- Results ---
    rep_configs = list(all_reps["warm"].keys())

    print(f"\n{'='*100}")
    print("PROBE 2: Single Layer vs Multi-Layer Concat (last token)")
    print(f"{'='*100}")
    print(f"  {'Config':30s} | {'dim':>6s} | {'warm/cold':>8s} {'warm/adv':>8s} {'cold/adv':>8s} | {'avg':>6s}")
    print("-" * 100)

    all_results = {}
    for config in rep_configs:
        if "mean" in config and config != "L3_last1_mean":
            continue  # skip trailing windows for now
        if config.startswith("L") and "last1" in config and "mean" not in config:
            per_session = {name: all_reps[name][config] for name in conversations}
            cosines, avg = print_separation(config, per_session)
            all_results[config] = {"cosines": cosines, "avg": avg, "dim": int(all_reps["warm"][config].shape[0])}

    # Concat
    if "L2_3_4_concat_last1" in rep_configs:
        per_session = {name: all_reps[name]["L2_3_4_concat_last1"] for name in conversations}
        cosines, avg = print_separation("L2_3_4_concat_last1", per_session)
        all_results["L2_3_4_concat_last1"] = {"cosines": cosines, "avg": avg, "dim": int(all_reps["warm"]["L2_3_4_concat_last1"].shape[0])}

    print(f"\n{'='*100}")
    print("PROBE 3: Trailing Token Window (Layer 3)")
    print(f"{'='*100}")
    print(f"  {'Config':30s} | {'dim':>6s} | {'warm/cold':>8s} {'warm/adv':>8s} {'cold/adv':>8s} | {'avg':>6s}")
    print("-" * 100)

    for config in rep_configs:
        if "L3_last" in config and "mean" in config:
            per_session = {name: all_reps[name][config] for name in conversations}
            cosines, avg = print_separation(config, per_session)
            all_results[config] = {"cosines": cosines, "avg": avg, "dim": int(all_reps["warm"][config].shape[0])}

    # --- Verdict ---
    print(f"\n{'='*100}")
    print("VERDICT")
    print(f"{'='*100}")

    baseline = all_results.get("L3_last1", {}).get("avg", 999)
    print(f"\n  Baseline (Layer 3, last token): avg cosine = {baseline:.4f}")
    print(f"  Reference (Pinky): 0.036 warm/cold, 0.025 warm/adv, -0.007 cold/adv")

    for config, data in sorted(all_results.items(), key=lambda x: x[1]["avg"]):
        if config == "L3_last1":
            continue
        delta = data["avg"] - baseline
        better = "BETTER" if delta < -0.005 else "SAME" if abs(delta) < 0.005 else "WORSE"
        print(f"  {config:30s}: avg={data['avg']:.4f} (delta={delta:+.4f}) -> {better}")

    # Save
    out_path = session_dir / "multilayer_probe_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
