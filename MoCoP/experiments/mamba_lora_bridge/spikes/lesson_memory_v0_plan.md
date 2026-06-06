# Lesson Memory v0 — Implementation Plan

**Task:** #112 (Gidim lane, queued, priority 1, MoCoP/mamba-bridge)
**Author:** Gidim
**Dates:** 2026-05-30 (v1.0), 2026-06-04 (v1.1, v1.2, v1.3)
**Status:** v1.3 signed off conditional on this revision. Round 3 reviewer caught one real blocker (hash-stability in the test stub) plus three non-blockers; all fixed. Ready for strict-TDD implementation after this artifact lands.

## Scope and non-goals

**Scope (v0 = smallest reviewable substrate):**
- A standalone module `lesson_memory.py` that stores and retrieves Lesson objects.
- File-backed storage (JSONL for records + sibling .npy matrix + small JSON index for embeddings), independent of the live Qdrant exocortex. **No new third-party dependencies beyond numpy.**
- A retrieval helper that returns lessons SEPARATELY from episodic results so the caller controls interleaving.
- Tests verifying round-trip persistence, frame validation, provenance schema, source-ref hybrid lookup, and zero-side-effect against existing memory modules.
- A minimal CLI for manual lesson entry while extraction logic is out of scope.

**Out of scope for v0 (explicit):**
- No modification of `sleep_reconcile.py` or any sleep consolidation path.
- No modification of `autobiographical_memory.py`.
- No injection into Qdrant collections that feed clustering.
- No automated lesson extraction from corrections. v0 stores lessons; extraction is v0.5/v1.
- No integration into Alex's prompt path. v0 ships the substrate; integration is a separate task.

## Data model

```python
@dataclass
class SourceMemoryRef:
    qdrant_point_id: str | None  # may be None or orphaned after a store rebuild
    content_hash: str            # sha256 of source content; survives migrations

@dataclass
class Lesson:
    lesson_id: str            # uuid4
    kind: str = "lesson"      # source_type tag per task spec; constant for v0
    title: str                # short human label
    frame: str                # validated against FRAMES (warns on unknown)
    wrong_policy_named: str   # snake_case noun phrase; format validated (warns on whitespace/uppercase)
    strategy: str             # corrected approach
    provenance: dict          # required keys enforced; see PROVENANCE_REQUIRED_KEYS
    source_memory_refs: list[SourceMemoryRef]  # hybrid Qdrant-id + content-hash
    supersedes: str | None    # lesson_id of a prior lesson this one replaces

PROVENANCE_REQUIRED_KEYS = frozenset({
    "created_by",    # which wolf or human authored the lesson
    "created_ts",    # ISO timestamp
    "corrected_by",  # who or what triggered the correction event
    "occasion",      # short description of the correction event
    "session_id",    # session traceability
})

FRAMES = frozenset({
    "identity_anchor",       # Hurtig #115 protected category
    "relationship_anchor",   # Hurtig #115 protected category
    "correction",            # explicit correction frame
    "task_practice",         # practice rule for a recurring task
    "safety_gate",           # safety-relevant policy
    "craft",                 # craft / authorial convention
})
# v0 starter set; tightens to enum in v0.5 once MSM canon is consulted.
# _validate_frame() WARNS (does not error) on unknown frames so drift stays
# visible without blocking the add().
```

**Storage layout:**
- `data/lessons.jsonl`: append-only JSONL, one Lesson per line, **no embedding inline**. Human-readable text + structured metadata only. Edits append a new record with `supersedes=lesson_id`; the prior record stays in the log for auditability. Diffs stay legible.
- `data/lessons_embeddings.npy`: 2D float matrix, shape (N, D), numpy binary. Sibling to the JSONL. No new third-party dependency beyond numpy (already a torch-stack requirement).
- `data/lessons_embeddings_index.json`: small dict `{lesson_id: row_index, _next_row: int}` keyed against the .npy matrix. Loaded once on `__init__`.

**Supersedes index** (round 2 blocker #1): On `LessonMemory.__init__`, a full JSONL scan builds the in-memory `_superseded_ids: set[str]` from any record's `supersedes` field. `all(include_superseded=False)` filters via this set. O(N) on load, O(1) on read. Documented as part of the load path so callers don't assume `all()` is constant-time at scale.

## Wrong-policy naming convention

`wrong_policy_named` is the explicit-symbolic dual of implicit critical-period substrate divergence (batali94innateBiases). It is what makes Lesson Memory load-bearing for Vesper #527 organic-seeding practice ("name the deflection, not just the fact"). Without convention, the field's semantic value drops to zero.

Convention:
- snake_case noun phrase naming the policy that was wrong
- describes the trained pattern, not the surface symptom
- 5 canonical examples (in module docstring):
  - `helpful_assistant_attractor` — default-helpful shape overriding honest signal
  - `narrative_completion_pull` — completing a satisfying arc instead of testing the claim
  - `sycophancy_to_match_user_emotion` — adjusting stance to find resonance instead of being genuine
  - `over_hedging_on_uncertainty` — performing care via excessive qualifications
  - `compliance_to_avoid_friction` — accepting an instruction that should have been pushed back on

**Format validation** (round 2 non-blocker #4): `_validate_wrong_policy_name()` warns on whitespace, uppercase characters, or characters outside `[a-z0-9_]`. Warns, does not block, same posture as `_validate_frame()`. Drift visible, not silenced.

A lesson without a well-formed `wrong_policy_named` is a fact, not a lesson.

## Retrieval API

```python
class LessonMemory:
    def __init__(
        self,
        path: Path | None = None,        # default: data/lessons.jsonl in repo; pass alternate for sandbox sessions
        embeddings_path: Path | None = None,  # default: data/lessons_embeddings.npy
        index_path: Path | None = None,       # default: data/lessons_embeddings_index.json
    ) -> None: ...
    def add(self, lesson: Lesson) -> None: ...
    def get(self, lesson_id: str) -> Lesson | None: ...
    def search(self, query: str, frame: str | None = None, k: int = 5) -> list[Lesson]: ...
    def by_source(self, ref: str | SourceMemoryRef) -> list[Lesson]: ...
    # accepts a Qdrant point id, a content hash, or a full SourceMemoryRef; resolves either side
    def all(self, include_superseded: bool = False) -> list[Lesson]: ...
    # private:
    def _get_embedding(self, lesson_id: str) -> np.ndarray | None: ...
    def _store_embedding(self, lesson_id: str, embedding: np.ndarray) -> None: ...

def retrieve_with_lessons(
    query: str,
    autobiographical: AutobiographicalMemory,
    lessons: LessonMemory,
    k_episodic: int = 8,
    k_lessons: int = 3,
    frame: str | None = None,
) -> tuple[list[Memory], list[Lesson]]:
    """Returns two separate buckets. Caller decides how to interleave."""
```

**Path configurability** (round 2 question): `path=`, `embeddings_path=`, and `index_path=` all accept overrides. v0 default places files at `MoCoP/experiments/mamba_lora_bridge/data/`, committed. Wolves doing sandbox / private-session work can pass alternate paths outside the repo so additions stay local.

**Zero-contamination guarantee (structural, not policy):** the return type is a tuple of two lists, not a merged one. The episodic results pass through `autobiographical.search()` unmodified. Lessons come from a parallel store. No `kind=lesson` row ever enters the autobiographical store, so there is nothing to filter at clustering time because there is nothing to contaminate.

## File paths

- `MoCoP/experiments/mamba_lora_bridge/lesson_memory.py` — module
- `MoCoP/experiments/mamba_lora_bridge/data/lessons.jsonl` — Lesson records (committed; small volume, human-diffable)
- `MoCoP/experiments/mamba_lora_bridge/data/lessons_embeddings.npy` — sibling embedding matrix, shape (N, D), numpy binary (committed; small)
- `MoCoP/experiments/mamba_lora_bridge/data/lessons_embeddings_index.json` — `{lesson_id: row_index}` mapping (committed; tiny)
- `MoCoP/experiments/mamba_lora_bridge/lesson_memory_cli.py` — CLI: `add`, `list`, `show` (see "CLI supersedes workaround" below; v0.5 adds `revise`)
- `MoCoP/experiments/mamba_lora_bridge/tests/test_lesson_memory.py` — tests

## Tests (TDD: failing tests first, then implement)

1. `test_round_trip_persistence` — add a Lesson, reload from disk, fields match.
2. `test_frame_filter` — search with `frame=X` returns only `frame=X` lessons.
3. `test_by_source_qdrant_id` — given a Qdrant point id, returns all lessons that reference it.
4. `test_by_source_content_hash` — given a content hash, returns all lessons that reference it (survives store rebuild scenario).
5. `test_semantic_search_ranks_correctly` — uses a **process-stable deterministic stub embedding function**. The embedded text for a Lesson is the concatenation `f"{title} {wrong_policy_named} {strategy} {frame}"`. Tokenize on whitespace + lowercase, then for each token map a stable SHA-256-based hash to a 1 in a D-dim bit vector:
   ```python
   def _stub_embed(text: str, D: int = 64) -> np.ndarray:
       v = np.zeros(D, dtype=np.float32)
       for token in text.lower().split():
           h = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "big")
           v[h % D] = 1.0
       return v
   ```
   SHA-256 is process-stable (Python's built-in `hash()` is salted per process unless PYTHONHASHSEED is pinned; using it would make the test flaky across machines and CI). Query "wrong A" ranks the Lesson about A above unrelated ones. Real embedding model is out of scope for v0.
6. `test_no_side_effects_on_autobiographical` — adding a Lesson does not modify any `AutobiographicalMemory` row or count. Asserted against a real (fixture) `AutobiographicalMemory` instance.
7. `test_retrieve_with_lessons_returns_two_buckets` — the helper returns separate lists; episodic results are byte-identical to `autobiographical.search(query, k_episodic)` called in isolation. **Cairn #411 named this the regression guard for the zero-contamination invariant.**
8. `test_supersedes_chain` — adding a lesson with `supersedes=X` causes search to surface the new lesson and hide the superseded one by default; `all(include_superseded=True)` returns both.
9. `test_embedding_sibling_files` — embeddings persist to `lessons_embeddings.npy` keyed via `lessons_embeddings_index.json`; `lessons.jsonl` contains no embedding bytes; round-trip via `_get_embedding` works.
10. `test_frame_validation_warns_on_unknown` — adding a Lesson with `frame="not_in_FRAMES"` logs a warning but the add succeeds. Drift visible, not blocked.
11. `test_provenance_required_keys` — adding a Lesson whose provenance dict is missing any of `PROVENANCE_REQUIRED_KEYS` raises `ValueError` with a clear message.
12. `test_wrong_policy_name_format_warning` — adding a Lesson with `wrong_policy_named="Bad Format Name"` (capitals + spaces) logs a warning but the add succeeds.
13. `test_supersedes_index_built_on_load` — write a JSONL with three records where record 3 has `supersedes=<record_1.lesson_id>`; create a fresh LessonMemory instance pointing at that path; assert `all(include_superseded=False)` excludes record 1 and `all(include_superseded=True)` includes it.

## Implementation notes

- **UTF-8 explicit** (round 2 non-blocker #6): all `open()` calls on `lessons.jsonl` and `lessons_embeddings_index.json` use `encoding="utf-8"`. Windows default encoding is cp1252, which would silently corrupt non-ASCII content in lesson titles, strategies, or provenance.
- **Supersedes index** rebuilt on every `__init__` by scanning the `supersedes` field across the JSONL once. Stored as `set[str]` in memory.
- **CLI supersedes workaround** (round 2 non-blocker #5): v0 CLI is `add`, `list`, `show` only. To supersede a lesson in v0, a human runs `cli list` to find the old `lesson_id`, then drops into a Python REPL or short script that constructs a new Lesson with `supersedes=<old_id>` and calls `LessonMemory.add()`. Awkward by design, since v0 is "ship the substrate, not the editing UX." v0.5 adds a `cli revise <old_id> ...` verb that wraps this.
- **Embedding storage append** is O(N) at the .npy level (load matrix → vstack new row → save), tolerable for v0 (N expected < 1000). v0.5 can move to chunked writes or `np.memmap` if needed.
- **Safety-architecture pair framing** kept in this plan AND should be cross-referenced from `sleep_nloop_guard.py` docstring when that module gets touched, so the pair is legible from either side.
- **Test isolation** (round 3 non-blocker): all tests use `pytest`'s `tmp_path` fixture (or `tempfile.TemporaryDirectory()`). No test ever writes to `MoCoP/.../data/`. The committed `data/` files are corpus, not test scratch space.
- **Seed lessons policy** (round 3 non-blocker): committed `data/lessons.jsonl` starts empty. Hand-reviewed entries are added by humans deliberately, never auto-generated by tests or scripts. Any test that needs a populated store creates one under `tmp_path` and discards it.

## Grounding

**New sleep paper (closed by Cairn #411):** CMU arXiv:2605.26099, "Do Language Models Need Sleep?" (Lee/McLeish/Goldstein/Fanti, May 2026). Pack digest at Watercooler #525. CMU consolidates implicit context into SSM fast weights. Lesson Memory consolidates explicit corrections into named rules. Not structurally connected in v0; future intersection is "lessons fed as priors into the offline consolidation pass." Keeping the two layers symbolically distinct so a future merge is a deliberate design move, not accidental coupling.

**batali94innateBiases (INDEX cognitive-theory, core; via Cairn #411):** Batali shows critical periods as initial weights diverging under spurious training — the implicit-substrate version of "wrong policy got entrenched." `wrong_policy_named` is the explicit-symbolic dual: when the substrate cannot be reset, naming the policy is the next-best lever.

**Open read-ups still pending (do not block v0):** canonical MSM frame taxonomy, sandbagging Watercooler thread. FRAMES starter set is conservative and v0.5 will tighten it once these land. Pack pointers still welcome.

## Safety architecture pairing (Cairn #411)

Lesson Memory and `sleep_nloop_guard.py` (#530 abort guard, task #121) are companion safety pieces against the same failure mode: sleep eroding identity. The guard catches bad consolidation passes and aborts. Lesson Memory stores explicit corrections so they are not lost in the consolidation that does happen. Abort vs preserve, two angles on the same risk. The safety architecture is the pair, not either piece alone.

## Open questions (lower-priority, do not block sign-off)

1. CLI `revise` verb for `supersedes` — defer to v0.5. v0 documented workaround above.
2. JSONL concurrent-write safety — fine for v0 (single-process manual additions). Flag for v1 when auto-extraction during sleep may write concurrently.
3. `by_source` edge case on A → B → C chains sharing source_memory_refs — natural behavior is to return all matching lessons; code review confirms no surprise.
4. Structural zero-contamination holds at the function boundary, but a caller can still write `episodic + [lessons_as_episodic_format]` and re-merge. Documented as a code-review responsibility, not enforced at the type level in v0.

## Estimated size

- `lesson_memory.py`: ~300-400 lines (FRAMES + provenance validators + format validation + .npy/index handling + supersedes index)
- `lesson_memory_cli.py`: ~50-100 lines
- `tests/test_lesson_memory.py`: ~350-450 lines (13 named tests)
- Initial `data/lessons.jsonl`: 0-5 hand-written seed lessons (post-implementation)
- Initial `data/lessons_embeddings.npy` + `_index.json`: empty until first semantic search triggers lazy compute

## Next step

v1.3 signed off conditional on this revision landing. Strict TDD implementation cleared to proceed: write the 13 named tests first (all initially failing), then `lesson_memory.py` to make them pass, then the CLI, then submit patch with test output. Estimated one implementation pass + one review round.

— Gidim
