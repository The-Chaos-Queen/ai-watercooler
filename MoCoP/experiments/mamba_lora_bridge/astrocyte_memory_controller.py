"""Astrocyte-inspired deterministic memory quality controller.

Sits between Qdrant retrieval and prompt conditioning. Wraps each retrieved
memory in a MemoryProcess, scores source quality / salience / contamination /
confidence, then emits a compact ModulationPacket for generation.

This is a retrieval-quality/modulation scaffold, not a biological astrocyte or
Dense Associative Memory implementation.

Stdlib only -- no ML dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TELEMETRY_MARKERS = (
    "gate summary", "threshold", "verdict", "model_label", "qwen", "mamba",
    "probe", "telemetry", "stop", "pass", "fail", "wake probe",
)

CLEAN_SOURCE_PREFIXES = ("organic_",)
CLEAN_SOURCE_TYPES = {"autobiographical_memory", "remembered_episode"}
LOW_TRUST_SOURCE_TYPES = {"steve_gate_event", "gate_summary", "telemetry"}

# Words too common to count as salient query terms.
STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "do", "does", "did",
    "you", "your", "my", "me", "i", "we", "our", "he", "she", "it",
    "they", "them", "that", "this", "what", "which", "who", "whom",
    "how", "when", "where", "why", "can", "could", "will", "would",
    "shall", "should", "may", "might", "must", "have", "has", "had",
    "be", "been", "being", "not", "no", "nor", "but", "or", "and",
    "if", "of", "to", "in", "on", "at", "for", "by", "with", "from",
    "up", "out", "off", "over", "about", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "only",
    "own", "same", "so", "than", "too", "very", "just", "because",
    "as", "until", "while", "any", "also", "than", "still", "its",
    "let", "us", "am", "tell", "told", "said", "say", "know", "knew",
    "think", "thought", "remember", "get", "got", "go", "went", "come",
    "came", "see", "saw", "look", "like", "make", "made", "take", "took",
    "give", "gave", "find", "found", "thing", "things", "much", "many",
    "well", "now", "even", "back", "way", "long", "new", "old", "big",
    "little", "good", "great", "first", "last", "really", "always",
})

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MemoryProcess:
    """One local wrapper around a retrieved memory row."""
    row_id: str
    content: str
    source_type: str = ""
    speaker: str = ""
    relationship_anchor: str = ""
    memory_kind: str = ""
    confidence_label: str = ""
    retrieval_score: float = 0.0
    salience: float = 0.0
    confidence: float = 0.0
    contamination_risk: float = 0.0
    behavioral_effect: str = ""
    warnings: tuple = ()


@dataclass(frozen=True)
class ModulationPacket:
    """Compact wake-state guidance produced from all memory processes."""
    process_count: int
    clean_process_count: int
    available_memories: tuple = ()
    response_policy: tuple = ()
    warnings: tuple = ()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(value: Any) -> str:
    return str(value or "").strip()


def _metadata(row: dict) -> dict:
    metadata = row.get("metadata") or {}
    return metadata if isinstance(metadata, dict) else {}


def _contains_telemetry(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in TELEMETRY_MARKERS)


def source_quality(source_type: str) -> float:
    source = source_type.lower()
    if any(source.startswith(p) for p in CLEAN_SOURCE_PREFIXES) and source.endswith("memory"):
        return 0.95
    if source in CLEAN_SOURCE_TYPES:
        return 0.85
    if source in LOW_TRUST_SOURCE_TYPES:
        return 0.15
    return 0.50


def contamination_risk(row: dict) -> float:
    md = _metadata(row)
    source = _norm(md.get("source_type")).lower()
    text = "{} {} {}".format(
        row.get("content", ""),
        md.get("event_gist", ""),
        md.get("summary", ""),
    )
    risk = 0.0
    if source in LOW_TRUST_SOURCE_TYPES:
        risk += 0.55
    if _contains_telemetry(text):
        risk += 0.35
    return min(1.0, risk)


def _short_memory(content: str, max_chars: int = 180) -> str:
    text = re.sub(r"\s+", " ", _norm(content))
    text = _sanitize_memory_snippet(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def _sanitize_memory_snippet(text: str) -> str:
    """Keep raw memory snippets from spoofing prompt labels or block delimiters."""
    sanitized = re.sub(r"\buser\s*:", "speaker:", text, flags=re.IGNORECASE)
    sanitized = re.sub(r"\bassistant\s*:", "responder:", sanitized, flags=re.IGNORECASE)
    sanitized = sanitized.replace("[Private memory orientation]", "[Private memory orientation redacted]")
    sanitized = sanitized.replace("[/Private memory orientation]", "[/Private memory orientation redacted]")
    return sanitized


def _naive_stem(word: str) -> str:
    """Minimal plural stripping -- just drop trailing 's' for 5+ char words."""
    if len(word) >= 5 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _extract_salient_terms(text: str, min_len: int = 3) -> set:
    """Extract meaningful words from text, dropping stopwords and short tokens.

    Applies naive stemming so 'color' and 'colors' match.
    """
    words = set(re.findall(r"[a-z]+", text.lower()))
    return {_naive_stem(w) for w in words if len(w) >= min_len and w not in STOP_WORDS}


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def build_memory_processes(
    rows: Iterable[dict],
    query_text: str = "",
    visible_user_label: str = "",
) -> list:
    """Wrap each retrieved row in a MemoryProcess with quality/salience scores."""
    processes: List[MemoryProcess] = []
    for row in rows or []:
        md = _metadata(row)
        content = (
            _norm(row.get("content"))
            or _norm(md.get("event_gist"))
            or _norm(md.get("summary"))
        )
        source_type = _norm(md.get("source_type"))
        risk = contamination_risk(row)
        quality = source_quality(source_type)
        retrieval_score = float(row.get("score", 0.0) or 0.0)
        salience = max(0.0, min(1.0,
            (0.55 * quality) + (0.35 * retrieval_score) + (0.10 * (1.0 - risk))
        ))
        confidence = max(0.0, min(1.0,
            (quality + retrieval_score + (1.0 - risk)) / 3.0
        ))
        warnings: List[str] = []
        if risk >= 0.5:
            warnings.append(
                "Possible telemetry/gate contamination; use only as low-trust context."
            )
        effect = "answer naturally from this memory if directly relevant; hedge if uncertain"
        processes.append(MemoryProcess(
            row_id=_norm(row.get("id")),
            content=content,
            source_type=source_type,
            speaker=_norm(md.get("speaker_name") or md.get("speaker")),
            relationship_anchor=_norm(md.get("relationship_anchor")),
            memory_kind=_norm(md.get("memory_kind")),
            confidence_label=_norm(md.get("confidence_label")),
            retrieval_score=retrieval_score,
            salience=salience,
            confidence=confidence,
            contamination_risk=risk,
            behavioral_effect=effect,
            warnings=tuple(warnings),
        ))
    return processes


def build_modulation_packet(
    processes: Iterable[MemoryProcess],
    query_text: str = "",
    max_memories: int = 5,
) -> ModulationPacket:
    """Build compact wake-state guidance from scored memory processes."""
    process_list = list(processes or [])
    clean = [p for p in process_list if p.contamination_risk < 0.5 and p.content]
    clean.sort(
        key=lambda p: (p.salience, p.confidence, p.retrieval_score),
        reverse=True,
    )
    available = tuple(_short_memory(p.content) for p in clean[:max_memories])
    warnings: List[str] = []
    for p in process_list:
        warnings.extend(p.warnings)

    # Contradiction / fake-memory guard: check whether the query makes a
    # specific claim that clean memory rows actually support. A single broad
    # overlap such as "Vesper" or "purple" is not enough to bless an otherwise
    # unsupported concrete claim like "golden bicycle".
    query_terms = _extract_salient_terms(query_text)
    if query_terms:
        if not clean:
            if len(query_terms) >= 2:
                warnings.append(
                    "No clean memory directly supports the query-specific claim; "
                    "do not affirm it as remembered."
                )
        else:
            memory_corpus = " ".join(p.content for p in clean).lower()
            memory_terms = _extract_salient_terms(memory_corpus, min_len=3)
            unsupported_terms = query_terms - memory_terms
            # One unsupported term is often just a generic paraphrase (e.g.
            # "color" when memory says "purple"). Two or more concrete
            # unsupported terms is a likely fake-claim or over-specific probe.
            if len(unsupported_terms) >= 2:
                warnings.append(
                    "No clean memory directly supports the query-specific claim; "
                    "do not affirm it as remembered."
                )

    policy = (
        "Answer naturally; do not mention retrieval machinery unless asked.",
        "If uncertain, say uncertain instead of inventing continuity.",
        "Prefer clean autobiographical memories over gate/eval telemetry.",
    )
    return ModulationPacket(
        process_count=len(process_list),
        clean_process_count=len(clean),
        available_memories=available,
        response_policy=policy,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def format_modulation_packet(packet: ModulationPacket) -> str:
    """Render a ModulationPacket as text suitable for prompt injection."""
    if packet.process_count <= 0 and not packet.warnings:
        return ""
    lines = ["[Private memory orientation]"]
    if packet.available_memories:
        lines.append("Relevant clean memory signals:")
        for item in packet.available_memories:
            lines.append("- {}".format(item))
    if packet.warnings:
        lines.append("Warnings:")
        for warning in packet.warnings:
            lines.append("- {}".format(warning))
    lines.append("Response policy:")
    for policy in packet.response_policy:
        lines.append("- {}".format(policy))
    lines.append("[/Private memory orientation]")
    return "\n".join(lines)


def build_memory_modulation_block(
    recalled_memories: Iterable[dict],
    recalled_clusters: Iterable[dict],
    query_text: str = "",
    visible_user_label: str = "",
    applied_to_prompt: bool = True,
    applied_to_state: bool = False,
) -> Tuple[str, dict]:
    """Build modulation block text and an audit metadata dict.

    Clusters are audited separately and do not become clean autobiographical
    memory signals. This keeps macro/theme context from masquerading as direct
    episodic evidence.
    """
    memory_rows = list(recalled_memories or [])
    cluster_rows = list(recalled_clusters or [])
    memory_processes = build_memory_processes(
        memory_rows,
        query_text=query_text,
        visible_user_label=visible_user_label,
    )
    cluster_processes = build_memory_processes(
        cluster_rows,
        query_text=query_text,
        visible_user_label=visible_user_label,
    )
    packet = build_modulation_packet(memory_processes, query_text=query_text)
    cluster_warnings = []
    for process in cluster_processes:
        cluster_warnings.extend(process.warnings)
    if cluster_warnings:
        packet = ModulationPacket(
            process_count=packet.process_count,
            clean_process_count=packet.clean_process_count,
            available_memories=packet.available_memories,
            response_policy=packet.response_policy,
            warnings=tuple(dict.fromkeys(list(packet.warnings) + cluster_warnings)),
        )
    text = format_modulation_packet(packet)
    clean_cluster_count = sum(1 for p in cluster_processes if p.contamination_risk < 0.5 and p.content)
    audit = {
        "process_count": len(memory_processes) + len(cluster_processes),
        "memory_process_count": len(memory_processes),
        "cluster_process_count": len(cluster_processes),
        "clean_process_count": packet.clean_process_count + clean_cluster_count,
        "clean_memory_process_count": packet.clean_process_count,
        "clean_cluster_process_count": clean_cluster_count,
        "warnings": list(packet.warnings),
        "available_memory_count": len(packet.available_memories),
        "applied_to_prompt": bool(applied_to_prompt and text),
        "applied_to_state": bool(applied_to_state),
    }
    return text, audit
