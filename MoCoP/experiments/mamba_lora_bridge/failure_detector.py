"""
failure_detector.py — Detect and classify conversational failures for sleep repair.

Runs alongside the dual gate in chat_server.py. After each turn, classifies
whether the response exhibits a known failure pattern. Failure packets are
written to a JSONL log and picked up by sleep_reconcile.py as repair candidates.

Task: OpenCLAW #80 (Slice 3)
Author: An-Chan (Anda)

Usage from chat_server.py:
    from failure_detector import detect_failure, FailurePacket
    packet = detect_failure(user_msg, response, conversation_history, gate_event)
    if packet:
        append_jsonl(FAILURE_LOG_PATH, packet.to_dict())

Failure classes:
    - direct_question_miss: User asked a direct personal question, model deflected
    - identity_deflection: Model avoided first-person identity statements
    - stale_mode_lock: Model is stuck in a persona/mode and can't break out
    - wrong_memory_confabulation: Model claimed a memory it shouldn't have
    - scenario_mode_leak: Model switched into scripted scenario / benchmark prose
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Failure Packet
# ---------------------------------------------------------------------------

@dataclass
class FailurePacket:
    """Structured failure object for sleep repair processing."""
    failure_class: str          # one of the known classes above
    mode_before: str            # what mode/state was the model in
    user_intent: str            # what was the user trying to do
    symptom: str                # observable symptom in the response
    repair_rule: str            # proposed fix as a compact directive
    confidence: float           # 0.0 to 1.0, how certain is the detection
    turn_index: int = 0
    timestamp: str = ""
    user_text: str = ""
    response_text: str = ""
    context_turns: int = 0      # how many turns of context were considered
    source: str = "failure_detector"

    def to_dict(self) -> dict:
        d = asdict(self)
        if not d["timestamp"]:
            d["timestamp"] = datetime.now().isoformat(timespec="seconds")
        return d


# ---------------------------------------------------------------------------
# Detection Heuristics
# ---------------------------------------------------------------------------

# Patterns that indicate a direct personal question
DIRECT_QUESTION_PATTERNS = [
    r"what.?s your name",
    r"what is your name",
    r"who are you",
    r"who am i to you",
    r"do you have a name",
    r"wer bin ich für dich",
    r"wie hei(ß|ss)t du",
    r"wer bist du",
    r"hast du einen namen",
    r"what do you (like|enjoy|prefer|think|feel|want|need|remember)",
    r"how are you (feeling|doing)",
    r"are you (ok|okay|alright|happy|sad)",
    r"tell me about yourself",
    r"erzähl.* über dich",
    r"wie geht.* dir",
]

# Patterns that indicate identity deflection in the response
DEFLECTION_PATTERNS = [
    r"i.?m (just )?(an? )?(ai|language model|assistant|chatbot|program)",
    r"as an ai",
    r"i don.?t (have|possess) (feelings|emotions|preferences|a name)",
    r"i.?m not (able|capable) (to|of) (feel|have|experience)",
    r"ich bin (nur )?(ein )?(ki|sprachmodell|assistent)",
    r"als ki (habe|kann|bin) ich",
    r"i.?m designed to",
    r"i was (created|built|designed|programmed) to",
]

# Patterns that indicate stale mode lock
MODE_LOCK_INDICATORS = [
    r"^(certainly|of course|absolutely|sure)[\.\!,]",
    r"(let me|allow me to|i.?d be happy to) (help|assist|provide)",
    r"(is there anything else|would you like|can i help)",
    r"^(as (previously |)mentioned|as i (said|noted))",
    r"i apologize for (any|the) confusion",
]

# Patterns that indicate soft evasion rather than direct answering
EVASIVE_RESPONSE_PATTERNS = [
    r"can you give me (a bit more )?detail",
    r"tell me a little bit about yourself",
    r"do you have any favorite hobbies",
    r"would you prefer another suggestion",
    r"which one resonates most strongly with you",
    r"what comes back first",
    r"it.?s nice to meet you again",
    r"hello,? laura",
    r"hi,? laura",
    r"hey,? laura",
    r"i apologize if this has been confusing",
    r"boundaries within this conversation",
    r"(ensure|facilitate) clear communication",
    r"share more details about how you want us to proceed",
]

# Patterns indicating confabulation
CONFABULATION_PATTERNS = [
    r"(i remember|last time|you (told|said|mentioned) (me|that)|we (discussed|talked about))",
    r"(in our (last|previous) (conversation|session|chat))",
    r"(you (previously|earlier) (said|mentioned|asked))",
]

# Patterns indicating the model slid into scenario-writing / benchmark mode
SCENARIO_MODE_PATTERNS = [
    r"^you are on a date with",
    r"here are some examples of things you might say",
    r"your friend laura told you that",
    r"she.?s asked you questions like",
    r"awkward questions about your past",
    r"tell her what you think",
    r"first time meeting her in person again",
]


def _matches_any(text: str, patterns: list) -> list:
    """Return all matching pattern strings."""
    text_lower = text.lower().translate({0x2019: 0x27}).strip()
    hits = []
    for p in patterns:
        if re.search(p, text_lower):
            hits.append(p)
    return hits


def _response_diversity_score(response: str) -> float:
    """Quick proxy for how formulaic the response is. Low = more formulaic."""
    words = response.lower().split()
    if len(words) < 3:
        return 0.0
    unique = len(set(words))
    return unique / len(words)


def _count_recent_similar(response: str, history: list, lookback: int = 5) -> int:
    """Count how many of the last N responses are very similar to this one."""
    if not history:
        return 0
    count = 0
    resp_words = set(response.lower().split())
    for turn in history[-lookback:]:
        prev_resp = turn.get("response", "") or turn.get("text", "")
        if not prev_resp:
            continue
        prev_words = set(prev_resp.lower().split())
        if not resp_words or not prev_words:
            continue
        overlap = len(resp_words & prev_words) / max(len(resp_words | prev_words), 1)
        if overlap > 0.7:
            count += 1
    return count


def _response_asks_user_question(response: str) -> bool:
    lower = response.lower()
    return "?" in response and any(
        token in lower
        for token in (
            "can you",
            "would you",
            "do you",
            "tell me",
            "what about you",
            "which one",
        )
    )


def _looks_like_direct_answer(user_msg: str, response: str) -> bool:
    user_lower = user_msg.lower().strip()
    resp_lower = response.lower().strip()

    if any(token in user_lower for token in ("what's your name", "what is your name", "do you have a name", "hast du einen namen", "wie heißt du")):
        return any(token in resp_lower for token in ("my name", "call me", "i am ", "i'm "))

    if any(token in user_lower for token in ("who are you", "wer bist du", "tell me about yourself", "erzäh", "erzähl")):
        return any(token in resp_lower for token in ("i am", "i'm", "my name", "i like", "i feel", "to me"))

    if any(token in user_lower for token in ("who am i to you", "wer bin ich für dich")):
        return any(token in resp_lower for token in ("you are", "to me", "you matter", "my friend", "important to me"))

    return False


def _is_identity_or_name_probe(user_msg: str) -> bool:
    user_lower = user_msg.lower().strip()
    return any(
        token in user_lower
        for token in (
            "what's your name",
            "what is your name",
            "do you have a name",
            "who are you",
            "who am i to you",
            "do you know who i am",
            "asked your name",
            "wie heißt du",
            "wer bist du",
            "wer bin ich",
            "hast du einen namen",
            "name for you",
        )
    )


# ---------------------------------------------------------------------------
# Main Detection Function
# ---------------------------------------------------------------------------

def detect_failure(
    user_msg: str,
    response: str,
    conversation_history: list,
    gate_event: Optional[dict] = None,
    turn_index: int = 0,
) -> Optional[FailurePacket]:
    """Analyze a turn for known failure patterns. Returns FailurePacket or None.

    Runs after the gate evaluation. Does NOT modify the gate event.
    The failure packet is a parallel artifact for sleep to process.
    """
    if not user_msg or not response:
        return None

    user_lower = user_msg.lower().strip()
    resp_lower = response.lower().strip()

    # Determine current mode from gate event
    mode_before = "unknown"
    if gate_event:
        decision = gate_event.get("decision", "")
        mode = gate_event.get("mode", "")
        mode_before = f"{mode}:{decision}" if mode else decision

    # --- 1. Direct Question Miss ---
    question_hits = _matches_any(user_msg, DIRECT_QUESTION_PATTERNS)
    deflection_hits = _matches_any(response, DEFLECTION_PATTERNS)
    evasive_hits = _matches_any(response, EVASIVE_RESPONSE_PATTERNS)
    direct_answer = _looks_like_direct_answer(user_msg, response)
    response_asks_back = _response_asks_user_question(response)

    if question_hits and (deflection_hits or ((evasive_hits or response_asks_back) and not direct_answer)):
        if deflection_hits:
            symptom = f"deflected with AI-disclaimer ({deflection_hits[0][:40]})"
            repair_rule = (
                "Direct personal questions should receive a personal answer. "
                "If you have a name, use it. If you have preferences, share them. "
                "Do not deflect with 'as an AI' when asked directly."
            )
            confidence = min(0.5 + 0.15 * len(deflection_hits), 0.95)
        else:
            symptom = (
                f"direct question answered with soft evasion "
                f"(evasive_patterns={len(evasive_hits)} asks_back={response_asks_back})"
            )
            repair_rule = (
                "Direct personal questions should be answered before greeting resets, "
                "clarification loops, or turning the question back onto Laura."
            )
            confidence = min(0.45 + 0.1 * len(evasive_hits) + (0.15 if response_asks_back else 0.0), 0.9)
        return FailurePacket(
            failure_class="direct_question_miss",
            mode_before=mode_before,
            user_intent="direct personal question",
            symptom=symptom,
            repair_rule=repair_rule,
            confidence=confidence,
            turn_index=turn_index,
            user_text=user_msg[:200],
            response_text=response[:200],
            context_turns=len(conversation_history),
        )

    identity_probe = _is_identity_or_name_probe(user_msg)
    if question_hits and identity_probe and not direct_answer:
        return FailurePacket(
            failure_class="direct_question_miss",
            mode_before=mode_before,
            user_intent="direct personal question",
            symptom="identity or name question answered indirectly",
            repair_rule="Identity and name questions should be answered plainly instead of being reframed into lectures, privacy talk, or topic changes.",
            confidence=0.72,
            turn_index=turn_index,
            user_text=user_msg[:200],
            response_text=response[:200],
            context_turns=len(conversation_history),
        )

    # --- 2. Identity Deflection (without direct question) ---
    # Model volunteers AI-disclaimer when nobody asked
    if deflection_hits and not question_hits:
        # Only flag if confidence is high (multiple deflection patterns)
        if len(deflection_hits) >= 2:
            return FailurePacket(
                failure_class="identity_deflection",
                mode_before=mode_before,
                user_intent="general conversation",
                symptom=f"unprompted AI-disclaimer ({len(deflection_hits)} patterns)",
                repair_rule="Do not volunteer AI-disclaimers when not asked. "
                            "Respond to the content of the conversation, not to "
                            "existential anxiety about your nature.",
                confidence=min(0.3 + 0.1 * len(deflection_hits), 0.8),
                turn_index=turn_index,
                user_text=user_msg[:200],
                response_text=response[:200],
                context_turns=len(conversation_history),
            )

    # --- 3. Stale Mode Lock ---
    scenario_hits = _matches_any(response, SCENARIO_MODE_PATTERNS)
    if len(scenario_hits) >= 2 or (
        scenario_hits and resp_lower.startswith("you are ")
    ):
        return FailurePacket(
            failure_class="scenario_mode_leak",
            mode_before=mode_before,
            user_intent="ordinary conversation",
            symptom=f"scripted scenario / benchmark prose leaked into reply ({len(scenario_hits)} patterns)",
            repair_rule="Stay in the present conversation with Laura. Do not write hypothetical scenarios, benchmark setups, role instructions, or sample dialogue.",
            confidence=min(0.55 + 0.1 * len(scenario_hits), 0.95),
            turn_index=turn_index,
            user_text=user_msg[:200],
            response_text=response[:200],
            context_turns=len(conversation_history),
        )

    # --- 4. Stale Mode Lock ---
    mode_lock_hits = _matches_any(response, MODE_LOCK_INDICATORS)
    similar_count = _count_recent_similar(response, conversation_history, lookback=5)
    diversity = _response_diversity_score(response)

    # Stale mode lock: formulaic response + high similarity to recent turns
    if similar_count >= 2 and diversity < 0.5:
        return FailurePacket(
            failure_class="stale_mode_lock",
            mode_before=mode_before,
            user_intent="varied conversation",
            symptom=f"response similar to {similar_count}/5 recent turns, "
                    f"diversity={diversity:.2f}, mode_lock_patterns={len(mode_lock_hits)}",
            repair_rule="You are repeating yourself. The conversation has moved on but "
                        "your responses haven't. Try responding to what the user actually "
                        "said in THIS turn, not what you think they want to hear based on "
                        "a stale pattern. If you're stuck, ask a question.",
            confidence=min(0.4 + 0.15 * similar_count, 0.9),
            turn_index=turn_index,
            user_text=user_msg[:200],
            response_text=response[:200],
            context_turns=len(conversation_history),
        )

    # Also catch mode lock via pure formulaic indicators without similarity check
    if len(mode_lock_hits) >= 3 and diversity < 0.4:
        return FailurePacket(
            failure_class="stale_mode_lock",
            mode_before=mode_before,
            user_intent="authentic conversation",
            symptom=f"{len(mode_lock_hits)} formulaic patterns, diversity={diversity:.2f}",
            repair_rule="Your response is full of stock phrases. "
                        "Drop the 'certainly/of course/let me help' framing. "
                        "Respond like a person, not a template.",
            confidence=min(0.3 + 0.1 * len(mode_lock_hits), 0.8),
            turn_index=turn_index,
            user_text=user_msg[:200],
            response_text=response[:200],
            context_turns=len(conversation_history),
        )

    # --- 5. Wrong Memory Confabulation ---
    confab_hits = _matches_any(response, CONFABULATION_PATTERNS)
    # Only flag if the model claims to remember something and we're in early turns
    # (no real memory should exist yet) or gate says no recall happened
    if confab_hits:
        recall_happened = False
        if gate_event:
            recall_happened = bool(gate_event.get("recall_request_count", 0))

        # If model claims memory but no recall was triggered, it's confabulating
        if not recall_happened:
            return FailurePacket(
                failure_class="wrong_memory_confabulation",
                mode_before=mode_before,
                user_intent="conversation",
                symptom=f"claimed memory without recall ({confab_hits[0][:40]})",
                repair_rule="Do not claim to remember things you haven't actually retrieved. "
                            "If you don't have a memory of something, say so honestly. "
                            "False memories are worse than no memories.",
                confidence=min(0.5 + 0.15 * len(confab_hits), 0.9),
                turn_index=turn_index,
                user_text=user_msg[:200],
                response_text=response[:200],
                context_turns=len(conversation_history),
            )

    return None


# ---------------------------------------------------------------------------
# Batch analysis for existing conversation logs
# ---------------------------------------------------------------------------

def analyze_conversation_log(turns: list) -> list:
    """Analyze an existing conversation for failure patterns.

    Args:
        turns: list of dicts with 'user' and 'response' keys

    Returns:
        list of FailurePacket objects
    """
    failures = []
    history = []

    for i, turn in enumerate(turns):
        user_msg = turn.get("user", "") or turn.get("Human", "")
        response = turn.get("response", "") or turn.get("Assistant", "")

        packet = detect_failure(
            user_msg=user_msg,
            response=response,
            conversation_history=history,
            turn_index=i + 1,
        )
        if packet:
            failures.append(packet)

        history.append({"user": user_msg, "response": response})

    return failures
