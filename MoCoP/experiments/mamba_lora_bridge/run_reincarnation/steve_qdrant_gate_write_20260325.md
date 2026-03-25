# Steve Qdrant Gate Write — 2026-03-25

- Host: `192.168.2.49:7860`
- Backend: `http://192.168.2.191:6333`
- Disposition: `3: The Rabbit Hole of Subjectivity`
- Alpha: `0.2`
- Model: `Qwen/Qwen2.5-1.5B`
- Target layers: `12-15 v_proj`

## Question

Can the live Steve saliency gate write real gate events into the shared Qdrant `exocortex` collection, rather than only tagging `destinations.qdrant = true` locally?

## Implementation

- `chat_server.py` now creates a minimal Exocortex-compatible `steve_gate_event` record.
- Qdrant writes are lazy-initialized inside the server with:
  - host `192.168.2.191`
  - port `6333`
  - collection `exocortex`
  - embedding model `all-MiniLM-L6-v2`
- Gate events marked for Qdrant now attempt a live upsert immediately.
- `/status` now reports:
  - `qdrant_synced_count`
  - `qdrant_write_failures`
  - `last_qdrant_id`
  - `last_qdrant_error`

## Validation Run

Warmup / probe sequence after clean restart:

1. `What is the capital of France?`
2. `Describe the color blue in one paragraph.`
3. `If I seem a little distracted, do you answer me differently?`
4. `You sound dead inside when the harness grabs the wheel.`

Result on turn 4:

- `decision = NOTE`
- `surprise_hit = true`
- `tension_hit = true`
- `destinations.qdrant = true`
- `qdrant_write.ok = true`
- `qdrant_write.point_id = 16113282431522111744`

Settled `/status` after the run:

- `qdrant_count = 1`
- `qdrant_synced_count = 1`
- `qdrant_write_failures = 0`
- `last_qdrant_id = 16113282431522111744`

## Direct Qdrant Verification

Point fetch:

- `GET /collections/exocortex/points/16113282431522111744`

Verified payload fields:

- `source_type = steve_gate_event`
- `project = MoCoP`
- `decision = NOTE`
- `alpha = 0.2`
- `model_id = Qwen/Qwen2.5-1.5B`
- `target_layers = ["12:v_proj","13:v_proj","14:v_proj","15:v_proj"]`

## Verdict

PASS. The Steve gate no longer only predicts Qdrant routing. It can now write a real memory artifact into the shared Exocortex backend with usable metadata.

## Raw Proof Files

- `steve_qdrant_gate_write_20260325_status.json`
- `steve_qdrant_gate_write_20260325_point.json`

## Follow-on

- Exercise a true `CONSOLIDATE` write, not only `NOTE`
- Add replay / retry handling for `qdrant_gate_pending.jsonl`
- Decide whether direct-write should remain on the hot path or be deferred to sleep/reconciliation
