#!/bin/bash
nohup bash /mnt/c/Users/User/opa_pca_run.sh > /dev/null 2>&1 &
echo "PID=$!"
sleep 2
ps aux | grep train_bridge | grep -v grep || echo "checking log..."
head -3 /mnt/c/Users/User/mamba_lora_bridge/pca_run.log 2>/dev/null || echo "no log yet"
