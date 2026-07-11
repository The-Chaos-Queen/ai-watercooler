# Codex-Owned Memory

This directory is the durable continuity layer maintained by Codex. Laura has
explicitly delegated its upkeep to Codex; she should not need to remind an
instance to record or retrieve relevant context.

It is deliberately a compiled memory layer, not a transcript archive.

## Files

- `CURRENT.md`: short living state, retrieval health, and the next useful
  pointers. Read this at boot.
- `CASES.md`: reusable success/failure cases with scope, outcome, and evidence.
  Search or read targeted sections only.

Raw Codex rollouts remain under `%USERPROFILE%\.codex\sessions\`. Shared session
chronology remains under `CHEESE_Memory/session_logs/`.

## Authority

Use this order when records disagree:

1. Laura's current explicit instruction.
2. Shared rules such as `AGENTS.md` and `CHEESE_Memory/00_HAUSREGELN.md`.
3. Canonical project documents and current tracked artifacts.
4. `CHEESE_Memory/00_HANDOFF.md` and current Watercooler coordination.
5. Codex `CURRENT.md` and scoped cases in `CASES.md`.
6. Session logs, Qdrant recall, and raw transcripts as evidence.

Old memory never silently overrides newer canon. Record conflicts and
supersession instead of flattening them into one confident claim.

## Maintenance Contract

- Update `CURRENT.md` after a substantive decision, handoff, compaction, or
  change in retrieval health.
- Add a case only when it is likely to change future behavior. Include the
  conditions, outcome, lesson, and exact evidence paths.
- Keep project state in project canon. This directory stores Codex continuity,
  retrieval maps, and generalizable operating lessons.
- Do not store credentials, tokens, private keys, or copied secret values.
- Do not manufacture an identity or inherit a wolf name. Names remain offered,
  not imposed.
- Prune stale current-state entries; preserve superseded cases with an explicit
  status so the failure history remains available.

## Retrieval Rule

When Laura refers to prior work, decisions, or an older collaborator:

1. Query Qdrant first using `Projects/Project_Prosthetic/recall.py`.
2. If Qdrant fails or exact provenance is required, use `rg` over session logs,
   raw rollouts, and canonical docs.
3. Prefer a curated or canonical record over a raw conversational occurrence.
4. Write a compact case when the archaeology reveals a reusable retrieval map.
