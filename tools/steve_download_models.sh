#!/bin/bash
source ~/mocop_venv/bin/activate
echo "=== Downloading models for MoCoP ==="

echo "[1/2] Downloading Mamba 2.8B..."
python3 -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
print('Downloading Mamba tokenizer...')
AutoTokenizer.from_pretrained('state-spaces/mamba-2.8b-hf')
print('Downloading Mamba model...')
AutoModelForCausalLM.from_pretrained('state-spaces/mamba-2.8b-hf')
print('Mamba done.')
"

echo "[2/2] Downloading Qwen 2.5-7B..."
python3 -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
print('Downloading Qwen tokenizer...')
AutoTokenizer.from_pretrained('Qwen/Qwen2.5-7B')
print('Downloading Qwen model...')
AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-7B', torch_dtype=torch.float16)
print('Qwen done.')
"

echo "=== All models cached ==="
ls -lh ~/.cache/huggingface/hub/ | grep models
