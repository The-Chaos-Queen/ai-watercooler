---
description: Canonical session log template for CHEESE / Athena sessions
---

# Session Log Template

Copy this structure when creating a new file in `CHEESE_Memory/session_logs/`.

```markdown
---
date: YYYY-MM-DD
session: YYYY-MM-DD-session-NN
start: YYYY-MM-DDTHH:MM:SS+TZ
end: YYYY-MM-DDTHH:MM:SS+TZ
agent: [agent name]
system: [client / platform]
focus: [one-line summary]
tags: [tag1, tag2, tag3]
qdrant_sync: pending|done|failed|skipped
handoff_updated: true|false
tracking_updated: true|false
---

# Session Log: YYYY-MM-DD (Session NN)

## Summary
[2-3 sentence overview]

## Context Loaded
- [boot or task-specific files read]

## Key Decisions
- [decision 1]
- [decision 2]

## What Was Built / Changed
- [artifact 1]
- [artifact 2]

## Findings
- [measured result, review result, or technical observation]

## Risks / Watch Out For
- [risk, blocker, or operational caveat]

## Unfinished / Next Session
- [next thread 1]
- [next thread 2]

## Memory / Retrieval Notes
- Qdrant sync status: pending|done|failed|skipped
- Ingest target: `CHEESE_Memory/session_logs/YYYY-MM-DD-session-NN.md`

## Learnings
- [S] [system/workflow learning]
- [U] [Laura preference or collaboration learning]
```

## Notes

- Keep the log append-only once the session is closed.
- `00_HANDOFF.md` is the live boot summary; the session log is the archive.
- If Qdrant ingestion did not happen, say so explicitly.
