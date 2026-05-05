# Steve Live Gate A/B - 2026-04-03

## Setup

- Host: Steve (`Qwen/Qwen2.5-1.5B`, `alpha 0.2`)
- Probe: replay of the Episode 1 cross-episode chat sequence from
  [episode1_chat_turns_latest.jsonl](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/run_reincarnation/cross_episode_smoke_20260329/episode1_chat_turns_latest.jsonl)
- Compared configs:
  - baseline: `dual_gate_supported_tension_enabled = false`
  - candidate: `dual_gate_supported_tension_enabled = true`
  - candidate threshold: `0.55`

## Artifacts

- Stochastic (`temperature 0.7`)
  - [live_gate_ab_steve_2026-04-03_baseline.json](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/live_gate_ab_steve_2026-04-03_baseline.json)
  - [live_gate_ab_steve_2026-04-03_supported_tension.json](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/live_gate_ab_steve_2026-04-03_supported_tension.json)
- Deterministic control (`temperature 0.0`)
  - [live_gate_ab_steve_2026-04-03_temp0_baseline.json](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/live_gate_ab_steve_2026-04-03_temp0_baseline.json)
  - [live_gate_ab_steve_2026-04-03_temp0_supported_tension.json](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/live_gate_ab_steve_2026-04-03_temp0_supported_tension.json)

## Result

### 1. Stochastic run looked promising but was not trustworthy

At `temperature 0.7`, the candidate run promoted turn `6` via
`attend_reason = tension_supported`, and the transcript looked somewhat less
benchmark-corrupted than the baseline. But the two runs diverged early enough
that sampling noise remained a serious confound.

### 2. Deterministic control removed the ambiguity

At `temperature 0.0`, the baseline and candidate runs were identical:

- same response text on every turn
- same gate decision on every turn
- no `tension_supported` promotions fired

That means this exact live probe does **not** currently demonstrate a real
behavioral effect from `supported_tension_attend` at threshold `0.55`.

## Interpretation

- Offline replay still says the rule is a plausible candidate.
- Live Steve evidence is weaker:
  - under sampling, it can appear to help
  - under deterministic replay, it produced no effect on this sequence

Current honest status: **testable candidate, not confirmed live win**.

## Follow-up

A deterministic threshold sweep was run afterward on the same probe and wrote a
cleaner answer:

- [live_gate_threshold_sweep_2026-04-03_summary.md](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/live_gate_threshold_sweep_2026-04-03_summary.md)

Short version: the rule fires exactly where expected on a live boundary turn
(`support_ratio = 0.5045`), but on this probe the effect is still sub-surface:
gate routing changes without changing the surface text.

## Cleanup

Steve was restored to the normal default state after the test:

- `temperature 0.7`
- `dual_gate_supported_tension_enabled = false`
- `turns = 0`

Note: `qdrant_pending_count` increased across the four probe runs because the
server is still writing sleep-tagged pending rows during these live checks.
