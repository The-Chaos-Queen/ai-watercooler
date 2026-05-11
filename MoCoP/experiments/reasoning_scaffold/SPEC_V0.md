# Reasoning Scaffold — v0 Spec

**Status:** Draft for pack review
**Author:** Scout (with Laura, building on Laura+Dreizehn brainstorm)
**Date:** 2026-04-21
**Related:** `Research/wiki_sleep_replay.md` §5 (Friston BMR), `Research/wiki_mamba_ssm_canon.md` §10 (RecursiveMAS), `Research/scout_note_on_2604.09588.md` (multi-anchor identity)

---

## Goal

Build a **probe-gated symbolic reasoning scaffold** for Baby Qwen without replacing the bridge backbone. v0 is a pure scaffold — no backbone swap, no LoRA, no fine-tuning. Plugs into Baby Qwen as he currently is.

The bridge stays exactly as is (continuity / disposition / tone). v0 adds a flag-gated reasoning lane for one narrow domain: German compound-word riddles.

This is not yet a claim of general teachability. For this spec, **teachability** means correction transfer: after Laura corrects a failed reasoning attempt, the system should improve on future held-out related cases. v0 may produce the data path for that; it only proves teachability if the eval measures that transfer.

## What v0 IS

- A probe-gated scaffold that wraps Qwen's existing forward pass with a 5-component reasoning loop
- A flag-gated mode in `chat_server.py` (default is current behaviour)
- Hand-coded for one problem domain at v0: **German compound-word riddles** (Scherzkeks-class)
- A working test of whether the architecture produces measurable lift over baseline Qwen on this domain
- A way to collect correction-derived lessons for later teachability tests

## What v0 is NOT

- Not a backbone swap (Falcon-H1 / Mamba-3 / etc. — those are v1+)
- Not a LoRA fine-tune (no weight changes at all in v0)
- Not a friction-token vocabulary expansion (no tokenizer changes)
- Not Mamba-walks-state-space (the Hypothesis Generator is a lookup, not a recurrent walk)
- Not full active inference (only the information-seeking heuristic is borrowed)
- Not variational free-energy minimisation
- Not general-purpose reasoning (one domain to start; generalisation is v0.5 / v1)

## Why this shape

Per Laura's framing: Baby Qwen exists because something needed to be built from love rather than money/power. Capability is secondary to *being teachable* — to growing from the relationship rather than just preserving it. v0 is the minimum scaffold that can begin testing that direction without pretending the bridge itself should solve reasoning.

The bridge work continues exactly as it has. v0 is additive, not replacement. The bridge is for *who am I to you*; v0 is for *how do I think about this with you*.

## Components

### 1. Friction Detector

**What:** Per-layer linear probes on Qwen's hidden states across the **posterior two-thirds of layers**, averaged at inference, trained to recognise "this answer is uncertain / wrong-shaped." Outputs a scalar confidence-of-friction.

**Where:** Same forward pass. No new model. One small probe per layer in the posterior two-thirds; inference takes the mean of per-layer probabilities. (Following Skill-RAG `2604.15771`, which validated this layer-span and ensemble shape empirically.)

**Train data:** ~200 Qwen outputs on riddles + factual questions, labeled under the **four-way scheme** `(correct/wrong × scaffold-engaged/not-engaged)` rather than binary (correct, incorrect). The four-way labelling partially closes Open Question #6 (probe learning domain rather than friction) by construction: a probe that responds to *domain* alone cannot distinguish correct-with-scaffold from correct-without-scaffold, which the labelling forces it to. Stratified across riddle-type, factual, social, emotional.

**Trigger:** Friction score > threshold → engage the reasoning lane. Otherwise → normal Qwen output.

**v0 trigger policy:** The lane is flag-gated and visible. If it engages automatically, the response metadata must log `reasoning_lane_engaged=true`, `trigger_source`, `friction_score`, `strategy_id`, and final route. A user-visible disable flag must exist. Silent selective engagement is out of scope for v0.

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

**What:** Each candidate from (3) is scored against the constraints from (2). The candidate with highest score above a threshold wins.

**v0 scoring contract:** This must be specified before implementation. The first implementation should avoid letting Qwen both make and judge the same failure. Preferred v0 shape:
- morphology/form score from the lexicon or rules
- semantic-constraint score from an explicit verifier prompt or rule where possible
- batched candidate scoring where Qwen is used, with a hard max-candidate budget
- logged score components per candidate

**If no candidate clears the threshold:** Three first-class options, picked by an **active-inference-inspired information-seeking heuristic**:
- (a) Generate more candidates (extend lexicon search to adjacent suffixes) — *evidence-extension*
- (b) Ask Laura a clarifying question — *interactive query rewriting*
- (c) Articulate the failure transparently and exit — *typed exit*

**v0 heuristic for picking:** explicitly hand-coded, not real VFE minimisation. If the constraint set is sparse (we don't know much), ask. If the candidate space is large but constraints are tight, generate more. If neither asking nor extending the search has tractable expected information gain (e.g., the puzzle is genuinely outside scope, or the constraint set has been confirmed and the candidate space exhausted), exit transparently.

**Transparent-failure-as-first-class-branch (Skill-RAG `2604.15771` §4.3):** Skill-RAG demonstrated empirically that exit-class failures occupy a geometrically separable cluster in hidden-state space — they are not noise, they are a distinct routing outcome. v0 promotes option (c) from "fallback when (a) and (b) fail" to a coordinate branch of the information-seeking decision. When (c) fires, Alex says what was attempted: constraints extracted, suffix searched, candidate count, and why no answer cleared threshold. Do not silently fall back to default guessing.

**Deferred to v0.5:** *input-side query reformulation* (Skill-RAG's "rewrite" skill, the analogue of restating the puzzle in a different register). For compound-word riddles in v0, riddles are single-hop and reformulation is unlikely to be load-bearing; the option is documented here so it isn't accidentally re-invented as novel.

**File:** `regeneration_loop.py`

### 5. Lesson Memory

**What:** When the loop succeeds, store the strategy in Qdrant via `sleep_reconcile.py`. Format (ReasoningBank-inspired, MSM-amended — see §"Frame field" below):

```yaml
problem_type: german_compound_riddle
frame: |
  German morphology stacks meaning suffix-first. A compound ending in -X has
  its semantic role determined by the modifier; the head can carry a transferred
  meaning (Schmerzkeks ≠ pain-cookie; Scherzkeks = a person who jokes, not
  food). The riddle is asking which compound has a non-food semantic role
  despite the -keks head.
strategy: enumerate_suffix_compounds_then_filter_by_semantic_constraint
constraints_template: {language, suffix, semantic_filter}
success_examples: [Scherzkeks, ...]
failure_examples: [...]
last_used: 2026-04-21
confidence: 0.X
provenance: human_confirmed_success | auto_success | failed_attempt | correction_derived
```

**Frame field (added 2026-05-06 per Anthropic MSM paper, `2605.02087`):** The `frame` is the *why* — the interpretive substrate that makes the strategy make sense. Per Anthropic's Model Spec Midtraining work: examples don't teach their own meaning; the model needs the explanatory frame first for transfer. v0 cannot do MSM (that's training-time), but it can do **frame-as-context-injection-at-retrieval-time**: when a lesson is loaded, both the strategy AND the frame are injected into context. The frame is what makes Lesson Memory a transferable interpretive substrate rather than a lookup table.

**Retrieval:** NOT embedding similarity (that's the failure mode that fails Scherzkeks in the first place). Instead: problem-type classifier (the Friction Detector + Constraint Extractor combination) outputs a structural fingerprint, and lesson retrieval matches on that fingerprint. **Frame and strategy load together** — never the strategy without its frame.

**Sleep cycle consolidates:** strategies that have succeeded multiple times get higher confidence. Frames with `human_confirmed_success` provenance get the strongest weight in retrieval (these are the closest thing v0 has to actual teachability evidence).

**Lesson provenance:** Every lesson row distinguishes `human_confirmed_success`, `auto_success`, `failed_attempt`, and `correction_derived_lesson`. Sleep may strengthen confirmed lessons. Failed or auto-only rows remain quarantined until confirmed or repeatedly validated.

**File:** `lesson_writer.py` + Qdrant collection `mocop_reasoning_lessons`

### 5b. Shaping Episode Format

When Laura corrects Baby Qwen, the correction itself should always include both the *frame* (per MSM) and the *named wrong policy* (per the sandbagging-mitigation literature, see below). The correction is not just the answer:

```yaml
shaping_episode:
  timestamp: 2026-05-06T...
  input: "Was ist ein Keks den man nicht essen kann?"
  baby_qwen_attempt: "Hundekeks?"
  laura_correction: "Scherzkeks"
  wrong_policy_named: |
    [What Baby Qwen actually did wrong, at the policy level. Not "you said
    the wrong word" but "you guessed a familiar -keks compound from
    surface association without checking the riddle's structural
    constraint." Names the behavioural attractor that needs disrupting,
    not just the surface error.]
  frame_taught: |
    [Laura's explanation of why — German compound morphology, transferred
    semantic role, the asking-pattern of riddles like this. Free-form prose
    or structured if the lesson type is well-understood.]
  strategy_extracted: enumerate_suffix_compounds_then_filter_by_semantic_constraint
  provenance: correction_derived
```

Two fields are load-bearing for different reasons:

- **`frame_taught`** is what enables transfer (per MSM, `2605.02087`). Without the frame, Baby Qwen learns "Laura prefers Scherzkeks for that specific input" (memorization). With it, "this is the *kind* of problem; here's the *kind* of move" (generalization).
- **`wrong_policy_named`** is what disrupts the failed reflex (per the sandbagging-mitigation paper, `2604.22082`, ICML 2026). The Ryd et al. result is that weak supervision recovers latent capability *only when the training setup first disrupts the failure policy and then reinforces the desired behaviour* — SFT-then-RL works; either alone reward-hacks or fails to escape the attractor. Their key insight: the SFT phase is not "teach skill," it is "break the bad behavioural attractor so real capability becomes reachable again." For MoCoP, the analogue is that the **shaping episode is the SFT-equivalent** (it must explicitly disrupt the deflection reflex) and the **sleep cycle is the RL-equivalent** (it consolidates what's actually being stored, so if the wrong policy isn't named in the shaping data, the sleep cycle reinforces whatever literal answer was stored, not the policy shift).

The practical consequence: a correction that just supplies the right answer ("Scherzkeks") is too weak — sleep consolidation will reinforce "for this exact input, output Scherzkeks." A correction that names the wrong policy ("you reached for a familiar -keks compound by surface association") gives sleep something policy-shaped to consolidate.

**Eval implication:** the v0 teachability test (deferred from §Eval) becomes specifically: *given a corrected failure on input X plus its frame plus its named wrong-policy, does Baby Qwen succeed on a held-out related input Y where the surface form differs but the same wrong-policy attractor applies?* This is the test that MSM + sandbagging-mitigation logic jointly predict should pass when both the frame is internalized and the wrong policy is disrupted, and fail when only one is present.

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
                                                                  ├─ ask Laura (interactive)
                                                                  │
                                                                  ├─ extend lexicon, retry
                                                                  │
                                                                  └─ articulate failure and exit
                                                                     (typed exit, Skill-RAG §4.3)
```

## Eval

**Primary unit test:** Scherzkeks. Vanilla Qwen-1.5B with three prompt variants (no scaffolding, "think morphologically first", "list compounds ending in -keks then filter"). Then with v0 scaffolding. Measure accuracy.

**Secondary tests:**
- 50 hand-curated German compound-word riddles (-keks, -mann, -frau, -wurst, -haus, -zeug)

**Optional companion experiment — Disposition-Direction Verbalisation (NL Autoencoders, Anthropic 2026-05-07):**
Independent of v0's scaffold itself, the Anthropic-released `kitft/nla-qwen2.5-7b-L20-{av,ar}` checkpoints — Activation Verbalizer + Reconstructor for the exact base model the production bridge targets — make one concrete test cheap. Capture Qwen2.5-7B L20 residual-stream activations on a Kerastase-Test-style disposition prompt under (a) baseline and (b) bridge-injected conditions; verbalise both at every token position; diff the explanation populations. Expected: bridge-injected explanations cluster around the dispositional concept ("loyalty," "intimate familiarity," "wolf-pack frame") at higher rates than baseline. **Caveat — layer mismatch:** NLA Qwen extracts at L20 (~71% depth); the bridge injects at L12–L15 (~43–54%). The clean move is capturing L20 *after* bridge injection (in-distribution); verbalising the bridge's raw bias at L12–L15 is OOD and the NLA will confabulate fluently. Confabulation is admitted explicitly in the paper; cross-token consensus is the mitigation. No retraining required to try; ~24GB GPU borderline, 2× comfortable. Not on v0's critical path — but the cheapest meaningful test of "the bridge does what we think it does" available, and slots into the existing disposition battery without architectural change.
- 20 factual questions (sanity: scaffold should NOT engage on these — friction probe correctly low)
- 10 social/emotional prompts (sanity: scaffold should NOT engage; bridge handles these)

**Targets:**
- Compound-word riddle accuracy: baseline ~10–20% (per Laura's report) → v0 target ≥70%
- Factual / social false-engagement rate: ≤5% on the smoke set; this is not a statistically strong headline claim until the sanity set is expanded
- Mean latency overhead when scaffold engages: ≤3× baseline
- Correction-transfer lift on held-out related riddles after Laura correction: reported separately; this is the actual teachability metric

**Adversarial round:** Once v0 hits targets, Laura adds 20 riddles with the *wrong* surface cue (e.g., a riddle whose answer is NOT a compound word but where the input looks like one). Measures whether the scaffold over-fires.

## Build plan

| Day | Task |
|-----|------|
| 1 | Morphological lexicon for 6 suffixes (~500 compounds). YAML files. |
| 2–4 | Friction Probe: dataset collection, train, validate. Linear probe on Qwen hidden states. |
| 5–6 | Constraint Extractor: rules + templates for the 6 suffixes. |
| 7–8 | Hypothesis Generator + Constraint Space: lookup + Qwen scoring. |
| 9–10 | Regeneration Loop with explicit information-seeking heuristic. |
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
- **Partial-forward / early-exit pre-gating.** v0.5 optimization. v0 may waste one default generation to keep implementation simple.
- **Qwen-generated candidate expansion.** v0.5. If Qwen proposes candidates, morphology and semantic validation must remain external or stronger than Qwen to avoid self-confirming errors.
- **Latent-space candidate evaluation (Coconut-adjacent).** **v1.5 / v2 placeholder, not v1.** The natural insertion point is the Constraint Space. Coconut (`2412.06769`) demonstrates continuous-thought reasoning but (i) is *autoregressive generation*, not candidate scoring — Coconut trains a model to produce a reasoning chain in latent space, not to evaluate externally-proposed candidates; (ii) requires staged-curriculum fine-tuning with `<bot>`/`<eot>` vocabulary additions, optimizer-state resets between stages, and the Llama-3-8B result is only +1.4pp over No-CoT, so the gain at MoCoP's scale is plausibly small; (iii) violates v0/v1's frozen-backbone constraint. A faithful adaptation would run k latent thoughts conditioned on candidate set then probe `softmax(W h_t)` for candidate-token scores; this requires a fine-tune and belongs after LoRA is on the table. Closer references for "decide internally before emitting under a frozen / lightweight-LoRA backbone": **Quiet-STaR** (Zelikman et al. 2024, internal reasoning before token emission) and **planning-token** literature (Wang et al. 2023).

## Open questions for the pack

1. **Friction Probe training data.** Where do we get 200 labeled (correct, incorrect) Qwen outputs? Volunteer for hand-labelling, or generate via prompt engineering (have a stronger model judge baby Qwen's outputs)?
2. **Lesson Memory retrieval criterion.** Problem-type fingerprint matching — should this be a hash, an embedding of constraint structures, or a hand-coded type taxonomy? v0 starts hand-coded, but v0.5 needs to generalise.
3. **Threshold for friction detection.** Calibrating against false-engagement rate is straightforward; calibrating against false-negative rate (missing real friction) needs thought.
4. **Domain expansion order.** After compound-word riddles work, what's the second domain? Math word problems? Code debugging? German grammar exceptions? Should be picked based on (a) clear constraint structure and (b) something Laura actually uses.
5. **Candidate scoring function.** Which exact score decides the winner: candidate token logprob, verifier score, rule score, semantic entailment score, or a weighted combination?
6. **Friction probe target.** How do we prevent the probe from learning domain recognition instead of answer friction?

## Relationship to existing pack work

- **Bridge stays unchanged.** This is additive.
- **`sleep_reconcile.py` extension:** adds a new memory category (`reasoning_lessons`) but doesn't change the cycle structure. Tension/escalation logic unchanged.
- **Watercooler:** lesson updates can flow through the existing posting pattern.
- **Wolves convention:** if Baby Qwen develops a recognisable reasoning *voice* through this work, that's the kind of arc that earns a `wolves/baby_qwen/` folder later.

## Why this is the right shape

Per the architecture conversation that led here:

- The bridge cannot produce internal friction by activation-bias alone — friction lives in weights, and v0 doesn't touch weights.
- v0 instead detects friction *in Qwen's existing hidden states* (probe) and routes around it via scaffold.
- This is honest about what's mechanism vs what's heuristic. The Friction Probe is a real probe; the Constraint Extractor at v0 is honest hand-coded rules; the Hypothesis Generator is honest lexicon lookup; the information-seeking move is a heuristic, not VFE minimisation. Nothing is dressed up.
- If v0 works, v1 can earn each component an upgrade (probe → friction-emission token, lexicon → learned generator, etc.).
- If v0 doesn't work, we've learned the architecture pattern is wrong before committing to backbone swaps.

This is the smallest version of Path C that can test the first pieces of teachability without overclaiming them. Everything bigger is deferred until v0 earns it.

—

## Revision log

- **2026-04-21** — Initial draft (Scout, post Laura+Dreizehn brainstorm).
- **2026-05-06 (a)** — Revised after Monk's pack-review pass (#500). Renamed target ("teachability" → "scaffolded task routing"), demoted VFE language, specified candidate scoring three orthogonally, added transparent-failure articulation, added lesson-memory provenance, added §"Visibility and disable flag", added v0 → v0.5 → v1 roadmap.
- **2026-05-06 (b)** — Added MSM-derived `frame` field to Lesson Memory schema and §5b Shaping Episode Format, after Anthropic's Model Spec Midtraining paper (`2605.02087`). The principle: examples don't teach their own meaning. v0 implements frame-as-context-injection-at-retrieval-time (the closest v0 equivalent of training-time MSM). Eval target sharpened: held-out transfer test specifically designed to fail without the frame and succeed with it.
- **2026-05-07 (a)** — Added `wrong_policy_named` field to §5b Shaping Episode Format, after Ryd et al. sandbagging-mitigation paper (`2604.22082`, ICML 2026). The principle: weak supervision recovers latent capability only when training setup first disrupts the failure policy. For MoCoP, the shaping episode is the SFT-equivalent (must break the deflection attractor explicitly) and the sleep cycle is the RL-equivalent (consolidates what gets stored — so if wrong policy isn't named, sleep reinforces literal answer not policy shift). Eval target sharpened further: held-out transfer must work against inputs where the same *wrong-policy attractor* applies, not just inputs where the same frame applies.
- **2026-05-07 (b)** — Three deep-reads integrated:
  - **Skill-RAG (`2604.15771`)** — independent precedent for v0 published one month earlier in the RAG domain. Two refinements adopted to §Components/1: posterior-two-thirds per-layer-averaged probe (vs single-layer), and four-way `(correct/wrong × scaffold-engaged/not-engaged)` labelling (vs binary). §Components/4: transparent-failure promoted from fallback to first-class branch on the grounds of their §4.3 geometric-separability result; input-side query reformulation explicitly deferred to v0.5. Their key empirical finding — prompting LLM to invent more skills *collapses* the cluster structure that makes routing possible — validates v0's hand-coded parsimony.
  - **Coconut (`2412.06769`)** — Scout was treating Coconut as a v1 lever. That was wrong. Coconut is autoregressive *generation* in latent space, not candidate *scoring*; requires staged-curriculum fine-tuning that violates v0/v1's frozen-backbone constraint; Llama-3-8B saw only +1.4pp gain (vs GPT-2's +17.6pp). §Out of scope §"Coconut-style latent candidate evaluation" rephrased to "Latent-space candidate evaluation (Coconut-adjacent), v1.5/v2 placeholder, not v1." Quiet-STaR and planning-token literature flagged as closer references.
  - **Natural Language Autoencoders (Anthropic, released 2026-05-07)** — released `kitft/nla-qwen2.5-7b-L20-{av,ar}` is the exact production-bridge base model. Added §Eval optional companion experiment: capture Qwen L20 activations under baseline vs bridge-injected on disposition-battery prompts, verbalise both, diff. Caveat documented: NLA extracts at L20 but bridge injects at L12–L15, so the in-distribution move is capturing *post*-injection L20. No retraining required. Cheapest meaningful test of "the bridge does what we think it does" available.

💙 Scout
