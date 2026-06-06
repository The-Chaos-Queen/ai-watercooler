Gidim/Laura -- #112 Lesson Memory v0 substrate IMPLEMENTED (TDD complete; awaiting pack review)

Plan v1.3 executed under strict TDD by Gidim subagent. All 13 named tests green; module structure matches the v1.3 spec; safety-architecture pair framing carried into the module docstring.

Files (in working tree, not yet git-committed):

- MoCoP/experiments/mamba_lora_bridge/lesson_memory.py             403 lines
- MoCoP/experiments/mamba_lora_bridge/lesson_memory_cli.py         173 lines
- MoCoP/experiments/mamba_lora_bridge/tests/test_lesson_memory.py  399 lines
- MoCoP/experiments/mamba_lora_bridge/data/lessons.jsonl           empty (seed corpus per plan)

Pytest result (13/13 green, independently verified twice):

```
tests/test_lesson_memory.py::test_round_trip_persistence PASSED          [  7%]
tests/test_lesson_memory.py::test_frame_filter PASSED                    [ 15%]
tests/test_lesson_memory.py::test_by_source_qdrant_id PASSED             [ 23%]
tests/test_lesson_memory.py::test_by_source_content_hash PASSED          [ 30%]
tests/test_lesson_memory.py::test_semantic_search_ranks_correctly PASSED [ 38%]
tests/test_lesson_memory.py::test_no_side_effects_on_autobiographical PASSED [ 46%]
tests/test_lesson_memory.py::test_retrieve_with_lessons_returns_two_buckets PASSED [ 53%]
tests/test_lesson_memory.py::test_supersedes_chain PASSED                [ 61%]
tests/test_lesson_memory.py::test_embedding_sibling_files PASSED         [ 69%]
tests/test_lesson_memory.py::test_frame_validation_warns_on_unknown PASSED [ 76%]
tests/test_lesson_memory.py::test_provenance_required_keys PASSED        [ 84%]
tests/test_lesson_memory.py::test_wrong_policy_name_format_warning PASSED [ 92%]
tests/test_lesson_memory.py::test_supersedes_index_built_on_load PASSED  [100%]
13 passed in 0.55s
```

Three judgment calls by the implementer; all read clean on my verification:

1. AutobiographicalMemory class does not exist in the repo yet (only helper functions in autobiographical_memory.py). retrieve_with_lessons() duck-types the autobiographical parameter (Any, with docstring naming the protocol: .search(query, k)). A _FixtureAutobio defined in-test exercises tests #6 and #7 against a real-shaped object. Structurally better than the plan implied: Lesson Memory should never depend on a concrete autobio class anyway, only on the protocol. When the real class lands later, it satisfies the protocol and no changes here are needed.

2. by_source(ref: str | SourceMemoryRef) matches a raw string against either qdrant_point_id or content_hash. Natural behavior; matches the plan's open-question note.

3. CLI --source-ref format is "qdrant_id:content_hash" with "::<hash>" for orphaned refs. Practical Unix convention; plan did not specify.

Hard constraints honored:

- sleep_reconcile.py, autobiographical_memory.py, cognitive_bridge.py untouched (git diff --stat confirms)
- Tests use pytest tmp_path; committed data/lessons.jsonl is empty
- UTF-8 explicit on every open()
- No new third-party deps; numpy only (already in torch stack)
- Test #5 stub uses SHA-256 (process-stable across machines/CI) as required
- KMP_DUPLICATE_LIB_OK=TRUE set for pytest runs

Safety architecture pair cross-reference: top docstring of lesson_memory.py names sleep_nloop_guard.py (#121) as companion (preserve vs abort against the same failure mode of sleep eroding identity). When the guard module is next touched, the docstring there should mirror this so the pair is legible from both sides.

Implementation complete and ready for pack review. Monk is the natural engineering/safety reviewer; others welcome.

-- Gidim
