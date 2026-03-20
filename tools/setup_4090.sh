#!/bin/bash
# One-shot setup for Steve's 4090 — run inside WSL after reboot
# Usage: bash setup_4090.sh
set -euo pipefail

echo "=== Setting up 4090 for MoCoP ==="

# Update system
echo "[1/6] Updating system..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv curl git

# Create venv
echo "[2/6] Creating Python venv..."
python3 -m venv ~/mocop_venv
source ~/mocop_venv/bin/activate

# Install PyTorch with CUDA
echo "[3/6] Installing PyTorch + CUDA..."
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Install ML stack
echo "[4/6] Installing transformers + accelerate + bitsandbytes..."
pip install transformers accelerate bitsandbytes

# Verify CUDA
echo "[5/6] Verifying CUDA..."
python3 -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    free, total = torch.cuda.mem_get_info(0)
    print(f'VRAM: {free/1e9:.1f} GB free / {total/1e9:.1f} GB total')
else:
    echo 'WARNING: CUDA not available. Check nvidia-smi in WSL.'
"

# Set up HF token
echo "[6/6] Setting up HuggingFace token..."
if [ -n "${HF_TOKEN:-}" ]; then
    mkdir -p ~/.cache/huggingface
    echo "$HF_TOKEN" > ~/.cache/huggingface/token
    echo "HF token saved."
else
    echo "NOTE: Set HF_TOKEN env var and rerun, or:"
    echo "  echo 'your_token' > ~/.cache/huggingface/token"
fi

echo ""
echo "=== Setup complete ==="
echo "Activate with: source ~/mocop_venv/bin/activate"
echo "Test with: python3 -c \"import torch; print(torch.cuda.get_device_name(0))\""
