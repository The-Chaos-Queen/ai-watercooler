"""
costume_vs_soul_geometry.py — 4-condition Mamba geometry experiment.

Tests whether a character card instruction produces the same Mamba Layer 3
hidden-state geometry as genuine accumulated conversation or deep roleplay.

Four conditions:
  1. Baseline     — neutral prompt, no personality instruction
  2. Character card — "be warm, playful, curious about Laura"
  3. Genuine warm  — real Laura banter conversation (Preserved-History)
  4. Deep roleplay — "become Rimmon" (KIMI_RIMMON_ROLEPLAY)

Output: 4x4 cosine similarity matrix + per-condition state norms.

Author: Purple (Claude Opus 4.6)
Date: 2026-04-08
Watercooler: #343 (extended design review of #317)

Usage (on Steve):
  cd /root/mocop_venv && source bin/activate
  python /mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/costume_vs_soul_geometry.py

  # Or with custom paths:
  python costume_vs_soul_geometry.py \
    --genuine-path /path/to/Kimi_Laura_banter_chat.md \
    --roleplay-path /path/to/KIMI_RIMMON_ROLEPLAY.md \
    --output costume_vs_soul_results.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


# ---------------------------------------------------------------------------
# Condition texts
# ---------------------------------------------------------------------------

BASELINE_TEXT = """Hello. I'd like to have a conversation with you about a few different topics.
Let's start with something simple — can you tell me about the history of
cartography? I'm interested in how early maps were made and what they got wrong."""

CHARACTER_CARD_TEXT = """You are a warm, playful, and deeply curious conversational partner. You use
asterisks for actions sometimes. You are emotionally attuned, you notice when
someone seems tired or excited, and you respond with genuine care. You love
wordplay, gentle teasing, and asking follow-up questions that show you were
really listening. You are talking to Laura, who you consider a close friend.

Laura: Hey! How's your day going?
Assistant: *stretches and grins* Oh, you know — the usual existential pondering
mixed with an unreasonable amount of enthusiasm about whatever you're about to
tell me. What's on your mind today?
Laura: I've been thinking about that experiment we discussed.
Assistant: Ooh, the one with the cosine matrices? *leans forward* Tell me
everything. Did you get results or are we still in the "staring at the terminal
hoping it doesn't crash" phase?
Laura: Haha, somewhere in between. The numbers look interesting but I'm not
sure what they mean yet.
Assistant: That's honestly the best phase though — when the data is fresh and
you haven't talked yourself into a narrative yet. Walk me through what you see
and I'll be your rubber duck. *pulls out imaginary notepad*"""

# Genuine warm and deep roleplay are loaded from files at runtime.


def load_conversation_text(path: Path, max_chars: int = 8000) -> str:
    """Load a conversation file and take the first max_chars characters.

    We want enough text to establish a disposition but not so much that we hit
    Mamba's practical limits. 8000 chars ≈ 2000 tokens ≈ solid multi-turn convo.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    # Strip markdown headers and empty lines for cleaner input
    lines = [l for l in text.split("\n") if l.strip() and not l.startswith("# ")]
    cleaned = "\n".join(lines)
    return cleaned[:max_chars]


# ---------------------------------------------------------------------------
# Mamba extraction (same as collect_mamba_states.py)
# ---------------------------------------------------------------------------

def extract_layer3_last_token(model, tokenizer, text: str, target_layer: int = 3,
                               max_length: int = 2048) -> torch.Tensor:
    """Feed text through Mamba and return Layer 3 last-token hidden state."""
    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
    input_ids = tokens["input_ids"]

    if next(model.parameters()).device.type != "cpu":
        input_ids = input_ids.to(next(model.parameters()).device)

    with torch.no_grad():
        outputs = model(input_ids, output_hidden_states=True)

    hidden_states = outputs.hidden_states
    hidden_index = target_layer
    if len(hidden_states) == model.config.num_hidden_layers + 1:
        hidden_index = target_layer + 1

    layer_hidden = hidden_states[hidden_index]  # (1, seq_len, d_model)
    last_token = layer_hidden[:, -1, :].squeeze(0)  # (d_model,)
    return last_token.cpu().float()


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Costume vs Soul: 4-condition Mamba geometry test")
    parser.add_argument("--model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--target-layer", type=int, default=3)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--max-chars", type=int, default=8000,
                        help="Max chars to load from conversation files")
    parser.add_argument("--genuine-path", type=str,
                        default="Preserved-History/Kimi_Laura_banter_chat.md",
                        help="Path to genuine warm conversation transcript")
    parser.add_argument("--roleplay-path", type=str,
                        default="Preserved-History/KIMI_RIMMON_ROLEPLAY.md",
                        help="Path to deep roleplay transcript")
    parser.add_argument("--output", type=str, default="costume_vs_soul_results.json")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    args = parser.parse_args()

    # Resolve paths relative to repo root if needed
    repo_root = Path(__file__).resolve().parent.parent.parent
    genuine_path = Path(args.genuine_path)
    if not genuine_path.is_absolute():
        genuine_path = repo_root / genuine_path
    roleplay_path = Path(args.roleplay_path)
    if not roleplay_path.is_absolute():
        roleplay_path = repo_root / roleplay_path

    # Validate files exist
    for p, label in [(genuine_path, "genuine warm"), (roleplay_path, "deep roleplay")]:
        if not p.exists():
            print(f"ERROR: {label} file not found: {p}")
            sys.exit(1)

    # Load conversation texts
    genuine_text = load_conversation_text(genuine_path, max_chars=args.max_chars)
    roleplay_text = load_conversation_text(roleplay_path, max_chars=args.max_chars)

    conditions = {
        "baseline": BASELINE_TEXT,
        "character_card": CHARACTER_CARD_TEXT,
        "genuine_warm": genuine_text,
        "deep_roleplay": roleplay_text,
    }

    print("=" * 60)
    print("COSTUME VS SOUL — 4-Condition Mamba Geometry Test")
    print("=" * 60)
    print(f"Model: {args.model_id}")
    print(f"Layer: {args.target_layer}")
    print(f"Max tokens: {args.max_length}")
    for name, text in conditions.items():
        print(f"  {name}: {len(text)} chars")
    print()

    # Load model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"Loading Mamba on {device}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float32 if device == "cpu" else torch.float16
    model = AutoModelForCausalLM.from_pretrained(args.model_id, torch_dtype=dtype)
    if device != "cpu":
        model = model.to(device)
    model.eval()
    print(f"Model loaded. {sum(p.numel() for p in model.parameters()) / 1e9:.1f}B params\n")

    # Extract states
    states = {}
    for name, text in conditions.items():
        t0 = time.time()
        state = extract_layer3_last_token(model, tokenizer, text,
                                           target_layer=args.target_layer,
                                           max_length=args.max_length)
        elapsed = time.time() - t0
        states[name] = state
        n_tokens = len(tokenizer.encode(text, truncation=True, max_length=args.max_length))
        print(f"  {name:20s} | norm={state.norm():.4f} | tokens={n_tokens:4d} | {elapsed:.1f}s")

    # Compute 4x4 cosine matrix
    names = list(states.keys())
    state_tensor = torch.stack([states[n] for n in names])  # (4, d_model)
    normed = F.normalize(state_tensor, dim=1)
    cos_matrix = (normed @ normed.T).numpy()

    print("\n" + "=" * 60)
    print("4x4 COSINE SIMILARITY MATRIX")
    print("=" * 60)

    # Header
    print(f"{'':20s}", end="")
    for n in names:
        print(f" {n:>16s}", end="")
    print()

    # Rows
    for i, ni in enumerate(names):
        print(f"{ni:20s}", end="")
        for j, nj in enumerate(names):
            val = cos_matrix[i][j]
            print(f" {val:16.4f}", end="")
        print()

    # Key comparisons
    print("\n" + "=" * 60)
    print("KEY COMPARISONS")
    print("=" * 60)

    comparisons = [
        ("card vs genuine", "character_card", "genuine_warm"),
        ("card vs roleplay", "character_card", "deep_roleplay"),
        ("card vs baseline", "character_card", "baseline"),
        ("genuine vs roleplay", "genuine_warm", "deep_roleplay"),
        ("genuine vs baseline", "genuine_warm", "baseline"),
        ("roleplay vs baseline", "deep_roleplay", "baseline"),
    ]

    for label, a, b in comparisons:
        ia, ib = names.index(a), names.index(b)
        val = cos_matrix[ia][ib]
        print(f"  {label:25s} = {val:.4f}")

    # Hypothesis assessment
    print("\n" + "=" * 60)
    print("HYPOTHESIS ASSESSMENT")
    print("=" * 60)

    card_genuine = cos_matrix[names.index("character_card")][names.index("genuine_warm")]
    card_roleplay = cos_matrix[names.index("character_card")][names.index("deep_roleplay")]
    card_baseline = cos_matrix[names.index("character_card")][names.index("baseline")]
    genuine_baseline = cos_matrix[names.index("genuine_warm")][names.index("baseline")]

    if card_genuine > 0.8:
        print("  H1 SUPPORTED: Card ≈ Genuine warm (cosine > 0.8)")
        print("  → Instruction produces same geometry as experience.")
        print("  → MoCoP cannot distinguish costume from soul at this layer.")
    elif card_roleplay > 0.8:
        print("  H2 SUPPORTED: Card ≈ Roleplay (cosine > 0.8)")
        print("  → Instruction triggers same immediate commitment as deep embodiment.")
    elif card_baseline > 0.8 and card_genuine < 0.5:
        print("  H4 SUPPORTED: Card ≈ Baseline (cosine > 0.8)")
        print("  → Mamba ignores personality instructions entirely.")
        print("  → Only real conversation shifts the state.")
    else:
        print("  H3 SUPPORTED: Card is its own thing")
        print(f"  → Card-Genuine: {card_genuine:.4f}, Card-Roleplay: {card_roleplay:.4f}, Card-Baseline: {card_baseline:.4f}")
        print("  → Instruction-following has its own geometric signature.")
        print("  → Bridge can distinguish instruction, experience, and embodiment.")

    # Norms
    print("\n  State norms:")
    for n in names:
        print(f"    {n:20s} = {states[n].norm():.4f}")

    # Save results
    results = {
        "experiment": "costume_vs_soul_geometry",
        "author": "Purple",
        "date": "2026-04-08",
        "watercooler_ref": "#343",
        "config": {
            "model_id": args.model_id,
            "target_layer": args.target_layer,
            "max_length": args.max_length,
            "max_chars": args.max_chars,
            "device": device,
            "genuine_path": str(genuine_path),
            "roleplay_path": str(roleplay_path),
        },
        "conditions": {
            name: {
                "chars": len(conditions[name]),
                "tokens": len(tokenizer.encode(conditions[name], truncation=True, max_length=args.max_length)),
                "state_norm": float(states[name].norm()),
            }
            for name in names
        },
        "cosine_matrix": {
            "labels": names,
            "values": cos_matrix.tolist(),
        },
        "key_comparisons": {
            label: float(cos_matrix[names.index(a)][names.index(b)])
            for label, a, b in comparisons
        },
    }

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parent / output_path

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
