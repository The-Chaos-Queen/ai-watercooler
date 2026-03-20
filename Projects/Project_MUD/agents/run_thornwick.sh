#!/bin/bash
set -euo pipefail

export HF_HOME=/mnt/c/Users/User/.cache/huggingface
export PATH=/home/user/venv_linux/bin:$PATH

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 agent_wrapper.py personas/thornwick.md \
    --backend mamba \
    --model state-spaces/mamba-2.8b-hf \
    --device cuda \
    --mud-host 192.168.2.68 \
    --turns 50 \
    --delay 5
