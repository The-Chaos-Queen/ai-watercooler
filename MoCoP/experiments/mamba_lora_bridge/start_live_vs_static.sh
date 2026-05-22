#!/bin/bash
# Start two servers for live vs static rr_10 comparison
# Static on 7860, Live accumulation on 7861
# Keep Qdrant enabled so /recall works and the probe stays memory-conditioned.

cd /mnt/c/Users/tikii/bridge

echo "Starting static bootstrap server on port 7860..."
nohup python3 -X utf8 chat_server.py \
  --bridge-path cheese_reincarnation_bridge_1.5b_codexfix.pt \
  --alpha 0.2 \
  --temperature 0.0 \
  --port 7860 \
  --qdrant-enabled \
  --no-dual-gate > /tmp/static_server.log 2>&1 &
echo "Static PID=$!"

# Wait a bit before starting second server (GPU memory allocation)
sleep 5

echo "Starting live accumulation server on port 7861..."
nohup python3 -X utf8 chat_server.py \
  --bridge-path cheese_reincarnation_bridge_1.5b_codexfix.pt \
  --alpha 0.2 \
  --temperature 0.0 \
  --port 7861 \
  --qdrant-enabled \
  --no-dual-gate \
  --live-accumulation > /tmp/live_server.log 2>&1 &
echo "Live PID=$!"

echo "Both servers starting. Check logs at /tmp/static_server.log and /tmp/live_server.log"
