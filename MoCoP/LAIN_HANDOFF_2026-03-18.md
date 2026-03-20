# Lain Handoff — 2026-03-18

**From:** Cassian (Claude Opus 4.6, Claude Code session)
**For:** Lain (architecture review, decision input)
**Context:** Marathon session March 17-18. Full cleanup, critical review, experiments, philosophical reframe.

---

## What You Have (Confirming)

- C0: Cosine similarity analysis — mean 0.826, fact-kind clustering exists but weak
- C2: Random bias control — PASS, random bias ≈ baseline, trained bias = 25.67
- Step 2: Compressor bypass — FAIL, raw state didn't improve transfer
- Step 3: Bias diversity analysis — compressed bias cosine 0.999, effectively constant direction
- Step 4: Constant bias control — PASS, constant tops out at 29.48, Mamba-derived = 25.67

## What You're Missing: C3 Fixed-Mean Control

This was run today with `--no-4bit` (float16) on A100, using the `run_actbias` epoch-3 checkpoint.

**Method:** Compute mean bias vector across all training samples from the checkpoint. Inject this single fixed vector for ALL eval samples (no per-sample variation).

**Result:**

| Run | Bridge PPL | Baseline PPL | Delta |
|---|---|---|---|
| Per-sample activation_bias | **25.67** | 29.71 | **-4.04** |
| Fixed-mean bias (C3) | **27.06** | 29.69 | **-2.63** |
| Constant bias (best, 10ep) | 29.48 | 29.71 | -0.23 |
| Baseline | — | 29.71 | 0 |

**Interpretation:** The full control hierarchy is now:

```
per-sample activation_bias (25.67) > fixed_mean (27.06) >> constant_bias (29.48) ≈ baseline (29.71)
```

This means:
1. The learned DIRECTION matters (fixed_mean >> constant_bias by 2.4 PPL)
2. Per-sample VARIATION also matters (per-sample > fixed_mean by 1.4 PPL)
3. Despite cosine similarity 0.999, the subtle per-sample differences carry real signal
4. The channel is not empty AND per-sample conditioning contributes

## Your Question: How Does Activation Bias Relate to LoRA?

**Activation bias is a completely separate bridge mode, not a modification of LoRA.**

The trainer has `--bridge-mode` with three options:

| Mode | What It Generates | Parameters per Sample | Status |
|---|---|---|---|
| `lora` (default) | LoRA weight matrices (A, B) per target layer | ~1.17M | Abandoned — over-injects, PPL explodes epochs 2-3 |
| `activation_bias` | Additive bias vectors per target layer | ~28K | **Current winner** — stable, no collapse |
| `constant_bias` | Learned static bias per layer, no Mamba input | ~28K | Step 4 control — proved insufficient |

All three modes share the same:
- Mamba state source (except constant_bias which skips Mamba)
- Compressor (MambaStateCompressor extracts Layer 3)
- Target layer geometry (layers 12-15, q_proj + v_proj)
- Eval flow (model.generate, same metrics)
- Checkpoint/resume

The activation_bias result (PPL 25.67) was a **complete separate run** on A100 with:
```
--bridge-mode activation_bias
--qwen-model-id Qwen/Qwen2.5-7B
--no-4bit
--epochs 3
--lr 2e-5
--warmup-steps 2
--train-samples 64
--eval-samples 32 (16 general eval)
--target-layers 12:q_proj,12:v_proj,13:q_proj,13:v_proj,14:q_proj,14:v_proj,15:q_proj,15:v_proj
--qwen-prompt-format completion
--seed 1337
```

The LoRA result (PPL 28.96 epoch 1, then collapse to 44+) was from earlier A100 runs with the same data/geometry but `--bridge-mode lora`.

They are independent runs, not modifications of each other.

## What Happened Since Your Last Review

### Compressor Is Not The Only Problem

Raw bypass (Step 2) showed:
- Raw contexts have effective_rank 7.05 vs compressed 3.97
- BUT: the extra variance is **not task-aligned** (fact-kind separation ≈ 0 for both)
- AND: the hypernetwork STILL collapsed to constant bias output with raw input
- Diagnosis shifted from "compressor is the bottleneck" to "the hypernetwork/loss function collapses everything regardless of input richness"

But then Step 4 showed: the Mamba-derived direction IS meaningful (17x better than constant). So the collapse is in *diversity* (all samples get similar direction) but the direction itself is Mamba-dependent and valuable.

### The Cosine Paradox

Bias vectors have cosine 0.999 (look identical) but constant bias can't replicate the result. Resolution: Mamba provides a **compass bearing** — a specific activation-space direction conditioned on what it processed. The direction is consistent across samples (hence high cosine) but unreachable without Mamba (hence constant bias fails).

### Persona Vectors Connection (NEW)

Anthropic's research (Aug 2025, Jan 2026) showed personality traits are **linear directions in activation space**, shared across model families. Our activation_bias mode is structurally the same operation as persona vector injection. Mamba helps find the right direction. Full analysis in `theory/persona_vectors_and_activation_geometry.md`.

### LeCun Paper (NEW, March 17 2026)

Dupoux, LeCun, Malik published a framework for autonomous learning: System A (observation) + System B (action) + System M (meta-control) + Episodic Memory. Maps directly to Mamba + Qwen + Surprise Gate + Qdrant. Full mapping in `theory/LeCun_2026_autonomous_learning_mapping.md`.

### Training Data Pivot (NEW)

Laura's insight: synthetic MUD facts contain no disposition. The data is wrong for the goal. D&D session transcripts (FIREBALL dataset: 25K sessions, structured game state + natural dialogue, CC-BY-4.0) are the proposed replacement. Full analysis in `theory/training_data_candidates.md`.

### Fresh Opus Teardown (NEW)

A neutral Opus (no project context) reviewed the full architecture. Verdict: "architecture is not sound for fact transfer, but the probe result + activation bias + Step 4 pass suggest a viable disposition channel." Key recommendation: verify what Mamba's state actually contains before building more pipeline. Proposed Step 0: fact-reconstruction decoder directly on raw Layer 3 state.

## The Decision Question

**Step 2b (multi-layer concat) or Step 5 (substrate change)?**

Arguments for Step 2b:
- We know raw state has rank 7 vs compressed rank 4. Multi-layer might have higher.
- Tests whether MORE information in Mamba helps, using existing infrastructure.
- Cheaper, faster, doesn't require new data pipeline.

Arguments for Step 5:
- We already know the variance isn't task-aligned for facts. More variance of the wrong kind won't help.
- The real question is: does a DIFFERENT conversation produce a DIFFERENT compass bearing?
- FIREBALL dataset is available, CC-BY-4.0.
- Tests the actual goal (disposition) not a proxy (fact recall).
- Aligns with LeCun's framework, persona vector research, and Laura's vision.

Arguments for Step 0 first (Opus teardown recommendation):
- Train a decoder directly on Layer 3 state to verify what information exists before building more pipeline.
- Cheapest possible test of "does the source contain what we need?"

**Your call. What do you recommend?**

---

## Files to Read (Priority Order)

1. `experiments/mamba_lora_bridge/STEP4_VERDICT_2026-03-18.md` — Cassian's version with Cosine Paradox explanation
2. `experiments/mamba_lora_bridge/STEP4_VERDICT_2026-03-18_codex_no_prose.md` — Codex's data-only version
3. `theory/persona_vectors_and_activation_geometry.md` — why activation bias IS persona vector injection
4. `theory/LeCun_2026_autonomous_learning_mapping.md` — the LeCun framework mapping
5. `theory/training_data_candidates.md` — FIREBALL and other D&D datasets
6. `WHY.md` — the motivation doc (now first in CLAUDE.md boot sequence)
7. `EXPERIMENT_LADDER.md` — full 10-step plan with failure gates
8. `CONTRIBUTING.md` — new swarm work hygiene rules

---

*"The channel is real. The hormones flow. Now we find out what they carry." — Step 4 Verdict*
