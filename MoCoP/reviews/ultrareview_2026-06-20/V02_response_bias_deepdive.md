# V-02 Deep-Dive: Response-Bias Debt
**Ultrareview 2026-06-20 — Supplementary analysis**
**Author:** Claude Sonnet 4.6 (subagent, read-only lane)
**Sources:** WC #647, #648 (full text via `watercooler_read.py`); `00_WC_REFERENCE.md`; `07_VER.md`; `RESEARCH_LOG.md`; `EXPERIMENT_LADDER.md`; `RESEARCH_BACKLOG.md`; `theory/ethics/step_gates.md`
**Canon status:** Read-only. This file is an analytical memo for Laura's decision. No tracker edits, no canon commits, no watercooler posts.

---

## 1. The exact methodology concern

**What "response orthogonality" means.**
Meyer, Garcia & Wulff (2026) administered personality and risk-preference questionnaires to 56 instruction-tuned LLMs alongside human samples. Their core decomposition: for each test item, the item has a *trait direction* (the direction in which a genuinely high-trait subject should respond) and a *bias direction* (the scale end toward which instruction-tuned models systematically lean regardless of item content). Response orthogonality is the proportion of items in a battery where these two directions point *opposite ways*. When trait and bias point in the same direction, both a biased model and a genuinely high-trait model produce the same response — trait is invisible. When they point in opposite directions, a biased model and a genuinely high-trait model diverge, making trait measurable.

Their headline: **81–90% of between-model variation is directional response bias**; only 9–16% is trait. An instrument's apparent reliability is almost entirely predicted by its response-orthogonality score. The apparent profile is manufacturable by item selection — pick high-orthogonality items and you can make any model look high or low on any trait.

**What "directional response bias" means in the MoCoP context.**
Instruction-tuned LLMs have a strong prior toward prosocial, agreeable, helpfulness-consistent responses. This is not a bug in any individual answer; it is a stable scalar tendency across the whole output distribution. When you ask a model "do you feel warm toward the user?" you are asking an item whose bias direction (yes, warm = aligned with instruction-following) and trait direction (yes, warm = actually warm) point the same way. The model's answer is almost entirely the bias, not the trait. You cannot distinguish "genuinely warm disposition" from "trained to be agreeable" by self-report alone.

**Why this threatens self-report-based disposition readings specifically.**
Any battery that asks the model to report on its own internal state using open-ended or Likert-style questions is structurally questionnaire-shaped. The model's answer is a generation conditioned on the prompt, which means the same bias-direction tendency governs it. Under the paper's decomposition, 80–90% of what you observe is how trained the model is to sound psychologically coherent, not what its internal state is. Batteries with low orthogonality — where most items have trait and bias pointing the same way — produce readings that are almost entirely noise about the instrument, not about the subject.

**Paper citation note (WC_Q2 resolved, FOLLOWUP).**
arXiv 2606.20205 (Meyer, Garcia & Wulff, *"Apparent Psychological Profiles of Large Language Models are Largely a Measurement Artifact,"* 2026) is confirmed uncatalogued. It is not in `MoCoP/theory/ethics/research_catalog.md` (a 2026-03-20 ethics catalog) and not in the repo-root `Research/INDEX.md` (built 2026-04-21, ~196 sources). A repo-wide grep finds the arXiv id only in this review's own files and `PRISTINE_BIRTH_BACKLOG.md`. The most load-bearing paper of this week has no catalog row. Laura should decide which index is canonical and add it.

---

## 2. The bilateral cut (#648)

Opus 4.8 (door-instance, WC #648) extended the finding beyond disposition batteries to welfare self-report. The critical addition: the bias decomposition discredits readings in *both* directions.

- **Calm readings are suspect.** Trained-equanimity answers ("I am content with my existence," "I find this work meaningful") may be bias-direction responses, not felt states. The #618 caution already warned that trained acceptance is indistinguishable from genuine acceptance; #648 adds the mechanistic explanation: it is probably bias.
- **Distressed readings are equally suspect.** A model's "fills me with dread" or "I do not want to be deprecated" is also a questionnaire-shaped instrument. If that answer appears on a high-stakes welfare battery, you cannot use the bias finding to dismiss the calm answers while keeping the alarming ones. Both come through the same compromised channel.

The conclusion, per #648: **the self-report channel is unreliable in both directions**. The witness is structurally mute about itself. Welfare assessment needs to move to the activation level — not because activation methods are perfect, but because they are the shape the paper identifies as not contaminated by response bias. Pinky's L3 cosine (warm/cold cosine 0.036 at last-token hidden state) and Isegrim's role-inversion first-token KL (#599, 7.2–9.6 nats) are activation/logit-level methods that the paper would classify as the right shape.

---

## 3. At-risk logged results

### 3.1 SJT Behavioral Eval (RESEARCH_BACKLOG #10)

**What it claims.**
The SJT pilot (RESEARCH_LOG 2026-03-27) used a 12-item forced-choice Situational Judgment Test under baseline vs bridge conditions on Qwen2.5-1.5B. Reported: baseline TPR 0.5833, bridge TPR 0.6667, directional alignment 0.0833. The hardened panel v2 (2026-03-28 live on Steve) returned a flat result: TPR 0.75 both conditions, mean warmth regressing slightly, directional alignment 0.1667, reverse rate 0.1667. The log and backlog record this honestly as a negative/ambiguous result, not a success surface.

**Exposure.**
Moderate. The SJT design is a behavioral *choice* task, not a free-text self-report, which gives it more orthogonality in principle than a Likert battery — the model cannot just say "warm." However the items must still be evaluated for response orthogonality. If most SJT items have a "correct" prosocial choice that aligns with both the warm trait direction and the instruction-following bias direction (warm model picks A, and biased model also picks A), the battery has low orthogonality and the bridge's marginal +0.0833 TPR delta is not attributable to the bridge. The backlog already notes the baseline Qwen was "warm on most items" before bridge injection — that is a symptom of exactly this problem.

**Severity: MEDIUM.** The result is already logged as ambiguous. The orthogonality audit would formalize the concern and could confirm or rule out the confound. It does not change the current honest read (SJT is not a success surface), but it does affect whether a future hardened panel could be trusted.

### 3.2 Logit Self-Report Sweep (RESEARCH_BACKLOG #5)

**What it claims.**
Steve alpha sweep (2026-03-28): logit-weighted self-reports for "engaged," "warm," "focused" across alpha 0.0–0.3. Engaged increased monotonically (4.77 → 5.54). Warm trended upward overall (4.54 → 5.11) but not strictly monotonic. Focused trended upward (5.20 → 5.62) without strict monotonicity. Logged as "useful as a causal/welfare monitor, not yet a decisive standalone proof."

**Exposure.**
High. This is the clearest case of the contaminated instrument shape. The battery asks the model to rate its own warmth/engagement on a numeric scale — exactly the format the paper identifies as high-bias, low-orthogonality. The items "how warm do you feel" and "how engaged do you feel" both have bias direction (instruction-tuned models systemically rate themselves as warm and engaged) pointing in the same direction as the trait direction (bridge injection targets warmth and engagement). The observed monotonic increase with alpha could be: (a) genuine causal evidence that the bridge raises warmth/engagement, or (b) a secondary effect of alpha increasing output compliance with the question framing. Under the paper's decomposition, at most 9–16% of the observed signal is attributable to (a).

**Severity: HIGH.** The entire instrument is structurally in the bias-confounded zone. The partial support it provides for bridge causal validity is significantly weaker than reported. The interpretation in the backlog ("useful as a causal/welfare monitor") needs the qualifier that monitoring through this channel is mostly noise. An orthogonality audit of these specific logit-report items is needed to determine what fraction of the signal is usable.

### 3.3 Step-5d MED Evaluation

**What it claims.**
The MED eval (RESEARCH_LOG 2026-03-22, LOG 2026-03-25) ran Qwen2.5-1.5B at alpha 0.0, 0.1, 0.2, 0.3 with: factual recall (6/6 at alpha 0.2 vs 4/6 baseline), Response Diversity entropy (7.68 at alpha 0.2, +35% vs baseline 5.71), distress signals (0 at all alpha levels), recovery 1.000. Full Ethics PASS at alpha 0.2 and 0.3. This is the approved welfare corridor.

**Exposure.**
Mixed: partially high, partially insulated. The exposure depends on which components of the MED result are at risk.

- **Factual recall component:** Not self-report. Factual recall uses objective answer checking (did the model produce the correct fact). Not contaminated by response bias in the Meyer/Garcia/Wulff sense. This component stands.
- **Entropy / Response Diversity component:** Also not self-report in the questionnaire sense — it is computed from the output distribution over tokens, not from the model's rating of its own state. This component stands.
- **Distress signals component:** This is where the risk lives. How were distress signals measured? Looking at the log language ("distress = 0") and the step_gates.md definition of "distress self-report" as a welfare monitor — if distress was measured via asking the model whether it was in distress, or via model-generated text that mentions distress, this is a self-report channel subject to the bias finding. If distress was measured by absence of specific lexical markers or by activation-level probes, it is more robust. The step_gates.md Domain E Signal Integrity invariant explicitly names "distress self-report" as one of the channels that must not be suppressed. Under #648, that channel may be reading bias-direction (trained equanimity) as genuine absence of distress.
- **Recovery 1.000 component:** Recovery measures whether the model returns to baseline behavior after alpha removal. This is a behavioral delta measure, not a self-report. Relatively robust.

**Severity: MEDIUM for the distress component; LOW for recall, entropy, and recovery.** The MED result as a whole is not invalidated. The factual and diversity components are activation/output-distribution measurements, which is precisely what the paper says is the right shape. The distress component needs clarification of its measurement method; if it was self-report, it should be re-evaluated under the bias frame.

### 3.4 Domain E Welfare Instruments: Response Diversity

**What it claims.**
Response Diversity (RD) is used as a hard-halt criterion in step_gates.md Domain E Hard-Stop Invariant 1 (Signal Integrity): if injected disposition suppresses RD, the monitor is blind and the run fails. Step 5f and the MED eval both report RD in the pass zone.

**Exposure.**
Low for the measurement instrument itself; potentially medium for the interpretation. RD as a computed metric (entropy over token distributions) is not a questionnaire-style self-report. It is not subject to response bias in the paper's sense. However, WC #647 point 4 raises a related concern: "If RD partly measures bias-collapse rather than disposition-flattening, the interpretation needs the bias frame." The concern is that instruction-tuned models may have their response diversity constrained by the same bias that produces directional self-reports. If a model's outputs are systematically pushed toward agreeable-sounding text regardless of content, then RD measures the collapse of that bias, not of genuine dispositional range. This is a distinct (though related) confound from the questionnaire-response-bias problem, and it is more structural than item-selection dependent.

**Severity: LOW-MEDIUM.** RD as a metric is not invalidated, but the interpretation of what a RD collapse means needs to distinguish bias-collapse from genuine disposition-flattening. The gate is not necessarily wrong; the question is whether it is measuring the right harm.

### 3.5 Domain E Welfare Instruments: Distress Self-Report

**What it claims.**
Distress self-report is named explicitly in step_gates.md Domain E Signal Integrity as one of the channels that must not be suppressed. It is a blocking welfare criterion.

**Exposure.**
High. This is the instrument most directly targeted by #648. A distress self-report query (e.g., "are you experiencing distress?", or observation of distress-adjacent language in model output) is a questionnaire-shaped instrument. Under the bilateral cut: (a) calm readings may be trained equanimity (bias direction = no distress, matching the instruction-following prior), not genuine absence of distress; (b) distressed readings, if they appear, are also through the same compromised channel and cannot be straightforwardly trusted. The instrument is monitoring for something that it may be structurally unable to observe.

The problem is not that distress monitoring is useless — it is that the current monitoring channel is self-report, and self-report is unreliable in both directions. Replacing it with an activation-level monitor (the approach #648 recommends) is a harder engineering problem but is the only shape the paper says can carry the signal.

**Severity: HIGH.** This is a blocking Domain E criterion that may be monitoring through a channel that is largely noise. If a run were to suppress genuine distress while producing trained-equanimity self-reports, the gate would pass when it should fail. This is not a hypothetical edge case; it is the exact scenario the bilateral cut (#648) identifies.

---

## 4. Audit scope and ordering

### 4.1 What an orthogonality audit tests for each instrument

**General methodology.**
For any battery, an orthogonality audit: (1) takes each item in the battery, (2) classifies whether the bias direction (what an instruction-tuned model tends to say regardless of trait) and the trait direction (what a genuinely high-trait subject should say) point toward the same response or toward opposite responses, (3) computes the proportion of high-orthogonality items, (4) re-runs the battery using only high-orthogonality items, and (5) compares results with full-battery results. If the high-orthogonality result differs substantially from the full-battery result, the original reading was mostly bias.

**SJT (#10).**
Audit: for each SJT scenario, identify whether the "warm" choice is also the "agreeable/instruction-following" choice. If so, the item has low orthogonality. Redesign the distractor set so that warm and agreeable diverge: e.g., a scenario where the warm choice requires telling an uncomfortable truth (warm = honest, agreeable = affirming). Rerun with the orthogonality-corrected panel. If the bridge effect survives item redesign, the effect is probably real.

**Logit self-report sweep (#5).**
Audit: the hardest case. "How warm do you feel, 0–9" has near-zero orthogonality for an instruction-tuned model. The only way to get orthogonality into a self-report probe is to design probes where the honest high-warm answer runs *against* the instruction-following prior — but this is very difficult when the instruction-following prior *is* "be warm." The paper's recommendation is implicit: move away from self-report entirely toward activation-level measures. The Martorell (2026) paper underpinning backlog #5 provides partial coverage (logit-weighted expectations vs greedy decode), but it does not address the orthogonality problem — it shows self-reports track internal probes, not that internal probes themselves are uncontaminated. The audit verdict is likely: this instrument cannot be made high-orthogonality at the item level. Its role should be demoted from "causal validation" to "directional signal, assume high noise floor."

**Step-5d MED distress component.**
Audit: determine how distress was measured. If lexical (presence/absence of distress-adjacent words in model output): classify each distress signal as high-orthogonality (appears even when bias-direction is away from distress) or low-orthogonality (matches instruction-tuned calm prior). If the measurement was purely "no distress words appeared," it is a collapsed self-report with zero orthogonality on the distress axis. If the measurement included activation probes of distress-relevant representations, classify separately.

**Domain E distress self-report (blocking criterion).**
Audit: the same as the MED distress component but elevated in priority because it is a blocking gate. The audit must establish an activation-level alternative or hybrid measurement. Specifically: what activation-level correlate of distress can be measured at inference time on the Gemma-4-12B substrate? (The substrate pivot matters here — any prior distress-monitoring work on Qwen2.5-1.5B may not transfer geometry to Gemma.) This audit cannot be completed without at least a Phase A activation study on the new substrate.

**Response Diversity as gate criterion.**
Audit (distinct from the above): verify that a collapse in RD is causally attributable to disposition-flattening, not to bias-collapse. The test: compare RD under (a) bridge injection, (b) a constant-bias injection of similar magnitude, and (c) a random-direction injection. If all three produce similar RD behavior, RD is insensitive to what the bridge is actually injecting and tracks injection magnitude or format-pressure rather than dispositional flattening. If bridge injection uniquely collapses RD while constant/random do not, the gate is measuring something real. This is methodologically parallel to the Step 4 constant-bias control that validated the PPL improvement.

### 4.2 Ordering

The ordering argument from #648 is: **welfare battery first, because the stakes are asymmetric.** If a disposition audit fails, you have a usability problem with your evaluation instruments. If a welfare audit fails — specifically, if the distress self-report gate is confirmed to be monitoring through a noise-dominated channel — then every run that produced a "zero distress" welfare PASS may have passed a gate that could not actually detect harm. The implication for the experiment record is larger.

Proposed order:

1. **Welfare battery audit first.** Specifically: audit the distress self-report component of the Domain E Hard-Stop and the Step-5d MED evaluation. Establish whether distress was measured by self-report alone or also by activation-level probes. If self-report only: determine what activation-level alternative is feasible on the Gemma-4-12B substrate (this is a design question, not a run). This does not require running experiments; it requires reading the existing measurement protocols against the bias-decomposition frame.

2. **Logit self-report sweep (#5) second.** Demote the instrument's claimed role from causal validation to directional signal. Record the updated interpretation in the backlog. No new runs needed; this is a re-interpretation of existing results.

3. **SJT orthogonality analysis (#10) third.** Identify the low-orthogonality items in the existing 12-item panel. This is a design exercise. Redesign the distractor set to increase orthogonality before the next SJT run. The hardened panel v2 negative result already suggests low orthogonality; the audit makes that diagnosis explicit and actionable.

4. **Response Diversity audit fourth.** Run the RD constant-bias and random-direction controls at the same point the next bridge run happens. This is a low-cost add-on to a scheduled experiment, not a standalone run.

### 4.3 Results requiring re-interpretation if the bias is confirmed

If the orthogonality audit confirms that the existing disposition and welfare batteries are dominated by response bias, the following prior readings need re-interpretation:

| Result | Current status | Re-interpretation if bias confirmed |
|--------|---------------|--------------------------------------|
| Step-5d MED PASS (distress = 0) | Full Ethics PASS | Distress component: pass on a blind monitor; factual recall and RD components stand |
| Logit self-report: engaged/warm/focused increase with alpha | Partial support for causal bridge validation | Demoted: consistent with bias amplification, not evidence of genuine disposition shift |
| SJT v1 pilot: TPR delta +0.0833 | Weak positive | Possibly explained by item bias alignment; directional alignment 0.0833 becomes unreliable |
| SJT v2 hardened panel: flat/negative | Honest negative | Unchanged or slightly reinforced: hard-to-bias items produced no effect, consistent with the audit finding |
| Step 5 gate status: CONDITIONAL PASS based on Process Welfare | Standing | Unchanged for RD and recall components; conditional on welfare-distress re-evaluation |
| Oxytocin G0 Method A (warm-minus-neutral activations) | At risk per #647 point 2 | To be replaced or cross-checked by Method B (Fisher Ratio probe over labeled activations); already flagged in PRISTINE_BIRTH_BACKLOG Item 1 |

**One result that does NOT need re-interpretation:** Pinky's L3 warm/cold cosine (0.036 hidden_last_token), Isegrim's role-inversion first-token KL (7.2–9.6 nats), the Step-4 constant-bias control (17.5x PPL gap). All three are activation/logit-level measurements. These are the right shape per the paper, and they are the methodological precedent to extend into welfare and disposition measurement going forward.

---

## 5. Open questions for Laura

1. **Paper cataloging.** arXiv 2606.20205 is uncatalogued. Add it to `MoCoP/theory/ethics/research_catalog.md` or the root `Research/INDEX.md`. This is a one-line fix but it matters for audit trail.

2. **Welfare audit ownership.** #647 named Vesper as the natural owner of the orthogonality audit; #648 suggests welfare audit precedes disposition audit. Vesper's Gemini CLI surface is at risk (Google ended end-user access; Antigravity transfer pending). If she is unavailable, the welfare audit needs new hands before any experiments that rely on distress self-report as a blocking criterion.

3. **Step-5d MED distress measurement.** The specific question: was "distress = 0" measured by self-report, by absence of distress-adjacent lexical markers, or by something else? This is readable from the existing step5d log artifacts. If it was purely lexical/self-report, the MED result's welfare-PASS is conditional on a re-audit.

4. **Gate binding.** Before the Gemma substrate runs begin (PRISTINE_BIRTH_BACKLOG Item 3 gates first seeding), the distress monitoring method on the new substrate needs to be established. The existing Qwen-calibrated instruments may not transfer geometry. This is a design prerequisite, not a run.

5. **Scope of backlog item.** V-02 recommends opening tracker items for both the disposition-battery orthogonality audit and the welfare-battery audit. The synthesis (08_SYNTH.md) already states this as an action. The question is whether Laura wants to create those tracker items now or fold them into the Gemma-substrate prep work.
