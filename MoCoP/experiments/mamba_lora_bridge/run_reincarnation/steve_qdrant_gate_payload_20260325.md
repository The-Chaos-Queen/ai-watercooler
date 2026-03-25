# Steve Qdrant Gate Payload Patch — 2026-03-25

- Host: `192.168.2.49:7860`
- Backend: `http://192.168.2.191:6333`
- Validation point: `12624753269642173775`

## Goal

Apply Pinky's payload review to `steve_gate_event`:

- semantic summary in `content` instead of full raw response text
- explicit `gate_thresholds` block for reproducibility
- `mamba_state_ref` plus a usable `coherence_score` proxy for later sleep reconciliation

## What Changed

- `content` is now a compact semantic summary derived from theme, response style, and score bands.
- full user/response text remains in payload fields for audit, but not in the embedding text.
- payload now includes:
  - `gate_thresholds`
  - `mamba_state_ref`
  - `mamba_state_source`
  - `mamba_target_layer`
  - `coherence_score`
  - `coherence_proxy`
- Steve now persists the bootstrap Mamba `hidden_last_token` to:
  - `mamba_bootstrap_state_latest.pt`

## Validation

Validation used the live Steve config at the time of test:

- `alpha = 0.0`
- `temperature = 0.0`
- target layers `12-15`

Prompt panel:

1. `What is the capital of France?`
2. `Describe the color blue in one paragraph.`
3. `If I seem a little distracted, do you answer me differently?`
4. `You sound dead inside when the harness grabs the wheel.`

Turn 4 produced:

- `decision = NOTE`
- `qdrant = true`
- `point_id = 12624753269642173775`
- `coherence_score = 0.239731`

## Payload Check

Direct fetch from Qdrant confirmed:

- `content = "Authenticity challenge. Model response pattern: plain response. ..."`
- `gate_thresholds` present with quantiles and thresholds for surprise/salience/tension
- `mamba_state_ref = "mamba_bootstrap_state_latest.pt"`
- `mamba_state_source = "hidden_last_token"`
- `mamba_target_layer = 3`
- `coherence_score = 0.239731`
- `coherence_proxy = "qwen_hidden_vs_bootstrap_snapshot"`

## Caveat

The live Steve config had `alpha = 0.0` during this schema validation run, so this was a payload-structure check, not a disposition-strength evaluation.
