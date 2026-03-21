#!/bin/bash
set -euo pipefail

BRIDGE_DIR="/mnt/c/Users/tikii/bridge"
PYTHON_BIN="${CHAT_PYTHON_BIN:-/root/mocop_venv/bin/python3}"
CHAT_TEMPERATURE="${CHAT_TEMPERATURE:-0.7}"
CHAT_MAX_NEW_TOKENS="${CHAT_MAX_NEW_TOKENS:-200}"

mkdir -p "${BRIDGE_DIR}/logs" "${BRIDGE_DIR}/chat_sessions"
cd "${BRIDGE_DIR}"
exec >> "${BRIDGE_DIR}/logs/steve_chat_server.log" 2>&1

echo "[$(date +%Y-%m-%dT%H:%M:%S%z)] starting mocop-chat"

exec "${PYTHON_BIN}" -X utf8 chat_server.py \
  --temperature "${CHAT_TEMPERATURE}" \
  --max-new-tokens "${CHAT_MAX_NEW_TOKENS}"
