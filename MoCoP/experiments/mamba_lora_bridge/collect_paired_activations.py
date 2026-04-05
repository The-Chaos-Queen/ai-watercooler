#!/usr/bin/env python3
"""
collect_paired_activations.py — Collect paired Mamba L3 + Qwen L13
activations from conversation files for DFC crosscoder training.

Processes each conversation through both models and extracts paired
hidden states at multiple points per conversation.

Output: two .npy files (mamba_activations, qwen_activations) with
matching rows — each row is one turn's paired activation.

Usage:
  python -X utf8 collect_paired_activations.py \
    --conversations conv1.md conv2.md conv3.md \
    --output-dir paired_activations/ \
    --device cuda

  python -X utf8 collect_paired_activations.py \
    --conversations-json lucian.json --conv-index 35 \
    --output-dir paired_activations/ \
    --sample-every 5

OpenCLAW #86 (data collection for DFC crosscoder)
Author: Anda-Conda
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Optional

import numpy as np

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


# ---------------------------------------------------------------------------
# Conversation Parsing (reused from persistent_subnetwork_analysis.py)
# ---------------------------------------------------------------------------

def parse_markdown_conversation(filepath: Path) -> List[dict]:
    text = filepath.read_text(encoding="utf-8-sig")
    lines = text.split("\n")
    turns = []
    current_role = None
    current_lines = []
    for line in lines:
        m = re.match(r"^##\s+(.+)$", line.strip())
        if m:
            if current_role is not None:
                turn_text = "\n".join(current_lines).strip()
                if turn_text:
                    turns.append({"role": current_role, "text": turn_text})
            current_role = m.group(1).strip()
            current_lines = []
        elif re.match(r"^---\s*$", line.strip()):
            continue
        elif line.startswith("# ") and not line.startswith("## "):
            continue
        else:
            if current_role is not None:
                current_lines.append(line)
    if current_role is not None:
        turn_text = "\n".join(current_lines).strip()
        if turn_text:
            turns.append({"role": current_role, "text": turn_text})
    return turns


def parse_claude_json(filepath: str, conv_index: int) -> List[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    conv = data[conv_index]
    turns = []
    for msg in conv.get("chat_messages", []):
        sender = msg.get("sender", "unknown")
        role = "User" if sender == "human" else "Assistant"
        text = "".join(
            p.get("text", "") for p in msg.get("content", []) if p.get("type") == "text"
        ).strip()
        if text:
            turns.append({"role": role, "text": text})
    return turns


def build_cumulative_transcript(turns: List[dict], end_idx: int) -> str:
    lines = []
    for t in turns[:end_idx]:
        lines.append(f"{t['role']}: {t['text']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model Loading
# ---------------------------------------------------------------------------

def load_mamba(model_id: str, device: str):
    import torch
    from transformers import AutoTokenizer, MambaForCausalLM

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.float16 if "cuda" in device else torch.float32
    model = MambaForCausalLM.from_pretrained(model_id, dtype=dtype)
    model.to(device)
    model.eval()
    return model, tokenizer


def load_qwen(model_id: str, device: str):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.float16 if "cuda" in device else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=dtype, device_map=device
    )
    model.eval()
    return model, tokenizer


# ---------------------------------------------------------------------------
# Activation Extraction
# ---------------------------------------------------------------------------

def extract_mamba_l3(model, tokenizer, text: str, device: str, max_tokens: int = 2048) -> np.ndarray:
    import torch
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_tokens)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)
    hs = outputs.hidden_states
    hidden_idx = 4 if len(hs) > 64 else 3  # Layer 3 (0-indexed + embedding)
    return hs[hidden_idx][:, -1, :].detach().float().cpu().numpy().reshape(-1)


def extract_qwen_l13(model, tokenizer, text: str, device: str, max_tokens: int = 2048) -> np.ndarray:
    import torch
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_tokens)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)
    hs = outputs.hidden_states
    # Qwen 1.5B: 28 layers + embedding = 29 hidden states
    # Layer 13 is index 14 (0=embedding, 1=layer0, ...)
    layer_idx = min(14, len(hs) - 1)
    return hs[layer_idx][:, -1, :].detach().float().cpu().numpy().reshape(-1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Collect paired Mamba+Qwen activations")
    parser.add_argument("--conversations", nargs="+", help="Markdown conversation files")
    parser.add_argument("--conversations-json", help="Claude JSON export")
    parser.add_argument("--conv-index", type=int, default=0)
    parser.add_argument("--labels", nargs="+", help="Labels for each conversation")
    parser.add_argument("--sample-every", type=int, default=5,
                        help="Sample paired activations every N turns")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--mamba-model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--qwen-model-id", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-dir", default="paired_activations")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Parse conversations
    all_turns = []
    if args.conversations:
        for filepath in args.conversations:
            path = Path(filepath)
            if path.exists():
                turns = parse_markdown_conversation(path)
                label = path.stem
                all_turns.append((label, turns))
                print(f"  {label}: {len(turns)} turns")
    elif args.conversations_json:
        turns = parse_claude_json(args.conversations_json, args.conv_index)
        all_turns.append((f"conv_{args.conv_index}", turns))
        print(f"  conv_{args.conv_index}: {len(turns)} turns")
    else:
        print("Error: --conversations or --conversations-json required")
        return 1

    # Calculate total sample points
    total_samples = 0
    for label, turns in all_turns:
        indices = list(range(args.sample_every, len(turns) + 1, args.sample_every))
        if indices and indices[-1] != len(turns):
            indices.append(len(turns))
        total_samples += len(indices)

    print(f"\nTotal conversations: {len(all_turns)}")
    print(f"Total sample points: {total_samples}")

    if args.dry_run:
        print(f"[dry-run] Would extract {total_samples} paired activations")
        return 0

    # Load models
    import torch
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # Build all transcripts up front
    all_transcripts = []
    for label, turns in all_turns:
        indices = list(range(args.sample_every, len(turns) + 1, args.sample_every))
        if indices and indices[-1] != len(turns):
            indices.append(len(turns))
        for end_idx in indices:
            transcript = build_cumulative_transcript(turns, end_idx)
            all_transcripts.append({"label": label, "end_idx": end_idx, "text": transcript})

    print(f"\n{len(all_transcripts)} transcripts prepared")

    # Pass 1: Mamba (load, extract, unload)
    print(f"\n--- Pass 1: Mamba ({args.mamba_model_id}) on {device} ---")
    mamba_model, mamba_tok = load_mamba(args.mamba_model_id, device)
    mamba_acts = []
    for i, item in enumerate(all_transcripts):
        t0 = time.time()
        vec = extract_mamba_l3(mamba_model, mamba_tok, item["text"], device, args.max_tokens)
        mamba_acts.append(vec)
        elapsed = time.time() - t0
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  [{i+1}/{len(all_transcripts)}] {item['label']} turn {item['end_idx']}: "
                  f"norm={np.linalg.norm(vec):.4f} ({elapsed:.1f}s)")

    # Free Mamba VRAM
    del mamba_model, mamba_tok
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"  Mamba unloaded")

    # Pass 2: Qwen (load, extract, unload)
    print(f"\n--- Pass 2: Qwen ({args.qwen_model_id}) on {device} ---")
    qwen_model, qwen_tok = load_qwen(args.qwen_model_id, device)
    qwen_acts = []
    for i, item in enumerate(all_transcripts):
        t0 = time.time()
        vec = extract_qwen_l13(qwen_model, qwen_tok, item["text"], device, args.max_tokens)
        qwen_acts.append(vec)
        elapsed = time.time() - t0
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  [{i+1}/{len(all_transcripts)}] {item['label']} turn {item['end_idx']}: "
                  f"norm={np.linalg.norm(vec):.4f} ({elapsed:.1f}s)")

    del qwen_model, qwen_tok
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"  Qwen unloaded")

    # Build metadata
    metadata = []
    for i, item in enumerate(all_transcripts):
        metadata.append({
            "label": item["label"],
            "end_idx": item["end_idx"],
            "mamba_norm": float(np.linalg.norm(mamba_acts[i])),
            "qwen_norm": float(np.linalg.norm(qwen_acts[i])),
        })

    # Save
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mamba_array = np.stack(mamba_acts)
    qwen_array = np.stack(qwen_acts)

    np.save(out_dir / "mamba_l3_activations.npy", mamba_array)
    np.save(out_dir / "qwen_l13_activations.npy", qwen_array)
    (out_dir / "paired_metadata.json").write_text(
        json.dumps({"samples": len(metadata), "metadata": metadata}, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved {len(mamba_acts)} paired activations:")
    print(f"  Mamba L3:  {mamba_array.shape} -> {out_dir / 'mamba_l3_activations.npy'}")
    print(f"  Qwen L13:  {qwen_array.shape} -> {out_dir / 'qwen_l13_activations.npy'}")
    print(f"  Metadata: {out_dir / 'paired_metadata.json'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
