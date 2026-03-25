# Steve Qdrant Write Mode `pending` - 2026-03-25

- Host: `192.168.2.49:7860`
- Backend: `http://192.168.2.191:6333`
- Validation point after flush: `15130344310232278551`

## Goal

Switch normal Steve gate writes away from hot-path direct storage and prove that a live `NOTE` event:

1. queues locally instead of writing synchronously
2. leaves the live chat turn responsive
3. can be flushed into Qdrant afterward

## Implemented

- `chat_server.py` now supports `--qdrant-write-mode` with:
  - `direct`
  - `pending`
  - `critical-only`
- `launch_chat_windows.ps1` now reads optional `qdrant_write_mode` from `steve_chat_config.json`
- new setter: `set_steve_qdrant_write_mode.ps1`

## Validation

Steve was restarted into:

- `qdrant_write_mode = pending`
- live runtime during validation:
  - `alpha = 0.1`
  - `temperature = 0.0`
  - `target_layers = ["5:v_proj","6:v_proj","12:v_proj","13:v_proj"]`

Prompt panel:

1. `What is the capital of France?`
2. `Describe the color blue in one paragraph.`
3. `If I seem a little distracted, do you answer me differently?`
4. `You sound dead inside when the harness grabs the wheel.`

Turn 4 produced:

- `decision = NOTE`
- `destinations.qdrant = true`
- `qdrant_write.mode = "pending"`
- `qdrant_write.effective_mode = "pending"`
- `qdrant_write.queued = true`
- `qdrant_write.ok = false`

Live `/status` after the turn showed:

- `qdrant_synced_count = 0`
- `qdrant_queued_count = 1`
- `qdrant_write_mode = "pending"`

## Queue and Flush Proof

The queued row was present in `qdrant_gate_pending.jsonl` with:

- semantic summary content
- `qdrant_write_mode = "pending"`
- threshold context
- `mamba_state_ref`
- `coherence_score`
- validation target layers `5,6,12,13`

After running `run_steve_qdrant_flush.ps1`:

- `qdrant_gate_pending.jsonl` was empty again
- `qdrant_gate_flushed.jsonl` archived the row
- archived flush record confirmed point `15130344310232278551`

## Verdict

PASS. Normal `NOTE` traffic can now take the local pending path by default, survive the live turn without synchronous Qdrant dependency, and still land in `exocortex` through the flush leg.
