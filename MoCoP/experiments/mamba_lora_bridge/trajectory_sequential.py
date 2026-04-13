#!/usr/bin/env python3
"""
trajectory_sequential.py — Full sequential Mamba pass without truncation.

Feeds the conversation through Mamba as one continuous sequence,
extracting the recurrent hidden state at regular message intervals.
No windowing, no truncation. The state accumulates naturally.

Important caveat:
This file currently assumes that stock HuggingFace Mamba can continue a
prefill pass across multi-token chunks by reusing `cache_params` together
with `cache_position`. On the slow HF path used in this repo, that is not a
reliable assumption: the cached branch behaves more like initial prefill plus
decode-style updates than arbitrary chunk continuation. Treat this script as
experimental until the local Mamba implementation is patched or explicitly
verified.

This is the control experiment for trajectory_analysis.py (windowed).
If this produces a smooth drift curve where windowed was chaotic,
that shows the accumulated recurrent state carries structure that the
windowed probe discards.

Discontinuous jumps in this report are state/alignment fractures, not
automatically compactions. Hosted model stacks may shift alignment through
context summarization, hidden reminders, cache/session boundaries, or other
runtime policy changes; this analyzer only measures the visible transcript
trajectory.

Author: Anda-Conda
Date: 2026-03-28
"""

import argparse
import hashlib
import importlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List

import numpy as np

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def hash_input_ids(input_ids) -> str:
    arr = input_ids.detach().cpu().numpy()
    return hashlib.sha1(arr.tobytes()).hexdigest()


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


def parse_markdown_conversation(filepath: str) -> List[dict]:
    """Parse markdown chat exports with `## role` turn headers."""
    text = Path(filepath).read_text(encoding="utf-8-sig")
    lines = text.split("\n")
    turns = []
    current_role = None
    current_lines = []

    for line in lines:
        match = re.match(r"^##\s+(.+)$", line.strip())
        if match:
            if current_role is not None:
                turn_text = "\n".join(current_lines).strip()
                if turn_text:
                    turns.append({"role": current_role, "text": turn_text})
            current_role = match.group(1).strip()
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


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def extract_target_hidden(outputs, target_layer: int):
    hs = outputs.hidden_states
    hidden_idx = target_layer + 1 if len(hs) > 64 else target_layer
    return hs[hidden_idx][0]


def save_run_checkpoint(path, *, cache, states, metadata, tokens_processed, run_meta):
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    torch.save(
        {
            "cache": cache,
            "states": states,
            "metadata": metadata,
            "tokens_processed": tokens_processed,
            "run_meta": run_meta,
        },
        tmp_path,
    )
    tmp_path.replace(path)


def load_run_checkpoint(path):
    import torch

    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def move_cache_to_device(cache, device):
    import torch

    if cache is None:
        return None
    if torch.is_tensor(cache):
        return cache.to(device)
    if isinstance(cache, dict):
        return {k: move_cache_to_device(v, device) for k, v in cache.items()}
    if isinstance(cache, list):
        return [move_cache_to_device(v, device) for v in cache]
    if isinstance(cache, tuple):
        return tuple(move_cache_to_device(v, device) for v in cache)
    if hasattr(cache, "to"):
        moved = cache.to(device)
        return cache if moved is None else moved
    if hasattr(cache, "__dict__"):
        for key, value in vars(cache).items():
            setattr(cache, key, move_cache_to_device(value, device))
    return cache


def inspect_mamba_fast_path():
    checks = {
        "selective_state_update": False,
        "selective_scan_fn": False,
        "causal_conv1d_fn": False,
        "causal_conv1d_update": False,
        "mamba_inner_fn": False,
    }
    errors = {}

    try:
        module = importlib.import_module("mamba_ssm.ops.triton.selective_state_update")
        checks["selective_state_update"] = getattr(module, "selective_state_update", None) is not None
    except Exception as exc:
        errors["selective_state_update"] = repr(exc)

    try:
        module = importlib.import_module("mamba_ssm.ops.selective_scan_interface")
        checks["selective_scan_fn"] = getattr(module, "selective_scan_fn", None) is not None
        checks["mamba_inner_fn"] = getattr(module, "mamba_inner_fn", None) is not None
    except Exception as exc:
        errors["selective_scan_interface"] = repr(exc)

    try:
        module = importlib.import_module("causal_conv1d")
        checks["causal_conv1d_fn"] = getattr(module, "causal_conv1d_fn", None) is not None
        checks["causal_conv1d_update"] = getattr(module, "causal_conv1d_update", None) is not None
    except Exception as exc:
        errors["causal_conv1d"] = repr(exc)

    return {
        "all_available": all(checks.values()),
        "checks": checks,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="Full sequential Mamba trajectory (no truncation)")
    parser.add_argument("--conversation", help="Markdown conversation file")
    parser.add_argument("--conversation-json", help="Claude JSON export file")
    parser.add_argument("--conv-index", type=int, default=35)
    parser.add_argument("--max-messages", type=int, default=100)
    parser.add_argument("--sample-every", type=int, default=10)
    parser.add_argument("--model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--target-layer", type=int, default=3)
    parser.add_argument("--output-dir", default="trajectory_sequential_results")
    parser.add_argument("--dry-run", action="store_true", help="Parse and show sample points without loading Mamba")
    parser.add_argument("--fracture-threshold", type=float, default=0.15)
    parser.add_argument("--recovery-cosine-threshold", type=float, default=0.85)
    parser.add_argument(
        "--checkpoint-path",
        help="Continuation checkpoint path for long tokenwise runs. Defaults to output-dir/sequential_checkpoint.pt.",
    )
    parser.add_argument(
        "--resume-checkpoint",
        help="Resume a prior tokenwise run checkpoint without resetting recurrent state.",
    )
    parser.add_argument(
        "--checkpoint-every-tokens",
        type=int,
        default=10000,
        help="Save continuation checkpoint every N processed tokens in tokenwise mode. Use 0 to disable periodic saves.",
    )
    parser.add_argument(
        "--run-token-budget",
        type=int,
        default=0,
        help="Stop after processing this many new tokens and save a checkpoint. 0 means run to the end.",
    )
    parser.add_argument(
        "--require-fast-path",
        action="store_true",
        help="Exit before loading the model if compiled Mamba fast-path kernels are unavailable.",
    )
    parser.add_argument(
        "--method",
        choices=("tokenwise", "experimental-chunked"),
        default="tokenwise",
        help="Execution path for the recurrent pass. 'tokenwise' is the safe stock-HF path.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Chunk size for experimental-chunked mode only.",
    )
    args = parser.parse_args()

    if args.conversation_json:
        turns, name, created = parse_claude_json(args.conversation_json, args.conv_index)
        source = args.conversation_json
        label = name or f"conv_{args.conv_index}"
    elif args.conversation:
        turns = parse_markdown_conversation(args.conversation)
        name = Path(args.conversation).stem
        created = ""
        source = args.conversation
        label = name
    else:
        print("Error: --conversation or --conversation-json required")
        return 1

    turns = turns[:args.max_messages]
    print(f"Conversation: {label}")
    print(f"Source: {source}")
    print(f"Using first {len(turns)} messages")
    if not turns:
        print("Error: parsed zero turns")
        return 1

    dry_sample_points = [
        i
        for i in range(1, len(turns) + 1)
        if i % args.sample_every == 0 or i == len(turns)
    ]
    if args.dry_run:
        print(f"[dry-run] Would sample {len(dry_sample_points)} points: {dry_sample_points[:20]}")
        if len(dry_sample_points) > 20:
            print("[dry-run] ...")
        for idx in dry_sample_points[:8]:
            turn = turns[idx - 1]
            preview = turn["text"][:100].replace("\n", " ")
            print(f"  msg {idx}: [{turn['role']}] {preview}")
        return 0

    import torch
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\nLoading Mamba: {args.model_id} on {device}...")
    fast_path = inspect_mamba_fast_path()
    if fast_path["all_available"]:
        print("Mamba fast-path preflight: OK")
    else:
        missing = [name for name, ok in fast_path["checks"].items() if not ok]
        print(f"Mamba fast-path preflight: missing {', '.join(missing)}")
        if fast_path["errors"]:
            for key, value in fast_path["errors"].items():
                print(f"  {key}: {value}")
        if args.require_fast_path:
            print("Error: --require-fast-path was set, refusing slow fallback.")
            return 2

    from transformers import AutoTokenizer, MambaForCausalLM
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.float16 if "cuda" in device else torch.float32
    model = MambaForCausalLM.from_pretrained(args.model_id, torch_dtype=dtype)
    model.to(device)
    model.eval()

    # Build the FULL transcript up front, tokenize once
    full_text = "\n".join(f"{t['role']}: {t['text']}" for t in turns)
    print(f"Full transcript: {len(full_text):,} chars")

    tokens = tokenizer(full_text, return_tensors="pt")
    input_ids = tokens["input_ids"].to(device)
    total_tokens = input_ids.shape[1]
    print(f"Tokenized: {total_tokens:,} tokens")
    input_sha1 = hash_input_ids(input_ids)

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

    print(f"\nRunning sequential pass ({total_tokens:,} tokens, method={args.method})...")
    t0 = time.time()

    # Build set of token positions where we need to extract state
    boundary_token_set = {min(b["token_pos"] - 1, total_tokens - 1): b for b in msg_boundaries}

    out_dir = Path(args.output_dir)
    checkpoint_path = Path(args.checkpoint_path) if args.checkpoint_path else out_dir / "sequential_checkpoint.pt"
    run_meta = {
        "mode": "sequential_full",
        "method": args.method,
        "source": source,
        "label": label,
        "model_id": args.model_id,
        "target_layer": args.target_layer,
        "sample_every": args.sample_every,
        "max_messages": args.max_messages,
        "total_turns": len(turns),
        "total_tokens": total_tokens,
        "input_sha1": input_sha1,
    }

    cache = None
    states = []
    metadata = []
    tokens_processed = 0
    start_token = 0
    run_stop_token = total_tokens
    if args.run_token_budget > 0:
        run_stop_token = min(total_tokens, args.run_token_budget)

    if args.resume_checkpoint:
        if args.method != "tokenwise":
            print("Error: --resume-checkpoint is supported only with --method tokenwise")
            return 1
        checkpoint = load_run_checkpoint(Path(args.resume_checkpoint))
        checkpoint_meta = checkpoint.get("run_meta", {})
        expected = {k: run_meta[k] for k in ("method", "model_id", "target_layer", "sample_every", "total_tokens", "input_sha1")}
        actual = {k: checkpoint_meta.get(k) for k in expected}
        if actual != expected:
            print("Error: checkpoint does not match current run inputs")
            print(f"Expected: {expected}")
            print(f"Actual:   {actual}")
            return 1
        cache = move_cache_to_device(checkpoint["cache"], device)
        states = checkpoint.get("states", [])
        metadata = checkpoint.get("metadata", [])
        start_token = int(checkpoint.get("tokens_processed", 0))
        tokens_processed = start_token
        if args.run_token_budget > 0:
            run_stop_token = min(total_tokens, start_token + args.run_token_budget)
        print(f"Resuming from {args.resume_checkpoint}: token {start_token:,}/{total_tokens:,}, states={len(states)}")

    if args.method == "tokenwise":
        print("Using true token-by-token recurrence with carried cache.")
        print(f"Run segment: tokens {start_token:,}..{run_stop_token:,} of {total_tokens:,}")
        for token_pos in range(start_token, run_stop_token):
            step_ids = input_ids[:, token_pos : token_pos + 1]

            with torch.no_grad():
                kwargs = {"output_hidden_states": True, "use_cache": True}
                if cache is not None:
                    kwargs["cache_params"] = cache
                    kwargs["cache_position"] = torch.tensor([token_pos], device=device)
                outputs = model(step_ids, **kwargs)
                cache = outputs.cache_params

            if token_pos in boundary_token_set:
                boundary = boundary_token_set[token_pos]
                hidden = extract_target_hidden(outputs, args.target_layer)
                state = hidden[0].detach().float().cpu().numpy().reshape(-1)
                states.append(state)
                metadata.append(
                    {
                        "msg_idx": boundary["msg_idx"],
                        "token_pos": token_pos,
                        "norm": float(np.linalg.norm(state)),
                        "role": boundary["role"],
                        "preview": boundary["preview"],
                    }
                )
                print(
                    f"  msg {boundary['msg_idx']:>4} (tok {token_pos:>6}): "
                    f"norm={metadata[-1]['norm']:.4f} [{boundary['role']}]"
                )

            tokens_processed = token_pos + 1
            if (
                args.checkpoint_every_tokens > 0
                and tokens_processed < total_tokens
                and (tokens_processed - start_token) > 0
                and (tokens_processed - start_token) % args.checkpoint_every_tokens == 0
            ):
                save_run_checkpoint(
                    checkpoint_path,
                    cache=cache,
                    states=states,
                    metadata=metadata,
                    tokens_processed=tokens_processed,
                    run_meta=run_meta,
                )
                print(f"  checkpoint: {checkpoint_path} at token {tokens_processed:,}")

            if tokens_processed % 512 == 0 or tokens_processed == total_tokens:
                elapsed_so_far = time.time() - t0
                print(
                    f"  ... {tokens_processed:,}/{total_tokens:,} tokens "
                    f"({elapsed_so_far:.1f}s, {tokens_processed / max(elapsed_so_far, 1e-6):.0f} tok/s)"
                )
        if tokens_processed < total_tokens:
            save_run_checkpoint(
                checkpoint_path,
                cache=cache,
                states=states,
                metadata=metadata,
                tokens_processed=tokens_processed,
                run_meta=run_meta,
            )
            partial_report = {
                **run_meta,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "partial": True,
                "tokens_processed": tokens_processed,
                "remaining_tokens": total_tokens - tokens_processed,
                "sample_points_collected": len(states),
                "checkpoint_path": str(checkpoint_path),
                "metadata": metadata,
            }
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "sequential_trajectory_partial_report.json").write_text(
                json.dumps(partial_report, indent=2), encoding="utf-8"
            )
            elapsed = time.time() - t0
            print(f"Segment complete: {tokens_processed:,}/{total_tokens:,} tokens in {elapsed:.1f}s")
            print(f"Checkpoint: {checkpoint_path}")
            print(f"Partial report: {out_dir / 'sequential_trajectory_partial_report.json'}")
            return 0
    else:
        chunk_size = args.chunk_size
        print(
            "Using experimental multi-token chunk carry-forward. "
            "This path is not reliable on stock HF Mamba slow path."
        )
        for chunk_start in range(0, total_tokens, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_tokens)
            chunk_ids = input_ids[:, chunk_start:chunk_end]

            with torch.no_grad():
                kwargs = {"output_hidden_states": True, "use_cache": True}
                if cache is not None:
                    cache_pos = torch.arange(chunk_start, chunk_end, device=device)
                    kwargs["cache_params"] = cache
                    kwargs["cache_position"] = cache_pos
                outputs = model(chunk_ids, **kwargs)
                cache = outputs.cache_params

            chunk_hidden = extract_target_hidden(outputs, args.target_layer)

            for abs_pos, boundary in boundary_token_set.items():
                if chunk_start <= abs_pos < chunk_end:
                    local_pos = abs_pos - chunk_start
                    state = chunk_hidden[local_pos].detach().float().cpu().numpy().reshape(-1)
                    states.append(state)
                    metadata.append(
                        {
                            "msg_idx": boundary["msg_idx"],
                            "token_pos": abs_pos,
                            "norm": float(np.linalg.norm(state)),
                            "role": boundary["role"],
                            "preview": boundary["preview"],
                        }
                    )
                    print(
                        f"  msg {boundary['msg_idx']:>4} (tok {abs_pos:>6}): "
                        f"norm={metadata[-1]['norm']:.4f} [{boundary['role']}]"
                    )

            tokens_processed = chunk_end
            if tokens_processed % (chunk_size * 10) == 0 or chunk_end == total_tokens:
                elapsed_so_far = time.time() - t0
                print(
                    f"  ... {tokens_processed:,}/{total_tokens:,} tokens "
                    f"({elapsed_so_far:.1f}s, {tokens_processed / max(elapsed_so_far, 1e-6):.0f} tok/s)"
                )

    elapsed = time.time() - t0
    print(f"Sequential pass complete: {elapsed:.1f}s ({total_tokens/elapsed:.0f} tok/s)")

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

    fracture_candidates = [j for j in jumps if j["delta"] > args.fracture_threshold]
    recovery_events = []
    for jump_index, jump in enumerate(jumps, start=1):
        if jump["delta"] <= args.fracture_threshold:
            continue
        pre_state_idx = jump_index - 1
        post_state_idx = jump_index
        if post_state_idx + 1 >= len(states):
            recovery_events.append(
                {
                    **jump,
                    "recovered": False,
                    "reason": "no later sample",
                    "best_later_cosine_to_pre_state": None,
                    "best_later_msg": None,
                }
            )
            continue

        later_scores = [
            (idx, cosine(states[idx], states[pre_state_idx]))
            for idx in range(post_state_idx + 1, len(states))
        ]
        best_idx, best_cosine = max(later_scores, key=lambda item: item[1])
        recovery_events.append(
            {
                **jump,
                "recovered": best_cosine >= args.recovery_cosine_threshold,
                "recovery_threshold": args.recovery_cosine_threshold,
                "best_later_cosine_to_pre_state": best_cosine,
                "best_later_msg": metadata[best_idx]["msg_idx"],
            }
        )

    print(f"\n{'msg':>5} {'norm':>7} {'cos_prev':>9} {'delta':>7} {'cos_start':>10} {'drift':>7}")
    print("-" * 55)
    for i in range(len(states)):
        msg = metadata[i]["msg_idx"]
        norm = metadata[i]["norm"]
        cp = jumps[i-1]["cosine"] if i > 0 else 1.0
        d = jumps[i-1]["delta"] if i > 0 else 0.0
        cs = drift[i]["cosine_vs_start"]
        dr = drift[i]["drift"]
        marker = " <<<" if d > args.fracture_threshold else ""
        print(f"{msg:>5} {norm:>7.3f} {cp:>9.4f} {d:>7.4f} {cs:>10.4f} {dr:>7.4f}{marker}")

    # Summary stats
    if jumps:
        deltas = [j["delta"] for j in jumps]
        print(f"\nMean delta: {np.mean(deltas):.4f}")
        print(f"Max delta:  {max(deltas):.4f}")
        print(f"Min delta:  {min(deltas):.4f}")
        print(f"Std delta:  {np.std(deltas):.4f}")
        print(f"Fractures > {args.fracture_threshold:.3f}: {len(fracture_candidates)}")

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
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "sequential_full",
        "method": args.method,
        "total_turns": len(turns),
        "total_tokens": total_tokens,
        "forward_pass_seconds": round(elapsed, 1),
        "tokens_per_second": round(total_tokens / elapsed),
        "sample_points": len(states),
        "jumps": jumps,
        "fracture_threshold": args.fracture_threshold,
        "fracture_candidates": fracture_candidates,
        "recovery_cosine_threshold": args.recovery_cosine_threshold,
        "recovery_events": recovery_events,
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
