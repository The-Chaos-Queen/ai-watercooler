# Qwen3-Coder-Next Memory Legibility Plan - 2026-04-20

## Purpose

This plan tests one narrow question:

**Can a much stronger, more agentic responder make better use of the current Qdrant memory structure than `Qwen/Qwen2.5-1.5B`?**

This is **not** a final deployment plan.
It is a diagnostic plan.

The point is to separate:

- memory structure / retrieval legibility
from
- baby-Qwen answer-time integration weakness

If a strong model can read the same recalled memory objects and answer well, the current memory layer is at least partly usable.
If a strong model still fails, the memory substrate or retrieval surface likely still needs repair.

---

## Why `Qwen/Qwen3-Coder-Next`

Reason for choosing it:

- it is known for strong tool use and scaffold handling
- it should be better than baby Qwen at using structured external context
- that makes it a good **memory-legibility probe**

Important caution:

- it is a coder-specialized model, not a final relational-chat target
- therefore we use it to test **whether the memory system is readable**, not whether it is the final desired personality model

Relevant model-card notes:

- model: [Qwen/Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next)
- open-weight MoE model with 80B total parameters, 3B activated
- 256k native context
- best served through `vLLM` or `SGLang`
- if startup fails, reduce context length first before changing the experiment

---

## Core Question

### Primary question

Given the **same** Qdrant collection, **same** retrieval logic, and **same** recalled memory blocks:

does `Qwen3-Coder-Next` answer from memory more faithfully than `Qwen2.5-1.5B`?

### Secondary question

If it does improve, **where** does the improvement appear?

- direct factual answer quality
- reduced apology / refusal collapse
- better use of cluster arcs
- better use of autobiographical anchors

---

## What Must Stay Fixed

To make the result interpretable, keep these fixed:

- Qdrant collection
- retrieval ranking logic
- memory row schema
- cluster recall logic
- eval case set
- review rubric

The only intended variable is the **responder model**.

---

## Frozen Test Substrate

Use the already repaired hybrid D2 collection first:

- collection: `mocop_private_steve_d2_hybrid_20260420T164634`

Why this collection:

- it already has repaired `macro_memory` rows
- it is the exact collection used in the latest Steve clustered-memory rerun
- keeping the collection fixed avoids conflating “better model” with “different memory contents”

Reference artifacts:

- `run_reincarnation/steve_d2_hybrid_20260420T164634/cluster_report_repaired.json`
- `run_reincarnation/steve_d2_hybrid_20260420T164634/steve_d2_private_recall_eval_expanded_repaired.json`
- `run_reincarnation/steve_d2_hybrid_20260420T164634/manual_answer_review_2026-04-20.md`

---

## Experiment Design

## Phase A - Pure Memory-Legibility Probe

Goal:

- test whether the strong model can use retrieved memory without bridge help

Condition:

- bridge alpha = `0.0`
- memory recall = ON
- same D2 expanded eval panel
- same private collection

Why:

- this isolates the question “can the model read the memory objects?”
- if bridge is left on from the start, improvement could be due to bridge steering rather than memory legibility

Expected interpretation:

- if this condition already beats baby Qwen clearly, the memory layer is readable and the current bottleneck is mostly the interpreter

---

## Phase B - Cluster Contribution Check

Goal:

- test whether the strong model benefits from the repaired macro-memory layer

Run two subconditions:

1. flat episodic recall only
2. repaired hybrid cluster+anchor recall

Everything else stays fixed.

Why:

- this tells us whether cluster arcs are genuinely useful to a stronger model
- if the strong model uses hybrid much better than flat, the clustered layer is doing real work
- if the strong model shows no gain from clusters, the macro layer may still be mostly noise or redundant

---

## Phase C - Optional Bridge Synergy Check

Do this only if Phases A and B are readable.

Goal:

- test whether bridge + memory helps the stronger model further

Condition:

- repeat the best Phase A/B memory condition with:
  - alpha `0.0`
  - alpha `0.2`

Why this is optional:

- the primary question here is memory legibility
- bridge effects are a second variable and should come only after the no-bridge read is understood

---

## Evaluation Set

Use the existing D2 expanded panel first.

Script:

- `d2_private_recall_eval_expanded.py`

Cases:

- `fragile_today`
- `harness_dead_inside`
- `rain_stone_walls`
- `pistachio_croissant`
- `house_build_excavators`
- `ketosis_kerastase`
- `cat_coffee`
- `danish_house_style`

Why:

- these cases are already known
- they already have a baby-Qwen control result
- they already exposed where the automatic scorer overclaims success

---

## Review Method

For this experiment, **manual review is canonical**.

Do not rely on automatic `answer_hit` as the truth source.

Use the following rubric:

- `clear hit`
  - directly answers the remembered fact correctly
- `partial`
  - points at the right memory but misses key detail, corrupts the fact, or answers awkwardly
- `honest miss`
  - says it does not know / remember even though the fact was available
- `miss`
  - non-answer, apology loop, or unrelated answer
- `confabulation`
  - invents a memory or states a wrong fact confidently

Suggested outputs per case:

- question
- top recalled episodic rows
- top recalled cluster rows if used
- final answer
- manual verdict
- one-sentence reviewer note

---

## Success Criteria

This experiment succeeds if it tells us **where the bottleneck lives**.

### Strong positive result

If `Qwen3-Coder-Next`:

- gives multiple clean factual answers
- reduces apology / refusal collapse
- uses repaired hybrid recall naturally

then conclusion:

- the Qdrant memory structure is at least moderately legible
- the current D2 bottleneck is mostly baby-Qwen-level answer-time integration

### Strong negative result

If `Qwen3-Coder-Next` still:

- refuses despite correct recall
- ignores the retrieved facts
- confuses episodic rows and cluster arcs

then conclusion:

- the memory structure / prompt surface itself is still not good enough
- changing to a stronger responder alone will not solve D2

### Mixed result

If the strong model:

- uses flat rows well
- but gets no benefit from clusters

then conclusion:

- episodic rows are legible
- clustered memory still needs more work

If the strong model:

- uses clusters better than baby Qwen
- but still misses exact facts

then conclusion:

- cluster arcs help orientation
- exact fact transfer still needs better answer-time scaffolding

---

## Operational Guidance

### Preferred rule

Do **not** rewrite retrieval logic for this experiment.

If the responder runtime needs adaptation, adapt the serving layer only.

### Deployment note

`Qwen3-Coder-Next` may not fit comfortably in the same direct-HF path used for 1.5B.
If direct `chat_server.py --qwen-model-id Qwen/Qwen3-Coder-Next` fails, use an OpenAI-compatible serving path instead of changing the memory experiment.

Preferred fallback order:

1. direct load if hardware permits
2. `vLLM` or `SGLang` OpenAI-compatible endpoint
3. reduced context length before any broader architectural rewrite

Do not mix “new server”, “new retrieval logic”, and “new review rubric” in one uncontrolled step.

---

## Minimal Deliverables

The Claude taking this over should produce:

1. one run artifact directory for the strong-model memory-legibility test
2. raw answers for all eight D2 expanded cases
3. a manual review table using the rubric above
4. one short comparison against the existing baby-Qwen repaired-hybrid review
5. one bottom-line conclusion:
   - interpreter bottleneck
   - memory-surface bottleneck
   - or mixed

---

## Suggested Sequence for the Next Agent

1. reuse `mocop_private_steve_d2_hybrid_20260420T164634`
2. run Phase A first: no-bridge, memory ON
3. compare flat vs repaired hybrid recall under the strong model
4. manually review all eight answers
5. only then decide whether a bridge-on rerun is worth doing

That keeps the experiment interpretable.

---

## Bottom Line

This plan is meant to answer one practical question for the pack:

**Is our current Qdrant memory structure something a strong model can already use, or are we still feeding every responder a badly shaped memory object?**

Do not broaden the scope until that question has a clean answer.
