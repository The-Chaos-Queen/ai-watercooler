# 01_EXP — Experiment Findings (FIND_V1)
## ultrareview 2026-06-20

Caveman format. Each record = one problem cluster. IDs sequential.

---

### EXP-01 — RESULT NOT IN LOG: mvp0_raw_state SJT result files live on Steve only

**Type:** result-not-logged (partial)
**Paths:**
- `C:\Users\tikii\bridge\mvp0_raw_state_sjt_alpha005.json` (Steve)
- `C:\Users\tikii\bridge\mvp0_raw_state_sjt_alpha010.json` (Steve)
- `C:\Users\tikii\bridge\mvp0_raw_state_sjt_alpha020.json` (Steve)

**Claim in LOG (Entry 30, 2026-04-08):** MVP-0 raw-state translator was behaviorally inert across alpha 0.05/0.1/0.2, all 12-item ties. LOG says artifacts are on Steve only. No copy in repo.

**Problem:** Three result JSONs are not in the repo at all. They appear nowhere under `MoCoP/experiments/`. LOG entry is complete (negative result, logged), but the artifacts are unrecoverable if Steve is wiped.

**Action:** Fetch from Steve and commit to `run_reincarnation/` or mark explicitly as Steve-local and permanent in LOG.

---

### EXP-02 — RESULT NOT IN LOG: DAM phase 0 sweep JSON on ML-WS only

**Type:** result-not-logged (partial)
**Paths:**
- `/tmp/dam_phase0_sweep.json` on ML-WS (Entry 55)
- `/tmp/dam_qdrant_scaling.json` on ML-WS (Entry 56)
- `/tmp/dam_diverse_eval.json` on ML-WS (Entry 57)

**Problem:** Three result files are explicitly described as `/tmp/` on ML-WS. `/tmp` is volatile. LOG entries (55-57) exist and are well-documented, but the raw data is ephemeral and not committed to repo.

**Action:** Either accept as intentional (ML-WS scratch space, LOG is the record) or fetch and commit to `results/dam_phase0/`.

---

### EXP-03 — RESULT NOT IN LOG: role inversion spike result dirs on ML-WS only

**Type:** result-not-logged (partial)
**Paths:**
- ML-WS: `results/role_inversion_spike_20260609/` (v1)
- ML-WS: `results/role_inversion_spike_20260609_v2/` (v2)

**Problem:** Entry 58 (2026-06-09) references these paths on ML-WS but they are not in the repo. The spec file `spikes/ROLE_INVERSION_SPIKE_SPEC.md` is in the repo; the result JSONs are not. First-token KL numbers and all per-condition counts are quoted in the LOG but raw data is not committed.

**Action:** Commit result dirs to `results/role_inversion_spike/` or mark as ML-WS-local.

---

### EXP-04 — ORPHAN OUTPUT: `chat_session_latest.txt`, `chat_turns_latest.jsonl`, `dual_gate_turns_latest.jsonl`

**Type:** orphan output (ephemeral runtime state committed to repo)
**Paths:**
- `MoCoP/experiments/mamba_lora_bridge/chat_session_latest.txt`
- `MoCoP/experiments/mamba_lora_bridge/chat_turns_latest.jsonl`
- `MoCoP/experiments/mamba_lora_bridge/dual_gate_turns_latest.jsonl`

**Problem:** These are `_latest` runtime outputs — whatever session last ran on the local machine. They are not associated with any specific experiment entry in the LOG. They are not named by date/session and will be silently overwritten on the next run. Committing them is misleading (suggests they are a preserved result when they are not).

**Action:** Add to `.gitignore` or rename with session timestamp before committing.

---

### EXP-05 — ORPHAN OUTPUT: `mamba_bootstrap_state_latest.pt` inside results archive

**Type:** orphan output (runtime bootstrap state in cold archive dir)
**Path:** `MoCoP/experiments/mamba_lora_bridge/results/baby_alex_116_pre_sleep_archive/baby_alex_116_pre_sleep_archive_20260603T204746Z/mamba_bootstrap_state_latest.pt`

**Problem:** A `_latest` bootstrap state file was captured inside the pre-sleep archive bundle. This file is a moment-in-time Mamba hidden state from the archive run (2026-06-03). It is not referenced in the LOG as a named artifact. It may be intentional (snapshot for the archive bundle) but it is ambiguous — `_latest` naming inside a dated archive suggests it was captured by a runtime sweep rather than explicitly named.

**Action:** Rename to `mamba_bootstrap_state_20260603T204746Z.pt` inside the archive dir, or add a note in the archive manifest that this is the bootstrap state at archive time.

---

### EXP-06 — HALF-FINISHED WORK: `AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN.md` — implementation status unclear

**Type:** half-finished (spec with unknown completion)
**Path:** `MoCoP/experiments/mamba_lora_bridge/AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN.md`

**Problem:** This spec exists but has no PLAN date in the filename (unlike `ARCHIVIST_MAMBA_IMPLEMENTATION_PLAN_2026-05-21.md`). `autobiographical_memory.py` exists and is tested (Entry 52 references `test_autobiographical_memory.py`, 17 passed). However, the LOG does not contain an explicit "AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN completed / superseded" entry. The plan may be fully implemented, partially implemented, or superseded by the astrocyte memory controller (Entry 54).

**Action:** Human check — is this plan complete? If yes, add a note or archive it. If superseded, prepend `ARCHIVED_` to filename.

---

### EXP-07 — HALF-FINISHED WORK: `TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md` filed but no run entry

**Type:** half-finished (spec with no result)
**Path:** `MoCoP/experiments/mamba_lora_bridge/spikes/TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md`

**Problem:** Spec is in the repo (recent — git commit message `docs(mocop): file temporal-cascade sleep-residue spike spec` is in the recent commits log). No RESEARCH_LOG entry exists for this spike being run. No result JSON for it appears in `results/` or anywhere in the classification. This is a queued unrun experiment.

**Action:** No immediate action needed, but flag so it does not get confused with completed spikes. Add `[UNRUN]` to the spec's title or first line.

---

### EXP-08 — DIR MISSING README: `results/` top-level and most subdirs have no README

**Type:** dir-missing-README
**Paths:**
- `MoCoP/experiments/mamba_lora_bridge/results/` — no README
- `MoCoP/experiments/mamba_lora_bridge/results/jrt_spike/` — no README
- `MoCoP/experiments/mamba_lora_bridge/results/baby_alex_116_pre_sleep_archive/` — no README (has manifest.json/manifest.md inside the timestamped subdir, good)
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws/` — no README
- `MoCoP/experiments/mamba_lora_bridge/results/monk_variable_probe_20260606/` — no README
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/` — no README

**Problem:** `results/` has grown to 12+ subdirectories with no top-level index. `run_reincarnation/` has 20+ subdirs and flat JSON files with no manifest. New readers (and future wolves) cannot orient without opening individual files.

**Action:** Add a `INDEX.md` or `README.md` to `results/` and `run_reincarnation/` summarizing what each subdir is. Alternatively, accept as "read the LOG" and add a note there.

---

### EXP-09 — DIR MISSING README: `spikes/` subdirectory has no README

**Type:** dir-missing-README
**Path:** `MoCoP/experiments/mamba_lora_bridge/spikes/`

**Problem:** `spikes/` contains 5 spec files (DAM_PHASE0, JRT_ORDERING, MAMBA_STYLE_DISPOSITION_CONTROL, ROLE_INVERSION, TEMPORAL_CASCADE), 4 probe scripts, and a `fixtures/` subdir. No README or INDEX. The directory grew organically; its relationship to the main ladder is implicit.

**Action:** Add a one-page README listing what's been run vs. queued unrun.

---

### EXP-10 — CLAIM VS ARTIFACT MISMATCH: Entry 35 hidden-gated bridge checkpoint not confirmed in repo

**Type:** claim-vs-artifact mismatch
**Claim in LOG (Entry 35, 2026-04-13):** `mvp2_hidden_gated_1p5b.pt` used for internal diagnostic showing better separation than codexfix.
**Expected path:** `MoCoP/experiments/mamba_lora_bridge/mvp2_hidden_gated_1p5b.pt` or similar
**Status:** Not in classification table. The checkpoint may be on Steve only (same pattern as mvp0_raw_state).

**Problem:** Entry 35 declares a significant architectural improvement (context cosine 0.948 vs 0.9997 for codexfix). The checkpoint enabling this result is not confirmed in the repo. If Steve is wiped, the finding cannot be reproduced.

**Action:** Confirm location of `mvp2_hidden_gated_1p5b.pt`. If Steve-only, document explicitly. If lost, flag as non-reproducible in the LOG.

---

### EXP-11 — CLAIM VS ARTIFACT MISMATCH: Entry 23 `kimi_roleplay_bridge_1.5b_2026-04-03.pt` (80-epoch, discarded) vs `_e65.pt` (kept)

**Type:** claim-vs-artifact mismatch (minor)
**Paths:**
- `MoCoP/experiments/mamba_lora_bridge/kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt` — IN REPO
- `kimi_roleplay_bridge_1.5b_2026-04-03.pt` (80-epoch, overshot) — status unknown

**Problem:** Entry 23 mentions the 80-epoch checkpoint was produced first and then discarded in favor of the 65-epoch clean version. The `_e65.pt` is in the repo. The 80-epoch version's fate is unspecified — it may have been overwritten or may exist on Steve. Not a blocking issue but a minor ambiguity if someone wonders whether there is a 80-epoch version to compare against.

**Action:** Add a note in LOG Entry 23 that the 80-epoch checkpoint was discarded (not archived).

---

### EXP-12 — ORPHAN OUTPUT: `results/baby_alex_116_pre_sleep_archive` contains duplicated protocol/plan files

**Type:** orphan outputs (files duplicated into archive bundle)
**Paths inside `results/baby_alex_116_pre_sleep_archive/.../`:**
- `BABY_ALEX_116_DRY_RUN_PROTOCOL_2026-05-28.md` — duplicate of root-level spec
- `BABY_ALEX_116_WAKE_PROBE_PLAN.md` — duplicate of root-level spec
- `build_baby_alex_116_preflight.py` — duplicate of root-level module
- `build_baby_alex_protected_set_audit.py` — duplicate of root-level module
- `run_baby_alex_wake_probe.py` — present here; not in classification table at root level

**Problem:** The archive bundle contains copies of live spec/code files. If the specs are updated, the archive bundle goes stale without warning. The bundle probably captured these as a snapshot of the code state at archive time, which is intentional, but it creates confusion about which is the "real" version.

**Action:** Confirm the bundle was intentionally created as a snapshot (acceptable). Add a note in `manifest.md` that the code files are frozen snapshots at archive time, not live sources.

---

### EXP-13 — RESULT NOT IN LOG: `live_gate_threshold_sweep_2026-04-03.json` has no LOG entry

**Type:** result-not-logged
**Paths:**
- `MoCoP/experiments/mamba_lora_bridge/live_gate_threshold_sweep_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/live_gate_threshold_sweep_2026-04-03_summary.md`

**Problem:** These files exist in the repo but no LOG entry explicitly covers a "live gate threshold sweep" on 2026-04-03. Entry 21 (live gate alpha 0.2 probe) and Entry 22 (alpha 0.3 probe) are the closest LOG entries from that date but neither references this filename directly. The summary.md may contain the narrative; the JSON is an unlogged result.

**Action:** Verify whether Entry 21/22 cover this data. If yes, add a cross-reference artifact line. If this was a separate unlisted sweep, add a brief LOG entry.

---

### EXP-14 — RESULT NOT IN LOG: `results/board_91_92_mlws/` and `results/board_91_92_mlws_static_readonly/` — no LOG entry

**Type:** result-not-logged
**Paths:**
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws/`
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws_static_readonly/`

**Problem:** Two result directories named after OpenCLAW board items 91-92 on ML-WS have no corresponding LOG entry. Board items 91/92 are not mentioned in the LOG entries scanned (Entries 1-67). May be a watercooler/board artifact fetch, not an experiment result, but the directory sits inside `results/` which is convention for experiment outputs.

**Action:** Human check — what are board items 91-92? Add a LOG stub or move to a non-results location if these are board scrapes rather than experiment artifacts.

---

### EXP-15 — RESULT NOT IN LOG: `results/monk_variable_probe_20260606/` — no LOG entry

**Type:** result-not-logged
**Path:** `MoCoP/experiments/mamba_lora_bridge/results/monk_variable_probe_20260606/`

**Problem:** Directory dated 2026-06-06 (same day as Entry 54 astrocyte memory controller). No LOG entry mentions a "monk variable probe." Entry 54 (Workstream B DAM Phase 0) and Entry 55-57 are on 2026-06-08/09. The 06-06 probe predates these and is unlogged.

**Action:** Add a LOG stub for 2026-06-06 or clarify if this was a casual probe that fed into Entry 54's development and can be cross-referenced there.

---

## Coverage Line

**Files classified vs total:** 1633 / 1633 (100% from Batch 1 full table). Batches 2-16 returned empty — all files were in Batch 1. No files skipped.

**LOG entries reviewed:** 1-67 (complete as of 2026-06-17 Entry 67). RESEARCH_LOG ends at Entry 67; no log entries after that date exist.

**Scope note:** This review covers `MoCoP/experiments/` only. Files on Steve (`C:\Users\tikii\bridge\`) and ML-WS (`/tmp/`, `/home/isabell/`) are tracked only where referenced in LOG artifacts sections. Those remote-only result files are flagged (EXP-01, EXP-02, EXP-03) but not inventoried here.
