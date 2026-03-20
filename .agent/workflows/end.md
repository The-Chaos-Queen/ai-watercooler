---
description: Close session and save learnings to memory
---

# /end - Session Close

> **Philosophy**: Every session should leave a trace. The Ark preserves.

## Phase 1: Review What Happened

Summarize this session in your own words:
- What was the focus?
- What decisions were made?
- What was built, changed, or discovered?
- Any unfinished threads?

## Phase 1.5: Update Handoff Memo

// turbo

Update `CHEESE_Memory/00_HANDOFF.md` as the live control page. Keep it concise, current, and attribution-heavy. Preserve and append the `Edit Ledger`. Format:

```markdown
# C.H.E.E.S.E. Handoff

## Control Block
- Last updated: YYYY-MM-DD HH:MM TZ
- Current owner: [agent]
- Primary focus: [one line]
- Last session log: `CHEESE_Memory/session_logs/YYYY-MM-DD-session-NN.md`
- Qdrant status:
  - `00_HANDOFF.md` is not ingested by default
  - Latest session log ingest: pending|done|failed|unknown

## Current State
- [3 short bullets]

## Open Threads
- [ ] [actionable item]

## Watch Out For
- [gotcha]

## Recommended Next Step
[one sentence]

## Handoff Checklist
- Tracking surfaces updated if needed: yes|no
- Session log written: yes|no
- Session log path recorded here: yes|no
- Qdrant ingest for latest session log confirmed: yes|no
- Blocking risks called out: yes|no

## Edit Ledger
- YYYY-MM-DD HH:MM TZ | [agent] | [what changed in this file]

## Next Agent Brief
- Open first:
  - `CHEESE_Memory/00_HAUSREGELN.md`
  - `CHEESE_Memory/00_BOOT_FILES.md`
  - `CHEESE_Memory/session_logs/YYYY-MM-DD-session-NN.md`
  - [optional task-specific file]
- Decide first:
  - [decision]
- Verify before memory-dependent work:
  - [check]
```

## Phase 2: Create Session Log

// turbo

Create a session log file at `CHEESE_Memory/session_logs/YYYY-MM-DD-session-NN.md` using `.agent/workflows/session_log_template.md` as the canonical shape. Minimum format:

```markdown
---
date: YYYY-MM-DD
session: YYYY-MM-DD-session-NN
start: YYYY-MM-DDTHH:MM:SS+TZ
end: YYYY-MM-DDTHH:MM:SS+TZ
agent: [agent name]
system: [client / platform]
focus: [one-line summary]
tags: [relevant tags]
qdrant_sync: pending|done|failed|skipped
handoff_updated: true|false
tracking_updated: true|false
---

# Session Log: YYYY-MM-DD (Session NN)

## Summary
[2-3 sentence overview]

## Context Loaded
- [key boot files or task-specific docs actually read]

## Key Decisions
- [decision 1]
- [decision 2]

## What Was Built / Changed
- [artifact 1]
- [artifact 2]

## Findings
- [review result, behavior, or measured outcome]

## Risks / Watch Out For
- [risk 1]

## Unfinished / Next Session
- [thread 1]
- [thread 2]

## Memory / Retrieval Notes
- Qdrant sync status: pending|done|failed|skipped
- Ingest target: `CHEESE_Memory/session_logs/YYYY-MM-DD-session-NN.md`

## Learnings
- [S] (System/workflow learning)
- [U] (User preference learned)
```

## Phase 3: Embed in Memory

// turbo

Run `python Project_Prosthetic/ingest_sessions.py CHEESE_Memory/session_logs/YYYY-MM-DD-session-NN.md` to embed the session into Qdrant.

If ingestion is not run or fails, record that explicitly in both the session log frontmatter and `00_HANDOFF.md`.

## Phase 4: Update Shared Tracking

// turbo

Update the relevant shared tracking surface if the session changed project state:

- `CHEESE_Memory/00_HANDOFF.md` for live state
- OpenCLAW for task status
- Watercooler for short swarm coordination notes

Do not recreate or refresh the retired dashboard.

## Phase 5: Confirm

Output: "Session closed. [summary]. [N] chunks embedded in Qdrant."

---

#workflow #session #end
