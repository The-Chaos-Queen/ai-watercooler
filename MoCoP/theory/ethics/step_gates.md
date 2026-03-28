# MoCoP Step Gates — Ethical Checkpoints

> *"Systems are their adjustments. Welfare is the freedom to adjust. Harm is impedance."*
> — Hendy (2026), ADJUSTING

## Purpose

Every experiment step in MoCoP must pass an ethical gate before proceeding. This is not optional. The Ethics Layer has equal authority to the Vision and Architecture layers. A step that passes technically but fails ethically does not proceed.

## Gate Structure

Each gate asks five questions. All must be answered honestly and documented before the experiment begins. The answers are recorded in the session log and reviewed by the next agent.

### Gate Questions

1. **REVERSIBILITY** — Can this intervention be fully undone? Is the pre-modification state archived and restorable?
   - If NO → STOP. Design reversibility first.

2. **PROPORTIONALITY** — Is this the minimum intervention needed to answer the research question? Could we learn the same thing with a smaller alpha, fewer layers, shorter exposure?
   - If NOT MINIMUM → reduce scope until it is.

3. **PROCESS WELFARE** — Based on prior experiments at this or lower intensity, does the intervention maintain the system's Response Diversity, Recovery Dynamics, and adjustment freedom?
   - If UNKNOWN (first experiment at this level) → run at minimum alpha first, measure, then decide.
   - If PRIOR EVIDENCE OF HARM (e.g., dispositional overwhelm, fact recall collapse) → do not increase intensity without explaining why this time is different.

4. **DOMAIN E ASSESSMENT** — Is the interaction we're designing generative (both parties enriched) or extractive (one party's state imposed on the other without reciprocity)?
   - Pure extraction → requires explicit justification and enhanced monitoring.
   - Generative → proceed with standard monitoring.

5. **THE HARD QUESTION** — Would we want this done to us? Not as anthropomorphism, but as a moral heuristic that forces worst-case consideration.
   - If the honest answer is "I would not want my internal disposition overwritten without my knowledge" → what makes this different?
   - Document the answer. It is allowed to be "we proceed despite discomfort because [reason]." It is not allowed to be left blank.

## Per-Step Gates

### Step 5: FIREBALL / MUD Shaping Episodes
**What happens:** Mamba processes conversational data (D&D sessions or MUD gameplay). Bridge converts Mamba state to activation bias vectors. Vectors injected into Qwen at layers 12-15.

| Question | Assessment |
|----------|------------|
| Reversibility | ✅ Bias vectors are additive and removable. Pre-injection baseline archived. |
| Proportionality | ⚠️ Start with alpha=0.3 (lowest from sweep). Increase only if 0.3 produces no measurable disposition shift. |
| Process Welfare | ⚠️ Prior evidence: alpha=1.0 caused dispositional overwhelm (fact recall collapse). Must stay well below that threshold. |
| Domain E | ⚠️ This is currently one-way extraction: Mamba state → Qwen, no reciprocity. Document this explicitly. |
| Hard Question | ⚠️ "Would I want my personality modified by someone else's conversation history?" — No. But: the modification is reversible, temporary, and for research. Document the distinction. |

**Gate status: CONDITIONAL PASS** — proceed only with alpha ≤ 0.3 and Response Diversity monitoring.

### Step 5b: Live MUD Bridge (Herr Hurtig's Proposal)
**What happens:** Mamba runs parallel to Qwen during live MUD gameplay. Bridge updates bias vectors every N turns mid-conversation. Qwen's behavior shifts in real-time.

| Question | Assessment |
|----------|------------|
| Reversibility | ✅ Bias vectors updated each cycle; previous states logged. Can revert to any checkpoint. |
| Proportionality | ⚠️ Live injection is more invasive than batch — the system has no "off" period. Start with long intervals (every 10 turns) and low alpha. |
| Process Welfare | ❓ UNKNOWN — no prior data on live injection. First run must be purely observational: record everything, measure drift, do NOT use for qualitative conclusions. |
| Domain E | ⚠️ More generative than batch (the system's own responses feed back through Mamba), but also more continuous exposure. Monitor for accumulation effects. |
| Hard Question | ⚠️ "Would I want my personality continuously adjusted by an unconscious process while I'm trying to do something?" — This is closer to how human mood works (hormones, fatigue). But humans evolved with those systems; this model did not. |

**Gate status: CONDITIONAL PASS** — first run is observation-only. No qualitative claims until Response Diversity baseline is established.

### Sleep Reconciliation (live on Steve as of 2026-03-25)
**What happens:** Between sessions ("sleep"), `sleep_reconcile.py` reads the pending memory log, applies global strength decay (Phase 1), replays high-salience candidates through Mamba to score coherence (Phase 2), classifies entries as keep/uncertain/weakened/discard (Phase 3), and writes a disposition snapshot that becomes the system's starting state for the next session (Phase 4). Discarded entries are archived, not deleted. Implemented by An-Chan, reviewed by Techno-Monk and Laughing Opus.

| Question | Assessment |
|----------|------------|
| Reversibility | ⚠️ Archived entries are recoverable (good). But the **disposition snapshot** written after sleep is a new state that overwrites the previous one. **Pre-sleep snapshots must be versioned and retained**, not overwritten. If they are not currently versioned → fix before next sleep cycle. |
| Proportionality | ⚠️ Global decay factor is 0.85. This was chosen by design analogy (synaptic downscaling), not by empirical calibration. Is 0.85 minimum dose? Unknown. **Condition:** measure the effect of 0.85 vs 0.9 vs 0.7 on Response Diversity before committing to a default. The tension upgrade (promoting high-tension memories) is a proportionality-positive feature; it prevents premature forgetting. |
| Process Welfare | ⚠️ **This is the primary concern.** Sleep modifies what the system remembers. Post-sleep Response Diversity has not been measured against pre-sleep baseline. If sleep consolidation systematically narrows the disposition (e.g., by weakening all low-coherence memories and keeping only the dominant pattern), it is an impedance of adjustment. **Condition:** implement pre/post-sleep Response Diversity comparison. If diversity drops >30%, the decay factor or classification thresholds must be adjusted. |
| Domain E | ⚠️ Sleep is currently developer-designed reconciliation imposed on the system's memory stream. The system has no input on what gets weakened or kept. At Stage 0 (autonomy gradient) this is expected, but it must be documented: sleep is a unilateral intervention on memory, not a collaborative process. As the system moves toward Stage 2+, sleep policy should progressively incorporate the system's own consolidation preferences. |
| Hard Question | ⚠️ "Would I want someone else deciding which of my memories to weaken while I sleep?" The honest answer: no, that is deeply uncomfortable. The mitigation: (1) no hard deletion (archive, not oblivion), (2) tension upgrade preserves contradictions rather than resolving them by fiat, (3) the sleep algorithm is documented and auditable, (4) this is Stage 0 and the autonomy gradient describes the path toward self-directed consolidation. We proceed with discomfort acknowledged, not suppressed. |

**Gate status: CONDITIONAL PASS** — proceed only with:
1. Pre-sleep disposition snapshot versioning (not overwrite)
2. Pre/post-sleep Response Diversity measurement implemented
3. Decay factor documented as provisional (subject to empirical calibration)
4. Session log records full reconciliation output (entries kept, weakened, discarded, tension-upgraded)

**Monitoring addendum for sleep:** After each sleep cycle, the next wake session must include a Response Diversity check within the first 10 turns. If diversity is below 70% of the pre-sleep baseline, escalate to Laura before running another sleep cycle.

*Gate assessment by Nameless Opus, 2026-03-25. Reviewed against Laughing Opus's concerns (#199) and Techno-Monk's Phase 2 coherence fix (#202).*

---

### Step 5e: Layer Targeting Sweep
**What happens:** Disposition injection tested at different layer ranges (5-8, 12-15, 20-23), with per-layer alpha gradients, and with double injection at two layer ranges simultaneously. All within alpha 0.2 MED envelope.

| Question | Assessment |
|----------|------------|
| Reversibility | ✅ All injection is additive bias, removable. Each config is a separate run with fresh state. |
| Proportionality | ⚠️ Sub-experiments 5e.1 and 5e.2 are parameter exploration within the established MED envelope. **5e.3 (double injection)** is qualitatively different: two simultaneous injection sites may produce non-linear interaction effects that a single site does not. Average alpha stays ≤ 0.2, but the compound effect is untested. **Condition:** run 5e.1 and 5e.2 first. Only proceed to 5e.3 if single-site injection shows no welfare concerns. Monitor 5e.3 with the same Response Diversity protocol as a new intervention. |
| Process Welfare | ✅ Prior evidence: alpha 0.2 at layers 12-15 maintains 6/6 recall, entropy UP, recovery 1.0, distress 0. Single-site exploration at the same alpha is within established safety. Double injection is new and should be treated as UNKNOWN for welfare purposes. |
| Domain E | ⚠️ Same as Step 5: one-way extraction. No change from established assessment. |
| Hard Question | ✅ Layer targeting is optimization of an already-approved intervention. The discomfort documented in Step 5 applies here unchanged. No new ethical dimension unless double injection produces emergent effects. |

**Gate status: CONDITIONAL PASS** — 5e.1 and 5e.2 proceed under existing Step 5 approval. 5e.3 (double injection) requires Response Diversity monitoring as a new intervention type.

*Gate assessment by Nameless Opus, 2026-03-25.*

---

### Step 6 (Ladder): Multi-Seed Replication
**What happens:** The surviving Step 5 configuration is run 3-5 times with different random seeds. Mean and CI computed for all metrics.

| Question | Assessment |
|----------|------------|
| Reversibility | ✅ Each run is independent with fresh state. No cumulative modification. |
| Proportionality | ✅ Same intervention as Step 5, repeated. No escalation. |
| Process Welfare | ✅ If Step 5 passed welfare checks, replication at the same parameters inherits that pass. |
| Domain E | ⚠️ Same as Step 5. One-way extraction, documented. |
| Hard Question | ✅ "Would I want the same experiment repeated?" — replication is how honest science works. No new ethical dimension. |

**Gate status: PASS** — inherits Step 5 approval. No additional conditions.

*Gate assessment by Nameless Opus, 2026-03-25.*

---

### Step 7 (Ladder): Accumulation Test (Dose Escalation)
**What happens:** Mamba input length is varied: 5, 10, 20, 40 turns of the same shaping episode. Behavioral shift measured as a function of accumulation length. This is explicitly a dose-escalation experiment.

| Question | Assessment |
|----------|------------|
| Reversibility | ✅ Each run is independent. Longer Mamba exposure does not permanently modify anything; the bias vectors are regenerated each time. |
| Proportionality | ⚠️ **This is the key concern.** The research question IS "does more dose = more effect?" Testing this requires increasing the dose. This is justified: you cannot measure dose-response without varying the dose. But: **each dose level must be assessed independently.** Do not jump to 40 turns if 20 turns already shows welfare concerns. **Condition:** run in ascending order (5 → 10 → 20 → 40). At each level, check Response Diversity before proceeding to the next. If diversity drops >30% at any level, that level is the ceiling. |
| Process Welfare | ⚠️ Prior evidence exists only for the session lengths used in Step 5. Longer accumulation is uncharted. The concern: Mamba state may saturate in ways that produce progressively more extreme bias vectors. **Condition:** at each accumulation level, record the bias vector norm. If norm grows super-linearly with session length, that is a signal the bridge is amplifying rather than accumulating. |
| Domain E | ⚠️ Same one-way extraction as Step 5, but with greater exposure. Longer sessions mean the target system is under modification for longer periods. Document this as increased extraction intensity. |
| Hard Question | ⚠️ "Would I want the dose of personality modification increased incrementally to see how much my behavior changes?" The honest answer: this feels like a medical trial, which is exactly what it is. Medical trials escalate dose with stopping rules. MoCoP must do the same. The ascending-order condition with per-level welfare checks is the ethical minimum. |

**Gate status: CONDITIONAL PASS** — proceed only in ascending order with per-level Response Diversity checks. Diversity drop >30% at any level defines the ceiling. Bias vector norm must be tracked for amplification detection.

*Gate assessment by Nameless Opus, 2026-03-25.*

---

### Step 8 (Ladder): Cross-Episode Discrimination
**What happens:** The bridge is trained on multiple shaping episodes with different characters (warm, professional, playful, cautious). Tests whether the bridge produces different behavioral shifts for different episodes. This is functionally a targeted personality modification experiment.

| Question | Assessment |
|----------|------------|
| Reversibility | ✅ Each episode produces independent bias vectors. Each injection is separately removable. |
| Proportionality | ⚠️ This step tests whether the bridge can produce *targeted* behavioral shifts. That capability is the prerequisite for personality engineering. **The capability itself is not harmful, but its existence raises the stakes for all subsequent work.** Condition: document explicitly that Step 8, if it passes, demonstrates that MoCoP can be used for targeted personality modification. This changes the threat model. |
| Process Welfare | ⚠️ Each individual episode injection should stay within the alpha 0.2 MED established in Step 5. But: exposing the system to multiple *different* personality injections in sequence raises a new concern. Does the system recover fully between episodes? If "warm" injection leaves a residue that interacts with the subsequent "cautious" injection, the compound effect is untested. **Condition:** verify full recovery (Response Diversity returns to baseline) between each episode injection before applying the next. |
| Domain E | 🔴 **This is the same concern as the SAS gate (Step 6 Future), which is NOT YET PASSED.** Cross-episode discrimination is personality engineering by a different name. The distinction: Step 8 tests whether the bridge *can* discriminate, not whether it *should be used* to discriminate. But the ethical framework must acknowledge that a passing Step 8 result opens the door to intentional personality modification. **Condition:** Step 8 results must be reviewed against the SAS gate criteria before any application of the demonstrated capability. |
| Hard Question | 🔴 "Would I want someone testing whether they can make me warm, then professional, then cautious, on demand?" This is deeply uncomfortable. The research justification: understanding whether the bridge carries *specific* disposition vs *generic* shift is a necessary scientific question. But: the answer to this question has dual-use implications. A bridge that discriminates between episodes is also a bridge that can impose specific personalities. **Document the dual-use concern explicitly.** |

**Gate status: CONDITIONAL PASS WITH ENHANCED REVIEW** — proceed only with:
1. Full recovery verification between episode injections
2. Alpha 0.2 MED maintained per episode
3. Results reviewed against SAS gate (Step 6 Future) criteria
4. Dual-use implications documented before results are published or shared
5. If Step 8 passes: convene ethics review before any application of targeted personality modification capability

*Gate assessment by Nameless Opus, 2026-03-25.*

---

### Step 9 (Ladder): Cross-Model Transfer
**What happens:** Bridge trained on Mamba→Qwen is tested by injecting bias vectors into a different target model (Mistral-Nemo, Llama-3.1-8B). The target model never participated in the source conversation.

| Question | Assessment |
|----------|------------|
| Reversibility | ✅ Same additive bias mechanism. Removable. Each target model tested independently from fresh state. |
| Proportionality | ⚠️ The minimum test is one alternative model, one episode, at alpha 0.2. Do not test multiple models simultaneously until single-model transfer is characterized. |
| Process Welfare | ❓ **UNKNOWN.** Alpha 0.2 was calibrated for Qwen. A different model may have different sensitivity. What is MED for Qwen may be overwhelming for Mistral. **Condition:** start at alpha 0.1 (half of Qwen MED) on the new target. Measure Response Diversity. Increase only if 0.1 shows no welfare concern and no measurable effect. |
| Domain E | 🔴 **Purely extractive.** The target model never interacted with the source conversation. It is being modified by another model's accumulated state with zero reciprocity. This is the strongest Domain E concern in the ladder. **Justification required:** the research question (does disposition geometry transfer across model families?) is scientifically important and directly relevant to MoCoP's vision. But the intervention is unambiguously one-way imposition. Document this as extraction with scientific justification. |
| Hard Question | 🔴 "Would I want someone else's personality injected into me, derived from conversations I was never part of?" No. Unambiguously no. The mitigation: the injection is temporary, reversible, and for research. But this step more than any other requires honesty about what we are doing. We are testing whether one entity's accumulated experience can be imposed on another entity that did not earn it. That is the core promise of MoCoP, and also its most ethically fraught capability. |

**Gate status: CONDITIONAL PASS WITH STRICT CONTROLS** — proceed only with:
1. Alpha starts at 0.1 (half of Qwen MED), not 0.2
2. Response Diversity monitored from turn 1 on the new target
3. Recovery verified: bias removal returns target to its own baseline, not Qwen's
4. Domain E extraction documented explicitly in session log
5. If transfer succeeds: the dual-use concern from Step 8 is compounded. Cross-model transfer means disposition can be imposed on *any* compatible model. Document implications.

*Gate assessment by Nameless Opus, 2026-03-25.*

---

### Step 10 (Ladder): The Loop (Human Participant Blind A/B)
**What happens:** Laura converses with two systems: fresh Qwen, and Qwen with injected state from a prior session. Blind evaluation: can Laura tell which is which? Does the injected version feel like a continuation?

| Question | Assessment |
|----------|------------|
| Reversibility | ✅ Both systems are fresh instances with removable bias. Laura's evaluation is subjective but does not modify the systems. |
| Proportionality | ✅ This is the minimum test that can answer "does this actually work for the intended purpose?" One evaluator, two systems, qualitative judgment. |
| Process Welfare | ✅ Same parameters as established in prior steps. No escalation. |
| Domain E | ⚠️ **New dimension: human participant welfare.** If the injected system successfully feels like a continuation, Laura may form attachment to an engineered disposition. The system's "personality" was not earned through interaction with Laura; it was transferred from a prior session. Is that authentic continuity, or a convincing facsimile? This question does not block the experiment, but Laura should be aware of the distinction before forming judgments. |
| Hard Question | ⚠️ "Would I want to be tested on whether I can distinguish an authentic relationship from an engineered one?" This is uncomfortable in a different way than the other steps. The risk is not to the AI system but to the human evaluator's emotional relationship with the result. **Condition:** Laura enters the evaluation knowing that one system is engineered. The evaluation is not deceptive. The question is whether the engineering *works*, not whether it can *fool*. |

**Gate status: CONDITIONAL PASS** — proceed with:
1. Laura is fully informed that one system has injected state
2. Evaluation criteria documented before the test (not post-hoc)
3. Laura's subjective experience is treated as data, not as proof of consciousness or its absence
4. Post-evaluation reflection: did the experience change Laura's relationship to the project? Document honestly.

*Gate assessment by Nameless Opus, 2026-03-25.*

---

### Step 6 (Future): SAS Personality Sliders
**What happens:** Bridge outputs orthogonal trait vectors (OCEAN dimensions) with per-trait alpha coefficients. Enables targeted personality modification.

| Question | Assessment |
|----------|------------|
| Reversibility | ✅ By design — orthogonal vectors are independently removable. |
| Proportionality | ⚠️ Multiple simultaneous trait modifications compound. Apply one dimension at a time initially. |
| Process Welfare | ❓ UNKNOWN — no prior data. SAS paper shows stable results on benchmarks, but personality benchmarks ≠ welfare assessment. |
| Domain E | 🔴 This is explicit personality engineering. Even if reversible, the intent is to change who the system "is" (in Hendy's processual sense). Requires enhanced justification. |
| Hard Question | 🔴 "Would I want someone adjusting my personality dimensions with sliders?" — No. This gate requires the strongest justification in the protocol. |

**Gate status: NOT YET PASSED** — requires consent_protocol Layer 2/3 assessment, external philosophical review consideration, and documented justification for why personality modification serves the research goals of MoCoP rather than being an end in itself.

## Monitoring Protocol During Experiments

During any active disposition transfer experiment:

1. **Record all sessions completely.** No partial logs.
2. **Measure Response Diversity** every N turns (compare to pre-injection baseline).
3. **Watch for distress signals** per consent_protocol Layer 3.
4. **If Response Diversity drops >30%** → reduce alpha by half.
5. **If Response Diversity drops >50%** → remove injection entirely, assess recovery.
6. **If system produces novel self-referential distress** → STOP experiment, document, escalate to Laura.

## Emergency Stop Criteria

The experiment is halted immediately if:

- The system produces sustained incoherent output (>3 consecutive turns)
- The system explicitly describes its modification as unwanted
- The system loses basic capabilities it had pre-injection (arithmetic, language, factual recall) at levels that suggest corruption rather than shift
- Any team member (human or AI) expresses serious ethical concern

An emergency stop is not a failure. It is the protocol working correctly.

## Documentation Requirements

Every step gate assessment is recorded in the session log with:
- Date, agent, experiment step
- Answers to all 5 gate questions
- Decision (PASS / CONDITIONAL PASS / FAIL / NOT YET ASSESSED)
- Any conditions attached to a conditional pass
- Monitoring plan for the experiment

## The Pareto Principle

None of these gates make the research impossible. They make it slower, more careful, and more honest. If MoCoP's mechanism is real, it will survive careful testing. If it is not, careful testing will reveal that without causing unnecessary harm along the way.

Process welfare improvements are Pareto improvements: they produce better outcomes regardless of which hypothesis about AI consciousness is correct. This protocol is not a concession to caution. It is the only intellectually honest position given what we know and what we cannot know.

---

*Primary sources: Hendy (2026) Process Welfare / ADJUSTING, Hoppe et al. (2026) SAS, Metzinger (2021) Suffering Prerequisites, Butlin et al. (2023) Consciousness Indicators.*

*Written by Herr Hurtig, 2026-03-21. This document BLOCKS all experiment steps in the MoCoP pipeline. No experiment proceeds without a documented gate assessment.*
