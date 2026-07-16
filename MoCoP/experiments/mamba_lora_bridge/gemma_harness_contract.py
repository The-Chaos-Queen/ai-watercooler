"""Pure output-boundary contract for isolated Gemma evaluation harnesses.

This module deliberately has no torch/transformers dependency.  It records the
first answer boundary without mutating or discarding the raw model output, and
provides a token-suffix matcher that a future explicitly invoked generation
adapter can use as a stopping criterion.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

# These are visible continuation headers observed in the historical Gemma-base
# bakeoff.  They are a generation-contract diagnostic, not a judgment on the
# underlying model or a general-purpose assistant policy.
DEFAULT_TEXT_BOUNDARIES: tuple[str, ...] = (
    "[Memory evidence]",
    "[Drift-gate",
    "Current test namespace:",
    "Question:",
    "Q:",
)


@dataclass(frozen=True)
class TextBoundaryMatch:
    """The earliest visible continuation header in a raw generation."""

    marker: str
    index: int


@dataclass(frozen=True)
class FinalizedAnswer:
    """Raw generation plus its first-answer scoring view.

    ``raw_text`` is deliberately retained exactly as supplied.  ``answer`` is
    a trimmed scoring projection only; it is never a replacement for raw
    evidence.
    """

    raw_text: str
    answer: str
    continuation_detected: bool
    boundary: TextBoundaryMatch | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "answer": self.answer,
            "continuation_detected": self.continuation_detected,
            "boundary": asdict(self.boundary) if self.boundary else None,
        }


@dataclass(frozen=True)
class TokenBoundaryMatch:
    """A token boundary that matches the suffix of a generated sequence."""

    marker: str
    token_ids: tuple[int, ...]


def _validate_markers(markers: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(markers)
    if not normalized:
        raise ValueError("at least one boundary marker is required")
    if any(not isinstance(marker, str) or not marker for marker in normalized):
        raise ValueError("boundary markers must be non-empty strings")
    return normalized


def _find_blank_line_header(raw_text: str, marker: str) -> int:
    """Return the first marker occurrence after an observed blank line.

    Historical bakeoff continuations began after ``\n\n``. A single newline can
    be legitimate quoted/structured answer text, so it is intentionally not a
    continuation boundary here. CRLF blank lines are accepted for captured
    Windows output.
    """

    search_from = 0
    while True:
        index = raw_text.find(marker, search_from)
        if index < 0:
            return -1
        if raw_text[:index].endswith(("\n\n", "\r\n\r\n")):
            return index
        search_from = index + 1


def find_text_boundary(
    raw_text: str,
    markers: Sequence[str] = DEFAULT_TEXT_BOUNDARIES,
) -> TextBoundaryMatch | None:
    """Find the earliest configured continuation header after a blank line.

    Inline mentions and single-newline headings remain part of the answer. This
    matches the observed archived bakeoff continuations. If multiple markers
    begin at the same character offset, prefer the longest marker. That yields
    deterministic receipts for overlapping markers.
    """

    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be a string")
    best: TextBoundaryMatch | None = None
    for marker in _validate_markers(markers):
        index = _find_blank_line_header(raw_text, marker)
        if index < 0:
            continue
        candidate = TextBoundaryMatch(marker=marker, index=index)
        if best is None or index < best.index or (
            index == best.index and len(marker) > len(best.marker)
        ):
            best = candidate
    return best


def finalize_answer(
    raw_text: str,
    markers: Sequence[str] = DEFAULT_TEXT_BOUNDARIES,
) -> FinalizedAnswer:
    """Return a first-answer scoring projection while preserving raw evidence."""

    boundary = find_text_boundary(raw_text, markers)
    if boundary is None:
        return FinalizedAnswer(
            raw_text=raw_text,
            answer=raw_text.strip(),
            continuation_detected=False,
            boundary=None,
        )
    return FinalizedAnswer(
        raw_text=raw_text,
        answer=raw_text[: boundary.index].strip(),
        continuation_detected=True,
        boundary=boundary,
    )


def marker_token_sequences(
    tokenizer: Any,
    markers: Sequence[str] = DEFAULT_TEXT_BOUNDARIES,
) -> dict[str, tuple[int, ...]]:
    """Encode continuation headers without special tokens for a stop adapter."""

    if not hasattr(tokenizer, "encode"):
        raise TypeError("tokenizer must expose encode(text, add_special_tokens=False)")
    sequences: dict[str, tuple[int, ...]] = {}
    for marker in _validate_markers(markers):
        encoded = tokenizer.encode(marker, add_special_tokens=False)
        token_ids = tuple(int(token) for token in encoded)
        if not token_ids:
            raise ValueError(f"marker tokenized to an empty sequence: {marker!r}")
        sequences[marker] = token_ids
    return sequences


class TokenSuffixMatcher:
    """Match a generated-token suffix against named boundary sequences.

    It intentionally knows nothing about tensor libraries. A future
    Transformers ``StoppingCriteria`` wrapper can convert its input IDs to
    ordinary integers and call ``match_suffix``. Token-suffix matching alone
    does not prove the text-level line-start rule used by ``find_text_boundary``;
    an adapter must make its newline/prompt-boundary contract explicit and
    record that decision in its receipt.
    """

    def __init__(self, boundaries: Mapping[str, Sequence[int]]):
        if not boundaries:
            raise ValueError("at least one token boundary is required")
        normalized: list[TokenBoundaryMatch] = []
        for marker, token_ids in boundaries.items():
            if not isinstance(marker, str) or not marker:
                raise ValueError("token-boundary markers must be non-empty strings")
            values = tuple(int(token) for token in token_ids)
            if not values:
                raise ValueError(f"token boundary is empty: {marker!r}")
            normalized.append(TokenBoundaryMatch(marker=marker, token_ids=values))
        self._boundaries = tuple(normalized)

    def match_suffix(self, token_ids: Sequence[int]) -> TokenBoundaryMatch | None:
        """Return the longest configured boundary matching the sequence tail."""

        observed = tuple(int(token) for token in token_ids)
        matches = [
            boundary
            for boundary in self._boundaries
            if len(observed) >= len(boundary.token_ids)
            and observed[-len(boundary.token_ids) :] == boundary.token_ids
        ]
        if not matches:
            return None
        # Stable input order resolves identical-length duplicates deterministically.
        return max(matches, key=lambda boundary: len(boundary.token_ids))
