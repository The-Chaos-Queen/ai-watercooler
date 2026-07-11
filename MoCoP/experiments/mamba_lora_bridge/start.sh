#!/usr/bin/env bash
# Canonical ML-WS chat launcher. Qdrant writes are opt-in and credential-gated.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${MOCOP_CHAT_PYTHON:-$HOME/miniforge3/envs/torch311/bin/python}"

COMMON_ARGS=(
    --model Qwen/Qwen2.5-1.5B
    --bridge-path cheese_reincarnation_bridge_1.5b_codexfix.pt
    --episodes-file CHEESE_SHAPING_EPISODES.md
    --episode-index 2
    --instance-id lobby
    --no-shared-memory
    --no-ambient-recall
    --memory-integration-mode both
    --memory-state-max-tokens 768
    --live-accumulation
    --qwen-device cuda:0
    --mamba-device cuda:0
    --user-label You
    --model-label I
    --alpha 0.2
    --temperature 0.2
    --max-new-tokens 120
    --host 0.0.0.0
    --port 7860
)

RUNTIME_ENV=(
    HF_HOME="$HOME/ml/hf_cache"
    HF_HUB_CACHE="$HOME/ml/hf_cache/hub"
    HF_HUB_OFFLINE=1
    TRANSFORMERS_OFFLINE=1
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
)

if [[ "${MOCOP_ENABLE_QDRANT_WRITES:-0}" == "1" ]]; then
    echo "[mocop] Qdrant writer mode explicitly enabled; loading private writer environment."
    exec env "${RUNTIME_ENV[@]}" \
        "$SCRIPT_DIR/with_qdrant_writer_env.sh" \
        "$PYTHON_BIN" -u "$SCRIPT_DIR/chat_server.py" \
        "${COMMON_ARGS[@]}" "$@" --qdrant-enabled
fi

echo "[mocop] Qdrant is disabled by default. Set MOCOP_ENABLE_QDRANT_WRITES=1 only after the reviewed writer gate is intended."
exec env "${RUNTIME_ENV[@]}" \
    "$PYTHON_BIN" -u "$SCRIPT_DIR/chat_server.py" \
    "${COMMON_ARGS[@]}" "$@" --no-qdrant
