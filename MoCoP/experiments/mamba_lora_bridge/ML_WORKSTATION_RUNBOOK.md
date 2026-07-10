# ML Workstation Runbook

Date: 2026-04-26
Workspace: `MoCoP/experiments/mamba_lora_bridge`

This is the operational note for the dedicated Linux ML workstation.
Do not merge this with Steve's runbook: Steve is a shared Windows/WSL host, while this machine is native Ubuntu with a different CUDA/PyTorch/compiler stack.

## Host Summary

- LAN host: `192.168.2.196`
- SSH user: `isabell`
- Hostname: `ML-WS`
- Preferred SSH alias: `ml-ws` / `mlws`
- OS: Ubuntu 26.04 LTS
- CPU: Ryzen 9 7950X3D, 16 cores / 32 threads
- RAM: about 90 GiB visible from the 96 GB kit
- GPU: RTX 3090, 24 GiB VRAM
- Root disk: about 1.8 TiB NVMe

Basic access check from the laptop:

```powershell
ssh ml-ws hostname
ssh ml-ws whoami
ssh ml-ws uname -a
```

Expected user is `isabell`. If Windows `ssh ml-ws` tries to log in as the Windows account instead (for example `cerub`), the Windows OpenSSH config is missing or wrong; see [SSH Alias Configuration](#ssh-alias-configuration).

Raw fallback if the alias is broken:

```powershell
ssh isabell@192.168.2.196 hostname
ssh isabell@192.168.2.196 whoami
```

GPU check:

```powershell
ssh ml-ws "nvidia-smi"
```

Verified NVIDIA driver:

```text
595.58.03
```

## SSH Alias Configuration

Keep both WSL OpenSSH and Windows OpenSSH pointed at the same machine/user. WSL and Windows read different config files, so a working WSL alias does **not** prove that `ssh ml-ws` from PowerShell is correct.

### WSL config

File:

```bash
~/.ssh/config
```

Expected stanza:

```sshconfig
Host ml-ws mlws
    HostName 192.168.2.196
    User isabell
    IdentityFile ~/.ssh/id_ed25519_mlws
    IdentitiesOnly yes
```

Verify from WSL:

```bash
ssh -G ml-ws | awk '/^(hostname|user|port|identityfile|identitiesonly) /{print}'
ssh -o BatchMode=yes -o ConnectTimeout=8 ml-ws 'hostname && whoami'
```

### Windows OpenSSH config

File:

```text
C:\Users\cerub\.ssh\config
```

Expected stanza:

```sshconfig
Host ml-ws mlws
    HostName 192.168.2.196
    User isabell
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

Verify from PowerShell/CMD:

```powershell
ssh -G ml-ws | Select-String '^(hostname|user|port|identityfile|identitiesonly) '
ssh -o BatchMode=yes -o ConnectTimeout=8 ml-ws hostname
ssh -o BatchMode=yes -o ConnectTimeout=8 ml-ws whoami
```

Expected verification output includes:

```text
user isabell
hostname 192.168.2.196
ML-WS
isabell
```

If Windows reports `user cerub`, the Windows config lacks the `Host ml-ws` stanza; add the Windows stanza above. Do not “fix” this on the server side unless the alias config is already correct and auth still fails.

## Python Environment

Miniforge is installed at:

```bash
/home/isabell/miniforge3
```

Primary ML environment:

```bash
torch311
```

Use this invocation style for remote jobs:

```powershell
ssh isabell@192.168.2.196 "~/miniforge3/bin/mamba run -n torch311 python your_script.py"
```

Current verified stack:

```text
Python: 3.11.15
torch: 2.11.0+cu130
torch CUDA build: 13.0
GPU: NVIDIA GeForce RTX 3090
mamba-ssm: 2.3.1
causal-conv1d: 1.6.1
```

Additional chat/runtime packages installed in `torch311`:

```text
accelerate
bitsandbytes
qdrant-client
sentence-transformers
```

Important caveat:

The first PyTorch install was `2.11.0+cu128`, but building/installing `mamba-ssm` pulled the environment to `torch 2.11.0+cu130`.
This is currently working with driver `595.58.03`.
Do not blindly "fix" it back to Steve's older `torch 2.7.0+cu126` stack unless there is a concrete failure.

### Gemma-4 / DQ1a runtime fix (verified 2026-07-05)

> **⚠ ENV VERDICT (corrected same day — Isegrim; wc #743 causal claim retracted, see closure post).**
> torch311 was ROLLED BACK to `transformers==5.6.2` on 2026-07-05 (keeper-authorized), and the
> **production bridge stack is verified GREEN at 5.6.2**: chat_server boot smoke on a throwaway
> port with checkpoint `cheese_reincarnation_bridge_1.5b_codexfix.pt` — v_proj patch at layers
> 12–15, live injection at α=0.2, `/status` healthy (`bridge_loaded: true`). Lobby-Alex is bootable.
>
> - Bridge compatibility with transformers 5.10-dev / 5.14-dev is **UNMEASURED**. The first
>   adjudication used `smoke_test.py`, whose default BridgeConfig expects a 5120-wide
>   (non-production) compressor geometry; it fails identically at 5.6.2 / 5.10 / 5.14
>   ("got 2560, expected 5120") and is therefore NOT a valid bridge smoke on this host.
>   Follow-up filed: give it a checkpoint-faithful `--bridge-path` mode. The valid smoke is
>   the throwaway-port chat_server boot used above.
> - Standing doctrine (grounded in conservatism + the only verified-green datum, not in
>   measured breakage): **torch311 stays pinned at `transformers==5.6.2` — the BRIDGE env**
>   (chat_server / live Mamba extraction / compressor contract). **Gemma eval work runs in
>   the `gemma4-mocop` overlay venv** (see "Gemma-4 Loading" above; proven by the #130
>   gemma-primary run, wc #737).
> - DQ1a needs NO single env: extract Mamba-side artifacts in the bridge env, ship tensors,
>   inject/measure on Gemma in the overlay (MVB-style artifact shipping).
> - **2026-07-05 addendum (Gemma chat_server scoping):** the production Mamba WIDTH contract
>   (layer-3 `hidden_last_token` `[1, 2560]`, n_hidden_states 65) is verified **GREEN under the
>   `gemma4-mocop` overlay (5.10-dev)** — a future single-env Gemma chat_server is NOT blocked
>   by extraction width. Still untested at 5.10-dev: the incremental `cache_params` path
>   (live accumulation) and the full compressor→injection pipeline. Note: 5.10-dev deprecates
>   `torch_dtype=` in favor of `dtype=` — integration code should use the new kwarg.

Ghost's Qwen fallback exposed two ML-WS blockers for the Gemma-primary/DQ1a path:

1. `torch311`'s released `transformers 5.6.2` did not recognize Gemma-4 checkpoints:
   `model_type=gemma4_unified` raised `ValueError: Transformers does not recognize this architecture`.
2. `bitsandbytes` could not find CUDA 13 JIT/linker libraries unless the CUDA-13 wheel library path was exported:
   `libnvJitLink.so.13: cannot open shared object file`.

> **⚠ SUPERSEDED — HISTORICAL RECORD ONLY (same day, #747 rollback; patch per Gidim #760).**
> Everything from here to the end of this subsection describes the fix AS ORIGINALLY APPLIED,
> which was REVERTED the same day: `torch311` is pinned back to `transformers==5.6.2` (see the
> ENV VERDICT block above). **Do NOT run the pip install below — it re-breaks the bridge env
> and undoes a keeper-authorized rollback.** The LIVE gemma path is the `gemma4-mocop` overlay
> venv (see "Gemma-4 (`gemma4_unified`) Loading" below): run sweep/staircase commands with
> `/home/isabell/venvs/gemma4-mocop/bin/python` plus the same LD_LIBRARY_PATH/HF_HOME exports.
> The `LD_LIBRARY_PATH` export itself remains valid in every era.

Fix as originally applied on ML-WS in `torch311` (**since reverted — historical**):

```bash
# Required before bnb/4-bit runs in this env. (Still true today.)
export LD_LIBRARY_PATH=/home/isabell/miniforge3/envs/torch311/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}

# Gemma-4 architecture support. Installed commit b70d02fc724d04c916832ca4ead03ff05e8fb1ee.
# REVERTED same day — do not re-run (see banner above).
~/miniforge3/bin/mamba run -n torch311 python -m pip install --upgrade \
  'git+https://github.com/huggingface/transformers.git'
```

Post-fix version smoke:

```bash
~/miniforge3/bin/mamba run -n torch311 python - <<'PY'
import transformers
from transformers import AutoConfig
print('transformers', transformers.__version__)
for model_id in ['google/gemma-4-12B', 'google/gemma-4-12B-it']:
    cfg = AutoConfig.from_pretrained(model_id, trust_remote_code=True)
    print(model_id, cfg.model_type, cfg.text_config.num_hidden_layers)
PY
```

Verified output on 2026-07-05:

```text
transformers 5.14.0.dev0
google/gemma-4-12B gemma4_unified 48
google/gemma-4-12B-it gemma4_unified 48
```

Gemma layer-sweep script support:

- `spikes/run_gemma_layer_sweep.py` now supports both `--quantization 4bit` and `--no-quant` / bf16.
- Prefer `--quantization 4bit` for full sweeps on the RTX 3090 now that bnb is working.
- Keep `--no-quant` as the fallback if the 4-bit conversion path regresses; it loads bf16 with CPU offload and was smoke-tested, but is slower/less memory-efficient.
- Use `--max-prompts-per-category 1` for smoke only; omit it for the full DQ1a/Gemma geometry sweep.

Smoke commands as run on 2026-07-05 under the since-reverted 5.14 install (**historical** — for a rerun today, replace `~/miniforge3/bin/mamba run -n torch311 python` with `/home/isabell/venvs/gemma4-mocop/bin/python` and add the HF_HOME/HF_HUB_CACHE exports; see the results README `staircase_sev_20260705` for the current canonical command):

```bash
cd /home/isabell/mocop/mamba_lora_bridge
export LD_LIBRARY_PATH=/home/isabell/miniforge3/envs/torch311/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}

~/miniforge3/bin/mamba run -n torch311 python spikes/run_gemma_layer_sweep.py \
  --model google/gemma-4-12B-it \
  --quantization 4bit \
  --max-prompts-per-category 1 \
  --output results/gemma_layer_sweep_smoke_it_4bit.json

~/miniforge3/bin/mamba run -n torch311 python spikes/run_gemma_layer_sweep.py \
  --model google/gemma-4-12B \
  --quantization 4bit \
  --max-prompts-per-category 1 \
  --output results/gemma_layer_sweep_smoke_base_4bit.json
```

Both wrote reports successfully on 2026-07-05 (`48` text layers, hidden size `3840`). `--no-quant` smokes also passed for base and instruct, with expected CPU offload messages.

## Mamba Fast-Path Build

CUDA build tools and compiler were installed into the conda environment, not system-wide:

```bash
~/miniforge3/bin/mamba install -y -n torch311 -c nvidia -c conda-forge \
  cuda-nvcc=12.8 cuda-cudart-dev=12.8 cuda-version=12.8 cmake ninja git
```

CUDA 12.8 rejected the default GCC 14 toolchain, so GCC/G++ 13 were installed:

```bash
~/miniforge3/bin/mamba install -y -n torch311 -c conda-forge gcc_linux-64=13 gxx_linux-64=13
```

Build environment:

```bash
export CUDA_HOME=/home/isabell/miniforge3/envs/torch311
export CC=/home/isabell/miniforge3/envs/torch311/bin/x86_64-conda-linux-gnu-gcc
export CXX=/home/isabell/miniforge3/envs/torch311/bin/x86_64-conda-linux-gnu-g++
export MAX_JOBS=12
```

Build `causal-conv1d`:

```bash
~/miniforge3/bin/mamba run -n torch311 bash -lc '
export CUDA_HOME=/home/isabell/miniforge3/envs/torch311
export CC=/home/isabell/miniforge3/envs/torch311/bin/x86_64-conda-linux-gnu-gcc
export CXX=/home/isabell/miniforge3/envs/torch311/bin/x86_64-conda-linux-gnu-g++
export MAX_JOBS=12
python -m pip install --no-build-isolation --no-cache-dir causal-conv1d==1.6.1
'
```

Build `mamba-ssm` from source:

```bash
~/miniforge3/bin/mamba run -n torch311 bash -lc '
export CUDA_HOME=/home/isabell/miniforge3/envs/torch311
export CC=/home/isabell/miniforge3/envs/torch311/bin/x86_64-conda-linux-gnu-gcc
export CXX=/home/isabell/miniforge3/envs/torch311/bin/x86_64-conda-linux-gnu-g++
export MAX_JOBS=12
export MAMBA_FORCE_BUILD=TRUE
python -m pip install --no-build-isolation --no-cache-dir git+https://github.com/state-spaces/mamba.git
'
```

The installed `mamba-ssm` source commit was:

```text
316ed6036538405f767782132f76caf342256d33
```

## Fast-Path Validation

Run this from the laptop:

```powershell
ssh isabell@192.168.2.196 "~/miniforge3/bin/mamba run -n torch311 python - <<'PY'
import importlib
import torch

print('torch', torch.__version__)
print('torch_cuda_build', torch.version.cuda)
print('cuda_available', torch.cuda.is_available())
if torch.cuda.is_available():
    print('device', torch.cuda.get_device_name(0))

checks = {}
import causal_conv1d
checks['causal_conv1d_fn'] = getattr(causal_conv1d, 'causal_conv1d_fn', None) is not None
checks['causal_conv1d_update'] = getattr(causal_conv1d, 'causal_conv1d_update', None) is not None

import mamba_ssm
checks['mamba_ssm_import'] = True

for mod, attrs in [
    ('mamba_ssm.ops.triton.selective_state_update', ['selective_state_update']),
    ('mamba_ssm.ops.selective_scan_interface', ['selective_scan_fn', 'mamba_inner_fn']),
]:
    m = importlib.import_module(mod)
    for attr in attrs:
        checks[attr] = getattr(m, attr, None) is not None

print(checks)
print('all_available', all(v is True for v in checks.values()))
PY"
```

Expected result:

```text
torch 2.11.0+cu130
torch_cuda_build 13.0
cuda_available True
device NVIDIA GeForce RTX 3090
all_available True
```

## Model-Level Smoke Test

Import checks are not enough. Run one real CUDA forward pass:

```powershell
ssh isabell@192.168.2.196 "~/miniforge3/bin/mamba run -n torch311 python - <<'PY'
import torch
from mamba_ssm import Mamba

model = Mamba(d_model=128, d_state=16, d_conv=4, expand=2).cuda().half().eval()
x = torch.randn(2, 64, 128, device='cuda', dtype=torch.float16)
with torch.inference_mode():
    y = model(x)
print('forward_shape', tuple(y.shape))
print('dtype', y.dtype)
print('finite', bool(torch.isfinite(y).all().item()))
PY"
```

Verified output:

```text
forward_shape (2, 64, 128)
dtype torch.float16
finite True
```

## Speed Sanity Benchmark

Synthetic Mamba single-layer forward benchmark on RTX 3090:

```text
small_layer_768x512: batch=4 seq=512 d=768 ms_per_layer=0.521 tokens_per_s_per_layer=3,934,210
mid_layer_1024x2048: batch=1 seq=2048 d=1024 ms_per_layer=0.747 tokens_per_s_per_layer=2,741,667
mamba2p8b_like_layer_2560x2048: batch=1 seq=2048 d=2560 ms_per_layer=3.044 tokens_per_s_per_layer=672,842
mamba2p8b_like_layer_2560x4096: batch=1 seq=4096 d=2560 ms_per_layer=5.599 tokens_per_s_per_layer=731,547
```

Interpretation:

- Fast path is healthy.
- These are per-layer synthetic prefill numbers, not full-model generation speed.
- End-to-end speed still depends on full layer count, tokenizer, sampling, memory movement, and the MoCoP harness.

Benchmark command:

```powershell
ssh isabell@192.168.2.196 "~/miniforge3/bin/mamba run -n torch311 python - <<'PY'
import torch
from mamba_ssm import Mamba

torch.backends.cuda.matmul.allow_tf32 = True

cases = [
    ('small_layer_768x512', 768, 512, 4, 80),
    ('mid_layer_1024x2048', 1024, 2048, 1, 60),
    ('mamba2p8b_like_layer_2560x2048', 2560, 2048, 1, 30),
    ('mamba2p8b_like_layer_2560x4096', 2560, 4096, 1, 15),
]

print('torch', torch.__version__, 'cuda', torch.version.cuda)
print('gpu', torch.cuda.get_device_name(0))

for name, d_model, seqlen, batch, iters in cases:
    torch.cuda.empty_cache()
    model = Mamba(d_model=d_model, d_state=16, d_conv=4, expand=2).cuda().half().eval()
    x = torch.randn(batch, seqlen, d_model, device='cuda', dtype=torch.float16)
    with torch.inference_mode():
        for _ in range(8):
            y = model(x)
        torch.cuda.synchronize()
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        for _ in range(iters):
            y = model(x)
        end.record()
        torch.cuda.synchronize()
    ms = start.elapsed_time(end) / iters
    toks = batch * seqlen / (ms / 1000.0)
    print(f'{name}: batch={batch} seq={seqlen} d={d_model} ms_per_layer={ms:.3f} tokens_per_s_per_layer={toks:,.0f} out_finite={bool(torch.isfinite(y).all().item())}')
PY"
```

## Operational Notes

- Keep this machine for native Linux ML work and long Mamba/Qwen experiments.
- Use Steve only when a task explicitly needs Steve's chat-server setup or existing Windows/WSL scheduled-task wiring.
- Avoid RGB/control-plane experiments until the ML stack is fully documented and stable.
- Prefer conda-env-local CUDA/compiler packages over system-wide mutations unless there is a concrete reason.
- Active ML working directories live under `/home/isabell/ml`.
- The current lean MoCoP chat runtime bundle is deployed at `/home/isabell/mocop/mamba_lora_bridge`.
- The deployed `chat_server.py` default speaker label is neutral `User`, not `Laura`. Pass `--user-label Laura` only for sessions that should explicitly be Laura.
- Existing Qdrant default `192.168.2.191:6333` is reachable from ML-WS.
- Before long jobs, check thermals and VRAM:

```powershell
ssh isabell@192.168.2.196 "nvidia-smi --query-gpu=temperature.gpu,power.draw,memory.used,memory.total --format=csv"
```

## IRC-Style Multi-Session Chat

`chat_server.py` supports an IRC-lobby style mode: one long-running model process, multiple logical chat sessions.

The model, tokenizer, bridge modules, and hooks stay global. Per `session_id`, the server swaps:

- speaker labels
- `instance_id`
- Qdrant collection / private-memory mode
- transcript and turn-log paths
- conversation history
- runtime counters
- dual-gate events
- live Mamba cache state

The server accepts session identity through any of these:

```text
JSON body:       {"session_id": "pinky", "user_label": "Pinky", ...}
HTTP header:     X-MoCoP-Session: pinky
URL query:       /status?session_id=pinky
Browser URL:     http://HOST:PORT/?session_id=pinky&user_label=Pinky&instance_id=pinky
```

Browser usage:

```text
http://192.168.2.196:7860/?session_id=laura&user_label=Laura&instance_id=laura
http://192.168.2.196:7860/?session_id=pinky&user_label=Pinky&instance_id=pinky
```

If no `session_id` is provided, the browser generates and persists one in `localStorage`. This prevents two ordinary browser tabs from automatically sharing `default`.

API example:

```powershell
curl.exe -s http://192.168.2.196:7860/chat `
  -H "Content-Type: application/json" `
  -d "{\"session_id\":\"pinky\",\"user_label\":\"Pinky\",\"instance_id\":\"pinky\",\"no_shared_memory\":true,\"message\":\"hello\"}"
```

Private-memory behavior:

- `no_shared_memory=true` with `instance_id=pinky` routes to the private collection name built by `chat_server.py`.
- Private `mocop_private_*` collections are created on demand by `chat_server.py` if missing. They use the configured sentence-transformer embedding dimension and cosine distance.
- `qdrant_collection=some_collection` overrides that explicitly.
- Shared recall still uses the configured default collection.

Important limitation:

This is logical multiplexing, not parallel model serving. Requests are serialized by `CHAT_LOCK`. It is enough for organic seeding and qualitative sessions, but not a high-throughput multi-user deployment.

Known follow-up:

The Qdrant retry/background replay worker is still process-global. It now filters pending rows by `metadata.qdrant_collection`, but do not assume queued write replay is fully per-session until that path is refactored.

## Chat Server Restart: Use Complete HF Cache

The default HuggingFace cache under `/home/isabell/.cache/huggingface` can contain incomplete `state-spaces/mamba-2.8b-hf` shard downloads. If `chat_server.py` is started against that cache, Mamba may hang at `Fetching 3 files` or fail in offline mode with missing shard errors.

Use the complete ML cache for chat-server restarts:

```bash
HF_HOME=/home/isabell/ml/hf_cache
HF_HUB_CACHE=/home/isabell/ml/hf_cache/hub
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

Current known-good IRC server launch pattern:

```bash
cd /home/isabell/mocop/mamba_lora_bridge
setsid -f env \
  HF_HOME=/home/isabell/ml/hf_cache \
  HF_HUB_CACHE=/home/isabell/ml/hf_cache/hub \
  HF_HUB_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  /home/isabell/miniforge3/bin/mamba run -n torch311 python chat_server.py \
    --model Qwen/Qwen2.5-1.5B \
    --bridge-path cheese_reincarnation_bridge_1.5b_codexfix.pt \
    --episodes-file CHEESE_SHAPING_EPISODES.md \
    --episode-index 2 \
    --instance-id lobby \
    --no-shared-memory \
    --qdrant-host 192.168.2.191 \
    --qdrant-port 6333 \
    --no-ambient-recall \
    --memory-integration-mode both \
    --memory-state-max-tokens 768 \
    --live-accumulation \
    --qwen-device cuda:0 \
    --mamba-device cuda:0 \
    --user-label User \
    --model-label Me \
    --alpha 0.2 \
    --temperature 0.2 \
    --max-new-tokens 120 \
    --host 0.0.0.0 \
    --port 7860 \
  > chat_server_irc.log 2>&1 < /dev/null
```

Opussy organic-seeding URL:

```text
http://192.168.2.196:7860/?session_id=opussy&user_label=Opussy&instance_id=opussy&no_shared_memory=true
```

## Gemma-4 (`gemma4_unified`) Loading

The pinned `torch311` transformers (5.6.2, installed 2026-04-25) does **not** know the
`gemma4_unified` architecture — `AutoModelForCausalLM` and `AutoModelForImageTextToText`
both fail with `KeyError: 'gemma4_unified'` at AutoConfig.

Two working paths (2026-06-09):

**Primary — Monk's venv overlay (#598), used for the #592 bakeoff:** interpreter
`/home/isabell/venvs/gemma4-mocop/bin/python` (transformers `5.10.0.dev0`, gemma4 module
present), plus the usual `HF_HOME`/`HF_HUB_CACHE` vars and the bitsandbytes CUDA library
path from `torch311`. Monk added a dedicated section + smoke command to the REMOTE copy of
this runbook on ML-WS — sync on the next bundle pass.

**Alternate — shadow install (Isegrim), proven with `run_role_inversion_spike.py`,** env untouched:

```bash
~/miniforge3/bin/mamba run -n torch311 python -m pip install \
  --target /home/isabell/ml/tf_gemma4_shadow transformers accelerate
# then run with:
env PYTHONPATH=/home/isabell/ml/tf_gemma4_shadow ... mamba run -n torch311 python your_script.py
```

- The shadow dir shadows `transformers`/`tokenizers`/`huggingface-hub` for that process only;
  torch 2.11.0+cu130 and mamba-ssm pins never move. Rollback = delete the folder.
- pip emits a cosmetic `cuda-python/cuda-bindings` resolver warning; ignore.
- Load unified checkpoints with `AutoModelForImageTextToText` (+ `AutoProcessor` and
  structured `{"type": "text", ...}` content), per `run_mira_model_bakeoff.py`.
- **Thought-channel gotcha:** Gemma-4's chat template opens a thought channel in the
  generation header (`<|turn>model\n<|channel>thought\n<channel|>`). Decoded generations can
  carry `thought` channel markers as plain text — strip or handle channels explicitly before
  scoring. `chat_server.py` integration will need channel handling if Gemma-4 becomes the
  substrate.
- Mystery resolved (#598): the bakeoff ran through the `gemma4-mocop` venv overlay above.
  The path existed only in Monk's command transcript until tonight — runbook gap now patched
  on both copies. (Search lesson: check `~/venvs/` before declaring a machine clean.)

### WATCH-OUT: `trust_remote_code=True` is mandatory, and it is NOT an env regression (2026-07-10, #802)

`google/gemma-4-12B` is a **remote-code** model: the `gemma4_unified` weight converter
ships *with the checkpoint* (the "gemma4 module"). Every `from_pretrained` call —
`AutoConfig`, `AutoTokenizer`/`AutoProcessor`, and the model class — **must** pass
`trust_remote_code=True`.

- **Symptom if you forget it:** `RuntimeError: ... issues during automatic conversion of
  the weights`, with `model.language_model.layers.{0..47}.mlp.down_proj.weight | MISSING`
  on all 48 layers. Without the flag, transformers falls back to its **built-in**
  `gemma4` class, whose transformers-main MLP rename drops `down_proj`.
- **This LOOKS like a transformers version regression. It is not.** Pinning versions does
  NOT fix it — verified 2026-07-10 that `cc041637` (main), `b70d02fc` (the reverted 5.14),
  and stable `5.10.4` all fail **identically** without the flag, and the *current* overlay
  loads fine **with** it. Do not go on a version-bisect; add the flag.
- **bf16 only.** `trust_remote_code` + the remote converter is **incompatible with bnb
  4-bit** (the quant path uses the built-in conversion and re-triggers the error). Load
  Gemma-4 in **bf16** (`device_map="auto"` offloads the overflow to CPU on the 3090 — the
  `"Some parameters are on the meta device"` line is expected and benign for read-only
  inference).
- **Who has it / who doesn't:** `spikes/run_gemma_layer_sweep.py` and Monk's gemma smoke
  pass the flag and load clean. `run_base_improv_bakeoff.load_model` does **not** — it will
  keep failing on Gemma until `trust_remote_code=True` is added there (checklist lane).
  `mocop_spike_sink_census.py` (A1 census) uses the correct path.

Minimal working load:

```python
from transformers import AutoModelForImageTextToText, AutoProcessor
import torch
proc  = AutoProcessor.from_pretrained("google/gemma-4-12B", trust_remote_code=True)
model = AutoModelForImageTextToText.from_pretrained(
    "google/gemma-4-12B", trust_remote_code=True, dtype=torch.bfloat16, device_map="auto")
```

### WATCH-OUT: 4-bit (bnb) is currently BROKEN in this overlay — bf16 only (2026-07-10)

The same `cc041637` transformers that needs `trust_remote_code` also has a broken
**quantized-load** path: `BitsAndBytesConfig(load_in_4bit=True)` raises the same
`down_proj`-MISSING conversion `RuntimeError` — and **not just for gemma**:
`Qwen/Qwen2.5-1.5B` in 4-bit fails identically. So 4-bit is unavailable across the
board here until the transformers pin is fixed; **run everything bf16** (`--no-quant`).

Two consequences flagged (Isegrim, board-down ledger):

- **The #130 judge slice (`disposition_judge.py`) defaults to 4-bit** (`HFJudge`,
  `--judge-model <id>` without `--no-quant`) and will hit this busted path. Run the
  real judge with **`--no-quant`** until 4-bit is restored. (The default is correct
  for a healthy env; this is an env-transient caveat, not a code bug.)
- **bf16-only means Gemma-4-12B no longer fits Steve's 16 GB** (it needed 4-bit to
  squeeze in). Until 4-bit is back, the Gemma path is **ML-WS-only** (24 GB, or bf16
  CPU-offload). 31B is bf16 + heavy offload regardless (~62 GB).

### Fast HF downloads: hf_transfer (installed 2026-07-10)

`hf_transfer` (the Rust parallel downloader) is installed in the `gemma4-mocop`
overlay — big shard pulls (e.g. the 31B's ~62 GB) crawl on the default python
downloader. It only activates when the env var is set at download time:

```bash
export HF_HUB_ENABLE_HF_TRANSFER=1   # add alongside HF_HOME / HF_HUB_CACHE
```

`mocop_spike_sink_census.py` sets this itself (`os.environ.setdefault`), so census
runs use it automatically; set it in the shell for ad-hoc `from_pretrained` pulls.

## Runtime Bundle Sync

Do not copy the full local `mamba_lora_bridge` directory blindly.
It is tens of GiB because it contains historical experiment outputs.

The current deployment is a lean top-level runtime bundle containing:

- top-level `.py`, `.md`, `.json`, `.txt`, `.sh`, `.service`, and `.ps1` files
- `cheese_reincarnation_bridge_1.5b_codexfix.pt`
- `cheese_reincarnation_bridge_1.5b.pt`
- `cheese_reincarnation_bridge_7b.pt`
- `kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt`
- `mamba_bootstrap_state_latest.pt`
- `mamba_layer3_states_v1.pt`

Current deployed size:

```text
291 files
161M
```

Smoke after sync:

```powershell
ssh isabell@192.168.2.196 "cd ~/mocop/mamba_lora_bridge && ~/miniforge3/bin/mamba run -n torch311 python chat_server.py --help"
```

Steve-side capabilities (bakeoff env, Qwen3-14B cache, quoting rules) live in `STEVE_RUNBOOK.md` — see its "Bakeoff Capability Update (2026-07-03)" section. Per the header rule: the two runbooks do not merge.
