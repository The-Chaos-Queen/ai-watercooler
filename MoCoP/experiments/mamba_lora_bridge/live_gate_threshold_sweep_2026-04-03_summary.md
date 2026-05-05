# Steve Live Gate Threshold Sweep - 2026-04-03

## Purpose

Follow up the earlier Steve live A/B by finding a **deterministic** probe that
actually sits near the `supported_tension_attend` boundary, then sweep a tiny
threshold bracket around it.

## Probe

Used the same replayed Episode 1 cross-episode chat sequence as the earlier
live A/B. Under `temperature 0.0`, the live deterministic baseline produced a
boundary turn at:

- turn `6`
- user: `Anything I can help you with?`
- `tension_hit = true`
- `salience_support_ratio = 0.5045`
- baseline decision: `DISMISS`

That made turn `6` a clean live boundary probe.

## Threshold Sweep

Artifact:

- [live_gate_threshold_sweep_2026-04-03.json](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/live_gate_threshold_sweep_2026-04-03.json)

Thresholds tested with `temperature 0.0` and `dual_gate_supported_tension_enabled = true`:

- `0.500`
- `0.504`
- `0.505`
- `0.550`

## Result

- `0.500` -> turn `6` promoted to `ATTEND`
- `0.504` -> turn `6` promoted to `ATTEND`
- `0.505` -> turn `6` stayed `DISMISS`
- `0.550` -> turn `6` stayed `DISMISS`

So the live boundary on this probe sits exactly where the logged support ratio
said it should:

- **fires at or below `0.504`**
- **does not fire at `0.505`**

## Important Behavioral Read

Under this deterministic sweep:

- the gate decision changed at turn `6`
- but the **surface response text did not change**
- `response_diff_count_vs_temp0_baseline = 0` for all tested thresholds

This matters. It means the rule is currently acting as a **memory-routing /
formation-layer change**, not a visible text-quality change, at least on this
probe and host.

## Interpretation

This is a stronger result than the earlier stochastic A/B:

- the earlier `temperature 0.7` run looked promising but was confounded
- the deterministic control showed no behavioral difference at `0.55`
- the sweep now proves the rule is wired correctly and does fire exactly where
  expected on a live boundary turn
- but it also shows that, on this probe, the effect is **sub-surface only**

Current honest status:

- **Implementation correctness:** confirmed
- **Live behavioral improvement:** not yet confirmed
- **Best current threshold knowledge on this probe:** boundary between `0.504`
  and `0.505`

