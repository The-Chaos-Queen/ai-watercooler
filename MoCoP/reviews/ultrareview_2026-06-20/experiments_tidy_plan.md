# experiments/ tidy plan — ultrareview 2026-06-20

Branch: `docs/theory-reconciliation`
Scope: `MoCoP/experiments/` — 1633 files total (100% classified)
Status: READ-ONLY PLAN. Nothing has been moved, deleted, or edited.

---

## 1. TRASH (safe, regenerable)

These are build artifacts. Every file is recreated automatically by the Python runtime or pytest. No experiment data lives here.

### Glob patterns

| Pattern | Verified count | Notes |
|---------|---------------|-------|
| `MoCoP/experiments/**/__pycache__/**` | **152 .pyc files** across 8 `__pycache__` dirs | cpython-310, 311, 313, 314, plus pytest variants |
| `MoCoP/experiments/**/*.pyc` | same 152 (overlaps above) | redundant safety net for any orphan .pyc outside a __pycache__ dir |
| `MoCoP/experiments/**/.pytest_cache/**` | **5 files** in one dir: `README.md`, `.gitignore`, `CACHEDIR.TAG`, `v/cache/lastfailed`, `v/cache/nodeids` | only one .pytest_cache found under `mamba_lora_bridge/` |

**Total trash: ~157 files across 9 directories.**
All are regenerated on next `python` or `pytest` invocation. No manual review needed.

---

## 2. ARCHIVE (keep history, cold storage)

Proposed destination: `MoCoP/experiments/mamba_lora_bridge/archive/`
(The `archive/` subdirectory already exists and contains `RUNBOOK_2026-03-25.md` and `STEVE_PC_HANDOFF_2026-03-20.md`. Extend it.)

### 2a. Old .pt model weights (dated 2026-03 / early 2026-04)

These weights predate the active checkpoint. They are not referenced as current experiment prerequisites in any recent LOG entry.

| Exact path | Date | Rationale |
|-----------|------|-----------|
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/activation_session_20260318_202311.pt` | 2026-03-18 | March activation sweep, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/activation_session_20260318_203419.pt` | 2026-03-18 | March activation sweep, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/activation_session_20260318_203646.pt` | 2026-03-18 | March activation sweep, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/activation_session_20260318_204514.pt` | 2026-03-18 | March activation sweep, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/activation_session_20260318_210957.pt` | 2026-03-18 | March activation sweep, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/activation_session_20260318_211313.pt` | 2026-03-18 | March activation sweep, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/activation_session_20260318_211751.pt` | 2026-03-18 | March activation sweep, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/scripted_warm_opus_20260318_213202.pt` | 2026-03-18 | Scripted disposition runs, superseded by panel_b |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/scripted_cold_clinical_20260318_213401.pt` | 2026-03-18 | Scripted disposition runs, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions/scripted_adversarial_20260318_213439.pt` | 2026-03-18 | Scripted disposition runs, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions_1.5b/target_cheese_1_the_terminal_and_the_phoenix.pt` | 2026-03/04 | 1.5b input-gate sweep, superseded by codexfix |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions_1.5b/target_cheese_2_the_gps_and_the_solution_space.pt` | 2026-03/04 | same |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions_1.5b/target_cheese_3_the_rabbit_hole_of_subjectivity.pt` | 2026-03/04 | same |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions_1.5b_input_gate/target_cheese_1_the_terminal_and_the_phoenix.pt` | 2026-03/04 | 1.5b input-gate variant, superseded |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions_1.5b_input_gate/target_cheese_2_the_gps_and_the_solution_space.pt` | 2026-03/04 | same |
| `MoCoP/experiments/mamba_lora_bridge/activation_sessions_1.5b_input_gate/target_cheese_3_the_rabbit_hole_of_subjectivity.pt` | 2026-03/04 | same |
| `MoCoP/experiments/mamba_lora_bridge/cheese_reincarnation_bridge.pt` | 2026-03 | Original bridge v1, superseded by 1.5b and codexfix |
| `MoCoP/experiments/mamba_lora_bridge/cheese_reincarnation_bridge_1.5b.pt` | 2026-04 | Intermediate 1.5b, superseded by codexfix |
| `MoCoP/experiments/mamba_lora_bridge/cheese_reincarnation_bridge_7b.pt` | 2026-04 | 7b variant, not current production path |
| `MoCoP/experiments/mamba_lora_bridge/kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt` | 2026-04-03 | Kimi roleplay bridge, not active |
| `MoCoP/experiments/mamba_lora_bridge/dfc_results/dfc_crosscoder.pt` | 2026-04 | DFC crosscoder artifact, superseded |

**DO NOT ARCHIVE (active checkpoint):**
`MoCoP/experiments/mamba_lora_bridge/cheese_reincarnation_bridge_1.5b_codexfix.pt`

**Status-uncertain weights (keep in place until confirmed):**
- `mamba_layer3_states_v1.pt` — not dated in filename; no LOG reference found; keep until clarified
- `sae_mamba_layer3_v1.pt` — same
- `mvp8_prompt_trace_episode_contrastive_1p5b.pt` — not dated; keep until clarified
- `mamba_bootstrap_state_latest.pt` (root-level) — ephemeral runtime state; see Section 5

### 2b. Self-labeled ARCHIVE_* documents

| Exact path | Rationale |
|-----------|-----------|
| `MoCoP/experiments/mamba_lora_bridge/ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md` | Self-labeled archive; already cold |

### 2c. Superseded utilities

| Exact path | Rationale |
|-----------|-----------|
| `MoCoP/experiments/mamba_lora_bridge/archive_chat_session.sh` | Superseded by current chat archiving pipeline; no LOG reference as active tool |
| `MoCoP/experiments/mamba_lora_bridge/compare_archive_pipeline.py` | Diagnostic utility for old pipeline; superseded |
| `MoCoP/experiments/mamba_lora_bridge/build_baby_alex_116_archive_bundle.py` | One-shot bundle builder; the bundle is complete; script is spent |

### 2d. Explicitly superseded eval result

| Exact path | Rationale |
|-----------|-----------|
| `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/old7b_checkpoint_easyfirst_panel_ep2_20260414.json` | Filename prefix `old7b_` makes intent explicit; superseded |

**Proposed destination for all archive moves:**
`MoCoP/experiments/mamba_lora_bridge/archive/`

---

## 3. GITIGNORE ADDITIONS

File to edit: `MoCoP/experiments/mamba_lora_bridge/.gitignore`
(Create if it does not exist; check with `git ls-files MoCoP/experiments/mamba_lora_bridge/.gitignore`)

Add the following blocks:

```gitignore
# ── Python build artifacts ──────────────────────────────────────────────────
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# ── Ephemeral runtime session files ─────────────────────────────────────────
# These are overwritten on every run and carry no stable experiment identity.
chat_session_latest.txt
chat_turns_latest.jsonl
dual_gate_turns_latest.jsonl
mamba_bootstrap_state_latest.pt

# ── Watercooler helper files (token-risk, not experiment data) ───────────────
# Pattern covers _wc_raw*.json and _wc_digest.txt in any reviews/** subdir.
```

Add to repo root `.gitignore` (or `MoCoP/reviews/.gitignore` if scoped):

```gitignore
# Watercooler raw dumps (contain token material — never commit)
MoCoP/reviews/**/_wc_raw*.json
MoCoP/reviews/**/_wc_digest.txt
```

**Note:** `chat_session_latest.txt`, `chat_turns_latest.jsonl`, and `dual_gate_turns_latest.jsonl` are currently tracked by git (they appear in `git status` as modified). They need to be untracked first (`git rm --cached`) before the .gitignore entry takes effect. See Section 6.

---

## 4. DO-NOT-TOUCH

These are the live core. Nothing here moves or renames.

### Core server and bridge modules
- `MoCoP/experiments/mamba_lora_bridge/chat_server.py`
- `MoCoP/experiments/mamba_lora_bridge/cognitive_bridge.py`
- `MoCoP/experiments/mamba_lora_bridge/memory_evidence.py`
- `MoCoP/experiments/mamba_lora_bridge/autobiographical_memory.py`
- `MoCoP/experiments/mamba_lora_bridge/dense_associative_memory.py`
- `MoCoP/experiments/mamba_lora_bridge/astrocyte_memory_controller.py`
- `MoCoP/experiments/mamba_lora_bridge/lesson_memory.py`

### Sleep cycle modules
- `MoCoP/experiments/mamba_lora_bridge/sleep_reconcile.py`
- `MoCoP/experiments/mamba_lora_bridge/sleep_flush.py`
- `MoCoP/experiments/mamba_lora_bridge/sleep_nloop_guard.py`
- `MoCoP/experiments/mamba_lora_bridge/sleep_ethics_gate.py`
- `MoCoP/experiments/mamba_lora_bridge/run_sleep_cycle.py`

### Active checkpoint
- `MoCoP/experiments/mamba_lora_bridge/cheese_reincarnation_bridge_1.5b_codexfix.pt`

### Recent (2026-06) experiment results
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/cassian_*_20260611.*`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/panel_b_*_20260611.*`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/style_disposition_control_panel_20260611.*`
- `MoCoP/experiments/mamba_lora_bridge/results/jrt_spike/`
- `MoCoP/experiments/mamba_lora_bridge/results/monk_variable_probe_20260606/`
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws/`
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws_static_readonly/`

### Spike specs (active pipeline)
- `MoCoP/experiments/mamba_lora_bridge/spikes/DAM_PHASE0_SPEC.md`
- `MoCoP/experiments/mamba_lora_bridge/spikes/JRT_ORDERING_SPIKE_SPEC.md`
- `MoCoP/experiments/mamba_lora_bridge/spikes/MAMBA_STYLE_DISPOSITION_CONTROL_SPEC.md`
- `MoCoP/experiments/mamba_lora_bridge/spikes/ROLE_INVERSION_SPIKE_SPEC.md`
- `MoCoP/experiments/mamba_lora_bridge/spikes/TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md` (unrun but queued — see Section 5)

### Archivist Mamba package
- `MoCoP/experiments/mamba_lora_bridge/archivist_mamba/` (all files)

### Baby Alex 116 archive bundle
- `MoCoP/experiments/mamba_lora_bridge/results/baby_alex_116_pre_sleep_archive/` (entire subtree)

---

## 5. HUMAN-DECISION

Thirteen items require a judgment call before any action. None of these are touched by the tidy plan; they are listed for Laura's review.

### HD-01: `AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN.md` — complete or superseded?
**Path:** `MoCoP/experiments/mamba_lora_bridge/AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN.md`
**Question:** `autobiographical_memory.py` exists and passes 17 tests (LOG Entry 52). Is the plan fully implemented? Or was it superseded when `astrocyte_memory_controller.py` was introduced (LOG Entry 54)?
**Options:** (a) Add a "COMPLETED" note at the top; (b) Prepend `ARCHIVED_` to filename if superseded; (c) Leave as-is if still partially relevant.

### HD-02: `TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md` — add [UNRUN] marker?
**Path:** `MoCoP/experiments/mamba_lora_bridge/spikes/TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md`
**Question:** This spec was filed (recent commit) but no run entry exists in the LOG. Add `[UNRUN]` to the title/first line so it is not confused with completed spikes?
**Options:** (a) Add marker now; (b) Leave until the spike is scheduled.

### HD-03: `results/board_91_92_mlws/` — experiment result or board scrape?
**Paths:**
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws/board-91-92-20260602t064603z.json`
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws/board-91-92-20260602t064637z.json`
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws/summary_20260602T064637Z.md`
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws_static_readonly/board-91-92-static-readonly-20260603t085505z.json`
- `MoCoP/experiments/mamba_lora_bridge/results/board_91_92_mlws_static_readonly/summary_20260603T085505Z.md`
**Question:** These are named after OpenCLAW board items 91-92, not an experiment. Are they watercooler/board snapshots that belong in `MoCoP/reviews/` rather than `results/`? No LOG entry covers them.
**Options:** (a) Add a LOG stub; (b) Move to `MoCoP/reviews/`; (c) Leave as-is with a README note.

### HD-04: `results/monk_variable_probe_20260606/` — add LOG stub?
**Path:** `MoCoP/experiments/mamba_lora_bridge/results/monk_variable_probe_20260606/` (7 files: lane1 modulation probes + bridge_dc_geometry JSON)
**Question:** Dated 2026-06-06, predates LOG Entry 54 (2026-06-08). No LOG entry for this probe. Was it a casual development run feeding into Entry 54? If yes, add a cross-reference. If it stands alone, add a stub.

### HD-05: `chat_session_latest.txt` + `chat_turns_latest.jsonl` + `dual_gate_turns_latest.jsonl` — untrack or snapshot?
**Paths:**
- `MoCoP/experiments/mamba_lora_bridge/chat_session_latest.txt`
- `MoCoP/experiments/mamba_lora_bridge/chat_turns_latest.jsonl`
- `MoCoP/experiments/mamba_lora_bridge/dual_gate_turns_latest.jsonl`
**Question:** These are currently tracked by git. They will be silently overwritten on the next run. Options: (a) Untrack with `git rm --cached` and add to .gitignore (recommended); (b) Rename with a session timestamp before untacking to preserve their current content.

### HD-06: `mamba_bootstrap_state_latest.pt` (root-level) — untrack or rename?
**Path:** `MoCoP/experiments/mamba_lora_bridge/mamba_bootstrap_state_latest.pt`
**Question:** Same `_latest` naming problem as HD-05. This is a runtime bootstrap state that will be overwritten. The archive bundle has its own timestamped copy. Should this be gitignored (it's a large binary) or renamed to a dated version?

### HD-07: `mamba_bootstrap_state_latest.pt` inside the archive bundle — rename?
**Path:** `MoCoP/experiments/mamba_lora_bridge/results/baby_alex_116_pre_sleep_archive/baby_alex_116_pre_sleep_archive_20260603T204746Z/mamba_bootstrap_state_latest.pt`
**Question:** This file is inside a dated archive dir and was captured at archive time. The `_latest` name inside a frozen archive is misleading. Should it be renamed to `mamba_bootstrap_state_20260603T204746Z.pt`? Low priority, but clarifies intent.

### HD-08: Remote-only artifacts — document or fetch?
Three result sets exist only on Steve or ML-WS (EXP-01, EXP-02, EXP-03):
- Steve: `mvp0_raw_state_sjt_alpha005/010/020.json`
- ML-WS `/tmp/`: `dam_phase0_sweep.json`, `dam_qdrant_scaling.json`, `dam_diverse_eval.json`
- ML-WS: `results/role_inversion_spike_20260609/` (v1 + v2)
**Question:** Accept LOG-as-record (no repo commit needed) or fetch and commit to repo? ML-WS `/tmp/` is volatile — if those files matter, they should be fetched now.

### HD-09: `mvp2_hidden_gated_1p5b.pt` — locate or document as lost
**Question (EXP-10):** LOG Entry 35 references this checkpoint (context cosine 0.948) but it is not in the repo. Is it on Steve? If so, commit or explicitly document as Steve-local in LOG.

### HD-10: `kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt` — archive or keep warm?
**Path:** `MoCoP/experiments/mamba_lora_bridge/kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt`
**Question:** Listed under ARCHIVE in Section 2a above, but Laura may want it accessible if Kimi roleplay experiments resume. Confirm before moving.

### HD-11: `live_gate_threshold_sweep_2026-04-03.json` — add LOG cross-reference?
**Paths:**
- `MoCoP/experiments/mamba_lora_bridge/live_gate_threshold_sweep_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/live_gate_threshold_sweep_2026-04-03_summary.md`
**Question (EXP-13):** No LOG entry explicitly covers this filename. Do LOG Entries 21/22 (live gate alpha probes, 2026-04-03) cover this data? If yes, add an artifact cross-reference line to those entries.

### HD-12: `results/` and `run_reincarnation/` — add INDEX.md?
**Question (EXP-08):** `results/` has 12+ subdirs; `run_reincarnation/` has 20+ subdirs and flat JSONs. No top-level index. Should an INDEX.md be added? (Out of scope for tidy cleanup but a low-cost improvement.)

### HD-13: `spikes/` — add README listing run vs. unrun?
**Question (EXP-09):** `spikes/` has 5 spec files at different completion states (DAM_PHASE0 run, JRT run, MAMBA_STYLE run, ROLE_INVERSION run, TEMPORAL_CASCADE unrun). A one-page README listing status would prevent confusion.

---

## 6. EXACT COMMANDS

Read-only plan. The commands below are written for Laura to review and execute herself. Nothing has been run.

### Step 1: Create the branch

```powershell
git checkout -b docs/theory-reconciliation
```

### Step 2: Remove trash (pyc + pytest cache)

```powershell
# Remove all __pycache__ directories
Get-ChildItem -Recurse -Path "MoCoP\experiments" -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force

# Remove the .pytest_cache directory
Remove-Item -Recurse -Force "MoCoP\experiments\mamba_lora_bridge\.pytest_cache"
```

### Step 3: Move archive items to archive/

```powershell
$archiveDir = "MoCoP\experiments\mamba_lora_bridge\archive"

# 2a — March 2026-03-18 activation session .pt weights (10 files)
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\activation_session_20260318_202311.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\activation_session_20260318_203419.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\activation_session_20260318_203646.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\activation_session_20260318_204514.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\activation_session_20260318_210957.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\activation_session_20260318_211313.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\activation_session_20260318_211751.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\scripted_warm_opus_20260318_213202.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\scripted_cold_clinical_20260318_213401.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions\scripted_adversarial_20260318_213439.pt" $archiveDir

# 2a — 1.5b and 1.5b_input_gate target_cheese .pt weights (6 files)
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions_1.5b\target_cheese_1_the_terminal_and_the_phoenix.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions_1.5b\target_cheese_2_the_gps_and_the_solution_space.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions_1.5b\target_cheese_3_the_rabbit_hole_of_subjectivity.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions_1.5b_input_gate\target_cheese_1_the_terminal_and_the_phoenix.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions_1.5b_input_gate\target_cheese_2_the_gps_and_the_solution_space.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\activation_sessions_1.5b_input_gate\target_cheese_3_the_rabbit_hole_of_subjectivity.pt" $archiveDir

# 2a — Superseded bridge .pt weights (4 files — SKIP codexfix)
Move-Item "MoCoP\experiments\mamba_lora_bridge\cheese_reincarnation_bridge.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\cheese_reincarnation_bridge_1.5b.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\cheese_reincarnation_bridge_7b.pt" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt" $archiveDir

# 2a — DFC crosscoder
Move-Item "MoCoP\experiments\mamba_lora_bridge\dfc_results\dfc_crosscoder.pt" $archiveDir

# 2b — Self-labeled archive doc
Move-Item "MoCoP\experiments\mamba_lora_bridge\ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md" $archiveDir

# 2c — Superseded utilities
Move-Item "MoCoP\experiments\mamba_lora_bridge\archive_chat_session.sh" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\compare_archive_pipeline.py" $archiveDir
Move-Item "MoCoP\experiments\mamba_lora_bridge\build_baby_alex_116_archive_bundle.py" $archiveDir

# 2d — Explicitly superseded eval result
Move-Item "MoCoP\experiments\mamba_lora_bridge\behavioral_eval_runs\old7b_checkpoint_easyfirst_panel_ep2_20260414.json" $archiveDir
```

### Step 4: Add .gitignore entries

Edit `MoCoP/experiments/mamba_lora_bridge/.gitignore` (create if missing):

```powershell
$gitignorePath = "MoCoP\experiments\mamba_lora_bridge\.gitignore"
Add-Content -Path $gitignorePath -Value @'

# ── Python build artifacts ────────────────────────────────────────────────
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# ── Ephemeral runtime session files ──────────────────────────────────────
chat_session_latest.txt
chat_turns_latest.jsonl
dual_gate_turns_latest.jsonl
mamba_bootstrap_state_latest.pt
'@
```

Add watercooler dump patterns to repo root `.gitignore`:

```powershell
Add-Content -Path ".gitignore" -Value @'

# ── Watercooler raw dumps (token material — never commit) ─────────────────
MoCoP/reviews/**/_wc_raw*.json
MoCoP/reviews/**/_wc_digest.txt
'@
```

### Step 5: Untrack the _latest runtime files (HD-05)

Run only after confirming you do not need their current content:

```powershell
git rm --cached "MoCoP/experiments/mamba_lora_bridge/chat_session_latest.txt"
git rm --cached "MoCoP/experiments/mamba_lora_bridge/chat_turns_latest.jsonl"
git rm --cached "MoCoP/experiments/mamba_lora_bridge/dual_gate_turns_latest.jsonl"
```

Also untrack the watercooler dumps if they were ever tracked:

```powershell
git rm --cached "MoCoP/reviews/ultrareview_2026-06-20/_wc_raw.json"
git rm --cached "MoCoP/reviews/ultrareview_2026-06-20/_wc_digest.txt"
```

### Step 6: Stage and commit

```powershell
# Stage deletions (trash removal)
git add -u MoCoP/experiments/

# Stage archive moves
git add MoCoP/experiments/mamba_lora_bridge/archive/

# Stage gitignore changes
git add MoCoP/experiments/mamba_lora_bridge/.gitignore
git add .gitignore

# Commit
git commit -m "$(cat <<'EOF'
chore(experiments): tidy build artifacts, archive old weights, extend gitignore

- Remove 152 .pyc files and 5 .pytest_cache files (regenerable)
- Move 21 superseded .pt weights + 4 utilities to archive/
- Add __pycache__/, *.pyc, .pytest_cache/, _latest session files to .gitignore
- Untrack _latest runtime files from git index
- Add watercooler dump patterns to root .gitignore

Plan: MoCoP/reviews/ultrareview_2026-06-20/experiments_tidy_plan.md
EOF
)"
```

---

## Summary counts

| Action | File count | Human input required |
|--------|-----------|---------------------|
| TRASH (delete) | ~157 | No |
| ARCHIVE (move) | ~25 (confirmed paths above) | Confirm kimi_roleplay .pt (HD-10) |
| GITIGNORE additions | 2 files edited | No |
| UNTRACK _latest files | 3–5 files | Confirm content not needed (HD-05) |
| HUMAN-DECISION items | 13 | Yes — see Section 5 |
| DO-NOT-TOUCH | ~1363 | — |

---

*Generated 2026-06-20. Read-only. No files were modified during plan generation.*
