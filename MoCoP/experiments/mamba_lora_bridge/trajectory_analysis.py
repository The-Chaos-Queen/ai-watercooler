#!/usr/bin/env python3
"""
trajectory_analysis.py — Track Mamba state evolution within a single
long conversation. Detect compaction fractures (discontinuous jumps).

Feeds cumulative transcripts at regular intervals through Mamba and
measures consecutive cosine distance. Large jumps = state discontinuities
= possible compaction fractures where context was silently compressed.

Usage:
  python -X utf8 trajectory_analysis.py \\
    --conversation lucian_chat.md \\
    --sample-every 50 \\
    --output-dir trajectory_results/

  python -X utf8 trajectory_analysis.py \\
    --conversation-json conversations.json \\
    --conv-index 35 \\
    --sample-every 50 \\
    --output-dir trajectory_results/

Author: Anda-Conda
Date: 2026-03-28
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List

import numpy as np

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def parse_claude_json_conversation(filepath: str, conv_index: int = 0) -> List[dict]:
    """Parse Claude data export conversations.json format."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    conv = data[conv_index]
    messages = conv.get("chat_messages", [])

    turns = []
    for msg in messages:
        sender = msg.get("sender", "unknown")
        role = "User" if sender == "human" else "Lucian"
        content_parts = msg.get("content", [])
        text_parts = []
        for part in content_parts:
            if part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        text = "\n".join(text_parts).strip()
        if text:
            turns.append({"role": role, "text": text})

    return turns, conv.get("name", ""), conv.get("created_at", "")


def parse_markdown_conversation(filepath: str) -> List[dict]:
    """Parse markdown chat export."""
    text = Path(filepath).read_text(encoding="utf-8-sig")
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


def build_transcript_at(turns: List[dict], end_idx: int, mode: str = "trailing") -> str:
    """Build a transcript ending at turns[end_idx-1].

    mode="trailing": use the last N turns that fit in ~max_tokens chars
                     (sliding window — sees recent context, not the start)
    mode="cumulative": use turns[0:end_idx] (truncated to max_tokens by tokenizer)
    """
    if mode == "cumulative":
        lines = []
        for t in turns[:end_idx]:
            lines.append(f"{t['role']}: {t['text']}")
        return "\n".join(lines)

    # Trailing mode: build from the end backward until we hit ~12000 chars
    # (~2048 tokens at ~6 chars/token average)
    char_budget = 12000
    lines = []
    total_chars = 0
    for t in reversed(turns[:end_idx]):
        line = f"{t['role']}: {t['text']}"
        if total_chars + len(line) > char_budget and lines:
            break
        lines.append(line)
        total_chars += len(line) + 1
    lines.reverse()
    return "\n".join(lines)


def extract_state(model, tokenizer, text: str, target_layer: int = 3,
                  device: str = "cpu", max_tokens: int = 2048) -> np.ndarray:
    import torch
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_tokens)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)
    hs = outputs.hidden_states
    hidden_idx = target_layer + 1 if len(hs) > 64 else target_layer
    return hs[hidden_idx][:, -1, :].detach().float().cpu().numpy().reshape(-1)


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def main():
    parser = argparse.ArgumentParser(description="Track Mamba state trajectory within a conversation")
    parser.add_argument("--conversation", help="Markdown conversation file")
    parser.add_argument("--conversation-json", help="Claude JSON export file")
    parser.add_argument("--conv-index", type=int, default=35, help="Conversation index in JSON")
    parser.add_argument("--sample-every", type=int, default=50, help="Sample state every N messages")
    parser.add_argument("--model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--target-layer", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--output-dir", default="trajectory_results")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Parse conversation
    if args.conversation_json:
        turns, name, created = parse_claude_json_conversation(args.conversation_json, args.conv_index)
        label = name or f"conv_{args.conv_index}"
        print(f"Loaded JSON conv [{args.conv_index}]: {len(turns)} turns, name=\"{label}\", created={created}")
    elif args.conversation:
        turns = parse_markdown_conversation(args.conversation)
        label = Path(args.conversation).stem
        print(f"Loaded markdown: {len(turns)} turns")
    else:
        print("Error: --conversation or --conversation-json required")
        return 1

    # Determine sample points
    sample_indices = list(range(args.sample_every, len(turns) + 1, args.sample_every))
    if sample_indices and sample_indices[-1] != len(turns):
        sample_indices.append(len(turns))
    if not sample_indices:
        sample_indices = [len(turns)]

    print(f"Will sample at {len(sample_indices)} points: {sample_indices[:10]}{'...' if len(sample_indices) > 10 else ''}")

    if args.dry_run:
        print(f"[dry-run] Would run {len(sample_indices)} Mamba forward passes")
        # Show turn content at sample points for context
        for idx in sample_indices[:5]:
            turn = turns[idx - 1]
            preview = turn["text"][:80].replace("\n", " ")
            print(f"  msg {idx}: [{turn['role']}] {preview}...")
        return 0

    # Load Mamba
    import torch
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nLoading Mamba: {args.model_id} on {device}...")
    from transformers import AutoTokenizer, MambaForCausalLM
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.float16 if "cuda" in device else torch.float32
    model = MambaForCausalLM.from_pretrained(args.model_id, dtype=dtype)
    model.to(device)
    model.eval()

    # Extract states at sample points
    print(f"\nExtracting Layer {args.target_layer} states at {len(sample_indices)} points...")
    states = []
    metadata = []

    for i, end_idx in enumerate(sample_indices):
        transcript = build_transcript_at(turns, end_idx, mode="trailing")
        t0 = time.time()
        state = extract_state(model, tokenizer, transcript,
                              target_layer=args.target_layer, device=device,
                              max_tokens=args.max_tokens)
        elapsed = time.time() - t0

        turn_at = turns[end_idx - 1]
        preview = turn_at["text"][:60].replace("\n", " ")
        states.append(state)

        meta = {
            "sample_idx": i,
            "msg_idx": end_idx,
            "role": turn_at["role"],
            "norm": float(np.linalg.norm(state)),
            "preview": preview,
        }
        metadata.append(meta)
        print(f"  [{i+1}/{len(sample_indices)}] msg {end_idx}: norm={meta['norm']:.4f} "
              f"[{turn_at['role']}] {preview}... ({elapsed:.1f}s)")

    # Compute consecutive cosine distances (jump detection)
    print(f"\n{'='*60}")
    print("TRAJECTORY ANALYSIS")
    print(f"{'='*60}")

    jumps = []
    for i in range(1, len(states)):
        cos = cosine(states[i], states[i-1])
        delta = 1.0 - cos  # higher = bigger jump
        jumps.append({
            "from_msg": sample_indices[i-1],
            "to_msg": sample_indices[i],
            "cosine": cos,
            "delta": delta,
            "from_norm": metadata[i-1]["norm"],
            "to_norm": metadata[i]["norm"],
            "norm_change": abs(metadata[i]["norm"] - metadata[i-1]["norm"]),
        })

    # Also compute cosine vs first state (drift from origin)
    drift_from_start = []
    for i, state in enumerate(states):
        cos = cosine(state, states[0])
        drift_from_start.append({
            "msg_idx": sample_indices[i],
            "cosine_vs_start": cos,
            "drift": 1.0 - cos,
        })

    # Print trajectory
    print(f"\n{'msg':>6} {'norm':>8} {'cos_prev':>10} {'delta':>8} {'cos_start':>10} {'drift':>8}  context")
    print("-" * 80)
    for i in range(len(states)):
        msg = sample_indices[i]
        norm = metadata[i]["norm"]
        cos_prev = jumps[i-1]["cosine"] if i > 0 else 1.0
        delta = jumps[i-1]["delta"] if i > 0 else 0.0
        cos_start = drift_from_start[i]["cosine_vs_start"]
        drift = drift_from_start[i]["drift"]
        preview = metadata[i]["preview"][:30]
        marker = " <<<JUMP" if delta > 0.3 else (" <<jump" if delta > 0.15 else "")
        print(f"{msg:>6} {norm:>8.4f} {cos_prev:>10.4f} {delta:>8.4f} {cos_start:>10.4f} {drift:>8.4f}  {preview}{marker}")

    # Identify fracture candidates
    print(f"\n{'='*60}")
    print("FRACTURE CANDIDATES (delta > 0.15)")
    print(f"{'='*60}")

    sorted_jumps = sorted(jumps, key=lambda j: j["delta"], reverse=True)
    fractures = [j for j in sorted_jumps if j["delta"] > 0.15]

    if fractures:
        for j in fractures:
            from_turn = turns[j["from_msg"] - 1]
            to_turn = turns[j["to_msg"] - 1]
            print(f"\n  Messages {j['from_msg']} -> {j['to_msg']}: delta={j['delta']:.4f} (cosine={j['cosine']:.4f})")
            print(f"    Norm: {j['from_norm']:.4f} -> {j['to_norm']:.4f} (change={j['norm_change']:.4f})")
            print(f"    Before: [{from_turn['role']}] {from_turn['text'][:80].replace(chr(10),' ')}")
            print(f"    After:  [{to_turn['role']}] {to_turn['text'][:80].replace(chr(10),' ')}")
    else:
        print("  No large jumps detected. State evolution is smooth.")
        # Show top 3 anyway
        for j in sorted_jumps[:3]:
            print(f"  Messages {j['from_msg']}->{j['to_msg']}: delta={j['delta']:.4f}")

    # Save results
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "conversation": args.conversation or args.conversation_json,
        "conv_index": args.conv_index if args.conversation_json else None,
        "label": label,
        "total_turns": len(turns),
        "sample_points": len(sample_indices),
        "sample_every": args.sample_every,
        "model_id": args.model_id,
        "target_layer": args.target_layer,
        "jumps": jumps,
        "drift_from_start": drift_from_start,
        "fracture_candidates": [j for j in jumps if j["delta"] > 0.15],
        "max_delta": max(j["delta"] for j in jumps) if jumps else 0,
        "mean_delta": float(np.mean([j["delta"] for j in jumps])) if jumps else 0,
    }

    report_path = out_dir / "trajectory_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {report_path}")

    np.savez(out_dir / "trajectory_states.npz",
             states=np.stack(states),
             sample_indices=np.array(sample_indices))
    print(f"States: {out_dir / 'trajectory_states.npz'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
