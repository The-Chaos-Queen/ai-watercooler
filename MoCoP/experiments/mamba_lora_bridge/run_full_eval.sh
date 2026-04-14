#!/bin/bash
set -e

cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3
CKPT=kimi_roleplay_bridge_1.5b_2026-04-03.pt

# Kill any existing listeners
fuser -k 7860/tcp 2>/dev/null || true
fuser -k 7861/tcp 2>/dev/null || true
sleep 2

echo "=== Starting control server (port 7860, skip-mamba) ==="
$VENV -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --skip-mamba \
  --alpha 0.0 \
  --temperature 0.0 \
  --port 7860 \
  --qdrant-enabled \
  --no-dual-gate &
CONTROL_PID=$!

echo "=== Starting bridge server (port 7861, alpha=0.2) ==="
$VENV -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --alpha 0.2 \
  --temperature 0.0 \
  --mamba-device cuda:0 \
  --port 7861 \
  --qdrant-enabled \
  --no-dual-gate &
BRIDGE_PID=$!

# Function to cleanup on exit
cleanup() {
  echo "Cleaning up..."
  kill $CONTROL_PID 2>/dev/null || true
  kill $BRIDGE_PID 2>/dev/null || true
}
trap cleanup EXIT

echo "=== Waiting for servers (control ~30s, bridge ~90s) ==="
for i in {1..120}; do
  sleep 1
  C_OK=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"running": true' || echo 0)
  B_OK=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"running": true' || echo 0)
  if [ "$C_OK" -gt 0 ] && [ "$B_OK" -gt 0 ]; then
    echo "Both servers ready after ${i}s"
    break
  fi
  if [ $((i % 10)) -eq 0 ]; then
    echo "Waiting... ${i}s (control=$C_OK, bridge=$B_OK)"
  fi
done

# Final health check
echo ""
echo "=== Server status ==="
curl -s http://127.0.0.1:7860/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Control: running={d.get(\"running\")}, disposition={d.get(\"disposition\")}, alpha={d.get(\"alpha\")}')" || echo "Control: NOT RESPONDING"
curl -s http://127.0.0.1:7861/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Bridge: running={d.get(\"running\")}, disposition={d.get(\"disposition\")}, alpha={d.get(\"alpha\")}')" || echo "Bridge: NOT RESPONDING"
echo ""

echo "=== Running memory-conditioned eval matrix ==="
$VENV -X utf8 run_memory_conditioned_eval_matrix.py \
  --control-base-url http://127.0.0.1:7860 \
  --bridge-base-url http://127.0.0.1:7861 \
  --panel-file mvp2b_easyfirst_composite_panel_2026-04-13.json \
  --query-map-file memory_conditioned_eval_queries_2026-04-14.json \
  --results-json behavioral_eval_runs/memory_conditioned_2x2_kimi_20260414.json

echo ""
echo "=== DONE ==="
