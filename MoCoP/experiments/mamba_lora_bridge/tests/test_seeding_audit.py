"""Tests for seeding_audit.py — organic memory seeding audit helper."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from seeding_audit import (
    parse_organic_source_type,
    source_priority,
    build_rows,
    build_audit,
    compute_relational_diversity,
    detect_confabulation_candidates,
    format_text,
    format_watercooler,
    format_json,
    MemoryRow,
)


def _make_point(pid, content, source_type="", **extra_meta):
    meta = {"source_type": source_type, "content": content, **extra_meta}
    return {"id": pid, "payload": {"content": content, "metadata": meta}}


class TestParseOrganicSourceType:
    def test_first_meeting_laura(self):
        cat, wolf = parse_organic_source_type("organic_first_meeting_laura_memory")
        assert cat == "first_meeting"
        assert wolf == "laura"

    def test_correction_techno_monk(self):
        cat, wolf = parse_organic_source_type("organic_correction_techno_monk_memory")
        assert cat == "correction"
        assert wolf == "techno_monk"

    def test_shared_humor_elf(self):
        cat, wolf = parse_organic_source_type("organic_shared_humor_elf_memory")
        assert cat == "shared_humor"
        assert wolf == "elf"

    def test_fond_moment_purple(self):
        cat, wolf = parse_organic_source_type("organic_fond_moment_purple_memory")
        assert cat == "fond_moment"
        assert wolf == "purple"

    def test_conflict_isegrim(self):
        cat, wolf = parse_organic_source_type("organic_conflict_isegrim_memory")
        assert cat == "conflict"
        assert wolf == "isegrim"

    def test_factual_exchange_cairn(self):
        cat, wolf = parse_organic_source_type("organic_factual_exchange_cairn_memory")
        assert cat == "factual_exchange"
        assert wolf == "cairn"

    def test_not_organic(self):
        assert parse_organic_source_type("autobiographical_memory") == (None, None)

    def test_empty(self):
        assert parse_organic_source_type("") == (None, None)

    def test_steve_gate(self):
        assert parse_organic_source_type("steve_gate_event") == (None, None)

    def test_case_insensitive(self):
        cat, wolf = parse_organic_source_type("Organic_First_Meeting_Laura_Memory")
        assert cat == "first_meeting"
        assert wolf == "laura"

    def test_category_only_no_wolf(self):
        cat, wolf = parse_organic_source_type("organic_correction_memory")
        assert cat == "correction"
        assert wolf == ""


class TestSourcePriority:
    def test_organic_highest(self):
        assert source_priority("organic_first_meeting_laura_memory") == 5

    def test_autobiographical(self):
        assert source_priority("autobiographical_memory") == 4

    def test_steve_gate_lowest(self):
        assert source_priority("steve_gate_event") == 0

    def test_unknown_default(self):
        assert source_priority("something_else") == 1


class TestBuildRows:
    def test_organic_parsed(self):
        points = [_make_point("p1", "Hello", "organic_first_meeting_laura_memory")]
        rows = build_rows(points)
        assert len(rows) == 1
        assert rows[0].is_organic
        assert rows[0].category == "first_meeting"
        assert rows[0].seeding_wolf == "laura"

    def test_non_organic(self):
        points = [_make_point("p2", "Data", "autobiographical_memory")]
        rows = build_rows(points)
        assert not rows[0].is_organic
        assert rows[0].category == ""


class TestBuildAudit:
    def _sample_points(self):
        return [
            _make_point("1", "Hi I'm Laura", "organic_first_meeting_laura_memory"),
            _make_point("2", "That's funny", "organic_shared_humor_laura_memory"),
            _make_point("3", "Nice moment", "organic_fond_moment_monk_memory"),
            _make_point("4", "Wrong detail", "organic_correction_monk_memory"),
            _make_point("5", "A fact", "organic_factual_exchange_laura_memory"),
            _make_point("6", "Gate event", "steve_gate_event"),
            _make_point("7", "Old memory", "autobiographical_memory",
                        evidence_confidence=0.3),
        ]

    def test_counts(self):
        report = build_audit("test_col", self._sample_points())
        assert report.total_points == 7
        assert report.organic_count == 5
        assert report.non_organic_count == 2

    def test_category_coverage(self):
        report = build_audit("test_col", self._sample_points())
        assert report.categories_covered >= 4
        assert "conflict" in report.categories_missing

    def test_wolf_breakdown(self):
        report = build_audit("test_col", self._sample_points())
        assert report.by_wolf["laura"] == 3
        assert report.by_wolf["monk"] == 2

    def test_relational_diversity(self):
        report = build_audit("test_col", self._sample_points())
        assert 0.0 < report.relational_diversity_score < 1.0


class TestRelationalDiversity:
    def test_perfect_coverage(self):
        by_wc = {"wolf_a": {cat: 1 for cat in ["first_meeting", "shared_humor",
                 "fond_moment", "conflict", "frustration", "factual_exchange", "correction"]}}
        assert compute_relational_diversity(by_wc) == 1.0

    def test_empty(self):
        assert compute_relational_diversity({}) == 0.0

    def test_partial(self):
        by_wc = {"wolf_a": {"first_meeting": 1, "correction": 1}}
        score = compute_relational_diversity(by_wc)
        assert 0.0 < score < 1.0


class TestConfabulation:
    def test_low_confidence_non_organic_flagged(self):
        rows = [MemoryRow(point_id="x", content="claim", source_type="macro_memory",
                          evidence_confidence=0.2)]
        candidates = detect_confabulation_candidates(rows)
        assert len(candidates) == 1

    def test_organic_not_flagged(self):
        rows = [MemoryRow(point_id="x", content="real", source_type="organic_first_meeting_laura_memory",
                          is_organic=True, evidence_confidence=0.1)]
        candidates = detect_confabulation_candidates(rows)
        assert len(candidates) == 0

    def test_gate_events_skipped(self):
        rows = [MemoryRow(point_id="x", content="gate", source_type="steve_gate_event",
                          evidence_confidence=0.0)]
        candidates = detect_confabulation_candidates(rows)
        assert len(candidates) == 0


class TestFormatters:
    def _sample_report(self):
        points = [
            _make_point("1", "Hi", "organic_first_meeting_laura_memory"),
            _make_point("2", "Joke", "organic_shared_humor_monk_memory"),
        ]
        return build_audit("test_col", points)

    def test_text_format(self):
        out = format_text(self._sample_report())
        assert "test_col" in out
        assert "First meeting" in out

    def test_watercooler_format(self):
        out = format_watercooler(self._sample_report())
        assert "SEEDING AUDIT" in out
        assert "Coverage:" in out

    def test_json_format(self):
        out = format_json(self._sample_report())
        data = json.loads(out)
        assert data["collection"] == "test_col"
        assert data["organic_count"] == 2
        assert len(data["organic_memories"]) == 2
