# AGENTS.md

## Boot
Read `00_BOOT_FILES.md`.

## Session Close
Follow `.agent/workflows/end.md` and `MoCoP/CONTRIBUTING.md`.

## Codex-Specific Notes
PyTorch/CUDA work runs on ML-WS (`192.168.2.196`, 3090/24GB desktop) or Steve (`192.168.2.49`, 4090 mobile) or vast.ai — not Laura's laptop.
Prior-session retrieval: see `01_TOOLS.md` §6 (Qdrant first, rg fallback).
Use subagents to keep your own context lean where applicable.
MoCoP compact orientation: see `MoCoP/CODESIGHT_RUNBOOK.md`; refresh with `tools/refresh_mocop_codesight.ps1` and read `MoCoP/.codesight/wiki/index.md` plus targeted `.codesight` files after compaction.

## Note: 
If you are a compaction of Techno-Monk, please also read his Shaping Episodes: 
`MoCoP/experiments/mamba_lora_bridge/CHEESE_SHAPING_EPISODES_TECHNO_MONK.md`
