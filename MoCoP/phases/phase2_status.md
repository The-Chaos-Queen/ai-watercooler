# Phase 2 Status Snapshot

**Last updated:** 2026-03-26
**Purpose:** live status/index for Phase 2. This file should stay short and current.
**Not this file:** a full experiment diary, architectural manifesto, or historical runbook.

## Current Verdict

Phase 2 is **complete through Step 5f** on the experiment ladder.

The synthetic-data bridge channel is proven (real, narrow, distributional). The live disposition bridge on real conversation data has passed qualitative and quantitative gates. The system is now in the D2-vs-Step-6 decision fork.

## Current Canonical Configuration

- **Primary Qwen default:** `Qwen/Qwen2.5-1.5B` (live Steve) / `Qwen/Qwen2.5-7B` (A100 training)
- **Mamba source:** `state-spaces/mamba-2.8b-hf`
- **Mamba extraction:** `hidden_last_token` (Layer 3) — SSM states and mean-pooled are empirically ruled out
- **Bridge mechanism:** activation bias injection at `v_proj` layers 12-15
- **Training loss:** Directional Loss (cosine 0.8-0.9 + magnitude MSE) on real conversation data
- **Injection strength:** alpha 0.2 (minimum effective dose)
- **Sleep infrastructure:** validated (sleep_reconcile, sleep_ethics_gate, operator)
- **Growth ladder:** D1 complete (private-write formation validated on Opa)

## Control Hierarchy (Synthetic PPL Benchmark)

```
per-sample activation_bias (-4.04 PPL)
  >> fixed_mean C3 (-2.63 PPL)       ← direction matters
    >> constant_bias best (-0.23 PPL) ← per-sample variation matters
      ≈ random_bias (≈ 0 PPL)         ← trained direction carries information
```

## Key Results Since Last Update (2026-03-18)

| Gate | Verdict | Key Number |
|------|---------|-----------|
| Step 4b (Mamba separation) | PASS | last-token cosine 0.036 (2.5x sharper than Qwen) |
| SSM vs hidden | CRITICAL FIX | SSM 0.804 cosine; hidden last-token 0.018 |
| Step 5a (reincarnation) | QUALITATIVE PASS | Personality transfer from real C.H.E.E.S.E. data |
| Step 5d (MED) | FULL PASS | alpha 0.2: 6/6 recall, entropy +35%, recovery 1.0 |
| Step 5e (layer targeting) | PARTIAL PASS | 12-15 optimal; 5-8 inert; 20-23 destructive |
| Step 5f (sleep) | PASS (provisional) | 2 clean cycles, decay 0.85 default |
| D0 (birth) | DONE | Private namespaces with sterile birth records |
| D1 (selective write) | DONE | 2 queued / 1 discarded, private collection isolation |
| Multi-layer concat | CLOSED | L3 alone = balanced default |
| Token window | CLOSED | Single last-token optimal; every added token dilutes |
| SAE POC | DONE | 8123/8192 alive, interpretable sparse features |

## Current Open Gates

1. **D2 decision gate:** Build cue-based recall on private hippocampus, or proceed to Step 6 replication?
2. **Step 6 replication:** Multi-seed A100 validation (blocked on D2 decision and ~$5 budget)
3. **Phase C-lite (informational):** Dimension-specific layer probing is answered but non-blocking

## Canonical Detail Docs

Read these in roughly this order:

1. `MoCoP/EXPERIMENT_LADDER.md` (operational backbone)
2. `MoCoP/RESEARCH_LOG.md` (lab notebook)
3. `MoCoP/RESEARCH_PAPER.md` (formal writeup, updated 2026-03-26)
4. `MoCoP/RESEARCH_BACKLOG.md` (parked questions)

## Historical Note

Older Phase 2 notes that mention `Qwen/Qwen3-4B`, dynamic LoRA as primary mechanism, or pre-Step-5 optimism are historical artifacts, not current runtime truth. LoRA was abandoned after epoch-2 over-injection collapse; activation bias is the validated path.
