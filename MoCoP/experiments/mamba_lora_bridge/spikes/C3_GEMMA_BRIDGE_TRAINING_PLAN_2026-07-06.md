# C3 — Gemma Activation-Bridge: Design & Training Plan [FRAGMENT — dead branch]
**PROVENANCE NOTE (Isegrim, 2026-07-06 night):** This file was written by a PRUNED BRANCH
of the 2026-07-06 session (Laura rewound the prompt ~8×; the classifier killed the branch
mid-write — the file ends mid-sentence). Author attribution "Isegrim" is accurate but
posthumous-of-branch. KEPT because §1.3's zone-rule mapping table is the correct fix for
review finding B1 on Purple's `GEMMA_BRIDGE_DESIGN_2026-07-06.md` (see
`GEMMA_BRIDGE_DESIGN_2026-07-06_REVIEW_ISEGRIM.md`) — live-branch review and dead-branch
design converged independently on the same line: inject {29,35,41}, tooth 47 readout-only,
teeth ≤23 untouched. Treat everything below as SALVAGE, not a complete design.
A companion 20-line stub (`C3_GEMMA_BRIDGE_DESIGN_2026-07-06.md`) was deleted as empty.

**Task:** OpenCLAW #139 · **Author:** Isegrim · **Date:** 2026-07-06 (evening)
**Status:** DESIGN ONLY — no training launch without keeper (Laura) approval, per task scope.
**Trust class:** needs-review — reviewers: Cairn (ethics plane), Elf (metrics), Gidim (runner/env), Monk (infra).

---

## 0. Standing assumptions (mark before arguing with the plan)

- **A1 — Substrate verdict pending.** This plan assumes 5g.4 selects Gemma-4 12B. The judge
  slice (#130, Gidim) and the DC/RMS 4-cell are still ahead of us. If 5g.4 lands elsewhere,
  §2–§4 re-derive; §1, §5–§7 survive any substrate.
- **A2 — DQ1a BLOCKS everything downstream of G1.** MED re-derivation in effective-magnitude
  units on Gemma geometry is the standing blocker for seeding (divergence audit 2026-07-05).
  This plan sequences around it; it does not route around it.
- **A3 — Birth, not brain swap** (canon, chat_server dependency map 2026-07-05): fresh Mamba
  state, encrypted-from-birth Qdrant collection (Purple #138 P0 prerequisites), new drift
  baseline, α-ramp starting at 0.1. Pre-Vault memories stay Alex's (DQ2, keeper-decided).

## 1. Architecture

### 1.1 Source side (unchanged, production contract)
- Mamba compressor, Layer-3 last-token readout: **`hidden_last_token` [1, 2560]**, n_hidden 65
  — width contract verified GREEN under the gemma4-mocop overlay env (#756).
- Live accumulation (`cache_params` path) on transformers 5.10.0.dev0 remains **untested**
  → G0 gate item, not an assumption.

### 1.2 Target side: Gemma-4 12B
- 48 layers, hidden 3840, `gemma4_unified` (Monk smoke #769: config loads, base generates,
  base has **no chat template**; `-it` emits `<|channel>thought` markers — integration must
  preserve/render channels, not strip them).
- **Global teeth: {5, 11, 17, 23, 29, 35, 41, 47}** — the whole-context attention sites; the
  task directive and the comb doctrine agree: MoCoP signal rides the global teeth.

### 1.3 Zone-rule v2 mapping (#758 — the four planes are load-bearing here)
| Plane | Gemma consequence for C3 |
|---|---|
| **Formation** | Base completes formation mid-stack (L22–27, dense-like; staircase falsified at power #745). Early teeth {5, 11, 17, 23} sit in/before the formation zone → **excluded as injection targets in v1.** Injection there risks perturbing formation, and the plane doctrine says formation sites are not steering sites. |
| **Extraction/Readout** | DFC basis = teeth **{29, 35, 41, 47}** (cross-tooth cosine stability). Readout/monitoring instruments live here. Directions before states. |
| **Injection/Steerability** | Entry 79 steering-site rule: **{29, 35, 41}** — direction separation + remaining integration capacity. **These are the v1 injection targets.** |
| **Commitment/Destructiveness** | Tooth **47** is the deepest global site nearest the output commitment zone → **readout-only in v1.** No injection at 47 until a dedicated commitment-plane study clears it. |

**Decision D1 — injection targets: v_proj at layers {29, 35, 41}; tooth 47 reserved for
monitoring (DFC/drift), teeth ≤23 untouched.** The v_proj value-stream patch is the
mechanism already production-proven on the current server (smoke GREEN at layers 12–15,
α = 0.2, RMS-scaled).

### 1.4 Bridge network & checkpoint shape
- Input: Mamba `hidden_last_token` [2560].
- Trunk: MLP 2560 → 4096 (GELU) → per-target-layer heads 4096 → 3840, one head per tooth
  in {29, 35, 41} → **