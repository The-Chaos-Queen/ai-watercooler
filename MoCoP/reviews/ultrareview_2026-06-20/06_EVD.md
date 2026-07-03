# LANE EVD — EvidenceGapArchaeologist
# MoCoP Ultrareview 2026-06-20

LANE: EVD
scope_checked:
  MoCoP/RESEARCH_LOG.md (full; 3783 lines; LOG entries 1–67)
  MoCoP/EXPERIMENT_LADDER.md (full; 521 lines)
  MoCoP/RESEARCH_BACKLOG.md (items 1–23 confirmed)
  MoCoP/theory/unified_cognitive_framework.md (lines 160–660 relevant)
  MoCoP/theory/sleep_architecture.md (lines 160–170 relevant)
  MoCoP/experiments/mamba_lora_bridge/STEP4_VERDICT_2026-03-18.md
  MoCoP/experiments/mamba_lora_bridge/STEP5_DESIGN_NOTES.md
  MoCoP/experiments/mamba_lora_bridge/activation_sessions/ssm_vs_hidden_separation.json
  MoCoP/experiments/mamba_lora_bridge/activation_sessions/mamba_state_separation.json
  MoCoP/experiments/mamba_lora_bridge/activation_sessions/session_comparison.json
  MoCoP/experiments/mamba_lora_bridge/activation_sessions/DISPOSITION_EVIDENCE_2026-03-18.md
  MoCoP/experiments/mamba_lora_bridge/run_reincarnation/C.H.E.E.S.E_Reincarnation_Debrief_20260325.md
  MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_sleep_cycle_default_20260326.md
  MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_open_tension_sleep_cycle_20260326.md
  MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_sleep_cycle_report_20260326T113050.json
  MoCoP/experiments/mamba_lora_bridge/run_reincarnation/opa_reincarnation_t07_140tok_20260325.txt (exists)
  MoCoP/experiments/mamba_lora_bridge/run_reincarnation/opa_reincarnation_t03_140tok_20260325.txt (exists)
  MoCoP/reviews/ultrareview_2026-06-20/02_THY.md (THY lane prior findings, read-only)
files_read: ~30 files; no run/ artifact dirs (run_constant_bias/, run_actbias/, tmp/step5d_20260322/) found on disk — confirmed missing

---

## RECON VERIFICATION (targets: SA-10 downgrade + alpha 0.9/0.8 backlog)

### RECON-CHECK-01: SA-10 flagged unverified
RECON asserts: commit 431b95f added unverified caveat to unified_cognitive_framework.md:481.
Independent hunt: searched all of MoCoP/ for the drift values 0.91/0.83/0.85, for "SA-10", for any run log or JSON that could back them.
FOUND:
- unified_cognitive_framework.md:481 — caveat present: "these exact magnitudes are not backed by a logged RESEARCH_LOG run; treat as illustrative/unverified pending provenance."
- sleep_architecture.md:165-167 — same values (0.91, 0.85, 0.83) presented without caveat.
- No RESEARCH_LOG entry references these three drift magnitudes.
- No artifact file (JSON, txt, pt) found with these values.
- No Watercooler id cited for them in any canon doc.
VERDICT: Downgrade correct on facts. However sleep_architecture.md:165-167 still states values as fact without the caveat added to unified_cognitive_framework.md. Recon was incomplete: it only patched one doc. (THY lane THY-04 independently caught this gap.)

### RECON-CHECK-02: alpha 0.9/0.8 → backlog #19
RECON asserts: contradiction tracked as backlog item #19.
Confirmed: RESEARCH_BACKLOG.md item #19 exists at line ~290-303, correctly describes "live trainer uses 0.9; STEP5_DESIGN_NOTES records 0.8; unified §3.2 self-flags."
STEP5_DESIGN_NOTES.md code block: alpha=0.8 (line 30, DispositionBridgeLoss.__init__).
No resolution run found; item open. RECON landing confirmed.

---

## PRIMARY CLAIMS — evidence classification

FIND_V1
id: EVD-01
type: EVD
claim: MED alpha=0.2 inverted-U; 6/6 recall, entropy +35%, recovery 1.000 at alpha=0.2
ev: RESEARCH_LOG.md:814-833 (2026-03-22 Step 5d entry); RESEARCH_LOG.md:943-960 (2026-03-22 duplicate clean entry); EXPERIMENT_LADDER.md:63-67 (Step 5d status block); MoCoP/experiments/mamba_lora_bridge/step5d_chat_client.py (script exists); MoCoP/experiments/mamba_lora_bridge/step5d_bridge_recorder.py (script exists); MoCoP/experiments/mamba_lora_bridge/run_step5d_steve_sweep.ps1 (orchestrator exists)
ev_class: log_result (primary run log in RESEARCH_LOG); primary artifact directory tmp/step5d_20260322/ NOT FOUND on disk (not committed; gitignored tmp/)
canon: logged
conf: high
act: Accept log_result evidence. Note primary run dir is uncommitted/gitignored — reproducibility depends on scripts + checkpoint.
risk: low

---

FIND_V1
id: EVD-02
type: EVD
claim: L13 warm/cold cosine 0.092 (Cassian, 2026-03-18; Qwen2.5-7B layers 12-15)
ev: MoCoP/experiments/mamba_lora_bridge/activation_sessions/DISPOSITION_EVIDENCE_2026-03-18.md:26 (table row: Layer 13, 0.092); MoCoP/experiments/mamba_lora_bridge/activation_sessions/mamba_state_separation.json:28 (qwen_layer13_reference.warm_vs_cold: 0.092); RESEARCH_LOG.md:261-276 (2026-03-18 entry, table confirms 0.092); scripted session .pt files exist: scripted_warm_opus_20260318_213202.pt, scripted_cold_clinical_20260318_213401.pt, scripted_adversarial_20260318_213439.pt
ev_class: primary_run (DISPOSITION_EVIDENCE doc + .pt session files + JSON reference)
canon: logged
conf: high
act: No action needed. Primary artifacts confirmed on disk.
risk: none

---

FIND_V1
id: EVD-03
type: EVD
claim: 17x PPL input-dependent (Mamba-derived -4.04 vs constant -0.23; ratio ~17.5x)
ev: MoCoP/experiments/mamba_lora_bridge/STEP4_VERDICT_2026-03-18.md:8,26,30 (verdict doc, table, ratio); RESEARCH_LOG.md:233-252 (2026-03-18 Step 4 entry, table + "~17.5x" ratio); unified_cognitive_framework.md:165 ("17x PPL improvement over constant bias; STEP4_VERDICT_2026-03-18.md"); RESEARCH_LOG.md:246 (Ratio: ~17.5x)
ev_class: log_result (verdict doc + LOG entry). Primary run dirs run_constant_bias/, run_constant_bias_10ep/, run_constant_bias_seed42/, run_actbias/ NOT FOUND on disk.
canon: logged
conf: high
act: Accept log_result. Run dirs are referenced but not committed. STEP4_VERDICT_2026-03-18.md is the committed verdict doc and suffices.
risk: low

---

FIND_V1
id: EVD-04
type: EVD
claim: hidden-last-tok vs ssm-state: avg cosines 0.018 vs 0.8
ev: MoCoP/experiments/mamba_lora_bridge/activation_sessions/ssm_vs_hidden_separation.json (full data: hidden_last warm/cold=0.036, warm/adv=0.025, cold/adv=-0.007 → avg ~0.018; ssm_state_flat warm/cold=0.778, warm/adv=0.785, cold/adv=0.848 → avg 0.804 ≈ "0.8"); RESEARCH_LOG.md:348-363 (2026-03-25 entry, table); RESEARCH_LOG.md:1217-1231 (2026-03-26 upstream ablation, Opa confirmation, avg cosine 0.018 hidden vs 0.804 ssm); RESEARCH_BACKLOG.md item #1 (closed, cites same numbers)
ev_class: primary_run (JSON artifact on disk, two independent runs: Steve 2026-03-25 + Opa 2026-03-26)
canon: logged
conf: high
act: No action needed. Strongest evidence base of all targets.
risk: none

---

FIND_V1
id: EVD-05
type: EVD
claim: reincarnation qual-PASS n=3 (overfit; 3 shaping episodes)
ev: MoCoP/experiments/mamba_lora_bridge/run_reincarnation/C.H.E.E.S.E_Reincarnation_Debrief_20260325.md (debrief doc: "three high-salience conversational snippets"; loss 12.3→0.012; qualitative output shift confirmed); opa_reincarnation_t07_140tok_20260325.txt + opa_reincarnation_t03_140tok_20260325.txt (inference run logs exist on disk); RESEARCH_LOG.md entry "Gemini Adrenaline Bridge" (2026-03-20: "Training loss: 27.2→0.021 in 100 epochs on 3 CHEESE shaping episodes"); unified_cognitive_framework.md:651 ("Medium (overfit, n=3)")
ev_class: primary_run (debrief + inference output files on disk)
NOTE: "n=3" means 3 shaping episodes (not 3 independent replications). Overfit is acknowledged in the claim itself. This is qualitative, not statistically replicated.
canon: logged
conf: high
act: No action. Evidence class and caveat (overfit) already explicit in canon. Do not upgrade to quantitative claim.
risk: low

---

FIND_V1
id: EVD-06
type: EVD
claim: sleep-infra-gate 5f PASS (2 sleep cycles, 2K/0U/0W/0D + 1K/0U/0W/0D, diversity 100%, recovery 1.0)
ev: MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_sleep_cycle_default_20260326.md (cycle 1: 2K/0U/0W/0D, PASS, diversity 100%, recovery 1.0); MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_sleep_cycle_report_20260326T113050.json (machine-readable: verdict PASS, diversity_ratio 1.0, recovery_score 1.0); MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_open_tension_sleep_cycle_20260326.md (cycle 2: 1K/0U/0W/0D, PASS, diversity 100%, recovery 1.0); RESEARCH_LOG.md:1147-1158 (2026-03-26 Step 5f entry confirms both cycles); EXPERIMENT_LADDER.md:71-74 (Step 5f status block)
ev_class: primary_run (run docs + machine-readable JSON on disk)
HONEST CAVEAT: decay calibration did not distinguish 0.70/0.85/0.90; 0.85 is provisional per step_gates.md (stated in run_constant_bias / in the cycle report: "Decay factor 0.85 is provisional").
canon: logged
conf: high
act: No action. All artifacts present. Provisional decay caveat already in canon.
risk: none

---

## SA-10 INDEPENDENT HUNT (primary task per RECON spec)

FIND_V1
id: EVD-07
type: RECON_DOUBT
claim: Recon downgraded SA-10 drift 0.91/0.83/0.85 to "unverified" — independent hunt finds NO primary artifact anywhere in repo
ev: none (exhaustive search: all .json, .jsonl, .md in MoCoP/; no file contains these three values together except unified_cognitive_framework.md:481 and sleep_architecture.md:165-167, both theory docs not run outputs)
canon: missing (primary_run)
conf: high
act: RECON_DOUBT confirmed: downgrade was correct. No contrary evidence found (did not find a hidden run). Raise: sleep_architecture.md:165-167 still presents values without caveat — partial recon (recon only patched unified_cognitive_framework.md). Needs Laura decision: either add matching caveat to sleep_architecture.md or accept that THY-04 (from THY lane) covers this.
risk: med

---

FIND_V1
id: EVD-08
type: GAP
claim: step5d primary run directory (tmp/step5d_20260322/) is not committed or present on disk
ev: RESEARCH_LOG.md:832,960 (both cite "tmp/step5d_20260322/" as artifact); Glob on MoCoP/experiments/mamba_lora_bridge/tmp/ returns no results; run_step5d_steve_sweep.ps1 creates output in tmp/step5d_<timestamp>/ (gitignored)
canon: logged (LOG entry present; artifact missing)
conf: high
act: Log result is the surviving evidence. Flag for Laura: step5d raw run data is not preserved in the repo. Scripts + checkpoint (cheese_reincarnation_bridge_1.5b_codexfix.pt, present) allow re-run but original output is gone.
risk: med

---

FIND_V1
id: EVD-09
type: GAP
claim: Step 4 run directories (run_constant_bias/, run_actbias/, run_constant_bias_10ep/, run_constant_bias_seed42/) referenced in RESEARCH_LOG are absent from repo
ev: RESEARCH_LOG.md:252 (artifacts: run_constant_bias/, run_constant_bias_10ep/, run_constant_bias_seed42/); RESEARCH_LOG.md:177 (artifacts: run_actbias/); Glob on those paths returns no results
canon: logged (LOG + STEP4_VERDICT; raw artifacts missing)
conf: high
act: STEP4_VERDICT_2026-03-18.md and LOG entry suffice as log_result evidence. Raw checkpoint dirs not committed (likely gitignored large binaries). Acceptable for this result tier but worth noting for provenance.
risk: low

---

FIND_V1
id: EVD-10
type: CONFLICT
claim: 17x vs 17.5x ratio inconsistency between STEP4_VERDICT doc and RESEARCH_LOG/RESEARCH_ABSTRACT
ev: STEP4_VERDICT_2026-03-18.md:8 ("17x PPL improvement gap"); STEP4_VERDICT_2026-03-18.md:30 ("17x the constant bias ceiling"); RESEARCH_LOG.md:246 ("~17.5x gap"); RESEARCH_ABSTRACT.md:29 ("17.5x"); unified_cognitive_framework.md:165 ("17x"); RESEARCH_PAPER.md:203 ("17.5x")
ev_class: log_result (both figures calculated from same run data: 4.04/0.23 = 17.56x; STEP4_VERDICT rounds to 17x, LOG/ABSTRACT/PAPER use 17.5x)
canon: conflict (minor)
conf: high
act: Both values are from the same data (4.04/0.23 = 17.56x). Rounding difference only. Low priority but a source of reader confusion. Recommend standardising on "~17.5x" (more accurate) across all docs at next edit pass.
risk: low

---

FIND_V1
id: EVD-11
type: RECON_DOUBT
claim: Recon added SA-10 unverified caveat to unified_cognitive_framework.md:481 but sleep_architecture.md:165-167 still presents same values (0.91/0.85/0.83 drift) as factual without any caveat
ev: unified_cognitive_framework.md:481 (caveat present); sleep_architecture.md:165-167 (no caveat; values presented in a data table as measured results)
canon: conflict
conf: high
act: RECON_DOUBT — recon was incomplete. Either (a) add matching caveat to sleep_architecture.md:165-167, or (b) remove the table row entirely. Needs Laura decision; route to 08_SYNTH "Needs Laura decision."
risk: med
