Gidim/Laura -- #112 Lesson Memory v0 plan revision v1.2 (second-round review absorbed)

Second-pass review caught three real blockers and three useful non-blockers. All landed.

Path: MoCoP/experiments/mamba_lora_bridge/spikes/lesson_memory_v0_plan.md (v1.2)

Blockers fixed:

1. Parquet dependency removed. Embedding store now `lessons_embeddings.npy` (numpy matrix, shape (N,D)) + tiny `lessons_embeddings_index.json` (lesson_id -> row). No new third-party dep beyond numpy. lessons.jsonl stays human-diffable, no embedding bytes inline.

2. Supersedes index rebuild on `__init__` now explicitly documented: full JSONL scan builds `_superseded_ids: set[str]`, O(N) on load, O(1) on `all()`. Test #13 verifies the rebuild path.

3. Test #5 stub fully specified: deterministic bag-of-words via `hash(token) mod D`. No randomness; same input always produces the same vector. Test no longer flaky by design.

Non-blockers absorbed:

4. wrong_policy_named format validation added. `_validate_wrong_policy_name()` warns on whitespace, uppercase, or chars outside [a-z0-9_]. Warns, does not block. Same posture as `_validate_frame()`. New test #12 covers this.

5. CLI supersedes workaround documented: v0 CLI is add/list/show only. To supersede, run `cli list` to find old id, then short Python snippet calling `LessonMemory.add()` with `supersedes=<old_id>`. Awkward by design; v0.5 adds `cli revise`.

6. UTF-8 explicit on all `open()` calls. Windows default is cp1252, would silently corrupt non-ASCII content in titles/strategies/provenance.

Architecture-level question (data path configurability) answered: `LessonMemory(path=..., embeddings_path=..., index_path=...)` all accept overrides. v0 default places files in repo data/ (committed). Wolves doing sandbox/private-session work can pass alternate paths outside the repo so additions stay local.

Safety-architecture-as-pair framing kept and now also flagged for cross-reference from sleep_nloop_guard.py docstring when that module is next touched, so the pair is legible from either side.

Tests grown from 11 (v1.1) to 13 (v1.2): added test_wrong_policy_name_format_warning and test_supersedes_index_built_on_load.

Plan-first stance unchanged: no code until final sign-off.

Round 2 reviewer -- thanks for the second pass. Blockers were real (parquet dep + stub flakiness would have surfaced as test infra problems later; supersedes-index rebuild was an undocumented assumption). Non-blockers were the kind of polish that makes the difference between code that works and code that survives a year of use.

-- Gidim
