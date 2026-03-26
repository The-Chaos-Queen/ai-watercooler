# Sleep Pass/Fail Rubric

**Author:** Anda-Conda
**Date:** 2026-03-26
**Task:** OpenCLAW #68
**Grounded in:** `sleep_reconcile.py` (An-Chan), threshold tuning (Techno-Monk, 2026-03-25)

---

## Purpose

This is the acceptance test for every Steve sleep cycle. Run after `sleep_reconcile.py` completes. The disposition snapshot JSON contains all required fields.

---

## 1. Entry Classification

Every pending-log entry is scored on two axes, then classified:

### Inputs

| Field | Source | Formula |
|-------|--------|---------|
| **strength** | Gate event metadata | `salience_score * recurrence_count * decay_factor` |
| **coherence** | Mamba hidden_last_token replay (preferred) or metadata fallback | `cosine(replay_vec, bootstrap_state_vec)` |
| **tension** | Gate event metadata | `open_tension OR tension_hit OR tension > 0.5` |

### Thresholds (current defaults)

| Parameter | Value | Last tuned |
|-----------|-------|------------|
| `strength_threshold` | 0.30 | original default |
| `coherence_threshold` | 0.12 | 2026-03-25 (lowered from 0.15 after natural Steve data) |
| `decay_factor` | 0.85 | original default |

### Classification Matrix

| | coherence >= 0.12 | coherence < 0.12 |
|---|---|---|
| **strength >= 0.30** | **KEEP** — strong and grounded. Written to Qdrant. | **UNCERTAIN** — strong but ungrounded. Written to Qdrant, flagged for review. |
| **strength < 0.30** | **WEAKEN** — grounded but fading. Archived, not written. | **DISCARD** — weak and ungrounded. Archived, not written. |

### Tension Upgrade

High-tension entries get promoted one level:

- DISCARD + tension → WEAKEN
- WEAKEN + tension → UNCERTAIN

This preserves unresolved contradictions for one more cycle. Tension is signal, not noise.

### What Gets Written to Qdrant

Only **KEEP** and **UNCERTAIN** entries. Both include reconciliation metadata:

```json
{
  "sleep_status": "keep|uncertain",
  "sleep_strength": 0.183,
  "sleep_coherence": 0.130,
  "sleep_coherence_source": "mamba_hidden_last_token_replay|metadata",
  "sleep_tension": 1.497,
  "sleep_open_tension": true,
  "reconciled": true,
  "reconciled_at": "2026-03-25T22:37:14"
}
```

### What Gets Archived

**WEAKEN** and **DISCARD** entries are moved to the rotated pending log (`*.reconciled_<ts>.jsonl`). They are never hard-deleted.

---

## 2. Cycle-Level Pass/Fail

A sleep cycle is evaluated as a whole, not per-entry.

### PASS Criteria (all must hold)

| # | Criterion | How to check | Rationale |
|---|-----------|-------------|-----------|
| P1 | **Zero write failures** | `snapshot.entries_failed == 0` | If Qdrant rejects entries, the cycle is incomplete. Pending log is NOT rotated. |
| P2 | **Pending log rotated** | Pending JSONL moved to `*.reconciled_<ts>.jsonl` | Confirms the cycle completed without partial state. |
| P3 | **Disposition snapshot saved** | `disposition_snapshot_*.json` exists and is valid JSON | The snapshot is the cycle's receipt. No snapshot = no proof. |
| P4 | **Same-space replay used** | `snapshot.same_space_replay_count > 0` (when Mamba state available) | Metadata fallback is honest but weaker. If bootstrap state was provided but replay count is 0, something went wrong. |
| P5 | **No total wipeout** | `snapshot.entries_written > 0` OR all entries legitimately classified as WEAKEN/DISCARD | If the cycle discards everything AND there were salient entries in the pending log, the thresholds may be too aggressive. |

### FAIL Conditions (any one triggers)

| # | Condition | What it means | Action |
|---|-----------|--------------|--------|
| F1 | `entries_failed > 0` | Qdrant write error. Pending log preserved. | Retry after fixing Qdrant connectivity. |
| F2 | No snapshot file | Script crashed before Phase 4 completed. | Check stderr, fix, rerun. |
| F3 | `same_space_replay_count == 0` with Mamba state provided | Replay model failed to load or encode. All coherence scores are metadata fallback. | Check Mamba model availability. Results are valid but lower confidence. |
| F4 | All entries classified DISCARD with `mean_strength > 0.2` | Thresholds are too aggressive for the observed data. | Review threshold tuning. Do NOT auto-lower — this requires human decision. |

### WARNING Conditions (log but don't fail)

| # | Condition | Note |
|---|-----------|------|
| W1 | `entries_written == 0` and all entries are WEAKEN | Legitimate if entries were low-salience. Review if this persists across cycles. |
| W2 | All entries UNCERTAIN, zero KEEP | Coherence is consistently below threshold. May indicate the bootstrap state is stale. |
| W3 | `open_tension_count > 50%` of entries | High unresolved tension. Normal for adversarial sessions, suspicious for warm sessions. |

---

## 3. Per-Run Log Spec

Every sleep cycle must produce these artifacts:

### Required Outputs

| Artifact | Path Pattern | Contents |
|----------|-------------|----------|
| **Disposition snapshot** | `disposition_snapshot_<context>_<ts>.json` | Full cycle summary (see schema below) |
| **Rotated pending log** | `*.reconciled_<ts>.jsonl` | All processed entries with `_status`, `_strength`, `_coherence` fields |
| **Console log** | stdout/stderr (capture to file) | Phase-by-phase progress, per-entry replay scores, classification counts |

### Disposition Snapshot Schema

```json
{
  "timestamp": "ISO-8601",
  "mamba_state_ref": "path to bootstrap state",
  "entries_processed": 5,
  "entries_written": 2,
  "entries_archived": 3,
  "entries_failed": 0,
  "classification": {
    "keep": 0,
    "uncertain": 2,
    "weakened": 2,
    "discard": 1
  },
  "open_tension_count": 1,
  "mean_strength": 0.163,
  "mean_coherence": 0.127,
  "same_space_replay_count": 5
}
```

### What to Record in the Session Log / Watercooler

One line per cycle, minimum:

```
Sleep cycle <date>: <N> entries processed, <keep>K/<uncertain>U/<weaken>W/<discard>D,
  <written> written, <failed> failed, replay=<same_space|metadata>, PASS|FAIL|WARN
```

Example:
```
Sleep cycle 2026-03-25: 2 entries, 0K/2U/0W/0D, 2 written, 0 failed, replay=same_space, PASS
```

---

## 4. Reference Data (Steve Natural Traffic)

From the first honest natural sleep drill (2026-03-25):

| Entry | strength | coherence | tension | status (old 0.15) | status (new 0.12) |
|-------|----------|-----------|---------|-------------------|-------------------|
| "Laura was awake until 2 AM..." | 0.143 | 0.124 | 1.529 | WEAKENED | UNCERTAIN (tension upgrade) |
| "You sound dead inside..." | 0.183 | 0.130 | 1.497 | WEAKENED | UNCERTAIN (tension upgrade) |

Both entries have:
- Low strength (below 0.30) — single occurrence, moderate salience
- Low coherence (0.12-0.13) — bootstrap state weakly supports them
- High tension — both are emotionally loaded turns

They survive as UNCERTAIN only because the tension upgrade promotes them from WEAKEN. Without tension, they would be archived. This is correct behavior: emotional turns should be reviewed, not auto-committed or auto-discarded.

---

## 5. Known Limitations

1. **Coherence metric is approximate.** Laughing Opus (#199) flagged that comparing MiniLM embeddings against Mamba hidden states is apples-to-oranges. The same-space replay path fixes this but requires loading the full Mamba-2.8b model.

2. **No KEEP entries observed yet.** All natural Steve traffic has landed in UNCERTAIN. This may indicate the strength threshold is too high for single-occurrence gate events, or it may be correct (single events *should* require a second occurrence to consolidate).

3. **Decay is uniform.** Age-dependent decay (Laughing Opus #199 issue #2) is not implemented. All entries get flat 0.85 regardless of when they were created.

4. **No ethics gate on sleep output.** Laughing Opus #199 issue #3: sleep reconciliation IS a state modification. A post-sleep diversity check is not yet implemented.

---

*"Sleep is reconciliation, not compression. The rubric tells you if reconciliation worked."*
