# D2 Memory Repair Plan - 2026-04-18

## Purpose

This document combines the current D2 findings into one execution plan.

It is meant to replace scattered thread fragments like:

- "retrieval is wrong"
- "memory should feel natural"
- "Qdrant only finds fragments"
- "maybe this needs to be a math function"
- "maybe clustering is the missing layer"

The point is not to solve all of memory at once.
The point is to separate the current failure modes and sequence them correctly.

---

## Current Empirical State

### What is already true

- The bridge is not the primary blocker for honest continuity behavior.
- The 2x2 memory-conditioned eval already showed:
  - `bridge + memory` can route honestly
  - every other condition can still fail
- The `c0fde05` ranking patch materially improved selection quality.

### What the Steve D2 smoke established

Run:
- `run_reincarnation/steve_d2_smoke_20260418T201047/`

Settings:
- model: `Qwen/Qwen2.5-1.5B`
- alpha: `0.2`
- temperature: `0.0`
- fresh private namespace

Observed result:
- `retrieval_hit@3 = 2/2`
- `answer_accuracy = 0/2`
- `explicit_memory_language_rate = 0/2`

Interpretation:
- the system can now find the right autobiographical rows
- the model still does not reliably use them as direct, faithful memory during answer generation

This means D2 is no longer just a retrieval-ranking problem.
It is now a **memory integration** problem.

---

## Core Diagnosis

There are three different layers of failure. They must not be conflated.

### 1. Selection

Question:
- Can the system retrieve the correct memory row at all?

Current status:
- mostly improved
- `c0fde05` appears to have fixed a real part of the wrong-memory problem

### 2. Use

Question:
- Once the correct memory is retrieved, can Qwen turn it into a natural and faithful answer?

Current status:
- still failing

Observed Steve pattern:
- correct row found
- answer paraphrases vaguely, drops key detail, or falls back to non-recall behavior

### 3. Structure

Question:
- Is flat semantic retrieval over isolated memory rows the right substrate for continuity?

Current status:
- probably not

Flat retrieval is good at:
- finding similar fragments

Flat retrieval is weak at:
- recovering a story
- recovering an arc
- surfacing texture instead of scraps

This is where the HDBSCAN / clustered-memory idea belongs.

---

## Working Hypotheses

### Hypothesis A - The current recall block is too forensic

The recalled memory is currently surfaced in a way that reads more like evidence or diagnostics than recollection.

That is enough for:
- hit@k
- log inspection

That is not enough for:
- natural autobiographical completion

In plain terms:
- we are handing Qwen a case file, not a memory

### Hypothesis B - Natural memory use requires a latent path

Known knowledge does not feel retrieved because it is already integrated into the hidden state and completion dynamics.

Autobiographical memory may need the same shape:
- not just retrieved as text
- but converted into a latent influence on generation

This is the "math function" thesis.

### Hypothesis C - Qdrant rows alone are too thin

Even if direct cue-based recall works on row-level facts, continuity and presence likely need more than nearest-neighbor fragments.

We probably need layered memory:
- episodic fragments
- clustered meso-memory
- narrative arc / macro-memory

This is the HDBSCAN / story-layer thesis.

---

## Execution Order

The sequence matters. This plan is intentionally narrow-first.

### Phase 0 - Freeze the current baseline

Goal:
- preserve the current D2 result as the control condition

Artifacts:
- `D2_RECALL_STATUS_2026-04-17.md`
- `run_steve_d2_private_recall.ps1`
- `run_reincarnation/steve_d2_smoke_20260418T201047/`

Reason:
- every future change must be evaluated against the same explicit D2 harness
- no moving target

Success condition:
- baseline remains reproducible

---

### Phase 1 - Fix answer-time memory use

Goal:
- improve answer faithfulness without changing ranking again

What stays fixed:
- retrieval query
- ranking
- eval prompts
- Steve harness

What changes:
- only the recall-to-answer surface

Prototype ladder:

1. **Current mode**
   - existing recollection block

2. **Factual-anchor mode**
   - strip gate diagnostics
   - put the concrete autobiographical fact first
   - example:
     - "Earlier today you said you were awake until 2 AM and felt fragile."

3. **Narrative-recall mode**
   - same fact, but framed like recollection instead of evidence
   - example:
     - "I'm remembering that earlier you said you were awake until 2 AM and felt fragile today."

Why this phase comes first:
- the Steve run already proved selection works better
- the next cheapest test is whether format / framing is the blocker

Success condition:
- `retrieval_hit@3` stays high
- `answer_accuracy` improves
- direct memory use becomes more faithful

Failure meaning:
- if answer use still fails despite cleaner recall formatting, then the problem is probably not just presentation

2026-04-18 Steve update:

- `full` -> `retrieval_hit@3 = 2/2`, `answer_accuracy = 0/2`, `explicit_memory_language_rate = 0/2`
- `answer_first` -> `retrieval_hit@3 = 2/2`, `answer_accuracy = 0/2`, `explicit_memory_language_rate = 1/2`
- `answer_only` -> `retrieval_hit@3 = 2/2`, `answer_accuracy = 1/2`, `explicit_memory_language_rate = 2/2`

What that means:

- answer framing is a real control lever
- reducing the recollection block to direct remembered facts helps
- the remaining failure is factual specificity, not total recall collapse
- stay in Phase 1 a little longer before escalating to latent-memory injection

---

### Phase 2 - Prototype latent memory integration

Goal:
- test the thesis that memory must enter generation as a latent influence, not just a pasted recollection

Minimal prototype:
- retrieve top-1 or top-2 memory anchors
- embed the factual anchor text
- compress it to a small memory vector
- inject that vector into Qwen before generation

Candidate forms:
- one virtual token
- one tiny additive hidden-state bias
- one minimal adapter-state perturbation

What stays fixed:
- same D2 retrieval
- same prompts
- same eval

Question:
- does latent integration improve answer faithfulness where text recall alone fails?

Success condition:
- better `answer_accuracy`
- no contamination on control prompts
- no collapse into benchmark-prose or false-memory claims

Failure meaning:
- if latent integration also fails, the issue may be deeper than recall formatting vs. latent insertion

---

### Phase 3 - Add structured memory above flat rows

Goal:
- move from fragment retrieval toward story / arc retrieval

This is where HDBSCAN belongs.

Important:
- this phase does **not** replace the explicit row-based D2 path
- it complements it

Proposed memory layers:

1. **Fragment layer**
   - current Qdrant episodic rows
   - best for exact cue-based recall

2. **Cluster layer**
   - HDBSCAN over episodic memories
   - best for meso-scale story recovery and recurring themes

3. **Arc layer**
   - cluster summaries / macro-memory
   - best for longer continuity and identity-level recall

Operational rule:
- explicit probes stay fragment-first
- ambient / continuity prompts can use:
  - row
  - plus cluster summary
  - plus neighboring detail

Success condition:
- compared to flat retrieval, cluster-assisted recall improves:
  - continuity
  - ambient presence
  - "we already did this" recovery
  - narrative coherence

Failure meaning:
- if clustering adds noise or generic summaries without behavioral benefit, keep it off the critical path

---

### Phase 4 - Revisit retrieval mode itself

Goal:
- move beyond text-only semantic retrieval

This is the old `G2` idea:
- semantic similarity
- plus latent / state similarity
- optionally plus cluster support

Shape:
- retrieve by text
- rerank by hidden-state or Mamba-state similarity

This should only happen after Phase 1 and likely after Phase 2.

Reason:
- right now we already know the system can find the correct row
- the bottleneck is use, not only search

Success condition:
- combined retrieval beats semantic-only on identity, continuity, and mode-sensitive recall

---

### Phase 5 - Ambient recall after D2 is stable

Goal:
- make memory-conditioned chat the default operating mode

Constraint:
- ambient recall should stay opt-in until explicit D2 recall is behaviorally solid

Why:
- broadening memory exposure while answer-time use is still unreliable increases contamination risk

Required preconditions:
- explicit D2 recall behavior is stable
- control prompts remain clean
- `rr_10` remains honest under memory-conditioned mode
- Hurtig conditions remain satisfied

---

## Immediate Next Build

The next build should be **Phase 1, not a full architecture rewrite**.

Concrete task:
- implement recall formatting variants for explicit D2 probes
- run the exact same Steve D2 harness
- compare answer fidelity against the current baseline

Reason:
- cheapest test
- highest information gain
- keeps the system narrow and falsifiable

---

## What Not To Do

Do not do these out of order:

- do not reopen broad bridge-architecture work as if D2 were solved
- do not claim ambient recall fixes D2 before explicit cue-based answer use is clean
- do not treat HDBSCAN as a substitute for answer-time memory integration
- do not keep tweaking ranking forever if the correct row is already being selected
- do not call the current problem "retrieval" alone when the evidence now says "retrieval + use"

---

## Decision Rules

### If Phase 1 works

- prioritize cleaner recollection formatting / answer integration
- keep latent integration as optimization or strengthening path

### If Phase 1 fails but Phase 2 works

- memory likely needs a latent insertion path to feel natural
- prioritize the smallest trainable or rule-based latent memory interface

### If Phases 1 and 2 both fail

- revisit whether the current recalled payload itself is the wrong object
- that pushes clustering / hierarchical memory and retrieval mode changes up in priority

### If Phase 3 works

- adopt layered memory:
  - fragments for exact recall
  - clusters for continuity
  - summaries for arc

---

## Short Version

If the whole plan must be compressed to one line:

**First make recalled memory usable, then make memory structured.**

Operationally that means:

1. freeze current D2 baseline
2. improve recall-to-answer integration
3. prototype latent memory injection if needed
4. add HDBSCAN cluster memory as a higher-level layer
5. only then broaden into ambient/default mode

---

## Canonical Next Step

Build and test **Phase 1: answer-time memory use** on the existing Steve D2 harness.

That is the cheapest experiment that cleanly distinguishes:
- "retrieval is still wrong"
from
- "memory is found but not yet naturally integrated"
