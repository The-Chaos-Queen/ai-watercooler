#!/bin/bash
source /home/user/venv_linux/bin/activate
echo "=== Venv Python ==="
which python3
python3 --version
echo ""
echo "=== PyTorch ==="
python3 -c "import torch; print('PyTorch', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
echo ""
echo "=== Relevant packages ==="
pip list | grep -iE "torch|mamba|transformers|accelerate|huggingface"
echo ""
echo "=== HF cache ==="
ls ~/.cache/huggingface/hub/ 2>/dev/null | head -10
echo "=== DONE ==="
