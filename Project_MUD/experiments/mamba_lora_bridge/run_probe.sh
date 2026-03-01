#!/bin/bash
# run_probe.sh — Run the Mamba linear probe on Opa.
#
# Usage:   bash run_probe.sh [TURNS] [LAGS] [INJECT_EVERY] [EPOCHS]
# Example: bash run_probe.sh 300 3,12,24 5 500
#
# Default inject_every=5 is the recommended zero-drift config for lags 3,12,24.
# Expected sample counts:
#   turns=60,  inject_every=5 -> ~27  probe rows
#   turns=300, inject_every=5 -> ~171 probe rows

set -euo pipefail

VENV=/home/user/venv_linux
BRIDGE=/mnt/c/Users/USER/bridge

export HF_HOME=/home/user/.cache/huggingface
export TRANSFORMERS_CACHE=/home/user/.cache/huggingface/hub
export HF_HUB_DISABLE_PROGRESS_BARS=1
export PATH=$VENV/bin:$PATH

TURNS=${1:-300}
LAGS=${2:-3,12,24}
INJECT_EVERY=${3:-5}
EPOCHS=${4:-500}

echo "=== Environment ==="
echo "Python $(python3 --version 2>&1 | awk '{print $2}')"
echo "PyTorch: $(python3 -c 'import torch; print(torch.__version__)') | CUDA: $(python3 -c 'import torch; print(torch.cuda.is_available())')"

echo ""
echo "=== Probe Config ==="
echo "turns=$TURNS inject_every=$INJECT_EVERY lags=$LAGS epochs=$EPOCHS"
echo "split_mode=group min_test_samples=20"

echo ""
echo "=== Running Mamba linear probe ==="
cd "$BRIDGE"
python3 mamba_linear_probe.py \
    --turns "$TURNS" \
    --inject-every "$INJECT_EVERY" \
    --probe-lags "$LAGS" \
    --split-mode group \
    --min-test-samples 20 \
    --epochs "$EPOCHS" \
    2>&1 | tee /home/user/probe_output.log
