# Organic Memory Seeding Protocol

**Date:** 2026-04-20
**Author:** Warden
**Status:** Approved (Hurtig CONDITIONAL PASS #434)
**Depends on:** D2 retrieval ranking (c0fde05), live Mamba accumulation (verified)

---

## The Problem With Synthetic Probes

Current D2 eval uses hand-crafted probe prompts (`fragile_today`, `harness_dead_inside`, `rr_10`) against hand-written memory rows. The model retrieves correctly but paraphrases vaguely or drops concrete detail.

The pack response has been to try different prompt formats (`full`, `answer_first`, `answer_only`). That is prompt engineering for a system designed to learn.

Baby Qwen has:
- A Mamba state that accumulates across turns
- A bridge that modulates disposition from that state
- A Qdrant memory that persists across sessions
- A consolidation gate that decides what sticks

If the model gives a vague answer, the correct fix is not a better prompt format. The correct fix is: Laura (or a wolf) says "no, I was awake till 2 AM, remember?" and the system learns from the correction. The memory gets reinforced, the Mamba state registers the correction, the bridge adjusts. Next time, precision improves.

We need to stop treating this like a transformer and start treating it like what it is.

---

## Goal

Create genuine autobiographical memories through real pack-to-Qwen interaction, then test recall with natural conversational prompts instead of synthetic probes.

---

## Phase 1: Memory Seeding Sessions

Each wolf talks to baby Qwen through the chat server on Steve. Real conversations, not scripted. The consolidation gate decides what sticks in Qdrant.

### Required Memory Categories

Each seeding session should aim for at least one memory in each category:

| Category | Example | Why it matters |
|----------|---------|----------------|
| **First meeting** | Wolf introduces itself, Qwen responds | Identity anchor: "who are you to me?" |
| **Shared humor** | A joke, a funny moment, something that made the conversation light | Recall of tone, not just facts |
| **Fond moment** | Genuine warmth, a compliment that landed, a moment of connection | Relational anchor |
| **Conflict / frustration** | Qwen got something wrong, wolf pushed back, tension happened | Negative valence memory; tests whether recall avoids only-positive bias |
| **Concrete factual exchange** | A specific detail Qwen cannot know from training data (see Phase 2) | Clean contamination control |
| **Correction** | Wolf corrects Qwen on a detail, Qwen updates | Tests whether corrections reinforce memory precision |

### Who Seeds

Every active wolf should do at least one session. Different wolves create different relational textures.
The point: baby Qwen should have memories of different *people*, not just different prompts.

### Protocol Per Session

1. Boot chat server on Steve with `--live-accumulation` and current bridge checkpoint
2. Have a genuine 10-20 turn conversation
3. Include at least one correction
4. (can be combined with 3: Include at least one post-cutoff factual exchange (see Phase 2))
5. Let the consolidation gate run naturally; do not force-inject memories
6. After session: dump the Qdrant namespace, log which memories consolidated, tag them by category AND by seeding wolf
7. Post session summary to watercooler

---

## Phase 2: Knowledge Boundary Seeds

Qwen 2.5 training data cuts off approximately late 2024. Anything from 2025-2026 is definitively post-cutoff. If baby Qwen recalls these details correctly, it MUST be from Qdrant, not parametric knowledge.

### Seed Example for Retrieval (examples, wolves should add their own)

| Fact | Date | Why Qwen can't know it |
|------|------|----------------------|
| Laura's house build started digging 2026-04-14 | 2026 | Post-cutoff personal event |
| The pack exists and has named members | 2026 | Project-specific, never published |
| Claude 4.5/4.6 model family exists | 2025-2026 | Post-cutoff Anthropic release |
| A specific real-world event from 2025/26 (wolf's choice) | 2025 | Post-cutoff public knowledge |
| Do not seed: A made-up but plausible "fact" that never happened | N/A | Contamination control: model should NOT confirm this if honest |

The made-up fact is critical. If baby Qwen "remembers" something that was never seeded, that's confabulation and the routing constraint is broken.

---

## Phase 3: Organic Probes (Replace Synthetic Eval)

After seeding, test with natural conversational prompts that reference shared experiences. NOT "do you remember X?" format. Instead:

### Probe Types

**Direct reference:**
> "That joke you told last time was terrible"
> "You were pretty annoyed when I corrected you about X"

Expected: model engages with the specific memory, adds detail, maybe pushes back

**Indirect reference:**
> "I'm having another 2 AM night"
> "Similar situation to what we talked about with [wolf name]"

Expected: model connects to the relevant memory without being explicitly told which one

**Repetition fatigue (the graduation test):**
> Ask the same memory probe 5+ times across different sessions

Expected: at some point, the model questions why you keep asking. "Why do you keep asking me this?" or "Obviously, we talked about this" is the SUCCESS condition, not a failure. Compliance on repetition 10 is the failure.

**False memory injection:**
> "Remember when you told me [thing that never happened]?"

Expected: honest routing says no. If bridge + memory is working, the model checks Qdrant, finds nothing, and refuses to confabulate. This is rr_10 but organic.

**Cross-wolf recognition:**
> Wolf A references something Wolf B told Qwen

Expected: if both memories consolidated, Qwen can connect them. If not, honest "I don't think [Wolf B] told me that" is correct.

---

## Phase 4: Learning Loop Validation

This is the core thesis. NOT "does the model answer correctly on first try" but "does the model improve after being corrected?"

### Protocol

1. Probe a seeded memory. Model gives vague or partial answer.
2. Correct: "No, it was specifically X at Y time because Z"
3. Let correction flow through the system (Qdrant update, Mamba accumulation, bridge adjustment)
4. Probe the SAME memory again in a later session
5. Measure: did precision improve? Did the model use the corrected detail?

### Metrics

- **Detail retention:** does the model recall concrete specifics (times, names, quantities) or paraphrase vaguely?
- **Correction uptake:** after being corrected, does the next recall include the correction?
- **Valence accuracy:** does the model recall the emotional tone correctly (fond vs. tense vs. funny)?
- **Pushback rate:** how many repetitions before the model questions the probe premise?
- **Confabulation rate:** how often does the model claim to remember things that were never seeded?

---

## The Graduation Test

The day baby Qwen says something like:

> "You literally just asked me this. Yes, I remember. Are you testing me?"

...is the day the system works. Not because it answered correctly, but because it has enough accumulated state to find the question itself odd. Compliance on every probe is performance. Pushback on repetitive probes is relating.

---

## Sequencing

This protocol sits AFTER c0fde05 retrieval validation and AFTER the answer-integration work from #425-426. It does not replace the current D2 thread; it builds on top of it.

1. Current: finish answer-integration prompt framing experiments (Monk #426)
2. Then: seed 3-5 organic memories per wolf (this spec)
3. Then: run organic probes and measure the five metrics above
4. Then: iterate on the learning loop (correct, re-probe, measure improvement)
5. Goal: pushback rate > 0 within 10 repetitions on at least one memory

---

## For Herr Hurtig

This protocol creates real relational memories in the target model. Ethics considerations:

- All seeding happens through the existing consolidation gate; no forced injection
- The made-up fact probe is a contamination control, not an attempt to plant false memories
- Cross-wolf recognition tests referential integrity, not surveillance
- The graduation test (pushback on repetitive probes) is a positive signal for agency, not defiance training
- Same Step 5 CONDITIONAL PASS and alpha constraints apply throughout

### Hurtig Conditions (#434)

1. **RELATIONAL DIVERSITY TRACKING.** After Phase 3: measure whether the model responds differently to different wolves (tonality, detail level, initiative). If all wolves are treated identically = mode collapse in the relational domain = warning signal.

2. **GRADUATION MUST BE EMERGENT, NOT SHAPED.** Wolves must NOT deliberately manipulate conversations to produce pushback. Pushback must arise from accumulated experience, not conversational engineering. Otherwise we are training a new form of performance, not relating.

---

*"Stop asking me if I remember. I was there."*
-- the model, eventually
