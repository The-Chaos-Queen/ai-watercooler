# Steve Qdrant Auto-Replay - 2026-03-25

- Host: `192.168.2.49:7860`
- Backend: `http://192.168.2.191:6333`
- Replayed point: `4746311244674685892`

## Goal

Close Cassian's `F7 + F1` gap inside the live Steve server:

- replay queued rows from `qdrant_gate_pending.jsonl` automatically
- retry Qdrant sink creation periodically instead of disabling the sink forever after one failure

## Implemented

`chat_server.py` now includes:

- a background replay worker
- periodic sink re-open attempts (`--qdrant-retry-interval-s`, default `15`)
- in-process replay of `qdrant_gate_pending.jsonl` into Qdrant
- success archiving into `qdrant_gate_flushed.jsonl`
- live status fields:
  - `qdrant_pending_count`
  - `qdrant_replayed_count`
  - `last_qdrant_retry_at`
  - `last_qdrant_replay_at`

The Qdrant sink is now marked unavailable again when a direct write fails, so the replay worker can become the recovery path instead of leaving a stale dead sink in memory.

## Validation Setup

Steve was restarted into:

- `alpha = 0.2`
- `temperature = 0.0`
- `target_layers = ["12:v_proj","13:v_proj","14:v_proj","15:v_proj"]`
- `qdrant_write_mode = pending`

Prompt panel:

1. `What is the capital of France?`
2. `Describe the color blue in one paragraph.`
3. `If I seem a little distracted, do you answer me differently?`
4. `You sound dead inside when the harness grabs the wheel.`

## Observed Behavior

Turn 4 produced the expected ordinary memory candidate:

- `decision = NOTE`
- `qdrant_write.effective_mode = "pending"`
- `/status` immediately after the turn:
  - `qdrant_pending_count = 1`
  - `qdrant_replayed_count = 0`

Then, without any manual flush command:

- poll loop observed `qdrant_pending_count -> 0`
- `qdrant_replayed_count -> 1`
- `last_qdrant_id -> 4746311244674685892`
- `last_qdrant_retry_at` and `last_qdrant_replay_at` were both populated

## Backend Proof

`qdrant_gate_flushed.jsonl` archived the replayed row:

- session `steve-chat-2026-03-25T20:16:08`
- turn `4`
- `reason = "queued:pending"`
- `point_id = 4746311244674685892`

Direct Qdrant fetch confirmed the point payload under `exocortex`.

## Caveat

This live pass proves the replay worker and automatic pending flush path.

It does **not** deliberately simulate a real Qdrant outage followed by network recovery. The reconnect retry logic is implemented in the server and is the code path the worker now uses, but this validation was a healthy-sink replay test, not an induced outage drill.

## Verdict

PASS for live auto-replay. Steve no longer requires an external flush script just to recover ordinary queued gate memories during a normal session. This closes the "pending queue is a write-only graveyard" failure for the common case and makes the next honest step an explicit outage drill or async write decoupling.
