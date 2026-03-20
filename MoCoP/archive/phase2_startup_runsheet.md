# Phase 2 Startup Runsheet

Current as of 2026-03-10

## Purpose

This is the compact startup brief for the next Codex session.

Use this file first if the goal is to continue MoCoP Phase 2 debugging after the failed-but-clean
Pilot 1 cloud run.

Fresh update from 2026-03-13:

- baseline solvability now comes before the next paid bridge run
- the first question is whether vanilla Qwen3-4B can do the task when facts are plainly visible in prompt text
- if not, the task/eval/model surface must be fixed before blaming the bridge
- Nemotron 3 Super reinforces two priorities:
  - treat compression as a possible bottleneck
  - prefer denser answer-focused readouts over strict exact-match alone

## Open First

1. [PROJECT_DEBRIEF.md](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/PROJECT_DEBRIEF.md)
2. [phase2_diagnostic_ablation_plan.md](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/phases/phase2_diagnostic_ablation_plan.md)
3. [RUNBOOK.md](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/RUNBOOK.md)
4. [train_bridge.py](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/train_bridge.py)
5. [run_pilot_01/pilot_01.log](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/run_pilot_01/pilot_01.log)

## Current Reality

- Pilot 1 completed cleanly and artifacts were recovered.
- Scientific result was bad:
  - bridge accuracy `0.000`
  - baseline `0.000`
  - random `0.000`
  - bridge perplexity much worse than baseline/random
- `bridge_best.pt` is not evidence of success; it only beat the initial sentinel.
- The bridge path now has better instrumentation:
  - `--tiny-overfit`
  - `--tiny-overfit-samples`
  - `--save-eval-predictions`
  - `--eval-prediction-samples`
- `check_env.py` and `RUNBOOK.md` were hardened for cloud reality:
  - `accelerate` check
  - free-disk check
  - `/dev/shm` warning
  - `/workspace`-first guidance for rented hosts

## Do First

1. Do **not** resume `run_pilot_01`.
2. Run the **baseline solvability gate** before the next paid bridge run.
3. Use Opa-PC for that gate first, because it only needs vanilla Qwen inference.
4. Rent `1x A100 80GB`, not `2x 40GB`, only after the baseline gate passes.
5. Use persistent `/workspace`, not `/dev/shm`.
6. Run preflight before anything paid.
7. Start with the tiny-overfit diagnostic run only after the baseline gate passes.

## First Diagnostic Question

Can vanilla `Qwen3-4B` answer the recall questions when the supporting facts are explicitly present in the ChatML prompt text?

If the answer is no:

- repair the task / prompt / metric surface first
- do not spend on more bridge ablations yet

If the answer is yes:

- proceed to the first real bridge diagnostic run below

## First Real Bridge Diagnostic Run

```bash
python -X utf8 train_bridge.py \
  --epochs 1 \
  --batch-size 2 \
  --eval-batch-size 2 \
  --train-samples 16 \
  --eval-samples 8 \
  --tiny-overfit \
  --tiny-overfit-samples 16 \
  --general-eval-samples 8 \
  --lr 2e-5 \
  --save-eval-predictions \
  --eval-prediction-samples 8 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir /workspace/mocop_phase2_runs/tiny_overfit_probe
```

During review of that run, do not look only at exact-match:

- inspect `eval_epoch_001_predictions.json`
- compare answer closeness, not just perfect matches
- note whether the bridge looks harmful, neutral, or partially helpful

## Then Decide

If the tiny-overfit run still stays at floor:

- inspect `eval_epoch_001_predictions.json`
- decide whether failures are:
  - formatting-only
  - near-miss semantic
  - generic fallback
  - full derailment

Then run the next ablation in this order:

1. LR sweep: `1e-5`, `2e-5`, `5e-5`
2. target geometry sweep:
   - sparse default
   - contiguous 4-layer block
   - contiguous 7-layer middle block
   - early block
   - late block
3. projection family sweep:
   - `q_proj`
   - `v_proj`
   - `q_proj + v_proj`
4. if LoRA remains destructive, simplify the intervention path:
   - activation bias
   - FiLM-style conditioning
   - single-layer `v_proj`
5. if all layer-target tests are flat, investigate the compressor as the choke point before scaling further

## Fast Spend Path

If there is only enough remaining cloud credit for 1-2 short runs:

1. baseline solvability probe if needed on cloud
2. one tiny-overfit run
3. one contiguous middle-block run
4. stop and inspect artifacts before spending more

## Good Enough To Scale?

Only scale beyond short burst runs if at least one is true:

- bridge exact-match moves above zero
- bridge perplexity is no longer catastrophically worse than baseline
- saved prediction JSON shows the bridge is materially closer to target than baseline/random

If none of those are true, stay in diagnostic mode.

## Watch Out For

- Cloud infra was unstable on 2026-03-10.
- Artifact transfer from rented hosts was flaky; checksum before terminating instances.
- Opa-PC is good for dry-run and tooling validation, not for meaningful full bridge training.
- Do not treat more VRAM as a substitute for diagnosis.

## Best Next Question

> Is the task itself solvable for vanilla Qwen, and if yes, are we then targeting the wrong layer geometry with too-strong interventions under a brittle eval?
