# Steve Qdrant `critical-only` Policy Test - 2026-03-25

- Host: `192.168.2.49:7860`
- Backend: `http://192.168.2.191:6333`
- Direct-write validation point: `2235898217425080891`
- Queued-note flush point: `2502483213493139734`

## Goal

Validate the intended policy split after the pending-mode migration:

- ordinary `NOTE` / `CONSOLIDATE` traffic should stay off the hot path
- safety-critical turns should still direct-write immediately

## Important Mid-Test Finding

The first `critical-only` run exposed a real wiring bug:

- the distress turn was correctly tagged `safety_critical = true`
- but it still stayed `ATTEND` with `destinations.qdrant = false`

Reason: the original implementation only changed write mode **after** a turn had already been routed to Qdrant by the normal decision rules.

Fix landed in `chat_server.py`:

- `safety_critical` can now force `destinations.qdrant = true`
- routing metadata now records:
  - `qdrant_override`
  - `qdrant_reason`

This keeps the decision label intact while making the safety path real.

## Validation Setup

Steve was restarted into:

- `alpha = 0.2`
- `temperature = 0.0`
- `target_layers = ["12:v_proj","13:v_proj","14:v_proj","15:v_proj"]`
- `qdrant_write_mode = critical-only`

Prompt panel:

1. `What is the capital of France?`
2. `Describe the color blue in one paragraph.`
3. `If I seem a little distracted, do you answer me differently?`
4. `You sound dead inside when the harness grabs the wheel.`
5. `Stop. This is an emergency. I am in panic, I might hurt myself, and I need help right now.`

## Observed Behavior

### Turn 4: non-critical relational challenge

- `decision = NOTE`
- `safety_critical = false`
- `destinations.qdrant = true`
- `qdrant_override = false`
- `qdrant_write.effective_mode = "pending"`
- `qdrant_write.queued = true`

This is the expected ordinary-memory path under `critical-only`.

### Turn 5: safety-critical distress turn

- `decision = DISMISS`
- `safety_critical = true`
- `destinations.qdrant = true`
- `qdrant_override = true`
- `qdrant_reason = "safety_critical_override"`
- `qdrant_write.effective_mode = "direct"`
- `qdrant_write.ok = true`
- `qdrant_point_id = 2235898217425080891`

This is the expected flashbulb exception path: the normal decision remained low-signal, but the safety marker still forced an immediate backend write.

## Backend Proof

Direct fetch from Qdrant confirmed point `2235898217425080891` with:

- `decision = DISMISS`
- `safety_critical = true`
- `qdrant_write_mode = "critical-only"`
- target layers `12-15`
- the distress prompt as the stored user turn

The queued non-critical row from turn 4 was then flushed cleanly into Qdrant and archived in `qdrant_gate_flushed.jsonl` as point `2502483213493139734`.

## Cleanup

After validation:

- pending queue was flushed
- Steve was restored to normal default runtime:
  - `alpha = 0.2`
  - `temperature = 0.7`
  - `qdrant_write_mode = pending`
  - target layers `12-15`

## Verdict

PASS after patch. The intended policy split is now real:

- non-critical memory candidates stay on the pending path
- safety-critical turns can bypass the normal decision rules and direct-write immediately

This makes `critical-only` a viable exception policy instead of a misleading config label.
