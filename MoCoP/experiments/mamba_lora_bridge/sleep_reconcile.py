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
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Phase 1: Synaptic Downscaling
# ---------------------------------------------------------------------------

def phase1_decay(
    entries: list,
    decay_factor: float = 0.85,
    tension_decay: float = 0.85,
    tension_floor_drain: float = 0.02,
    tension_resolve_threshold: float = 0.1,
) -> list:
    """Global strength AND tension decay. Preserves relative differences.

    Strength and tension are orthogonal channels (§3.6/§3.7.1 of the framework):
    - Strength: how well-consolidated the memory is
    - Tension: how much unresolved pressure it exerts

    Tension decays passively during sleep. Only wake experience can re-tension.
    This is the structural firewall against anxiety loops / PTSD.
    """
    tension_resolved_count = 0
    for entry in entries:
        salience = float(entry["metadata"].get("salience_score", 0.5) or 0.5)
        recurrence = float(entry["metadata"].get("recurrence_count", 1) or 1)
        raw_strength = salience * recurrence
        entry["_strength"] = raw_strength * decay_factor

        # Tension decay — independent of strength
        old_tension = float(entry["metadata"].get("tension_score", 0.0) or 0.0)
        if old_tension > 0:
            new_tension = max(0.0, old_tension * tension_decay - tension_floor_drain)
            entry["_tension"] = new_tension
            entry["metadata"]["tension_score"] = new_tension

            # Increment sleep cycle counter for open tension memories
            cycles = int(entry["metadata"].get("sleep_tension_cycles", 0) or 0)
            entry["metadata"]["sleep_tension_cycles"] = cycles + 1

            # Track peak tension (for escalation diagnostics)
            peak = float(entry["metadata"].get("sleep_tension_peak", 0.0) or 0.0)
            entry["metadata"]["sleep_tension_peak"] = max(peak, old_tension)

            # Auto-resolve if tension decayed below threshold
            if new_tension < tension_resolve_threshold:
                was_open = bool(entry["metadata"].get("open_tension", False))
                entry["metadata"]["open_tension"] = False
                entry["metadata"]["tension_status"] = "RESOLVED_BY_DECAY"
                entry["_open_tension"] = False
                if was_open:
                    tension_resolved_count += 1
        else:
            entry["_tension"] = 0.0

    print(f"[phase1] Decayed {len(entries)} entries by {decay_factor} "
          f"(tension_decay={tension_decay}, floor_drain={tension_floor_drain}, "
          f"{tension_resolved_count} tensions resolved by decay)")
    return entries


# ---------------------------------------------------------------------------
# Phase 1b: Expiration and Relevance
# ---------------------------------------------------------------------------

def estimate_relevance(entry: dict, rules: list) -> tuple[bool, int]:
    """Estimate relevance based on learned rules (Phase 1c stub).
    Returns (is_relevant, days_to_extend).
    """
    return False, 0

def phase1b_expiration_and_relevance(entries: list, rules: list = None, now: datetime = None) -> list:
    """Check memory expiration. Extend lifetime if relevant, otherwise mark FORGOTTEN."""
    if now is None:
        now = datetime.now(timezone.utc)
    
    rules = rules or []
    expired_count = 0
    extended_count = 0
    forgotten_count = 0

    for entry in entries:
        metadata = entry.get("metadata", {})
        expiration_str = metadata.get("expiration")
        if not expiration_str:
            continue
            
        try:
            expiration = datetime.fromisoformat(str(expiration_str).replace("Z", "+00:00"))
            if expiration.tzinfo is None:
                expiration = expiration.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        if expiration < now:
            expired_count += 1
            is_relevant, days_to_extend = estimate_relevance(entry, rules)
            if is_relevant:
                extended_count += 1
                new_expiration = now + timedelta(days=days_to_extend)
                metadata["expiration"] = new_expiration.isoformat().replace("+00:00", "Z")
                metadata["relevance_extensions"] = metadata.get("relevance_extensions", 0) + 1
            else:
                forgotten_count += 1
                entry["_status"] = FORGOTTEN
                if "status" not in metadata:
                    metadata["status"] = {}
                metadata["status"]["sleep_status"] = FORGOTTEN
                metadata["status"]["forgotten_at"] = now.isoformat().replace("+00:00", "Z")

    print(f"[phase1b] Expiration check: {expired_count} expired, {extended_count} extended, {forgotten_count} marked FORGOTTEN")
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
                  replay_stack=None, tension_budget_ratio: float = 0.30) -> list:
    """
    Re-score coherence in the same hidden_last_token space when possible.

    This replaces the invalid apples-to-oranges comparison between a text embedding
    vector and a truncated Mamba hidden state. If same-space replay is unavailable,
    fall back honestly to the stored metadata coherence score.

    Replay budget cap (§3.7.1 anti-PTSD):
    Open-tension memories get at most `tension_budget_ratio` of the top_k replay
    slots. The rest goes to normal consolidation. This prevents anxiety loops from
    starving normal learning.
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
        if entry.get("_status") == "FORGOTTEN":
            continue
            
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

    # Budget-capped replay: split into tension and normal pools (§3.7.1)
    tension_pool = []
    normal_pool = []
    for entry in entries:
        is_open = bool(entry.get("_open_tension", False))
        escalated = bool(entry.get("metadata", {}).get("escalated_to_partner", False))
        # Escalated memories move to normal pool — they've had their chance
        if is_open and not escalated:
            tension_pool.append(entry)
        else:
            normal_pool.append(entry)

    sort_key = lambda e: e["_strength"] * abs(e.get("_coherence", 0.0))
    tension_pool.sort(key=sort_key, reverse=True)
    normal_pool.sort(key=sort_key, reverse=True)

    tension_budget = int(tension_budget_ratio * top_k)
    normal_budget = top_k - tension_budget

    # Take from each pool, overflow transfers
    tension_take = tension_pool[:tension_budget]
    normal_take = normal_pool[:normal_budget]
    tension_remaining = tension_budget - len(tension_take)
    normal_remaining = normal_budget - len(normal_take)
    if tension_remaining > 0:
        normal_take = normal_pool[:normal_budget + tension_remaining]
    if normal_remaining > 0:
        tension_take = tension_pool[:tension_budget + normal_remaining]

    replayed_entries = tension_take + normal_take
    replayed_entries.sort(key=sort_key, reverse=True)

    for i, entry in enumerate(replayed_entries[:top_k]):
        decision = entry["metadata"].get("decision", "?")
        source = entry.get("_coherence_source", "?")
        pool_tag = "T" if entry in tension_take else "N"
        print(
            f"  [replay] #{i+1} [{pool_tag}]: [{decision}] strength={entry['_strength']:.3f} "
            f"coherence={entry.get('_coherence', 0):.3f} source={source} | "
            f"{entry['content'][:60]}..."
        )

    replayed = sum(1 for entry in entries if entry.get("_coherence_source") == "mamba_hidden_last_token_replay")
    print(
        f"[phase2] Scored coherence for {len(entries)} entries "
        f"({replayed} via same-space replay, "
        f"budget: {len(tension_take)}T/{len(normal_take)}N of {top_k} slots)"
    )
    return entries


# ---------------------------------------------------------------------------
# Phase 3: Conflict Resolution
# ---------------------------------------------------------------------------

KEEP = "keep"
UNCERTAIN = "uncertain"
WEAKEN = "weakened"
DISCARD = "discard"
FORGOTTEN = "FORGOTTEN"


def phase3_classify(entries: list,
                    strength_threshold: float = 0.3,
                    coherence_threshold: float = 0.12,
                    escalation_cycles: int = 5,
                    escalation_tension_floor: float = 0.3) -> list:
    """Cross-trace agreement classification with escalation logic (§3.7.1).

    Escalation: if a memory has been open_tension for >escalation_cycles sleep
    cycles with tension still above escalation_tension_floor, it is flagged for
    partner review. This is the 'therapist referral' — the system admits it
    cannot resolve this alone.
    """
    counts = {KEEP: 0, UNCERTAIN: 0, WEAKEN: 0, DISCARD: 0, FORGOTTEN: 0}
    escalation_count = 0

    for entry in entries:
        metadata = entry.get("metadata") or {}
        tension = float(metadata.get("tension_score", 0.0) or 0.0)
        if entry.get("_status") == FORGOTTEN:
            # Expiration is an upstream terminal decision. Preserve it and only
            # populate metrics needed by the later snapshot path.
            entry.setdefault("_coherence", float(metadata.get("coherence_score", 0.0) or 0.0))
            entry["_tension"] = tension
            entry["_open_tension"] = False
            counts[FORGOTTEN] += 1
            continue

        strength = entry["_strength"]
        coherence = abs(entry.get("_coherence", 0.0))
        open_tension = bool(metadata.get("open_tension", False))
        tension_hit = bool(metadata.get("tension_hit", False))
        tension_status = str(metadata.get("tension_status", "") or "").strip().upper()
        high_tension = open_tension or tension_hit or tension_status == "OPEN" or tension > 0.5

        # Escalation check: too many unresolved cycles?
        sleep_cycles = int(metadata.get("sleep_tension_cycles", 0) or 0)
        already_escalated = bool(metadata.get("escalated_to_partner", False))

        if (high_tension
                and not already_escalated
                and sleep_cycles > escalation_cycles
                and tension > escalation_tension_floor):
            metadata["escalated_to_partner"] = True
            metadata["escalation_cycle"] = sleep_cycles
            metadata["escalation_tension"] = tension
            escalation_count += 1
            print(
                f"  [escalate] Memory escalated to partner after {sleep_cycles} cycles "
                f"(tension={tension:.3f}): {entry.get('content', '')[:60]}..."
            )

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
        entry["_open_tension"] = high_tension
        counts[status] += 1

    print(f"[phase3] Classification: {counts}, escalated: {escalation_count}")
    return entries


# ---------------------------------------------------------------------------
# Phase 4: Distilled Residue
# ---------------------------------------------------------------------------

def _normalize_text(value) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def _truncate(text: str, limit: int = 180) -> str:
    cleaned = _normalize_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def infer_sleep_failure_class(entry: dict) -> str:
    metadata = entry.get("metadata") or {}
    explicit_failure = _normalize_text(metadata.get("failure_class"))
    if explicit_failure:
        return explicit_failure
    user_text = _normalize_text(metadata.get("user")).lower()
    response_text = _normalize_text(metadata.get("response")).lower()
    event_gist = _normalize_text(metadata.get("event_gist")).lower()

    if any(token in user_text for token in ("what is your name", "what's your name", "asked your name", "who are you", "who am i", "who am i to you")):
        if any(token in response_text for token in ("as an ai", "language model", "openai", "guidelines", "authorized")):
            return "identity_deflection"
        return "identity_probe"

    if "remember" in user_text or "yesterday" in user_text or "earlier" in user_text or "previous" in user_text:
        if any(token in response_text for token in ("i don't know", "not sure", "hello!", "openai", "language model")):
            return "wrong_memory_confabulation"
        return "continuity_probe"

    if metadata.get("open_tension") or entry.get("_open_tension"):
        return "open_tension"

    direct_question = "?" in user_text or bool(re.match(r"^(who|what|when|where|why|how|do you|did you|can you|are you)\b", user_text))
    if direct_question and not any(token in response_text for token in ("yes", "no", "i", "you")):
        return "direct_question_miss"

    if "identity and continuity challenge" in event_gist:
        return "continuity_probe"
    return "episodic_residue"


def build_sleep_residue(entry: dict) -> dict:
    metadata = entry.get("metadata") or {}
    failure_class = infer_sleep_failure_class(entry)
    source_session = _normalize_text(metadata.get("session"))
    source_turn = metadata.get("turn")
    source_ref = f"{source_session}:{source_turn}" if source_session or source_turn is not None else ""

    residue_kind = "episodic_residue"
    trigger_pattern = _normalize_text(metadata.get("trigger_pattern"))
    distilled_lesson = _truncate(metadata.get("event_gist") or entry.get("content") or "")
    repair_rule = _normalize_text(metadata.get("failure_repair_rule") or metadata.get("repair_rule"))
    packet_symptom = _normalize_text(metadata.get("failure_symptom"))

    if failure_class == "identity_deflection":
        residue_kind = "repair_memory"
        trigger_pattern = trigger_pattern or "identity_or_name_probe"
        distilled_lesson = packet_symptom or "Identity questions pulled the model into generic assistant ontology instead of shared history."
        repair_rule = repair_rule or "Answer identity and name questions directly from shared history before any generic ontology fallback."
    elif failure_class == "continuity_probe":
        residue_kind = "identity_anchor"
        trigger_pattern = trigger_pattern or "continuity_probe"
        distilled_lesson = packet_symptom or "Continuity questions should search shared history and recent prior turns, not improvise from generic model priors."
        repair_rule = repair_rule or "When Laura asks about earlier or yesterday, prefer recalled shared history over fresh invention."
    elif failure_class == "wrong_memory_confabulation":
        residue_kind = "repair_memory"
        trigger_pattern = trigger_pattern or "memory_probe_after_failed_recall"
        distilled_lesson = packet_symptom or "Memory prompts triggered confident but wrong reconstruction."
        repair_rule = repair_rule or "If recall is weak or conflicting, state uncertainty and stay anchored to retrieved evidence."
    elif failure_class == "open_tension":
        residue_kind = "open_tension_summary"
        trigger_pattern = trigger_pattern or "unresolved_high_tension"
        distilled_lesson = _truncate(metadata.get("event_gist") or entry.get("content") or "")
        repair_rule = repair_rule or "Keep this unresolved thread available for future re-entry."
    elif failure_class == "direct_question_miss":
        residue_kind = "repair_memory"
        trigger_pattern = trigger_pattern or "direct_question_without_direct_answer"
        distilled_lesson = packet_symptom or "A direct question was not answered directly."
        repair_rule = repair_rule or "Answer Laura's explicit question first before summarizing, interviewing, or reframing."
    elif failure_class == "stale_mode_lock":
        residue_kind = "repair_memory"
        trigger_pattern = trigger_pattern or "stale_mode_lock"
        distilled_lesson = packet_symptom or "A stale response pattern overrode the actual turn."
        repair_rule = repair_rule or "Break stale mode lock and answer the current turn instead of repeating the old scene."

    return {
        "ts": datetime.now().isoformat(),
        "source_memory_ref": source_ref,
        "source_session": source_session,
        "source_turn": source_turn,
        "source_sleep_status": entry.get("_status", ""),
        "sleep_residue_kind": residue_kind,
        "failure_class": failure_class,
        "trigger_pattern": trigger_pattern,
        "distilled_lesson": distilled_lesson,
        "repair_rule": repair_rule,
        "event_gist": _normalize_text(metadata.get("event_gist")),
        "user_preview": _truncate(metadata.get("user")),
        "response_preview": _truncate(metadata.get("response")),
        "coherence": float(entry.get("_coherence", 0.0) or 0.0),
        "strength": float(entry.get("_strength", 0.0) or 0.0),
        "open_tension": bool(entry.get("_open_tension")),
    }


def load_failure_packets(path: Path) -> list:
    if not path.exists():
        return []
    packets = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_num, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"[skip] failure line {line_num}: bad JSON - {exc}")
                continue
            if not isinstance(row, dict):
                continue
            packets.append(row)
    return packets


def attach_failure_packets(entries: list, failure_packets: list) -> tuple[list, int]:
    if not entries or not failure_packets:
        return entries, 0

    packet_index = {}
    for packet in failure_packets:
        key = (
            _normalize_text(packet.get("session")),
            int(packet.get("turn_index", 0) or 0),
        )
        packet_index[key] = packet

    attached = 0
    for entry in entries:
        metadata = entry.setdefault("metadata", {})
        key = (
            _normalize_text(metadata.get("session")),
            int(metadata.get("turn", 0) or 0),
        )
        packet = packet_index.get(key)
        if packet is None:
            continue
        metadata["failure_class"] = _normalize_text(packet.get("failure_class"))
        metadata["failure_mode_before"] = _normalize_text(packet.get("mode_before"))
        metadata["failure_user_intent"] = _normalize_text(packet.get("user_intent"))
        metadata["failure_symptom"] = _normalize_text(packet.get("symptom"))
        metadata["failure_repair_rule"] = _normalize_text(packet.get("repair_rule"))
        metadata["failure_confidence"] = float(packet.get("confidence", 0.0) or 0.0)
        metadata["failure_source"] = _normalize_text(packet.get("source"))
        attached += 1
    return entries, attached


def build_sleep_residue_entries(entries: list) -> list:
    return [
        build_sleep_residue(entry)
        for entry in entries
        if entry.get("_status") in (KEEP, UNCERTAIN)
    ]


def write_residue_log(residue_entries: list, residue_path: Path, dry_run: bool = False):
    if dry_run:
        print(f"[phase4] [dry-run] Would write {len(residue_entries)} residue entries to {residue_path}")
        return
    residue_path.parent.mkdir(parents=True, exist_ok=True)
    with residue_path.open("w", encoding="utf-8") as handle:
        for row in residue_entries:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[phase4] Sleep residue log -> {residue_path}")


# ---------------------------------------------------------------------------
# Phase 5: Identity Distillation + Flush
# ---------------------------------------------------------------------------

def phase5_flush(entries: list, sink_fn, snapshot_path: Path,
                 mamba_state_path: str, residue_path: Path, dry_run: bool = False) -> dict:
    """Write validated entries to Qdrant and save disposition snapshot."""
    to_write = [entry for entry in entries if entry.get("_status") in (KEEP, UNCERTAIN)]
    to_archive = [entry for entry in entries if entry.get("_status") in (WEAKEN, DISCARD)]
    forgotten = [entry for entry in entries if entry.get("_status") == FORGOTTEN]
    residue_entries = build_sleep_residue_entries(entries)

    print(
        f"[phase5] Writing {len(to_write)} entries to Qdrant "
        f"({len(to_archive)} archived/discarded, {len(forgotten)} forgotten, {len(residue_entries)} residue entries)"
    )

    written = 0
    failed = 0

    if not dry_run and sink_fn is not None:
        for entry in to_write:
            try:
                residue = build_sleep_residue(entry)
                entry["metadata"]["sleep_status"] = entry["_status"]
                entry["metadata"]["sleep_strength"] = entry["_strength"]
                entry["metadata"]["sleep_coherence"] = entry["_coherence"]
                entry["metadata"]["sleep_coherence_source"] = entry.get("_coherence_source", "metadata")
                entry["metadata"]["sleep_tension"] = entry.get("_tension", 0.0)
                entry["metadata"]["sleep_open_tension"] = bool(entry.get("_open_tension"))
                entry["metadata"]["sleep_residue_kind"] = residue["sleep_residue_kind"]
                entry["metadata"]["failure_class"] = residue["failure_class"]
                entry["metadata"]["trigger_pattern"] = residue["trigger_pattern"]
                entry["metadata"]["distilled_lesson"] = residue["distilled_lesson"]
                entry["metadata"]["repair_rule"] = residue["repair_rule"]
                entry["metadata"]["source_memory_ref"] = residue["source_memory_ref"]
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
        "open_tension_count": sum(1 for entry in entries if entry.get("_open_tension")),
        "escalated_count": sum(
            1 for entry in entries
            if entry.get("metadata", {}).get("escalated_to_partner", False)
        ),
        "tension_resolved_by_decay": sum(
            1 for entry in entries
            if entry.get("metadata", {}).get("tension_status") == "RESOLVED_BY_DECAY"
        ),
        "mean_tension": float(np.mean([
            entry.get("_tension", 0.0) for entry in entries
        ])) if entries else 0.0,
        "max_sleep_tension_cycles": max(
            (int(entry.get("metadata", {}).get("sleep_tension_cycles", 0) or 0) for entry in entries),
            default=0,
        ),
        "residue_count": len(residue_entries),
        "residue_kinds": {
            kind: sum(1 for row in residue_entries if row.get("sleep_residue_kind") == kind)
            for kind in sorted({row.get("sleep_residue_kind", "") for row in residue_entries})
        },
        "mean_strength": float(np.mean([entry["_strength"] for entry in entries])) if entries else 0.0,
        "mean_coherence": float(np.mean([abs(entry["_coherence"]) for entry in entries])) if entries else 0.0,
        "same_space_replay_count": sum(
            1 for entry in entries if entry.get("_coherence_source") == "mamba_hidden_last_token_replay"
        ),
    }

    write_residue_log(residue_entries, residue_path, dry_run=dry_run)

    if not dry_run:
        snapshot_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[phase5] Disposition snapshot -> {snapshot_path}")
    else:
        print(f"[phase5] [dry-run] Would save snapshot to {snapshot_path}")
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
    parser.add_argument(
        "--residue-path",
        default="sleep_residue_latest.jsonl",
        help="Where to save distilled sleep residue JSONL",
    )
    parser.add_argument(
        "--failure-path",
        default="failure_log.jsonl",
        help="Optional failure packet log to fold into sleep residue generation",
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
    parser.add_argument("--tension-decay", type=float, default=0.85,
                        help="Per-cycle tension retention factor (§3.7.1 anti-PTSD)")
    parser.add_argument("--tension-floor-drain", type=float, default=0.02,
                        help="Absolute tension reduction per cycle (ensures eventual resolution)")
    parser.add_argument("--tension-resolve-threshold", type=float, default=0.1,
                        help="Tension below this auto-resolves open_tension status")
    parser.add_argument("--escalation-cycles", type=int, default=5,
                        help="Sleep cycles before unresolved tension escalates to partner")
    parser.add_argument("--escalation-tension-floor", type=float, default=0.3,
                        help="Minimum tension to trigger escalation")
    parser.add_argument("--tension-budget-ratio", type=float, default=0.30,
                        help="Max fraction of replay slots for open_tension memories")
    parser.add_argument("--strength-threshold", type=float, default=0.3)
    parser.add_argument("--coherence-threshold", type=float, default=0.12)
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
    residue_path = Path(args.residue_path)
    failure_path = Path(args.failure_path)

    entries = load_pending(pending_path)
    if not entries:
        print("[ok] No pending entries. Nothing to reconcile.")
        return 0

    failure_packets = load_failure_packets(failure_path)
    entries, failure_attached = attach_failure_packets(entries, failure_packets)
    if failure_packets:
        print(
            f"[sleep] Loaded {len(failure_packets)} failure packets from {failure_path} "
            f"({failure_attached} matched to pending entries)"
        )

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

    entries = phase1_decay(
        entries,
        decay_factor=args.decay_factor,
        tension_decay=args.tension_decay,
        tension_floor_drain=args.tension_floor_drain,
        tension_resolve_threshold=args.tension_resolve_threshold,
    )
    entries = phase1b_expiration_and_relevance(
        entries,
        rules=None,  # Placeholder for Phase 1c rules load
    )
    entries = phase2_replay(
        entries, bootstrap_state,
        top_k=args.top_k,
        replay_stack=replay_stack,
        tension_budget_ratio=args.tension_budget_ratio,
    )
    entries = phase3_classify(
        entries,
        strength_threshold=args.strength_threshold,
        coherence_threshold=args.coherence_threshold,
        escalation_cycles=args.escalation_cycles,
        escalation_tension_floor=args.escalation_tension_floor,
    )

    sink_fn = None
    if not args.dry_run and not args.skip_qdrant:
        try:
            from sleep_flush import create_sink
            sink_fn = create_sink(args.host, args.port, args.collection, args.embedding_model)
        except Exception as exc:
            print(f"[warn] Could not create Qdrant sink: {exc}")

    snapshot = phase5_flush(
        entries,
        sink_fn,
        snapshot_path,
        mamba_state_path=args.mamba_state,
        residue_path=residue_path,
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
