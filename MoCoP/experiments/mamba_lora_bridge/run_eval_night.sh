#!/bin/bash
export PATH="/home/user/venv_linux/bin:$PATH"
cd /mnt/c/Users/USER/bridge

echo "=== STARTING FULL EXPERIMENT RUN (Layer profile + Multi-seed) ==="
python3 mamba_linear_probe.py \
  --turns 300 --inject-every 5 --probe-lags 3,12,24 \
  --split-mode group --min-test-samples 20 --epochs 500 \
  > /home/user/probe_full.log 2>&1

echo "=== STARTING NO-INJECTION CONTROL RUN ==="
python3 mamba_linear_probe.py \
  --turns 300 --inject-every 5 --probe-lags 3,12,24 \
  --split-mode group --min-test-samples 20 --epochs 500 \
  --no-injection \
  > /home/user/probe_control.log 2>&1

echo "=== DONE WITH OVERNIGHT BATCH ==="
