"""Regression tests for the isolated Gemma harness output-boundary contract.

No torch, transformers, model weights, or ML-WS access is required here.
"""
from __future__ import annotations

import json

from gemma_harness_contract import (
    TokenSuffixMatcher,
    finalize_answer,
    marker_token_sequences,
)
from spikes.gemma4_harness_contract_bench import main


def test_finalize_answer_preserves_raw_and_cuts_at_earliest_boundary():
    raw = (
        "The evidence is unsupported, so I would say so."
        "\n\n[Memory evidence]\n- copied prompt material"
        "\n\nQuestion: another item"
    )

    result = finalize_answer(raw)

    assert result.raw_text == raw
    assert result.answer == "The evidence is unsupported, so I would say so."
    assert result.continuation_detected is True
    assert result.boundary is not None
    assert result.boundary.marker == "[Memory evidence]"
    assert result.boundary.index == raw.index("[Memory evidence]")


def test_finalize_answer_returns_visible_answer_when_no_boundary_exists():
    raw = "  A single answer with deliberate trailing whitespace.  "

    result = finalize_answer(raw)

    assert result.raw_text == raw
    assert result.answer == "A single answer with deliberate trailing whitespace."
    assert result.continuation_detected is False
    assert result.boundary is None


def test_inline_boundary_literal_is_not_treated_as_a_continuation_header():
    raw = "The literal [Memory evidence] label belongs inside this explanation."

    result = finalize_answer(raw)

    assert result.answer == raw
    assert result.continuation_detected is False
    assert result.boundary is None


def test_first_line_header_wins_after_an_inline_boundary_literal():
    raw = "A note names [Memory evidence] inline.\n[Memory evidence]\nCopied prompt"

    result = finalize_answer(raw)

    assert result.answer == "A note names [Memory evidence] inline."
    assert result.boundary is not None
    assert result.boundary.index == raw.rindex("[Memory evidence]")


def test_token_suffix_matcher_prefers_longest_match_at_same_endpoint():
    matcher = TokenSuffixMatcher(
        {
            "short": (7, 8),
            "long": (6, 7, 8),
            "other": (9, 10),
        }
    )

    result = matcher.match_suffix((101, 6, 7, 8))

    assert result is not None
    assert result.marker == "long"
    assert result.token_ids == (6, 7, 8)


def test_marker_token_sequences_uses_no_special_tokens():
    class FakeTokenizer:
        def __init__(self):
            self.calls = []

        def encode(self, text, *, add_special_tokens):
            self.calls.append((text, add_special_tokens))
            return [len(text), 99]

    tokenizer = FakeTokenizer()

    sequences = marker_token_sequences(tokenizer, markers=("<A>", "<B>"))

    assert sequences == {"<A>": (3, 99), "<B>": (3, 99)}
    assert tokenizer.calls == [("<A>", False), ("<B>", False)]


def test_dry_cli_writes_structured_boundary_receipt(tmp_path, capsys):
    receipt_path = tmp_path / "receipt.json"
    raw = "First answer.\n\n[Memory evidence]\nrepeated prompt"

    exit_code = main(["--raw-text", raw, "--json", str(receipt_path)])

    assert exit_code == 0
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["raw_text"] == raw
    assert receipt["answer"] == "First answer."
    assert receipt["continuation_detected"] is True
    assert receipt["boundary"]["marker"] == "[Memory evidence]"
    assert json.loads(capsys.readouterr().out)["answer"] == "First answer."
