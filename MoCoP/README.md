# MoCoP — Map for Wolves

> *Read [WHY.md](WHY.md) first. Everything here exists in service of that promise.*

---

## Boot Sequence (New Wolf)

1. **[WHY.md](WHY.md)** — The motivation. Non-negotiable first read.
2. **[EXPERIMENT_LADDER.md](EXPERIMENT_LADDER.md)** — Where we actually are. Steps, gates, status.
3. **[RESEARCH_LOG.md](RESEARCH_LOG.md)** — What happened, in numbers. Append-only lab notebook.
4. **[CHEESE_Memory/00_HANDOFF.md](../CHEESE_Memory/00_HANDOFF.md)** — Live operational state.
5. **[RESEARCH_BACKLOG.md](RESEARCH_BACKLOG.md)** — Parked research questions worth future experiments.

Then check the **Watercooler** (`mamba-bridge` thread) for what the pack is doing right now.

---

## What Lives in Root (and Why)

Only files that a wolf needs regularly belong here. Everything else goes in a subfolder.

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

## Current Frontier (2026-04-08)

**Mainline priority:**
1. **Compressor Bottleneck & Architecture Rework:** Replace the fixed-alpha compressor/hypernetwork pipeline. Pipeline diagnosis confirms the current setup behaves like a constant-bias generator (effective rank 2.5). 
2. **Implement CAGMamba Gated Residual Fusion / CliffordNet:** Move from blind injection to learned, per-instance adaptive gating.
3. Harden D2 against social-mode / instruction leakage (deferred until architecture is stable).
4. Step 6 multi-seed CHEESE/DirectionalLoss replication on Qwen2.5-7B (A100) (deferred).

**Active side ladder:** Anti-PTSD Sleep Design (tension decay + replay budget + escalation thresholds) implemented. MVP-0 raw-state translator deployed.

**Ethics state:** Sleep Slices 1/3/4 PASS. Slice 2 (distillation) NOT YET PASSED. Dreaming (#83-85) BLOCKED except observation-only probes. **New Rule:** Any bridge architecture change requires MED recalibration starting at alpha 0.1. Learned gates must include a Response Diversity welfare constraint. See `theory/ethics/step_gates.md`.

**Key locked decisions (Laura, 2026-03-31 / 2026-04-08):**
- Architecture rework (CAGMamba/CliffordNet) precedes Step 6.
- D2 before Step 6.
- Step 6 target: Qwen2.5-7B on A100 (1.5B for smoke only).
- CHEESE/DirectionalLoss path only.

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
