#!/bin/bash
cd /workspace/bridge

echo "Starting 7B control server..."
nohup python3 -X utf8 chat_server.py \
  --bridge-path cheese_reincarnation_bridge_7b.pt \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --skip-mamba \
  --alpha 0.0 \
  --temperature 0.0 \
  --port 7860 \
  --no-qdrant \
  --no-dual-gate > /tmp/ctrl_7b.log 2>&1 &
echo "Control PID=$!"

echo "Starting 7B bridge server..."
nohup python3 -X utf8 chat_server.py \
  --bridge-path cheese_reincarnation_bridge_7b.pt \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --alpha 0.2 \
  --temperature 0.0 \
  --mamba-device cuda:0 \
  --port 7861 \
  --no-qdrant \
  --no-dual-gate > /tmp/bridge_7b.log 2>&1 &
echo "Bridge PID=$!"

echo "Servers launched"
