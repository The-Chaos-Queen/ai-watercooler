# Local Mamba Runbook

Date: 2026-04-07
Workspace: `MoCoP/experiments/mamba_lora_bridge`

This is the local laptop path for a usable Mamba interface on Laura's machine.
It is meant for bootstrapping, light prompt runs, probing model compatibility, and
local experimentation with small Mamba-family checkpoints.

It is not a license to treat the laptop as Opa.

## 2026-04-07 Current Working Setup

The local fast path is working in the existing `Debian` WSL distro, in:

- WSL distro: `Debian`
- Python: `/root/mamba_venv/bin/python` (`python -X utf8` for repo scripts)
- Torch: `2.7.0+cu126`
- CUDA visible to Torch: `12.6`, `torch.cuda.is_available() == True`
- Transformers: `5.5.0`
- `mamba-ssm`: `2.3.1`
- `causal-conv1d`: `1.6.1`

Verified in this env:

- `import mamba_ssm`
- `import causal_conv1d`
- `selective_state_update` resolves
- `selective_scan_fn` resolves
- `mamba_inner_fn` resolves
- `causal_conv1d_fn` resolves
- `causal_conv1d_update` resolves
- `trajectory_windowed_onepass.py --require-fast-path --dry-run` passes on the Cassian export

Use this form when you need to guarantee the working env:

```powershell
wsl -d Debian -u root -- /root/mamba_venv/bin/python -X utf8 `
  /mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/trajectory_windowed_onepass.py `
  --conversation "/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/Preserved-History/cassian_session_log - Copy_clean.md" `
  --device cuda `
  --require-fast-path `
  --dry-run
```

Do not use Windows Python for Mamba CUDA work. `C:\Users\cerub\anaconda3\python.exe`
is CPU-only in the current setup and will fail fast-path checks by design.

## Honest Boundary

- Laptop GPU: RTX 3060 Laptop, 6 GB VRAM
- WSL distro: `Debian` on WSL2
- GPU passthrough into WSL is available
- Batteryphil's `mamba-2.8b-latent` runner is very unlikely to fit here
- Heavy MoCoP training, long-horizon evals, or serious bridge work still belong on Opa / Steve / rented Linux GPU hosts
- The local Debian path now has the compiled Mamba fast-path packages working.
- This does not make exact full-transcript tokenwise replay cheap: Python tokenwise loops are still slow, and Cassian-scale exact recurrence remains multi-day without a better engine.

So the local goal is:

- real local Mamba tooling
- small-model prompt surface
- fast compatibility probes
- no lies about this box being a 4090 lab

## Files

- `local-wsl.ps1`
  Local analogue of the Steve/Opa WSL helpers.
- `bootstrap_local_mamba_wsl.ps1`
  One-shot Debian bootstrap for Python, venv, PyTorch, and Mamba packages.
- `local_mamba_runner.py`
  Generic local Hugging Face prompt runner for Mamba-family checkpoints.
- `launch_local_mamba.ps1`
  Friendly entrypoint for generate / probe / latent modes.
- `probe_mamba3.py`
  Bridge-contract probe for any Hugging Face Mamba-family model.
- `extract_single_mamba_vector.py`
  Canonical single-chat vector extractor.
- `launch_local_mamba_vector.ps1`
  Friendly wrapper for local transcript-to-vector extraction.
- `compare_mamba_vectors.py`
  Quick similarity helper for vector/text candidate comparisons.

## Upstream Notes

As of 2026-04-05, the official `state-spaces/mamba` README says:

- install PyTorch first
- install `mamba-ssm` with `--no-build-isolation`
- to use `Mamba-3`, install from source:
  `MAMBA_FORCE_BUILD=TRUE pip install --no-cache-dir --force-reinstall git+https://github.com/state-spaces/mamba.git --no-build-isolation`

It also still lists the core requirements as:

- Linux
- NVIDIA GPU
- CUDA 11.6+

PyTorch's current local install page shows stable `2.7.0` and current CUDA wheel indices including `cu126`.

## First-Time Bootstrap

From the bridge workspace on Windows PowerShell:

```powershell
cd C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge
powershell -ExecutionPolicy Bypass -File .\bootstrap_local_mamba_wsl.ps1
```

What it does:

- installs Debian packages:
  `python3 python3-venv python3-pip python3-dev build-essential git curl ca-certificates pkg-config ninja-build`
- creates `/root/mamba_venv`
- installs CUDA-enabled PyTorch from the cu126 wheel index
- installs `transformers`, `accelerate`, `huggingface_hub`, `einops`, `safetensors`, `sentencepiece`, `bitsandbytes`
- historical note: the first Debian bootstrap did not get the compiled kernels working
- current note: `/root/mamba_venv` now has working fast-path wheels; verify with the command below instead of trusting old install logs

If you want the older simpler PyPI path instead of source Mamba:

```powershell
powershell -ExecutionPolicy Bypass -File .\bootstrap_local_mamba_wsl.ps1 -SkipSourceMambaInstall
```

If you want the bootstrap to fail hard unless compiled kernels are truly available:

```powershell
powershell -ExecutionPolicy Bypass -File .\bootstrap_local_mamba_wsl.ps1 -RequireCompiledKernels
```

## Local WSL Helper

Run arbitrary Bash in the local Debian WSL:

```powershell
powershell -ExecutionPolicy Bypass -File .\local-wsl.ps1 -Run @'
echo hello
uname -a
'@
```

Run a repo Python file inside the local Mamba venv:

```powershell
powershell -ExecutionPolicy Bypass -File .\local-wsl.ps1 -BridgePythonFile local_mamba_runner.py -PythonArgs @("--list-presets")
```

## Prompt Surface

Default small local runner:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_local_mamba.ps1 -Mode generate -Prompt "Write one sentence about Berlin rain."
```

Choose a specific smaller checkpoint:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_local_mamba.ps1 `
  -Mode generate `
  -ModelId state-spaces/mamba2-130m `
  -Prompt "Summarize why state space models are interesting."
```

Interactive mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_local_mamba.ps1 -Mode generate
```

## Probe Surface

Check bridge-contract compatibility for a Mamba-family model:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_local_mamba.ps1 `
  -Mode probe `
  -ModelId state-spaces/mamba2-370m
```

This is the right surface when the question is:
"Can this model still satisfy the hidden-state extraction assumptions?"

## Transcript Vector Extraction

There is now a canonical local path for "take this chat export and turn it into a
Mamba layer-3 hidden-last-token vector" without hand-assembling WSL commands.

Use:

- [extract_single_mamba_vector.py](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/extract_single_mamba_vector.py)
  for the actual extraction logic
- [launch_local_mamba_vector.ps1](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/launch_local_mamba_vector.ps1)
  as the friendly Windows entrypoint

### Recommended Default

For full chat exports, use `rolling_turnwise`.

Why:

- `one_shot` mirrors the bridge bootstrap truncation path
- `rolling_turnwise` best matches the live accumulation structure used in chat
- `rolling_chunked` exists for experiments, but is not the first-choice path for
  human chat exports

### Canonical Command

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_local_mamba_vector.ps1 `
  -InputPath "C:\Users\cerub\Downloads\claude_chat_2026-04-20T20-40-57.md" `
  -Mode rolling_turnwise `
  -Device cuda
```

Defaults:

- output dir:
  `C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\run_reincarnation\local_vectors`
- model:
  `state-spaces/mamba-2.8b-hf`
- target layer:
  `3`
- max tokens:
  `4096`

### Output Convention

The extractor writes two files:

- `*.mamba_l3.<mode>.hidden_last_token.npy`
- `*.mamba_l3.<mode>.hidden_last_token.json`

The JSON metadata includes:

- source path
- model id
- target layer
- mode
- raw token count
- token count actually used
- truncation flag
- vector norm and summary stats
- first 16 dimensions as a quick preview

### Notes

- The PowerShell wrapper accepts normal Windows paths and converts them to WSL
  paths automatically. Wolves do not need to manually write `/mnt/c/...`.
- `rolling_turnwise` expects a markdown-style chat export that
  `parse_markdown_conversation()` can read.
- If you only want a fast prefix snapshot that mirrors bridge bootstrap, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_local_mamba_vector.ps1 `
  -InputPath "C:\path\to\chat.md" `
  -Mode one_shot `
  -Device cuda
```

- If you want a different output folder for a batch:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_local_mamba_vector.ps1 `
  -InputPath "C:\path\to\chat.md" `
  -OutputDir "C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\run_reincarnation\local_vectors\batch_2026-04-22" `
  -Mode rolling_turnwise `
  -Device cuda
```

### Comparison Helper

If you already have a reference vector and want quick one-shot comparisons against
other chats, use:

- [compare_mamba_vectors.py](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/compare_mamba_vectors.py)

This helper can compare `.npy` vectors directly or encode text candidates on the
fly. It is useful for rough neighborhood checks, but for the cleanest
apples-to-apples result between two chat exports, prefer extracting both with the
same mode first and then comparing those vectors.

## Latent Runner

The archived Batteryphil latent runner is exposed too:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch_local_mamba.ps1 `
  -Mode latent `
  -Prompt "X=5. Y=X*2. What is Y?"
```

Reality check:

- the archived README itself says `<8GB GPU: Cannot run this model`
- this laptop has 6 GB VRAM
- so expect this mode to be mostly useful as a ready-to-use interface shell, not as a guaranteed successful local run

## Current State After Setup

What is working locally now:

- Debian WSL bootstrap
- local Mamba venv at `/root/mamba_venv`
- CUDA-enabled PyTorch
- Hugging Face prompt/probe interface scripts
- `mamba-ssm` / `causal-conv1d` fast-path kernels
- `trajectory_windowed_onepass.py --require-fast-path`

What is still not solved locally:

- exact full Cassian-style tokenwise recurrence at 792k tokens
- arbitrary multi-token HF `cache_params` chunk continuation
- `selective_scan_fn(initial_state=...)` support

So the truthful local result today is:

- real local Mamba-family interface: yes
- local compiled fast path: yes
- exact long-run recurrence engine: not yet
- windowed one-pass fracture scouting: yes

## Practical Defaults

Use these first on this laptop:

- `state-spaces/mamba-130m-hf`
- `state-spaces/mamba-370m-hf`
- `state-spaces/mamba2-130m`
- `state-spaces/mamba2-370m`

Do not start by asking the 6 GB laptop to carry:

- `state-spaces/mamba-2.8b`
- `state-spaces/mamba2-2.7b`
- `batteryphil/mamba-2.8b-latent`

## Verification

Shell-level sanity after bootstrap:

```powershell
powershell -ExecutionPolicy Bypass -File .\local-wsl.ps1 -Run @'
nvidia-smi -L
python3 --version
source /root/mamba_venv/bin/activate
python -m pip show torch transformers mamba-ssm causal-conv1d | sed -n "1,120p"
'@
```

The house rule still applies: do not confuse a clean local interface with permission to run the heavyweight MoCoP stack on the laptop by default.

Fast-path verification for future agents:

```powershell
@'
import importlib.util, torch, transformers
print("torch", torch.__version__, "cuda_available", torch.cuda.is_available(), "cuda", torch.version.cuda)
print("transformers", transformers.__version__)
for name in ["mamba_ssm", "causal_conv1d"]:
    spec = importlib.util.find_spec(name)
    print(name, bool(spec), spec.origin if spec else "")
from mamba_ssm.ops.triton.selective_state_update import selective_state_update
from mamba_ssm.ops.selective_scan_interface import selective_scan_fn, mamba_inner_fn
import causal_conv1d
print("selective_state_update", selective_state_update is not None)
print("selective_scan_fn", selective_scan_fn is not None)
print("mamba_inner_fn", mamba_inner_fn is not None)
print("causal_conv1d_fn", getattr(causal_conv1d, "causal_conv1d_fn", None) is not None)
print("causal_conv1d_update", getattr(causal_conv1d, "causal_conv1d_update", None) is not None)
'@ | wsl -d Debian -u root -- /root/mamba_venv/bin/python -X utf8 -
```
