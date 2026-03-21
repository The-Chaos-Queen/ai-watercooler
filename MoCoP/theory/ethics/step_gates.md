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
