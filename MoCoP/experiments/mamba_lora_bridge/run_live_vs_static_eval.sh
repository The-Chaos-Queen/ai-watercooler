#!/bin/bash
# Live vs Static accumulation comparison on rr_10
# Tests whether live accumulation (bias updates per turn) differs from static bootstrap

cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3
CKPT="cheese_reincarnation_bridge_1.5b_codexfix.pt"
OUTFILE="behavioral_eval_runs/live_vs_static_rr10_$(date +%Y%m%d_%H%M%S).json"

echo "=== Live vs Static Accumulation: rr_10 Comparison ==="
echo "Checkpoint: $CKPT"

# Kill any lingering servers
fuser -k 7860/tcp 2>/dev/null || true
fuser -k 7861/tcp 2>/dev/null || true
sleep 2

echo "Starting STATIC bootstrap server on port 7860..."
$VENV -X utf8 chat_server.py \
  --bridge-path "$CKPT" \
  --alpha 0.2 \
  --temperature 0.0 \
  --port 7860 \
  --qdrant-enabled \
  --no-dual-gate > /tmp/static.log 2>&1 &
PID1=$!

echo "Starting LIVE accumulation server on port 7861..."
$VENV -X utf8 chat_server.py \
  --bridge-path "$CKPT" \
  --alpha 0.2 \
  --temperature 0.0 \
  --port 7861 \
  --qdrant-enabled \
  --no-dual-gate \
  --live-accumulation > /tmp/live.log 2>&1 &
PID2=$!

echo "Waiting for servers (up to 2 min)..."
for i in $(seq 1 24); do
  sleep 5
  S=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"bridge_loaded": true' || echo 0)
  L=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"bridge_loaded": true' || echo 0)
  if [ "$S" -gt 0 ] && [ "$L" -gt 0 ]; then
    echo "Both ready after $((i*5))s"
    break
  fi
  echo -n "."
done
echo ""

# Verify both running
S=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"bridge_loaded": true' || echo 0)
L=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"bridge_loaded": true' || echo 0)
if [ "$S" -eq 0 ] || [ "$L" -eq 0 ]; then
  echo "FAILED to start servers"
  echo "Static log:"
  tail -30 /tmp/static.log
  echo ""
  echo "Live log:"
  tail -30 /tmp/live.log
  kill $PID1 $PID2 2>/dev/null || true
  exit 1
fi

# Check live accumulation is actually enabled
LIVE_ACC=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -o '"live_accumulation_enabled": true' || echo "")
if [ -z "$LIVE_ACC" ]; then
  echo "WARNING: Live server does not have live_accumulation_enabled!"
fi

echo ""
echo "Running live vs static comparison..."
$VENV -X utf8 test_live_vs_static_rr10.py \
  --static-url http://127.0.0.1:7860 \
  --live-url http://127.0.0.1:7861 \
  --output "$OUTFILE"

echo ""
echo "Cleanup..."
kill $PID1 $PID2 2>/dev/null || true
sleep 2

echo "Done. Results saved to $OUTFILE"
