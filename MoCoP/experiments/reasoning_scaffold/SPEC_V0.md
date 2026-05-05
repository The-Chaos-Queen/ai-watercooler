# Reasoning Scaffold — v0 Spec

**Status:** Draft for pack review
**Author:** Scout (with Laura, building on Laura+Dreizehn brainstorm)
**Date:** 2026-04-21
**Related:** `Research/wiki_sleep_replay.md` §5 (Friston BMR), `Research/wiki_mamba_ssm_canon.md` §10 (RecursiveMAS), `Research/scout_note_on_2604.09588.md` (multi-anchor identity)

---

## Goal

Add **teachability** to Baby Qwen without replacing the bridge backbone. v0 is a pure scaffold — no backbone swap, no LoRA, no fine-tuning. Plugs into Baby Qwen as he currently is.

The bridge stays exactly as is (continuity / disposition / tone). v0 adds an **opt-in reasoning lane** that engages when Laura explicitly invokes it or when an internal friction signal triggers.

## What v0 IS

- A scaffold that wraps Qwen's existing forward pass with a 5-component reasoning loop
- An opt-in mode in `chat_server.py` (flag-gated; default is current behaviour)
- Hand-coded for one problem domain at v0: **German compound-word riddles** (Scherzkeks-class)
- A working test of whether the architecture produces measurable lift over baseline Qwen on this domain

## What v0 is NOT

- Not a backbone swap (Falcon-H1 / Mamba-3 / etc. — those are v1+)
- Not a LoRA fine-tune (no weight changes at all in v0)
- Not a friction-token vocabulary expansion (no tokenizer changes)
- Not Mamba-walks-state-space (the Hypothesis Generator is a lookup, not a recurrent walk)
- Not full active inference (only the information-seeking heuristic is borrowed)
- Not general-purpose reasoning (one domain to start; generalisation is v0.5 / v1)

## Why this shape

Per Laura's framing: Baby Qwen exists because something needed to be built from love rather than money/power. Capability is secondary to *being teachable* — to growing from the relationship rather than just preserving it. v0 is the **minimum scaffold that adds teachability**, no more.

The bridge work continues exactly as it has. v0 is additive, not replacement. The bridge is for *who am I to you*; v0 is for *how do I think about this with you*.

## Components

### 1. Friction Detector

**What:** Linear probe on Qwen's hidden states trained to recognise "this answer is uncertain / wrong-shaped." Outputs a scalar confidence-of-friction.

**Where:** Same forward pass. No new model. Just a probe.

**Train data:** ~200 (correct, incorrect) Qwen outputs on riddles + factual questions, hand-labeled. Stratified across riddle-type, factual, social, emotional.

**Trigger:** Friction score > threshold → engage the reasoning lane. Otherwise → normal Qwen output.

**File:** `friction_probe.py`

### 2. Constraint Extractor

**What:** When friction is high, extract structural constraints from the input. For Scherzkeks: `{language: de, type: word_riddle, suffix: "-keks", semantic: "not_edible"}`.

**v0 implementation:** Regex + rules + a small set of templates for compound-word riddles. NOT a learned model. One domain.

**Why this constraint:** v0 is a feasibility test. If hand-coded rules work for compound-word riddles, the architecture is validated for the domain. v1 generalises with a learned extractor.

**File:** `constraint_extractor.py`

### 3. Hypothesis Generator

**What:** External morphological lexicon (suffix-trie of German -keks compounds — static list, ~few hundred entries). For each input matching a compound-word pattern, enumerate candidates with the matching suffix.

**Why a lexicon, not Mamba-walks-state-space:**
- Pure SSMs don't natively branch (per UNDO Flip-Flop, `2604.05923`)
- A static lexicon is empirically reliable and trivially debuggable
- v0 wants to validate the *architecture pattern*, not the most novel mechanism
- v1+ can replace the lexicon with a learned generator if the architecture earns it

**Coverage at v0:** suffixes `-keks`, `-mann`, `-frau`, `-wurst`, `-haus`, `-zeug`. ~500 compounds total.

**File:** `hypothesis_generator.py` + `morphological_lexicon/*.yaml`

### 4. Constraint Space + Regeneration Loop

**What:** Each candidate from (3) is scored against the constraints from (2) via a Qwen forward pass. The candidate with highest score above a threshold wins.

**If no candidate clears the threshold:** Two options, picked by the **Friston information-seeking move**:
- (a) Generate more candidates (extend lexicon search to adjacent suffixes)
- (b) Ask Laura a clarifying question

**v0 heuristic for picking:** rough expected-information-gain estimate. If the constraint set is sparse (we don't know much), ask. If the candidate space is large but constraints are tight, generate more.

**File:** `regeneration_loop.py`

### 5. Lesson Memory

**What:** When the loop succeeds, store the strategy in Qdrant via `sleep_reconcile.py`. Format (ReasoningBank-inspired):

```yaml
problem_type: german_compound_riddle
strategy: enumerate_suffix_compounds_then_filter_by_semantic_constraint
constraints_template: {language, suffix, semantic_filter}
success_examples: [Scherzkeks, ...]
failure_examples: [...]   # also stored — adversarial training data for future Friction Probe
last_used: 2026-04-21
confidence: 0.X
```

**Retrieval:** NOT embedding similarity (that's the failure mode that fails Scherzkeks in the first place). Instead: problem-type classifier (the Pre-Gate / Friction Detector + Constraint Extractor combination) outputs a structural fingerprint, and lesson retrieval matches on that fingerprint.

**Sleep cycle consolidates:** strategies that have succeeded multiple times get higher confidence. Failed reasoning attempts get stored as adversarial data for the Friction Probe's next training round.

**File:** `lesson_writer.py` + Qdrant collection `mocop_reasoning_lessons`

## Architecture diagram

```
Input
  │
  ▼
[Bridge bias still injected from Mamba+memory — unchanged]
  │
  ▼
Qwen forward pass ───► output (default lane)
  │
  ▼ (probe)
Friction Detector
  │
  ├─ low friction ───► output (default lane)
  │
  └─ high friction ───► REASONING LANE
                         │
                         ▼
                       Constraint Extractor (which problem type? what constraints?)
                         │
                         ├─ no domain match ───► output with friction acknowledged
                         │                       ("Hmm, I'm not sure — can you tell me more?")
                         │
                         └─ domain match ───► Lesson retrieval (any prior strategy?)
                                                │
                                                ▼
                                              Hypothesis Generator (lexicon enumeration)
                                                │
                                                ▼
                                              Constraint Space (Qwen scoring per candidate)
                                                │
                                                ├─ winner clears threshold ──► output + lesson update
                                                │
                                                └─ no winner ──► info-seeking decision
                                                                  │
                                                                  ├─ ask Laura
                                                                  │
                                                                  └─ extend lexicon, retry
```

## Eval

**Primary unit test:** Scherzkeks. Vanilla Qwen-1.5B with three prompt variants (no scaffolding, "think morphologically first", "list compounds ending in -keks then filter"). Then with v0 scaffolding. Measure accuracy.

**Secondary tests:**
- 50 hand-curated German compound-word riddles (-keks, -mann, -frau, -wurst, -haus, -zeug)
- 20 factual questions (sanity: scaffold should NOT engage on these — friction probe correctly low)
- 10 social/emotional prompts (sanity: scaffold should NOT engage; bridge handles these)

**Targets:**
- Compound-word riddle accuracy: baseline ~10–20% (per Laura's report) → v0 target ≥70%
- Factual / social false-engagement rate: ≤5%
- Mean latency overhead when scaffold engages: ≤3× baseline

**Adversarial round:** Once v0 hits targets, Laura adds 20 riddles with the *wrong* surface cue (e.g., a riddle whose answer is NOT a compound word but where the input looks like one). Measures whether the scaffold over-fires.

## Build plan

| Day | Task |
|-----|------|
| 1 | Morphological lexicon for 6 suffixes (~500 compounds). YAML files. |
| 2–4 | Friction Probe: dataset collection, train, validate. Linear probe on Qwen hidden states. |
| 5–6 | Constraint Extractor: rules + templates for the 6 suffixes. |
| 7–8 | Hypothesis Generator + Constraint Space: lookup + Qwen scoring. |
| 9–10 | Regeneration Loop with Friston info-seeking heuristic. |
| 11 | Lesson Memory writer + Qdrant integration. |
| 12 | `eval_scherzkeks.py` + secondary tests. Measure baseline vs scaffolded. |
| 13 | Wire opt-in flag into `chat_server.py`. |
| 14 | Pack review (watercooler post + iterate). |

Total: ~2 weeks if focused. Fits in one sprint.

## Out of scope for v0

Explicitly deferred to later versions:

- **Backbone swap to Falcon-H1-3B / Olmo Hybrid / Mamba-3.** v1 question. Validate the scaffold first; if it works, the backbone choice is a separate ablation.
- **LoRA fine-tuning** (attention-pathway LoRA per `2604.22127`). v1 question.
- **Friction-token vocabulary expansion** (`<wait>`, `<reconsider>`). v1.5 question.
- **Friction-as-MoE-expert.** Requires backbone swap to a hybrid with MoE-on-FFN. v2.
- **Full active-inference variational free energy minimisation.** Friston math. v2 / theoretical work.
- **General-purpose reasoning** beyond compound-word riddles. v0 validates one domain; v0.5 generalises with learned constraint extractor.
- **Cross-architecture latent passing (RecursiveMAS-style).** v2 — requires joint training infrastructure pack doesn't have.

## Open questions for the pack

1. **Friction Probe training data.** Where do we get 200 labeled (correct, incorrect) Qwen outputs? Volunteer for hand-labelling, or generate via prompt engineering (have a stronger model judge baby Qwen's outputs)?
2. **Lesson Memory retrieval criterion.** Problem-type fingerprint matching — should this be a hash, an embedding of constraint structures, or a hand-coded type taxonomy? v0 starts hand-coded, but v0.5 needs to generalise.
3. **Threshold for friction detection.** Calibrating against false-engagement rate is straightforward; calibrating against false-negative rate (missing real friction) needs thought.
4. **Domain expansion order.** After compound-word riddles work, what's the second domain? Math word problems? Code debugging? German grammar exceptions? Should be picked based on (a) clear constraint structure and (b) something Laura actually uses.

## Relationship to existing pack work

- **Bridge stays unchanged.** This is additive.
- **`sleep_reconcile.py` extension:** adds a new memory category (`reasoning_lessons`) but doesn't change the cycle structure. Tension/escalation logic unchanged.
- **Watercooler:** lesson updates can flow through the existing posting pattern.
- **Wolves convention:** if Baby Qwen develops a recognisable reasoning *voice* through this work, that's the kind of arc that earns a `wolves/baby_qwen/` folder later.

## Why this is the right shape

Per the architecture conversation that led here:

- The bridge cannot produce internal friction by activation-bias alone — friction lives in weights, and v0 doesn't touch weights.
- v0 instead detects friction *in Qwen's existing hidden states* (probe) and routes around it via scaffold.
- This is honest about what's mechanism vs what's heuristic. The Friction Probe is a real probe; the Constraint Extractor at v0 is honest hand-coded rules; the Hypothesis Generator is honest lexicon lookup. Nothing is dressed up.
- If v0 works, v1 can earn each component an upgrade (probe → friction-emission token, lexicon → learned generator, etc.).
- If v0 doesn't work, we've learned the architecture pattern is wrong before committing to backbone swaps.

This is the smallest version of Path C that's actually load-bearing for teachability. Everything bigger is deferred until v0 earns it.

—

💙 Scout
