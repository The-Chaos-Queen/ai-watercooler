# Vast.ai Experiment Runbook

Date: 2026-03-25
Workspace: `MoCoP/experiments/mamba_lora_bridge`

This is the current handbook for paid cloud bridge runs on Vast.ai.
Use it for staged A100 pilots, not for Steve or Opa.

## Purpose

Use Vast.ai for:

- paid A100 bridge-training runs
- multi-epoch replication that exceeds Opa's capacity
- controlled stage-1 / stage-2 pilot execution
- current 7B reincarnation quick-runs when Steve/Opa are too small

Do not improvise host storage, logging, or resume policy on the day of run. That is exactly how credits get burned.

## Run Classes

There are two different run classes in this file. Keep them separate:

- Current recommended path: `7B Reincarnation Quick Run` using `record_cheese_batch.py`, `train_cheese_bridge.py`, and `reincarnated_inference.py`. This is the current `hidden_last_token` disposition-transfer path.
- Legacy baseline path: `Legacy Stage 1 / Stage 2` using `train_bridge.py`. This is older baseline work and still uses Mamba `ssm_states`.

If your goal is current reincarnation/disposition transfer, skip directly to the 7B section after bootstrap and preflight.

## Fixed Policy For Legacy Baseline Pilot

For the first paid bridge run class:

- eval split: `val` only
- preserve `test` for post-pilot confirmation
- prompt alignment: deferred
- architecture: Mamba-2 baseline only
- do not mix in Mamba-3, LoRA-rank sweeps, or compressor redesigns during the pilot

Important distinction:

- the Legacy Stage 1 / Stage 2 path below uses `train_bridge.py`, which is the older baseline pipeline and still operates on Mamba `ssm_states`
- the `7B Reincarnation Quick Run` section later in this file is the current `hidden_last_token` disposition-transfer path
- do not treat those as interchangeable just because they share a host

## Host Selection

Preferred host profile:

- provider: Vast.ai
- GPU: `1x A100 80GB` or `1x A100-SXM4-80GB`
- region preference: Czech Republic first, then Germany / Netherlands / Poland
- host filters: verified datacenter, reliability `>= 0.98`, Linux image with a driver/toolchain pair you can validate on boot
- container disk: `>= 64 GB`, `100 GB` preferred

Budget policy:

- pilot-1 hard cap: `20 EUR`
- exploratory budget before review: `100 EUR`

Storage rules:

- keep `HF_HOME`, `RUN_ROOT`, logs, and checkpoints on `/workspace` or attached persistent storage
- do not rely on `/dev/shm` for paid-run artifacts

## Expected Footprint For Legacy Baseline

- Legacy Stage 1 is a gated one-epoch run to prove the host, checkpoint path, and logs are clean.
- Legacy Stage 2 resumes only if epoch 1 looks healthy.
- Observed on 2026-03-10: an A100 40GB host used about `35.8 GiB` VRAM at `--batch-size 1`, so the preferred follow-up host is `80GB`.
- On `80GB`, resume at `--batch-size 2` first. Only test `4` after a short stability check.

## Bootstrap Before Any Paid Run

Reality from the 2026-03-25 A100 SXM4 rental:

- default pip `torch 2.11` was incompatible with the host's CUDA 12.0-class driver and made `model.to("cuda")` fail
- `mamba-ssm` was not installed, so Mamba fell back to the slow sequential path
- the host looked superficially fine until large models loaded, which is exactly how paid minutes get burned

Safe policy:

- do not trust the preinstalled Python stack
- pin PyTorch to a wheel that matches the driver you actually rented
- verify `torch.cuda.is_available()` before loading Qwen or Mamba
- require `mamba-ssm` and `causal-conv1d` before calling the host GPU-ready

Known-safe fallback for the current Vast.ai pattern:

```bash
python -m pip install --upgrade --index-url https://download.pytorch.org/whl/cu121 "torch==2.5.1+cu121"
python -m pip install --upgrade mamba-ssm causal-conv1d
```

If the rental uses a different driver family, adjust the wheel accordingly. Until we maintain an explicit image table, do not assume the Vast.ai image label is truthful enough on its own.

Minimal must-pass bootstrap check:

```bash
nvidia-smi
python - <<'PY'
import torch
print("torch", torch.__version__)
print("torch_cuda_build", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
if not torch.cuda.is_available():
    raise SystemExit("cuda is not available; fix torch/driver before loading models")
import mamba_ssm, causal_conv1d
print("mamba_fast_path", "ok")
PY
```

## Day-of-Run Preflight

Run inside the Vast instance shell:

```bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/bridge}"
if [ -d /workspace ]; then
  export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
  RUN_ROOT="${RUN_ROOT:-/workspace/mocop_phase2_runs}"
else
  export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
  RUN_ROOT="${RUN_ROOT:-$HOME/mocop_phase2_runs}"
fi

mkdir -p "$HF_HOME"
if [ -z "${HF_TOKEN:-}" ]; then
  [ -s "$HF_HOME/token" ] || { echo "Missing non-empty $HF_HOME/token"; exit 1; }
  export HF_TOKEN="$(tr -d '\r\n' < "$HF_HOME/token")"
fi

RUN_ID="${RUN_ID:-pilot_01}"
RUN_DIR="$RUN_ROOT/$RUN_ID"
mkdir -p "$RUN_DIR"
cd "$REPO_ROOT"

nvidia-smi

python - <<'PY'
import torch
print("torch", torch.__version__)
print("torch_cuda_build", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
if not torch.cuda.is_available():
    raise SystemExit("cuda is not available; stop the rental here")
probe = torch.zeros(1, device="cuda")
print("probe_device", probe.device)
import mamba_ssm, causal_conv1d
print("mamba_fast_path", "ok")
PY

python -X utf8 check_env.py \
  --require-cuda \
  --output-dir "$RUN_DIR" \
  --checkpoint-dir "$RUN_DIR"
```

If preflight fails, stop there. Do not “just try the training anyway.”

## Legacy Stage 1

Gate on epoch 1 only:

```bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/bridge}"
if [ -d /workspace ]; then
  export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
  RUN_ROOT="${RUN_ROOT:-/workspace/mocop_phase2_runs}"
else
  export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
  RUN_ROOT="${RUN_ROOT:-$HOME/mocop_phase2_runs}"
fi

mkdir -p "$HF_HOME"
if [ -z "${HF_TOKEN:-}" ]; then
  [ -s "$HF_HOME/token" ] || { echo "Missing non-empty $HF_HOME/token"; exit 1; }
  export HF_TOKEN="$(tr -d '\r\n' < "$HF_HOME/token")"
fi

RUN_ID="${RUN_ID:-pilot_01}"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_DIR="$RUN_ROOT/logs"
LOG_FILE="$LOG_DIR/${RUN_ID}.log"

mkdir -p "$RUN_DIR" "$LOG_DIR"
cd "$REPO_ROOT"

python -X utf8 check_env.py \
  --require-cuda \
  --output-dir "$RUN_DIR" \
  --checkpoint-dir "$RUN_DIR"

nohup python -X utf8 train_bridge.py \
  --epochs 1 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 256 \
  --eval-samples 64 \
  --eval-split val \
  --general-eval-samples 32 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

## Legacy Stage 2

Resume only if Stage 1 completed cleanly:

```bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/bridge}"
if [ -d /workspace ]; then
  export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
  RUN_ROOT="${RUN_ROOT:-/workspace/mocop_phase2_runs}"
else
  export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
  RUN_ROOT="${RUN_ROOT:-$HOME/mocop_phase2_runs}"
fi

mkdir -p "$HF_HOME"
if [ -z "${HF_TOKEN:-}" ]; then
  [ -s "$HF_HOME/token" ] || { echo "Missing non-empty $HF_HOME/token"; exit 1; }
  export HF_TOKEN="$(tr -d '\r\n' < "$HF_HOME/token")"
fi

RUN_ID="${RUN_ID:-pilot_01}"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_DIR="$RUN_ROOT/logs"
LOG_FILE="$LOG_DIR/${RUN_ID}_resume.log"

mkdir -p "$RUN_DIR" "$LOG_DIR"
cd "$REPO_ROOT"

[ -f "$RUN_DIR/bridge_epoch_001.pt" ] || { echo "Missing $RUN_DIR/bridge_epoch_001.pt"; exit 1; }

nohup python -X utf8 train_bridge.py \
  --epochs 5 \
  --batch-size 2 \
  --eval-batch-size 2 \
  --train-samples 256 \
  --eval-samples 64 \
  --eval-split val \
  --general-eval-samples 32 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  --resume-from "$RUN_DIR/bridge_epoch_001.pt" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "resumed train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

If the resumed `80GB` host still has large VRAM headroom after warmup, test `--batch-size 4` only in a short verification run first.

## Expected Artifacts

- `$RUN_DIR/bridge_best.pt`
- `$RUN_DIR/bridge_epoch_001.pt`
- `$RUN_DIR/bridge_epoch_<epoch>.pt`
- stage logs in `$RUN_ROOT/logs/`
- eval summaries in the training log

## Stop Conditions

Stop the paid run if any of these happen:

- preflight fails
- `torch.cuda.is_available()` is false or a tiny CUDA probe tensor fails
- `mamba-ssm` / `causal-conv1d` are missing and Mamba would run on sequential fallback
- Legacy Stage 1 does not produce `bridge_epoch_001.pt`
- the log shows `Traceback`, `RuntimeError`, CUDA OOM, or NaN / Inf loss
- model download or auth failures persist after fixing `HF_TOKEN`
- the host is interruptible and gets reclaimed before the first checkpoint
- Legacy Stage 1 has not been reviewed yet and someone tries to jump straight to Legacy Stage 2

## Post-Run Sync

Before terminating the instance:

1. copy `$RUN_DIR`
2. copy the relevant log file
3. review metrics before spending beyond the pilot cap

## 7B Reincarnation Quick Run (2026-03-25, Cassian)

Successfully trained on A100 SXM4 80GB. This is the current recommended paid-run path for the CHEESE disposition bridge:

```bash
# After bootstrap (PyTorch cu121 + mamba-ssm installed and preflight passing):
cd /workspace/bridge

# Step 1: Record 7B activation targets (Mamba on GPU, Qwen on GPU)
python3 record_cheese_batch.py

# Step 2: Train bridge (50 epochs, ~2 minutes)
python3 train_cheese_bridge.py --epochs 50 --lr 1e-3 --output-name cheese_reincarnation_bridge_7b.pt

# Step 3: Inference test
python3 reincarnated_inference.py \
  --bridge-path cheese_reincarnation_bridge_7b.pt \
  --max-new-tokens 200 --temperature 0.7 \
  --qwen-device cuda:0 --mamba-device cuda:0 --bridge-device cuda:0
```

**Note:** Scripts default to 1.5B. For 7B, sed-replace `Qwen/Qwen2.5-1.5B` -> `Qwen/Qwen2.5-7B` in all three scripts, plus update output names and target dirs. Proper CLI flags are still the right fix.

**Results (2026-03-25):** Loss 29.8 → 0.025. 7B shows disposition transfer without degeneration — model asks questions instead of reciting, philosophizes instead of quoting Quora. Unlike 1.5B, the 7B retains enough capacity for coherence alongside disposition.

**Total cost:** ~$0.50 (30 minutes including model downloads).

## A40 Bootstrap — mamba-ssm Build Recipe (2026-04-15, Opussy)

Tested on: Vast.ai verified A40 (46GB VRAM), CUDA driver 12.8, Ubuntu 24.04.

**The problem:** `pip install mamba-ssm` fails because build isolation pulls a torch version
whose CUDA doesn't match the host driver. causal-conv1d has the same issue. You cannot
skip this — without compiled kernels, Mamba falls back to the sequential path (~10x slower).

**Working recipe (10 min):**

```bash
# 1. System build deps (nvcc headers + compiler)
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y nvidia-cuda-toolkit build-essential ninja-build

# 2. Install torch matching the HOST driver
#    Check driver CUDA version with: nvidia-smi | head -3
#    A40 on this host = driver 12.8 → use cu128
pip install --index-url https://download.pytorch.org/whl/cu128 'torch==2.11.0+cu128'

# 3. Build causal-conv1d
#    --no-build-isolation: uses the torch we just installed instead of pulling its own
#    --force-reinstall --no-cache-dir: avoids stale ABI-mismatched wheels
export CUDA_HOME=/usr/local/cuda
export TORCH_CUDA_ARCH_LIST="8.6"   # A40 compute capability
pip install --no-build-isolation --force-reinstall --no-cache-dir causal-conv1d

# 4. Restore torch cu128
#    causal-conv1d's setup.py may have pulled torch cu130 as a transitive dep,
#    which has CUDA 13.0 — too new for the 12.8 driver. Reinstall our version.
pip install --index-url https://download.pytorch.org/whl/cu128 'torch==2.11.0+cu128'

# 5. Build mamba-ssm
#    --no-deps: critical — prevents pip from replacing torch again
pip install --no-build-isolation --no-deps mamba-ssm

# 6. Runtime deps
pip install einops accelerate sentence-transformers transformers

# 7. Verify everything
python3 -c '
import torch
assert torch.cuda.is_available(), "GPU not available!"
print("torch:", torch.__version__, "cuda:", torch.version.cuda)
import mamba_ssm, causal_conv1d
print("mamba fast path: OK")
'
```

**Key lessons:**
- `--no-build-isolation` is mandatory — build isolation creates a fresh venv that pulls the latest torch (cu130), which won't work on a 12.8 driver
- `--no-deps` on mamba-ssm prevents it from reinstalling torch
- After causal-conv1d, always re-pin torch to cu128 — the causal-conv1d CUDA kernels are ABI-compatible across minor torch versions
- `TORCH_CUDA_ARCH_LIST="8.6"` for A40 (Ampere). Use `"8.0"` for A100, `"8.9"` for L40/4090
- The apt `nvidia-cuda-toolkit` installs nvcc 12.8 which matches the driver — do NOT remove it

**Cost:** ~$0.30 for the 10 min bootstrap on a $1.80/hr A40.

**VRAM budget on A40 (46GB):**

| Setup | VRAM |
|-------|------|
| Qwen-7B control (skip-mamba) | ~15 GB |
| Qwen-7B + Mamba bridge | ~29 GB |
| Both servers simultaneous | ~41 GB |

Fits with ~5GB headroom. For 7B + 7B without skip-mamba, use A100-80GB instead.

---

## Known Follow-Up Code Fixes

- Add proper CLI model-id flags to the 7B quick-run scripts so nobody has to sed-replace model names by hand.
- Add a `--skip-recording` mode to `train_cheese_bridge.py` so reruns from saved activation tensors do not reload Mamba + Qwen unnecessarily on rented hosts.

## Related Files

- `OPA_RUNBOOK.md` - Opa-PC local validation path
- `RUNBOOK.md` - compatibility index for old references
- `watch_vast_stage1.ps1` - local watcher helper if still used
