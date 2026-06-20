# MoCoP — Overview

> **Navigation aid.** This article shows WHERE things live (routes, models, files). Read actual source files before implementing new features or making changes.

**MoCoP** is a javascript project built with raw-http.

## Scale

134 library files · 5 middleware layers · 31 environment variables

**Libraries:** 134 files — see [libraries.md](./libraries.md)

## Required Environment Variables

- `BRAIN_BRIDGE_MODE` — `experiments\mamba_lora_bridge\server.py`
- `BRAIN_CHECKPOINT_PATH` — `experiments\mamba_lora_bridge\server.py`
- `BRAIN_MODE` — `experiments\mamba_lora_bridge\server.py`
- `BRAIN_TARGET_LAYERS` — `experiments\mamba_lora_bridge\server.py`
- `COGNITIVE_RESPONSE_FORMAT` — `experiments\mamba_lora_bridge\server.py`
- `CONTEXT_DIM` — `experiments\mamba_lora_bridge\server.py`
- `HF_HOME` — `experiments\mamba_lora_bridge\check_env.py`
- `HF_TOKEN` — `experiments\mamba_lora_bridge\check_env.py`
- `HYPER_DEVICE` — `experiments\mamba_lora_bridge\server.py`
- `INCLUDE_QWEN30` — `experiments\mamba_lora_bridge\run_base_improv_bakeoff.py`
- `KMP_DUPLICATE_LIB_OK` — `experiments\mamba_lora_bridge\activation_sessions\ccgp_disposition_test.py`
- `LORA_RANK` — `experiments\mamba_lora_bridge\server.py`
- _...19 more_

---
_Back to [index.md](./index.md) · Generated 2026-06-17_