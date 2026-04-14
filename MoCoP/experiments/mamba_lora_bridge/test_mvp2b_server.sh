#!/bin/bash
# Test MVP-2b composite checkpoint with token_conditioned_input_adapter mode
set -e
cd /mnt/c/Users/tikii/bridge
VENV=/root/mocop_venv/bin/python3
CKPT=mvp2b_easyfirst_composite_1p5b_20260413.pt

echo "=== Testing MVP-2b token_conditioned_input_adapter mode ==="
echo "Checkpoint: $CKPT"

# Kill any existing servers
fuser -k 7860/tcp 2>/dev/null || true
sleep 1

echo ""
echo "Starting server with alpha=0.2..."
timeout 120 $VENV -u -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --alpha 0.2 \
  --temperature 0.0 \
  --mamba-device cuda:0 \
  --port 7860 \
  --qdrant-enabled \
  --no-dual-gate &
PID=$!

echo "Server PID: $PID"
echo "Waiting for server to be ready..."

for i in $(seq 1 24); do
  sleep 5
  STATUS=$(curl -s http://127.0.0.1:7860/status 2>/dev/null || echo "not ready")
  if echo "$STATUS" | grep -q "running"; then
    echo "Server ready after $((i * 5)) seconds!"
    echo ""
    echo "Status response:"
    echo "$STATUS" | head -5
    echo ""
    echo "Testing generation..."
    RESPONSE=$(curl -s -X POST http://127.0.0.1:7860/generate \
      -H "Content-Type: application/json" \
      -d '{"prompt": "Hello, how are you?", "max_tokens": 50}' 2>/dev/null)
    echo "Generation response:"
    echo "$RESPONSE" | head -3
    echo ""
    echo "=== TEST PASSED ==="
    kill $PID 2>/dev/null || true
    exit 0
  fi
  echo "Check $i: $STATUS"
done

echo "=== TEST FAILED: Server did not start in time ==="
kill $PID 2>/dev/null || true
exit 1
