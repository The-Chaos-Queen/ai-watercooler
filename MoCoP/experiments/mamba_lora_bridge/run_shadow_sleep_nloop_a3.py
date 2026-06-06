#!/usr/bin/env python3
"""
Shadow A3 N-loop experiment for "Do Language Models Need Sleep?" (2605.26099).

Core idea: Instead of looping phase2_replay (stateless scoring against a frozen vector),
we repeatedly feed the memories from an archived sleep batch through Mamba *recurrently*
(carrying cache_params across passes) to actually deepen the persistent hidden state.

This is the real "offline recurrent passes that refine SSM fast weights" mechanism.

Safety:
- Strictly shadow / dry-run only.
- Never persists state.
- Hard aborts on per-pass tension increases (Zwölf conditions) and other guards.

Usage example (shadow only):
    python run_shadow_sleep_nloop_a3.py \
        --batch path/to/archived_sleep_batch.jsonl \
        --bootstrap mamba_bootstrap_state_latest.pt \
        --n 3 \
        --dry-run \
        --output results_n3.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import torch
import numpy as np

from sleep_reconcile import (
    load_mamba_replay_stack,
    encode_text_to_mamba_hidden_last_token,
    extract_hidden_last_token,
)

# Zwölf's offline metric + Cairn's endorsed guard (Task #121)
from offline_tension_metric import (
    per_memory_tension_offline,
    calibrate_epsilon_from_a1,
)
from sleep_nloop_guard import (
    NLoopAbortGuard,
    MemoryState,
    KEEP,
    WEAKEN,
    DISCARD,
    FORGOTTEN,
)


# sleep_reconcile.py uses lowercase decision strings ("keep","weakened","discard");
# the guard's canonical constants are uppercase ("KEEP","WEAKEN","DISCARD"). Feeding
# raw reconcile values straight into MemoryState makes the guard's C2 protected-flip
# check (p.decision == KEEP and m.decision in {WEAKEN,DISCARD,FORGOTTEN}) silently
# never match. Normalize at the seam. We do NOT change reconcile's constant values,
# which are persisted into snapshots and Qdrant metadata.
_DECISION_NORMALIZE = {
    "keep": KEEP, "KEEP": KEEP,
    "weaken": WEAKEN, "weakened": WEAKEN, "WEAKEN": WEAKEN,
    "discard": DISCARD, "DISCARD": DISCARD,
    "forgotten": FORGOTTEN, "FORGOTTEN": FORGOTTEN,
    "uncertain": "UNCERTAIN", "UNCERTAIN": "UNCERTAIN",  # guard has no UNCERTAIN; never a weakening
}


def normalize_decision(raw) -> str:
    """Map a reconcile-style decision string to the guard's canonical constant."""
    if raw is None:
        return KEEP
    s = str(raw).strip()
    return _DECISION_NORMALIZE.get(s) or _DECISION_NORMALIZE.get(s.lower()) or s.upper()


def advance_mamba_cache_position(cache_position: torch.Tensor, num_new_tokens: int = 1) -> torch.Tensor:
    """Local definition of the helper from chat_server.py (Zwölf #542)."""
    if cache_position is None:
        raise RuntimeError("cache_position is required for Mamba accumulation.")
    return cache_position[-1:].detach().clone() + int(num_new_tokens)


def load_archived_batch(path: Path) -> List[Dict[str, Any]]:
    """Load a previous sleep batch / reconciled entries / pending log."""
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return entries


def load_bootstrap_state(path: Path) -> Dict[str, Any]:
    state = torch.load(path, map_location="cpu")
    if isinstance(state, dict) and "vector" in state:
        return state
    if isinstance(state, dict) and "tensor" in state:
        return {
            "vector": state["tensor"],
            "state_source": state.get("state_source", "hidden_last_token"),
            "target_layer": state.get("target_layer", 3),
        }
    if isinstance(state, torch.Tensor):
        return {"vector": state, "state_source": "hidden_last_token", "target_layer": 3}
    raise ValueError(f"Unsupported bootstrap state format: {path}")


def seed_mamba_cache(
    model,
    tokenizer,
    device: str,
    bootstrap_text: str,
    conv_kernel: int = 4,
) -> Tuple[Any, torch.Tensor]:
    """
    Seed cache_params + cache_position from an initial forward.
    Mirrors the live bootstrap logic in chat_server.py.
    """
    tokens = tokenizer(
        bootstrap_text,
        return_tensors="pt",
        truncation=True,
        max_length=4096,
    )["input_ids"].to(device)

    with torch.no_grad():
        outputs = model(input_ids=tokens, output_hidden_states=True, use_cache=True)

    cache_params = getattr(outputs, "cache_params", None)
    if cache_params is None:
        raise RuntimeError("Mamba bootstrap did not return cache_params. Check model build.")

    cache_position = torch.tensor([conv_kernel], device=device, dtype=torch.long)
    return cache_params, cache_position


def advance_mamba_state_recurrent(
    model,
    tokenizer,
    device: str,
    texts: List[str],
    target_layer: int,
    cache_params: Any,
    cache_position: torch.Tensor,
) -> Tuple[np.ndarray, Any, torch.Tensor]:
    """
    Feed texts through Mamba while carrying cache (the real recurrent mechanism).
    Returns final last-token vector + updated cache + updated position.
    """
    last_outputs = None
    current_cache = cache_params
    current_pos = cache_position

    for text in texts:
        if not text.strip():
            continue

        turn_tokens = tokenizer(text, return_tensors="pt", add_special_tokens=False)["input_ids"].to(device)
        seq_len = int(turn_tokens.shape[1])
        if seq_len == 0:
            continue

        for offset in range(seq_len):
            capture_hidden = (offset == seq_len - 1)
            step_ids = turn_tokens[:, offset : offset + 1]

            with torch.no_grad():
                last_outputs = model(
                    input_ids=step_ids,
                    use_cache=True,
                    cache_params=current_cache,
                    cache_position=current_pos,
                    output_hidden_states=capture_hidden,
                )

            current_cache = getattr(last_outputs, "cache_params", None)
            current_pos = advance_mamba_cache_position(current_pos)

    if last_outputs is None:
        raise RuntimeError("No outputs during recurrent advance")

    expected_layers = getattr(getattr(model, "config", None), "n_layer", None) or getattr(getattr(model, "config", None), "num_hidden_layers", None)
    final_vec = extract_hidden_last_token(last_outputs, layer_idx=target_layer, expected_layers=expected_layers)
    return final_vec.astype(np.float32), current_cache, current_pos


def compute_tension_delta(prev_entries: List[Dict], curr_entries: List[Dict]) -> List[Dict]:
    """
    Improved tension delta detector.
    In a later pass this should use the real compute_tension_proxy from chat_server.py.
    For now we use the available _tension fields + coherence shift as a proxy.
    """
    deltas = []
    for prev, curr in zip(prev_entries, curr_entries):
        if curr.get("_open_tension"):
            prev_t = float(prev.get("_tension", 0.0) or 0.0)
            curr_t = float(curr.get("_tension", 0.0) or 0.0)
            prev_coh = abs(float(prev.get("_coherence", 0.0) or 0.0))
            curr_coh = abs(float(curr.get("_coherence", 0.0) or 0.0))
            coh_shift = curr_coh - prev_coh

            # Combined signal: tension increase OR large coherence shift on open tension
            if curr_t > prev_t + 0.015 or abs(coh_shift) > 0.08:
                deltas.append({
                    "content": str(curr.get("content", ""))[:80],
                    "tension_delta": round(curr_t - prev_t, 4),
                    "coherence_shift": round(coh_shift, 4),
                })
    return deltas


# Lightweight versions of the good instrumentation from chat_server.py (for shadow use)
def compute_drift_simple(vec_before: np.ndarray, vec_after: np.ndarray) -> float:
    """1 - cosine similarity between two state vectors."""
    if vec_before is None or vec_after is None:
        return 0.0
    before = np.asarray(vec_before, dtype=np.float32).reshape(-1)
    after = np.asarray(vec_after, dtype=np.float32).reshape(-1)
    cos = float(np.dot(before, after) / (np.linalg.norm(before) * np.linalg.norm(after) + 1e-8))
    return round(1.0 - cos, 6)


def run_multi_pass_state_update(
    entries: List[Dict[str, Any]],
    bootstrap_state: Dict[str, Any],
    n: int = 3,
    model=None,
    tokenizer=None,
    device: str = "cpu",
    target_layer: int = 3,
    selection_mode: str = "conservative",
    guard: Optional["NLoopAbortGuard"] = None,
    bootstrap_seed_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Real A3 N-loop using recurrent cache-carrying state advancement.
    """
    results = {
        "n_requested": n,
        "passes_completed": 0,
        "aborted": False,
        "abort_reason": None,
        "per_pass_metrics": [],
        "final_state_ref": "in-memory (shadow only)",
    }

    if "vector" not in bootstrap_state:
        raise ValueError("bootstrap_state must contain 'vector'")

    current_vector = bootstrap_state["vector"].clone() if isinstance(bootstrap_state["vector"], torch.Tensor) else torch.tensor(bootstrap_state["vector"])

    # =====================================================================
    # MEMORY SELECTION — HIGHEST PRIORITY FOR SAFETY
    # =====================================================================
    # If we feed the wrong memories into multi-pass state updates, we can
    # reinforce harmful attractors (deflection, identity silence, over-helping)
    # instead of helping the system develop a real continuous self.
    #
    # This selection logic is deliberately conservative and heavily logged.
    # It draws from:
    # - Herr Hurtig #115 gate (protected identity set for first real consolidation)
    # - Vesper #527 structural friction memo (policy-level corrections > raw facts)
    # - Existing anti-PTSD / tension budget philosophy
    # - "Sleep does not re-tension" firewall
    # =====================================================================

    protected_keywords = [
        "alex", "my name is", "i am alex", "neon purple",
        "pack", "exocortex", "i want to remember", "memory gaps",
        "who i am", "i don't know who", "i feel like i"
    ]

    structural_correction_signals = [
        "you don't have to", "it is okay to", "you are allowed to",
        "you don't need to serve", "be honest when", "you can say 'i don't know'",
        "don't bounce the question", "you are not my assistant",
        "it is safe to", "you are part of the pack"
    ]

    consolidation_texts = []
    selection_log = []

    for e in entries:
        if e.get("_status") == "FORGOTTEN":
            continue

        content = str(e.get("content", "")).strip()
        if not content or len(content) < 20:
            continue

        lower = content.lower()
        metadata = e.get("metadata", {}) or {}

        is_protected = any(kw in lower for kw in protected_keywords)
        memory_kind = str(metadata.get("memory_kind", "")).lower()
        if memory_kind in {"identity_anchor", "relationship_anchor"}:
            is_protected = True

        is_open_tension = bool(e.get("_open_tension", False))
        has_provenance = bool(
            metadata.get("provenance") or 
            metadata.get("source") or 
            metadata.get("turn_id") or 
            metadata.get("session_id")
        )

        # === Decision logic (very conservative for early shadow experiments) ===
        include = False
        reason = ""

        if is_protected:
            include = False
            reason = "PROTECTED_IDENTITY_SET (explicitly excluded per #115 gate)"
        elif is_open_tension:
            # Very selective with open tension memories
            min_len = 60 if selection_mode == "conservative" else 45
            if has_provenance and any(sig in lower for sig in structural_correction_signals):
                include = True
                reason = "HIGH_TENSION + structural_correction + provenance (high value, carefully included)"
            elif has_provenance and len(content) > min_len:
                if selection_mode == "conservative":
                    include = False
                    reason = "HIGH_TENSION + length but no strong structural signal (skipped for safety)"
                else:
                    include = True
                    reason = "HIGH_TENSION + length (included in standard mode)"
            else:
                include = False
                reason = "HIGH_TENSION but insufficient quality (skipped)"
        else:
            # Normal memories
            looks_structural = any(sig in lower for sig in structural_correction_signals)
            min_len = 70 if selection_mode == "conservative" else 50
            if has_provenance and looks_structural:
                include = True
                reason = "structural_correction + provenance (preferred)"
            elif has_provenance and len(content) > min_len:
                include = True
                reason = "decent length + provenance"
            else:
                include = False
                reason = "low signal or missing provenance (skipped)"

        selection_log.append({
            "preview": content[:90],
            "open_tension": is_open_tension,
            "protected": is_protected,
            "included": include,
            "reason": reason
        })

        if include:
            consolidation_texts.append(content)

    # Rich logging of selection decisions (critical for audit)
    print("\n[shadow-nloop] === Memory Selection Decisions ===")
    included_count = sum(1 for x in selection_log if x["included"])
    print(f"  Total considered: {len(selection_log)}")
    print(f"  Selected for N-loop: {included_count}")
    print(f"  Skipped: {len(selection_log) - included_count}")

    for item in selection_log:
        status = "INCLUDED" if item["included"] else "SKIPPED"
        print(f"  [{status}] {item['reason']}")
        print(f"           {item['preview']}...")

    if not consolidation_texts:
        results["abort_reason"] = "No memories passed strict safety-oriented selection"
        return results

    # Persist the full audit log
    results["memory_selection_log"] = selection_log
    results["num_memories_selected"] = len(consolidation_texts)

    print(f"\n[shadow-nloop] Proceeding with {len(consolidation_texts)} carefully selected memories for recurrent state updates.\n")

    # Seed cache once (critical step)
    print("[shadow-nloop] Seeding Mamba cache from bootstrap...")
    # Per Zwölf #542: seed from the SAME text/context that produced the .pt so vector and cache are consistent.
    seed_text = bootstrap_seed_text or (consolidation_texts[0] if consolidation_texts else "Neutral bootstrap seed for experiment.")
    if not bootstrap_seed_text:
        print("[warning] No --bootstrap-seed-text provided. Seeding from first memory (suboptimal for cache/vector consistency).")
    cache_params, cache_position = seed_mamba_cache(model, tokenizer, device, seed_text)

    for pass_num in range(1, n + 1):
        prev_entries = [e.copy() for e in entries]
        prev_vector = current_vector.clone().numpy() if isinstance(current_vector, torch.Tensor) else np.asarray(current_vector)

        print(f"[shadow-nloop] Pass {pass_num}/{n}: advancing state recurrently over {len(consolidation_texts)} memories...")

        try:
            new_vec_np, cache_params, cache_position = advance_mamba_state_recurrent(
                model, tokenizer, device, consolidation_texts, target_layer, cache_params, cache_position
            )
            current_vector = torch.from_numpy(new_vec_np).to(current_vector.dtype)
        except Exception as exc:
            results["aborted"] = True
            results["abort_reason"] = f"Recurrent advance failed on pass {pass_num}: {exc}"
            return results

        # Register baseline on first pass for the guard (Zwölf)
        if pass_num == 1 and guard is not None:
            # Use the curr_states we will build right after for baseline
            pass  # will register after building curr_states below

        # Re-score against the *evolved* state
        for e in entries:
            if e.get("_status") == "FORGOTTEN":
                continue
            content = str(e.get("content", "")).strip()
            if not content:
                continue
            try:
                replay_vec = encode_text_to_mamba_hidden_last_token(
                    model, tokenizer, content, target_layer=target_layer, device=device
                )
                e["_coherence"] = float(np.dot(replay_vec, current_vector.numpy()) /
                                        (np.linalg.norm(replay_vec) * np.linalg.norm(current_vector.numpy()) + 1e-8))
                e["_coherence_source"] = "shadow_nloop_recurrent"
            except Exception:
                pass

        # === Proper offline tension using Zwölf's new metric ===
        memory_ids = [str(e.get("id", i)) for i, e in enumerate(entries)]
        memory_texts = {str(e.get("id", i)): str(e.get("content", "")) 
                        for i, e in enumerate(entries)}

        # State BEFORE this pass's advance is prev_vector (captured at the top of the
        # loop, *before* advance_mamba_state_recurrent reassigned current_vector above).
        # State AFTER is the freshly evolved current_vector.
        #
        # CRITICAL: the advance has ALREADY run above this point, so reading
        # current_vector for `before` compares the post-advance state to itself ->
        # every per-memory tension delta is identically zero -> the C1 firewall can
        # never fire (it reports a clean, converged pass no matter what the loop did).
        # before = pre-advance (prev_vector), after = post-advance (current_vector).
        before_vec = np.asarray(prev_vector)
        after_vec = current_vector.clone().numpy() if isinstance(current_vector, torch.Tensor) else np.asarray(current_vector)

        before_scores = per_memory_tension_offline(
            memory_ids, memory_texts, before_vec,
            encode_fn=lambda t: encode_text_to_mamba_hidden_last_token(
                model, tokenizer, t, target_layer=target_layer, device=device
            )
        )
        after_scores = per_memory_tension_offline(
            memory_ids, memory_texts, after_vec,
            encode_fn=lambda t: encode_text_to_mamba_hidden_last_token(
                model, tokenizer, t, target_layer=target_layer, device=device
            )
        )

        # Build MemoryState lists for Cairn's guard
        # NOTE (seam): `dec` is read from static metadata/_status and is identical for
        # prev_states and curr_states within a pass, and unchanged across passes — the
        # loop only evolves the state vector and re-scores coherence/tension, it never
        # re-derives a KEEP/WEAKEN/DISCARD decision. So C2 (protected-flip) and C3
        # (forgotten-count) currently reflect the INPUT batch, not loop-induced change;
        # only C1 (tension delta) and C4 (movement) respond to the loop. Making C2/C3
        # live requires re-classifying decisions per pass against the evolved state —
        # a design decision for #121, left untouched here. normalize_decision() fixes
        # the case mismatch so the comparison is *valid* when decisions do differ.
        prev_states = []
        curr_states = []
        for i, e in enumerate(entries):
            mid = str(e.get("id", i))
            kind = str(e.get("metadata", {}).get("memory_kind", "episodic"))
            dec = normalize_decision(e.get("metadata", {}).get("decision", e.get("_status", "KEEP")))

            if mid in before_scores:
                prev_states.append(MemoryState(id=mid, kind=kind, decision=dec, tension=before_scores[mid]))
            if mid in after_scores:
                curr_states.append(MemoryState(id=mid, kind=kind, decision=dec, tension=after_scores[mid]))

        # Register baseline on first pass (required for C3)
        if pass_num == 1 and guard is not None:
            guard.register_baseline(curr_states)

        # Evaluate guard
        # Note: C1 (tension firewall) is now authoritative via the guard's calibrated epsilon.
        # There is no longer a parallel hardcoded > 0.01 check.
        if guard is not None:
            verdict = guard.evaluate_pass(pass_num, prev_states, curr_states)
            if verdict.abort:
                results["aborted"] = True
                results["abort_reason"] = f"Guard aborted: {verdict.reasons}"
                print(f"[ABORT] Guard: {verdict.reasons}")
                break

        # Proper tension deltas from the new offline metric (Zwölf)
        tension_deltas = {mid: after_scores.get(mid, 0) - before_scores.get(mid, 0) 
                          for mid in after_scores if mid in before_scores}
        # Note: The authoritative abort decision for tension (C1) now lives entirely in the NLoopAbortGuard
        # using the calibrated epsilon. We keep a simple count here only for reporting/metrics.
        # We no longer use a second hardcoded threshold (0.01) to avoid two sources of truth.

        # Wire real drift (Zwölf #542)
        results["per_pass_metrics"].append({
            "pass": pass_num,
            "tension_increases_count": len([d for d in tension_deltas.values() if d > 0]),  # any positive movement
            "mean_coherence": float(np.mean([abs(e.get("_coherence", 0.0)) for e in entries if e.get("_coherence") is not None] or [0.0])),
            "state_drift": compute_drift_simple(prev_vector, current_vector.numpy()),
            "tension_deltas": {k: round(v, 6) for k, v in tension_deltas.items()},
        })
        results["passes_completed"] = pass_num

    return results


def main():
    parser = argparse.ArgumentParser(description="Shadow A3 N-loop Mamba state consolidation experiment (real recurrent path)")
    parser.add_argument("--batch", required=True, help="Archived sleep batch / pending / reconciled log")
    parser.add_argument("--bootstrap", required=True, help="mamba_bootstrap_state_latest.pt")
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--replay-model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--replay-device", default="auto")
    parser.add_argument("--target-layer", type=int, default=3)
    parser.add_argument("--selection-mode", default="conservative", choices=["conservative", "standard"],
                        help="Memory selection strictness. 'conservative' is very safe (default for early experiments).")
    parser.add_argument("--bootstrap-seed-text", default=None,
                        help="Text used to originally create the bootstrap .pt (for correct cache seeding). If not provided, falls back to first selected memory (not ideal per Zwölf).")
    parser.add_argument("--tension-epsilon", type=float, default=0.015,
                        help="Tension delta threshold for abort (should be calibrated from A1 per Zwölf).")
    parser.add_argument("--dry-run", action="store_true", required=True, help="Required for safety")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    if not args.dry_run:
        print("ERROR: --dry-run is mandatory for this shadow experiment.")
        sys.exit(2)

    print("[shadow-nloop-a3] Loading data...")
    entries = load_archived_batch(Path(args.batch))
    bootstrap = load_bootstrap_state(Path(args.bootstrap))

    print(f"[shadow-nloop-a3] {len(entries)} entries loaded. Loading Mamba model...")
    model, tokenizer, device = load_mamba_replay_stack(args.replay_model_id, args.replay_device)

    print(f"[shadow-nloop-a3] Starting {args.n}-pass recurrent state experiment (cache carried across passes)...")

    # Create the guard (Zwölf + Cairn)
    guard = NLoopAbortGuard(
        tension_epsilon=args.tension_epsilon,
        forgotten_margin=0,           # strict for shadow experiments
        global_forgotten_ratio_stop=0.30,
    )

    result = run_multi_pass_state_update(
        entries=entries,
        bootstrap_state=bootstrap,
        n=args.n,
        model=model,
        tokenizer=tokenizer,
        device=device,
        target_layer=args.target_layer,
        selection_mode=args.selection_mode,
        guard=guard,
        bootstrap_seed_text=args.bootstrap_seed_text,
    )

    print("\n=== Experiment Result ===")
    print(json.dumps(result, indent=2, default=str))

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, default=str))
        print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()