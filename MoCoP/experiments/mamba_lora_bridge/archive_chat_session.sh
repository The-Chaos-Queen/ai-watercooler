#!/bin/bash
set -euo pipefail

BRIDGE_DIR="/mnt/c/Users/tikii/bridge"
LATEST_LOG="${BRIDGE_DIR}/chat_session_latest.txt"
ARCHIVE_DIR="${BRIDGE_DIR}/chat_sessions"

mkdir -p "${ARCHIVE_DIR}"

if [[ -s "${LATEST_LOG}" ]]; then
  timestamp="$(date +%Y-%m-%dT%H%M%S)"
  cp "${LATEST_LOG}" "${ARCHIVE_DIR}/chat_session_${timestamp}.txt"
fi
