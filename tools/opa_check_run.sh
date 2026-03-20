#!/bin/bash
echo "=== Process ==="
ps aux | grep train_bridge | grep -v grep || echo "not running"
echo "=== Log tail ==="
tail -10 /mnt/c/Users/User/mamba_lora_bridge/pca_run.log 2>/dev/null || echo "no log"
echo "=== Output dir ==="
ls -lh /mnt/c/Users/User/mamba_lora_bridge/pca_run/ 2>/dev/null || echo "no dir"
