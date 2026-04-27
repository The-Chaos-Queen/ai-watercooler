"""
Shared autobiographical-memory helpers for the current D2 private-recall path.

This is intentionally modest. It does not try to solve the whole self-model.
It adds enough structure that stored memories stop being flat transcript scraps
and start looking like recent autobiographical event packets.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional


def calculate_expiration(memory_kind: str, created_at: Optional[str] = None) -> Optional[str]:
    """Calculates expiration time (τ) based on H2-EMV learned relevance rules."""
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
        if created_at:
            try:
                base_time = datetime.datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                if base_time.tzinfo is None:
                    base_time = base_time.replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                base_time = datetime.datetime.now(datetime.timezone.utc)
        else:
            base_time = datetime.datetime.now(datetime.timezone.utc)
            
        return (base_time + datetime.timedelta(days=days)).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


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
    enriched = dict(metadata or {})
    frame = build_autobiographical_frame(content, enriched, speaker_name=speaker_name)
    enriched["autobio_schema_version"] = AUTOBIO_SCHEMA_VERSION
    enriched["memory_kind"] = frame["memory_kind"]
    enriched["recall_mode"] = frame["recall_mode"]
    enriched["time_scope"] = frame["context"]["time_scope"]
    enriched["event_gist"] = frame["event"]["gist"]
    enriched["relationship_anchor"] = frame["relationship_anchor"]["name"]
    enriched["people"] = [person["name"] for person in frame["people"]]
    enriched["confidence_label"] = frame["status"]["confidence_label"]
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
