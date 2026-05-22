#!/bin/bash
cd /mnt/c/Users/tikii/bridge
/root/mocop_venv/bin/python3 -X utf8 chat_server.py \
  --bridge-path kimi_roleplay_bridge_1.5b_2026-04-03.pt \
  --skip-mamba \
  --alpha 0.0 \
  --port 7860 \
  --qdrant-enabled \
  --no-dual-gate 2>&1 | head -30
