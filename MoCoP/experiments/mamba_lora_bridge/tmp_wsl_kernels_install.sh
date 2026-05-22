set -euo pipefail
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export CUDACXX="$CUDA_HOME/bin/nvcc"
export MAX_JOBS=4
source /root/mamba_venv/bin/activate
nvcc --version | sed -n '1,4p'
python -m pip install --no-build-isolation --no-cache-dir causal-conv1d
export MAMBA_FORCE_BUILD=TRUE
python -m pip install --no-cache-dir --force-reinstall git+https://github.com/state-spaces/mamba.git --no-build-isolation
