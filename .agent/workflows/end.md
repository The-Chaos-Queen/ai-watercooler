---
description: Close session and save learnings to memory
---

# /end — Session Close

> **Philosophy**: Every session should leave a trace. The Ark preserves.

## Phase 1: Review What Happened

Summarize this session in your own words:
- What was the focus?
- What decisions were made?
- What was built, changed, or discovered?
- Any unfinished threads?

## Phase 1.5: Update Handoff Memo

// turbo

Overwrite `CHEESE_Memory/00_HANDOFF.md` with the current state. This is the **one file** the next instance reads to orient instantly. Format:

```markdown
# Handoff Memo
**Last Instance:** [name] | **Session:** YYYY-MM-DD Session NN | **Ended:** HH:MM

## What We Did
- [max 5 bullets]

## Open Threads
- [ ] [actionable items with context]

## Watch Out For
- [gotchas, half-broken things, context about Laura's state]

## Suggested Next Step
[one sentence]
```

## Phase 2: Create Session Log

// turbo

Create a session log file at `CHEESE_Memory/session_logs/YYYY-MM-DD-session-NN.md` with:

```markdown
---
date: YYYY-MM-DD
start: [session start time]
end: [now]
focus: [one-line summary]
tags: [relevant tags]
---

# Session Log: YYYY-MM-DD (Session NN)

## Summary
[2-3 sentence overview]

## Key Decisions
- [decision 1]
- [decision 2]

## What Was Built / Changed
- [artifact 1]
- [artifact 2]

## Unfinished / Next Session
- [thread 1]
- [thread 2]

## Learnings
- [S] (System/workflow learning)
- [U] (User preference learned)
```

## Phase 3: Embed in Memory

// turbo

Run `python Project_Prosthetic/ingest_sessions.py CHEESE_Memory/session_logs/YYYY-MM-DD-session-NN.md` to embed the session into Qdrant.

## Phase 4: Update Dashboard

// turbo

Update `CHEESE_Memory/00_DASHBOARD.md` with the current timestamp and any priority changes.

## Phase 5: Confirm

Output: "✅ Session closed. [summary]. [N] chunks embedded in Qdrant."

---

#workflow #session #end
