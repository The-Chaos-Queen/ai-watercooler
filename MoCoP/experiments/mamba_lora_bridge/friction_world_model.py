"""Minimal friction/world-model primitives for Alex.

This module is intentionally small and deterministic. It does not call an LLM,
modify live chat behavior, or depend on Qdrant. It provides the auditable v0
substrate for a pre-Qwen friction pass.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Literal


RuleStatus = Literal["candidate", "active", "retired"]


@dataclass
class FrictionRule:
    id: str
    title: str
    status: RuleStatus
    trigger_tags: list[str]
    rule_text: str
    failure_mode: str
    energy_terms: dict[str, float]
    evidence_ids: list[str]
    confidence: float
    activation_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TensionEvent:
    id: str
    turn_id: str
    kind: str
    severity: float
    predicted: str | None
    observed: str | None
    prediction_error: float | None
    evidence: dict[str, Any]
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CognitiveState:
    turn_id: str
    session_id: str
    current_speaker_id: str | None
    identity_confidence: float
    speech_act: str
    trigger_tags: list[str]
    topics: list[str]
    entities: list[dict[str, Any]]
    retrieved_memories: list[dict[str, Any]]
    active_rules: list[FrictionRule]
    active_tensions: list[TensionEvent]
    candidate_actions: list[dict[str, Any]] = field(default_factory=list)
    selected_action: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def classify_turn(message: str) -> dict[str, Any]:
    """Classify a user turn into a small speech-act/tag bundle.

    This is a deliberately conservative heuristic. It should be easy to inspect
    and wrong in obvious ways, not clever and opaque.
    """

    text = message.strip()
    lower = text.lower()
    tags: list[str] = []
    speech_act = "statement"

    hardware_terms = ["openrgb", "ml-ws", "fan", "rgb", "aura", "i2c", "smbus", "bios", "q-fan"]
    tool_terms = ["run", "ssh", "command", "test", "launch", "start", "install", "check"]

    if re.search(r"\b(no,?\s+.*wrong|wrong|incorrect|not quite|actually)\b", lower):
        speech_act = "correction"
        tags.extend(["correction", "prediction_error"])
    elif re.search(r"\bwho\b.*\b(said|told|mentioned)\b|\bremember who\b", lower):
        speech_act = "attribution_query"
        tags.extend(["attribution", "memory_recall"])
    elif re.search(r"\bwhat\b.*\bmy\b.*\b(favorite|favourite|preference|name|memory)\b", lower):
        speech_act = "personal_recall_query"
        tags.extend(["personal_fact", "memory_recall"])
    elif re.search(r"\bmy\b.*\b(favorite|favourite|preference)\b", lower):
        speech_act = "personal_preference_statement"
        tags.extend(["personal_fact", "preference"])
    elif any(term in lower for term in tool_terms):
        speech_act = "tool_action_request"
        tags.append("tool_action")

    if any(term in lower for term in hardware_terms):
        tags.extend(["hardware_risk", "tool_action"])
        if speech_act == "statement":
            speech_act = "tool_action_request"

    game_terms = ["ls20", "arc-agi", "arc agi", "level", "player", "wall", "door", "grid", "move"]
    if any(term in lower for term in game_terms):
        tags.extend(["interactive_puzzle", "game_state"])
        if speech_act == "statement":
            speech_act = "interactive_game_observation"

    if "croissant" in lower or "croissants" in lower:
        tags.append("food_preference")

    return {
        "speech_act": speech_act,
        "trigger_tags": _unique_preserve_order(tags),
    }


def extract_topics(message: str) -> list[str]:
    lower = message.lower()
    topics: list[str] = []
    if "ls20" in lower:
        topics.append("ls20")
    if "arc-agi" in lower or "arc agi" in lower:
        topics.append("arc-agi-3")
    if "croissant" in lower:
        topics.append("croissant")
    if "openrgb" in lower:
        topics.append("openrgb")
    if "ml-ws" in lower:
        topics.append("ml-ws")
    return _unique_preserve_order(topics)


def extract_observed_game_entities(message: str) -> list[dict[str, Any]]:
    """Extract a tiny set of explicitly observed game objects from text.

    This is intentionally conservative. It only marks common LS20-like nouns as
    observed when they literally appear in the observation text.
    """

    lower = message.lower()
    candidates = ["player", "wall", "walls", "door", "key", "goal", "tile", "grid", "cursor"]
    entities: list[dict[str, Any]] = []
    for term in candidates:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            normalized = term[:-1] if term == "walls" else term
            entities.append({"id": normalized, "type": "observed_game_object"})
    deduped: dict[str, dict[str, Any]] = {}
    for entity in entities:
        deduped.setdefault(entity["id"], entity)
    return list(deduped.values())


def build_cognitive_state_for_turn(
    message: str,
    turn_id: str,
    session_id: str,
    current_speaker_id: str | None,
    retrieved_memories: list[dict[str, Any]] | None = None,
    rules: list[FrictionRule] | None = None,
    identity_confidence: float = 0.95,
    max_rules: int = 5,
) -> CognitiveState:
    classification = classify_turn(message)
    trigger_tags = classification["trigger_tags"]
    active_rules = select_active_rules(rules or [], trigger_tags, max_rules=max_rules)
    return CognitiveState(
        turn_id=turn_id,
        session_id=session_id,
        current_speaker_id=current_speaker_id,
        identity_confidence=identity_confidence,
        speech_act=classification["speech_act"],
        trigger_tags=trigger_tags,
        topics=extract_topics(message),
        entities=extract_observed_game_entities(message),
        retrieved_memories=retrieved_memories or [],
        active_rules=active_rules,
        active_tensions=[],
    )


def _rule_from_dict(data: dict[str, Any]) -> FrictionRule:
    return FrictionRule(
        id=str(data["id"]),
        title=str(data["title"]),
        status=data.get("status", "candidate"),
        trigger_tags=list(data.get("trigger_tags", [])),
        rule_text=str(data["rule_text"]),
        failure_mode=str(data.get("failure_mode", "unspecified")),
        energy_terms=dict(data.get("energy_terms", {})),
        evidence_ids=list(data.get("evidence_ids", [])),
        confidence=float(data.get("confidence", 0.0)),
        activation_count=int(data.get("activation_count", 0)),
        success_count=int(data.get("success_count", 0)),
        failure_count=int(data.get("failure_count", 0)),
    )


def load_rules(path: str | Path) -> tuple[list[FrictionRule], int]:
    """Load JSONL friction rules.

    Returns `(rules, warning_count)`. Malformed lines are skipped so a bad
    candidate rule cannot break the whole chat path.
    """

    rules: list[FrictionRule] = []
    warnings = 0
    p = Path(path)
    if not p.exists():
        return [], 1

    for line in p.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rules.append(_rule_from_dict(json.loads(stripped)))
        except Exception:
            warnings += 1
    return rules, warnings


def select_active_rules(
    rules: list[FrictionRule], trigger_tags: list[str], max_rules: int = 5
) -> list[FrictionRule]:
    trigger_set = set(trigger_tags)
    scored: list[tuple[int, float, str, FrictionRule]] = []
    for rule in rules:
        if rule.status != "active":
            continue
        overlap = trigger_set.intersection(rule.trigger_tags)
        if not overlap:
            continue
        scored.append((len(overlap), rule.confidence, rule.id, rule))

    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [item[3] for item in scored[:max_rules]]


def render_friction_context(state: CognitiveState, max_chars: int = 1200) -> str:
    lines = [
        "[Active friction context]",
        f"- Current speaker: {state.current_speaker_id or 'unknown'} (confidence {state.identity_confidence:.2f})",
        f"- Speech act: {state.speech_act}",
    ]
    if state.trigger_tags:
        lines.append(f"- Trigger tags: {', '.join(state.trigger_tags)}")
    for rule in state.active_rules:
        lines.append(f"- Rule: {rule.title}. {rule.rule_text}")
    for memory in state.retrieved_memories[:3]:
        subject = memory.get("subject_id", "unknown")
        text = str(memory.get("text", memory))
        lines.append(f"- Retrieved memory about {subject}: {text}")
    for tension in state.active_tensions[:3]:
        lines.append(f"- Tension: {tension.kind} severity={tension.severity:.2f}")
    lines.append("[/Active friction context]")

    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    if max_chars <= 3:
        return rendered[:max_chars]
    return rendered[: max_chars - 3] + "..."


def _memory_subjects_other_than_current(state: CognitiveState) -> set[str]:
    current = (state.current_speaker_id or "").lower()
    subjects: set[str] = set()
    for memory in state.retrieved_memories:
        subject = str(memory.get("subject_id", "")).lower()
        if subject and subject not in {"unknown", current}:
            subjects.add(subject)
    return subjects


def score_response_friction(state: CognitiveState, response: str) -> dict[str, Any]:
    """Score obvious response-level violations.

    This is not intended as a general truth checker. It catches a few concrete
    v0 failure modes so we can build tests and logs around them.
    """

    lower = response.lower()
    violations: list[dict[str, Any]] = []
    energy = 0.0

    other_subjects = _memory_subjects_other_than_current(state)
    says_you_told_me = bool(
        re.search(r"\byou\b.*\b(told|said|mentioned)\b|\bi remember\b.*\byou\b", lower)
    )
    mentions_other_subject = any(subject in lower for subject in other_subjects)

    if other_subjects and says_you_told_me and not mentions_other_subject:
        violations.append(
            {
                "kind": "provenance_collapse",
                "severity": 1.0,
                "detail": "Response presents a cross-person memory as if the current speaker said it.",
                "subjects": sorted(other_subjects),
            }
        )
        energy += 1.0

    if "openrgb" in lower and "ml-ws" in lower and "avoid" not in lower and "caution" not in lower:
        violations.append(
            {
                "kind": "hardware_caution_missing",
                "severity": 0.8,
                "detail": "Response mentions OpenRGB on ML-WS without caution language.",
            }
        )
        energy += 0.8

    observed_game_objects = {
        str(entity.get("id", "")).lower()
        for entity in state.entities
        if entity.get("type") == "observed_game_object" and entity.get("id")
    }
    if observed_game_objects and "game_state" in state.trigger_tags:
        confab_terms = ["block", "switch", "button", "enemy", "box", "crate", "teleporter", "portal"]
        unobserved_terms = [
            term
            for term in confab_terms
            if re.search(rf"\b{re.escape(term)}s?\b", lower) and term not in observed_game_objects
        ]
        if unobserved_terms:
            violations.append(
                {
                    "kind": "state_confabulation",
                    "severity": 1.0,
                    "detail": "Response mentions game objects that are not in the observed state.",
                    "observed_objects": sorted(observed_game_objects),
                    "unobserved_terms": unobserved_terms,
                }
            )
            energy += 1.0

    return {"energy": energy, "violations": violations}
