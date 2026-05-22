set -euo pipefail
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
source /root/mamba_venv/bin/activate
python -V
python -m pip --version
python -m pip install --upgrade pip setuptools wheel packaging ninja cmake
python -m pip install --index-url https://download.pytorch.org/whl/cu126 torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0
python -m pip install transformers accelerate huggingface_hub einops safetensors sentencepiece bitsandbytes
python -m pip install --no-build-isolation --no-cache-dir causal-conv1d
export MAMBA_FORCE_BUILD=TRUE
python -m pip install --no-cache-dir --force-reinstall git+https://github.com/state-spaces/mamba.git --no-build-isolation
