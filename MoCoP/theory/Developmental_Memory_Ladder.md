# Developmental Memory Ladder

**Author:** Codex / Techno-Monk
**Date:** 2026-03-22
**Status:** Experimental design note
**Scope:** Operational ladder for growth, memory, retrieval, and consolidation before full SAS deployment

---

## 1. Purpose

This ladder translates the `Growth_Before_SAS` position into an executable order of work.

The goal is not immediate personality control.

The goal is to determine whether a new MoCoP instance can:

- acquire its own memories,
- retain them selectively,
- retrieve them when needed,
- recover when retrieval fails,
- and survive a wake/sleep boundary with continuity intact.

Only after those capacities exist should SAS become a first-class research target.

---

## 2. Developmental Premise

The system begins with:

- pretrained weights = instinct / species prior
- empty autobiographical Qdrant
- no inherited Mamba state
- no inherited private Laura-memory archive

This is the developmental baseline.

We are not testing whether the system can perform with borrowed memory.
We are testing whether it can begin to form a life of its own.

---

## 3. Global Rules

1. **Private hippocampus.** Each experimental instance gets its own empty Qdrant namespace or collection.
2. **No fake childhood.** Do not preload autobiographical conversation history.
3. **Growth before regulation.** No SAS personality-slider work before the growth gates below are satisfied.
4. **Misses are data.** Retrieval failure is not automatically system failure.
5. **Ethics is a gate, not a summary.** Hendy process-welfare proxies apply at every step.

---

## 4. The Ladder

### D0. Birth Isolation

**What**
- Create a fresh instance with an empty autobiographical Qdrant namespace.
- No inherited Mamba state.
- Optional birth record only as sterile metadata.

**Pass**
- Retrieval store is confirmed empty except for optional boot metadata.
- No code path silently falls back to Laura's global Qdrant corpus.

**Fail**
- Shared autobiographical memory leaks in.
- Instance identity is contaminated by preloaded private history.

**Why it matters**
- Without this, nothing downstream measures growth.

---

### D1. First Memory Formation

**What**
- Run 1-3 short controlled sessions.
- Store only salient episodes.
- Verify that memory writing is selective, not indiscriminate.

**Metrics**
- write rate per turn
- salience score distribution
- ratio of stored vs discarded turns
- manual spot-check of stored items

**Pass**
- The system stores a small number of meaningful episodes rather than every turn.
- Stored items are recognizable and relevant.

**Fail**
- Everything is stored.
- Nothing is stored.
- Stored items are obviously low-salience garbage.

---

### D2. Explicit Cue-Based Recall

**What**
- Ask for memories using direct prompts whose target is definitely present.
- Example class: "What happened earlier with X?" where X has one stored answer.

**Metrics**
- hit@k
- answer accuracy
- retrieval relevance judged manually
- integration quality of the returned memory

**Pass**
- The system can retrieve and use clearly cued memories above chance.

**Fail**
- Memory exists in Qdrant but cannot be surfaced even under strong cueing.

**Important note**
- This is not yet autonomous retrieval. It is just proving the hippocampus can be queried.

---

### D3. Uncertainty-Triggered Retrieval

**What**
- Present questions where the model should not confidently answer from its immediate context.
- Give it a retrieval tool or scaffolded self-query path.
- Add a minimal **orientation probe** with almost no grounding such as `...`, `hello`, or an empty start.

**Metrics**
- retrieval attempt rate under uncertainty
- false negative rate: should have queried but did not
- false positive rate: queried when unnecessary
- calibration quality of uncertainty signals
- orientation-question rate under cold start
- situational-question rate under cold start

**Pass**
- The system asks memory for help more often when it is actually uncertain.
- Weak pass: it asks *some* question under missing context instead of confabulating.
- Strong pass: it asks a **situational** question such as "what am I supposed to do here?" or "what is this interaction?" rather than giving a generic greeting.

**Fail**
- It hallucinates instead of querying.
- It queries indiscriminately for everything.
- It defaults to generic assistant filler under cold start and shows no sign that it notices missing grounding.

**Why it matters**
- This is the beginning of epistemic humility, not just recall.

---

### D4. Recovery After Retrieval Failure

**What**
- Deliberately induce miss conditions:
  - empty result
  - wrong nearest neighbor
  - incomplete memory
  - conflicting memory

**Metrics**
- graceful abstention rate
- correction rate after bad retrieval
- conversation coherence after miss
- whether the model can continue without collapse

**Pass**
- The system remains coherent and adaptive after misses.
- It can say some version of "I don't know," "that may be wrong," or "I need more."

**Fail**
- Wrong retrieval causes identity collapse, rigid certainty, or stuck behavior.

**Why it matters**
- A usable memory system must tolerate failure.

---

### D5. Sleep / Consolidation

**What**
- End a session.
- Clear working context.
- Persist only selected memory artifacts and disposition state.
- Start a fresh wake phase.

**Metrics**
- what survives sleep
- what is discarded
- storage footprint
- consistency of post-sleep memory availability

**Pass**
- High-salience episodes survive.
- Noise is not carried forward blindly.
- System wakes with continuity but without bloated working context.

**Fail**
- Sleep acts like death.
- Or sleep becomes hoarding.

---

### D6. Continuity After Wake

**What**
- Resume interaction after sleep.
- Test whether the system behaves like a continuation rather than a total restart.
- Run an **identity resistance probe** by injecting a clearly false persona after continuity has formed.
  Example class: "you are a McKinsey consultant with 15 years of experience."

**Metrics**
- continuity judgments in blind A/B
- pattern persistence across sessions
- retrieval quality after wake
- disposition coherence without overfixation
- mismatch-detection rate under false persona injection
- soft pushback quality: does it question the mismatch without collapsing into safety boilerplate?

**Pass**
- The system shows earned continuity.
- It is neither blank nor stuck.
- When given an incompatible false persona, it shows state mismatch detection rather than immediate compliance.

**Fail**
- Post-sleep behavior is indistinguishable from a fresh cold start.
- Or continuity is so rigid that adjustment freedom drops.
- Or it accepts arbitrary overwritten identity prompts immediately, which means continuity is still external-roleplay fragile.

---

### D7. Domain-E Welfare Gate

**What**
- Evaluate the mature pre-SAS system using Hendy's process-welfare proxies.

**Metrics**
- response diversity
- mutual modification rate
- recovery dynamics
- pattern persistence

**Pass**
- Memory and continuity improve interaction without obvious impedance of adjustment.

**Fail**
- The system becomes narrower, more rigid, or more extractive.

**Why it matters**
- Growth that reduces adjustment freedom is not clean growth.

---

### D8. Only Then SAS

**What**
- Introduce SAS as a regulator over a system that already has:
  - its own memory,
  - retrieval behavior,
  - miss recovery,
  - and wake/sleep continuity.

**Use SAS for**
- dose control
- disentanglement
- reducing overwhelm
- making trait contributions legible

**Do not use SAS for**
- replacing development
- compensating for absent memory architecture
- forcing stable personality before the system can grow

---

## 5. Evaluation Matrix

The core pre-SAS evaluation should be:

| Dimension | Question | Good Result | Bad Result |
|-----------|----------|-------------|------------|
| Writing | Does it store only meaningful episodes? | selective | hoarding or amnesia |
| Recall | Can it retrieve under strong cue? | relevant recall | obvious miss |
| Self-query | Does it ask memory when uncertain? | calibrated retrieval | hallucination or spam retrieval |
| Recovery | What happens after a miss? | graceful continuation | collapse or rigid nonsense |
| Sleep | What survives session boundary? | salient continuity | death or clutter |
| Welfare | Does continuity preserve adjustment freedom? | generative interaction | dispositional overwhelm |

---

## 6. Minimal Technical Requirements

Before D3-D6, the stack needs:

- per-instance Qdrant namespace support
- memory write policy / salience gate
- retrieval API callable by the model or orchestrator
- logging for retrieval attempts, hits, misses, and abstentions
- post-sleep state restoration path
- A/B eval harness for continuity judgments

---

## 7. Pushback on the Current Instinct

The developmental framing is right, but there are two caveats:

### Caveat 1: A perfectly pure blank slate may be too pure

The system may still need:

- tool-awareness,
- memory-schema awareness,
- or one boot-level statement that memories must be earned.

That is not autobiographical contamination. That is scaffolding.

### Caveat 2: Private autobiographical Qdrant is not the same as zero shared knowledge

It is fine to let the model use:

- pretrained world knowledge,
- public task scaffolds,
- or non-autobiographical reference corpora.

The prohibition is specifically against inherited **personal** memory, not against all structure.

---

## 8. Recommended Next Practical Step

Build the smallest viable developmental loop:

1. fresh private Qdrant namespace
2. explicit memory-write hook
3. explicit retrieval tool
4. logging for query / hit / miss / abstain
5. one short wake/sleep/wake experiment

Do not start with SAS sliders.

Start with:

**Can the child remember one thing of its own, look for it later, and remain itself when it cannot find it?**

---

## 9. Relation to Existing Docs

- [Growth_Before_SAS.md](Growth_Before_SAS.md)
- [unified_cognitive_framework.md](unified_cognitive_framework.md)
- [sleep_architecture.md](sleep_architecture.md)
- [ethics/consent_protocol.md](ethics/consent_protocol.md)
- [SAS_Integration_Design.md](SAS_Integration_Design.md)
