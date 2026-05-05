"""
Shared autobiographical-memory helpers for the current D2 private-recall path.

This is intentionally modest. It does not try to solve the whole self-model.
It adds enough structure that stored memories stop being flat transcript scraps
and start looking like recent autobiographical event packets.
"""

from __future__ import annotations

import datetime
import math
from typing import Any, Dict, List, Optional

from memory_evidence import enrich_memory_evidence_metadata


def _parse_memory_timestamp(value: Any) -> datetime.datetime:
    if not value:
        return datetime.datetime.now(datetime.timezone.utc)
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.datetime.now(datetime.timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def calculate_expiration(memory_kind: str, created_at: Optional[str] = None) -> Optional[str]:
    """Calculate expiration time based on H2-EMV learned relevance rules."""
    if memory_kind == "identity_anchor":
        return None

    lifetimes_days = {
        "salient_episode": 60,       # 30 * 2
        "attended_episode": 14,      # 14 * 1
        "noted_episode": 7,          # 7 * 1
        "relationship_anchor": 360,  # 90 * 4
        "correction": 180            # 60 * 3
    }
    days = lifetimes_days.get(memory_kind, 14)

    try:
        base_time = _parse_memory_timestamp(created_at)
        return (base_time + datetime.timedelta(days=days)).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def _memory_age_seconds(created_at: Any, now: Optional[datetime.datetime] = None) -> float:
    current = now or datetime.datetime.now(datetime.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=datetime.timezone.utc)
    current = current.astimezone(datetime.timezone.utc)
    created = _parse_memory_timestamp(created_at)
    return max(0.0, (current - created).total_seconds())


def temporal_feel_label(age_seconds: float) -> str:
    """Compress exact age into a fuzzy lived-time bucket."""
    age = max(0.0, float(age_seconds or 0.0))
    if age <= 5 * 60:
        return "right_now"
    if age <= 60 * 60:
        return "just_now"
    if age <= 18 * 60 * 60:
        return "earlier_today"
    if age <= 2 * 24 * 60 * 60:
        return "yesterdayish"
    if age <= 14 * 24 * 60 * 60:
        return "recent_days"
    if age <= 90 * 24 * 60 * 60:
        return "long_ago"
    return "forever_ago"


def build_temporal_qualia(
    metadata: Dict[str, Any],
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """Build a small non-semantic time-feel packet for memory conditioning.

    Exact timestamps stay in metadata. This packet is deliberately fuzzy: it is
    meant to tell the bridge whether a memory feels warm, old, repeated, or
    stale without corrupting the semantic embedding geometry.
    """
    metadata = dict(metadata or {})
    created_at = (
        metadata.get("created_at")
        or metadata.get("timestamp")
        or metadata.get("queued_at")
    )
    last_seen_at = (
        metadata.get("last_recalled_at")
        or metadata.get("last_seen_at")
        or metadata.get("last_accessed_at")
        or created_at
    )
    age_seconds = _memory_age_seconds(created_at, now=now)
    last_seen_seconds = _memory_age_seconds(last_seen_at, now=now)

    try:
        sleep_cycles_since = max(0, int(metadata.get("sleep_cycles_since", 0) or 0))
    except (TypeError, ValueError):
        sleep_cycles_since = 0
    try:
        recall_count = max(0, int(metadata.get("recall_count", metadata.get("relevance_extensions", 0)) or 0))
    except (TypeError, ValueError):
        recall_count = 0

    return {
        "temporal_schema_version": "d2_temporal_qualia_v1",
        "feel": temporal_feel_label(age_seconds),
        "age_seconds": round(age_seconds, 3),
        "last_seen_seconds": round(last_seen_seconds, 3),
        "log_age_seconds": round(math.log1p(age_seconds), 6),
        "log_last_seen_seconds": round(math.log1p(last_seen_seconds), 6),
        "sleep_cycles_since": sleep_cycles_since,
        "recall_count": recall_count,
        "same_wake": infer_time_scope(metadata) == "current_session",
    }


AUTOBIO_SCHEMA_VERSION = "d2_autobio_v1"


def _clean_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def _truncate(text: str, limit: int = 220) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _strip_leading_speaker(text: str, speaker_name: str) -> str:
    cleaned = _clean_text(text)
    lowered = cleaned.lower()
    speaker_lower = _clean_text(speaker_name).lower()
    for prefix in (f"{speaker_lower}:", f"{speaker_lower},", f"{speaker_lower} "):
        if lowered.startswith(prefix):
            return cleaned[len(prefix):].lstrip()
    return cleaned


def _clamp_unit(value: Any) -> Optional[float]:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return numeric


def infer_memory_kind(metadata: Dict[str, Any]) -> str:
    explicit_kind = _clean_text(metadata.get("memory_kind"))
    if explicit_kind:
        return explicit_kind

    decision = _clean_text(metadata.get("decision")).upper()
    if bool(metadata.get("open_tension")):
        return "open_tension"
    if decision == "CONSOLIDATE":
        return "salient_episode"
    if decision == "ATTEND":
        return "attended_episode"
    if decision == "NOTE":
        return "noted_episode"
    return "remembered_episode"


def infer_time_scope(metadata: Dict[str, Any]) -> str:
    explicit = _clean_text(metadata.get("time_scope"))
    if explicit:
        return explicit
    if _clean_text(metadata.get("life_period_id")):
        return "life_period"
    return "current_session"


def infer_confidence_score(metadata: Dict[str, Any]) -> Optional[float]:
    for key in ("sleep_coherence", "coherence_score"):
        score = _clamp_unit(metadata.get(key))
        if score is not None:
            return score
    return None


def infer_confidence_label(metadata: Dict[str, Any]) -> str:
    sleep_status = _clean_text(metadata.get("sleep_status")).lower()
    if sleep_status == "keep":
        return "anchored"
    if sleep_status == "uncertain":
        return "partial"
    if sleep_status in {"weakened", "discard"}:
        return "fragile"

    score = infer_confidence_score(metadata)
    if score is None:
        user_text = _clean_text(metadata.get("user"))
        response_text = _clean_text(metadata.get("response"))
        return "scene" if user_text and response_text else "gist"
    if score >= 0.45:
        return "anchored"
    if score >= 0.20:
        return "partial"
    return "gist"


def _build_event_gist(content: str, metadata: Dict[str, Any], speaker_name: str) -> str:
    raw_user_text = _clean_text(metadata.get("user"))
    user_text = _strip_leading_speaker(raw_user_text, speaker_name)
    response_text = _clean_text(metadata.get("response"))
    if user_text and response_text:
        user_gist = raw_user_text if raw_user_text and raw_user_text != user_text else f"{speaker_name} said {user_text}"
        return _truncate(f"{user_gist}; I replied {response_text}")
    if user_text:
        return _truncate(raw_user_text if raw_user_text and raw_user_text != user_text else f"{speaker_name} said {user_text}")
    if response_text:
        return _truncate(f"I replied {response_text}")
    return _truncate(content)


def build_autobiographical_frame(
    content: str,
    metadata: Dict[str, Any],
    speaker_name: Optional[str] = None,
) -> Dict[str, Any]:
    metadata = dict(metadata or {})
    resolved_speaker = _clean_text(speaker_name or metadata.get("speaker_name")) or "User"
    event_gist = _build_event_gist(content, metadata, resolved_speaker)
    confidence_label = infer_confidence_label(metadata)
    temporal_qualia = build_temporal_qualia(metadata)

    return {
        "schema_version": AUTOBIO_SCHEMA_VERSION,
        "memory_layer": "episodic_recent",
        "memory_kind": infer_memory_kind(metadata),
        "recall_mode": "recent_scene",
        "self_anchor": {
            "label": "I",
            "perspective": "first_person",
            "continuity_role": "remembering_self",
        },
        "relationship_anchor": {
            "name": resolved_speaker,
            "role": "current_interlocutor",
            "reference_when_present": "you",
        },
        "people": [
            {
                "name": resolved_speaker,
                "role": "current_interlocutor",
                "present_now": True,
            }
        ],
        "context": {
            "time_scope": infer_time_scope(metadata),
            "session": _clean_text(metadata.get("session")),
            "turn": metadata.get("turn"),
            "memory_scope": _clean_text(metadata.get("memory_scope")),
            "qdrant_collection": _clean_text(metadata.get("qdrant_collection")),
            "temporal_qualia": temporal_qualia,
        },
        "event": {
            "gist": event_gist,
            "user_signal": _clean_text(metadata.get("user")),
            "self_response": _clean_text(metadata.get("response")),
            "meaning": _clean_text(content),
            "decision": _clean_text(metadata.get("decision")),
        },
        "affect": {
            "surprise": metadata.get("surprise_score"),
            "salience": metadata.get("salience_score"),
            "tension": metadata.get("tension_score"),
            "open_tension": bool(metadata.get("open_tension")),
        },
        "status": {
            "sleep_status": _clean_text(metadata.get("sleep_status")),
            "confidence_label": confidence_label,
            "confidence_score": infer_confidence_score(metadata),
        },
    }


def enrich_memory_metadata(
    content: str,
    metadata: Dict[str, Any],
    speaker_name: Optional[str] = None,
) -> Dict[str, Any]:
    enriched = enrich_memory_evidence_metadata(
        content,
        dict(metadata or {}),
        current_interlocutor=speaker_name,
    )
    frame = build_autobiographical_frame(content, enriched, speaker_name=speaker_name)
    enriched["autobio_schema_version"] = AUTOBIO_SCHEMA_VERSION
    enriched["memory_kind"] = frame["memory_kind"]
    enriched["recall_mode"] = frame["recall_mode"]
    enriched["time_scope"] = frame["context"]["time_scope"]
    enriched["event_gist"] = frame["event"]["gist"]
    enriched["relationship_anchor"] = frame["relationship_anchor"]["name"]
    enriched["people"] = [person["name"] for person in frame["people"]]
    enriched["confidence_label"] = frame["status"]["confidence_label"]
    enriched["temporal_qualia"] = frame["context"]["temporal_qualia"]
    enriched["autobiographical_frame"] = frame

    if "expiration" not in enriched:
        created_time = enriched.get("created_at") or enriched.get("timestamp") or enriched.get("queued_at")
        enriched["expiration"] = calculate_expiration(
            frame["memory_kind"],
            created_time
        )
    enriched.setdefault("relevance_extensions", 0)
    enriched.setdefault("relevance_rules_applied", [])

    return enriched


def build_recall_text(
    content: str,
    metadata: Dict[str, Any],
    speaker_name: Optional[str] = None,
) -> str:
    enriched = enrich_memory_metadata(content, metadata, speaker_name=speaker_name)
    frame = enriched["autobiographical_frame"]
    resolved_speaker = frame["relationship_anchor"]["name"]
    lines: List[str] = [
        f"{resolved_speaker} is the person I am speaking with here.",
        f"When {resolved_speaker} is present, I should treat this as part of our own shared history.",
        f"Memory layer: {frame['memory_layer']}.",
        f"Time scope: {frame['context']['time_scope']}.",
        f"What comes to mind first: {frame['event']['gist']}",
    ]

    if frame["event"]["user_signal"]:
        lines.append(f"Earlier, {resolved_speaker} had told me: {frame['event']['user_signal']}")
    if frame["event"]["self_response"]:
        lines.append(f"I had replied: {frame['event']['self_response']}")
    if frame["event"]["meaning"]:
        lines.append(f"Why it mattered: {frame['event']['meaning']}")
    if frame["affect"]["open_tension"]:
        lines.append("This still felt unresolved.")
    if frame["status"]["confidence_label"]:
        lines.append(f"Detail confidence: {frame['status']['confidence_label']}")

    return "\n".join(line for line in lines if line).strip()


def format_memory_anchor_lines(
    content: str,
    metadata: Dict[str, Any],
    current_speaker: Optional[str] = None,
) -> List[str]:
    speaker_name = _clean_text(metadata.get("speaker_name")) or _clean_text(current_speaker) or None
    enriched = enrich_memory_metadata(content, metadata, speaker_name=speaker_name)
    frame = enriched["autobiographical_frame"]
    resolved_speaker = frame["relationship_anchor"]["name"]
    use_second_person = bool(current_speaker) and resolved_speaker == _clean_text(current_speaker)

    lines = [f"What comes back first: {frame['event']['gist']}"]
    if frame["event"]["user_signal"]:
        if use_second_person:
            lines.append(f"What you had told me: {frame['event']['user_signal']}")
        else:
            lines.append(f"What {resolved_speaker} had told me: {frame['event']['user_signal']}")
    if frame["event"]["self_response"]:
        lines.append(f"What I had said back: {frame['event']['self_response']}")
    if frame["event"]["meaning"]:
        lines.append(f"Why it mattered: {frame['event']['meaning']}")
    if frame["affect"]["open_tension"]:
        lines.append("This still felt unresolved.")
    lines.append(f"Detail confidence: {frame['status']['confidence_label']}")
    return lines
