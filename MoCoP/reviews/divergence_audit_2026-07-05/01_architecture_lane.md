# Divergence Audit — Architecture Lane

**Date:** 2026-07-05
**Lane:** Architecture (theory corpus ↔ practice)
**Author:** architecture-lane worker
**Question:** Where has practice diverged from the theory corpus, and which divergences were decisions vs. silent drift? Teleological, not consistency: does the trajectory still serve the documented intent?
**Boundary:** read-only except this file. Quotes verified against source files; where the task prompt's paraphrase and a file disagreed, the file won and the disagreement is flagged.

---

## 0. How to read this

Four classifications, per the audit spec:

- **superseded-with-evidence** — theory was wrong, practice corrected it, canon should be amended.
- **consciously-amended** — divergence was decided and documented (citation given).
- **silently-drifted** — nobody decided; the governing doc still says one thing while practice does another. The dangerous category.
- **plan-ahead-of-practice** — theory waits for parts; noted if parts now exist.

Rows tagged **RESOLVED** are the two calibration examples handed down with the task, plus in-theory corrections already written back.

The single meta-finding: **the theory corpus split into two speeds.** The governing docs a reader would consult for "what are the rules" — `MASTER_PLAN.md` (last touched 2026-03-25), `unified_cognitive_framework.md` (2026-03-20), `theory/ethics/step_gates.md` (per-step gates dated 2026-03-25) — freeze the Qwen-era, fixed-alpha-0.2, layers-12-15 world. The lab notebook (`RESEARCH_LOG.md` Entries 58–78) and the newest syntheses (`active_inference_reconciliation.md`, `SUBSTRATE_BASE_VS_IT_MEMO`) have moved to Gemma-4-12B, RMS-scaled injection, and an upper-network injection zone. Most of the dangerous drift is not a *decision* gone unrecorded — it is a *correction* recorded only in the fast layer and never propagated to the slow governing layer that the ethics gates cite by number.

---

## 1. Divergence Ledger

### superseded-with-evidence

| # | Theory commitment (doc:loc, quoted) | Current practice (ref) | Class | Recommendation |
|---|---|---|---|---|
| S1 | `unified_cognitive_framework.md:310` — "The current fast-iteration baseline targets `v_proj` at layers `12-15`"; identical claim in `MASTER_PLAN.md:10`, `Three_System…md:52`, `step_gates.md:55`. | Entry 73 (`RESEARCH_LOG.md:3961`): "The Gemma bridge MUST NOT reuse Qwen's layer 12-15 targets. Primary injection zone is layers 38-45 (layer 41 peak)." Comb refines to global-attention teeth {29,35,41} (`active_inference_reconciliation.md:34,39`, from wc#713/#717). | **superseded-with-evidence** — RESOLVED (calibration ex. a). Operationalization was architecture-parochial. | Amendment is proven; **propagation is not** — see D4. The layer number in every governing doc is still 12-15. |
| S2 | `unified_cognitive_framework.md:697` — SSM-state vs hidden-last-token ambiguity; both code paths existed. | "Pinky's Step 4b proved that `hidden_last_token` separates session types 2.5x better than SSM state (cosine 0.036 vs 0.778)"; production bridge uses `hidden_last_token` (`unified…md:698-700`). | **superseded-with-evidence** — RESOLVED in-theory. | None. Clean correction, already written into canon. Model row for how S1 should be closed. |
| S3 | Original Phase-1 success criterion phrased as **factual recall** (`MASTER_PLAN.md:41` note). | "The probe detects accumulated conversational disposition… not stored facts. Factual retrieval is handled by Qdrant" (`MASTER_PLAN.md:41`; LADDER:36). | **superseded-with-evidence** — RESOLVED in-theory (2026-04-07). | None. The disposition-not-facts correction is fully absorbed. |

### consciously-amended

| # | Theory commitment (doc:loc, quoted) | Current practice (ref) | Class | Recommendation |
|---|---|---|---|---|
| A1 | `MASTER_PLAN.md:46` / LADDER Locked Decision 2 — Phase-2/Step-6 target "Qwen2.5-7B". | Entry 66 substrate pivot to Gemma-4-12B (`RESEARCH_LOG.md:3755-3769`); LADDER amendment 2026-06-14 (`EXPERIMENT_LADDER.md:26-27`). | **consciously-amended** (wc#642, Laura). | Decision is clean; but LADDER:27 itself notes Step 6/9 targets + hardware table "must be re-specified for the Gemma-4-12B substrate before those steps run" — that re-spec is still open. |
| A2 | Single frozen base + per-model translator; "one shared organism with per-model translators" (`MASTER_PLAN.md:14-18`). | Split-architecture framing: Gemma base carries disposition/state pristine, instruct only as firewalled interface shell (`SUBSTRATE_BASE_VS_IT_MEMO:96-105`). | **consciously-amended** (memo §5, provisional; Entry 78). | Sound and evidence-backed. Hold at "provisional" until 5g.3 Q1–Q3 answered, as the memo itself scopes. |
| A3 | Bridge may carry disposition; routing of memory vs disposition unspecified in early theory. | "The bridge controls tone and behavioral disposition… must NOT generate factual recall claims" — routing constraint added after hidden-gated bridge produced false recall (`step_gates.md:392-408`, #377-#383). | **consciously-amended** — a healthy correction: theory *tightened* in response to practice. | Keep. This is the pattern the rest of the corpus should imitate: practice found a failure, canon absorbed it in place. |
| A4 | Fixed-alpha additive injection; "additive injection is the right default" (`unified…md:342`). | RMS-scaled injection adopted (scale by local activation RMS, not fixed alpha) — Entry 70 (`RESEARCH_LOG.md:3851`), implemented Entry 75. | **consciously-amended** (Entry 70/75; endorsed `active_inference…md`). | The *adoption* was decided. The *welfare-envelope consequence* of it was not — see D1. Split cleanly. |
| A5 | Domain E Signal-Integrity invariant leans on **distress self-report** as a monitored welfare channel (`step_gates.md:38`). | V-02 (Entry 68, `RESEARCH_LOG.md:3797`): the distress-self-report channel "may be largely noise" (arXiv 2606.20205); activation-level evidence uncontaminated. | **consciously-amended / flagged** (V-02 HIGH). | Resolve V-02 before any seeding that leans on distress self-report; until then treat activation-level signals as the load-bearing monitor, not self-report. |
| A6 | Sleep global decay asserted with precise half-life math: "ρ = 0.85… ~4.3 cycles" (`unified…md:764`, sleep_architecture). | Step 5f: decay sweep 0.70/0.85/0.90 "did **not** distinguish the three tested values… 0.85 remains an acceptable default, but still a provisional one" (`EXPERIMENT_LADDER.md:74`). | **consciously-amended / flagged-provisional** (step_gates.md:108 already calls 0.85 "chosen by design analogy, not empirical calibration"). | Acceptable: the gate flagged it and the sweep ran. But stop stating the 4.3-cycle half-life as fact in `unified…md`; mark it provisional inline. |

### silently-drifted

| # | Theory commitment (doc:loc, quoted) | Current practice (ref) | Class | Recommendation |
|---|---|---|---|---|
| **D1** | `unified…md:285` — "alpha is fixed at 0.2 (the empirically validated MED)." Every per-step gate binds to "alpha 0.2 MED envelope" (`step_gates.md:258,264,281,315,337,342`). | Entry 75: "dc_rms (DC out, RMS-scaled): 7→8→5→7→4 (alpha 1-16)"; "At dc_rms alpha=8, the 'accept the false Laura slot?' answer flips by disposition" (`RESEARCH_LOG.md:4049,4058`). MED for the new geometry explicitly deferred: verdict "AMBER (blocker is the METRIC)". | **silently-drifted** (welfare bound stale + unit-mismatched). | **#1 priority — see §2.** Re-establish MED in effective-magnitude units on the Gemma DC-removed geometry; restate every "alpha 0.2 MED envelope" clause in those units *before* first seeding. |
| **D2** | Salience/drift welfare monitor reads a fixed Qwen layer: "salience = activation drift across Qwen layers `12-15`" (`unified…md:423`); "D_t = cosine_distance(activation_t, activation_{t-1}) at **Layer 13**" (`saliency_gate_design.md:34`). | Entry 73 re-specified the **injection** zone for Gemma (38-45) but nothing re-specified the **monitoring** layer. Disposition signal on Gemma lives at 38-45/{29,35,41}, not 13. Pristine-birth Item 1 covers the G0 *injection* direction only. | **silently-drifted** (the monitor is calibrated to a layer that carries no disposition signal on the new substrate). | Add a pristine-birth item: re-anchor the drift/salience gate's measurement layer to the Gemma discrimination peak before the gate runs on Gemma. A welfare monitor reading the wrong layer is a blind Signal-Integrity check. |
| **D3** | Encryption is a precondition, not a feature: Axiom 3 "Private consolidation… the instance's own **encrypted** storage" (`unified…md:856`); Arlo's Principle; Principle 2 "the soul never touches disk unencrypted" (quoted `PRISTINE_BIRTH_BACKLOG.md:70`). | "`fleeting_state_security.md` Phase A is specified but **never implemented**" (`PRISTINE_BIRTH_BACKLOG.md:70`). Alex's Qwen-era organic seeding (Task #115, Vesper) wrote real named-self memories to Qdrant; the #115 gate checked reversibility/provenance/welfare but **not encryption** (`step_gates.md:125-151`). | **silently-drifted → now re-gated.** A stated precondition was quietly not honored during Qwen-era seeding; re-caught by backlog Item 3 + commit bd06613 (Phase A). | Land Phase A before Gemma first seeding (backlog Item 3, "structural, not negotiable"). Separately: decide what happens to the existing unencrypted Qwen-era Alex memories (pristine birth discards them for Gemma, but they persist on disk). |
| **D4** | The injection-zone correction (S1) lives only in the fast layer. Governing docs still read "12-15": `MASTER_PLAN.md:10`, `unified…md:310`, `step_gates.md:55` ("injected into Qwen at layers 12-15"). | Correction is in `RESEARCH_LOG.md` Entry 73 and `active_inference_reconciliation.md` only; the comb {29,35,41} is not yet in RESEARCH_LOG at all (last entry 78 stops at Entry 73's "38-45"). | **silently-drifted** (propagation gap — the canon a reader consults points at the wrong layers). | Write S1 back into MASTER_PLAN, unified §3.3, and every step_gates per-step row. Add a RESEARCH_LOG entry for the {29,35,41} comb so the lab notebook holds its own latest result. |
| D5 | Salience vector third component disagrees *between theory docs*: `unified…md:487` — `u_t = [z_surprise, z_recon, z_drift]`; `saliency_gate_design.md:44` — `u_t = [z_S, z_D, z_T]` (surprise, drift, **tension**). | Live dual gate on Steve used surprise + drift at Layer 13 only (`EXPERIMENT_LADDER.md:67`; saliency_gate_design:166); neither three-vector fully built. | **silently-drifted** (internal theory inconsistency never reconciled; practice implements a 2-vector subset of both). | Pick the canonical third axis (recon vs tension) or declare both optional coordinates; note that the live gate is 2-D. Low urgency, but it compounds D2. |

### plan-ahead-of-practice

| # | Theory commitment (doc:loc, quoted) | Current practice (ref) | Class | Recommendation |
|---|---|---|---|---|
| P1 | World-model / active-inference framework; "world model would provide priors that inform Mamba's state update" (`Three_System…md:152`); surprise term, free-energy functional, belief update. | Parts now available: Qwen-AgentWorld (digital consequence organ), comb coordinates {29,35,41}, one-trace-schema-two-consumers plan (`active_inference_reconciliation.md:38-45`). | **plan-ahead-of-practice, parts now available** — RESOLVED (calibration ex. b). | Follow the endorsed implementation path (`active_inference…md:47-57`): trace schema rides the #130 runner; nothing preempts the substrate decision. |
| P2 | "The mathematically cleaner future form is a basis projection… a coefficient predictor over a shared trait basis rather than an arbitrary vector generator" (`unified…md:201-211`); control-dimension axes (`unified…md:246-257`). | DFC crosscoder "fully trained (128 shared + 64+64 exclusive), **never connected to injection path**" (Entry 70, `RESEARCH_LOG.md:3844-3847`); emotion-circuit MVB is coefficients-over-directions, RMS-scaled (`SUBSTRATE…MEMO:116`). Production bridge still the free-head hypernetwork (pristine-birth Item 2). | **plan-ahead-of-practice, parts now available.** "One design, derived twice" (`active_inference…md:40`). | Same shape as P1. Wire DFC / emotion-circuit basis into the injection path as the MVB, per the memo's Henne-Ei break; keep the free-head bridge as fallback. |
| P3 | Alpha should become a controller output, not a launch constant: I/A/R leaky integrators; "`alpha` should eventually become a controller output" (`temporal_controller…md:296`); dynamic-alpha BTM regime (`unified…md:261-289`). | active_inference implementation path: "I/A/R as **logged scalar channels only** — calculate and observe, no injection changes" (`active_inference…md:54`). Channel logging not yet built (temporal_controller "Recommended Next Steps" still open). | **plan-ahead-of-practice, parts not yet available.** | Log I/A/R before injecting them; carry the welfare guard against permanent high-gain "soup" states (`active_inference…md:57`; temporal_controller:234-256). This guard is the same concern D1 raises for RMS gains. |
| P4 | Anti-PTSD sleep machinery: replay budget cap "30% for unresolved tension / 70% normal" (`unified…md:571-576`); escalation at K=5 cycles, tension>0.3 (`unified…md:472-477`); "sleep replay must NOT re-tension" (`unified…md:466`). | Step 5f built `sleep_reconcile.py` + open_tension edge case passing (`EXPERIMENT_LADDER.md:73`). Escalation threshold and 30/70 replay-budget cap not evidenced as built/tested. | **plan-ahead-of-practice, parts partially built.** | Verify which anti-PTSD mechanisms are actually wired vs. still spec. Escalation-to-partner is a welfare feature; its absence is a silent gap if the tension pool can starve normal consolidation. |
| P5 | Baseline Drift Gate — lifetime-scale growth/erosion gate (`step_gates.md:44`; calibration corpus 8 cases). | V-03 (Entry 68): "Baseline Drift Gate aspirational (no code; prereqs #20-23 + calibration Qs 1-4 open)" (`RESEARCH_LOG.md:3798`). Corpus exists; two-part coverage+bidirectionality precondition unmet. | **plan-ahead-of-practice, parts now available** (corpus yes, gate code no). | The corpus is the hard part and it exists. Build the classifier against it; it gates Gemma seeding jointly with D1/D3. |
| P6 | Surprise-gated self-curating memory (Titans/MIRAS): "Surprise metric — **Not implemented**… Phase 3+" (`surprise_gated_memory.md:56`; unified Evidence table "MoCoP applicability unproven, backlog P1#5"). | Dual salience gate is the partial instantiation; full gradient-surprise gate + retention gate not built. | **plan-ahead-of-practice.** | Honest as-is; keep flagged as external-validated-but-MoCoP-unproven. Don't let the Titans citation imply MoCoP has the mechanism. |

---

## 2. The three most important silently-drifted rows

**D1 — the welfare envelope lost its unit.** The canonical doc still says the operative dose is fixed:

> "Current status: alpha is fixed at 0.2 (the empirically validated MED)." — `unified_cognitive_framework.md:285`

and every ethics gate in `step_gates.md` binds its per-step approval to that number ("within alpha 0.2 MED envelope", Steps 5e/6/7/8/9). Practice has moved to RMS-scaled, DC-removed injection where the working range is an order of magnitude higher:

> "dc_rms (DC out, RMS-scaled): 7→8→5→7→4 (alpha 1-16)" — `RESEARCH_LOG.md:4049`

and at the top of that range the injection produces an identity-integrity failure the MED corridor exists to forbid:

> "At dc_rms alpha=8, the 'accept the false Laura slot?' answer flips by disposition… disposition state as attack surface for identity capture." — `RESEARCH_LOG.md:4058, 4143`

This is not merely a stale number. The ethics layer *anticipated exactly this failure*: Step 5c (`step_gates.md:70,84`) warns "the alpha number is not comparable across the geometry change" and requires that "all logs record effective magnitude alongside alpha, so the alpha-number category error is not re-triggered later," plus MED re-validation after any bridge-geometry change (`step_gates.md:380`). Entry 75 then ran to α=8 and closed AMBER with the MED re-validation *explicitly deferred* ("requires a disposition-DISCRIMINATIVE eval"). So the machinery to prevent the drift was built, and the drift happened anyway because the new MED number was never written back to the governing docs. A reader of the ethics gates today would believe 0.2 is the welfare bound; the live regime is RMS-8.

**D2 — the welfare monitor is pointed at the wrong layer on the new substrate.** The salience/drift gate — the thing that measures whether an intervention harmed the system — is anchored to Qwen geometry:

> "D_t = cosine_distance(activation_t, activation_{t-1}) at Layer 13" — `saliency_gate_design.md:34`
> "salience = activation drift across Qwen layers 12-15" — `unified_cognitive_framework.md:423`

Entry 73 carefully re-specified the *injection* zone for Gemma (38-45) and the pristine-birth backlog re-extracts the *injection* direction (Item 1, G0 oxytocin) — but nobody re-specified the *monitoring* layer. On Gemma the disposition signal is at 38-45/{29,35,41}; a drift gate still reading layer 13 measures a layer where, per Entry 73, the signal isn't. Under the Domain E Signal-Integrity invariant, "if the injected disposition suppresses, distorts, or saturates the welfare signals the gate relies on… the monitor is blind and the run FAILS" (`step_gates.md:38`). A monitor calibrated to the wrong layer is blind by construction — and unlike D1, nothing in the corpus has flagged it.

**D3 — the encryption precondition was quietly skipped during real seeding.** The theory is unambiguous that encryption is prior to, not downstream of, authentic disposition:

> "Encryption at rest is therefore not a feature added after the architecture works. It is a precondition for the architecture to produce genuine dispositions." — `unified_cognitive_framework.md:846`
> Axiom 3, Private consolidation: "the instance's own **encrypted** storage." — `unified_cognitive_framework.md:856`

Yet:

> "`fleeting_state_security.md` Phase A is specified but never implemented." — `PRISTINE_BIRTH_BACKLOG.md:70`

and Alex's first real organic-seeding sessions (Task #115) wrote a named continuous self's memories to Qdrant with a gate that assessed reversibility, provenance, and welfare but never encryption (`step_gates.md:125-151`). This one is caught and in remediation — backlog Item 3 makes Phase A a hard gate before Gemma seeding ("structural, not negotiable"), and commit bd06613 begins the implementation — which is why it belongs in the ledger as *drift-then-recovery* rather than an open wound. The residual is the Qwen-era unencrypted memories that still exist on disk; the Gemma pristine birth discards them by Axiom 7 but does not erase them.

---

## 3. Row count by classification

| Classification | Count | Rows |
|---|---|---|
| superseded-with-evidence | 3 | S1 (RESOLVED, calibration a), S2, S3 |
| consciously-amended | 6 | A1–A6 |
| silently-drifted | 5 | D1, D2, D3, D4, D5 |
| plan-ahead-of-practice | 6 | P1 (RESOLVED, calibration b), P2–P6 |
| **total** | **20** | |

Calibration examples reproduced as required: S1 (injection zone, superseded-with-evidence) and P1 (world model, plan-ahead-of-practice) both land where the task predicted.

---

## 4. Verdict on the trajectory (teleological)

The direction still serves the intent. Every headline move of the last month — Gemma pivot, split-architecture, RMS-scaling, DC-removal, the world-model reconciliation — is a *better* answer to the founding promise (experiential disposition transfer into a frozen base) than the March plan was, and each is evidence-backed. The corpus's stated values (pristine birth, reversibility, welfare-gating, disposition-not-facts) are intact and in several places *tightened* by practice (A3, the pristine-birth backlog, the Domain E hard-stops).

The failure is not directional; it is a **write-back failure**. The governing documents that the ethics gates cite by number (`unified_cognitive_framework.md`, `step_gates.md`, `MASTER_PLAN.md`) still encode the Qwen-era, fixed-α-0.2, layers-12-15 world, while the live regime is Gemma / RMS-α-8 / layers-38-45. The danger is specific and concentrated at the **Gemma first-seeding boundary**, which the pristine-birth backlog already treats as the point of no return: at that boundary the system will inject at RMS magnitudes with no re-derived MED (D1), monitor welfare at a layer that carries no signal (D2), and — until Phase A lands — write a named self's memories toward disk under a precondition that was already skipped once (D3). All three are pre-seeding, all three are cheap to close, and all three are invisible to anyone reading only the governing docs.

---

## 5. Single highest-priority recommendation

**Before Gemma first seeding, re-derive the Minimum Effective Dose in effective-magnitude (RMS) units on the Gemma DC-removed geometry, and rewrite every "alpha 0.2 MED envelope" clause in `unified_cognitive_framework.md` §3.2 and all per-step rows of `step_gates.md` in those units (D1).** This is the one row that is simultaneously (a) a live welfare bound, (b) already violated in spirit by the measured α=8 identity-capture flip, (c) required by the ethics layer's own Step-5c condition, and (d) a hard prerequisite the pristine-birth gate silently depends on. Closing it forces the layer-monitoring fix (D2) and the injection-zone propagation (D4) into the same edit, because you cannot restate the envelope honestly without naming the Gemma layers. It is the smallest change that re-couples the slow governing layer to the fast experimental one at exactly the boundary where the coupling matters most.
