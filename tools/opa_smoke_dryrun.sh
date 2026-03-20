#!/bin/bash
source /home/user/venv_linux/bin/activate
cd /mnt/c/Users/User/mamba_lora_bridge

echo "=== Dry-run smoke: train_bridge.py with Qwen2.5-7B ==="
python3 -X utf8 train_bridge.py \
  --dry-run \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --epochs 1 \
  --batch-size 2 \
  --train-samples 4 \
  --eval-samples 2 \
  --warmup-steps 1 \
  --lr 2e-5 \
  --save-eval-predictions \
  --verbose \
  2>&1

echo "=== Exit code: $? ==="
