#!/bin/bash
source ~/mocop_venv/bin/activate
echo "=== HF Cache ==="
du -sh ~/.cache/huggingface/hub/models--* 2>/dev/null || echo "no models cached"
echo "=== Quick model test ==="
python3 -c "
from transformers import AutoTokenizer
try:
    t = AutoTokenizer.from_pretrained('state-spaces/mamba-2.8b-hf')
    print('Mamba tokenizer: OK')
except: print('Mamba: NOT CACHED')
try:
    t = AutoTokenizer.from_pretrained('Qwen/Qwen2.5-7B')
    print('Qwen tokenizer: OK')
except: print('Qwen: NOT CACHED')
"
