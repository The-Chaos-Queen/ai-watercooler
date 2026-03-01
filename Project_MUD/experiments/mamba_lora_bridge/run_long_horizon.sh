#!/bin/bash
# run_long_horizon.sh - Run long-horizon memory evaluation in WSL.

set -e

VENV=/home/user/venv_linux
BRIDGE=/mnt/c/Users/USER/bridge
HF_CACHE=/home/user/.cache/huggingface

export HF_HOME=$HF_CACHE
export TRANSFORMERS_CACHE=$HF_CACHE/hub
export PATH=$VENV/bin:$PATH

TURNS=${1:-50}
LAGS=${2:-5,25}
INJECT_EVERY=${3:-10}
LORA_MODE=${4:-on}

echo "=== Environment ==="
python3 --version
python3 -c "import torch; print('PyTorch:', torch.__version__, '| CUDA:', torch.cuda.is_available())"

echo ""
echo "=== Running long horizon eval ==="
cd $BRIDGE
python3 long_horizon_eval.py \
    --turns "$TURNS" \
    --probe-lags "$LAGS" \
    --inject-every "$INJECT_EVERY" \
    --lora-mode "$LORA_MODE" \
    2>&1 | tee /home/user/long_horizon_output.log
