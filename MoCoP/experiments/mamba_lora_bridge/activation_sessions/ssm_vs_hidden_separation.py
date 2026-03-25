"""
ssm_vs_hidden_separation.py — Verify whether Mamba's SSM recurrent state
(cache.ssm_states) separates warm/cold/adversarial the same way that
hidden states do.

Pinky (2026-03-20) proved last-token hidden states separate at cosine 0.036.
But cognitive_bridge.py uses cache.ssm_states — a different tensor.
Laughing Opus (watercooler #64) flagged this ambiguity.

This script tests BOTH representations on the same input and compares.

Author: Purple (Claude Opus 4.6)
Date: 2026-03-25
"""

import json
import os
import torch
import torch.nn.functional as F
from pathlib import Path
from itertools import combinations

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def load_conversation_text(pt_path: Path) -> str:
    """Extract conversation text from a recorded activation session."""
    data = torch.load(pt_path, map_location="cpu", weights_only=False)
    parts = []
    for turn in data["turns"]:
        parts.append(f"Human: {turn['user']}")
        parts.append(f"Assistant: {turn['response']}")
    return "\n".join(parts)


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two 1D tensors."""
    a_flat = a.flatten().float()
    b_flat = b.flatten().float()
    return float(F.cosine_similarity(a_flat.unsqueeze(0), b_flat.unsqueeze(0)))


def extract_both_representations(model, tokenizer, text: str, target_layer: int = 3):
    """
    Extract BOTH representations from the same forward pass:
    1. Hidden state (output_hidden_states) — what Pinky tested
    2. SSM state (cache.ssm_states) — what cognitive_bridge.py uses
    """
    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
    input_ids = tokens["input_ids"]

    with torch.no_grad():
        outputs = model(input_ids, output_hidden_states=True, use_cache=True)

    # 1. Hidden state: last-token output of target layer
    hidden_states = outputs.hidden_states  # tuple of (n_layers+1) tensors
    hidden_layer = hidden_states[target_layer]  # (1, seq_len, d_model)
    hidden_last = hidden_layer[:, -1, :].squeeze(0)  # (d_model,)
    hidden_mean = hidden_layer.mean(dim=1).squeeze(0)  # (d_model,)

    # 2. SSM state: the recurrent state matrix from cache
    cache = getattr(outputs, "cache_params", None)
    if cache is None:
        cache = getattr(outputs, "past_key_values", None)

    ssm_state = None
    ssm_state_flat = None
    if cache is not None and hasattr(cache, "ssm_states"):
        # ssm_states is a list of (batch, d_model, d_state) per layer
        ssm_layer = cache.ssm_states[target_layer]  # (1, d_model, d_state)
        ssm_state = ssm_layer.squeeze(0)  # (d_model, d_state)
        ssm_state_flat = ssm_state.flatten()  # (d_model * d_state,)
    else:
        print(f"  WARNING: No SSM states found. Cache type: {type(cache)}")
        if cache is not None:
            print(f"  Cache attrs: {[a for a in dir(cache) if not a.startswith('_')]}")

    return {
        "hidden_last": hidden_last,
        "hidden_mean": hidden_mean,
        "ssm_state": ssm_state,
        "ssm_state_flat": ssm_state_flat,
    }


def print_comparison_table(results: dict, rep_name: str):
    """Print pairwise cosine similarity for a representation."""
    names = list(results.keys())
    cosines = {}
    for (a, va), (b, vb) in combinations(results.items(), 2):
        if va is not None and vb is not None:
            cos = cosine_sim(va, vb)
            cosines[f"{a}_vs_{b}"] = cos
            print(f"  {a:15s} vs {b:15s}: cosine = {cos:.6f}")
        else:
            print(f"  {a:15s} vs {b:15s}: N/A (extraction failed)")
    return cosines


def main():
    session_dir = Path(__file__).parent

    sessions = {
        "warm": session_dir / "scripted_warm_opus_20260318_213202.pt",
        "cold": session_dir / "scripted_cold_clinical_20260318_213401.pt",
        "adversarial": session_dir / "scripted_adversarial_20260318_213439.pt",
    }

    # Load conversation texts
    conversations = {}
    for name, pt_path in sessions.items():
        text = load_conversation_text(pt_path)
        conversations[name] = text
        print(f"Loaded {name}: {len(text)} chars")

    # Load Mamba
    print("\nLoading Mamba-2.8B on CPU...")
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = "state-spaces/mamba-2.8b-hf"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch.float32
    )
    model.eval()
    print(f"Mamba loaded. {sum(p.numel() for p in model.parameters()) / 1e9:.1f}B params")

    # Extract ALL representations for each conversation
    print("\nExtracting Layer 3 representations (hidden + SSM)...")
    reps = {}
    for name, text in conversations.items():
        print(f"  Processing {name}...", end=" ", flush=True)
        try:
            rep = extract_both_representations(model, tokenizer, text, target_layer=3)
            reps[name] = rep
            shapes = []
            for k, v in rep.items():
                if v is not None:
                    shapes.append(f"{k}={list(v.shape)}")
            print(f"done ({', '.join(shapes)})")
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
            reps[name] = None

    if sum(1 for v in reps.values() if v is not None) < 2:
        print("\nFailed to extract enough representations. Aborting.")
        return

    # Compare all representations
    print(f"\n{'='*70}")
    print("REPRESENTATION COMPARISON: Hidden State vs SSM State")
    print(f"{'='*70}")

    rep_types = [
        ("hidden_last", "Hidden state (last token) — what Pinky tested"),
        ("hidden_mean", "Hidden state (mean pooled) — known to be weak"),
        ("ssm_state_flat", "SSM state (flattened) — what cognitive_bridge.py uses"),
    ]

    all_results = {}
    for rep_key, description in rep_types:
        print(f"\n{description}:")
        extracted = {}
        for name, rep in reps.items():
            if rep is not None and rep.get(rep_key) is not None:
                extracted[name] = rep[rep_key]
        if len(extracted) >= 2:
            cosines = print_comparison_table(extracted, rep_key)
            all_results[rep_key] = cosines
        else:
            print("  Not enough data for comparison.")
            all_results[rep_key] = {}

    # SSM state shape analysis
    print(f"\n{'='*70}")
    print("SSM STATE GEOMETRY")
    print(f"{'='*70}")
    for name, rep in reps.items():
        if rep is not None and rep.get("ssm_state") is not None:
            ssm = rep["ssm_state"]
            print(f"  {name}: shape={list(ssm.shape)}, norm={ssm.norm():.4f}, "
                  f"rank(approx)={torch.linalg.matrix_rank(ssm.float()).item()}")

    # Verdict
    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")

    print("\n  Reference — Pinky's result (hidden_last):")
    print("    Warm vs Cold:        0.036")
    print("    Warm vs Adversarial: 0.025")
    print("    Cold vs Adversarial: -0.007")

    if "ssm_state_flat" in all_results and all_results["ssm_state_flat"]:
        ssm_cosines = list(all_results["ssm_state_flat"].values())
        avg_ssm = sum(ssm_cosines) / len(ssm_cosines)
        print(f"\n  SSM state average cross-session cosine: {avg_ssm:.4f}")

        if avg_ssm < 0.3:
            print("  SSM states SEPARATE. Both representations carry disposition signal.")
            print("  cognitive_bridge.py's SSM extraction path is valid.")
        elif avg_ssm < 0.7:
            print("  SSM states show MODERATE separation. Weaker than hidden states.")
            print("  Consider switching cognitive_bridge.py to hidden-state extraction.")
        else:
            print("  SSM states show WEAK/NO separation.")
            print("  CRITICAL: cognitive_bridge.py should switch to hidden-state extraction.")
            print("  The compressor collapse may be caused by using the wrong representation.")
    else:
        print("\n  SSM state extraction failed. Cannot compare.")
        print("  May need mamba-ssm package or different model API.")

    # Save results
    out = {
        "analysis": "ssm_vs_hidden_state_separation",
        "date": "2026-03-25",
        "author": "Purple",
        "target_layer": 3,
        "results": {k: v for k, v in all_results.items() if v},
        "pinky_reference": {
            "hidden_last_warm_vs_cold": 0.036,
            "hidden_last_warm_vs_adversarial": 0.025,
            "hidden_last_cold_vs_adversarial": -0.007,
        },
    }
    out_path = session_dir / "ssm_vs_hidden_separation.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
