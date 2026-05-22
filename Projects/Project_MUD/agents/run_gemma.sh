#!/bin/bash
set -euo pipefail

export PATH=/home/user/venv_linux/bin:$PATH

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 agent_wrapper.py personas/gemma.md \
    --backend ollama \
    --model gemma4:4b \
    --mud-host 127.0.0.1 \
    --turns 50 \
    --delay 3
