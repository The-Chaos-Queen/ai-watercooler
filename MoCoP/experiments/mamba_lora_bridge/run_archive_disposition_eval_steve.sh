#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/Users/tikii/bridge

PANEL_FILE="relational_rivalry_eval_panel_v2_2026-04-11.json"
EPISODES_FILE="ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md"
BRIDGE_PATH="cheese_reincarnation_bridge_1.5b_codexfix.pt"
QWEN_MODEL="Qwen/Qwen2.5-1.5B-Instruct"
MAMBA_MODEL="state-spaces/mamba-2.8b-hf"
ALPHA="0.2"
MAX_NEW_TOKENS="200"
PROMPT_FORMAT="auto"

declare -a EPISODES=(
  "2:continuity_grief"
  "3:resonance_acceptance"
  "4:secure_closeness"
)

for item in "${EPISODES[@]}"; do
  IFS=":" read -r episode_index episode_slug <<<"$item"
  results_json="run_reincarnation/archive_eval_${episode_slug}_20260411_a0p2_t200.json"

  echo "=== Running episode ${episode_index} (${episode_slug}) ==="
  /root/mocop_venv/bin/python3 -X utf8 run_relational_eval_offline.py \
    --panel-file "$PANEL_FILE" \
    --episodes-file "$EPISODES_FILE" \
    --episode-index "$episode_index" \
    --results-json "$results_json" \
    --bridge-path "$BRIDGE_PATH" \
    --model "$QWEN_MODEL" \
    --mamba-model-id "$MAMBA_MODEL" \
    --qwen-device cuda:0 \
    --mamba-device cuda:0 \
    --bridge-device cuda:0 \
    --alpha "$ALPHA" \
    --max-new-tokens "$MAX_NEW_TOKENS" \
    --temperature 0.0 \
    --greedy \
    --prompt-format "$PROMPT_FORMAT"

  echo "Saved to $results_json"
  echo
done
