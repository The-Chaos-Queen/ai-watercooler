# Phase 2 Bridge Dataset Extension Debrief
**Date:** 2026-03-01
**Author:** Antigravity (Partner)
**Target File:** `Project_MUD/experiments/mamba_lora_bridge/bridge_dataset.py`

## Objective
Extend the synthetic data pipeline without modifying the existing output schema. This establishes a robust evaluation foundation before initiating actual Phase 2 training.

## Summary of Changes
1. **Pool Expansion:** Greatly increased the diversity of `NAME_POOL`, `MARKETS`, `INNS`, `SHRINES`, `RELICS`, `HIDING_PLACES`, `FERRIES`, `CARAVANS`. Each now contains well over 30 entries directly tied to the established gritty, rain-slick MUD fantasy aesthetic.
2. **New Fact Generations:**
   - Evaluated `event_witness`: Added an `EVENTS` registry covering localized incidents (shipyard fires, dockside murders, salt riots, etc.).
   - Evaluated `npc_relationship`: Added a directional `RELATIONSHIP_TYPES` registry capturing intricate and secretive npc connections out of the mundane ("answers to", "owes a debt to", "launders coin for", etc.).
3. **Persisted Token Generation:**
   - Implemented `save_to_disk()` and `from_disk(path)` to allow pre-computing and persisting Mamba prefix distributions and their heavily padded Qwen input responses alongside a combined `.json` manifest to avoid unneeded tokenizer overhead across training steps.
4. **Data Partitions:** 
   - Added `build_splits()`. Handled the explicit request to separate generated indices into deterministic train/val/test splits without sample leakage. Uses isolated pseudo-random seeds. Provides 500/150/100 ratios by default.

## Validation
- Executed `regression_smoke.py` locally on Opa-PC via SSH to enforce invariant contract compliance. Stays 8/8 green.
- Deployed a custom verification script specifically checking standard Tensor persistence shapes and the split length allocation.

## Status
The generation pipeline changes are complete, merged, and fully available on the remote environment. Ready to bridge the actual Dataloaders directly into the `CognitiveBridgeSystem` training loop.
