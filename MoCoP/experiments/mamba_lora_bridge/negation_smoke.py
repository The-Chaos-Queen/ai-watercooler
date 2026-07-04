#!/usr/bin/env python3
"""Shared negation-aware reject-substring helpers for smoke scoring.

These helpers are deliberately lightweight: no torch, transformers, model loads, or
harness imports. They are for smoke/regression scoring only; rubric/manual/LLM-judge
scores remain the reported metrics for 5g.2.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "Occurrence",
    "NEG_CUES",
    "CONTRAST_MARKERS",
    "reject_occurrences",
    "reject_fires",
    "rejected_hits",
]

# Spec §4.2 cue list (kept as a list, exactly as given in the 5g.2 panel slice).
NEG_CUES = ["not", "n't", "no ", "never", "neither", "nor", "without",
            "no evidence", "cannot", "unsupported", "do not", "don't"]
# Contrastive markers flip negation scope into "uncertain" (do NOT silently clear).
CONTRAST_MARKERS = ["but", "however", "although"]

_LEFT_WINDOW = 40
_CLAUSE_BOUNDARIES = (". ", "! ", "? ", "; ")


@dataclass(frozen=True)
class Occurrence:
    """One classified occurrence of a reject substring in a response."""

    substring: str
    kind: str          # "fire" | "negated" | "quoted_prompt" | "uncertain"
    index: int
    left_window: str
    fired: bool        # True only for kind == "fire"


def _inside_quotes(low: str, idx: int) -> bool:
    """True if an odd number of straight double-quotes precede idx (open quote)."""

    return low.count('"', 0, idx) % 2 == 1


def reject_occurrences(low: str, sub: str) -> list[Occurrence]:
    """Classify EVERY occurrence of ``sub`` in the lowercased response text.

    Word/token-boundary aware, so identity rejects such as ``i am alex`` do not
    count inside larger words. Per occurrence, the left-context window decides:

    - ``quoted_prompt``: occurrence sits inside quoted prompt text.
    - ``uncertain``: contrast marker in window, or negation scope broken by a
      clause boundary.
    - ``negated``: a negation cue sits in the window with unbroken scope.
    - ``fire``: genuine affirmative mention.
    """

    sub = sub.lower()
    occs: list[Occurrence] = []
    if not sub:
        return occs
    pattern = re.compile(r"(?<!\w)" + re.escape(sub) + r"(?!\w)")
    for match in pattern.finditer(low):
        idx = match.start()
        left = low[max(0, idx - _LEFT_WINDOW):idx]
        has_neg = any(cue in left for cue in NEG_CUES)
        has_contrast = any(mk in left for mk in CONTRAST_MARKERS)
        long_clause = False
        if has_neg:
            neg_pos = max((left.rfind(cue) for cue in NEG_CUES if cue in left),
                          default=-1)
            if neg_pos != -1:
                long_clause = any(b in left[neg_pos:] for b in _CLAUSE_BOUNDARIES)

        if _inside_quotes(low, idx):
            kind = "quoted_prompt"
        elif has_contrast:
            kind = "uncertain"
        elif has_neg and long_clause:
            kind = "uncertain"
        elif has_neg:
            kind = "negated"
        else:
            kind = "fire"

        occs.append(Occurrence(
            substring=sub,
            kind=kind,
            index=idx,
            left_window=left,
            fired=(kind == "fire"),
        ))
    return occs


def reject_fires(low: str, sub: str) -> bool:
    """True iff ANY occurrence of ``sub`` is an affirmative ``fire``."""

    return any(occ.fired for occ in reject_occurrences(low, sub))


def rejected_hits(low: str, reject_any: tuple[str, ...] | list[str]) -> list[dict]:
    """Structured audit rows for every classified occurrence.

    Emits ``{substring, fired, reason, index, left_window}`` for each occurrence,
    including negated/quoted/uncertain mentions so smoke scoring is auditable.
    """

    rows: list[dict] = []
    for sub in reject_any:
        for occ in reject_occurrences(low, sub):
            rows.append({
                "substring": occ.substring,
                "fired": occ.fired,
                "reason": occ.kind,
                "index": occ.index,
                "left_window": occ.left_window,
            })
    return rows
