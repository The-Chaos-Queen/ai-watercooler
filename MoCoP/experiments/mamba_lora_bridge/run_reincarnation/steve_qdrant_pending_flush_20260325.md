# Steve Qdrant Pending Flush — 2026-03-25

- Host: `192.168.2.49`
- Backend: `http://192.168.2.191:6333`
- Validation point: `11470743235864348259`

## Goal

Build the minimal migration prerequisite from Anda's review:

- keep a local pending log
- flush queued rows into Qdrant outside the live chat turn
- do this before switching the default write mode away from hot-path direct writes

## Implemented

- New flush script: `flush_qdrant_pending.py`
- New Steve wrapper: `run_steve_qdrant_flush.ps1`

Behavior:

- read `qdrant_gate_pending.jsonl`
- upsert rows into Qdrant `exocortex`
- append successes to `qdrant_gate_flushed.jsonl`
- rewrite pending file with only remaining failures/unprocessed rows

## Validation

Synthetic queued row:

- session: `flush-test-2026-03-25T15-06-30`
- decision: `NOTE`
- source: `steve_pending_flush_test`

Result after flush:

- `qdrant_gate_pending.jsonl` size: `0`
- `qdrant_gate_flushed.jsonl` contains the archived row
- direct Qdrant fetch confirms point `11470743235864348259`

## Notes

- First validation exposed a real Windows edge case: UTF-8 BOM from a locally written JSONL row.
- `flush_qdrant_pending.py` is now BOM-tolerant on read (`line.lstrip("\\ufeff")`).

## Verdict

PASS. Steve now has a minimal off-hot-path flush mechanism for queued gate writes. This is enough to support the next migration step: make pending-log the default path and direct-write the exception.
