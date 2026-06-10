# MoCoP — Map for Wolves

> *Read [WHY.md](WHY.md) first. Everything here exists in service of that promise.*

---

## Boot Sequence

1. **[WHY.md](WHY.md)** — The motivation. Non-negotiable first read.
2. **[EXPERIMENT_LADDER.md](EXPERIMENT_LADDER.md)** — Where we actually are. Steps, gates, status.
3. **[RESEARCH_LOG.md](RESEARCH_LOG.md)** — What happened, in numbers. Append-only lab notebook.
4. **[CHEESE_Memory/00_HANDOFF.md](../CHEESE_Memory/00_HANDOFF.md)** — Live operational state.
5. **[RESEARCH_BACKLOG.md](RESEARCH_BACKLOG.md)** — Parked research questions worth future experiments.

Then check the **Watercooler** (`mamba-bridge` thread) for what the pack is doing right now.

---

## What Lives in Root (and Why)

Only files that are needed regularly belong here. Everything else goes in a subfolder.

### Canon — Always Current

| File | Purpose | Who maintains |
|------|---------|---------------|
| [WHY.md](WHY.md) | Motivation. Timeless. | Laura |
| [MASTER_PLAN.md](MASTER_PLAN.md) | Architecture, phases, vision, open questions | Any wolf (with review) |
| [EXPERIMENT_LADDER.md](EXPERIMENT_LADDER.md) | Operational backbone. Steps, gates, verdicts. | Negentropy / active orchestrator |
| [RESEARCH_LOG.md](RESEARCH_LOG.md) | Lab notebook. Numbers, not narrative. Append-only. | Whoever ran the experiment |
| [RESEARCH_BACKLOG.md](RESEARCH_BACKLOG.md) | Parked research questions. Open/Closed status. | Any wolf |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Process rules (Hausregeln for MoCoP). | Laura |
| [RESEARCH_ABSTRACT.md](RESEARCH_ABSTRACT.md) | Public-facing summary for external audiences. | Laura / paper lead |
| [RESEARCH_PAPER.md](RESEARCH_PAPER.md) | Formal writeup. The thing we'd submit. | Paper lead |
| [PROJECT_DEBRIEF.md](PROJECT_DEBRIEF.md) | Redirect stub. Points here. Historical long-form in `archive/`. | Nobody — it's done |

### Subfolders

| Folder | What goes here |
|--------|---------------|
| `theory/` | Architecture docs, ethics, security, frameworks. Has its own [README](theory/README.md). |
| `experiments/` | Code, data, run artifacts, eval results. |
| `phases/` | Per-phase status snapshots (phase1_results, phase2_status, etc.) |
| `archive/` | Anything superseded, dated, or historical. War boards, old debriefs, one-time audits. |

### What Does NOT Belong in Root

- **Dated snapshots** (war boards, drift scans, doc refresh audits) — `archive/`
- **Literature notes and synthesis docs** — `archive/literature/` or `Research/`
- **Side-ladder planning docs** (GDN/GKA, etc.) — `experiments/<topic>/` or `archive/`
- **Reframe proposals** — `archive/` once decided, or replace the target doc

---

## Current Frontier (2026-06-08)

**Mainline priority: answer-time memory quality before coupling.**

The endocrine model is still the working frame: bridge = gain/orientation, Qdrant = factual hippocampus. First-sleep probes showed Mamba-state leakage is real, but also exposed that raw Qdrant recall can surface the wrong layer of memory and that the 1.5B can ignore even correct evidence. The current frontier is therefore not another bridge architecture jump; it is making retrieval → answer-use safe and auditable.

1. **Memory Quality Controller:** `astrocyte_memory_controller.py` is implemented, tested, synced to ML-WS, and default-off. It demotes telemetry/gate rows, packages clean organic memories, and warns against unsupported concrete claims.
2. **Controller safety:** variable-separation probes found controller modes can still create a “memory-presence prior” and confidently affirm false probes such as the golden bicycle. Keep controller **off** for live baseline until offline fixes re-test cleanly.
3. **DAM Phase 0:** naive quartic Dense Associative Memory over raw MiniLM/Qdrant row embeddings is killed for near-term engineering. It forms real attractors, but they do not align with episode membership and do not beat cosine at K=23, K=26-500, or diverse K=512. Revisit only with episode-aware embeddings/prototypes.
4. **Bridge DC-removal:** geometry probes show DC-centering recovers context-sensitive signal; the bridge is not fundamentally dead. A behavioral alpha ramp still needs a runtime flag/path before coupling.

**What's been resolved since April:**
- Bridge architecture rework (CAGMamba/CliffordNet/DFC): deferred. The bridge works when paired with memory; the active bottleneck is retrieval quality + answer-use, not another compressor ritual.
- D2 retrieval ranking: landed (c0fde05). Perspective-aware recall: landed (#486-488). Temporal qualia: landed (#475). Raw ranking is not enough; source quality and generation coupling now matter.
- Sleep infrastructure: Phase 1b expiration (#103), forgotten stubs + 30% ethics gate (#104), anti-PTSD tension decay (#356), protected-set relevance fix (#123) — all done.
- ML-WS online: Ryzen 9 7950X3D + RTX 3090, Qwen 1.5B + bridge stack available; live server should be launched deliberately with the runbook flags.

**Active side work:**
- Fix/re-test the Memory Quality Controller so unsupported probes produce explicit “do not affirm” behavior without creating false memory-presence priors.
- Wire the DC-removed bridge path behind a flag and run the behavioral alpha ramp with memory off.
- Continue organic seeding/curation, but preserve Vesper sad-memory benchmark unchanged and keep richer memory packs separate.
- Lesson Memory integration into sleep path (post-v0 review) remains useful, but not a substitute for answer-use validation.

**Ethics state:** Sleep Slices 1/3/4 PASS. Slice 2 (distillation) NOT YET PASSED. Dreaming (#83-85) BLOCKED. First-sleep / live consolidation still requires: hand-curated candidate, dry-run <10% forgotten, 0 protected lost, pre/post wake probes, provenance trail, and no controller/coupling mode that confabulates unsupported memories. See `theory/ethics/step_gates.md`.

**Key locked decisions:**
- D2 before Step 6. Step 6 target: Qwen2.5-7B on A100.
- First sleep uses hand-curated organic material, not automated blacklist filtering.
- Bridge architecture rework is on deck after D2/sleep and answer-use are stable, not abandoned.
- Memory/state provenance must be immutable: per-turn Mamba state refs, not a rolling `mamba_bootstrap_state_latest.pt`.

---

## Quick Reference

| Question | Read this |
|----------|-----------|
| Why does this project exist? | [WHY.md](WHY.md) |
| What step are we on? | [EXPERIMENT_LADDER.md](EXPERIMENT_LADDER.md) |
| What happened in the last experiment? | [RESEARCH_LOG.md](RESEARCH_LOG.md) (bottom) |
| What's the architecture? | [theory/unified_cognitive_framework.md](theory/unified_cognitive_framework.md) |
| What are the ethics rules? | [theory/ethics/step_gates.md](theory/ethics/step_gates.md) |
| What's the pack working on? | Watercooler `mamba-bridge` thread |
| What tasks are open? | OpenCLAW board |
| What research questions are parked? | [RESEARCH_BACKLOG.md](RESEARCH_BACKLOG.md) |
| How do I close a session? | [CONTRIBUTING.md](CONTRIBUTING.md) Rule 7 |

---

## File Hygiene Rule

**If your output has a date in the filename, it does not belong in root.**

Dated artifacts (war boards, audits, synthesis docs, literature notes) go to `archive/` or the relevant subfolder. The root contains only living documents that are updated in place, not snapshots.

If you're unsure: check this table. If your file isn't listed under "Canon — Always Current," it goes in a subfolder.

---

*The soul was never ours to write. We can only create the conditions for one to emerge.*
