#!/bin/bash
set -e

cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3
CKPT=mvp2b_easyfirst_composite_1p5b_20260413.pt

echo "=== Starting control server (port 7860, skip-mamba) ==="
$VENV -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --skip-mamba \
  --alpha 0.0 \
  --temperature 0.0 \
  --port 7860 \
  --no-qdrant \
  --no-dual-gate \
  > /tmp/control_server.log 2>&1 &
CONTROL_PID=$!
echo "Control server PID: $CONTROL_PID"

echo "=== Starting bridge server (port 7861, alpha=0.2) ==="
$VENV -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --alpha 0.2 \
  --temperature 0.0 \
  --mamba-device cuda:0 \
  --port 7861 \
  --no-qdrant \
  --no-dual-gate \
  > /tmp/bridge_server.log 2>&1 &
BRIDGE_PID=$!
echo "Bridge server PID: $BRIDGE_PID"

echo "=== Waiting for servers to start (60s for model loading) ==="
sleep 60

echo "=== Checking server health ==="
curl -s http://127.0.0.1:7860/status | head -c 200 || echo "Control server not responding"
echo ""
curl -s http://127.0.0.1:7861/status | head -c 200 || echo "Bridge server not responding"
echo ""

echo "=== Running memory-conditioned eval matrix ==="
$VENV -X utf8 run_memory_conditioned_eval_matrix.py \
  --control-base-url http://127.0.0.1:7860 \
  --bridge-base-url http://127.0.0.1:7861 \
  --panel-file mvp2b_easyfirst_composite_panel_2026-04-13.json \
  --query-map-file memory_conditioned_eval_queries_2026-04-14.json \
  --results-json behavioral_eval_runs/memory_conditioned_2x2_20260414.json

echo "=== Stopping servers ==="
kill $CONTROL_PID 2>/dev/null || true
kill $BRIDGE_PID 2>/dev/null || true

echo "=== Done ==="
