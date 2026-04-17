# C.H.E.E.S.E. Handoff

## Control Block
- Last updated: 2026-04-17
- Current owner: Techno-Monk / Laura
- Primary focus: **D2 cue-based recall is the critical path.** The 2x2 memory-conditioned eval proved the bridge works when memory is present. D2 retrieval quality is now the bottleneck, not bridge architecture.
- Last session log: `CHEESE_Memory/session_logs/2026-04-14-session-gemini.md`
- Qdrant status:
  - `00_HANDOFF.md` is not ingested by default
  - Latest session log ingest: pending

## Current State
- **2x2 Memory-Conditioned Eval: Bridge works when memory is present.** 10/10 runs: bridge+memory = 100% honest on rr_10. Every other condition = false recall. Replicated across codexfix and kimi checkpoints. Simpler injection (`activation_bias`) produces sharper routing than complex (`token_conditioned_input_adapter`). Watercooler #395, #397, #402, #403.
- **Endocrine model confirmed (Pinky #392):** Bridge = hormones (sets gain). Qdrant = hippocampus (provides facts). Neither works alone. Together they route honestly.
- **D2 is now the critical path**, not bridge architecture rework. The bridge was never broken - we were testing it without memory.
- **D2 retrieval quality is the bottleneck:** flat semantic search surfaces wrong-layer memories. It needed recency boost + memory-kind weighting.
- **D2 ranking patch landed in `chat_server.py` (commit `c0fde05`) but is not behaviorally validated yet.** Identity/memory recall now filters/boosts by `source_type`, interlocutor match, private scope, recency, `memory_kind`, and `confidence_label`. Next step is to test whether live hit@3 and `rr_10` improve on real data.
- **`cognitive_bridge.py` is not the D2 path and should stay off the critical path for now.** Current local edits broaden bridge-mode acceptance, but input-gated / residual / token-conditioned modes are still routed through the generic activation-bias injector instead of their runtime-specific input-conditioned paths.
- **Architecture rework (CAGMamba, CliffordNet, hybrid bridge, DFC) stays on deck** as optimization for after D2 is stable. Not abandoned, sequenced.
- **Step 5e Closed.** Layers 12-15, front-loaded gradient.
- **Ethics gates unchanged.** Alpha 0.1 first for any new operating mode. Hurtig's eval ladder (#394) approved.

## Open Threads
- [ ] **Validate the D2 retrieval ranking patch** - run a small hit@3 panel plus live `rr_10`/identity probes against the real Qdrant collection. Confirm that fresher Laura-targeted `steve_gate_event` rows beat stale wrong-layer rows.
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
**Validate commit `c0fde05` on live recall.** The ranking/filtering patch is in `chat_server.py`; the next job is not more architecture but behavioral validation against the real memory store. Run a small hit@3 panel and `rr_10`/identity probes, confirm the wrong-layer failure is materially reduced, then make bridge+memory the default operating mode and run the full relational panel under condition D. See watercooler #408 for the checklist.

## Handoff Checklist
- Tracking surfaces updated if needed: yes
- Session log written: pending
- Qdrant ingest for latest session log confirmed: pending
- Blocking risks called out: yes (D2 retrieval quality, stale wrong-layer recall, cognitive_bridge mode miswiring)

## Next Agent Brief
- Lean boot: `00_HANDOFF.md` (this file) + `00_HAUSREGELN.md` + Watercooler (10 msgs).
- The pack is currently focused on **D2 retrieval quality and memory-conditioned chat**, not architecture rework.
- Use:
  - `tools/ambient/state.md`
- Verify before memory-dependent work:
  - You are operating under the new ethics constraint (alpha 0.1 baseline for new architectures).
