# Codex Brief: Stage 2 Prep (while Stage 1 runs)

**Context:** Phase 2 Stage 1 is running on Vast.ai A100-SXM4-40GB (Instance 32636125, `root@212.13.234.23 -p 13120`). Claude launched it after taking over from Codex's stream disconnect. ETA ~2h from 14:49 CET. No action needed on the running instance.

**Priority 1: Stage 2 RUNBOOK update for A100-80GB**

Update `MoCoP/experiments/mamba_lora_bridge/RUNBOOK.md` Section "First Paid Cloud Pilot":
- Add a Stage 2 variant targeting A100-80GB hosts
- Recommend `--batch-size 4` (or 8 if VRAM permits) for better GPU utilization
- Current 40GB run uses 35.8GB VRAM at batch-size 1; extrapolate for 80GB
- Keep `--resume-from "$RUN_DIR/bridge_epoch_001.pt"` as-is
- Update host filters: `A100-80GB` or `A100-SXM4-80GB`, same region/reliability criteria
- Note: cost difference is ~$0.15-0.30/hr more, but higher throughput likely makes it cheaper per epoch

**Priority 2: Harden `check_env.py`**

File: `MoCoP/experiments/mamba_lora_bridge/check_env.py`

Add checks learned from today's Vast.ai launch:
1. Check `accelerate` is installed (transformers requires it for `device_map`/`tp_plan`)
2. Check available disk space; warn if < 30GB (HF model cache needs ~15GB for Qwen3-4B + Mamba-2.8b)
3. Check torchvision version compatibility with torch (today's crash: torchvision 0.21 vs torch 2.10)
4. Optional: warn if running on tmpfs/overlay with limited space

Keep existing checks intact. Add new ones as soft failures (increment `failures`) not hard returns.

**Not in scope:**
- Do not touch the running instance or any `/dev/shm` paths
- Do not modify `train_bridge.py` or `models.py`
- Qdrant re-ingest is separate (do that per normal routine)
