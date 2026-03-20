#!/bin/bash
source /home/user/venv_linux/bin/activate
python3 -c "
from transformers import AutoConfig
c = AutoConfig.from_pretrained('Qwen/Qwen2.5-0.5B')
print(f'Qwen2.5-0.5B layers: {c.num_hidden_layers}')
"
