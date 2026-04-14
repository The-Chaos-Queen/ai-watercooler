#!/bin/bash
# Start eval servers in a persistent tmux session

cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3
CKPT=cheese_reincarnation_bridge_1.5b_codexfix.pt

# Kill existing tmux session if any
tmux kill-session -t eval 2>/dev/null || true

# Kill any existing listeners
fuser -k 7860/tcp 2>/dev/null || true
fuser -k 7861/tcp 2>/dev/null || true
sleep 1

# Create new tmux session with control server
tmux new-session -d -s eval -n control \
  "$VENV -X utf8 chat_server.py --bridge-path $CKPT --skip-mamba --alpha 0.0 --temperature 0.0 --port 7860 --no-qdrant --no-dual-gate"

# Create second window for bridge server
tmux new-window -t eval -n bridge \
  "$VENV -X utf8 chat_server.py --bridge-path $CKPT --alpha 0.2 --temperature 0.0 --mamba-device cuda:0 --port 7861 --no-qdrant --no-dual-gate"

echo "tmux session 'eval' started with two windows: control (7860) and bridge (7861)"
echo "Attach with: tmux attach -t eval"
echo "List sessions: tmux ls"
