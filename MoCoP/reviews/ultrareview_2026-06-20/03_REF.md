LANE REF
scope_checked:
MoCoP/README.md
MoCoP/CODESIGHT_RUNBOOK.md
MoCoP/.codesight/wiki/index.md
MoCoP/.codesight/wiki/overview.md
MoCoP/.codesight/KNOWLEDGE.md
MoCoP/theory/README.md
MoCoP/theory/ethics/README.md
MoCoP/theory/ethics/step_gates.md
MoCoP/EXPERIMENT_LADDER.md
MoCoP/RESEARCH_BACKLOG.md
MoCoP/PRISTINE_BIRTH_BACKLOG.md
MoCoP/RESEARCH_LOG.md (head + tail)
MoCoP/phases/phase1_results.md (ref check)
MoCoP/theory/Three_System_Cognitive_Architecture.md (ref check)
MoCoP/experiments/mamba_lora_bridge/spikes/ (listing)
MoCoP/reviews/ultrareview_2026-06-20/00_WC_REFERENCE.md

files_read:
README.md, CODESIGHT_RUNBOOK.md, EXPERIMENT_LADDER.md, RESEARCH_BACKLOG.md,
PRISTINE_BIRTH_BACKLOG.md, theory/README.md, theory/ethics/README.md,
theory/ethics/step_gates.md, .codesight/wiki/index.md, .codesight/wiki/overview.md,
.codesight/KNOWLEDGE.md, 00_WC_REFERENCE.md (from reviews/ultrareview_2026-06-20/)
Glob/Grep checks on all file-existence claims below.

---

FIND_V1
id: REF-01
type: STALE
claim: README.md Current Frontier dated 2026-06-08 still lists Qwen2.5-7B as Step 6 target; Gemma pivot (#642) and PRISTINE_BIRTH_BACKLOG unmentioned
ev: MoCoP/README.md:55 ("Current Frontier (2026-06-08)"); MoCoP/README.md:81 ("Step 6 target: Qwen2.5-7B on A100"); MoCoP/EXPERIMENT_LADDER.md:27 (Amendment 2026-06-14 Gemma-4-12B); MoCoP/PRISTINE_BIRTH_BACKLOG.md exists (2026-06-20)
canon: stale
conf: high
act: Update README Current Frontier block to 2026-06-20 + reference Gemma pivot and PRISTINE_BIRTH_BACKLOG.md
risk: med

---

FIND_V1
id: REF-02
type: BROKEN_REF
claim: CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/ directory and files do not exist; referenced from theory/README.md, theory/Three_System_Cognitive_Architecture.md, phases/phase1_results.md, RESEARCH_LOG.md entry 1
ev: MoCoP/theory/README.md:151 ("Debriefs: CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/"); MoCoP/theory/Three_System_Cognitive_Architecture.md:197 (link to CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/Phase1_Mamba_Memory_Probe.md); MoCoP/phases/phase1_results.md:94; Glob CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/** = no files found
canon: missing
conf: high
act: Either create the dir with the Phase1/Phase2 debrief stubs or update refs to actual artifact locations; no canon read depends on them for gating, but dead links mislead orientation agents
risk: low

---

FIND_V1
id: REF-03
type: BROKEN_REF
claim: EXPERIMENT_LADDER.md Step 2 references CODEX_TASK_COMPRESSOR_BYPASS.md as a Codex task "already written" but file does not exist in repo
ev: MoCoP/EXPERIMENT_LADDER.md:166 ("How: Codex task already written (CODEX_TASK_COMPRESSOR_BYPASS.md)"); Glob MoCoP/experiments/mamba_lora_bridge/CODEX_TASK_COMPRESSOR_BYPASS.md = no files found
canon: missing
conf: high
act: Either create a minimal stub or remove the forward-ref; Step 2 is CLOSED so no functional block, but the dead file ref misleads agents looking for the Codex task
risk: low

---

FIND_V1
id: REF-04
type: STALE
claim: theory/README.md says "For current deployment, read STEVE_RUNBOOK.md" without a path; file lives at MoCoP/experiments/mamba_lora_bridge/STEVE_RUNBOOK.md — ambiguous for orientation agents
ev: MoCoP/theory/README.md:41 ("read `STEVE_RUNBOOK.md`" bare filename); STEVE_RUNBOOK.md exists at MoCoP/experiments/mamba_lora_bridge/STEVE_RUNBOOK.md
canon: stale
conf: med
act: Change bare reference to relative path `../experiments/mamba_lora_bridge/STEVE_RUNBOOK.md`
risk: low

---

FIND_V1
id: REF-05
type: STALE
claim: README.md canon table lists MASTER_PLAN.md but README Current Frontier omits all post-June-14 developments; MASTER_PLAN.md may also be stale re Gemma pivot (not checked in detail but same epoch as README)
ev: MoCoP/README.md:30 (MASTER_PLAN.md listed as "Architecture, phases, vision, open questions"); MASTER_PLAN.md exists (file confirmed); no Gemma/PRISTINE_BIRTH mentions found in README (Grep confirmed)
canon: stale
conf: med
act: Check MASTER_PLAN.md for Qwen references that should become Gemma-4-12B; update if stale
risk: med

---

FIND_V1
id: REF-06
type: STALE
claim: codesight KNOWLEDGE.md date range 2026-03-16 to 2026-05-28 (262 notes); does not include PRISTINE_BIRTH_BACKLOG.md (2026-06-20), baseline_drift_gate_calibration.md edits (431b95f), or step_gates.md amendments — all post 2026-05-28
ev: MoCoP/.codesight/KNOWLEDGE.md:2 ("262 notes … 2026-03-16 → 2026-05-28"); PRISTINE_BIRTH_BACKLOG.md absent from KNOWLEDGE.md (Grep confirmed); 00_WC_REFERENCE.md §2 confirms RESEARCH_LOG.md, EXPERIMENT_LADDER.md, RESEARCH_BACKLOG.md, step_gates.md are outside codesight ingestion scope entirely
canon: stale
conf: high
act: Re-run `npx codesight --wiki` per CODESIGHT_RUNBOOK.md refresh script; KNOWLEDGE.md range will extend to 2026-06-20 and pick up PRISTINE_BIRTH_BACKLOG + new activation_sessions files
risk: low

---

FIND_V1
id: REF-07
type: STALE
claim: codesight wiki/index.md generated stamp is 2026-06-17; the 946f0b0 codesight refresh (2026-06-20 14:05) updated CODESIGHT.md/libs.md/middleware but did NOT update the wiki/index.md Generated line
ev: MoCoP/.codesight/wiki/index.md:3 ("Generated 2026-06-17"); git show --stat 946f0b0 confirms wiki/index.md was changed but it still says 2026-06-17 in the file (Grep confirms "Generated 2026-06-17" is still present post-946f0b0); wiki/index.md:45 ("Last compiled: 2026-06-17")
canon: stale
conf: high
act: Re-run codesight wiki generation; the index.md date line should auto-update to 2026-06-20
risk: low

---

FIND_V1
id: REF-08
type: GAP
claim: RESEARCH_BACKLOG.md numbering has gap at item 19 (alpha reconciliation) vs surrounding items 16/17/18/20-23; no item 19 in P1 section near its peers — item 19 appears at line 290 but is separated from P1 block by items 16/17/18 in different order
ev: MoCoP/RESEARCH_BACKLOG.md:290 (item 19 at line 290 between items 18 and P2); items 14/15 appear in P3 section (line 728+); numbering is non-sequential in section order
canon: n/a
conf: med
act: Note for cleanup — numbering inconsistency may confuse agents looking for "item 19" in P1; not a broken link but a nav hazard; human decision on resequencing
risk: low

---

FIND_V1
id: REF-09
type: ORPH
claim: MoCoP/experiments/mamba_lora_bridge/spikes/TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md exists and is referenced in EXPERIMENT_LADDER.md Current Frontier block, but is not listed in any index doc (theory/README.md, codesight KNOWLEDGE.md, README.md)
ev: MoCoP/EXPERIMENT_LADDER.md:49 (explicit path reference); MoCoP/experiments/mamba_lora_bridge/spikes/TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md exists (Glob confirmed); not found in theory/README.md, codesight KNOWLEDGE.md, or README.md (Grep confirms no entry)
canon: missing
conf: high
act: Spike spec is parked (no sleep_reconcile.py change until PASS); add a brief mention to codesight KNOWLEDGE.md or a spikes README so it is findable; low priority
risk: low

---

FIND_V1
id: REF-10
type: STALE
claim: theory/ethics/README.md step_gates.md description says "Five gate questions per experiment. Per-step assessments for Steps 5, 5b, 6" — step_gates.md now also covers Steps 5c, 5e, 7, 8, 9, 10, Sleep Slices 1-5, Task #115, and multiple addenda
ev: MoCoP/theory/ethics/README.md:27 (step_gates.md row: "Five gate questions per experiment. Per-step assessments for Steps 5, 5b, 6"); MoCoP/theory/ethics/step_gates.md (full read: contains 5, 5b, 5c, 5e, 6, 7, 8, 9, 10, Sleep Slices, Task #115, architecture addenda)
canon: stale
conf: high
act: Update ethics/README.md step_gates.md row description to reflect current coverage; low editorial effort
risk: low

---

FIND_V1
id: REF-11
type: ORPH
claim: MoCoP/experiments/mamba_lora_bridge/results/jrt_spike/ directory (with jrt_ordering_state_readout.md/json) is not referenced in any index doc or RESEARCH_LOG entry visible in the scan; JRT results are referenced in RESEARCH_LOG Entry 65 but that entry does not cite the results/ path
ev: MoCoP/experiments/mamba_lora_bridge/results/jrt_spike/ (Glob confirmed: 2 files); RESEARCH_LOG.md (scan of entries 65-67 region not read fully — GAP: cannot confirm absence from LOG without full LOG read); 00_WC_REFERENCE.md §2 notes Entry 65 IS in RESEARCH_LOG (commit 9c9e989) but the exocortex hit is the spike spec doc, not the results/jrt_spike readout
ev: MoCoP/experiments/mamba_lora_bridge/results/jrt_spike/jrt_ordering_state_readout.md (exists); 00_WC_REFERENCE.md:43 (Entry 65 partial — "NOT in exocortex")
canon: missing
conf: med
act: Verify Entry 65 in RESEARCH_LOG.md cites results/jrt_spike/ path; if not, add artifact citation; EVD lane item
risk: low

---

FIND_V1
id: REF-12
type: STALE
claim: README.md Quick Reference table entry "What are the ethics rules?" points to theory/ethics/step_gates.md — link is correct, but the entry "How do I close a session?" points to CONTRIBUTING.md Rule 7 which may not match post-reconciliation CONTRIBUTING.md (not checked)
ev: MoCoP/README.md:100 ("How do I close a session? → CONTRIBUTING.md Rule 7"); CONTRIBUTING.md exists (Glob confirmed); content not read — flagging as low-risk staleness check
canon: stale
conf: low
act: Verify CONTRIBUTING.md Rule 7 is still the correct session-close rule; if CONTRIBUTING.md was updated post-reconciliation, cross-check
risk: low

---

FIND_V1
id: REF-13
type: GAP
claim: PRISTINE_BIRTH_BACKLOG.md is a new root-level MoCoP doc (2026-06-20) not listed in README.md canon table, theory/README.md, or codesight KNOWLEDGE.md
ev: MoCoP/PRISTINE_BIRTH_BACKLOG.md exists (Glob confirmed, 2026-06-20 date); MoCoP/README.md canon table (read fully): no PRISTINE_BIRTH_BACKLOG row; MoCoP/.codesight/KNOWLEDGE.md: absent (Grep confirmed); theory/README.md: absent
canon: missing
conf: high
act: Add PRISTINE_BIRTH_BACKLOG.md row to README.md canon table ("who maintains: Cairn / Laura, purpose: arch prerequisites for Gemma-substrate first seeding"); low risk edit
risk: low

---

FIND_V1
id: REF-14
type: ORPH
claim: MoCoP/experiments/mamba_lora_bridge/spikes/DAM_PHASE0_SPEC.md, ROLE_INVERSION_SPIKE_SPEC.md, JRT_ORDERING_SPIKE_SPEC.md, MAMBA_STYLE_DISPOSITION_CONTROL_SPEC.md exist in spikes/ but none are referenced by theory/README.md or codesight KNOWLEDGE.md index; only TEMPORAL_CASCADE and lesson_memory_v0_plan.md appear in any doc cross-ref scan
ev: Glob MoCoP/experiments/mamba_lora_bridge/spikes/*.md returns 5 spec files; Grep for DAM_PHASE0_SPEC/ROLE_INVERSION_SPIKE_SPEC/JRT_ORDERING_SPIKE_SPEC/MAMBA_STYLE_DISPOSITION_CONTROL_SPEC in theory/README.md returns nothing; codesight KNOWLEDGE.md scan returned none (those docs fall outside 2026-05-28 cutoff or are excluded)
canon: missing
conf: med
act: Add a spikes/README.md listing active spike specs with status (PASS/KILL/PARKED); low priority but useful orientation surface; human decision on which spikes are closed
risk: low

---

FIND_V1
id: REF-15
type: CONFLICT
claim: codesight wiki/index.md says "Generated 2026-06-17" but 946f0b0 commit (2026-06-20 14:05) is documented as "refresh codesight index" — two conflicting freshness signals for the same file
ev: MoCoP/.codesight/wiki/index.md:3 ("Generated 2026-06-17"); git log --oneline -- MoCoP/.codesight/ shows 946f0b0 "chore: refresh codesight index" at 2026-06-20; git show --stat 946f0b0 lists wiki/index.md as changed (+6/-6 lines) but the Generated line was not updated to 2026-06-20
canon: conflict
conf: high
act: Re-run codesight generation so wiki/index.md Generated date matches 946f0b0 commit date; commit message is correct, file content is stale
risk: low
