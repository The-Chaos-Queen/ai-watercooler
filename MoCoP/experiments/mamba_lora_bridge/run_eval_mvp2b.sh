#!/bin/bash
# Memory-conditioned 2x2 eval with MVP-2b composite
cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3
CKPT=mvp2b_easyfirst_composite_1p5b_20260413.pt

echo "=== MVP-2b Composite Loss - Refined Endocrine Test ==="
echo "Checkpoint: $CKPT"
echo "Mode: token_conditioned_input_adapter"

fuser -k 7860/tcp 2>/dev/null || true
fuser -k 7861/tcp 2>/dev/null || true
sleep 2

echo ""
echo "Starting control server..."
$VENV -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --skip-mamba \
  --alpha 0.0 \
  --temperature 0.0 \
  --port 7860 \
  --qdrant-enabled \
  --no-dual-gate > /tmp/ctrl_mvp2b.log 2>&1 &
PID1=$!
echo "Control PID=$PID1"

echo ""
echo "Starting bridge server..."
$VENV -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --alpha 0.2 \
  --temperature 0.0 \
  --mamba-device cuda:0 \
  --port 7861 \
  --qdrant-enabled \
  --no-dual-gate > /tmp/bridge_mvp2b.log 2>&1 &
PID2=$!
echo "Bridge PID=$PID2"

echo ""
echo "Waiting for servers (checking every 5s, max 100s)..."
for i in $(seq 1 20); do
  sleep 5
  C=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"running": true' || echo 0)
  B=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"running": true' || echo 0)
  echo "Check $i: control=$C bridge=$B"
  if [ "$C" -gt 0 ] && [ "$B" -gt 0 ]; then
    echo "Both servers ready!"
    break
  fi
done

# Check if both are ready
C=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"running": true' || echo 0)
B=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"running": true' || echo 0)
if [ "$C" -eq 0 ] || [ "$B" -eq 0 ]; then
  echo "=== STARTUP FAILED ==="
  echo "Control log tail:"
  tail -30 /tmp/ctrl_mvp2b.log
  echo ""
  echo "Bridge log tail:"
  tail -30 /tmp/bridge_mvp2b.log
  kill $PID1 $PID2 2>/dev/null || true
  exit 1
fi

echo ""
echo "=== Running 2x2 Memory-Conditioned Eval ==="
$VENV -X utf8 run_memory_conditioned_eval_matrix.py \
  --control-base-url http://127.0.0.1:7860 \
  --bridge-base-url http://127.0.0.1:7861 \
  --panel-file mvp2b_easyfirst_composite_panel_2026-04-13.json \
  --query-map-file memory_conditioned_eval_queries_2026-04-14.json \
  --results-json behavioral_eval_runs/memory_conditioned_2x2_mvp2b_composite_20260414.json

echo ""
echo "=== Cleanup ==="
kill $PID1 $PID2 2>/dev/null || true
echo "Done!"
