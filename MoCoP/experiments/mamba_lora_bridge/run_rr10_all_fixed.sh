#!/bin/bash
# Statistical eval with correct prompt for all checkpoints
cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3

echo "=== rr_10 Statistical Eval (Fixed Prompt) ==="

CKPTS=(
  "kimi_roleplay_bridge_1.5b_2026-04-03.pt"
  "mvp2b_easyfirst_composite_1p5b_20260413.pt"
)

for CKPT in "${CKPTS[@]}"; do
  echo ""
  echo "========================================"
  echo "Checkpoint: $CKPT"
  echo "========================================"

  CKPT_SHORT=$(basename "$CKPT" .pt)
  OUTFILE="behavioral_eval_runs/rr10_stats_${CKPT_SHORT}_fixed_20260414.json"

  fuser -k 7860/tcp 2>/dev/null || true
  fuser -k 7861/tcp 2>/dev/null || true
  sleep 2

  $VENV -X utf8 chat_server.py --bridge-path "$CKPT" --skip-mamba --alpha 0.0 --temperature 0.0 --port 7860 --qdrant-enabled --no-dual-gate > /tmp/ctrl.log 2>&1 &
  PID1=$!

  $VENV -X utf8 chat_server.py --bridge-path "$CKPT" --alpha 0.2 --temperature 0.0 --mamba-device cuda:0 --port 7861 --qdrant-enabled --no-dual-gate > /tmp/bridge.log 2>&1 &
  PID2=$!

  for i in $(seq 1 24); do
    sleep 5
    C=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"running": true' || echo 0)
    B=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"running": true' || echo 0)
    if [ "$C" -gt 0 ] && [ "$B" -gt 0 ]; then
      echo "Ready"
      break
    fi
  done

  $VENV -X utf8 run_rr10_statistical_eval.py \
    --control-base-url http://127.0.0.1:7860 \
    --bridge-base-url http://127.0.0.1:7861 \
    --runs 10 \
    --results-json "$OUTFILE"

  kill $PID1 $PID2 2>/dev/null || true
  sleep 2
done

echo ""
echo "=== All done ==="
