[CmdletBinding()]
param(
    [string]$Distro = "Debian",

    [string]$WslUser = "root",

    [string]$VenvPath = "/root/mamba_venv",

    [string]$PythonSpec = "3.11",

    [switch]$UseSystemPython,

    [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu126",

    [string]$CudaToolkitPackage = "cuda-toolkit-12-6",

    [switch]$SkipCudaToolkitInstall,

    [switch]$SkipAptBootstrap,

    [switch]$RecreateVenv,

    [switch]$SkipPythonPackages,

    [switch]$SkipSourceMambaInstall,

    [switch]$RequireCompiledKernels
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $scriptDir "local-wsl.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing local runner: $runner"
}

$useSystemPythonValue = if ($UseSystemPython) { "1" } else { "0" }
$skipCudaToolkitInstallValue = if ($SkipCudaToolkitInstall) { "1" } else { "0" }
$skipAptBootstrapValue = if ($SkipAptBootstrap) { "1" } else { "0" }
$recreateVenvValue = if ($RecreateVenv) { "1" } else { "0" }
$compiledRequiredValue = if ($RequireCompiledKernels) { "1" } else { "0" }

$bootstrap = @'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if [ "__SKIP_APT_BOOTSTRAP__" != "1" ]; then
  apt-get update
  apt-get install -y python3 python3-venv python3-pip python3-dev build-essential git curl ca-certificates pkg-config ninja-build cmake
else
  echo "[warn] Skipping apt bootstrap by request."
fi

if [ "__SKIP_CUDA_TOOLKIT_INSTALL__" != "1" ]; then
  if ! command -v nvcc >/dev/null 2>&1; then
    apt-get install -y __CUDA_TOOLKIT_PACKAGE__ || true
  fi
fi

if [ -x /usr/local/cuda/bin/nvcc ]; then
  export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
  export PATH="${CUDA_HOME}/bin:${PATH}"
  export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
  export CUDACXX="${CUDA_HOME}/bin/nvcc"
fi

if [ "__USE_SYSTEM_PYTHON__" = "1" ]; then
  PYTHON_BIN="$(command -v python3)"
else
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
  uv python install "__PYTHON_SPEC__"
  PYTHON_BIN="$(uv python find "__PYTHON_SPEC__")"
fi

echo "python_bin=${PYTHON_BIN}"
"${PYTHON_BIN}" --version
command -v nvcc >/dev/null 2>&1 && nvcc --version | sed -n '1,4p' || echo "nvcc: missing"

if [ "__RECREATE_VENV__" = "1" ] && [ -d "__VENV_PATH__" ]; then
  rm -rf "__VENV_PATH__"
fi

"${PYTHON_BIN}" -m venv "__VENV_PATH__"
source "__VENV_PATH__/bin/activate"
python -m pip install --upgrade pip setuptools wheel packaging ninja cmake
'@

if (-not $SkipPythonPackages) {
    $mambaInstallBlock = if ($SkipSourceMambaInstall) {
@'
  python -m pip install --no-build-isolation --no-cache-dir mamba-ssm
'@
    } else {
@'
  export MAMBA_FORCE_BUILD=TRUE
  python -m pip install --no-cache-dir --force-reinstall git+https://github.com/state-spaces/mamba.git --no-build-isolation
'@
    }

    $bootstrap = $bootstrap.TrimEnd() + "`n"
    $bootstrap += @'
python -m pip install torch torchvision torchaudio --index-url __TORCH_INDEX_URL__
python -m pip install transformers accelerate huggingface_hub einops safetensors sentencepiece bitsandbytes
if command -v nvcc >/dev/null 2>&1; then
  export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
  export PATH="${CUDA_HOME}/bin:${PATH}"
  export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
  export CUDACXX="${CUDA_HOME}/bin/nvcc"
  export MAX_JOBS="${MAX_JOBS:-4}"
  python -m pip install --no-build-isolation --no-cache-dir causal-conv1d
__MAMBA_INSTALL_BLOCK__
else
  echo "[warn] nvcc not found inside WSL; skipping compiled mamba-ssm / causal-conv1d install."
  if [ "__COMPILED_REQUIRED__" = "1" ]; then
    exit 1
  fi
fi
'@
    $bootstrap = $bootstrap.Replace("__MAMBA_INSTALL_BLOCK__", $mambaInstallBlock.TrimEnd())
}

$bootstrap = $bootstrap.TrimEnd() + "`n"
$bootstrap += @'
echo "--- final toolchain ---"
command -v nvcc >/dev/null 2>&1 && echo "nvcc: $(command -v nvcc)" || echo "nvcc: missing"
python - <<'PY'
import sys
try:
    import torch
    print("python", sys.version.split()[0])
    print("torch", torch.__version__)
    print("torch_cuda_build", torch.version.cuda)
    print("cuda_available", torch.cuda.is_available())
except Exception as exc:
    print("torch_check_failed", repr(exc))
PY
python -m pip show torch transformers bitsandbytes mamba-ssm causal-conv1d 2>/dev/null | sed -n '1,220p' || true
'@

$bootstrap = $bootstrap.Replace("__VENV_PATH__", $VenvPath)
$bootstrap = $bootstrap.Replace("__PYTHON_SPEC__", $PythonSpec)
$bootstrap = $bootstrap.Replace("__USE_SYSTEM_PYTHON__", $useSystemPythonValue)
$bootstrap = $bootstrap.Replace("__SKIP_APT_BOOTSTRAP__", $skipAptBootstrapValue)
$bootstrap = $bootstrap.Replace("__SKIP_CUDA_TOOLKIT_INSTALL__", $skipCudaToolkitInstallValue)
$bootstrap = $bootstrap.Replace("__CUDA_TOOLKIT_PACKAGE__", $CudaToolkitPackage)
$bootstrap = $bootstrap.Replace("__RECREATE_VENV__", $recreateVenvValue)
$bootstrap = $bootstrap.Replace("__TORCH_INDEX_URL__", $TorchIndexUrl)
$bootstrap = $bootstrap.Replace("__COMPILED_REQUIRED__", $compiledRequiredValue)

& $runner -Distro $Distro -WslUser $WslUser -Run $bootstrap
