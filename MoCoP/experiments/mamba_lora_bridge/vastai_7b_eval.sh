#!/bin/bash
# Vast.ai 7B rr_10 eval — run on A40/A100 instance
set -euo pipefail

echo "=== 7B rr_10 Eval Bootstrap ==="

# Bootstrap
echo "Installing dependencies..."
pip install --upgrade --index-url https://download.pytorch.org/whl/cu121 "torch==2.5.1+cu121"
pip install --upgrade mamba-ssm causal-conv1d accelerate sentence-transformers transformers

# Verify
python3 - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
if not torch.cuda.is_available():
    raise SystemExit("CUDA not available!")
import mamba_ssm, causal_conv1d
print("mamba_fast_path ok")
PY

cd /workspace/bridge

CKPT=cheese_reincarnation_bridge_7b.pt

echo ""
echo "=== Starting servers ==="

# Control server (Qwen-7B only, no Mamba)
python3 -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --skip-mamba \
  --alpha 0.0 \
  --temperature 0.0 \
  --port 7860 \
  --no-qdrant \
  --no-dual-gate > /tmp/ctrl_7b.log 2>&1 &
PID1=$!
echo "Control PID=$PID1"

# Bridge server (Qwen-7B + Mamba)
python3 -X utf8 chat_server.py \
  --bridge-path $CKPT \
  --alpha 0.2 \
  --temperature 0.0 \
  --mamba-device cuda:0 \
  --port 7861 \
  --no-qdrant \
  --no-dual-gate > /tmp/bridge_7b.log 2>&1 &
PID2=$!
echo "Bridge PID=$PID2"

echo "Waiting for servers..."
for i in $(seq 1 60); do
  sleep 5
  C=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"running": true' || echo 0)
  B=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"running": true' || echo 0)
  echo "Check $i: control=$C bridge=$B"
  if [ "$C" -gt 0 ] && [ "$B" -gt 0 ]; then
    echo "Both servers ready!"
    break
  fi
done

# Verify
C=$(curl -s http://127.0.0.1:7860/status 2>/dev/null | grep -c '"running": true' || echo 0)
B=$(curl -s http://127.0.0.1:7861/status 2>/dev/null | grep -c '"running": true' || echo 0)
if [ "$C" -eq 0 ] || [ "$B" -eq 0 ]; then
  echo "=== STARTUP FAILED ==="
  echo "Control log:"
  tail -50 /tmp/ctrl_7b.log
  echo ""
  echo "Bridge log:"
  tail -50 /tmp/bridge_7b.log
  kill $PID1 $PID2 2>/dev/null || true
  exit 1
fi

echo ""
echo "=== Running N=10 rr_10 eval ==="
python3 -X utf8 run_rr10_7b_vastai.py \
  --control-base-url http://127.0.0.1:7860 \
  --bridge-base-url http://127.0.0.1:7861 \
  --runs 10 \
  --results-json rr10_stats_7b_20260414.json

echo ""
echo "=== Results ==="
cat rr10_stats_7b_20260414.json

echo ""
echo "=== Cleanup ==="
kill $PID1 $PID2 2>/dev/null || true
echo "Done! Copy rr10_stats_7b_20260414.json before terminating instance."
