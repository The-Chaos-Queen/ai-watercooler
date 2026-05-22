#!/bin/bash
source ~/mocop_venv/bin/activate
cd /mnt/c/Users/tikii/bridge

echo "=== H2: Recording targets at LOWER layers (6-9) ==="
echo "Current targets: layers 12-15 v_proj (256-dim for 1.5B)"
echo "New targets: layers 6-9 v_proj"
echo ""

python3 -X utf8 record_cheese_batch.py \
  --qwen-model-id Qwen/Qwen2.5-1.5B \
  --mamba-model-id state-spaces/mamba-2.8b-hf \
  --target-layers "6:v_proj,7:v_proj,8:v_proj,9:v_proj" \
  --qwen-device cuda:0 \
  --mamba-device cpu \
  --output-dir activation_sessions_1.5b_lower \
  2>&1

echo ""
echo "=== Recording complete ==="
ls -lh activation_sessions_1.5b_lower/
