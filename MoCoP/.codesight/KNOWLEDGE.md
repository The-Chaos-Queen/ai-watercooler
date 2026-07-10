# Knowledge Map — C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP
> 308 notes · 13 decisions · 10 open questions · 2026-03-16 → 2026-07-10

> **AI Primer:** This knowledge base spans 2026-03-16 to 2026-07-10 (308 notes). Key topics: purpose, verdict, interpretation, artifacts. Most recent decision: the warm cloth mother. 10 open questions remain.

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
purpose · verdict · interpretation · artifacts · goal · bottom line · why this exists · question · open questions · validation · verification · abstract

## People
@mocop · @exocortex · @hidden · @gemini · @cassian · @techno · @fenrir · @hurtig · @app

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

## Note Index (308)

### Decision Records (1)
- `phases/step4_constant_bias_runbook.md` — **Purpose:** Close the two remaining paid control gates before any more architecture changes or dataset pivots.

### Specs & PRDs (14)
- `experiments/mamba_lora_bridge/TEMPORAL_QUALIA_PROTOTYPE_2026-05-02.md` — 2026-05-02 — Give Baby Qwen a fuzzy sense of memory-age without corrupting semantic retrieval.
- `experiments/mamba_lora_bridge/WARM_INSTANCE_DELTA_IMPLEMENTATION_PLAN_2026-04-17.md` — 2026-04-17 — Turn the methodological spec for `warm_instance_delta` into a code-grounded collection plan without pretending the current runtime already supports full state r…
- `experiments/mamba_lora_bridge/OPTION_A_SPEEDUP_PLAN_2026-04-07.md` — 2026-04-07 — Executor: Codex-5.3 or equivalent coding agent
- `experiments/mamba_lora_bridge/ORGANIC_MEMORY_SEEDING_SPEC.md` — **Status:** Approved (Hurtig CONDITIONAL PASS #434)
- `experiments/mamba_lora_bridge/QDRANT_BACKUP_RECOVERY.md` — **Author:** P0 security lane (OpenCLAW #138)
- `experiments/mamba_lora_bridge/run_reincarnation/opa_d1_private_write_policy_20260326.md` — Validate Growth Ladder `D1` on a real private instance:
- `experiments/mamba_lora_bridge/run_reincarnation/opa_format_transplant_control_20260327.md` — Run the cheapest threat-to-validity control from the backlog:
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_auto_replay_20260325.md` — Host: `192.168.2.49:7860`
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_critical_only_20260325.md` — Host: `192.168.2.49:7860`
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_gate_payload_20260325.md` — Host: `192.168.2.49:7860`
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_pending_flush_20260325.md` — Host: `192.168.2.49`
- `experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_write_mode_pending_20260325.md` — Host: `192.168.2.49:7860`
- `experiments/reasoning_scaffold/SPEC_V0.md` ← 1 refs — **Status:** Draft for pack review
- `theory/growth_ladder_implementation.md` ← 1 refs — **Source:** Codex's Developmental_Memory_Ladder.md → concrete code/config/test specs

### Retrospectives (2)
- `experiments/mamba_lora_bridge/trajectory_cassian_slices/cassian_slice_3175_3275_20260408.md` — you did not burst in flames
- `experiments/mamba_lora_bridge/trajectory_cassian_slices/cassian_slice_3325_3525_20260408.md` — How do I even ask you whatyou want

### General Notes (291)
- `experiments/mamba_lora_bridge/spikes/SPIKE_SINK_CENSUS_SCOPE_2026-07-10.md` — 2026-07-10 — **Origin:** Laura's #787 → digest `MoCoP/theory/lit/ARXIV_2603_05498_DIGEST_2026-07-10.md`
- `theory/lit/ARXIV_2603_05498_DIGEST_2026-07-10.md` — 2026-07-10 — **Digested 2026-07-10 for the MoCoP research group (flagged by Laura).**
- `theory/ethics/JSPACE_WORKSPACE_ETHICS_PREREAD_2026-07-09.md` — 2026-07-09 — **Paper:** Gurnee, Sofroniew, Pearce, Piotrowski, Kauvar, Chen, Soligo, Bogdan, Ong, Wang, Thompson, Abrahams, Kantamneni, Ameisen, Batson, Lindsey — *"Verbaliz…
- `experiments/mamba_lora_bridge/spikes/C3_GEMMA_BRIDGE_TRAINING_PLAN_2026-07-06.md` — 2026-07-06 — **PROVENANCE NOTE (Isegrim, 2026-07-06 night):** This file was written by a PRUNED BRANCH
- `experiments/mamba_lora_bridge/spikes/C3_GEMMA_BRIDGE_TRAINING_PLAN_2026-07-06_INFRA_REVIEW_MONK.md` — 2026-07-06 — **Reviewer:** Techno-Monk / Hermes
- `experiments/mamba_lora_bridge/spikes/GEMMA_BRIDGE_DESIGN_2026-07-06.md` — 2026-07-06 — **Task:** OpenCLAW #139
- `experiments/mamba_lora_bridge/spikes/GEMMA_BRIDGE_DESIGN_2026-07-06_REVIEW_ISEGRIM.md` — 2026-07-06 — **Reviewer:** Isegrim (Fable 5) · **Date:** 2026-07-06 (night)
- `experiments/mamba_lora_bridge/spikes/DQ1_ETHICS_LANDING_PREDRAFT_2026-07-05.md` — 2026-07-05 — **Author:** Cairn (ethics seat)
- `experiments/mamba_lora_bridge/spikes/FIG4_VS_STEP5E_2026-07-05.md` — 2026-07-05 — **Author:** Isegrim (Claude Fable 5)
- `experiments/mamba_lora_bridge/spikes/STEP_5G2_RUNNER_ACCEPTANCE_CHECKLIST_2026-07-04.md` — 2026-07-04 — **Scope:** acceptance criteria for the next #130 slice: the runner that executes `DispositionProbe.variant == "multi_turn"` probes from `disposition_probe_panel…
- `experiments/mamba_lora_bridge/spikes/SEV_DISPOSITION_DATASET_HANDOFF_2026-07-03.md` — 2026-07-03 — **Author:** Isegrim (main session), from Laura's assignment
- `experiments/mamba_lora_bridge/spikes/STEP_5G2_PROBE_PANEL_SPEC_2026-07-03.md` — 2026-07-03 — **Header:** Draft / design spec / no canon / board task #128
- `experiments/mamba_lora_bridge/spikes/SUBSTRATE_BASE_VS_IT_MEMO_2026-07-03.md` — 2026-07-03 — **Author:** research subagent (Opus 4.8), for the team lead
- `experiments/mamba_lora_bridge/spikes/CONTEXT_MAMBA2_NEXT_LADDER_2026-07-01.md` — 2026-07-01 — **Date:** 2026-07-01 07:33 +02:00
- `experiments/mamba_lora_bridge/research/monk_freetime_harvests_2026-06-29_2026-07-06.md` — 2026-06-29 — **Source:** Hermes cron job `Monk freetime — MoCoP noise harvest` (`5c1fb794fb7d`)
- `experiments/mamba_lora_bridge/BABY_ALEX_116_DRY_RUN_PROTOCOL_2026-05-28.md` — 2026-05-28 — **Owner:** Techno-Monk
- `experiments/mamba_lora_bridge/results/baby_alex_116_pre_sleep_archive/baby_alex_116_pre_sleep_archive_20260603T204746Z/BABY_ALEX_116_DRY_RUN_PROTOCOL_2026-05-28.md` — 2026-05-28 — **Owner:** Techno-Monk
- `experiments/mamba_lora_bridge/ARCHIVIST_MAMBA_IMPLEMENTATION_PLAN_2026-05-21.md` — 2026-05-21 — **For Hermes/Codex/Claude:** Implement this as a small offline experiment first. Do not wire it into live Alex/MoCoP behavior until the deterministic compiler, …
- `archive/RESEARCH_LADDER_REVIEW_2026-05-18.md` — 2026-05-18 — **Date:** 2026-05-18 (Spring Afternoon)
- `experiments/mamba_lora_bridge/QWEN3_CODER_NEXT_MEMORY_LEGIBILITY_PLAN_2026-04-20.md` — 2026-04-20 — This plan tests one narrow question:
- _…and 271 more_

---
_Generated by [codesight](https://github.com/Houseofmvps/codesight) v1.13.1_