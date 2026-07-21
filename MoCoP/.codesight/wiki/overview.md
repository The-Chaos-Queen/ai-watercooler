# MoCoP — Overview

> **Navigation aid.** This article shows WHERE things live (routes, models, files). Read actual source files before implementing new features or making changes.

**MoCoP** is a javascript project built with raw-http.

## Scale

183 library files · 5 middleware layers · 43 environment variables

**Libraries:** 183 files — see [libraries.md](./libraries.md)

## Required Environment Variables

- `ANSWER_CONTRACT` — `experiments\mamba_lora_bridge\run_base_improv_bakeoff.py`
- `BRAIN_BRIDGE_MODE` — `experiments\mamba_lora_bridge\server.py`
- `BRAIN_CHECKPOINT_PATH` — `experiments\mamba_lora_bridge\server.py`
- `BRAIN_MODE` — `experiments\mamba_lora_bridge\server.py`
- `BRAIN_TARGET_LAYERS` — `experiments\mamba_lora_bridge\server.py`
- `COGNITIVE_RESPONSE_FORMAT` — `experiments\mamba_lora_bridge\server.py`
- `COMPUTERNAME` — `experiments\mamba_lora_bridge\fleeting_state_crypto.py`
- `CONTEXT_DIM` — `experiments\mamba_lora_bridge\server.py`
- `HF_HOME` — `experiments\mamba_lora_bridge\check_env.py`
- `HF_TOKEN` — `experiments\mamba_lora_bridge\check_env.py`
- `HYPER_DEVICE` — `experiments\mamba_lora_bridge\server.py`
- `INCLUDE_QWEN30` — `experiments\mamba_lora_bridge\run_base_improv_bakeoff.py`
- _...31 more_

---
_Back to [index.md](./index.md) · Generated 2026-07-18_