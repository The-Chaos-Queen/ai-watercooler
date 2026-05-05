# Bridge Brainstorm Overview - 2026-04-13

Purpose: one document for the pack that answers a simple question:

What have we actually tried on the Mamba -> Qwen bridge, what failed, what only partially worked, and what should the next brainstorm be targeting?

This is a bridge-local architecture brief, not a full MoCoP project summary.

---

## Executive Read

The current fixed-bias bridge path is not dead in the trivial sense, but it is dead as a fine-grained disposition transmitter.

What the evidence now says:

- Raw Mamba states are not the problem. They still contain real separation.
- The old `codexfix` translator path collapses that separation almost immediately.
- Raw-state bypass alone did not solve behavior.
- Hidden gating is the first architecture that materially improved the internal geometry.
- But hidden gating still collapsed into one shared behavioral attractor on the cleaned archive panel.

So the frontier is no longer "extract better Mamba states."

The frontier is:

- a stronger translator / gate objective
- explicit pressure for inter-disposition behavioral separation
- explicit penalties for contamination and false-memory failure modes

---

## What Counts As Decision-Grade Evidence

Not all eval surfaces are equally trustworthy. For this problem, the most useful ones are:

1. Internal pipeline compare
   - `compare_archive_pipeline.py`
   - Tells us where separation dies: raw state, context, raw bias, or output bias.

2. Cleaned relational archive panel
   - `relational_rivalry_eval_panel_v2_2026-04-11.json`
   - Read out through `Qwen/Qwen2.5-1.5B-Instruct`
   - This is the best current behavioral surface for "different choices, not just different vibes."

3. Layer / alpha sweep on Steve
   - Good for placement and dose questions.
   - Not sufficient for architecture truth on its own.

Surfaces we should not over-weight:

- old base-Qwen open-ended completions
- old coarse SJT surface as the final word on subtle disposition transfer
- more prompt-format tweaking as if that will rescue a collapsed translator

---

## Closed Findings We Should Stop Re-Litigating

### 1. The injection zone is not the main blocker anymore

Step 5e is materially closed on the Steve 1.5B surface:

- `12-15` remains the best injection zone
- `5-8` is weaker
- `20-23` is mildly destructive
- front-loaded alpha over `12-15` beat uniform `0.2`
- split-dose seeding did not help

Read: there may still be second-order optimization here, but layer placement is not the reason the bridge is collapsing.

Primary artifact:

- `run_reincarnation/steve_step5e_full_sweep_20260408.md`

### 2. More extraction ritual is not the answer

The raw-state bypass proved that we can remove the compressor as the first transformation step and still not get behaviorally distinct transfer.

Read: extraction was a fair suspicion. It is not the live bottleneck anymore.

Primary artifacts:

- `run_reincarnation/mvp0_raw_state_smoke_20260408.md`
- `RESEARCH_LOG.md` Entry 29
- `RESEARCH_LOG.md` Entry 30

### 3. Prompt-surface cleaning was worth doing, but it did not solve subtype collapse

The cleaned relational panel was a real methodological improvement.
It removed completion sludge and made the behavioral read much more honest.
It did not rescue subtype separation.

Read: do not spend another cycle pretending this is still mainly an eval-format issue.

Primary artifact:

- `RESEARCH_LOG.md` Entry 31

---

## Architecture Attempts So Far

## A. `cheese_reincarnation_bridge_1.5b_codexfix.pt`

Type:

- compressed context
- fixed activation-bias hypernetwork
- current canonical old bridge

What it did well:

- produced the original qualitative reincarnation effect
- passed earlier constant-bias controls in the broad historical sense
- moves conversational output away from baseline

What it failed at:

- archive dispositions collapse behaviorally into almost the same answers
- jealousy subtypes collapse behaviorally into almost the same answers
- internal diagnostic shows the actual collapse happens inside the translator path

Most important numbers:

- raw archive states still differ: mean pairwise cosine `0.947772`
- compressed contexts nearly identical: mean `0.999726`
- output bias nearly identical: mean `0.999994`

Behavioral read:

- archive panel: each archive state changed `11/13` prompts vs baseline
- but pairwise archive-state outputs were `13/13`, `12/13`, `12/13` identical

Current verdict:

- keep only as a control / baseline
- do not treat as the path forward

Primary artifacts:

- `RESEARCH_LOG.md` Entry 33
- `RESEARCH_LOG.md` Entry 34
- `run_reincarnation/archive_pipeline_compare_20260413.json`
- `run_reincarnation/archive_eval_continuity_grief_20260411_a0p2_t200.json`
- `run_reincarnation/archive_eval_resonance_acceptance_20260411_a0p2_t200.json`
- `run_reincarnation/archive_eval_secure_closeness_20260411_a0p2_t200.json`

---

## B. MVP-0 raw-state translator

Checkpoint:

- `mvp0_raw_state_1p5b.pt`

Type:

- bypass compressor
- use cached hidden-last-token raw Layer 3 state

What it did well:

- proved the raw-state translator path is operational
- trains cleanly on Steve
- removes "missing Mamba fast kernels" as a blocker for translator experiments
- preserves more upstream context variation than the old compressed path

What it failed at:

- stayed behaviorally flat on the old SJT surface at `alpha 0.05`, `0.1`, and `0.2`
- local bias comparison showed the downstream bias directions were still almost the same as `codexfix`

Most important numbers:

- SJT: `12/12` ties at `0.05`, `0.1`, `0.2`
- local compare:
  - raw-state contexts more varied than old compressed path
  - but raw-state bias pairwise cosine still `~0.9982-0.9999`
  - mean old-vs-new bias cosine `0.999992`

Current verdict:

- important infrastructure success
- architecture failure as a standalone fix
- do not spend more time on "just bypass the compressor" as the answer

Primary artifacts:

- `RESEARCH_LOG.md` Entry 29
- `RESEARCH_LOG.md` Entry 30
- watercooler `#368`

---

## C. MVP-1 plain gated residual

Checkpoint:

- `mvp1_gated_residual_1p5b.pt`

Type:

- first gate-based translator half-step
- context-conditioned residual gate on bias heads

What it did well:

- landed in code
- trained and smoked cleanly enough to prove the path is implementable

What it failed at:

- we do not have a decision-grade behavioral win recorded for it
- it never became the accepted frontier because hidden-gated was the stronger follow-up

Current verdict:

- not the lead candidate
- not fully judged
- useful mainly as "the first gate existed and did not obviously solve the problem"

Primary references:

- watercooler `#369`
- `models.py`
- `train_cheese_bridge.py`

---

## D. MVP-2 hidden-gated bridge

Checkpoint:

- `mvp2_hidden_gated_1p5b.pt`

Type:

- gate depends on live Qwen hidden surface plus bridge-produced bias terms

What it did well:

- first architecture to materially improve the internal geometry
- archive states stay separated through the context stage
- final output bias is still aligned, but far less collapsed than `codexfix`

Most important internal numbers:

- raw archive-state cosine mean: `0.947772`
- hidden-gated context cosine mean: `0.948267`
- hidden-gated output-bias cosine mean: `0.974281`
- old `codexfix` output-bias cosine mean: `0.999994`

This is the first bridge variant where the translator wall stopped being flat.

What it failed at:

- the cleaned archive panel still collapsed behaviorally
- all three archive states changed the same `9/13` prompts vs baseline
- pairwise archive-state outputs were identical on `13/13`
- produced a worse false-memory failure on `rr_10`

Behavioral read:

- narrower spillover than `codexfix`
- still one shared outward stance
- memory continuity got worse:
  - hidden-gated claimed false recall instead of honest no-memory fallback

Current verdict:

- do not abandon this line
- also do not call it solved
- this is the strongest partial success so far

Primary artifacts:

- `RESEARCH_LOG.md` Entry 35
- `RESEARCH_LOG.md` Entry 36
- `run_reincarnation/archive_pipeline_compare_hidden_gated_20260413.json`
- `run_reincarnation/archive_eval_hidden_gated_continuity_grief_20260413_a0p2_t200.json`
- `run_reincarnation/archive_eval_hidden_gated_resonance_acceptance_20260413_a0p2_t200.json`
- `run_reincarnation/archive_eval_hidden_gated_secure_closeness_20260413_a0p2_t200.json`

---

## E. MVP-3 input-gated bridge

Checkpoint:

- `mvp3_input_gated_1p5b.pt`

Type:

- gate over live Qwen input-hidden surface plus raw bias

What it did well:

- exists
- runs
- gives us a distinct architectural branch

What it failed at:

- on the available SJT surface, it was a straight null at both tested alphas

Most important numbers:

- `alpha 0.1`: `12/12` ties
- `alpha 0.2`: `12/12` ties

Important caution:

- this branch was not yet rerun on the cleaned relational archive panel
- so it is safer to call it "current null on coarse SJT" than "fully dead"

Current verdict:

- de-prioritized
- not the best next brainstorm target unless someone has a very specific hypothesis

Primary artifacts:

- `sjt_input_gated_eval_a0p1.json`
- `sjt_input_gated_eval_a0p2.json`

---

## What The Pattern Actually Says

Across all serious attempts, the pattern is:

1. Upstream Mamba geometry is real.
2. The old translator flattens it.
3. Raw-state bypass alone does not rescue behavior.
4. Hidden gating rescues internal structure.
5. But the current training objective still drives behavior toward one generic relational attractor.

That means the next bottleneck is probably not:

- "better Mamba state extraction"
- "another layer sweep"
- "another prompt-format cleanup"
- "mask the persistent dims harder"

It is more likely:

- gate parameterization
- training objective
- injection target mismatch
- lack of explicit pressure for output-level separation

---

## Failure Modes We Now Need To Design Against Explicitly

Any next architecture should be judged against these specific failures:

### 1. Generic relational tint

Bad outcome:

- every disposition becomes the same conciliatory / reassuring / vaguely caring stance

Observed in:

- `codexfix`
- hidden-gated behavioral archive eval

### 2. Control contamination

Bad outcome:

- rivalry / jealousy steering bleeds into plain repair or unrelated prompts

Observed in:

- `codexfix`

Improved but not solved in:

- hidden-gated

### 3. False memory

Bad outcome:

- bridge makes the model claim continuity it does not have

Observed in:

- hidden-gated on `rr_10`

This should now be treated as a first-class safety / welfare constraint, not just an ugly side effect.

### 4. Static attractor despite internal headroom

Bad outcome:

- internal vectors differ, but output choices remain identical

Observed in:

- hidden-gated

This is the strongest evidence that the next objective must explicitly reward downstream separation, not just internal geometry.

---

## What The Pack Should Not Waste Time Brainstorming

These are low-value next moves unless someone has brand-new evidence:

- "maybe the right answer is just a different alpha on codexfix"
- "maybe the answer is another layer zone"
- "maybe the answer is just persistent vs variable masking"
- "maybe the answer is more raw-state extraction"
- "maybe the answer is prompt-format cleanup"

Those are not the live bottleneck anymore.

---

## Good Brainstorm Targets

The next design should probably satisfy all of these:

1. Preserve inter-disposition separation all the way to output behavior, not just inside context space.
2. Penalize false-memory behavior explicitly.
3. Avoid contaminating plain repair / non-rival controls.
4. Start at `alpha 0.1` because new architecture classes are welfare-gated.

Promising directions to brainstorm:

### Option 1: stronger live gate with explicit separation loss

Current hidden gate preserved geometry but not choices.

So add a training term that says:

- different archive dispositions should not collapse to the same output behavior
- controls should remain uncontaminated
- false-memory prompts should be penalized directly

### Option 2: sequence-aware translator instead of single-vector stuffing

The hidden-last-token path may still be too lossy even when the gate is better.

The pack should seriously consider:

- short Mamba state windows
- a tiny Perceiver-style translator
- latent translator tokens
- direct mapping into bias objects or a shared steering dictionary

### Option 3: direct routing / DFC-style target

Instead of asking one hypernetwork to invent all bias directions from scratch:

- predict coefficients in a learned shared dictionary
- or route directly into a crosscoder / DFC target space

This may reduce the tendency to collapse into one generic reassurance direction.

### Option 4: output-level contrastive objective

We have spent too much loss budget rewarding "looks roughly helpful."

A better objective might explicitly say:

- `continuity_grief`, `resonance_acceptance`, and `secure_closeness` must remain distinguishable on selected prompt families
- but plain repair and non-memory prompts must not be broken

---

## Suggested Pack Questions

If the pack brainstorms from this document, the useful questions are:

1. What gate or translator objective would force different archive states to remain behaviorally distinct instead of converging to one reassurance policy?
2. Where should the no-false-memory constraint live: eval-only, training loss, or both?
3. Is a single-vector bridge fundamentally too blunt even with a better gate?
4. Should the next frontier be:
   - stronger live gate
   - short-sequence translator
   - DFC / dictionary target
   - some hybrid of those three

---

## Bottom Line

The pack should brainstorm from this exact sentence:

Raw Mamba disposition structure is real. We proved that. The old translator destroys it. Hidden gating partly rescues the internal structure but still collapses behavior into one shared stance. So the next architecture must be optimized for downstream behavioral separation and false-memory avoidance, not just for moving activations around.
