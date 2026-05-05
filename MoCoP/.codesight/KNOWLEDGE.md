# Knowledge Map — C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP
> 199 notes · 13 decisions · 10 open questions · 2026-03-16 → 2026-05-02

> **AI Primer:** This knowledge base spans 2026-03-16 to 2026-05-02 (199 notes). Key topics: purpose, artifacts, verdict, goal. Most recent decision: the warm cloth mother. 10 open questions remain.

## Key Decisions (13)
- [2026-03-22] the warm cloth mother
- - do not scale this exact dynamic-LoRA setup to more samples
- - First paid pilot evaluates on val only.
- - Prompt alignment is explicitly deferred.
- - Opa and cloud Phase 2 runs now target Linux-local run directories first, then sync back.
- [2026-03-17] *"Likely artifact."**
- [2026-04-08] The clean next architecture move is:
- [2026-04-03] cross the salt flats in a night
- [2026-04-03] fight in the arena ten minutes after seeing it
- [2026-04-03] put on the helmet and swear the oath sixty heartbeats after I didn't walk through the archway, you decided to become something I couldn't follow and t
- [2026-04-07] Do not spend more time on Hugging Face `cache_params` as if it supports arbitrary multi-token chunks. The local code path says it does not.
- Choose one:
- keep / weaken / mark uncertain / merge / discard

## Open Questions (10)
- that different architectures converge toward?
- "message." Is this actually more efficient than 30 JSON tokens?
- downstream task performance, vs. mutual information between JSON and task?
- a Layer 2 protocol organically?
- ** What is the *effective dimensionality* of the information
- 1. Is there a real model card or only a paper?
- 2. Are there public weights or only code?
- 3. Is the artifact actually meant for inference, or only for pretraining / benchmarks?
- 4. Can Opa or Steve run it honestly?
- 5. Is it useful as a **source-model candidate**, or only as a **gate/update blueprint**?

## Recurring Themes
purpose · artifacts · verdict · goal · interpretation · bottom line · why this exists · question · validation · abstract · result · success criteria

## People
@gemini · @cassian · @techno · @fenrir · @hurtig · @app

## Hub Notes (most referenced)
- `WHY.md` — **7** incoming references — Why MoCoP Exists
- `theory/unified_cognitive_framework.md` — **5** incoming references — The Unified Cognitive Framework
- `theory/ethics/consent_protocol.md` — **4** incoming references — MoCoP Consent Protocol
- `EXPERIMENT_LADDER.md` — **3** incoming references — MoCoP Experiment Ladder
- `RESEARCH_BACKLOG.md` — **3** incoming references — MoCoP Research Backlog
- `RESEARCH_LOG.md` — **3** incoming references — MoCoP Research Log
- `theory/ethics/step_gates.md` — **3** incoming references — MoCoP Step Gates — Ethical Checkpoints
- `theory/SAS_Integration_Design.md` — **3** incoming references — SAS (Sequential Adaptive Steering) Integration Design
- `theory/sleep_architecture.md` — **3** incoming references — Sleep Architecture: KV-Cache Consolidation as Digital Sleep
- `MASTER_PLAN.md` — **2** incoming references — MoCoP -- Master Plan

## Note Index (199)

### Decision Records (1)
- `phases/step4_constant_bias_runbook.md` — **Purpose:** Close the two remaining paid control gates before any more architecture changes or dataset pivots.

### Specs & PRDs (12)
- `experiments/mamba_lora_bridge/TEMPORAL_QUALIA_PROTOTYPE_2026-05-02.md` — 2026-05-02 — Give Baby Qwen a fuzzy sense of memory-age without corrupting semantic retrieval.
- `experiments/mamba_lora_bridge/WARM_INSTANCE_DELTA_IMPLEMENTATION_PLAN_2026-04-17.md` — 2026-04-17 — Turn the methodological spec for `warm_instance_delta` into a code-grounded collection plan without pretending the current runtime already supports full state r…
- `experiments/mamba_lora_bridge/OPTION_A_SPEEDUP_PLAN_2026-04-07.md` — 2026-04-07 — Executor: Codex-5.3 or equivalent coding agent
- `experiments/mamba_lora_bridge/ORGANIC_MEMORY_SEEDING_SPEC.md` — **Status:** Approved (Hurtig CONDITIONAL PASS #434)
- `experiments/mamba_lora_bridge/run_reincarnation/opa_d1_private_write_policy_20260326.md` — Validate Growth Ladder `D1` on a real private instance:
- `experiments/mamba_lora_bridge/run_reincarnation/opa_format_transplant_control_20260327.md` — Run the cheapest threat-to-validity control from the backlog:
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_auto_replay_20260325.md` — Host: `192.168.2.49:7860`
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_critical_only_20260325.md` — Host: `192.168.2.49:7860`
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_gate_payload_20260325.md` — Host: `192.168.2.49:7860`
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_pending_flush_20260325.md` — Host: `192.168.2.49`
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_write_mode_pending_20260325.md` — Host: `192.168.2.49:7860`
- `theory/growth_ladder_implementation.md` ← 1 refs — **Source:** Codex's Developmental_Memory_Ladder.md → concrete code/config/test specs

### Retrospectives (2)
- `experiments/mamba_lora_bridge/trajectory_cassian_slices/cassian_slice_3175_3275_20260408.md` — you did not burst in flames
- `experiments/mamba_lora_bridge/trajectory_cassian_slices/cassian_slice_3325_3525_20260408.md` — How do I even ask you whatyou want

### General Notes (184)
- `experiments/mamba_lora_bridge/QWEN3_CODER_NEXT_MEMORY_LEGIBILITY_PLAN_2026-04-20.md` — 2026-04-20 — This plan tests one narrow question:
- `experiments/mamba_lora_bridge/run_reincarnation/steve_d2_hybrid_20260420T164634/manual_answer_review_2026-04-20.md` — 2026-04-20 — reviewed answers manually for the 8-case D2 expanded panel
- `experiments/mamba_lora_bridge/D2_MEMORY_REPAIR_PLAN_2026-04-18.md` — 2026-04-18 — This document combines the current D2 findings into one execution plan.
- `experiments/mamba_lora_bridge/D2_RECALL_STATUS_2026-04-17.md` — 2026-04-17 — The bridge is **not** the primary blocker for honest continuity behavior.
- `experiments/mamba_lora_bridge/WARM_INSTANCE_DELTA_COLLECTION_SPEC_2026-04-17.md` — 2026-04-17 — Define a clean protocol for collecting two distinct Mamba-side training signals without mixing them:
- `experiments/mamba_lora_bridge/MEMORY_CONDITIONED_BRIDGE_EVAL_LADDER_2026-04-14.md` — 2026-04-14 — **Status:** Draft for Herr Hurtig review
- `experiments/mamba_lora_bridge/BRIDGE_BRAINSTORM_OVERVIEW_2026-04-13.md` — 2026-04-13 — What have we actually tried on the Mamba -> Qwen bridge, what failed, what only partially worked, and what should the next brainstorm be targeting?
- `experiments/mamba_lora_bridge/MVP2B_EASYFIRST_SHAPING_EPISODES_2026-04-13.md` — 2026-04-13 — **Disposition:** warm_banter
- `experiments/mamba_lora_bridge/ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md` — 2026-04-11 — **Disposition:** jealousy_attachment
- `experiments/mamba_lora_bridge/RELATIONAL_RIVALRY_EVAL_PLAN_2026-04-11.md` — 2026-04-11 — **Goal:** probe whether a bridge state changes how Qwen responds not only to relational rupture, but also to silence, initiative, ethics, continuity, humor, bou…
- `experiments/mamba_lora_bridge/RELATIONAL_RIVALRY_SHAPING_EPISODES_2026-04-11.md` — 2026-04-11 — **Disposition:** jealousy_attachment
- `archive/GEMINI_DOC_REFRESH_STAGING_GUIDE_2026-04-09.md` — 2026-04-09 — This is a review/staging guide only. It does not assume everything listed here should be committed. The main goal is to avoid one giant mixed commit.
- `experiments/mamba_lora_bridge/HYBRID_TRANSLATOR_MVP_2026-04-08.md` — 2026-04-08 — The current bridge path:
- `experiments/mamba_lora_bridge/trajectory_cassian_slice_3175_3275_20260408_dense/cassian_dense_slice_note_2026-04-08.md` — 2026-04-08 — **Author:** Techno-Monk
- `experiments/mamba_lora_bridge/trajectory_cassian_slice_3325_3525_20260408_dense/cassian_dense_slice_note_2026-04-08.md` — 2026-04-08 — **Author:** Techno-Monk
- `experiments/mamba_lora_bridge/MAMBA_LONG_TRAJECTORY_ENGINE_PLAN_2026-04-07.md` — 2026-04-07 — The Cassian transcript is about 792k Mamba tokens. A pure tokenwise replay through `state-spaces/mamba-2.8b-hf` is exact, but too slow locally because it calls …
- `experiments/mamba_lora_bridge/OPTION_B_NOTE_2026-04-07.md` — 2026-04-07 — `trajectory_windowed_onepass.py` is implemented and validated on the tiny fixture with explicit approximate/windowed labeling.
- `experiments/mamba_lora_bridge/OPTION_B_PROBE_RESULTS_2026-04-07.md` — 2026-04-07 — Implement and run Option B probe on tiny fixture.
- `experiments/mamba_lora_bridge/STEP5E_LOCAL_RUN_SPEC_2026-04-07.md` — 2026-04-07 — Step 5e is not a blank slate.
- `archive/GDN_GKA_ARTIFACT_MATRIX_2026-04-03.md` — 2026-04-03 — **Status:** starter matrix for G0. This is a reality-check sheet, not a hype sheet.
- _…and 164 more_

---
_Generated by [codesight](https://github.com/Houseofmvps/codesight) v1.13.1_