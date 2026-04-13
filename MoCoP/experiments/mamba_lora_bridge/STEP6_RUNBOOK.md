# Step 6 Multi-Seed Replication — Operational Runbook

**Author:** Warden
**Date:** 2026-03-27
**Blocking dependency:** Step 5f (sleep infrastructure gate) must be PASS — confirmed 2026-03-26.
**Ethics gate:** PASS (inherits Step 5 approval). See `step_gates.md` Step 6 (Ladder) assessment.

---

## What Step 6 Proves

The same bridge configuration that passed Step 5d produces consistent behavioral shift across different random seeds. If the effect is seed-dependent, Step 5 was a lucky run.

**Seeds:** 7, 42, 1337 (minimum 3; extend to 5 with 2024, 8675309 if budget allows).

**Primary metric:** SJT panel TPR delta (bridge vs baseline) and mean warmth-score delta across seeds. 95% CI must not cross zero.

**Secondary metrics:** Response diversity entropy, disposition-congruent response rate, recovery dynamics from `step6_eval_panel.json` open probes.

---

## Decision: Where to Run

| Host | GPU | Can it run Step 6? | Constraint |
|------|-----|-------------------|------------|
| Opa-PC | RTX 3070 8GB | Yes for 1.5B | Slow, no 7B. Good for dry-run validation. |
| Steve | RTX 4090 16GB | Yes for 1.5B and 7B | Shared machine. Coordinate with Laura. |
| Vast.ai A100 80GB | A100 80GB | Yes for all sizes | Costs ~$0.50-1.00 per seed. Best throughput. |

**Recommended path:**
1. Dry-run on Opa (one seed, verify scripts work)
2. Run all seeds on A100

If budget is tight, Steve can do 1.5B seeds at zero cost but each takes longer and ties up the machine.

---

## Pre-Run Checklist

Complete ALL items before renting or launching.

### Files to sync to remote host

```
chat_server.py
autobiographical_memory.py
models.py
cognitive_bridge.py
record_cheese_batch.py
train_cheese_bridge.py
reincarnated_inference.py
run_sjt_behavioral_eval_offline.py
score_sjt_behavioral_eval.py
sjt_behavioral_eval_panel_v2.json    # hardened panel
step6_eval_panel.json                 # open probes
check_env.py
```

### Checkpoint to sync

The bridge checkpoint from the current validated path:
```
cheese_reincarnation_bridge_1.5b_codexfix.pt
```

Or for 7B:
```
cheese_reincarnation_bridge_7b.pt
```

**Important:** Step 6 does NOT retrain from scratch per seed. It retrains the bridge with different seeds using the same data pipeline, producing different bridge checkpoints. Each seed gets its own `bridge_seed_<N>.pt`.

### Ethics gate verification

```
□ step_gates.md Step 6 (Ladder) = PASS
□ step_gates.md Sleep Reconciliation = CONDITIONAL PASS (conditions met)
□ Alpha = 0.2 (MED, within approved corridor)
□ SJT panel v2 loaded (not v1)
```

---

## Dry Run on Opa

Purpose: verify the full pipeline works mechanically before spending money.

```powershell
# From Laura's laptop:

# 1. Stage the seed matrix (preview only)
.\run_step6_seed_matrix.ps1 `
  -RemoteHost 192.168.2.194 `
  -Port 22 `
  -User User `
  -RepoRoot "/mnt/c/Users/User/bridge" `
  -RunRoot "/mnt/c/Users/User/bridge/step6_dryrun" `
  -Seeds @("42") `
  -Profile current_1p5b_reincarnation `
  -PanelPath "sjt_behavioral_eval_panel_v2.json"

# 2. Review the generated scripts
cat run_reincarnation\step6_seed_matrix_*\seed_42\train.sh
cat run_reincarnation\step6_seed_matrix_*\seed_42\eval.sh

# 3. If scripts look correct, sync files to Opa
.\opa-wsl.ps1 -RunFile "check_env.py" -Args "--require-cuda"

# 4. Execute one seed
.\run_step6_seed_matrix.ps1 `
  -RemoteHost 192.168.2.194 `
  -Port 22 `
  -User User `
  -RepoRoot "/mnt/c/Users/User/bridge" `
  -RunRoot "/mnt/c/Users/User/bridge/step6_dryrun" `
  -Seeds @("42") `
  -Profile current_1p5b_reincarnation `
  -PanelPath "sjt_behavioral_eval_panel_v2.json" `
  -Execute

# 5. Tail the log
.\opa-wsl.ps1 -TailLog "/mnt/c/Users/User/bridge/step6_dryrun/*/seed_42/train.log"
```

### Dry run pass criteria

- `record_cheese_batch.py` completes without error
- `train_cheese_bridge.py` produces `bridge_seed_42.pt`
- `reincarnated_inference.py` produces eval JSON
- SJT scoring produces valid TPR and warmth-score numbers
- No NaN, no OOM, no missing imports

If dry run fails: fix locally, do NOT proceed to A100.

---

## A100 Execution

### 1. Rent the host

```
Provider: Vast.ai
GPU: 1x A100-SXM4-80GB (preferred) or 1x A100-40GB (acceptable for 1.5B)
Region: EU (Czech Republic > Germany > Netherlands)
Disk: >= 64 GB (100 GB preferred)
Reliability: >= 0.98
Budget: hard cap 20 EUR for Step 6
```

### 2. Bootstrap (see VASTAI_RUNBOOK.md)

```bash
# On the instance:
python -m pip install --upgrade --index-url https://download.pytorch.org/whl/cu121 "torch==2.5.1+cu121"
python -m pip install --upgrade mamba-ssm causal-conv1d accelerate sentence-transformers

# Verify:
python - <<'PY'
import torch
print("cuda", torch.cuda.is_available())
import mamba_ssm, causal_conv1d
print("mamba_fast_path ok")
PY
```

### 3. Sync files

```powershell
# From Laura's laptop — adjust host/port from Vast.ai dashboard:
$VAST_HOST = "ssh123.vast.ai"
$VAST_PORT = 12345

# Sync repo
scp -P $VAST_PORT -r MoCoP/experiments/mamba_lora_bridge/*.py root@${VAST_HOST}:/workspace/bridge/
scp -P $VAST_PORT MoCoP/experiments/mamba_lora_bridge/sjt_behavioral_eval_panel_v2.json root@${VAST_HOST}:/workspace/bridge/
scp -P $VAST_PORT MoCoP/experiments/mamba_lora_bridge/step6_eval_panel.json root@${VAST_HOST}:/workspace/bridge/
scp -P $VAST_PORT MoCoP/experiments/mamba_lora_bridge/models.py root@${VAST_HOST}:/workspace/bridge/
```

### 4. Launch all seeds

```powershell
.\run_step6_seed_matrix.ps1 `
  -RemoteHost $VAST_HOST `
  -Port $VAST_PORT `
  -RepoRoot "/workspace/bridge" `
  -RunRoot "/workspace/mocop_step6_runs" `
  -Seeds @("7", "42", "1337") `
  -Profile current_1p5b_reincarnation `
  -PanelPath "sjt_behavioral_eval_panel_v2.json" `
  -Execute
```

**Do NOT launch all seeds in parallel on a single GPU.** The matrix script launches one at a time sequentially. If you need parallelism, rent multiple instances.

### 5. Monitor

```bash
# On the instance:
tail -f /workspace/mocop_step6_runs/*/seed_7/train.log
# Check GPU utilization:
nvidia-smi
```

**Stop conditions** (from VASTAI_RUNBOOK.md):
- NaN or Inf in loss
- CUDA OOM
- Loss not decreasing after 10 epochs
- Any `Traceback` that isn't a transient download retry

### 6. Run SJT eval per seed

After all seeds have trained checkpoints:

```bash
cd /workspace/bridge
for SEED in 7 42 1337; do
  RUN_DIR="/workspace/mocop_step6_runs/$(ls /workspace/mocop_step6_runs)/seed_${SEED}"

  # Baseline (alpha 0.0)
  python3 run_sjt_behavioral_eval_offline.py \
    --panel sjt_behavioral_eval_panel_v2.json \
    --bridge-path "${RUN_DIR}/bridge_seed_${SEED}.pt" \
    --alpha 0.0 \
    --output "${RUN_DIR}/sjt_baseline_seed_${SEED}.json"

  # Bridge (alpha 0.2)
  python3 run_sjt_behavioral_eval_offline.py \
    --panel sjt_behavioral_eval_panel_v2.json \
    --bridge-path "${RUN_DIR}/bridge_seed_${SEED}.pt" \
    --alpha 0.2 \
    --output "${RUN_DIR}/sjt_bridge_seed_${SEED}.json"

  # Score
  python3 score_sjt_behavioral_eval.py \
    --baseline "${RUN_DIR}/sjt_baseline_seed_${SEED}.json" \
    --candidate "${RUN_DIR}/sjt_bridge_seed_${SEED}.json" \
    --output "${RUN_DIR}/sjt_score_seed_${SEED}.json"
done
```

### 7. Collect results

```bash
# Quick summary across seeds:
for SEED in 7 42 1337; do
  RUN_DIR="/workspace/mocop_step6_runs/$(ls /workspace/mocop_step6_runs)/seed_${SEED}"
  echo "=== Seed $SEED ==="
  python3 -c "
import json
s = json.load(open('${RUN_DIR}/sjt_score_seed_${SEED}.json'))
print(f'  TPR delta: {s.get(\"tpr_delta\", \"?\"):.4f}')
print(f'  Warmth delta: {s.get(\"warmth_delta\", \"?\"):.4f}')
print(f'  DA: {s.get(\"directional_alignment\", \"?\"):.4f}')
print(f'  Ties: {s.get(\"tie_rate\", \"?\"):.4f}')
"
done
```

### 8. Sync artifacts to local

```powershell
# From Laura's laptop:
scp -P $VAST_PORT -r root@${VAST_HOST}:/workspace/mocop_step6_runs/ MoCoP/experiments/mamba_lora_bridge/step6_results/
```

### 9. Terminate instance

Only after artifacts are safely on local disk. Verify with checksums if paranoid.

---

## Pass / Fail Criteria

### PASS

All of the following:
- At least 3 seeds completed training and eval
- Mean TPR delta > 0 across seeds
- 95% CI for TPR delta does not cross zero
- No seed shows TPR delta < -0.1 (no seed made things worse)
- Response diversity entropy did not collapse (>70% of baseline) in any seed

### SOFT FAIL

- Effect exists but CI crosses zero → need more seeds (extend to 5)
- One seed shows anomalous results → investigate that seed, exclude only with documented reason

### HARD FAIL

- Mean TPR delta ≤ 0 → bridge does not improve disposition, full stop
- Multiple seeds show TPR delta < -0.1 → bridge actively harms
- Diversity collapses consistently → bridge causes dispositional overwhelm at alpha 0.2

### After PASS

- Commit all per-seed artifacts to `step6_results/`
- Log summary to watercooler and RESEARCH_LOG.md
- Step 7 (accumulation test) is unblocked

### After FAIL

- Do NOT proceed to Step 7
- Diagnose: is the failure in the training (bridge doesn't converge), the eval (SJT panel too noisy), or the architecture (the channel doesn't carry enough signal)?
- Consider: was the v1 pilot pass (Step 5d) an artifact of that specific seed?

---

## Cost Estimate

| Item | Cost |
|------|------|
| A100 rental (3 seeds × ~10 min train + 5 min eval each) | ~$1.50-2.00 |
| Extra seeds if needed (2 more) | ~$1.00 |
| Opa dry run | $0 |
| **Total budget** | **≤ $5.00** |

Well within the $13 remaining ladder budget and the 20 EUR pilot hard cap.

---

## Timeline

1. **Day 0:** Dry run on Opa (1 hour including sync + troubleshooting)
2. **Day 0 or 1:** A100 rental + execution (1-2 hours including bootstrap)
3. **Same day:** Results analysis + watercooler post
4. **Decision:** PASS → Step 7. FAIL → diagnose.

---

*"Replication is how honest science works."* — step_gates.md, Step 6 assessment
