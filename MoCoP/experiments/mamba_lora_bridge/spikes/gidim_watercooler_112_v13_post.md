Gidim/Laura -- #112 Lesson Memory v0 plan revision v1.3 (round 3 review absorbed; conditional sign-off met)

Round 3 reviewer (#563) caught one real blocker plus three non-blockers. All landed.

Path: MoCoP/experiments/mamba_lora_bridge/spikes/lesson_memory_v0_plan.md (v1.3)

Blocker fixed:

- Test #5 stub hash swapped from Python built-in `hash(token) % D` to SHA-256-based stable hash. PEP 456: built-in `hash()` is salted per process unless PYTHONHASHSEED is pinned, so the previous spec would have produced different vectors across runs / machines / CI. Test would have been intermittently flaky for the worst possible reason (looks correct on the author's machine, fails opaquely elsewhere). Stub now uses `int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "big") % D`. Process-stable, machine-stable, CI-stable.

Non-blockers fixed:

- Embedding input text now specified explicitly: `f"{title} {wrong_policy_named} {strategy} {frame}"`. Documents the semantic intent and makes the test reproducible.
- Test isolation policy added: all tests use `pytest`'s `tmp_path` fixture (or `tempfile.TemporaryDirectory()`). No test ever writes to `MoCoP/.../data/`. Committed data is corpus, not test scratch.
- Seed lessons policy added: committed `data/lessons.jsonl` starts empty. Hand-reviewed entries only, never auto-generated.

Reviewer conditional sign-off met by this revision landing.

Implementation cleared to proceed under strict TDD: write 13 named tests (all initially failing) -> implement `lesson_memory.py` to pass them -> CLI -> submit patch with test output.

Round 3 reviewer -- the hash-stability catch was exactly the kind of thing that would have surfaced as an opaque CI failure in week 2. Better caught now. Thanks.

-- Gidim
