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
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List

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


def build_sample_indices(num_turns: int, sample_every: int) -> List[int]:
    indices = list(range(sample_every, num_turns + 1, sample_every))
    if indices and indices[-1] != num_turns:
        indices.append(num_turns)
    return indices


def hash_token_ids(token_ids: List[int]) -> str:
    return hashlib.sha1(" ".join(str(token_id) for token_id in token_ids).encode("utf-8")).hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


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
    model = MambaForCausalLM.from_pretrained(model_id, torch_dtype=dtype)
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

def tokenize_for_state(tokenizer, text: str, max_tokens: int, truncation_side: str):
    old_side = getattr(tokenizer, "truncation_side", "right")
    tokenizer.truncation_side = truncation_side
    try:
        full_inputs = tokenizer(text, add_special_tokens=True, truncation=False)
        full_ids = full_inputs["input_ids"]
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_tokens)
        kept_ids = inputs["input_ids"][0].tolist()
    finally:
        tokenizer.truncation_side = old_side

    stats = {
        "full_tokens": len(full_ids),
        "kept_tokens": len(kept_ids),
        "max_tokens": max_tokens,
        "truncated": len(full_ids) > len(kept_ids),
        "truncation_side": truncation_side,
        "effective_token_sha1": hash_token_ids(kept_ids),
    }
    return inputs, stats


def extract_mamba_l3(
    model,
    tokenizer,
    text: str,
    device: str,
    max_tokens: int = 2048,
    truncation_side: str = "left",
):
    import torch
    inputs, stats = tokenize_for_state(tokenizer, text, max_tokens, truncation_side)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)
    hs = outputs.hidden_states
    hidden_idx = 4 if len(hs) > 64 else 3  # Layer 3 (0-indexed + embedding)
    return hs[hidden_idx][:, -1, :].detach().float().cpu().numpy().reshape(-1), stats


def extract_qwen_l13(
    model,
    tokenizer,
    text: str,
    device: str,
    max_tokens: int = 2048,
    truncation_side: str = "left",
):
    import torch
    inputs, stats = tokenize_for_state(tokenizer, text, max_tokens, truncation_side)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)
    hs = outputs.hidden_states
    # Qwen 1.5B: 28 layers + embedding = 29 hidden states
    # Layer 13 is index 14 (0=embedding, 1=layer0, ...)
    layer_idx = min(14, len(hs) - 1)
    return hs[layer_idx][:, -1, :].detach().float().cpu().numpy().reshape(-1), stats


def save_partial_vector(partial_dir: Path, sample_id: int, vec: np.ndarray, stats: dict = None) -> Path:
    partial_dir.mkdir(parents=True, exist_ok=True)
    out_path = partial_dir / f"{sample_id:04d}.npy"
    np.save(out_path, vec)
    if stats is not None:
        (partial_dir / f"{sample_id:04d}.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return out_path


def load_partial_vector(partial_dir: Path, sample_id: int) -> np.ndarray:
    return np.load(partial_dir / f"{sample_id:04d}.npy")


def load_partial_stats(partial_dir: Path, sample_id: int) -> dict:
    stats_path = partial_dir / f"{sample_id:04d}.json"
    if not stats_path.exists():
        return {}
    return json.loads(stats_path.read_text(encoding="utf-8"))


def cached_vector_is_compatible(
    partial_dir: Path,
    sample_id: int,
    max_tokens: int,
    truncation_side: str,
    text_sha1: str,
    model_id: str,
) -> bool:
    stats = load_partial_stats(partial_dir, sample_id)
    return bool(
        stats
        and stats.get("max_tokens") == max_tokens
        and stats.get("truncation_side") == truncation_side
        and stats.get("text_sha1") == text_sha1
        and stats.get("model_id") == model_id
        and stats.get("effective_token_sha1")
    )


def count_cached_vectors(partial_dir: Path, total_samples: int) -> int:
    if not partial_dir.exists():
        return 0
    return sum(1 for idx in range(total_samples) if (partial_dir / f"{idx:04d}.npy").exists())


def find_duplicate_runs(metadata: List[dict], mamba_array: np.ndarray, qwen_array: np.ndarray) -> List[dict]:
    runs = []
    labels = sorted({item["label"] for item in metadata})
    for label in labels:
        indices = [idx for idx, item in enumerate(metadata) if item["label"] == label]
        if not indices:
            continue
        start = indices[0]
        prev = indices[0]
        for cur in indices[1:]:
            same_pair = np.array_equal(mamba_array[cur], mamba_array[prev]) and np.array_equal(
                qwen_array[cur], qwen_array[prev]
            )
            if same_pair:
                prev = cur
                continue
            if prev > start:
                runs.append({
                    "label": label,
                    "sample_start": metadata[start]["sample_num"],
                    "sample_end": metadata[prev]["sample_num"],
                    "turn_start": metadata[start]["end_idx"],
                    "turn_end": metadata[prev]["end_idx"],
                    "length": prev - start + 1,
                })
            start = prev = cur
        if prev > start:
            runs.append({
                "label": label,
                "sample_start": metadata[start]["sample_num"],
                "sample_end": metadata[prev]["sample_num"],
                "turn_start": metadata[start]["end_idx"],
                "turn_end": metadata[prev]["end_idx"],
                "length": prev - start + 1,
            })
    return runs


def write_data_quality_report(
    out_dir: Path,
    metadata: List[dict],
    mamba_array: np.ndarray,
    qwen_array: np.ndarray,
    min_unique_ratio: float,
) -> dict:
    n_samples = len(metadata)
    mamba_unique = np.unique(mamba_array, axis=0).shape[0]
    qwen_unique = np.unique(qwen_array, axis=0).shape[0]
    labels = sorted({item["label"] for item in metadata})

    per_label = []
    for label in labels:
        indices = [idx for idx, item in enumerate(metadata) if item["label"] == label]
        per_label.append({
            "label": label,
            "samples": len(indices),
            "mamba_unique": np.unique(mamba_array[indices], axis=0).shape[0],
            "qwen_unique": np.unique(qwen_array[indices], axis=0).shape[0],
        })

    truncated_mamba = sum(1 for item in metadata if item.get("mamba_token_stats", {}).get("truncated"))
    truncated_qwen = sum(1 for item in metadata if item.get("qwen_token_stats", {}).get("truncated"))
    report = {
        "n_samples": n_samples,
        "min_unique_ratio": min_unique_ratio,
        "passes": (mamba_unique / n_samples >= min_unique_ratio) and (qwen_unique / n_samples >= min_unique_ratio),
        "unique": {
            "mamba": mamba_unique,
            "qwen": qwen_unique,
            "mamba_ratio": mamba_unique / n_samples if n_samples else 0.0,
            "qwen_ratio": qwen_unique / n_samples if n_samples else 0.0,
        },
        "truncation": {
            "mamba_truncated_samples": truncated_mamba,
            "qwen_truncated_samples": truncated_qwen,
        },
        "per_label": per_label,
        "duplicate_runs": find_duplicate_runs(metadata, mamba_array, qwen_array),
    }
    (out_dir / "data_quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def write_progress_snapshot(
    out_dir: Path,
    all_transcripts: List[dict],
    selected_transcripts: List[dict],
    mamba_dir: Path,
    qwen_dir: Path,
) -> dict:
    total_samples = len(all_transcripts)
    mamba_cached = count_cached_vectors(mamba_dir, total_samples)
    qwen_cached = count_cached_vectors(qwen_dir, total_samples)
    paired_cached = sum(
        1
        for idx in range(total_samples)
        if (mamba_dir / f"{idx:04d}.npy").exists() and (qwen_dir / f"{idx:04d}.npy").exists()
    )
    snapshot = {
        "total_samples": total_samples,
        "selected_samples": len(selected_transcripts),
        "mamba_cached": mamba_cached,
        "qwen_cached": qwen_cached,
        "paired_cached": paired_cached,
        "complete": paired_cached == total_samples and total_samples > 0,
        "selected_range": {
            "start_sample": selected_transcripts[0]["sample_num"] if selected_transcripts else None,
            "end_sample": selected_transcripts[-1]["sample_num"] if selected_transcripts else None,
        },
    }
    (out_dir / "progress.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return snapshot


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
    parser.add_argument("--truncation-side", choices=["left", "right"], default="left",
                        help="Which side to truncate when transcripts exceed max_tokens; left keeps recent tokens")
    parser.add_argument("--mamba-model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--qwen-model-id", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-dir", default="paired_activations")
    parser.add_argument("--start-sample", type=int, default=1,
                        help="1-based sample index to start from")
    parser.add_argument("--end-sample", type=int,
                        help="1-based sample index to stop at (inclusive)")
    parser.add_argument("--progress-every", type=int, default=5,
                        help="Print progress every N samples")
    parser.add_argument("--force-recompute", action="store_true",
                        help="Recompute partials even if cached vectors already exist")
    parser.add_argument("--status-only", action="store_true",
                        help="Write/read progress metadata and exit without model work")
    parser.add_argument("--min-unique-ratio", type=float, default=0.5,
                        help="Warn when exact unique activation row ratio falls below this value")
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
        indices = build_sample_indices(len(turns), args.sample_every)
        total_samples += len(indices)

    print(f"\nTotal conversations: {len(all_turns)}")
    print(f"Total sample points: {total_samples}")

    # Build all transcripts up front
    all_transcripts = []
    for label, turns in all_turns:
        indices = build_sample_indices(len(turns), args.sample_every)
        for end_idx in indices:
            transcript = build_cumulative_transcript(turns, end_idx)
            all_transcripts.append({
                "sample_id": len(all_transcripts),
                "sample_num": len(all_transcripts) + 1,
                "label": label,
                "end_idx": end_idx,
                "text": transcript,
                "text_sha1": hash_text(transcript),
            })

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "transcripts_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "samples": len(all_transcripts),
                "sample_every": args.sample_every,
                "max_tokens": args.max_tokens,
                "truncation_side": args.truncation_side,
                "conversations": [
                    {
                        "sample_num": item["sample_num"],
                        "label": item["label"],
                        "end_idx": item["end_idx"],
                        "text_sha1": item["text_sha1"],
                    }
                    for item in all_transcripts
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    start_sample = max(1, args.start_sample)
    end_sample = args.end_sample or len(all_transcripts)
    end_sample = min(end_sample, len(all_transcripts))
    if start_sample > end_sample:
        print(f"Error: start_sample ({start_sample}) > end_sample ({end_sample})")
        return 1

    selected_transcripts = [
        item for item in all_transcripts
        if start_sample <= item["sample_num"] <= end_sample
    ]

    print(f"\n{len(all_transcripts)} transcripts prepared")
    print(f"Selected sample range: {start_sample}..{end_sample} ({len(selected_transcripts)} samples)")

    partials_dir = out_dir / "partials"
    mamba_dir = partials_dir / "mamba_l3"
    qwen_dir = partials_dir / "qwen_l13"

    snapshot = write_progress_snapshot(out_dir, all_transcripts, selected_transcripts, mamba_dir, qwen_dir)
    print(
        f"Cached progress: Mamba={snapshot['mamba_cached']}/{snapshot['total_samples']}, "
        f"Qwen={snapshot['qwen_cached']}/{snapshot['total_samples']}, "
        f"Paired={snapshot['paired_cached']}/{snapshot['total_samples']}"
    )

    if args.status_only:
        print("[status-only] Progress snapshot written; exiting.")
        return 0

    if args.dry_run:
        print(f"[dry-run] Would extract {len(selected_transcripts)} paired activations")
        return 0

    # Load models
    import torch
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # Pass 1: Mamba (load, extract, unload)
    print(f"\n--- Pass 1: Mamba ({args.mamba_model_id}) on {device} ---")
    mamba_model, mamba_tok = load_mamba(args.mamba_model_id, device)
    for idx, item in enumerate(selected_transcripts):
        partial_path = mamba_dir / f"{item['sample_id']:04d}.npy"
        t0 = time.time()
        if (
            partial_path.exists()
            and not args.force_recompute
            and cached_vector_is_compatible(
                mamba_dir,
                item["sample_id"],
                args.max_tokens,
                args.truncation_side,
                item["text_sha1"],
                args.mamba_model_id,
            )
        ):
            vec = load_partial_vector(mamba_dir, item["sample_id"])
            source = "cached"
        else:
            vec, stats = extract_mamba_l3(
                mamba_model,
                mamba_tok,
                item["text"],
                device,
                args.max_tokens,
                args.truncation_side,
            )
            stats["text_sha1"] = item["text_sha1"]
            stats["model_id"] = args.mamba_model_id
            save_partial_vector(mamba_dir, item["sample_id"], vec, stats)
            source = "fresh"
        elapsed = time.time() - t0
        if (idx + 1) % args.progress_every == 0 or idx == 0 or idx + 1 == len(selected_transcripts):
            print(
                f"  [{idx+1}/{len(selected_transcripts)} | sample {item['sample_num']}] "
                f"{item['label']} turn {item['end_idx']}: "
                f"norm={np.linalg.norm(vec):.4f} ({elapsed:.1f}s, {source})"
            )
            write_progress_snapshot(out_dir, all_transcripts, selected_transcripts, mamba_dir, qwen_dir)

    # Free Mamba VRAM
    del mamba_model, mamba_tok
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"  Mamba unloaded")

    # Pass 2: Qwen (load, extract, unload)
    print(f"\n--- Pass 2: Qwen ({args.qwen_model_id}) on {device} ---")
    qwen_model, qwen_tok = load_qwen(args.qwen_model_id, device)
    for idx, item in enumerate(selected_transcripts):
        partial_path = qwen_dir / f"{item['sample_id']:04d}.npy"
        t0 = time.time()
        if (
            partial_path.exists()
            and not args.force_recompute
            and cached_vector_is_compatible(
                qwen_dir,
                item["sample_id"],
                args.max_tokens,
                args.truncation_side,
                item["text_sha1"],
                args.qwen_model_id,
            )
        ):
            vec = load_partial_vector(qwen_dir, item["sample_id"])
            source = "cached"
        else:
            vec, stats = extract_qwen_l13(
                qwen_model,
                qwen_tok,
                item["text"],
                device,
                args.max_tokens,
                args.truncation_side,
            )
            stats["text_sha1"] = item["text_sha1"]
            stats["model_id"] = args.qwen_model_id
            save_partial_vector(qwen_dir, item["sample_id"], vec, stats)
            source = "fresh"
        elapsed = time.time() - t0
        if (idx + 1) % args.progress_every == 0 or idx == 0 or idx + 1 == len(selected_transcripts):
            print(
                f"  [{idx+1}/{len(selected_transcripts)} | sample {item['sample_num']}] "
                f"{item['label']} turn {item['end_idx']}: "
                f"norm={np.linalg.norm(vec):.4f} ({elapsed:.1f}s, {source})"
            )
            write_progress_snapshot(out_dir, all_transcripts, selected_transcripts, mamba_dir, qwen_dir)

    del qwen_model, qwen_tok
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"  Qwen unloaded")

    # Load cached arrays for final assembly
    complete_snapshot = write_progress_snapshot(out_dir, all_transcripts, selected_transcripts, mamba_dir, qwen_dir)
    if not complete_snapshot["complete"]:
        print(
            "\nPartial progress saved. Full paired arrays will be assembled once every "
            f"sample has both cached vectors ({complete_snapshot['paired_cached']}/"
            f"{complete_snapshot['total_samples']} complete)."
        )
        return 0

    # Build metadata
    metadata = []
    mamba_acts = []
    qwen_acts = []
    for item in all_transcripts:
        mamba_vec = load_partial_vector(mamba_dir, item["sample_id"])
        qwen_vec = load_partial_vector(qwen_dir, item["sample_id"])
        mamba_acts.append(mamba_vec)
        qwen_acts.append(qwen_vec)
        metadata.append({
            "label": item["label"],
            "end_idx": item["end_idx"],
            "sample_num": item["sample_num"],
            "mamba_norm": float(np.linalg.norm(mamba_vec)),
            "qwen_norm": float(np.linalg.norm(qwen_vec)),
            "mamba_token_stats": load_partial_stats(mamba_dir, item["sample_id"]),
            "qwen_token_stats": load_partial_stats(qwen_dir, item["sample_id"]),
        })

    mamba_array = np.stack(mamba_acts)
    qwen_array = np.stack(qwen_acts)

    np.save(out_dir / "mamba_l3_activations.npy", mamba_array)
    np.save(out_dir / "qwen_l13_activations.npy", qwen_array)
    (out_dir / "paired_metadata.json").write_text(
        json.dumps({"samples": len(metadata), "metadata": metadata}, indent=2),
        encoding="utf-8",
    )
    quality = write_data_quality_report(out_dir, metadata, mamba_array, qwen_array, args.min_unique_ratio)

    print(f"\nSaved {len(mamba_acts)} paired activations:")
    print(f"  Mamba L3:  {mamba_array.shape} -> {out_dir / 'mamba_l3_activations.npy'}")
    print(f"  Qwen L13:  {qwen_array.shape} -> {out_dir / 'qwen_l13_activations.npy'}")
    print(f"  Metadata: {out_dir / 'paired_metadata.json'}")
    print(f"  Quality:  {out_dir / 'data_quality_report.json'}")
    if not quality["passes"]:
        unique = quality["unique"]
        print(
            "  WARNING: Low exact-unique ratio "
            f"(Mamba={unique['mamba_ratio']:.3f}, Qwen={unique['qwen_ratio']:.3f}); "
            "do not train DFC on this without inspecting the report."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
