#!/bin/bash
echo "=== Process ==="
ps aux | grep -E "pip|python|setup" | grep -v grep || echo "nothing running"
echo "=== Venv ==="
ls ~/mocop_venv/bin/python3 2>/dev/null && echo "venv exists" || echo "no venv yet"
echo "=== PyTorch ==="
source ~/mocop_venv/bin/activate 2>/dev/null && python3 -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}')" 2>/dev/null || echo "not installed yet"
