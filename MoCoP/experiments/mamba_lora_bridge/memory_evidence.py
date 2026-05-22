"""
MemoryEvidence v1 helpers.

This module computes perspective/evidence metadata for autobiographical memory
rows. It is intentionally pure: no Qdrant, no model calls, no server globals.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional


EVIDENCE_SCHEMA_VERSION = "d2_memory_evidence_v1"
PRIVATE_QDRANT_COLLECTION_PREFIX = "mocop_private_"

DIRECT_SHARED = "direct_shared_episode"
GROUP_SHARED = "group_shared_episode"
THIRD_PARTY = "third_party_mention"
SYSTEM_OBSERVATION = "system_observation"
DIRECT_OTHER_SESSION = "direct_other_session_episode"
UNRELATED = "unrelated"
UNCERTAIN = "uncertain"


def clean_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def canonical_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).lower())


def display_name(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    if text.islower() and len(text) > 1:
        return text[0].upper() + text[1:]
    return text


def collection_owner(collection_name: Any) -> str:
    collection = clean_text(collection_name)
    if collection.startswith(PRIVATE_QDRANT_COLLECTION_PREFIX):
        return display_name(collection[len(PRIVATE_QDRANT_COLLECTION_PREFIX):])
    return ""


def coerce_name_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raw_values = re.split(r"[,;/|]+", values)
    elif isinstance(values, dict):
        raw_values = values.values()
    elif isinstance(values, Iterable):
        raw_values = values
    else:
        raw_values = [values]

    names = []
    seen = set()
    for value in raw_values:
        if isinstance(value, dict):
            value = value.get("name") or value.get("label") or value.get("id")
        name = display_name(value)
        key = canonical_name(name)
        if not key or key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def dedupe_names(*groups: Any) -> list[str]:
    names = []
    seen = set()
    for group in groups:
        for name in coerce_name_list(group):
            key = canonical_name(name)
            if key and key not in seen:
                seen.add(key)
                names.append(name)
    return names


def infer_instance_owner(metadata: Dict[str, Any], explicit: Optional[str] = None) -> str:
    return (
        display_name(explicit)
        or display_name(metadata.get("instance_owner"))
        or collection_owner(metadata.get("qdrant_collection"))
        or display_name(metadata.get("instance_id"))
        or ""
    )


def infer_current_interlocutors(metadata: Dict[str, Any], explicit: Any = None) -> list[str]:
    frame = metadata.get("autobiographical_frame", {}) or {}
    frame_anchor = frame.get("relationship_anchor", {}) or {}
    return dedupe_names(
        explicit,
        metadata.get("current_interlocutor"),
        metadata.get("current_interlocutors"),
        metadata.get("speaker_name"),
        metadata.get("relationship_anchor"),
        frame_anchor.get("name"),
    )


def infer_speaker(metadata: Dict[str, Any], current_interlocutors: list[str]) -> str:
    return (
        display_name(metadata.get("speaker"))
        or display_name(metadata.get("source_actor"))
        or display_name(metadata.get("speaker_name"))
        or (current_interlocutors[0] if current_interlocutors else "")
    )


def infer_mentioned_entities(content: str, metadata: Dict[str, Any], direct_participants: list[str]) -> list[str]:
    direct_keys = {canonical_name(name) for name in direct_participants}
    frame = metadata.get("autobiographical_frame", {}) or {}
    frame_people = [person.get("name") for person in (frame.get("people", []) or []) if isinstance(person, dict)]
    candidates = dedupe_names(
        metadata.get("mentioned_entities"),
        metadata.get("people"),
        frame_people,
    )

    # Lightweight fallback for natural seeding rows. This is not NER; it only
    # helps preserve obvious names already present in short chat memories.
    text = "\n".join(
        clean_text(value)
        for value in (
            content,
            metadata.get("user"),
            metadata.get("response"),
            metadata.get("event_gist"),
        )
        if clean_text(value)
    )
    lexical_names = re.findall(r"\b[A-Z][a-zA-Z0-9_-]{2,}\b", text)
    candidates = dedupe_names(candidates, lexical_names)

    return [name for name in candidates if canonical_name(name) not in direct_keys]


def infer_evidence_confidence(metadata: Dict[str, Any], direct_participants: list[str]) -> float:
    for key in ("evidence_confidence", "confidence", "confidence_score", "coherence_score"):
        raw = metadata.get(key)
        if raw is None:
            continue
        try:
            return max(0.0, min(1.0, float(raw)))
        except (TypeError, ValueError):
            continue

    has_turn_pair = bool(clean_text(metadata.get("user")) and clean_text(metadata.get("response")))
    if has_turn_pair and direct_participants:
        return 0.95
    if direct_participants:
        return 0.75
    return 0.35


def infer_primary_evidence_kind(
    metadata: Dict[str, Any],
    speaker: str,
    current_interlocutors: list[str],
    instance_owner: str,
) -> str:
    source_type = canonical_name(metadata.get("source_type"))
    if source_type in {"systemobservation", "system", "runtimeobservation"}:
        return SYSTEM_OBSERVATION

    speaker_key = canonical_name(speaker)
    current_keys = {canonical_name(name) for name in current_interlocutors}

    if len(current_interlocutors) > 1:
        return GROUP_SHARED
    if speaker_key and speaker_key in current_keys:
        return DIRECT_SHARED
    if current_interlocutors:
        return DIRECT_SHARED
    return UNCERTAIN


def build_memory_evidence(
    content: str,
    metadata: Dict[str, Any],
    *,
    current_interlocutor: Any = None,
    instance_owner: Optional[str] = None,
) -> Dict[str, Any]:
    metadata = dict(metadata or {})
    owner = infer_instance_owner(metadata, explicit=instance_owner)
    current = infer_current_interlocutors(metadata, explicit=current_interlocutor)
    speaker = infer_speaker(metadata, current)
    direct_participants = dedupe_names(current, speaker)
    participant_set = dedupe_names(metadata.get("participant_set"), direct_participants)
    mentioned = infer_mentioned_entities(content, metadata, direct_participants)
    kind = infer_primary_evidence_kind(metadata, speaker, current, owner)
    confidence = infer_evidence_confidence(metadata, direct_participants)

    return {
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "instance_owner": owner,
        "current_interlocutor": current[0] if len(current) == 1 else "",
        "current_interlocutors": current,
        "speaker": speaker,
        "participant_set": participant_set,
        "direct_participants": direct_participants,
        "mentioned_entities": mentioned,
        "evidence_kind": kind,
        "evidence_confidence": confidence,
    }


def enrich_memory_evidence_metadata(
    content: str,
    metadata: Dict[str, Any],
    *,
    current_interlocutor: Any = None,
    instance_owner: Optional[str] = None,
) -> Dict[str, Any]:
    enriched = dict(metadata or {})
    enriched.update(
        build_memory_evidence(
            content,
            enriched,
            current_interlocutor=current_interlocutor,
            instance_owner=instance_owner,
        )
    )
    return enriched


def classify_evidence_for_subject(
    metadata: Dict[str, Any],
    subject: str,
    *,
    active_interlocutor: Optional[str] = None,
) -> str:
    """Classify a stored row's evidential value for a queried subject.

    This is the read-time companion to the write-time metadata. It is useful for
    deterministic ranking: semantic search finds candidates, this decides how
    direct the evidence is for the question.
    """
    subject_key = canonical_name(subject)
    if not subject_key:
        return clean_text(metadata.get("evidence_kind")) or UNCERTAIN

    direct_keys = {
        canonical_name(name)
        for name in dedupe_names(
            metadata.get("direct_participants"),
            metadata.get("current_interlocutor"),
            metadata.get("current_interlocutors"),
            metadata.get("speaker"),
            metadata.get("speaker_name"),
            metadata.get("relationship_anchor"),
        )
    }
    participant_keys = {
        canonical_name(name)
        for name in dedupe_names(metadata.get("participant_set"), metadata.get("people"))
    }
    mentioned_keys = {
        canonical_name(name)
        for name in dedupe_names(metadata.get("mentioned_entities"), metadata.get("people"))
    } - direct_keys
    current_keys = {canonical_name(name) for name in coerce_name_list(metadata.get("current_interlocutors"))}
    active_key = canonical_name(active_interlocutor)

    if subject_key in direct_keys or subject_key in current_keys:
        return DIRECT_SHARED
    if subject_key in mentioned_keys:
        return THIRD_PARTY
    if active_key and subject_key in participant_keys and active_key not in participant_keys:
        return DIRECT_OTHER_SESSION
    if subject_key in participant_keys:
        return DIRECT_SHARED
    return UNRELATED
