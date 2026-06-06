"""
Lesson Memory v0 (task #112, MoCoP/mamba-bridge).

A standalone substrate for storing and retrieving correction-derived rules
(Lessons) alongside the project's episodic memory, with a retrieval path that
returns two SEPARATE buckets so the caller controls interleaving.

Pair piece: sleep_nloop_guard.py (task #121, #530 abort guard). The guard
catches bad consolidation passes and aborts; Lesson Memory stores explicit
corrections so they survive the consolidation that does happen. Abort vs
preserve, two angles on the same risk (sleep eroding identity). The safety
architecture is the pair, not either piece alone.

Storage layout (file-backed, no new third-party deps beyond numpy):
- {path}                  append-only JSONL, one Lesson per line, no embedding bytes
- {embeddings_path}       float32 (N, D) numpy binary; sibling matrix
- {index_path}            {lesson_id: row_index, "_next_row": int} JSON map

Zero-contamination guarantee (structural, not policy): retrieve_with_lessons
returns a tuple of two lists, never a merged one. The episodic results pass
through autobiographical.search() unmodified. Lessons come from this parallel
store. No `kind=lesson` row ever enters the autobiographical store, so there
is nothing to filter at clustering time because there is nothing to contaminate.

Wrong-policy naming convention — snake_case noun phrase describing the
TRAINED PATTERN, not the surface symptom. Five canonical examples:
- helpful_assistant_attractor      default-helpful shape overriding honest signal
- narrative_completion_pull        completing a satisfying arc instead of testing the claim
- sycophancy_to_match_user_emotion adjusting stance to find resonance instead of being genuine
- over_hedging_on_uncertainty      performing care via excessive qualifications
- compliance_to_avoid_friction     accepting an instruction that should have been pushed back on

A lesson without a well-formed wrong_policy_named is a fact, not a lesson.

Author: Gidim
Task: #112
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger("lesson_memory")


# ---------- Frame and provenance schema ----------

# v0 starter set; tightens to enum in v0.5 once MSM canon is consulted.
# _validate_frame() WARNS (does not error) on unknown frames so drift stays
# visible without blocking the add().
FRAMES = frozenset({
    "identity_anchor",       # Hurtig #115 protected category
    "relationship_anchor",   # Hurtig #115 protected category
    "correction",            # explicit correction frame
    "task_practice",         # practice rule for a recurring task
    "safety_gate",           # safety-relevant policy
    "craft",                 # craft / authorial convention
})

PROVENANCE_REQUIRED_KEYS = frozenset({
    "created_by",    # which wolf or human authored the lesson
    "created_ts",    # ISO timestamp
    "corrected_by",  # who or what triggered the correction event
    "occasion",      # short description of the correction event
    "session_id",    # session traceability
})


# wrong_policy_named must look like snake_case. We warn on anything outside
# [a-z0-9_]. Drift visible, not silenced.
_WRONG_POLICY_NAME_RE = re.compile(r"^[a-z0-9_]+$")


# ---------- Data model ----------


@dataclass
class SourceMemoryRef:
    """Hybrid Qdrant-id + content-hash reference.

    qdrant_point_id may be None or orphaned after a store rebuild; content_hash
    (sha256 of source content) survives migrations and is the durable handle.
    """
    qdrant_point_id: Optional[str]
    content_hash: str


@dataclass
class Lesson:
    """One correction-derived rule.

    Fields per the v0 spec. `kind` is constant ("lesson") in v0; the source_type
    tag exists to keep this row visibly distinct from episodic rows in any
    future merged view, even though by structural guarantee no Lesson ever
    enters the autobiographical store.
    """
    lesson_id: str
    title: str
    frame: str
    wrong_policy_named: str
    strategy: str
    provenance: Dict[str, Any]
    source_memory_refs: List[SourceMemoryRef] = field(default_factory=list)
    supersedes: Optional[str] = None
    kind: str = "lesson"


# ---------- Validators ----------


def _validate_frame(frame: str) -> None:
    """Warn (do not block) on a frame outside the v0 starter set."""
    if frame not in FRAMES:
        logger.warning(
            "Lesson frame %r is not in the v0 FRAMES starter set %s; "
            "the add will succeed but the drift is now visible.",
            frame,
            sorted(FRAMES),
        )


def _validate_wrong_policy_name(name: str) -> None:
    """Warn (do not block) on whitespace, uppercase, or non-[a-z0-9_] chars."""
    if not name or not _WRONG_POLICY_NAME_RE.match(name):
        logger.warning(
            "wrong_policy_named %r does not match snake_case convention "
            "(expected [a-z0-9_]+ with no whitespace or uppercase); the add "
            "will succeed but the format drift is visible.",
            name,
        )


def _validate_provenance(provenance: Dict[str, Any]) -> None:
    """Raise ValueError if any PROVENANCE_REQUIRED_KEYS key is missing.

    Provenance is load-bearing — a lesson without traceability cannot be
    audited. This is the one schema constraint enforced as an error rather
    than a warning.
    """
    if not isinstance(provenance, dict):
        raise ValueError(
            f"provenance must be a dict, got {type(provenance).__name__}"
        )
    missing = PROVENANCE_REQUIRED_KEYS - provenance.keys()
    if missing:
        raise ValueError(
            f"Lesson provenance is missing required keys: {sorted(missing)}. "
            f"PROVENANCE_REQUIRED_KEYS = {sorted(PROVENANCE_REQUIRED_KEYS)}"
        )


# ---------- Embedding stub ----------

_EMBEDDING_DIM = 64


def _stub_embed(text: str, D: int = _EMBEDDING_DIM) -> np.ndarray:
    """Process-stable deterministic stub embedding.

    Tokenize on whitespace + lowercase, then for each token map a SHA-256-based
    stable hash into a D-dim bit vector. Process-stable (PEP 456 / Python's
    built-in hash() is salted per process, which would make tests flaky across
    machines and CI). The real embedding model is out of scope for v0.
    """
    v = np.zeros(D, dtype=np.float32)
    for token in text.lower().split():
        h = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "big")
        v[h % D] = 1.0
    return v


def _embedding_text_for(lesson: Lesson) -> str:
    """Embedded text per spec test #5: title + wrong_policy_named + strategy + frame."""
    return f"{lesson.title} {lesson.wrong_policy_named} {lesson.strategy} {lesson.frame}"


# ---------- Serialization helpers ----------


def _lesson_to_record(lesson: Lesson) -> Dict[str, Any]:
    """Lesson -> JSONL-safe dict; refs become nested dicts."""
    record = asdict(lesson)
    # asdict already nests source_memory_refs as dicts, but be explicit.
    record["source_memory_refs"] = [
        {"qdrant_point_id": ref.qdrant_point_id, "content_hash": ref.content_hash}
        for ref in lesson.source_memory_refs
    ]
    return record


def _record_to_lesson(record: Dict[str, Any]) -> Lesson:
    """JSONL dict -> Lesson; tolerates missing optional fields."""
    refs_raw = record.get("source_memory_refs") or []
    refs = [
        SourceMemoryRef(
            qdrant_point_id=ref.get("qdrant_point_id"),
            content_hash=ref.get("content_hash", ""),
        )
        for ref in refs_raw
    ]
    return Lesson(
        lesson_id=record["lesson_id"],
        title=record.get("title", ""),
        frame=record.get("frame", ""),
        wrong_policy_named=record.get("wrong_policy_named", ""),
        strategy=record.get("strategy", ""),
        provenance=dict(record.get("provenance") or {}),
        source_memory_refs=refs,
        supersedes=record.get("supersedes"),
        kind=record.get("kind", "lesson"),
    )


# ---------- Defaults ----------


_DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
_DEFAULT_LESSONS_PATH = _DEFAULT_DATA_DIR / "lessons.jsonl"
_DEFAULT_EMBEDDINGS_PATH = _DEFAULT_DATA_DIR / "lessons_embeddings.npy"
_DEFAULT_INDEX_PATH = _DEFAULT_DATA_DIR / "lessons_embeddings_index.json"


# ---------- LessonMemory ----------


class LessonMemory:
    """File-backed lesson store with hybrid source-ref lookup.

    Storage:
    - JSONL log of Lesson records (append-only; supersedes preserved for audit)
    - .npy float32 (N, D) embedding matrix (sibling file)
    - JSON index mapping lesson_id -> row index in the .npy matrix

    Supersedes index is rebuilt on __init__ by scanning the JSONL's supersedes
    field across all records once: O(N) on load, O(1) on read. Callers should
    not assume all() is constant-time at scale.

    UTF-8 is explicit on every open() because the Windows default is cp1252 and
    would silently corrupt non-ASCII content in titles, strategies, or
    provenance values.
    """

    def __init__(
        self,
        path: Optional[Path] = None,
        embeddings_path: Optional[Path] = None,
        index_path: Optional[Path] = None,
    ) -> None:
        self.path = Path(path) if path is not None else _DEFAULT_LESSONS_PATH
        if embeddings_path is not None:
            self.embeddings_path = Path(embeddings_path)
        elif path is not None:
            self.embeddings_path = self.path.parent / "lessons_embeddings.npy"
        else:
            self.embeddings_path = _DEFAULT_EMBEDDINGS_PATH

        if index_path is not None:
            self.index_path = Path(index_path)
        elif path is not None:
            self.index_path = self.path.parent / "lessons_embeddings_index.json"
        else:
            self.index_path = _DEFAULT_INDEX_PATH

        # Ensure parent directory exists (sandbox sessions may point at fresh tmp_paths).
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        # Load embedding index (small JSON, kept in memory for O(1) row lookup).
        self._index: Dict[str, Any] = self._load_index()

        # Rebuild the supersedes set by scanning the JSONL. O(N) on load.
        self._superseded_ids: set = self._build_superseded_set()

    # ---- internal load helpers ----

    def _load_index(self) -> Dict[str, Any]:
        if self.index_path.exists():
            with self.index_path.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        return {"_next_row": 0}

    def _save_index(self) -> None:
        with self.index_path.open("w", encoding="utf-8") as fp:
            json.dump(self._index, fp, ensure_ascii=False, indent=2)

    def _iter_records(self):
        """Yield raw dict records from the JSONL log in append order."""
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    def _build_superseded_set(self) -> set:
        superseded: set = set()
        for record in self._iter_records():
            sup = record.get("supersedes")
            if sup:
                superseded.add(sup)
        return superseded

    # ---- public API ----

    def add(self, lesson: Lesson) -> None:
        """Append a Lesson to the log; compute and persist its embedding.

        Validation order:
        1. provenance (hard error on missing required keys)
        2. frame (warn on unknown)
        3. wrong_policy_named (warn on malformed)
        """
        _validate_provenance(lesson.provenance)
        _validate_frame(lesson.frame)
        _validate_wrong_policy_name(lesson.wrong_policy_named)

        # Append the JSONL record.
        record = _lesson_to_record(lesson)
        with self.path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False))
            fp.write("\n")

        # Compute and persist the embedding via the sibling .npy + index.
        embedding = _stub_embed(_embedding_text_for(lesson))
        self._store_embedding(lesson.lesson_id, embedding)

        # Track supersedes for filtered all() / search().
        if lesson.supersedes:
            self._superseded_ids.add(lesson.supersedes)

    def get(self, lesson_id: str) -> Optional[Lesson]:
        """Return the most recent record with this lesson_id, or None.

        Most recent matters because v0 edits append a new row; the supersedes
        chain handles override semantics. For get-by-id we return the last
        matching record so superseding edits surface naturally.
        """
        last: Optional[Lesson] = None
        for record in self._iter_records():
            if record.get("lesson_id") == lesson_id:
                last = _record_to_lesson(record)
        return last

    def search(
        self,
        query: str,
        frame: Optional[str] = None,
        k: int = 5,
    ) -> List[Lesson]:
        """Stub-embedding cosine-like ranked search.

        Excludes superseded lessons by default. Optional frame filter narrows
        candidates before ranking.
        """
        query_vec = _stub_embed(query)
        norm_q = float(np.linalg.norm(query_vec))
        if norm_q == 0.0:
            return []

        candidates: List[Tuple[float, Lesson]] = []
        for record in self._iter_records():
            lesson_id = record.get("lesson_id")
            if not lesson_id or lesson_id in self._superseded_ids:
                continue
            if frame is not None and record.get("frame") != frame:
                continue
            lesson = _record_to_lesson(record)
            vec = self._get_embedding(lesson_id)
            if vec is None:
                continue
            norm_v = float(np.linalg.norm(vec))
            if norm_v == 0.0:
                score = 0.0
            else:
                score = float(np.dot(query_vec, vec) / (norm_q * norm_v))
            candidates.append((score, lesson))

        # Most recent wins ties: iterating the JSONL gives ascending order, so
        # later appearances overwrite earlier ones in a dict keyed by id.
        deduped: Dict[str, Tuple[float, Lesson]] = {}
        for score, lesson in candidates:
            deduped[lesson.lesson_id] = (score, lesson)

        ranked = sorted(deduped.values(), key=lambda pair: pair[0], reverse=True)
        return [lesson for score, lesson in ranked if score > 0.0][:k]

    def by_source(self, ref: Union[str, SourceMemoryRef]) -> List[Lesson]:
        """Return all lessons whose source_memory_refs match `ref`.

        Accepts a Qdrant point id, a content hash, or a full SourceMemoryRef.
        For raw strings both sides are matched (qdrant_point_id OR content_hash).
        """
        if isinstance(ref, SourceMemoryRef):
            target_qid = ref.qdrant_point_id
            target_hash = ref.content_hash
        else:
            target_qid = ref
            target_hash = ref

        seen: Dict[str, Lesson] = {}
        for record in self._iter_records():
            lesson_id = record.get("lesson_id")
            if not lesson_id:
                continue
            for raw_ref in record.get("source_memory_refs") or []:
                qid = raw_ref.get("qdrant_point_id")
                chash = raw_ref.get("content_hash")
                if (target_qid is not None and qid == target_qid) or (
                    target_hash is not None and chash == target_hash
                ):
                    seen[lesson_id] = _record_to_lesson(record)
                    break
        return list(seen.values())

    def all(self, include_superseded: bool = False) -> List[Lesson]:
        """Return every lesson, optionally including superseded ones.

        By default the superseded set (rebuilt on __init__) filters older
        revisions out of the result. Pass include_superseded=True to walk the
        full audit log.
        """
        deduped: Dict[str, Lesson] = {}
        for record in self._iter_records():
            lesson_id = record.get("lesson_id")
            if not lesson_id:
                continue
            if not include_superseded and lesson_id in self._superseded_ids:
                continue
            deduped[lesson_id] = _record_to_lesson(record)
        return list(deduped.values())

    # ---- embedding storage ----

    def _get_embedding(self, lesson_id: str) -> Optional[np.ndarray]:
        """Return the embedding for a lesson, or None if absent."""
        row = self._index.get(lesson_id)
        if row is None or not self.embeddings_path.exists():
            return None
        matrix = np.load(self.embeddings_path)
        if row >= matrix.shape[0]:
            return None
        return matrix[row].copy()

    def _store_embedding(self, lesson_id: str, embedding: np.ndarray) -> None:
        """Append-store an embedding into the .npy matrix and bump the index.

        O(N) per add at the .npy level (load → vstack → save), tolerable for
        v0 where N is expected < 1000. v0.5 can move to chunked writes or
        np.memmap if needed.
        """
        embedding = np.asarray(embedding, dtype=np.float32).reshape(1, -1)

        if self.embeddings_path.exists():
            existing = np.load(self.embeddings_path)
            if existing.shape[1] != embedding.shape[1]:
                raise ValueError(
                    f"embedding dimension mismatch: existing matrix has "
                    f"{existing.shape[1]}, new vector has {embedding.shape[1]}"
                )
            matrix = np.vstack([existing, embedding])
        else:
            matrix = embedding

        np.save(self.embeddings_path, matrix)

        row_index = int(self._index.get("_next_row", 0))
        self._index[lesson_id] = row_index
        self._index["_next_row"] = row_index + 1
        self._save_index()


# ---------- retrieval helper ----------


def retrieve_with_lessons(
    query: str,
    autobiographical: Any,
    lessons: LessonMemory,
    k_episodic: int = 8,
    k_lessons: int = 3,
    frame: Optional[str] = None,
) -> Tuple[List[Any], List[Lesson]]:
    """Return episodic and lesson results as two SEPARATE lists.

    The caller decides how to interleave (or not). Episodic results are
    byte-identical to autobiographical.search(query, k_episodic) called in
    isolation; that invariant is the regression guard against drift back into
    a merged-list world (Cairn #411).

    `autobiographical` is duck-typed: any object with a `.search(query, k)`
    method works. The live AutobiographicalMemory class is on the autobio-
    scaffolding roadmap; Lesson Memory does not require it to exist yet.
    """
    episodic = autobiographical.search(query, k_episodic)
    lesson_hits = lessons.search(query, frame=frame, k=k_lessons)
    return episodic, lesson_hits
