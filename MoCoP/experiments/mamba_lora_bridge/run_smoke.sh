#!/bin/bash
# run_smoke.sh — Run the cognitive bridge smoke test in WSL on Opa-PC
# One script to rule them all. No more quote gymnastics.

set -e

VENV=/home/user/venv_linux
BRIDGE=/mnt/c/Users/USER/bridge
HF_CACHE=/home/user/.cache/huggingface

export HF_HOME=$HF_CACHE
export TRANSFORMERS_CACHE=$HF_CACHE/hub
export PATH=$VENV/bin:$PATH

echo "=== Environment ==="
python3 --version
python3 -c "import torch; print('PyTorch:', torch.__version__, '| CUDA:', torch.cuda.is_available())"

echo ""
echo "=== Running smoke test ==="
cd $BRIDGE
python3 smoke_test.py 2>&1 | tee /home/user/smoke_output.log
