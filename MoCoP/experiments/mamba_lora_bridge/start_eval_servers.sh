#!/bin/bash
# Start the two eval servers in background

cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3
CKPT=cheese_reincarnation_bridge_1.5b_codexfix.pt

# Kill any existing listeners on these ports
fuser -k 7860/tcp 2>/dev/null || true
fuser -k 7861/tcp 2>/dev/null || true
sleep 2

echo "Starting control server (port 7860, skip-mamba)..."
nohup $VENV -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --skip-mamba \
  --alpha 0.0 \
  --temperature 0.0 \
  --port 7860 \
  --no-qdrant \
  --no-dual-gate \
  > /tmp/control_server.log 2>&1 &
echo "Control PID: $!"

echo "Starting bridge server (port 7861, alpha=0.2)..."
nohup $VENV -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --alpha 0.2 \
  --temperature 0.0 \
  --mamba-device cuda:0 \
  --port 7861 \
  --no-qdrant \
  --no-dual-gate \
  > /tmp/bridge_server.log 2>&1 &
echo "Bridge PID: $!"

echo "Servers starting in background. Check logs at /tmp/*.log"
echo "Wait ~90s for model loading, then run the eval."
