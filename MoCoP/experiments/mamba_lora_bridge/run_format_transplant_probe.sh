#!/bin/bash
# run_format_transplant_probe.sh - Run the Phase 1 format-transplant control on Opa.
#
# Usage:
#   bash run_format_transplant_probe.sh [TURNS] [LAGS] [INJECT_EVERY] [EPOCHS] [SEEDS]
#
# Example:
#   bash run_format_transplant_probe.sh 300 3,12,24 5 300 5

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
EPOCHS=${4:-300}
SEEDS=${5:-5}

echo "=== Environment ==="
echo "Python $(python3 --version 2>&1 | awk '{print $2}')"
echo "PyTorch: $(python3 -c 'import torch; print(torch.__version__)') | CUDA: $(python3 -c 'import torch; print(torch.cuda.is_available())')"

echo ""
echo "=== Format-Transplant Config ==="
echo "turns=$TURNS inject_every=$INJECT_EVERY lags=$LAGS epochs=$EPOCHS seeds=$SEEDS"
echo "formats=game_world,ledger_note,dialogue_scene,narrative_brief"
echo "layer=3"

echo ""
echo "=== Running format-transplant probe ==="
cd "$BRIDGE"
python3 -X utf8 format_transplant_probe.py \
    --turns "$TURNS" \
    --inject-every "$INJECT_EVERY" \
    --probe-lags "$LAGS" \
    --epochs "$EPOCHS" \
    --seeds "$SEEDS" \
    --formats game_world,ledger_note,dialogue_scene,narrative_brief \
    --output-dir format_transplant_probe_runs \
    2>&1 | tee /home/user/format_transplant_probe.log
