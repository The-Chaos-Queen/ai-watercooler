set -euo pipefail

cd /mnt/c/Users/tikii/bridge

echo "== Steve mvp8 prompt-trace contrastive run =="
pwd
ls -lh train_cheese_bridge.py prompt_suffix_trace_dataset_step6.pt

/root/mocop_venv/bin/python3 -m py_compile train_cheese_bridge.py

/root/mocop_venv/bin/python3 -X utf8 train_cheese_bridge.py \
  --qwen-model-id Qwen/Qwen2.5-1.5B \
  --skip-compressor \
  --mamba-state-cache-dir mvp0_hidden_cache_smoke \
  --require-cached-mamba-states \
  --token-conditioned-input-adapter \
  --prompt-trace-dataset prompt_suffix_trace_dataset_step6.pt \
  --adapter-rank 8 \
  --epochs 120 \
  --output-name mvp8_prompt_trace_episode_contrastive_1p5b.pt \
  --legacy-output-name mvp8_prompt_trace_episode_contrastive_legacy.pt \
  --episode-separation-loss-weight 0.0 \
  --episode-contrastive-loss-weight 5.0 \
  --episode-contrastive-dim 128 \
  --episode-contrastive-temp 0.1 \
  2>&1 | tee mvp8_prompt_trace_episode_contrastive_train.log
