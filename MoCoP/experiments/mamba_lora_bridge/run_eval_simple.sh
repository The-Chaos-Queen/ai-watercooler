#!/bin/bash
set -x
cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3
CKPT=cheese_reincarnation_bridge_1.5b_codexfix.pt

fuser -k 7860/tcp 2>/dev/null || true
fuser -k 7861/tcp 2>/dev/null || true
sleep 2

echo "Starting control..."
$VENV -X utf8 chat_server.py --bridge-path $CKPT --skip-mamba --alpha 0.0 --temperature 0.0 --port 7860 --qdrant-enabled --no-dual-gate > /tmp/ctrl.log 2>&1 &
PID1=$!
echo "Control PID=$PID1"

echo "Starting bridge..."
$VENV -X utf8 chat_server.py --bridge-path $CKPT --alpha 0.2 --temperature 0.0 --mamba-device cuda:0 --port 7861 --qdrant-enabled --no-dual-gate > /tmp/bridge.log 2>&1 &
PID2=$!
echo "Bridge PID=$PID2"

echo "Waiting 90s..."
sleep 90

echo "Control log:"
cat /tmp/ctrl.log | tail -20

echo "Bridge log:"
cat /tmp/bridge.log | tail -20

echo "Running eval..."
$VENV -X utf8 run_memory_conditioned_eval_matrix.py \
  --control-base-url http://127.0.0.1:7860 \
  --bridge-base-url http://127.0.0.1:7861 \
  --panel-file mvp2b_easyfirst_composite_panel_2026-04-13.json \
  --query-map-file memory_conditioned_eval_queries_2026-04-14.json \
  --results-json behavioral_eval_runs/memory_conditioned_2x2_codexfix_run2_20260414.json

echo "Cleanup"
kill $PID1 $PID2 2>/dev/null
echo "Done"
