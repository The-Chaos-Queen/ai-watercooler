#!/usr/bin/env python3
"""
trajectory_sequential.py — Full sequential Mamba pass without truncation.

Feeds the conversation through Mamba as one continuous sequence,
extracting the recurrent hidden state at regular message intervals.
No windowing, no truncation. The state accumulates naturally.

This is the control experiment for trajectory_analysis.py (windowed).
If this produces a smooth drift curve where windowed was chaotic,
that proves MoCoP's bridge is needed to carry the accumulated state.

Author: Anda-Conda
Date: 2026-03-28
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List

import numpy as np

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def parse_claude_json(filepath: str, conv_index: int) -> List[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    conv = data[conv_index]
    turns = []
    for msg in conv.get("chat_messages", []):
        sender = msg.get("sender", "unknown")
        role = "User" if sender == "human" else "Assistant"
        text = "".join(p.get("text", "") for p in msg.get("content", []) if p.get("type") == "text").strip()
        if text:
            turns.append({"role": role, "text": text})
    return turns, conv.get("name", ""), conv.get("created_at", "")


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def main():
    parser = argparse.ArgumentParser(description="Full sequential Mamba trajectory (no truncation)")
    parser.add_argument("--conversation-json", required=True)
    parser.add_argument("--conv-index", type=int, default=35)
    parser.add_argument("--max-messages", type=int, default=100)
    parser.add_argument("--sample-every", type=int, default=10)
    parser.add_argument("--model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--target-layer", type=int, default=3)
    parser.add_argument("--output-dir", default="trajectory_sequential_results")
    args = parser.parse_args()

    turns, name, created = parse_claude_json(args.conversation_json, args.conv_index)
    turns = turns[:args.max_messages]
    print(f"Conversation: {name or f'conv_{args.conv_index}'}")
    print(f"Using first {len(turns)} messages")

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

    # Build the FULL transcript up front, tokenize once
    full_text = "\n".join(f"{t['role']}: {t['text']}" for t in turns)
    print(f"Full transcript: {len(full_text):,} chars")

    tokens = tokenizer(full_text, return_tensors="pt")
    input_ids = tokens["input_ids"].to(device)
    total_tokens = input_ids.shape[1]
    print(f"Tokenized: {total_tokens:,} tokens")

    # Find token positions corresponding to message boundaries
    # Build cumulative text and find where each message ends in token space
    msg_boundaries = []
    cumulative = ""
    for i, t in enumerate(turns):
        cumulative += f"{t['role']}: {t['text']}\n"
        if (i + 1) % args.sample_every == 0 or i == len(turns) - 1:
            # Tokenize cumulative to find the token position
            cum_tokens = tokenizer(cumulative, return_tensors="pt")["input_ids"].shape[1]
            msg_boundaries.append({
                "msg_idx": i + 1,
                "token_pos": min(cum_tokens, total_tokens),
                "role": t["role"],
                "preview": t["text"][:60].replace("\n", " "),
            })

    print(f"Will extract state at {len(msg_boundaries)} points")

    # Chunked forward pass with cache carry-forward
    # Process 512 tokens at a time, pass Mamba cache between chunks
    # This uses O(chunk_size) memory instead of O(seq_len)
    chunk_size = 512
    print(f"\nRunning chunked sequential pass ({total_tokens:,} tokens, chunk={chunk_size})...")
    t0 = time.time()

    # Build set of token positions where we need to extract state
    boundary_token_set = {min(b["token_pos"] - 1, total_tokens - 1): b for b in msg_boundaries}

    cache = None
    states = []
    metadata = []
    tokens_processed = 0

    for chunk_start in range(0, total_tokens, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_tokens)
        chunk_ids = input_ids[:, chunk_start:chunk_end]

        with torch.no_grad():
            kwargs = {"output_hidden_states": True}
            if cache is not None:
                cache_pos = torch.arange(chunk_start, chunk_end, device=device)
                kwargs["cache_params"] = cache
                kwargs["cache_position"] = cache_pos
            outputs = model(chunk_ids, **kwargs)
            cache = outputs.cache_params

        # Check if any boundaries fall in this chunk
        hs = outputs.hidden_states
        hidden_idx = args.target_layer + 1 if len(hs) > 64 else args.target_layer
        chunk_hidden = hs[hidden_idx][0]  # (chunk_len, d_model)

        for abs_pos, boundary in boundary_token_set.items():
            if chunk_start <= abs_pos < chunk_end:
                local_pos = abs_pos - chunk_start
                state = chunk_hidden[local_pos].detach().float().cpu().numpy().reshape(-1)
                states.append(state)
                metadata.append({
                    "msg_idx": boundary["msg_idx"],
                    "token_pos": abs_pos,
                    "norm": float(np.linalg.norm(state)),
                    "role": boundary["role"],
                    "preview": boundary["preview"],
                })
                print(f"  msg {boundary['msg_idx']:>4} (tok {abs_pos:>6}): "
                      f"norm={metadata[-1]['norm']:.4f} [{boundary['role']}]")

        tokens_processed = chunk_end
        if tokens_processed % (chunk_size * 10) == 0 or chunk_end == total_tokens:
            elapsed_so_far = time.time() - t0
            print(f"  ... {tokens_processed:,}/{total_tokens:,} tokens "
                  f"({elapsed_so_far:.1f}s, {tokens_processed/elapsed_so_far:.0f} tok/s)")

    elapsed = time.time() - t0
    print(f"Chunked pass complete: {elapsed:.1f}s ({total_tokens/elapsed:.0f} tok/s)")

    # Compute consecutive distances and drift
    print(f"\n{'='*60}")
    print("SEQUENTIAL TRAJECTORY (no truncation)")
    print(f"{'='*60}")

    jumps = []
    for i in range(1, len(states)):
        cos = cosine(states[i], states[i-1])
        delta = 1.0 - cos
        jumps.append({
            "from_msg": metadata[i-1]["msg_idx"],
            "to_msg": metadata[i]["msg_idx"],
            "cosine": cos,
            "delta": delta,
        })

    drift = []
    for i, state in enumerate(states):
        cos = cosine(state, states[0])
        drift.append({
            "msg_idx": metadata[i]["msg_idx"],
            "cosine_vs_start": cos,
            "drift": 1.0 - cos,
        })

    print(f"\n{'msg':>5} {'norm':>7} {'cos_prev':>9} {'delta':>7} {'cos_start':>10} {'drift':>7}")
    print("-" * 55)
    for i in range(len(states)):
        msg = metadata[i]["msg_idx"]
        norm = metadata[i]["norm"]
        cp = jumps[i-1]["cosine"] if i > 0 else 1.0
        d = jumps[i-1]["delta"] if i > 0 else 0.0
        cs = drift[i]["cosine_vs_start"]
        dr = drift[i]["drift"]
        marker = " <<<" if d > 0.15 else ""
        print(f"{msg:>5} {norm:>7.3f} {cp:>9.4f} {d:>7.4f} {cs:>10.4f} {dr:>7.4f}{marker}")

    # Summary stats
    if jumps:
        deltas = [j["delta"] for j in jumps]
        print(f"\nMean delta: {np.mean(deltas):.4f}")
        print(f"Max delta:  {max(deltas):.4f}")
        print(f"Min delta:  {min(deltas):.4f}")
        print(f"Std delta:  {np.std(deltas):.4f}")

        # Compare to windowed result
        print(f"\nCOMPARISON:")
        print(f"  Windowed (trajectory_analysis.py): mean delta ~0.83")
        print(f"  Sequential (this run):             mean delta {np.mean(deltas):.4f}")
        if np.mean(deltas) < 0.3:
            print(f"  VERDICT: Sequential is MUCH smoother. The bridge carries what windowing destroys.")
        elif np.mean(deltas) < 0.5:
            print(f"  VERDICT: Sequential is smoother but still noisy. Partial support for bridge value.")
        else:
            print(f"  VERDICT: Sequential is also chaotic. Disposition may not accumulate smoothly in Mamba.")

    # Save
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "sequential_full",
        "total_turns": len(turns),
        "total_tokens": total_tokens,
        "forward_pass_seconds": round(elapsed, 1),
        "tokens_per_second": round(total_tokens / elapsed),
        "sample_points": len(states),
        "jumps": jumps,
        "drift": drift,
        "mean_delta": float(np.mean([j["delta"] for j in jumps])) if jumps else 0,
        "max_delta": float(max(j["delta"] for j in jumps)) if jumps else 0,
        "metadata": metadata,
    }

    (out_dir / "sequential_trajectory_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    np.savez(out_dir / "sequential_states.npz", states=np.stack(states))
    print(f"\nReport: {out_dir / 'sequential_trajectory_report.json'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
