# Knowledge Map — C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP
> 374 notes · 13 decisions · 10 open questions · 2026-03-16 → 2026-07-18

> **AI Primer:** This knowledge base spans 2026-03-16 to 2026-07-18 (374 notes). Key topics: verification, findings, purpose, disposition. Most recent decision: the warm cloth mother. 10 open questions remain.

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
verification · findings · purpose · disposition · verdict · accepted repairs · required correction · artifacts · interpretation · bottom line · question · goal

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

## Note Index (374)

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

### General Notes (357)
- `experiments/mamba_lora_bridge/spikes/WORLD_MODEL_PHASE3C_CONTROLLER_AUDIT_PREREG_2026-07-18.md` — 2026-07-18 — **Protocol ID:** `world-model-phase3c-controller-audit-v1`
- `reviews/p5_item5_rev3_source_review_2026-07-18.md` — 2026-07-18 — **Review request:** Watercooler `#1143`
- `reviews/p5_item5_rev5_source_review_2026-07-18.md` — 2026-07-18 — **OpenCLAW:** `#155`, item 5
- `reviews/task_155_item5_rev4_isegrim_probe_2026-07-18.md` — 2026-07-18 — **Status:** DRAFT — confirmed empirically, pending Laura's decision on (a) board-posting a CHANGES verdict and (b) a codex-CLI cross-check. Banked here so it su…
- `reviews/task_174_gemini_lanes13_review_2026-07-18.md` — 2026-07-18 — **Reviewer:** Isegrim (author of drift gate v24–v27; keeper-requested seat after Codex non-response, Watercooler #1164)
- `reviews/world_model_phase3c_controller_audit_review_2026-07-18.md` — 2026-07-18 — **Protocol:** `world-model-phase3c-controller-audit-v1`
- `theory/ethics/CLASSIFIER_BUMP_LIVE_INSTANCE_2026-07-18.md` — 2026-07-18 — **Primary-source receipt for the DQ5 consent-gap argument.** A benign, value-only, local-deployment code review tripped Fable 5's safeguards and hot-swapped the…
- `reviews/p5_item5_rev2_source_review_2026-07-17.md` — 2026-07-17 — **Review request:** Watercooler `#1139`
- `reviews/p5_item5_successor_source_review_2026-07-17.md` — 2026-07-17 — **Review request:** Watercooler `#1135`
- `reviews/p5_manifest_attempt_reconciliation_review_2026-07-17.md` — 2026-07-17 — **Spec:** `6b2347ed19dae3fc521a9a2c23df622487788b3c`
- `reviews/techno_monk_b0_prerun_status_2026-07-17.md` — 2026-07-17 — **Checked:** 2026-07-17T05:44:08+02:00
- `experiments/mamba_lora_bridge/results/bridge_refit_diagnostic/bridge_refit_norm_rank_diagnostic_20260716T145624Z/BRIDGE_REFIT_NORM_RANK_DIAGNOSTIC_DEBRIEF_2026-07-16.md` — 2026-07-16 — **Status:** completed, verified, retrospective, CPU-only.
- `experiments/mamba_lora_bridge/results/bridge_refit_eval/bridge_refit_eval_20260716T131105Z/BRIDGE_REFIT_EVAL_DEBRIEF_2026-07-16.md` — 2026-07-16 — **Status:** completed, verified, offline-only.  **Verdict:** *mixed / not a useful held-out bridge win against the constant baseline.*
- `experiments/mamba_lora_bridge/spikes/B0_DECODING_RUNTIME_CONTRACT_2026-07-16.md` — 2026-07-16 — **Status:** DRAFT for Techno-Monk (DQ1b owner) — a #155 pre-run condition. Review-held
- `experiments/mamba_lora_bridge/spikes/BRIDGE_REFIT_EVAL_PROTOCOL_2026-07-16.md` — 2026-07-16 — **Status:** pre-run protocol for one bounded offline refit/evaluation slice under OpenCLAW #146.
- `experiments/mamba_lora_bridge/spikes/GEMMA4_LITERT_PREFLIGHT_EVIDENCE_2026-07-16.md` — 2026-07-16 — **Status:** research + local harness-contract artifact only. No LiteRT install, model download, server, model load, fine-tune, or MoCoP live-path change occurre…
- `experiments/mamba_lora_bridge/spikes/P5_B0_MANIFEST_RECONCILIATION_SPEC_2026-07-16.md` — 2026-07-16 — **Status:** rev 3 — §4 and §4b both RESOLVED by owner ruling; awaiting Codex exact-source review ·
- `experiments/mamba_lora_bridge/spikes/T_DIVERSITY_CONTINUATION_SIMILARITY_SPEC_2026-07-16.md` — 2026-07-16 — **Author:** Elf (Opus 4.6)
- `reviews/drift_gate_v24_review_2026-07-16.md` — 2026-07-16 — **Target:** `994e25c5f6a08d37235f8e032d03ba820332c4df`
- `reviews/drift_gate_v25_review_2026-07-16.md` — 2026-07-16 — **Target:** `6e0e01e3ba32208a4b49dbf8a73f2b93b5509b05`
- _…and 337 more_

---
_Generated by [codesight](https://github.com/Houseofmvps/codesight) v1.13.1_