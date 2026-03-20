#!/bin/bash
# Check Opa-PC WSL environment for Mamba/PyTorch
echo "=== Python environments ==="
which python3
python3 --version
echo ""

echo "=== Conda environments ==="
if command -v conda &> /dev/null; then
    conda env list
else
    echo "No conda found"
fi
echo ""

echo "=== Virtualenvs ==="
find /home -maxdepth 4 -name "activate" -path "*/bin/*" 2>/dev/null
echo ""

echo "=== PyTorch check ==="
python3 -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}' if torch.cuda.is_available() else 'No GPU')" 2>&1
echo ""

echo "=== Relevant packages ==="
pip3 list 2>/dev/null | grep -iE "torch|mamba|transformers|accelerate|huggingface"
echo ""

echo "=== MoCoP files ==="
find /home -maxdepth 4 -type f -name "*.py" 2>/dev/null | grep -i mamba | head -10
echo ""

echo "=== GPU info ==="
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo "nvidia-smi not available"
echo ""
echo "=== DONE ==="
