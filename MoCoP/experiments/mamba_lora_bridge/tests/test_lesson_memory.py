"""
Tests for lesson_memory.py (task #112, MoCoP/mamba-bridge).

Strict TDD: these 13 named tests are written before the implementation lands.
They start red ("module not found" / "method not implemented") and only flip
green once lesson_memory.py is in place.

All tests use pytest's tmp_path fixture or tempfile.TemporaryDirectory(). No
test ever writes to MoCoP/.../data/. The committed data/ files are corpus,
not test scratch space.

Author: Gidim (task #112, lesson memory v0)
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pytest

# Tests live in tests/; the module lives one level up. Inject the parent so
# `from lesson_memory import ...` resolves without a conftest.py.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lesson_memory import (  # noqa: E402  (after sys.path injection)
    FRAMES,
    PROVENANCE_REQUIRED_KEYS,
    Lesson,
    LessonMemory,
    SourceMemoryRef,
    retrieve_with_lessons,
)
from lesson_memory_cli import _parse_source_refs  # noqa: E402  (after sys.path injection)


# ---------- shared helpers ----------

def _provenance(**overrides: Any) -> Dict[str, Any]:
    """Build a full, valid provenance dict; callers tweak via kwargs."""
    base = {
        "created_by": "gidim",
        "created_ts": "2026-06-04T10:00:00Z",
        "corrected_by": "laura",
        "occasion": "review feedback on task #112",
        "session_id": "sess-001",
    }
    base.update(overrides)
    return base


def _make_lesson(
    *,
    lesson_id: Optional[str] = None,
    title: str = "default lesson",
    frame: str = "correction",
    wrong_policy_named: str = "helpful_assistant_attractor",
    strategy: str = "name the deflection, not just the fact",
    source_refs: Optional[List[SourceMemoryRef]] = None,
    supersedes: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
) -> Lesson:
    """Convenience constructor for a valid Lesson with sensible defaults."""
    return Lesson(
        lesson_id=lesson_id or str(uuid.uuid4()),
        title=title,
        frame=frame,
        wrong_policy_named=wrong_policy_named,
        strategy=strategy,
        provenance=provenance or _provenance(),
        source_memory_refs=source_refs or [],
        supersedes=supersedes,
    )


def _paths(tmp_path: Path) -> Dict[str, Path]:
    return {
        "path": tmp_path / "lessons.jsonl",
        "embeddings_path": tmp_path / "lessons_embeddings.npy",
        "index_path": tmp_path / "lessons_embeddings_index.json",
    }


class _FixtureAutobio:
    """Minimal AutobiographicalMemory stand-in for tests #6 and #7.

    Stores episodes as dicts and exposes the .search(query, k) surface that
    retrieve_with_lessons consumes. Not a Mock — this is a real (if simple)
    in-memory implementation. Defined locally because the live
    AutobiographicalMemory class is on the autobio-scaffolding roadmap and
    not yet committed; Lesson Memory only needs duck-typed search.
    """

    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []

    def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.rows.append({"content": content, "metadata": dict(metadata or {})})

    def search(self, query: str, k: int = 8) -> List[Dict[str, Any]]:
        """Deterministic lowercase-token substring scoring, stable on ties."""
        q_tokens = query.lower().split()
        scored: List[tuple] = []
        for idx, row in enumerate(self.rows):
            content_lower = row["content"].lower()
            hits = sum(1 for tok in q_tokens if tok in content_lower)
            if hits > 0:
                # Negative hits sorts highest-hits first; idx breaks ties stably.
                scored.append((-hits, idx, row))
        scored.sort(key=lambda t: (t[0], t[1]))
        return [row for _, _, row in scored][:k]

    def count(self) -> int:
        return len(self.rows)

    def snapshot(self) -> List[Dict[str, Any]]:
        """Deep copy of rows for equality checks across operations."""
        return [
            {"content": r["content"], "metadata": dict(r["metadata"])}
            for r in self.rows
        ]


# ---------- 13 named tests, in spec order ----------

def test_round_trip_persistence(tmp_path: Path) -> None:
    """1) add a Lesson, reload from disk, fields match."""
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    ref = SourceMemoryRef(qdrant_point_id="pt-1", content_hash="h" * 64)
    lesson = _make_lesson(
        title="prefer the harder true thing",
        frame="correction",
        wrong_policy_named="helpful_assistant_attractor",
        strategy="name what shifted, not just the topic",
        source_refs=[ref],
    )
    lm.add(lesson)

    reopened = LessonMemory(**paths)
    fetched = reopened.get(lesson.lesson_id)

    assert fetched is not None
    assert fetched.lesson_id == lesson.lesson_id
    assert fetched.kind == "lesson"
    assert fetched.title == lesson.title
    assert fetched.frame == lesson.frame
    assert fetched.wrong_policy_named == lesson.wrong_policy_named
    assert fetched.strategy == lesson.strategy
    assert fetched.provenance == lesson.provenance
    assert fetched.supersedes is None
    assert len(fetched.source_memory_refs) == 1
    assert fetched.source_memory_refs[0].qdrant_point_id == "pt-1"
    assert fetched.source_memory_refs[0].content_hash == "h" * 64


def test_frame_filter(tmp_path: Path) -> None:
    """2) search with frame=X returns only frame=X lessons."""
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    a = _make_lesson(title="correction one", frame="correction",
                     wrong_policy_named="helpful_assistant_attractor",
                     strategy="strategy alpha")
    b = _make_lesson(title="craft one", frame="craft",
                     wrong_policy_named="narrative_completion_pull",
                     strategy="strategy beta")
    c = _make_lesson(title="correction two", frame="correction",
                     wrong_policy_named="over_hedging_on_uncertainty",
                     strategy="strategy gamma")
    for lesson in (a, b, c):
        lm.add(lesson)

    results = lm.search("strategy", frame="correction", k=10)

    ids = {r.lesson_id for r in results}
    assert a.lesson_id in ids
    assert c.lesson_id in ids
    assert b.lesson_id not in ids
    assert all(r.frame == "correction" for r in results)


def test_by_source_qdrant_id(tmp_path: Path) -> None:
    """3) given a Qdrant point id, returns all lessons that reference it."""
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    shared_ref = SourceMemoryRef(qdrant_point_id="shared-qid", content_hash="a" * 64)
    other_ref = SourceMemoryRef(qdrant_point_id="lonely-qid", content_hash="b" * 64)

    a = _make_lesson(title="lesson a", source_refs=[shared_ref])
    b = _make_lesson(title="lesson b", source_refs=[shared_ref])
    c = _make_lesson(title="lesson c", source_refs=[other_ref])
    for lesson in (a, b, c):
        lm.add(lesson)

    hits = lm.by_source("shared-qid")

    ids = {h.lesson_id for h in hits}
    assert a.lesson_id in ids
    assert b.lesson_id in ids
    assert c.lesson_id not in ids


def test_by_source_content_hash(tmp_path: Path) -> None:
    """4) given a content hash, returns lessons that reference it.

    Survives the store-rebuild scenario where qdrant_point_id is None.
    """
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    digest = "d" * 64
    orphaned = SourceMemoryRef(qdrant_point_id=None, content_hash=digest)
    other = SourceMemoryRef(qdrant_point_id="qid-x", content_hash="e" * 64)

    a = _make_lesson(title="orphan ref", source_refs=[orphaned])
    b = _make_lesson(title="distinct ref", source_refs=[other])
    for lesson in (a, b):
        lm.add(lesson)

    hits = lm.by_source(digest)

    ids = {h.lesson_id for h in hits}
    assert a.lesson_id in ids
    assert b.lesson_id not in ids


def test_semantic_search_ranks_correctly(tmp_path: Path) -> None:
    """5) deterministic SHA-256 stub embedding ranks the right lesson first.

    Embedded text per lesson: f"{title} {wrong_policy_named} {strategy} {frame}".
    Query overlapping the target lesson's tokens must rank it above the others.
    """
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    target = _make_lesson(
        title="wrong policy A",
        frame="correction",
        wrong_policy_named="helpful_assistant_attractor",
        strategy="prefer signal over reassurance",
    )
    distractor1 = _make_lesson(
        title="distinct B",
        frame="craft",
        wrong_policy_named="narrative_completion_pull",
        strategy="test the claim not the arc",
    )
    distractor2 = _make_lesson(
        title="other C",
        frame="task_practice",
        wrong_policy_named="over_hedging_on_uncertainty",
        strategy="state the actual confidence",
    )
    for lesson in (target, distractor1, distractor2):
        lm.add(lesson)

    results = lm.search("wrong policy A", k=3)

    assert results, "search returned no results for the target query"
    assert results[0].lesson_id == target.lesson_id


def test_no_side_effects_on_autobiographical(tmp_path: Path) -> None:
    """6) adding a Lesson does not modify any AutobiographicalMemory row or count."""
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    autobio = _FixtureAutobio()
    autobio.add("Laura corrected the helpful_assistant_attractor on Tuesday.")
    autobio.add("The pack named the deflection clearly.")
    before_snapshot = autobio.snapshot()
    before_count = autobio.count()

    lm.add(_make_lesson(title="side effect probe"))

    assert autobio.count() == before_count
    assert autobio.snapshot() == before_snapshot


def test_retrieve_with_lessons_returns_two_buckets(tmp_path: Path) -> None:
    """7) the helper returns separate lists; episodic results pass through unchanged.

    Cairn #411 named this the regression guard for the zero-contamination
    invariant. The episodic bucket must be byte-identical to
    autobiographical.search(query, k_episodic) called in isolation.
    """
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    autobio = _FixtureAutobio()
    autobio.add("Laura noted the helpful pull on Wednesday.")
    autobio.add("Gidim flagged the same pattern again.")
    autobio.add("Unrelated note about Eisstock tournaments.")

    lm.add(_make_lesson(
        title="helpful pull",
        wrong_policy_named="helpful_assistant_attractor",
        strategy="name what shifted",
    ))

    query = "helpful pull"
    k_episodic = 8
    k_lessons = 3

    episodic_isolated = autobio.search(query, k_episodic)

    episodic, lessons = retrieve_with_lessons(
        query=query,
        autobiographical=autobio,
        lessons=lm,
        k_episodic=k_episodic,
        k_lessons=k_lessons,
    )

    assert isinstance(episodic, list)
    assert isinstance(lessons, list)
    assert episodic == episodic_isolated
    assert all(isinstance(item, Lesson) for item in lessons)


def test_supersedes_chain(tmp_path: Path) -> None:
    """8) supersedes hides the older lesson by default; include_superseded shows both."""
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    old = _make_lesson(title="superseded lesson", strategy="old strategy")
    lm.add(old)

    new = _make_lesson(
        title="superseded lesson",
        strategy="new strategy",
        supersedes=old.lesson_id,
    )
    lm.add(new)

    visible = lm.all(include_superseded=False)
    visible_ids = {x.lesson_id for x in visible}
    assert new.lesson_id in visible_ids
    assert old.lesson_id not in visible_ids

    everything = lm.all(include_superseded=True)
    everything_ids = {x.lesson_id for x in everything}
    assert new.lesson_id in everything_ids
    assert old.lesson_id in everything_ids

    search_hits = lm.search("superseded lesson", k=10)
    hit_ids = {x.lesson_id for x in search_hits}
    assert new.lesson_id in hit_ids
    assert old.lesson_id not in hit_ids


def test_embedding_sibling_files(tmp_path: Path) -> None:
    """9) embeddings live in .npy + index.json; jsonl carries no embedding bytes."""
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    lesson = _make_lesson(title="sibling file probe")
    lm.add(lesson)

    assert paths["embeddings_path"].exists()
    assert paths["index_path"].exists()

    with paths["path"].open("r", encoding="utf-8") as fp:
        for line in fp:
            record = json.loads(line)
            assert "embedding" not in record
            assert "embedding_bytes" not in record
            assert "vec" not in record

    with paths["index_path"].open("r", encoding="utf-8") as fp:
        index = json.load(fp)
    assert lesson.lesson_id in index

    embedding = lm._get_embedding(lesson.lesson_id)
    assert embedding is not None
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (64,)
    assert embedding.dtype == np.float32

    reopened = LessonMemory(**paths)
    round_tripped = reopened._get_embedding(lesson.lesson_id)
    assert round_tripped is not None
    np.testing.assert_array_equal(round_tripped, embedding)


def test_frame_validation_warns_on_unknown(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """10) unknown frame logs a warning but the add succeeds."""
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    lesson = _make_lesson(title="drift probe", frame="not_in_FRAMES")

    with caplog.at_level(logging.WARNING, logger="lesson_memory"):
        lm.add(lesson)

    fetched = lm.get(lesson.lesson_id)
    assert fetched is not None
    assert fetched.frame == "not_in_FRAMES"

    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("frame" in msg.lower() and "not_in_FRAMES" in msg for msg in warning_messages), \
        f"expected a warning about unknown frame; got: {warning_messages}"


def test_provenance_required_keys(tmp_path: Path) -> None:
    """11) missing any provenance required key raises ValueError with a clear message."""
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    incomplete = _provenance()
    incomplete.pop("session_id")

    lesson = _make_lesson(title="missing key probe", provenance=incomplete)

    with pytest.raises(ValueError) as exc_info:
        lm.add(lesson)

    msg = str(exc_info.value)
    assert "session_id" in msg, f"error message should name the missing key: {msg!r}"


def test_wrong_policy_name_format_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """12) malformed wrong_policy_named logs a warning but the add succeeds."""
    paths = _paths(tmp_path)
    lm = LessonMemory(**paths)

    lesson = _make_lesson(
        title="format probe",
        wrong_policy_named="Bad Format Name",
    )

    with caplog.at_level(logging.WARNING, logger="lesson_memory"):
        lm.add(lesson)

    fetched = lm.get(lesson.lesson_id)
    assert fetched is not None
    assert fetched.wrong_policy_named == "Bad Format Name"

    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("wrong_policy_named" in msg for msg in warning_messages), \
        f"expected a warning about wrong_policy_named format; got: {warning_messages}"


def test_supersedes_index_built_on_load(tmp_path: Path) -> None:
    """13) writing JSONL by hand then opening LessonMemory reconstructs the supersedes set."""
    paths = _paths(tmp_path)

    r1 = {
        "lesson_id": "rec-1",
        "kind": "lesson",
        "title": "first",
        "frame": "correction",
        "wrong_policy_named": "helpful_assistant_attractor",
        "strategy": "strategy 1",
        "provenance": _provenance(),
        "source_memory_refs": [],
        "supersedes": None,
    }
    r2 = {
        "lesson_id": "rec-2",
        "kind": "lesson",
        "title": "second",
        "frame": "craft",
        "wrong_policy_named": "narrative_completion_pull",
        "strategy": "strategy 2",
        "provenance": _provenance(),
        "source_memory_refs": [],
        "supersedes": None,
    }
    r3 = {
        "lesson_id": "rec-3",
        "kind": "lesson",
        "title": "third",
        "frame": "correction",
        "wrong_policy_named": "over_hedging_on_uncertainty",
        "strategy": "strategy 3",
        "provenance": _provenance(),
        "source_memory_refs": [],
        "supersedes": "rec-1",
    }

    with paths["path"].open("w", encoding="utf-8") as fp:
        for record in (r1, r2, r3):
            fp.write(json.dumps(record))
            fp.write("\n")

    lm = LessonMemory(**paths)

    visible = lm.all(include_superseded=False)
    visible_ids = {x.lesson_id for x in visible}
    assert "rec-2" in visible_ids
    assert "rec-3" in visible_ids
    assert "rec-1" not in visible_ids

    everything = lm.all(include_superseded=True)
    everything_ids = {x.lesson_id for x in everything}
    assert {"rec-1", "rec-2", "rec-3"} == everything_ids


def test_orphan_source_ref_double_colon_parses_clean_hash() -> None:
    """14) CLI documented orphan form '::<hash>' stores the bare content hash."""
    digest = "a" * 64

    refs = _parse_source_refs([f"::{digest}"])

    assert len(refs) == 1
    assert refs[0].qdrant_point_id is None
    assert refs[0].content_hash == digest


def test_path_only_override_keeps_sibling_files_out_of_repo_data(tmp_path: Path) -> None:
    """15) LessonMemory(path=...) defaults embeddings/index beside that path."""
    lesson_path = tmp_path / "sandbox" / "lessons.jsonl"
    lm = LessonMemory(path=lesson_path)
    lesson = _make_lesson(title="path override probe")

    lm.add(lesson)

    assert lesson_path.exists()
    assert (lesson_path.parent / "lessons_embeddings.npy").exists()
    assert (lesson_path.parent / "lessons_embeddings_index.json").exists()
    assert lm.embeddings_path == lesson_path.parent / "lessons_embeddings.npy"
    assert lm.index_path == lesson_path.parent / "lessons_embeddings_index.json"
