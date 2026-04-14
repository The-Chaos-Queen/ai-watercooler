set -euo pipefail

cd /mnt/c/Users/tikii/bridge
mkdir -p logs

/root/mocop_venv/bin/python3 -m py_compile train_cheese_bridge.py

/root/mocop_venv/bin/python3 -X utf8 train_cheese_bridge.py \
  --episodes-file MVP2B_EASYFIRST_SHAPING_EPISODES_2026-04-13.md \
  --qwen-model-id Qwen/Qwen2.5-1.5B \
  --skip-compressor \
  --mamba-state-cache-dir mvp2b_easyfirst_hidden_cache_20260413 \
  --save-mamba-states \
  --token-conditioned-input-adapter \
  --prompt-trace-dataset prompt_suffix_trace_dataset_mvp2b_easyfirst_20260413.pt \
  --adapter-rank 8 \
  --epochs 120 \
  --output-name mvp2b_easyfirst_composite_1p5b_20260413.pt \
  --legacy-output-name mvp2b_easyfirst_composite_legacy_20260413.pt \
  --episode-separation-loss-weight 0.0 \
  --episode-contrastive-loss-weight 5.0 \
  --episode-contrastive-dim 128 \
  --episode-contrastive-temp 0.1 \
  --margin-loss-weight 0.1 \
  --use-mamba-margins \
  --contamination-loss-weight 0.1 \
  --memory-routing-loss-weight 0.1 \
  --log-every 10 \
  2>&1 | tee /mnt/c/Users/tikii/bridge/logs/mvp2b_easyfirst_composite_1p5b_20260413.log
