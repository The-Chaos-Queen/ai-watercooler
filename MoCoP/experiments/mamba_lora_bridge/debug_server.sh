#!/bin/bash
cd /mnt/c/Users/tikii/bridge
echo "Testing server startup..."
/root/mocop_venv/bin/python3 -u -X utf8 chat_server.py \
  --bridge-path cheese_reincarnation_bridge_1.5b_codexfix.pt \
  --skip-mamba \
  --alpha 0.0 \
  --temperature 0.0 \
  --port 7860 \
  --qdrant-enabled \
  --no-dual-gate 2>&1
echo "Exit code: $?"
