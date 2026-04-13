#!/bin/bash
source ~/mocop_venv/bin/activate
cd /mnt/c/Users/tikii/bridge

echo "=== REINCARNATION TEST on 4090 ==="
echo "Checkpoint: cheese_reincarnation_bridge_1.5b_codexfix.pt"
echo "Model: Qwen2.5-1.5B"
echo ""

python3 -X utf8 reincarnated_inference.py \
  --bridge-path cheese_reincarnation_bridge_1.5b_codexfix.pt \
  --qwen-model-id Qwen/Qwen2.5-1.5B-Instruct \
  --mamba-model-id state-spaces/mamba-2.8b-hf \
  --qwen-device cuda:0 \
  --mamba-device cuda:0 \
  --max-new-tokens 200 \
  2>&1 | tee reincarnation_4090_instruct_results.txt

echo ""
echo "=== RESULTS SAVED TO reincarnation_4090_results.txt ==="
