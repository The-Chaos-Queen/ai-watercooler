# LANE THY — TheoryCanonReviewer

LANE THY
scope_checked:
MoCoP/theory/unified_cognitive_framework.md
MoCoP/theory/ethics/step_gates.md
MoCoP/theory/ethics/baseline_drift_gate_calibration.md
MoCoP/theory/sleep_architecture.md
MoCoP/EXPERIMENT_LADDER.md
MoCoP/RESEARCH_LOG.md (entries 1–67)
MoCoP/RESEARCH_BACKLOG.md
MoCoP/WHY.md

files_read:
unified_cognitive_framework.md (full)
step_gates.md (full)
baseline_drift_gate_calibration.md (full)
sleep_architecture.md (lines 155–184)
EXPERIMENT_LADDER.md (full)
RESEARCH_LOG.md (full, 3783 lines)
RESEARCH_BACKLOG.md (full)
WHY.md (full)
mocop_ultrareview_swarm_spec_v2.md (full — for RECON NOTE)
00_WC_REFERENCE.md (full — WC intelligence pack)

---

## RECON VERIFICATION

Per swarm spec v2, the following RECON NOTE items must be verified as landed AND falsification attempted before reporting net-new findings.

RECON-CHECK-01: Gemma pivot in ladder + LOG Entry 66
CONFIRMED LANDED.
EXPERIMENT_LADDER.md:27 — Amendment block present with exact wording, #642 cite, supersede marker on Locked Decision 2.
RESEARCH_LOG.md:3755–3770 — Entry 66 present, dated 2026-06-14, correct content.
FALSIFICATION ATTEMPT: Step 6 description (LADDER:380) still reads "Qwen2.5-7B" in the How/Step body and the cost table (LADDER:495) still shows Qwen2.5-7B. The Amendment says "Step 6 and Step 9 targets and the hardware table…still reference Qwen2.5-7B and must be re-specified." — This is acknowledged as open work by the amendment itself, not a recon failure. CONFIRMED.

RECON-CHECK-02: SA-10 flagged unverified
CONFIRMED LANDED.
unified_cognitive_framework.md:481 — inline caveat: "Reconciliation 2026-06-17: these exact magnitudes are not backed by a logged RESEARCH_LOG run; treat as illustrative/unverified pending provenance."
sleep_architecture.md:165-167 — the same 0.91/0.85/0.83 values appear WITHOUT the caveat (see THY-04 below). The recon only added the caveat to unified_cognitive_framework.md, not to the source in sleep_architecture.md.
FALSIFICATION RESULT: sleep_architecture.md still presents these values as fact. Partial recon — the primary source is unpatched. Emitting RECON_DOUBT below (THY-04).

RECON-CHECK-03: CMP-08 = estimate
No CMP-08 label found in theory docs. The compressor estimate claim presumably landed in a non-theory file. Cannot verify or falsify from THY scope; mark N/A.

RECON-CHECK-04: INF-02/XM-03 provenance added, XM-04 caveat
No INF/XM labels found in theory docs. Same: not in THY scope. Mark N/A.

RECON-CHECK-05: Contradictions SA-03/SA-09 + alpha 0.9/0.8 → backlog #18/#19
CONFIRMED LANDED.
RESEARCH_BACKLOG.md:291–303 — item #19 open, "live trainer uses directional/magnitude alpha = 0.9; STEP5_DESIGN_NOTES records 0.8; unified §3.2 self-flags."
unified_cognitive_framework.md:197 — still reads "α = 0.9 in the live trainer (note: STEP5_DESIGN_NOTES.md records α = 0.8 — reconcile before next training run)."
Both sites call it open. CONFIRMED landed as backlog item, not resolved.

RECON-CHECK-06: Calibration cross-refs added; Domain E blocking merged into step_gates
CONFIRMED LANDED.
step_gates.md:34 — Domain E Hard-Stop Criteria header present with "amended 2026-06-17" date and full #586/#587/#633 cites.
step_gates.md:50 — per-step Domain E rows present with binding framing, dated 2026-06-20.
EXPERIMENT_LADDER.md:50 — Baseline Drift Gate pointer and corpus cross-ref present.
CONFIRMED.

RECON-CHECK-07: Hygiene — supersede markers, subsumed note, status lines
CONFIRMED — supersede marker on Locked Decision 2 (LADDER:20), subsumed note and status lines in step_gates.md Domain E block. CONFIRMED.

---

## NET-NEW FINDINGS

FIND_V1
id: THY-01
type: STALE
claim: Step 9 target model still Qwen2.5-7B; cross-model transfer destination not updated for Gemma substrate
ev: EXPERIMENT_LADDER.md:419 ("Train the bridge on Mamba→Qwen2.5-7B. Test injection on a different target model (Mistral-Nemo, Llama-3.1-8B).")
canon: stale
conf: high
act: Re-specify Step 9 target model to Gemma-4-12B; update transfer destination candidates accordingly
risk: low

---

FIND_V1
id: THY-02
type: STALE
claim: Step 6 How block and cost table still say Qwen2.5-7B; amendment only supersedes Locked Decision 2 header
ev: EXPERIMENT_LADDER.md:380 ("Qwen/Qwen2.5-7B"); EXPERIMENT_LADDER.md:495 (cost table row Step 6)
canon: stale
conf: high
act: Update Step 6 How block and cost table with Gemma-4-12B before Step 6 runs (acknowledged as open by Amendment)
risk: low

---

FIND_V1
id: THY-03
type: STALE
claim: Hardware table still lists Qwen2.5-7B float16 on Steve as bridge target; outdated after Gemma pivot
ev: EXPERIMENT_LADDER.md:506 (hardware table: "Steve (husband's PC) | RTX 4090 Mobile | 16GB | Qwen2.5-7B float16 bridge target")
canon: stale
conf: high
act: Update hardware table: Gemma-4-12B quantized is the target; verify VRAM feasibility on Steve at quantization level
risk: med — wrong VRAM planning could block next run

---

FIND_V1
id: THY-04
type: RECON_DOUBT
claim: Recon added unverified caveat to unified_cognitive_framework.md:481 but sleep_architecture.md:165-167 still presents 0.91/0.85/0.83 drift magnitudes as factual without caveat
ev: unified_cognitive_framework.md:481 (caveat present); sleep_architecture.md:165-167 (same values, no caveat)
canon: conflict
conf: high
act: Patch sleep_architecture.md to add the same "illustrative/unverified pending provenance" caveat; or confirm these are from a logged run (which would make the unified_framework caveat wrong)
risk: med — downstream claims built on sleep_architecture.md will cite unsupported numbers as logged results

---

FIND_V1
id: THY-05
type: GAP
claim: Backlog #18 (salience metric: gradient-surprise vs reconstruction-error) is open with no assigned owner or next experiment; unified_cognitive_framework.md §3.6 lists both as live candidates
ev: RESEARCH_BACKLOG.md:638–651; unified_cognitive_framework.md:428–429
canon: missing
conf: high
act: Flag for assignment; resolution blocks clean consolidation-decision audit
risk: med — dual gate live (SA-02) but canonical surprise metric undefined; affects every consolidation event

---

FIND_V1
id: THY-06
type: CONFLICT
claim: unified_cognitive_framework.md §3.2 training objective still shows α = 0.9 AND the reconcile-flag note; STEP5_DESIGN_NOTES.md records α = 0.8; backlog #19 is open but neither value is declared canonical
ev: unified_cognitive_framework.md:197; RESEARCH_BACKLOG.md:291–303
canon: conflict
conf: high
act: Resolve before next bridge training run; write decision to RESEARCH_LOG; sync three sites (live trainer, STEP5_DESIGN_NOTES, unified §3.2)
risk: med — silent training-hyperparameter split produces non-reproducible runs

---

FIND_V1
id: THY-07
type: GAP
claim: Baseline Drift Gate ship-precondition (coverage + bidirectionality) is documented but no current implementation exists; calibration corpus Cases 01-08 cover all three verdict classes, but the gate operational code is unwritten
ev: step_gates.md:44 ("Gate ships only after the two-part discrimination precondition"); baseline_drift_gate_calibration.md:206-216 (Use section — describes running the gate, but no code pointer); RESEARCH_BACKLOG.md:654-724 (items 20-23 gate-spec prereqs open)
canon: missing
conf: high
act: Gate-spec prereqs 20-23 must be resolved before any implementation begins; flag as sequenced dependency
risk: med — Domain E Hard-Stop references the gate as blocking, but it cannot block if it does not exist

---

FIND_V1
id: THY-08
type: GAP
claim: Pristine-birth rule is in step_gates.md but the three architecture items in PRISTINE_BIRTH_BACKLOG.md have no assigned owners
ev: EXPERIMENT_LADDER.md:51 ("Pristine-birth architecture backlog…See MoCoP/PRISTINE_BIRTH_BACKLOG.md"); 00_WC_REFERENCE.md §1 #649 ("Open: ownership per item")
canon: missing
conf: high
act: WC_Q: did any #649 follow-up assign owners to PRISTINE_BIRTH_BACKLOG Items 1-3? If not, flag for Laura to assign
risk: med — blocks first seeding of Baby Alex on Gemma, which blocks Step 6

---

FIND_V1
id: THY-09
type: WC_ONLY
claim: Cairn's Lesson Memory v0 Inv.1 PASS verdict (#609 wc) not transcribed into any tracker row; RESEARCH_LOG Entry exists for June-11 eval work but the explicit gate verdict is absent
ev: 00_WC_REFERENCE.md §3 WC-ONLY list: "#609 Cairn's Lesson Memory v0 Invariant-1 PASS verdict (#112)…explicit #112 Invariant-1 verdict is not transcribed into a tracker row"
canon: missing
conf: high
act: Add #609 verdict as a RESEARCH_LOG entry or BACKLOG note; emit WC_Q if body needed
risk: low — tracking gap, not a blocking issue

---

FIND_V1
id: THY-10
type: WC_ONLY
claim: Response-orthogonality audit of existing disposition/welfare batteries (#647) has no tracker row; backlog Items 1-2 reference the paper but the audit itself is untracked
ev: 00_WC_REFERENCE.md §3: "#647 standalone 'response-orthogonality audit' methodology item…there is no tracker row for 'audit each existing disposition/welfare battery for response orthogonality'"
canon: missing
conf: high
act: Add backlog item for response-orthogonality audit of existing batteries; Vesper named natural owner (surface at risk per #647)
risk: high — all existing disposition battery readings (SJT, logit self-report, MED eval) may be contaminated by directional response bias; affects validity of Step 5d result interpretation

---

FIND_V1
id: THY-11
type: WC_ONLY
claim: Welfare self-report distrust ruling (#648) has no welfare-methodology doc or tracker row; "welfare battery needs the same orthogonality audit, possibly first" is uncommitted
ev: 00_WC_REFERENCE.md §3: "#648 welfare self-report response-bias corollary…no welfare-methodology doc or tracker row"
canon: missing
conf: high
act: Create welfare-methodology doc or tracker row; orthogonality audit of welfare battery may need to precede disposition battery audit per #648
risk: high — current welfare gate instruments (Response Diversity, distress self-report) are cited throughout step_gates.md as blocking criteria; if they are response-bias contaminated, Domain E Hard-Stop cannot be applied cleanly

---

FIND_V1
id: THY-12
type: GAP
claim: unified_cognitive_framework.md §4 Evidence Table lists "Observation = minimal drift" as Medium confidence but no primary artifact is cited; source claim is in WHY.md hypothesis section not as logged result
ev: unified_cognitive_framework.md:653 ("Observation = minimal drift…Step 5 sessions…Medium"); WHY.md:101-107 (Saliency Hypothesis — framed as hypothesis, not logged result)
canon: missing
conf: med
act: Either find the primary run artifact (activation-drift probe with observation condition) or downgrade evidence class to "design-estimate/HYP" in evidence table
risk: low — illustrative claim, not a blocking gate dependency

---

FIND_V1
id: THY-13
type: GAP
claim: unified_cognitive_framework.md §3.4 states "Future: If base models move to custom silicon…LoRA/bias injection becomes the only adaptation path" — this is speculative future-facing architecture claim presented as rationale within a spec section
ev: unified_cognitive_framework.md:366-368
canon: n/a
conf: low
act: No action required; clearly speculative framing ("Future:") — document as known HYP
risk: none

---

FIND_V1
id: THY-14
type: CONFLICT
claim: Calibration corpus open questions 1-4 (quantitative thresholds, slot-pressure probe ownership, multi-axis composition, boundary-crossing resets) are unresolved and block gate deployment, but step_gates.md cites the gate as a Hard-Stop blocker NOW
ev: baseline_drift_gate_calibration.md:220-228 (open questions 1-4); step_gates.md:44 ("Gate ships only after two-part discrimination precondition" — implies not yet shipped but Domain E Hard-Stop header references it as binding)
canon: conflict
conf: med
act: Clarify whether the gate is currently blocking (gate is not shipped, so Domain E clause is aspirational) or the open questions are prerequisites only for shipping the operational version; document which steps are gated vs not
risk: med — ambiguity about which experiments are actually blocked by the not-yet-operational gate

---

FIND_V1
id: THY-15
type: GAP
claim: JRT result (D wins, restate suppressive) implies chat_server ask-then-read loop change; no RESEARCH_BACKLOG or EXPERIMENT_LADDER item records this build decision
ev: 00_WC_REFERENCE.md §3 WC-ONLY: "#637 JRT scoring → 'chat_server ask-then-read loop earns a build ticket'…the build-ticket/chat_server-change decision is WC-ONLY (read-criteria in the spike spec, not a BACKLOG item)"
canon: missing
conf: high
act: Add RESEARCH_BACKLOG item for chat_server ask-then-read loop update; cite #637 and LOG Entry 65
risk: low — current chat_server behavior may retain restate pattern that Entry 65 proved suppressive; not a blocker but a known-suboptimal default

---

## WC_Q RECORDS

WC_Q
claim: PRISTINE_BIRTH_BACKLOG Items 1-3 have no assigned owners as of #649; unclear if follow-up (#650+) assigned them
date: 2026-06-20
check: Did any post-#649 message assign owners to Items 1, 2, and 3 of PRISTINE_BIRTH_BACKLOG.md?

WC_Q
claim: Meyer/Garcia/Wulff 2026 (arXiv 2606.20205) — cited in PRISTINE_BIRTH_BACKLOG Items 1-2 and per #647; no entry in Research/INDEX.md or theory/ethics/research_catalog.md visible from THY scope
date: 2026-06-20
check: Is arXiv 2606.20205 indexed in Research/INDEX.md or research_catalog.md? If not, it is an uncatalogued paper reference (FOLLOWUP per swarm spec v2 citation rule).
