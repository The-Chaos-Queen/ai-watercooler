#!/bin/bash
set -euo pipefail

source ~/venv_linux/bin/activate
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/check.py"
