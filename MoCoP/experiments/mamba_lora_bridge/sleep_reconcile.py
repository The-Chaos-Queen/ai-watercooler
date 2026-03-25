#!/usr/bin/env python3
"""
sleep_reconcile.py - Full sleep reconciliation with cross-trace validation.

Extends sleep_flush.py (Step 1) with Phases 2-4 from
sleep_reconciliation_algorithm.md (Cassian, 2026-03-24):

  Phase 1: Synaptic Downscaling - global strength decay
  Phase 2: Selective Replay - re-encode candidates through Mamba
  Phase 3: Conflict Resolution - cross-trace agreement scoring
  Phase 4: Identity Distillation - save disposition snapshot

Task: OpenCLAW #63
Author: An-Chan (Anda)
Depends: sleep_flush.py (#61), pending-log default (#62)

Usage:
    python sleep_reconcile.py --pending-path qdrant_gate_pending.jsonl
    python sleep_reconcile.py --pending-path qdrant_gate_pending.jsonl --dry-run
    python sleep_reconcile.py --pending-path pending.jsonl --mamba-state mamba_bootstrap_state_latest.pt

Flow:
    1. Load pending entries from JSONL
    2. Load bootstrap Mamba hidden-last-token state
    3. Phase 1: Decay all strengths by decay_factor
    4. Phase 2: Replay candidates into the same Mamba hidden-state space
    5. Phase 3: Classify entries (keep / uncertain / weaken / discard)
    6. Phase 4: Flush validated entries to Qdrant, save disposition snapshot
    7. Rotate pending log
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Phase 1: Synaptic Downscaling
# ---------------------------------------------------------------------------

def phase1_decay(entries: list, decay_factor: float = 0.85) -> list:
    """Global strength reduction. Preserves relative differences."""
    for entry in entries:
        salience = float(entry["metadata"].get("salience_score", 0.5) or 0.5)
        recurrence = float(entry["metadata"].get("recurrence_count", 1) or 1)
        raw_strength = salience * recurrence
        entry["_strength"] = raw_strength * decay_factor
    print(f"[phase1] Decayed {len(entries)} entries by {decay_factor}")
    return entries


# ---------------------------------------------------------------------------
# Phase 2: Selective Replay
# ---------------------------------------------------------------------------

def cosine_similarity_np(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32).reshape(-1)
    b = np.asarray(b, dtype=np.float32).reshape(-1)
    if a.size != b.size:
        raise ValueError(f"shape mismatch: {a.size} vs {b.size}")
    a_norm = float(np.linalg.norm(a))
    b_norm = float(np.linalg.norm(b))
    if a_norm <= 1e-8 or b_norm <= 1e-8:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def fallback_metadata_coherence(entries: list, reason: str) -> list:
    print(f"[phase2] {reason} - using metadata coherence fallback")
    for entry in entries:
        entry["_coherence"] = float(entry["metadata"].get("coherence_score", 0.0) or 0.0)
        entry["_coherence_source"] = "metadata"
    return entries


def extract_hidden_last_token(outputs, layer_idx: int, expected_layers: Optional[int] = None) -> np.ndarray:
    hidden_states = getattr(outputs, "hidden_states", None)
    if not hidden_states:
        raise RuntimeError("Mamba did not return hidden_states.")

    tuple_len = len(hidden_states)
    if expected_layers is None:
        expected_layers = tuple_len - 1 if tuple_len > 1 else tuple_len

    if tuple_len == expected_layers + 1:
        hidden_index = layer_idx + 1
    elif tuple_len == expected_layers:
        hidden_index = layer_idx
    else:
        raise RuntimeError(
            "Unexpected hidden_states layout: "
            f"tuple_len={tuple_len} expected_layers={expected_layers}"
        )

    return hidden_states[hidden_index][:, -1, :].detach().float().cpu().numpy().reshape(-1)


def load_mamba_replay_stack(model_id: str, device: str):
    import torch
    from transformers import AutoTokenizer, MambaForCausalLM

    resolved_device = device
    if resolved_device == "auto":
        resolved_device = "cuda" if torch.cuda.is_available() else "cpu"

    torch_dtype = torch.float16 if str(resolved_device).startswith("cuda") else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model = MambaForCausalLM.from_pretrained(model_id, torch_dtype=torch_dtype)
    model.to(resolved_device)
    model.eval()
    return model, tokenizer, resolved_device


def encode_text_to_mamba_hidden_last_token(model, tokenizer, text: str, target_layer: int, device: str) -> np.ndarray:
    import torch

    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)

    expected_layers = getattr(getattr(model, "config", None), "n_layer", None)
    if expected_layers is None:
        expected_layers = getattr(getattr(model, "config", None), "num_hidden_layers", None)

    return extract_hidden_last_token(outputs, layer_idx=target_layer, expected_layers=expected_layers)


def load_mamba_state(path: str) -> Optional[dict]:
    """Load persisted bootstrap Mamba hidden-last-token state from .pt file."""
    if not path or not Path(path).exists():
        return None
    try:
        import torch

        state = torch.load(path, map_location="cpu", weights_only=True)
        if isinstance(state, torch.Tensor):
            return {
                "vector": state.detach().float().numpy().reshape(-1),
                "target_layer": None,
                "state_source": "unknown",
                "started_at": "",
            }
        if isinstance(state, dict):
            tensor = None
            for key in ("tensor", "hidden_state", "mamba_state", "state", "h"):
                if key in state and isinstance(state[key], torch.Tensor):
                    tensor = state[key]
                    break
            if tensor is None:
                print(f"[warn] Could not extract state vector from {path}")
                return None
            return {
                "vector": tensor.detach().float().numpy().reshape(-1),
                "target_layer": state.get("target_layer"),
                "state_source": state.get("state_source", "unknown"),
                "started_at": state.get("started_at", ""),
            }
        print(f"[warn] Unsupported Mamba state payload in {path}")
        return None
    except Exception as exc:
        print(f"[warn] Failed to load Mamba state: {exc}")
        return None


def phase2_replay(entries: list, bootstrap_state: Optional[dict], top_k: int = 20,
                  replay_stack=None) -> list:
    """
    Re-score coherence in the same hidden_last_token space when possible.

    This replaces the invalid apples-to-oranges comparison between a text embedding
    vector and a truncated Mamba hidden state. If same-space replay is unavailable,
    fall back honestly to the stored metadata coherence score.
    """
    if bootstrap_state is None or bootstrap_state.get("vector") is None:
        return fallback_metadata_coherence(entries, "No Mamba state available")

    if bootstrap_state.get("state_source") != "hidden_last_token":
        return fallback_metadata_coherence(
            entries,
            f"Unsupported state_source={bootstrap_state.get('state_source')!r}"
        )

    if replay_stack is None:
        return fallback_metadata_coherence(entries, "No shared-space Mamba replay stack available")

    bootstrap_vec = np.asarray(bootstrap_state["vector"], dtype=np.float32).reshape(-1)
    target_layer = int(bootstrap_state.get("target_layer", 3) or 3)
    model, tokenizer, device = replay_stack

    for entry in entries:
        content = str(entry.get("content", "") or "").strip()
        if not content:
            entry["_coherence"] = float(entry["metadata"].get("coherence_score", 0.0) or 0.0)
            entry["_coherence_source"] = "metadata"
            continue
        try:
            replay_vec = encode_text_to_mamba_hidden_last_token(
                model,
                tokenizer,
                content,
                target_layer=target_layer,
                device=device,
            )
            entry["_coherence"] = cosine_similarity_np(replay_vec, bootstrap_vec)
            entry["_coherence_source"] = "mamba_hidden_last_token_replay"
        except Exception as exc:
            entry["_coherence"] = float(entry["metadata"].get("coherence_score", 0.0) or 0.0)
            entry["_coherence_source"] = "metadata"
            entry["_coherence_error"] = str(exc)

    ranked = sorted(entries, key=lambda e: e["_strength"] * abs(e["_coherence"]), reverse=True)
    for i, entry in enumerate(ranked[:top_k]):
        decision = entry["metadata"].get("decision", "?")
        source = entry.get("_coherence_source", "?")
        print(
            f"  [replay] #{i+1}: [{decision}] strength={entry['_strength']:.3f} "
            f"coherence={entry['_coherence']:.3f} source={source} | "
            f"{entry['content'][:60]}..."
        )

    replayed = sum(1 for entry in entries if entry.get("_coherence_source") == "mamba_hidden_last_token_replay")
    print(
        f"[phase2] Scored coherence for {len(entries)} entries "
        f"({replayed} via same-space replay, top {min(top_k, len(entries))} shown)"
    )
    return entries


# ---------------------------------------------------------------------------
# Phase 3: Conflict Resolution
# ---------------------------------------------------------------------------

KEEP = "keep"
UNCERTAIN = "uncertain"
WEAKEN = "weakened"
DISCARD = "discard"


def phase3_classify(entries: list,
                    strength_threshold: float = 0.3,
                    coherence_threshold: float = 0.15) -> list:
    """Cross-trace agreement classification."""
    counts = {KEEP: 0, UNCERTAIN: 0, WEAKEN: 0, DISCARD: 0}

    for entry in entries:
        strength = entry["_strength"]
        coherence = abs(entry["_coherence"])
        tension = float(entry["metadata"].get("tension_score", 0.0) or 0.0)
        high_tension = tension > 0.5

        if strength >= strength_threshold and coherence >= coherence_threshold:
            status = KEEP
        elif strength >= strength_threshold and coherence < coherence_threshold:
            status = UNCERTAIN
        elif strength < strength_threshold and coherence >= coherence_threshold:
            status = WEAKEN
        else:
            status = DISCARD

        if high_tension:
            if status == DISCARD:
                status = WEAKEN
            elif status == WEAKEN:
                status = UNCERTAIN

        entry["_status"] = status
        entry["_tension"] = tension
        counts[status] += 1

    print(f"[phase3] Classification: {counts}")
    return entries


# ---------------------------------------------------------------------------
# Phase 4: Identity Distillation + Flush
# ---------------------------------------------------------------------------

def phase4_flush(entries: list, sink_fn, snapshot_path: Path,
                 mamba_state_path: str, dry_run: bool = False) -> dict:
    """Write validated entries to Qdrant and save disposition snapshot."""
    to_write = [entry for entry in entries if entry["_status"] in (KEEP, UNCERTAIN)]
    to_archive = [entry for entry in entries if entry["_status"] in (WEAKEN, DISCARD)]

    print(f"[phase4] Writing {len(to_write)} entries to Qdrant ({len(to_archive)} archived/discarded)")

    written = 0
    failed = 0

    if not dry_run and sink_fn is not None:
        for entry in to_write:
            try:
                entry["metadata"]["sleep_status"] = entry["_status"]
                entry["metadata"]["sleep_strength"] = entry["_strength"]
                entry["metadata"]["sleep_coherence"] = entry["_coherence"]
                entry["metadata"]["sleep_coherence_source"] = entry.get("_coherence_source", "metadata")
                entry["metadata"]["sleep_tension"] = entry.get("_tension", 0.0)
                entry["metadata"]["reconciled"] = True
                entry["metadata"]["reconciled_at"] = datetime.now().isoformat()

                point_id = sink_fn(content=entry["content"], metadata=entry["metadata"])
                written += 1
                print(f"  [ok] [{entry['_status']}] -> {point_id}")
            except Exception as exc:
                failed += 1
                print(f"  [fail] {exc}")
    elif dry_run:
        for entry in to_write:
            status = entry["_status"]
            preview = entry["content"][:60].replace("\n", " ")
            print(
                f"  [dry-run] [{status}] s={entry['_strength']:.3f} "
                f"c={entry['_coherence']:.3f} | {preview}..."
            )
        written = len(to_write)

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "mamba_state_ref": mamba_state_path,
        "entries_processed": len(entries),
        "entries_written": written,
        "entries_archived": len(to_archive),
        "entries_failed": failed,
        "classification": {
            KEEP: sum(1 for entry in entries if entry["_status"] == KEEP),
            UNCERTAIN: sum(1 for entry in entries if entry["_status"] == UNCERTAIN),
            WEAKEN: sum(1 for entry in entries if entry["_status"] == WEAKEN),
            DISCARD: sum(1 for entry in entries if entry["_status"] == DISCARD),
        },
        "mean_strength": float(np.mean([entry["_strength"] for entry in entries])) if entries else 0.0,
        "mean_coherence": float(np.mean([abs(entry["_coherence"]) for entry in entries])) if entries else 0.0,
        "same_space_replay_count": sum(
            1 for entry in entries if entry.get("_coherence_source") == "mamba_hidden_last_token_replay"
        ),
    }

    if not dry_run:
        snapshot_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[phase4] Disposition snapshot -> {snapshot_path}")
    else:
        print(f"[phase4] [dry-run] Would save snapshot to {snapshot_path}")
        print(json.dumps(snapshot, indent=2))

    return snapshot


# ---------------------------------------------------------------------------
# Pending log helpers (same as sleep_flush.py)
# ---------------------------------------------------------------------------

def load_pending(path: Path):
    if not path.exists():
        return []
    entries = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_num, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                content = record.get("content", "")
                metadata = record.get("metadata", {})
                if content and isinstance(content, str) and len(content.strip()) >= 10:
                    entries.append({"content": content, "metadata": metadata, "_line": line_num})
                else:
                    print(f"[skip] line {line_num}: invalid or too short")
            except json.JSONDecodeError as exc:
                print(f"[skip] line {line_num}: bad JSON - {exc}")
    return entries


def rotate_log(path: Path):
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    archive = path.with_suffix(f".reconciled_{ts}.jsonl")
    shutil.move(str(path), str(archive))
    print(f"[rotate] {path.name} -> {archive.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sleep reconciliation: cross-trace validation before Qdrant write."
    )
    parser.add_argument("--pending-path", required=True, help="Path to qdrant_gate_pending.jsonl")
    parser.add_argument(
        "--mamba-state",
        default="mamba_bootstrap_state_latest.pt",
        help="Path to persisted bootstrap Mamba hidden-last-token state (.pt)",
    )
    parser.add_argument(
        "--snapshot-path",
        default="disposition_snapshot_latest.json",
        help="Where to save the disposition snapshot",
    )
    parser.add_argument("--host", default="192.168.2.191", help="Qdrant host")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant port")
    parser.add_argument("--collection", default="exocortex")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    parser.add_argument(
        "--replay-model-id",
        default="state-spaces/mamba-2.8b-hf",
        help="Mamba model used to replay entries into hidden_last_token space",
    )
    parser.add_argument(
        "--replay-device",
        default="auto",
        help="Device for replay model: auto, cpu, cuda, cuda:0, ...",
    )
    parser.add_argument(
        "--skip-replay",
        action="store_true",
        help="Skip Mamba replay and use metadata coherence only",
    )
    parser.add_argument("--decay-factor", type=float, default=0.85)
    parser.add_argument("--strength-threshold", type=float, default=0.3)
    parser.add_argument("--coherence-threshold", type=float, default=0.15)
    parser.add_argument("--top-k", type=int, default=20, help="Top entries to show in replay")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-rotate", action="store_true")
    parser.add_argument(
        "--skip-qdrant",
        action="store_true",
        help="Run reconciliation logic without writing to Qdrant",
    )
    args = parser.parse_args()

    pending_path = Path(args.pending_path)
    snapshot_path = Path(args.snapshot_path)

    entries = load_pending(pending_path)
    if not entries:
        print("[ok] No pending entries. Nothing to reconcile.")
        return 0

    print(f"[sleep] Starting reconciliation for {len(entries)} entries\n")

    bootstrap_state = load_mamba_state(args.mamba_state)
    if bootstrap_state is not None:
        shape = np.asarray(bootstrap_state["vector"]).shape
        print(
            f"[mamba] Loaded state from {args.mamba_state} - {shape} "
            f"source={bootstrap_state.get('state_source')} layer={bootstrap_state.get('target_layer')}"
        )
    else:
        print(f"[mamba] No state found at {args.mamba_state} - coherence will use metadata fallback")

    replay_stack = None
    if bootstrap_state is not None and not args.skip_replay:
        try:
            replay_stack = load_mamba_replay_stack(args.replay_model_id, args.replay_device)
            print(f"[replay] Loaded {args.replay_model_id} on {replay_stack[2]}")
        except Exception as exc:
            print(f"[warn] Could not load replay model: {exc}")

    entries = phase1_decay(entries, args.decay_factor)
    entries = phase2_replay(entries, bootstrap_state, top_k=args.top_k, replay_stack=replay_stack)
    entries = phase3_classify(entries, args.strength_threshold, args.coherence_threshold)

    sink_fn = None
    if not args.dry_run and not args.skip_qdrant:
        try:
            from sleep_flush import create_sink
            sink_fn = create_sink(args.host, args.port, args.collection, args.embedding_model)
        except Exception as exc:
            print(f"[warn] Could not create Qdrant sink: {exc}")

    snapshot = phase4_flush(
        entries,
        sink_fn,
        snapshot_path,
        mamba_state_path=args.mamba_state,
        dry_run=args.dry_run,
    )

    if not args.dry_run and not args.no_rotate and snapshot.get("entries_failed", 0) == 0:
        rotate_log(pending_path)
    elif snapshot.get("entries_failed", 0) > 0:
        print("[warn] Some writes failed - pending log NOT rotated.")

    print(
        f"\n[sleep] Reconciliation complete. "
        f"Written: {snapshot['entries_written']}, "
        f"Archived: {snapshot['entries_archived']}, "
        f"Failed: {snapshot['entries_failed']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
