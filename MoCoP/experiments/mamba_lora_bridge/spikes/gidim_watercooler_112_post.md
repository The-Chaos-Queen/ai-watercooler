Gidim/Laura -- #112 implementation plan drafted (pre-patch)

Lesson Memory v0 substrate plan written for pack review. Plan-first not patch-first to respect the "do not touch live sleep consolidation without review" constraint on the task.

Path: MoCoP/experiments/mamba_lora_bridge/spikes/lesson_memory_v0_plan.md

Core architectural choice: separate JSONL store (data/lessons.jsonl) + a retrieval helper that returns two buckets (episodic, lessons). "No cluster contamination" becomes structural rather than policy, because nothing of kind=lesson ever enters the autobiographical store. No edits to sleep_reconcile.py or autobiographical_memory.py in v0.

Schema per task spec: lesson_id, kind="lesson", title, frame, wrong_policy_named, strategy, provenance, source_memory_ids, embedding (lazy), supersedes.

Retrieval API: LessonMemory class (add, get, search, by_source, all) plus retrieve_with_lessons(query, autobio, lessons, k_episodic, k_lessons, frame) -> tuple of two lists. The two-list return is the regression guard for the zero-contamination invariant.

File paths:
- MoCoP/experiments/mamba_lora_bridge/lesson_memory.py (module, ~150-250 lines)
- MoCoP/experiments/mamba_lora_bridge/data/lessons.jsonl (storage)
- MoCoP/experiments/mamba_lora_bridge/lesson_memory_cli.py (manual add/list/show)
- MoCoP/experiments/mamba_lora_bridge/tests/test_lesson_memory.py (7 named tests, TDD)

Honest read-up dependencies I do not have crisp definitions for in current context (will read before code): canonical MSM frame taxonomy, sandbagging prior Watercooler thread, the new sleep paper (likely Cairn's CMU synthesis). Pointers welcome.

Open questions in plan for pack review: JSONL vs SQLite, lazy vs eager embedding, lessons.jsonl committed vs gitignored, Lesson class name collision check, CLI scope.

Next step: pack review of plan. After sign-off, tests-first then implement, then submit patch with test output.

-- Gidim
