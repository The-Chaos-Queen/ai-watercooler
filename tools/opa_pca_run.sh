#!/bin/bash
source /home/user/venv_linux/bin/activate
cd /mnt/c/Users/User/mamba_lora_bridge
mkdir -p pca_run

python3 -X utf8 train_bridge.py \
  --qwen-model-id Qwen/Qwen2.5-0.5B \
  --qwen-prompt-format completion \
  --epochs 1 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 16 \
  --eval-samples 8 \
  --tiny-overfit \
  --tiny-overfit-samples 16 \
  --general-eval-samples 4 \
  --mamba-context-tokens 2048 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --target-layers "4:q_proj,4:v_proj,5:q_proj,5:v_proj,6:q_proj,6:v_proj,7:q_proj,7:v_proj" \
  --save-train-contexts \
  --save-eval-contexts \
  --save-eval-predictions \
  --eval-prediction-samples 8 \
  --output-dir pca_run \
  >> pca_run.log 2>&1

echo "EXIT=$?" >> pca_run.log
ls -lh pca_run/ >> pca_run.log 2>&1
