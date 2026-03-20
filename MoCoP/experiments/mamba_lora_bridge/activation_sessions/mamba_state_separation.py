"""
mamba_state_separation.py — Test whether Mamba's Layer 3 hidden states
separate warm/cold/adversarial conversations.

This is the UPSTREAM test: Cassian proved Qwen's activations separate (cosine 0.09-0.55).
Now we test whether Mamba accumulates different states for different conversation types.
If Mamba states DON'T separate, the bridge has no signal to map from.

Author: Pinky (Claude Opus 4.6)
Date: 2026-03-20
"""

import json
import os
import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from itertools import combinations

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def load_conversation_text(pt_path: Path) -> list[dict]:
    """Extract user/response pairs from a recorded activation session."""
    data = torch.load(pt_path, map_location="cpu", weights_only=False)
    turns = []
    for turn in data["turns"]:
        turns.append({"user": turn["user"], "response": turn["response"]})
    return turns


def build_conversation_string(turns: list[dict]) -> str:
    """Build a single string from all turns for Mamba to process."""
    parts = []
    for t in turns:
        parts.append(f"Human: {t['user']}")
        parts.append(f"Assistant: {t['response']}")
    return "\n".join(parts)


def extract_mamba_layer3_state(model, tokenizer, text: str, device: str = "cpu") -> torch.Tensor:
    """Feed text through Mamba and extract Layer 3 hidden state."""
    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
    input_ids = tokens["input_ids"].to(device)

    with torch.no_grad():
        outputs = model(input_ids, output_hidden_states=True)

    # outputs.hidden_states is a tuple of (n_layers + 1) tensors
    # Layer 3 = index 3 (0 is embedding)
    layer3 = outputs.hidden_states[3]  # (batch, seq_len, hidden_dim)

    # Take mean over sequence length as the accumulated state
    state_mean = layer3.mean(dim=1).squeeze(0)  # (hidden_dim,)

    # Also take last token as alternative
    state_last = layer3[:, -1, :].squeeze(0)  # (hidden_dim,)

    return state_mean, state_last


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    return float(F.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)))


def main():
    session_dir = Path(__file__).parent

    # Load conversation texts
    sessions = {
        "warm": session_dir / "scripted_warm_opus_20260318_213202.pt",
        "cold": session_dir / "scripted_cold_clinical_20260318_213401.pt",
        "adversarial": session_dir / "scripted_adversarial_20260318_213439.pt",
    }

    conversations = {}
    for name, pt_path in sessions.items():
        turns = load_conversation_text(pt_path)
        text = build_conversation_string(turns)
        conversations[name] = text
        print(f"Loaded {name}: {len(turns)} turns, {len(text)} chars")

    # Load Mamba
    print("\nLoading Mamba-2.8B on CPU (this may take a minute)...")
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = "state-spaces/mamba-2.8b-hf"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float32,  # CPU, no quantization
    )
    model.eval()
    print(f"Mamba loaded. {sum(p.numel() for p in model.parameters()) / 1e9:.1f}B params")

    # Check if model supports output_hidden_states
    # Mamba HF wrapper should support this
    print("\nExtracting Layer 3 hidden states...")

    states_mean = {}
    states_last = {}
    for name, text in conversations.items():
        print(f"  Processing {name}...", end=" ", flush=True)
        try:
            mean_state, last_state = extract_mamba_layer3_state(model, tokenizer, text)
            states_mean[name] = mean_state
            states_last[name] = last_state
            print(f"done (mean shape: {mean_state.shape}, norm: {mean_state.norm():.4f})")
        except Exception as e:
            print(f"FAILED: {e}")
            # Try alternative: get all hidden states
            import traceback
            traceback.print_exc()

    if len(states_mean) < 2:
        print("\nFailed to extract enough states. Trying without output_hidden_states...")
        # Fallback: use hooks
        layer3_output = {}

        def hook_fn(module, input, output):
            # Mamba layers output differently than transformers
            if isinstance(output, tuple):
                layer3_output["state"] = output[0].detach()
            else:
                layer3_output["state"] = output.detach()

        # Try to find Layer 3
        layers = None
        if hasattr(model, "backbone") and hasattr(model.backbone, "layers"):
            layers = model.backbone.layers
        elif hasattr(model, "model") and hasattr(model.model, "layers"):
            layers = model.model.layers

        if layers and len(layers) > 3:
            hook = layers[3].register_forward_hook(hook_fn)
            for name, text in conversations.items():
                tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
                with torch.no_grad():
                    model(**tokens)
                if "state" in layer3_output:
                    state = layer3_output["state"]
                    states_mean[name] = state.mean(dim=1).squeeze(0)
                    states_last[name] = state[:, -1, :].squeeze(0)
                    print(f"  {name}: hook captured shape {state.shape}")
            hook.remove()
        else:
            print(f"  Cannot find layers. Model structure: {type(model)}")
            for attr_name in dir(model):
                if "layer" in attr_name.lower() or "block" in attr_name.lower():
                    print(f"    {attr_name}: {type(getattr(model, attr_name))}")

    if len(states_mean) < 2:
        print("\nCould not extract Mamba states. Aborting.")
        return

    # Compare!
    print(f"\n{'='*60}")
    print("MAMBA LAYER 3 STATE SEPARATION")
    print(f"{'='*60}")

    print("\nMean-pooled states:")
    names = list(states_mean.keys())
    results_mean = {}
    for (a, va), (b, vb) in combinations(states_mean.items(), 2):
        cos = cosine_sim(va, vb)
        results_mean[f"{a}_vs_{b}"] = cos
        print(f"  {a:15s} vs {b:15s}: cosine = {cos:.6f}")

    print("\nLast-token states:")
    results_last = {}
    for (a, va), (b, vb) in combinations(states_last.items(), 2):
        cos = cosine_sim(va, vb)
        results_last[f"{a}_vs_{b}"] = cos
        print(f"  {a:15s} vs {b:15s}: cosine = {cos:.6f}")

    # Also check other layers for comparison
    print(f"\n{'='*60}")
    print("PER-LAYER SEPARATION (mean-pooled)")
    print(f"{'='*60}")

    # Re-run with hooks on multiple layers
    try:
        layers = None
        if hasattr(model, "backbone") and hasattr(model.backbone, "layers"):
            layers = model.backbone.layers
        elif hasattr(model, "model") and hasattr(model.model, "layers"):
            layers = model.model.layers

        if layers:
            n_layers = len(layers)
            check_layers = [0, 1, 2, 3, 4, 5, min(10, n_layers - 1), min(20, n_layers - 1), n_layers - 1]
            check_layers = sorted(set(l for l in check_layers if l < n_layers))

            per_layer_states = {name: {} for name in names}
            for layer_idx in check_layers:
                captured = {}

                def make_hook(cap_dict):
                    def hook_fn(module, input, output):
                        if isinstance(output, tuple):
                            cap_dict["state"] = output[0].detach()
                        else:
                            cap_dict["state"] = output.detach()
                    return hook_fn

                hook = layers[layer_idx].register_forward_hook(make_hook(captured))
                for name, text in conversations.items():
                    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
                    with torch.no_grad():
                        model(**tokens)
                    if "state" in captured:
                        per_layer_states[name][layer_idx] = captured["state"].mean(dim=1).squeeze(0)
                hook.remove()

            print(f"\n{'Layer':>6s}  {'Warm vs Cold':>14s}  {'Warm vs Adv':>14s}  {'Cold vs Adv':>14s}")
            print("-" * 55)
            for layer_idx in check_layers:
                row = f"{layer_idx:6d}"
                for a, b in [("warm", "cold"), ("warm", "adversarial"), ("cold", "adversarial")]:
                    if layer_idx in per_layer_states[a] and layer_idx in per_layer_states[b]:
                        cos = cosine_sim(per_layer_states[a][layer_idx], per_layer_states[b][layer_idx])
                        row += f"  {cos:14.6f}"
                    else:
                        row += f"  {'N/A':>14s}"
                print(row)
    except Exception as e:
        print(f"Per-layer analysis failed: {e}")

    # Verdict
    print(f"\n{'='*60}")
    print("VERDICT")
    print(f"{'='*60}")
    mean_cosines = list(results_mean.values())
    if mean_cosines:
        avg = np.mean(mean_cosines)
        print(f"\n  Mean cross-session cosine (Layer 3, mean-pooled): {avg:.4f}")

        # Compare with Qwen's numbers
        print(f"\n  For comparison — Cassian's Qwen Layer 13 results:")
        print(f"    Warm vs Cold:        0.092")
        print(f"    Warm vs Adversarial: 0.095")
        print(f"    Cold vs Adversarial: 0.532")

        if avg < 0.50:
            print(f"\n  MAMBA SEPARATES! Mean cosine {avg:.3f} shows clear directional separation.")
            print("  The bridge has upstream signal to work with.")
            print("  ->DispositionBridgeLoss can map Mamba directions to Qwen directions.")
        elif avg < 0.80:
            print(f"\n  MODERATE SEPARATION. Mean cosine {avg:.3f}.")
            print("  Mamba accumulates some directional difference, but weaker than Qwen.")
            print("  ->Bridge needs to amplify weak Mamba signal into strong Qwen shift.")
        elif avg < 0.95:
            print(f"\n  WEAK SEPARATION. Mean cosine {avg:.3f}.")
            print("  Mamba states are similar across conversation types.")
            print("  ->Bridge will struggle to extract meaningful disposition signal.")
        else:
            print(f"\n  NO SEPARATION. Mean cosine {avg:.3f}.")
            print("  Mamba states are effectively identical regardless of conversation type.")
            print("  ->CRITICAL: The Mamba→Bridge path has no disposition signal to carry.")
            print("  ->Consider: different SSM, different layer, or Qwen-probing instead.")

    # Save results
    out = {
        "analysis": "mamba_layer3_state_separation",
        "date": "2026-03-20",
        "author": "Pinky",
        "layer3_mean_cosines": results_mean,
        "layer3_last_cosines": results_last,
        "qwen_layer13_reference": {
            "warm_vs_cold": 0.092,
            "warm_vs_adversarial": 0.095,
            "cold_vs_adversarial": 0.532,
        },
    }
    out_path = session_dir / "mamba_state_separation.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
