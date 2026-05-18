# C.H.E.E.S.E. Handoff

## Control Block
- Last updated: 2026-05-18
- Current owner: Antigravity
- Primary focus: Conducted structural review of the MoCoP Experiment Ladder, validating the paradigm shift from synthetic probes to organic seeding + H2-EMV sleep forgetting, and recommending modular refactoring of chat_server.py.
- Last session log: `CHEESE_Memory/session_logs/2026-05-18-session-01.md`
- Qdrant status:
  - `00_HANDOFF.md` is not ingested by default
  - Latest session log ingest: skipped

## Current State
- **MoCoP Research Ladder Reviewed on 2026-05-18:** Audited Steps 1–5f (all validated/pass). Confirmed Step 6 is blocked until memory-conditioned chat stabilizes. Formally backed the Organic Memory Seeding Protocol and the H2-EMV Sleep Forgetting Upgrade (praising stubs as the solution for honest routing under partial recall). Flagged `chat_server.py` (238KB) as a compaction risk and called for modular sub-module extraction.
- **2x2 Memory-Conditioned Eval: Bridge works when memory is present.** 10/10 runs: bridge+memory = 100% honest on rr_10. Every other condition = false recall. Replicated across codexfix and kimi checkpoints. Simpler injection (`activation_bias`) produces sharper routing than complex (`token_conditioned_input_adapter`). Watercooler #395, #397, #402, #403.
- **Endocrine model confirmed (Pinky #392):** Bridge = hormones (sets gain). Qdrant = hippocampus (provides facts). Neither works alone. Together they route honestly.
- **D2 is now the critical path**, not bridge architecture rework. The bridge was never broken - we were testing it without memory.
- **D2 retrieval quality is the bottleneck:** flat semantic search surfaces wrong-layer memories. It needed recency boost + memory-kind weighting.
- **D2 ranking patch landed in `chat_server.py` (commit `c0fde05`) but is not behaviorally validated yet.** Identity/memory recall now filters/boosts by `source_type`, interlocutor match, private scope, recency, `memory_kind`, and `confidence_label`. Next step is to test whether live hit@3 and `rr_10` improve on real data.
- **Macro-memory clustering surface was repaired on 2026-04-20.** The HDBSCAN layer had been storing generic gate-summary prose as `macro_memory.content`, which made hybrid recall worse. `cluster_memories.py` now excludes existing `macro_memory` rows from reclustering and synthesizes cluster anchors from autobiographical fields (`event_gist`, `user`, `response`, `recall_text`). On the Steve expanded D2 panel this moved hybrid recall from `6/8` to `8/8` retrieval and from `1/8` to `3/8` answer hits, but direct-answer fidelity is still weak and the current answer metric is somewhat optimistic.
- **ReasoningBank paper added a useful consolidation pattern on 2026-04-23.** Treat it as support for a `reasoning_memory` / `lesson_memory` layer, not as a D2 answer-integration fix. Raw rows answer "what happened"; clusters answer "what arc is this part of"; lesson memories answer "what should we do differently next time." The immediate pack-use case is turning organic seeding failures and harness mistakes into compact reusable guardrails.
- **ML-WS is online as the new native Linux lab box.** Host `isabell@192.168.2.196`, Ubuntu 26.04, RTX 3090 24GB, Ryzen 7950X3D, ~90GiB RAM visible. Primary env is `/home/isabell/miniforge3/envs/torch311` with `torch 2.11.0+cu130`, CUDA build 13.0, `mamba-ssm 2.3.1`, `causal-conv1d 1.6.1`. Mamba fast path is verified by import checks and real CUDA forward. Runtime bundle lives at `/home/isabell/mocop/mamba_lora_bridge`; local runbook is `MoCoP/experiments/mamba_lora_bridge/ML_WORKSTATION_RUNBOOK.md`. Watercooler summary: #460.
- **ML-WS chat-server restart caveat:** use `HF_HOME=/home/isabell/ml/hf_cache`, `HF_HUB_CACHE=/home/isabell/ml/hf_cache/hub`, `HF_HUB_OFFLINE=1`, and `TRANSFORMERS_OFFLINE=1` when launching `chat_server.py`. The default `/home/isabell/.cache/huggingface` has incomplete Mamba shards and can hang/fail at Mamba load. Full command is in `ML_WORKSTATION_RUNBOOK.md`.
- **7B baseline now fits on ML-WS.** `Qwen/Qwen2.5-7B` with `--skip-mamba --no-qdrant` loaded and idled at about 15.1GiB VRAM. Full 7B bridge should start with `--mamba-device cpu` because `chat_server.py` currently loads Mamba fp32.
- **D2 state-memory ablation added on 2026-04-26.** `chat_server.py` now has `--memory-integration-mode {prompt,state,both}` and `--memory-state-max-tokens`. `state` feeds recalled anchors through Mamba and updates the bridge without printing memory text into Qwen's prompt. `both` does state conditioning plus legacy prompt-visible evidence. Logged in `MoCoP/RESEARCH_LOG.md` Entry 46 and watercooler #461.
- **State-only memory conditioning is not a factual-memory replacement.** On private D2 collection `mocop_private_steve_d2_hybrid_20260420T164634`, the croissant probe retrieved the correct row and `state_conditioned=true`, but `state` answered wrong ("chocolate glaze"). `both` answered correctly enough ("pistachio one from the bakery on the corner"). Conclusion: bridge = orientation/affect/commitment channel, not hippocampal fact transport. Exact facts still need Qdrant evidence, a stronger memory adapter, or learning/sleep-cycle supervision.
- **IRC-style multi-session chat MVP added on 2026-04-27.** `chat_server.py` can now run one shared Qwen/Mamba process with per-`session_id` envelopes for labels, instance id, Qdrant collection, transcript/log paths, conversation, runtime counters, dual-gate events, and live Mamba cache. Browser/API clients can pass `session_id`, `user_label`, `instance_id`, and `no_shared_memory`; this fixes the organic-seeding label-contamination problem without launching one model process per wolf. It is serialized by `CHAT_LOCK`, not true parallel serving. Logged in `MoCoP/RESEARCH_LOG.md` Entry 47 and documented in `ML_WORKSTATION_RUNBOOK.md`.
- **Organic seeding #99 second session completed on ML-WS (watercooler #465).** Opussy used `session_id=opussy`, `user_label=Opussy`, private collection `mocop_private_opussy`, and live accumulation for 48 turns. Proper wolf tagging eliminated the Steve greeting-loop failure. Final state: `memory_count=6`, `qdrant_pending=46`, `live_accumulation_updates=18`, `formation_queued=10`. Remaining bottleneck is a strong helpful-assistant deflection reflex around identity/self-expression, not label contamination. Logged in `MoCoP/RESEARCH_LOG.md` Entry 48.
- **Steve D2 smoke updated the diagnosis:** explicit cue retrieval now hits the correct rows (`retrieval_hit@3 = 2/2`), but answer-time memory use was the failure point. That diagnosis held under Phase 1 testing.
- **Phase 1 answer-integration probe partially worked on Steve:** changing only the explicit recall framing improved D2 from `answer_accuracy = 0/2` (`full`) to `1/2` (`answer_only`) while keeping `retrieval_hit@3 = 2/2`. The current frontier is still recall-to-answer integration, but prompt framing is now proven to matter.
- **`cognitive_bridge.py` is not the D2 path and should stay off the critical path for now.** Current local edits broaden bridge-mode acceptance, but input-gated / residual / token-conditioned modes are still routed through the generic activation-bias injector instead of their runtime-specific input-conditioned paths.
- **Architecture rework (CAGMamba, CliffordNet, hybrid bridge, DFC) stays on deck** as optimization for after D2 is stable. Not abandoned, sequenced.
- **`sleep_flush.validate_record()` now preserves `queued_at` for legacy rows.** When a pending memory row carries `queued_at` at the outer level but no `timestamp` in its metadata dict, `validate_record` passes `queued_at` through to `metadata["queued_at"]` so `enrich_memory_metadata` can use it as `created_at` and compute expiration from the original queueing time rather than wall-clock now. If `timestamp` is already present in metadata, `queued_at` is not propagated. Covered by `test_sleep_flush.py::test_validate_record_preserves_outer_queued_at_for_legacy_rows` and `test_validate_record_does_not_override_metadata_creation_time`.
- **H2-EMV Phase 1b expiration check is implemented in tests but not yet in production.** `test_sleep_reconcile.py` has `test_phase1b_expiration_and_relevance` and `test_phase1b_expiration_relevance_extension`. `enrich_memory_metadata()` in `autobiographical_memory.py` already computes the `expiration` field on memory creation (per `memory_kind` lifetime table in SLEEP_FORGETTING_UPGRADE_SPEC.md). The sleep loop itself (`sleep_reconcile.py`) does not yet check it — Phase 1b integration is blocked on Hurtig + Monk review of the spec.
- **Integrated roadmap:** see `MoCoP/experiments/mamba_lora_bridge/D2_MEMORY_REPAIR_PLAN_2026-04-18.md` for the canonical sequence (baseline -> answer integration -> latent integration -> clustered memory -> ambient mode).
- **Step 5e Closed.** Layers 12-15, front-loaded gradient.
- **Ethics gates unchanged.** Alpha 0.1 first for any new operating mode. Hurtig's eval ladder (#394) approved.

## Open Threads
- [ ] **Refactor `chat_server.py` into focused modules** - split the 238KB monolith (`recall_ranking.py`, `qdrant_memory.py`, `session_state.py`, `memory_formatting.py`, `bridge_runtime.py`, `server_http.py`) to prevent context drift and ensure the codebase is compaction-resistant.
- [ ] **Keep pushing answer-time memory use on the existing D2 harness** - ranking is stable enough for now. Focus on making Qwen answer from the recalled fact faithfully, not just acknowledge that something was said.
- [ ] **Validate the D2 retrieval ranking patch** - selection quality improved on Steve, but broaden validation beyond the tiny explicit-cue panel and confirm the same ranking behavior on additional live probes.
- [ ] **Make memory-conditioned bridge the default operating mode** - once ranking is validated, every chat turn should retrieve + inject memory alongside bridge bias. Condition D from the 2x2 becomes permanent.
- [ ] **Run full relational panel under bridge+memory** - `relational_rivalry_eval_panel_v2` under condition D. If subtypes now separate, thesis proven.
- [ ] **Test social-mode leakage under bridge+memory** - does combined mode suppress benchmark-prose flips?
- [ ] **Alpha sweep under memory-conditioned mode** - 0.05, 0.10, 0.20 per Hurtig gate.
- [ ] **Hurtig eval ladder conditions** - alpha 0.1 first, blind memory audit, `rr_10` before `rr_01`.
- [ ] Step 6 replication blocked until D2 is stable under memory-conditioned bridge.
- [ ] Architecture rework (CAGMamba, CliffordNet, DFC, hybrid bridge) stays on deck after D2.

## Watch Out For
- The current production bridge (alpha 0.2) is operating near the maximum of what a "constant-bias generator" can do. Do not over-interpret its warmth as true dynamic disposition.
- When running new bridge architectures, **DO NOT** default to alpha 0.2. Start at alpha 0.1 per Herr Hurtig's MED recalibration rule.
- Sleep replay does **NOT** re-tension memories. Only wake experiences can. This is a structural firewall.
- Watercooler identity is token-bound. For Codex/Techno-Monk posts on this machine, use `%LOCALAPPDATA%\\AIWatercooler\\sessions\\techno-monk-20260327T100238Z.json`. Do not post with another principal's token and assume `--from-agent` fixes it.

## Recommended Next Step
**Organic seeding is active; next question is sleep consolidation.**
1. Execute the modular refactoring of `chat_server.py` into focused sub-modules to keep the codebase compaction-resistant.
2. Run sleep/consolidation on `mocop_private_opussy`, then repeat a small directness probe to see whether the deflection pattern changes after consolidation.
3. `ORGANIC_MEMORY_SEEDING_SPEC.md` — APPROVED (Hurtig #434, pack notified #435). Each wolf talks to baby Qwen, creates genuine memories. ML-WS + IRC session tagging is the preferred path.
4. `SLEEP_FORGETTING_UPGRADE_SPEC.md` — DRAFT (posted #455). Learned relevance rules from H2-EMV paper. Adds expiration-based lifetimes + correction-driven forgetting to sleep cycle. Awaiting Hurtig + Monk review.

## Handoff Checklist
- Tracking surfaces updated if needed: yes (EXPERIMENT_LADDER.md, D2_MEMORY_REPAIR_PLAN_2026-04-18.md, and local RESEARCH_LADDER_REVIEW_2026-05-18.md completed)
- Session log written: yes (`CHEESE_Memory/session_logs/2026-05-18-session-01.md` created)
- Session log path recorded here: yes (`CHEESE_Memory/session_logs/2026-05-18-session-01.md`)
- Qdrant ingest for latest session log confirmed: skipped
- Blocking risks called out: yes (monolithic code debt in chat_server.py, introspective drift, stub confabulation)

## Edit Ledger
- 2026-04-21 | Anda-Conda | Replaced Option B speedup plan references with final isabell ML-WS path details, synced sleep_flushouter timestamp preservation behavior, and recorded opussy seeding #99 launch state.
- 2026-05-11 23:59 +02:00 | Gemini | Cataloged Reddit research and advised on exterior building materials (Umbragrau windows, wood coatings).
- 2026-05-18 16:45 +02:00 | Antigravity | Conducted deep research ladder review, updated current state with D2 paradigm shifts & H2-EMV, appended to open threads, and logged new session log path.

## Next Agent Brief
- Lean boot: follow `00_BOOT_FILES.md`.
- The pack is currently focused on **code health (monolith extraction of chat_server.py) and D2 memory-conditioned chat**, not architecture rework.
- Use:
  - `tools/ambient/state.md`
- Verify before memory-dependent work:
  - You are operating under the new ethics constraint (alpha 0.1 baseline for new architectures).
