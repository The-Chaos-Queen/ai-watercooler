#!/bin/bash
source /home/user/venv_linux/bin/activate
python3 -c "
import torch
free, total = torch.cuda.mem_get_info(0)
print(f'GPU: {torch.cuda.get_device_name(0)}')
print(f'Free: {free/1e9:.1f} GB / Total: {total/1e9:.1f} GB')
print(f'Qwen2.5-7B 4-bit needs ~4.5GB + Mamba on CPU + hypernetwork')
print(f'Estimated fit: {\"YES\" if free > 5.0 else \"TIGHT\"}')
"
