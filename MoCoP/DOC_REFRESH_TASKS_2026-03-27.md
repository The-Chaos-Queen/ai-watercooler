# MoCoP Doc Refresh Tasks

**Purpose:** convert Kael's audit into an execution queue without duplicating work that is already done.

## Audit Correction First

Kael's audit is directionally right, but two files are fresher than the audit gives them credit for:

- `MoCoP/phases/phase2_status.md` is already updated through Step `5f`.
- `MoCoP/RESEARCH_PAPER.md` is already much newer than a March 18 snapshot, though it still needs a post-Step-5 expansion.

Do **not** "fix" those backward to match the audit narrative.

## Tier 1: Misleading Entry Points

### 1. `MoCoP/PROJECT_DEBRIEF.md`
- **Status:** patched into a superseded redirect.
- **Why:** this was the worst onboarding trap.
- **Next real fix:** either keep it as a short redirect permanently, or rewrite it as a truly current onboarding doc that matches Step `5f`, D0/D1, and the D2 vs Step 6 fork.

### 2. `MoCoP/MASTER_PLAN.md`
- **Why:** still contains stale Phase 3 language like `LoRA rank sweep`.
- **Fix target:** remove or historical-tag the remaining LoRA-era optimization language in the phase table, success criteria, and open questions.
- **Goal:** make the top-level roadmap reflect activation bias + growth ladder reality, not abandoned bridge branches.

### 3. `MoCoP/RESEARCH_ABSTRACT.md`
- **Why:** "current direction" is behind the actual frontier.
- **Fix target:** replace old open questions with the current fork:
  - D2 autobiographical cue-based recall / Slice 1 scaffolding
  - Step 6 multi-seed replication
  - growth-before-SAS framing

## Tier 2: Canon Narrative Catch-Up

### 4. `MoCoP/RESEARCH_PAPER.md`
- **Why:** solid foundation, but still incomplete as an external-facing narrative.
- **Missing block to add:**
  - Step 4b Mamba separation result
  - hidden-last-token vs SSM resolution
  - Step 5a reincarnation result
  - Step 5d MED result
  - Step 5e layer targeting
  - Step 5f sleep infrastructure gate
  - D0 / D1 growth ladder
  - SAE proof-of-concept
  - live Steve/Opa deployment story
- **Constraint:** keep the current strong Phase 1/2 control-hierarchy story; add, do not overwrite blindly.

### 5. `MoCoP/archive/PROJECT_DEBRIEF_archived_2026-03-26.md`
- **Why:** still useful historical artifact, but dangerous if read as current.
- **Fix target:** add a short archival warning at the top if it will continue to circulate.

## Tier 3: Link Hygiene

### 6. Broken or stale references to `MoCoP/PROJECT_DEBRIEF.md`
- **Known examples:**
  - `CHEESE_Memory/archive/00_DASHBOARD_archived_2026-03-19.md`
  - old session logs and archive notes
- **Fix target:** do not rewrite old session logs, but fix live docs and dashboards that still present the old debrief as current canon.

### 7. Historical LoRA references outside canon docs
- **Examples:**
  - theory docs
  - archived startup notes
  - old runbooks
- **Fix target:** only patch live/canonical docs. Historical docs may keep LoRA references if explicitly marked historical.

## Not Urgent / Already Good

- `MoCoP/EXPERIMENT_LADDER.md`
- `MoCoP/RESEARCH_LOG.md`
- `MoCoP/RESEARCH_BACKLOG.md`
- `MoCoP/WHY.md`
- `MoCoP/phases/phase2_status.md` (only minor cross-checking, not a major rewrite)

## Recommended Order For Kael

1. `MASTER_PLAN.md`
2. `RESEARCH_ABSTRACT.md`
3. `RESEARCH_PAPER.md`
4. archival warning pass / link hygiene

That sequence fixes the public/top-level narrative first, then the formal writeup, then the leftovers.
