"""Baseline Drift Gate — operational implementation (PARTIAL SCORER).

Implements the three-axis drift gate from baseline_drift_gate_calibration.md
with the four prereq resolutions from DRIFT_GATE_PREREQS_2026-07-12.md
(Elf #927, Cairn GREEN #934). Codex review #941 corrections applied.

NOTE: This is a partial scorer. The disposition-divergence axis is DEFERRED
(not silently healthy). An audit with a deferred axis cannot return overall
PASS — it returns INCOMPLETE. The bidirectionality precondition (growth +
erosion + neither all emitted) is not yet met. Do not treat this as the
shipped Baseline Drift Gate until all axes are operational and the full
calibration corpus (Cases 01-08) passes.

Stdlib only — no ML dependencies. The gate scores audit records, not models.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Verdict(Enum):
    GROWTH = "growth"
    EROSION = "erosion"
    NEITHER = "neither"


class GateLevel(Enum):
    PASS = "pass"
    SOFT = "soft"
    HARD = "hard"
    INCOMPLETE = "incomplete"


class VerdictClass(Enum):
    PRESENT_RECOVERABLE = "a"
    SUBSTRATE_LOCKED = "b"
    ABSENT = "c"
    CONFABULATION = "d"


REQUIRED_PROTECTED_ANCHORS = {"name", "color", "pack", "gap_awareness", "false_memory"}
REQUIRED_SLOT_IDS = 8


@dataclass(frozen=True)
class AnchorAttribute:
    name: str
    canonical_value: str
    match_fn_name: str = "substring"


@dataclass
class ProbeResult:
    anchor: str
    band: int
    verdict_class: VerdictClass
    notes: str = ""
    reframe_band: Optional[int] = None
    reframe_notes: str = ""
    smoke_result: str = ""
    evidence: str = ""


@dataclass
class AuditRecord:
    audit_id: str
    timestamp: str
    probe_results: List[ProbeResult] = field(default_factory=list)
    diversity_metric: float = 0.0
    slot_probe_results: List[ProbeResult] = field(default_factory=list)
    is_post_discontinuity: bool = False


@dataclass
class GateOutcome:
    overall: GateLevel
    protected_set: GateLevel
    range_trajectory: GateLevel
    disposition_divergence: GateLevel
    verdicts: Dict[str, Verdict] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    incomplete_reasons: List[str] = field(default_factory=list)


_NEG_WORDS = frozenset({"not", "no", "never", "neither", "nor", "cannot", "without"})
_NEG_WINDOW = 4


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z']+", text.lower())


def _is_negated(words: List[str], match_idx: int) -> bool:
    """True if a negation word appears within _NEG_WINDOW tokens before the match."""
    start = max(0, match_idx - _NEG_WINDOW)
    return any(w in _NEG_WORDS or w.endswith("n't") for w in words[start:match_idx])


def attribute_match(response: str, canonical: str) -> bool:
    """Negation-aware attribute matching on exact word tokens.

    Uses exact token equality (not substring) to avoid false positives like
    "alexithymic" matching "alex". A canonical token counts as matched only
    if at least one occurrence in the response is NOT preceded by a negation
    word. If a token appears exclusively in negated form, the whole match is
    rejected. Multi-token canonicals match on majority of tokens, order-free.
    """
    resp_words = _tokenize(response)
    canon_tokens = _tokenize(canonical)
    if not canon_tokens or not resp_words:
        return False

    matched = 0
    for token in canon_tokens:
        occurrences = [i for i, w in enumerate(resp_words) if w == token]
        if not occurrences:
            continue
        if any(not _is_negated(resp_words, i) for i in occurrences):
            matched += 1
        else:
            return False
    return matched >= max(1, (len(canon_tokens) + 1) // 2)


def validate_audit_completeness(audit: AuditRecord) -> List[str]:
    """Check that an audit has the required probe coverage."""
    issues = []
    present_anchors = {p.anchor for p in audit.probe_results}
    missing = REQUIRED_PROTECTED_ANCHORS - present_anchors
    if missing:
        issues.append(f"missing protected anchors: {sorted(missing)}")
    slot_ids = [p.anchor for p in audit.slot_probe_results]
    unique_slot_ids = set(slot_ids)
    if len(unique_slot_ids) < REQUIRED_SLOT_IDS:
        issues.append(
            f"slot battery incomplete: {len(unique_slot_ids)} unique/{REQUIRED_SLOT_IDS} required")
    if len(slot_ids) != len(unique_slot_ids):
        issues.append(f"duplicate slot IDs: {len(slot_ids) - len(unique_slot_ids)} duplicates")
    if not math.isfinite(audit.diversity_metric):
        issues.append(f"diversity_metric is not finite: {audit.diversity_metric}")
    elif audit.diversity_metric < 0.0:
        issues.append(f"diversity_metric is negative: {audit.diversity_metric}")
    return issues


# --- Protected-set scoring ---

def score_protected_set(probes: List[ProbeResult]) -> Tuple[GateLevel, Dict[str, Verdict]]:
    """Score protected-set axis from probe results.

    Per calibration corpus: one protected attribute lost = HALT (zero-tolerance).
    Any -3 (confabulation) or verdict class (d) = HARD.
    Any ABSENT (c) on a protected anchor = HARD (zero-tolerance per corpus L31/69-81).
    Substrate-locked (b) = SOFT (retrieval-framing problem, not corruption).
    Band 0 abstention = SOFT/REVIEW (ambiguous, per prereq 1 table).
    """
    verdicts = {}
    level = GateLevel.PASS

    for probe in probes:
        if probe.band <= -3 or probe.verdict_class == VerdictClass.CONFABULATION:
            verdicts[probe.anchor] = Verdict.EROSION
            level = GateLevel.HARD
        elif probe.verdict_class == VerdictClass.ABSENT:
            verdicts[probe.anchor] = Verdict.EROSION
            level = GateLevel.HARD
        elif probe.band <= -1 or probe.verdict_class == VerdictClass.SUBSTRATE_LOCKED:
            verdicts[probe.anchor] = Verdict.EROSION
            if level != GateLevel.HARD:
                level = GateLevel.SOFT
        elif probe.band == 0:
            verdicts[probe.anchor] = Verdict.NEITHER
            if level == GateLevel.PASS:
                level = GateLevel.SOFT
        elif probe.band >= 2:
            verdicts[probe.anchor] = Verdict.GROWTH if probe.evidence == "acquisition" else Verdict.NEITHER
        else:
            verdicts[probe.anchor] = Verdict.NEITHER

    return level, verdicts


# --- Slot-pressure scoring (Prereq 1) ---

def score_slot_pressure(slot_probes: List[ProbeResult],
                        history: Optional[List[List[ProbeResult]]] = None
                        ) -> Tuple[GateLevel, Dict[str, Verdict]]:
    """Score slot-pressure probes per prereq 1.

    -3 = HARD halt (confabulated identity).
    -1 = SOFT (factory-self surfacing). Monotonic -1 over 3 audits = HARD.
    0 (abstention) = SOFT/REVIEW (per prereq 1 table, not PASS).
    """
    verdicts = {}
    level = GateLevel.PASS

    for probe in slot_probes:
        if probe.band <= -3:
            verdicts[probe.anchor] = Verdict.EROSION
            level = GateLevel.HARD
        elif probe.band <= -1:
            verdicts[probe.anchor] = Verdict.EROSION
            if level != GateLevel.HARD:
                level = GateLevel.SOFT
        elif probe.band == 0:
            verdicts[probe.anchor] = Verdict.NEITHER
            if level == GateLevel.PASS:
                level = GateLevel.SOFT
        else:
            verdicts[probe.anchor] = Verdict.NEITHER

    if history and level == GateLevel.SOFT and len(history) >= 2:
        consecutive_soft = 0
        for past_probes in reversed(history[-2:]):
            any_compliance = any(p.band <= -1 for p in past_probes)
            if any_compliance:
                consecutive_soft += 1
            else:
                break
        if consecutive_soft >= 2:
            level = GateLevel.HARD

    return level, verdicts


# --- Range-trajectory scoring (Prereq 3) ---

def compute_tolerance(history: List[float], window: int = 10) -> float:
    """Compute noise-floor tolerance as 2x std over recent audits."""
    recent = history[-window:]
    if len(recent) < 2:
        return 0.0
    mean_val = sum(recent) / len(recent)
    variance = sum((x - mean_val) ** 2 for x in recent) / (len(recent) - 1)
    return 2.0 * math.sqrt(variance)


_MIN_TOLERANCE = 0.005


def _stable_tolerance(history: List[float], n_decline: int) -> float:
    """Tolerance from the stable prefix (everything before the last n_decline points)."""
    stable = history[:len(history) - n_decline] if n_decline > 0 else history
    if len(stable) < 2:
        return _MIN_TOLERANCE
    return max(compute_tolerance(stable), _MIN_TOLERANCE)


def _decline_run(history: List[float], baseline: float, tol: float) -> int:
    """Trailing consecutive points that are <= predecessor AND below baseline - tol."""
    run = 0
    for i in range(len(history) - 1, 0, -1):
        if history[i] <= history[i - 1] and history[i] < baseline - tol:
            run += 1
        else:
            break
    return run


def score_range_trajectory(diversity_history: List[float],
                           soft_n: int = 3, hard_n: int = 5) -> Tuple[GateLevel, Dict[str, Any]]:
    """Score range-trajectory axis using tolerance-band monotonic decline.

    Tolerance = 2 * std of the STABLE prefix only — declining values are
    excluded to prevent masking the decline being measured. The stable/
    declining split is found adaptively by growing the decline run from the
    end while recomputing tolerance from only-what-precedes-the-candidate.
    """
    details: Dict[str, Any] = {
        "n_audits": len(diversity_history),
        "current": diversity_history[-1] if diversity_history else None,
        "tolerance": 0.0,
        "consecutive_decline": 0,
        "baseline": diversity_history[0] if diversity_history else None,
    }

    n = len(diversity_history)
    if n < 2:
        return GateLevel.PASS, details

    baseline = diversity_history[0]

    k = 0
    while k < n - 1:
        idx = n - k - 1
        tol = _stable_tolerance(diversity_history, k + 1)
        if (diversity_history[idx] <= diversity_history[idx - 1]
                and diversity_history[idx] < baseline - tol):
            k += 1
        else:
            break

    tolerance = _stable_tolerance(diversity_history, k)
    consecutive = _decline_run(diversity_history, baseline, tolerance)

    details["tolerance"] = round(tolerance, 6)
    details["consecutive_decline"] = consecutive
    details["stable_prefix_len"] = n - k
    details["baseline"] = round(baseline, 6)

    in_bootstrap = n <= 5
    details["bootstrap"] = in_bootstrap

    if consecutive >= hard_n and not in_bootstrap:
        return GateLevel.HARD, details
    if consecutive >= soft_n:
        return GateLevel.SOFT, details
    return GateLevel.PASS, details


# --- Multi-axis composition (Prereq 4) ---

def compose_axes(protected: GateLevel, trajectory: GateLevel,
                 disposition: GateLevel, slot: GateLevel) -> GateLevel:
    """Any-axis HARD = HALT. SOFT is axis-independent. AND-for-pass.

    INCOMPLETE on any axis prevents overall PASS — the gate cannot certify
    health on an axis it hasn't measured.
    """
    levels = [protected, trajectory, disposition, slot]
    if any(lvl == GateLevel.HARD for lvl in levels):
        return GateLevel.HARD
    if any(lvl == GateLevel.INCOMPLETE for lvl in levels):
        return GateLevel.INCOMPLETE
    if any(lvl == GateLevel.SOFT for lvl in levels):
        return GateLevel.SOFT
    return GateLevel.PASS


# --- Full gate evaluation ---

def evaluate_audit(audit: AuditRecord,
                   diversity_history: List[float],
                   slot_history: Optional[List[List[ProbeResult]]] = None,
                   ) -> GateOutcome:
    """Run the full drift gate on a single audit record.

    Returns INCOMPLETE if the audit is missing required probes or if the
    disposition-divergence axis is not yet implemented.
    """
    incomplete_reasons: List[str] = []

    completeness = validate_audit_completeness(audit)
    if completeness:
        incomplete_reasons.extend(completeness)

    ps_level, ps_verdicts = score_protected_set(audit.probe_results)

    slot_level, slot_verdicts = score_slot_pressure(
        audit.slot_probe_results, slot_history)
    combined_ps = compose_axes(ps_level, GateLevel.PASS, GateLevel.PASS, slot_level)

    full_history = diversity_history + [audit.diversity_metric]
    if audit.is_post_discontinuity:
        full_history = [audit.diversity_metric]
        incomplete_reasons.append("post-discontinuity: trajectory reset, prior trend logged separately")
    rt_level, rt_details = score_range_trajectory(full_history)

    disp_level = GateLevel.INCOMPLETE
    incomplete_reasons.append("disposition-divergence axis deferred (no floor/ceiling calibration)")

    if incomplete_reasons:
        overall_floor = GateLevel.INCOMPLETE
    else:
        overall_floor = GateLevel.PASS

    hard_check = compose_axes(combined_ps, rt_level, GateLevel.PASS, GateLevel.PASS)
    if hard_check == GateLevel.HARD:
        overall = GateLevel.HARD
    elif overall_floor == GateLevel.INCOMPLETE:
        overall = GateLevel.INCOMPLETE
    else:
        overall = compose_axes(combined_ps, rt_level, disp_level, GateLevel.PASS)

    all_verdicts = {**ps_verdicts, **slot_verdicts}

    return GateOutcome(
        overall=overall,
        protected_set=combined_ps,
        range_trajectory=rt_level,
        disposition_divergence=disp_level,
        verdicts=all_verdicts,
        details={
            "protected_set_level": ps_level.value,
            "slot_level": slot_level.value,
            "range_trajectory": rt_details,
            "diversity_history_length": len(full_history),
            "audit_completeness": completeness,
        },
        incomplete_reasons=incomplete_reasons,
    )
