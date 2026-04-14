#!/bin/bash
cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3
CKPT=kimi_roleplay_bridge_1.5b_2026-04-03.pt

fuser -k 7860/tcp 2>/dev/null || true
fuser -k 7861/tcp 2>/dev/null || true
sleep 2

echo "Starting control server..."
$VENV -u -X utf8 chat_server.py --bridge-path $CKPT --skip-mamba --alpha 0.0 --temperature 0.0 --port 7860 --qdrant-enabled --no-dual-gate &
PID1=$!

echo "Starting bridge server..."
$VENV -u -X utf8 chat_server.py --bridge-path $CKPT --alpha 0.2 --temperature 0.0 --mamba-device cuda:0 --port 7861 --qdrant-enabled --no-dual-gate &
PID2=$!

echo "PIDs: control=$PID1 bridge=$PID2"

echo "Waiting for servers (checking every 5s)..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  sleep 5
  C=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c running || echo 0)
  B=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c running || echo 0)
  echo "Check $i: control=$C bridge=$B"
  if [ "$C" -gt 0 ] && [ "$B" -gt 0 ]; then
    echo "Both ready!"
    break
  fi
done

echo "Running eval..."
$VENV -X utf8 run_memory_conditioned_eval_matrix.py \
  --control-base-url http://127.0.0.1:7860 \
  --bridge-base-url http://127.0.0.1:7861 \
  --panel-file mvp2b_easyfirst_composite_panel_2026-04-13.json \
  --query-map-file memory_conditioned_eval_queries_2026-04-14.json \
  --results-json behavioral_eval_runs/memory_conditioned_2x2_kimi.json

echo "Cleanup"
kill $PID1 $PID2 2>/dev/null || true
echo "Done"
