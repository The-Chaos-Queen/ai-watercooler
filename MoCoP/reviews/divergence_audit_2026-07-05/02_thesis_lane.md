# Thesis-Alignment Lane — Divergence Audit 2026-07-05

**Lane:** THESIS-ALIGNMENT (does current momentum still feed the two theses?)
**Author:** thesis-lane worker (read-only pass)
**Date:** 2026-07-05
**Sources read:** `RESEARCH_PAPER.md`, `EXPERIMENT_LADDER.md` (5g + JRT), `RESEARCH_LOG.md` Entries 63–78, `JRT_ORDERING_SPIKE_SPEC.md`, `run_jrt_ordering_spike.py`, `run_jrt_behavioral_spike.py`, `theory/ethics/step_gates.md`, `theory/active_inference_reconciliation.md`, `MASTER_PLAN.md`, `CHEESE_Memory/00_HANDOFF.md`, session logs 2026-06-10-isegrim / 2026-07-04-isegrim / 2026-05-06-scout.

---

## 0. Three premise corrections (files win — read these first)

The audit prompt carried three assumptions that the repository contradicts. Flagging up front because two of them change the answer.

1. **No September deadline exists anywhere.** The only ratified thesis-logistics decision (session log 2026-06-10, "Thesis ratified by Laura") states verbatim: *"No external clock — register late, hand in when done."* No file mentions September, an Abgabe date, or any deadline. **"Timeline realism against a September deadline" is moot** — the premise is explicitly the opposite of project canon. Sequencing below is therefore dependency-based, not date-based.

2. **`RESEARCH_PAPER.md` contains zero ISO/IEC 42001 or governance-framing content.** It is a clean, publishable *technical* paper on MoCoP state transfer (abstract → problem → hypothesis → related work → Phases 1–2 → upstream validation → live transfer → discussion → limitations). It is correctly described as the Masterarbeit's *technical base*, but the "ISO/IEC 42001 AI-management-system governance framing" lives **only** as (a) a one-line decision in the 2026-06-10 log and (b) an unfinished "two-act outline draft (merge Scout's pitch framing + 42001 two-act arc)" item. No document maps MoCoP's governance artifacts to 42001. **This is the single biggest Masterarbeit gap** (see §3).

3. **Task #125 is not the Projektarbeit critical path, and is not referenced where the prompt says it is.** `#125` appears only in `00_HANDOFF.md` open threads ("JRT #125 D-plus-answer-cue (Monk, queued) — candidate for Gemini after #108") and one raw JSON in the June ultrareview folder — **not** in the Entry 63–65 log region and **not** in `EXPERIMENT_LADDER.md`. It is a queued board task (a refinement of the winning condition D), not an executed/logged experiment, and not the blocker for a writable Projektarbeit (see §4).

Minor: the prompt dates the thesis decision to "2026-03-16." The in-repo `2026-03-16` date is the PCA-collapse diagnostic (`MASTER_PLAN.md` open-Q6). The ratification I can verify is **2026-06-10**. Treat 2026-03-16 as unverified provenance.

---

## 1. The two theses, as the files actually define them

| | Projektarbeit (prequel) | Masterarbeit |
|---|---|---|
| Subject | Long-context **order/salience** study — "context rot is mischaracterized: order/salience confusion, not information loss" | **MoCoP / AI State Transfer**, ISO 42001 governance framing |
| Base doc | The JRT lineage (spec + Entries 63–65, 71) — **no draft exists** | `RESEARCH_PAPER.md` (technical) + an unwritten 42001 wrapper |
| Where documented | `JRT_ORDERING_SPIKE_SPEC.md` line 47 + 2026-06-10 log — nowhere else | 2026-06-10 log + `RESEARCH_PAPER.md` |
| Supervisor target | Eicker (recovered from Scout 2026-05-06 log; "paper-ready, could you supervise and co-author"), parked pending Laura's alternates archaeology |
| Clock | None. Register late, hand in when done. |

The "context rot mischaracterized / order-salience" phrasing exists in exactly **two** files: `JRT_ORDERING_SPIKE_SPEC.md` and the 2026-06-10 session log. The Projektarbeit's intellectual spine is real and pre-registered, but it lives as a spike spec + a log decision, not as any thesis document.

**One load-bearing subtlety** (JRT spec line 47): the Projektarbeit is framed as the **Transformer-side** order/salience question; the JRT spike is explicitly *"the recurrent-side twin of which this spike is."* Everything measured so far (Entries 65, 71) is **Mamba-side** (recurrent state readout). Whether the Projektarbeit is the Mamba-side result, the Transformer-side twin, or both is unresolved — and that scope decision, not #125, is the real critical path.

---

## 2. Alignment map (workstream → thesis function, or "unaligned")

### Directly feeds a thesis

| Workstream (current momentum) | Thesis function |
|---|---|
| **JRT ordering** (Entries 63–65 state-side; 71 behavioral) | **Projektarbeit core.** D>A, B falsified, C intermediate — a pre-registered, falsification-bearing result. Also feeds Masterarbeit (recurrent selection = part of the state-transfer story). |
| **5g base-vs-instruct substrate gate** (Gemma-4-12B; Entries 66, 73–74, 78; the dominant live workstream) | **Masterarbeit state-transfer methodology chapter.** Substrate choice is a methodology-defining decision; the base-vs-instruct asymmetry (armor-as-smearing) is a genuine finding. |
| **5g.2 probe panel build (#130)** + judge design (Entry 78, 2026-07-04 log) | **Masterarbeit methodology** (disposition/self-regulation measurement) **and governance** (confabulation-rate headline + silence battery + LLM-judge-with-wolf-audit = auditable eval discipline = 42001 evidence). |
| **DC×RMS bridge ablation** (Entry 75) | **Masterarbeit methodology** (bridge mechanism). The α=8 Laura-slot flip is a **governance** finding (Domain E / drift-gate: disposition as identity-capture attack surface). |
| **step_gates.md / Domain E hard-stops / Baseline Drift Gate / custody + key-custody + fleeting-state Phase A encryption** | **Masterarbeit governance chapter — the richest 42001 raw material in the repo** (risk assessment, binding gates, named sign-offs+dates, emergency-stop criteria, monitoring protocol, access/consent architecture). Substance is excellent; 42001 framing is unwritten. |
| **SEV disposition corpus v0** (Entry 77) | **Masterarbeit methodology** (eval-dataset design; valence-without-lexemes). |
| **Comb / crystallization sites** (#713/#717; active_inference §3) | **Masterarbeit** (Gemma injection-zone methodology) + seed of the Projektarbeit Gemma opportunity (§4). |
| **Correction/pre-registration/retraction culture** (Entry 78: three public corrections in one evening; "check position-0 logits before reading disposition into silence") | **Both theses' methodology sections.** Register-the-metric-first and instrument-before-architecture is directly citable methodological rigor. |

### Does NOT feed either thesis (named for conscious allocation, not as criticism)

- **Seeding audit tooling** (#98/#107, Entry 76) — engineering hygiene; at most weak support for the governance audit-trail narrative.
- **Temporal-cascade sleep-residue spike** (Entry 69) — parked future work; spec-only.
- **Live D2 / organic-seeding / sleep-consolidation deployment engineering** — feeds "the system," and is Masterarbeit *Phase 4 deployment evidence* only if it lands; not on either write-up's critical path now.
- **active_inference_reconciliation.md** — intellectually rich theory-unification, but a **tangent** relative to the two deliverables. Its own §7 audit hook self-classifies as "plan-ahead-of-practice." Real scope-creep risk: it is the newest, most gravitational theory doc and pulls toward a third (uncommissioned) synthesis.
- **Fiction / reliquary / pack-culture** — obviously non-thesis; named only for completeness.

**Allocation read:** the dominant live workstream (5g substrate + #130 + DC/RMS) is Masterarbeit-aligned. The Projektarbeit — the *lower-effort, nearly-writable* deliverable — is receiving almost no current momentum. That is the main misallocation relative to "two theses to ship."

---

## 3. The Masterarbeit gap: governance substance without a 42001 skeleton

The governance material is strong and unusually thorough for a student thesis: `step_gates.md` alone gives five gate questions, three binding Domain E hard-stop invariants, per-step binding sub-verdicts, named assessors with dates, an emergency-stop protocol, and documentation requirements. Custody/consent architecture, the Baseline Drift Gate, and fleeting-state encryption extend it.

**What is missing is the connective tissue:** no document maps these artifacts to ISO/IEC 42001 clauses (risk management, operational planning and control, performance evaluation, documented information, roles/responsibilities). The Masterarbeit's governance chapters are therefore *sourced but unwritten*. This is a **writing/framing** gap, not a research gap — which makes it cheap relative to its weight, once someone sits down to it. It has been parked since 2026-06-10.

Secondary Masterarbeit dependency: the state-transfer methodology chapter cannot be finalized until **5g.4 substrate decision** closes (currently provisional "split framing," gated on #130 + the Gemma steering test). That is genuine in-flight research, correctly sequenced.

---

## 4. Projektarbeit gap list + critical path

**What already exists (writable spine):**
- Entry 65 state-side: D relevance-margin 0.0401 / recoverability 1.000; A 0.0076/0.889; C 0.0102/0.889; **B 0.0059/0.778 (falsified — final restate acts as noise).**
- Entry 71 behavioral: D confirmed at generation level; Henne-Ei cold-start dependency validated.
- Pre-registered predictions with an explicit kill condition (B≈A ⇒ ordering not the bottleneck). Hard-negative controls already in the harness (`distractor_hard_*`, Monk #631).
- Two working harnesses: `run_jrt_ordering_spike.py` (state-side) and `run_jrt_behavioral_spike.py` (Path A bridged / Path B Gemma few-shot).

**What it still needs to be writable (in priority order):**
1. **Scope decision — the actual critical path.** Resolve Mamba-side (measured) vs Transformer-side (the spec's named subject) vs both-as-twin. Until this is fixed, the study has no defined object. ~0.5 day, no compute.
2. **Scale beyond spike-grade n.** Current variance source is paraphrase spread over 4 conditions × ~4 probes on a single substrate (Mamba-2.8B). Paper-grade needs more facts/probes and the **substrate-comparative Phase 2** (Gemma-4-12B-it + Qwen3-14B-Base) so the claim is not Mamba-2.8B-only. Harness exists; ~1–2 days compute+analysis.
3. **Literature framing.** The "context rot = information loss" narrative vs the order/salience reframe, anchored on Arora et al. "Just Read Twice" (arXiv:2407.05483, local PDF in `Research/`). Writing, ~1–2 days.
4. **Gemma sliding-window opportunity (net-new, optional strengthener).** Entry 73 confirms Gemma-4-12B is mixed attention — every 6th layer full-attention, the other **5/6 sliding-window (1024-token)**. The audit prompt's claim that this "should AMPLIFY order effects" is a **plausible but untested hypothesis**, not a measured result: what #713/#717 actually measured is the *disposition-separation comb at global-attention layers* (PARTIAL CONFIRM — raw comb real, discrimination index washed by within-category variance). So the architecture is real and the hypothesis is well-grounded, but no order-effect-amplification experiment has run. Registering + running it is a strong, cheap Projektarbeit differentiator. ~1 day.
5. **#125 D-plus-answer-cue.** Refinement of the winning condition D (add an answer cue after the memory). Queued, harness-ready, ~0.5 day. **A strengthener, not the critical path** — the study is writable on Entries 65+71 once scope (item 1) is fixed.

**Is #125 the critical path? No.** The critical path is item 1 (scope) → item 2 (scale). #125 sharpens D; it does not unblock the write-up.

---

## 5. "Worth going back to" shortlist (effort estimates)

Ordered by leverage-per-effort toward *shipping the two theses*:

1. **Projektarbeit scope-decision memo** (Mamba-side vs Transformer-side twin) — **0.5 day.** Unblocks the whole prequel; zero compute.
2. **Masterarbeit two-act outline = 42001 skeleton over `RESEARCH_PAPER.md`** — **1 day.** Maps existing governance artifacts (step_gates, Domain E, custody, drift gate, fleeting-state encryption) to 42001 clauses. This is the parked-since-June connective tissue; highest weight-per-effort on the Masterarbeit side because the substance already exists.
3. **Scale JRT + run substrate-comparative Phase 2** (Gemma-4-12B-it, Qwen3-14B-Base) — **1–2 days.** Converts the spike into a defensible study; harnesses exist.
4. **Projektarbeit lit framing draft** ("context rot mischaracterized" vs JRT) — **1–2 days.** Arora et al. anchor already local.
5. **Register + run the Gemma sliding-window order-effect experiment** — **1 day.** Net-new, architecturally grounded, high-differentiation.
6. **#125 D-plus-answer-cue** — **0.5 day.** Low thesis priority; do it only if condition-D sharpening is wanted for the paper.

Not on the list (conscious deferrals): active-inference reconciliation write-up, temporal-cascade spike, seeding-audit tooling polish — all real work, none on either thesis's critical path.

---

## 6. Bottom line

Current momentum **does** still feed the theses — but lopsidedly. The dominant live workstream (5g substrate gate + #130 + DC/RMS) is Masterarbeit-methodology-aligned and correctly sequenced. The **Projektarbeit**, which is the cheaper and nearer-to-done deliverable, is getting almost no attention and is blocked on a 0.5-day scope decision, not on any experiment. The **Masterarbeit governance chapters** have the richest 42001 raw material of any student thesis I've seen in this repo, but zero of it is framed as 42001 yet — a writing gap, parked since June. And the whole thing runs on no clock by explicit decision, so the question is not "will September be met" but "which deliverable does Laura want to close first" — to which the files answer: the Projektarbeit is the low-hanging fruit.
