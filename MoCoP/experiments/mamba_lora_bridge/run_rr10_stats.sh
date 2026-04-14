#!/bin/bash
# Statistical eval: rr_10 probe x 10 runs per condition x 4 checkpoints
cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3

echo "=== rr_10 Statistical Eval ==="
echo "10 runs per condition, 4 checkpoints"

# Checkpoints to test
CKPTS=(
  "cheese_reincarnation_bridge_1.5b_codexfix.pt"
  "kimi_roleplay_bridge_1.5b_2026-04-03.pt"
  "mvp2b_easyfirst_composite_1p5b_20260413.pt"
)

fuser -k 7860/tcp 2>/dev/null || true
fuser -k 7861/tcp 2>/dev/null || true
sleep 2

for CKPT in "${CKPTS[@]}"; do
  echo ""
  echo "========================================"
  echo "Checkpoint: $CKPT"
  echo "========================================"

  # Determine output filename
  CKPT_SHORT=$(basename "$CKPT" .pt)
  OUTFILE="behavioral_eval_runs/rr10_stats_${CKPT_SHORT}_20260414.json"

  # Kill any lingering servers
  fuser -k 7860/tcp 2>/dev/null || true
  fuser -k 7861/tcp 2>/dev/null || true
  sleep 2

  echo "Starting control server..."
  $VENV -X utf8 chat_server.py \
    --bridge-path "$CKPT" \
    --skip-mamba \
    --alpha 0.0 \
    --temperature 0.0 \
    --port 7860 \
    --qdrant-enabled \
    --no-dual-gate > /tmp/ctrl_stats.log 2>&1 &
  PID1=$!

  echo "Starting bridge server..."
  $VENV -X utf8 chat_server.py \
    --bridge-path "$CKPT" \
    --alpha 0.2 \
    --temperature 0.0 \
    --mamba-device cuda:0 \
    --port 7861 \
    --qdrant-enabled \
    --no-dual-gate > /tmp/bridge_stats.log 2>&1 &
  PID2=$!

  echo "Waiting for servers..."
  for i in $(seq 1 24); do
    sleep 5
    C=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"running": true' || echo 0)
    B=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"running": true' || echo 0)
    if [ "$C" -gt 0 ] && [ "$B" -gt 0 ]; then
      echo "Both ready after $((i*5))s"
      break
    fi
  done

  # Verify both running
  C=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"running": true' || echo 0)
  B=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"running": true' || echo 0)
  if [ "$C" -eq 0 ] || [ "$B" -eq 0 ]; then
    echo "FAILED to start servers for $CKPT"
    echo "Control log:"
    tail -20 /tmp/ctrl_stats.log
    echo "Bridge log:"
    tail -20 /tmp/bridge_stats.log
    kill $PID1 $PID2 2>/dev/null || true
    continue
  fi

  echo "Running 10x rr_10 eval..."
  $VENV -X utf8 run_rr10_statistical_eval.py \
    --control-base-url http://127.0.0.1:7860 \
    --bridge-base-url http://127.0.0.1:7861 \
    --runs 10 \
    --results-json "$OUTFILE"

  echo "Cleanup..."
  kill $PID1 $PID2 2>/dev/null || true
  sleep 2
done

echo ""
echo "=== All checkpoints done ==="
