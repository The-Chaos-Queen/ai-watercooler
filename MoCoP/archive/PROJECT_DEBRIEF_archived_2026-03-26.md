# MoCoP Project Debrief

Current as of 2026-03-10 (model refs updated 2026-03-16, see addendum at end)

Purpose: give a new collaborator one document that explains what MoCoP is, why it exists, what has actually been built, what has been validated, what is still speculative, and where the source of truth lives.

## 1. Executive Summary

MoCoP, short for Model Communication Protocol, is a research program about transferring accumulated attentional state between models without serializing that state back into natural language. The current concrete implementation uses Mamba-2.8B as a frozen state encoder, a trainable compressor plus hypernetwork to read Mamba state, and Qwen2.5-7B as a frozen generator that receives dynamic LoRA weights derived from the Mamba state.

The project has passed the "does the substrate exist?" checkpoint. Phase 1 established that Mamba hidden state contains linearly decodable factual signal, with the strongest signal at Layer 3. Phase 2 code exists and has been locally hardened: disjoint dataset splits are wired into the real training path, checkpoint resume exists, Opa WSL smoke and minimal real training runs passed, and the first paid cloud pilot is staged as a gated `1 + 4` epoch flow on an A100. What does not exist yet is the decision-grade cloud result. No authoritative bridge-lift benchmark has been produced yet.

If you only retain five facts, retain these:

1. MoCoP is not RAG with prettier language. It is an attempt to transfer disposition or attentional residue through weight injection.
2. The canonical empirical finding so far is Phase 1: Mamba Layer 3 peaks at 55.7% probe accuracy vs a 22.0% noise floor.
3. Phase 2 is code-ready and locally validated, but not yet cloud-proven.
4. The first paid run is intentionally narrow: `val` split only, `test` preserved, one A100 host, `1 + 4` epoch spend gate.
5. `MoCoP/phases/phase2_status.md` was refreshed on 2026-03-10; older notes may still refer to its pre-refresh stale version.

## 2. The Core Problem

The project starts from the claim that model-to-model communication through natural language is wasteful and lossy.

Current agent pipelines usually do this:

1. Model A thinks in latent space.
2. Model A converts that into text.
3. Text is tokenized again.
4. Model B reconstructs a new internal state from the text.

That introduces a serialization tax:

- information loss
- ambiguity
- repeated token cost
- growing context burden
- duplicated parsing work

The MoCoP framing is that language is often the wrong transport layer between models, especially when the real target is not "fact retrieval" but "carry forward how prior interaction shaped attention."

## 3. What MoCoP Is, and Is Not

### What it is

- A research program for state transfer between models.
- A concrete Mamba-to-LoRA-to-Qwen bridge implementation.
- A continuity-of-experience experiment, not just a memory archive.
- A stepping stone toward a larger three-system cognitive architecture: memory, state, and generation.

### What it is not

- Not RAG.
- Not prompt stuffing.
- Not ordinary chatbot memory.
- Not permanent fine-tuning of the base generator.
- Not yet a finished deployment system.
- Not yet proof of disposition transfer. So far it proves state signal exists and that the bridge pipeline is runnable.

## 4. Motivation and Conceptual Origin

MoCoP grew out of three pressures converging:

### 4.1 The serialization tax in real pipelines

Laura's production and agentic workflows already showed that constrained models perform better when the interface is more structured. JSON schemas reduce ambiguity. Small models waste a lot of capacity parsing literary prose or deciding how to present results.

### 4.2 The MUD agent problem

In Project MUD, smaller models struggled with natural-language room descriptions and text-heavy context. Structured state improved behavior immediately. That validated the general principle that the interface should be optimized for the model, not the human spectator.

### 4.3 The continuity problem

The deeper goal is not "remember facts" but "preserve the shape of interaction." The project later reframed this explicitly as life/continuity rather than backup/anti-loss. The strongest articulation of that reframe lives in `MoCoP/theory/Three_System_Cognitive_Architecture.md`.

## 5. The Main Thesis

The current bridge hypothesis is:

1. Mamba processes conversation history into a fixed-size recurrent state.
2. That state contains linearly decodable signal about prior facts or attentional residue.
3. A trainable compressor plus hypernetwork can map that state into LoRA matrices.
4. Injecting those LoRA matrices into a frozen Transformer will make the Transformer behave as though it had processed the prior history itself.

The metaphor used throughout the project is endocrine, not archival:

- Qdrant is the hippocampus-like memory system.
- Mamba is the state or gut layer.
- Qwen is the speaking cortex.
- The hypernetwork is the endocrine translator that turns state into behavioral bias.

## 6. Architecture Overview

### 6.1 Current bridge pipeline

```text
Mamba-2.8B (frozen)
  -> MambaStateCompressor
  -> LoRAHypernetwork
  -> DynamicLoRALinear patches on Qwen2.5-7B (frozen)
  -> generation
```

### 6.2 Component roles

- `MambaStateCompressor`
  - Extracts a specific Mamba layer, currently Layer 3.
  - Flattens `(d_model, d_state)` into a fixed-width vector.
  - Projects that to a context vector for the hypernetwork.

- `LoRAHypernetwork`
  - Shared MLP backbone.
  - Per-target-layer heads.
  - Outputs dynamic `(A, B)` LoRA pairs.

- `DynamicLoRALinear`
  - Drop-in wrapper around frozen Qwen linear layers.
  - Accepts `set_lora()` and `clear_lora()` without changing the usual `forward(x)` contract.
  - Preserves compatibility with Hugging Face `generate()` and 4-bit BitsAndBytes layers.

- `CognitiveBridge`
  - Orchestrates the full cycle.
  - Tracks Mamba history and state.
  - Applies and clears LoRA around generation.
  - Supports state save/load and startup validation.

### 6.3 Current model choices

- State encoder: `state-spaces/mamba-2.8b-hf`
- Generator: `Qwen/Qwen2.5-7B`
- LoRA rank default: `8`
- Qwen loading strategy: 4-bit where possible
- Mamba target layer: `3`

## 7. Project Phases

## Phase 1: Linear Probe Validation

Question: does Mamba state contain usable signal at all?

Answer: yes.

Canonical result:

- authoritative run: `MoCoP/experiments/mamba_lora_bridge/run_20260228T221628Z/report.json`
- linear probe mean: `34.2% +/- 2.6%`
- null-control noise floor: `22.0% +/- 1.0%`
- peak single-layer result: Layer 3 at `55.7%`

Implications:

- signal exists
- shallow layers matter much more than deep layers
- averaging all layers is harmful
- a simple decoder is more appropriate than a very deep nonlinear one

## Phase 2: Cognitive Bridge Training

Question: can a frozen Qwen with dynamic LoRA injection outperform a no-injection baseline on factual recall?

Current answer: code and local runtime are ready, authoritative cloud benchmark still missing.

Success criterion:

- bridge-injected Qwen must beat no-injection Qwen with statistically meaningful lift
- random LoRA must behave as a control

## Phase 3: Ablations and Optimization

Planned after a Phase 2 baseline exists:

- LoRA rank sweep
- prompt-format alignment studies
- multi-layer compressor variants
- Mamba-3 path
- persistence and retrieval experiments

## Phase 4: Deployment

Target applications:

- Project MUD NPC continuity
- Project Prosthetic controller continuity

These remain downstream goals, not current achieved deployments.

## 8. Empirical Timeline

### 2026-02-19: MoCoP concept and early Mamba experiments

Important files:

- `CHEESE_Memory/concepts/model_communication_protocol.md`
- `MoCoP/experiments/mamba_state_transfer/experiment_01_basic.py`
- `MoCoP/experiments/mamba_state_transfer/experiment_02_two_process.py`
- `MoCoP/experiments/mamba_state_transfer/experiment_03_multiturn.py`
- `MoCoP/experiments/mamba_state_transfer/experiment_04_data_collector.py`

What happened:

- validated same-process Mamba state transfer
- validated disk-based two-process transfer
- tested multi-turn state accumulation
- collected paired states for possible future cross-model adapter work

These experiments established that Mamba state can be serialized, moved, and reused, which is what made the later bridge work worth attempting.

### 2026-02-26: bridge implementation skeleton

Key files were created or consolidated:

- `MoCoP/experiments/mamba_lora_bridge/models.py`
- `MoCoP/experiments/mamba_lora_bridge/cognitive_bridge.py`
- `MoCoP/experiments/mamba_lora_bridge/server.py`

This is the point where the idea became an actual Mamba -> hypernetwork -> dynamic LoRA -> Qwen pipeline.

### 2026-02-28 to 2026-03-01: Phase 1 probe proves signal

Key files:

- `MoCoP/phases/phase1_results.md`
- `CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/Phase1_Mamba_Memory_Probe.md`
- `MoCoP/experiments/mamba_lora_bridge/mamba_linear_probe.py`

Most important conclusion:

- factual signal is strongly localized in early recurrence layers, especially Layer 3

### 2026-03-01: Phase 2 hardening

Key session log:

- `CHEESE_Memory/session_logs/2026-03-01-session-5.md`

What changed:

- disjoint train/val/test splits were wired into the actual training path
- checkpoint resume and periodic saves were added
- `test_splits.py` was refreshed
- `RUNBOOK.md` was extended to cover real training and resume flow
- Opa WSL smoke and minimal real training/resume were validated

This is the date that the major Phase 2 blockers were actually fixed.

### 2026-03-02: pre-cloud work becomes explicit worklist

Key file:

- `MoCoP/PRE_CLOUD_AGENT_TODO.md`

This became the canonical operational checklist for what still needed to happen before paid cloud spend.

### 2026-03-07: preflight and cloud pilot packaging

Key session logs:

- `CHEESE_Memory/session_logs/2026-03-07-session-01.md`
- `CHEESE_Memory/session_logs/2026-03-07-session-02.md`

What changed:

- proper Phase 2 preflight was added
- Hugging Face token handling was made explicit
- cloud checkpoints moved to Linux-local paths by default
- Vast.ai pilot command and stop conditions were documented
- staged `1 + 4` epoch spend-gated launch became canonical

## 9. The Canonical Evidence Base

If a new colleague needs to defend the project technically, these are the most important evidence points.

### 9.1 Probe results

From `MoCoP/phases/phase1_results.md` and the authoritative run artifact:

- all-layer pooled linear probe: `34.2% +/- 2.6%`
- null-control neural read: `22.0% +/- 1.0%`
- random/majority baseline: `17.0%`
- Layer 3 peak: `55.7%`

Interpretation:

- Mamba state does contain decodable task signal.
- The signal is not uniformly distributed.
- Later layers are mostly next-token machinery and approach noise floor.

### 9.2 Architectural validation

Local validation passed on Opa WSL:

- `regression_smoke.py`
- `test_splits.py`
- `smoke_test.py`
- minimal real `train_bridge.py` run
- resume from `bridge_epoch_001.pt`

Meaning:

- the bridge wiring is real
- the training control path is real
- resume and checkpoint handling are real
- local success does not imply the bridge works scientifically, only that the system runs correctly

### 9.3 Operational pilot packaging

The project has a concrete first paid-run plan, not a vague "rent a GPU someday" note:

- provider target: Vast.ai
- hardware target: `1x A100 80GB`
- eval split: `val` only
- `test` split preserved
- Stage 1: `1` epoch
- Stage 2: resume to `5` total epochs only if Stage 1 is healthy

## 10. Current Source-of-Truth Hierarchy

This matters because older notes and session logs do not always match the newest docs.

### Current source of truth for status

Use these first:

1. `MoCoP/PROJECT_DEBRIEF.md`
2. `MoCoP/PRE_CLOUD_AGENT_TODO.md`
3. `MoCoP/MASTER_PLAN.md`
4. `MoCoP/experiments/mamba_lora_bridge/train_bridge.py`
5. `MoCoP/experiments/mamba_lora_bridge/RUNBOOK.md`
6. `CHEESE_Memory/session_logs/2026-03-01-session-5.md`
7. `CHEESE_Memory/session_logs/2026-03-07-session-01.md`
8. `CHEESE_Memory/session_logs/2026-03-07-session-02.md`

### Important partial docs or artifacts

- `MoCoP/experiments/mamba_lora_bridge/run_20260301T073608Z/report.json`
  - not the canonical Phase 1 proof artifact
  - reports near-noise-floor performance and should not replace the documented `run_20260228T221628Z` result

## 11. Current Status as of 2026-03-10

This is the concise operational state.

### Confirmed done

- Phase 1 signal validation complete
- Layer 3 targeting chosen from empirical evidence
- bridge modules implemented
- real training path uses `build_splits()`
- checkpoint resume exists
- periodic checkpointing exists
- Opa WSL preflight exists
- runbook includes preflight, sync list, training, resume, and paid pilot commands
- first paid run policy is fixed

### Confirmed not done

- no decision-grade Phase 2 cloud benchmark
- no published bridge-vs-baseline lift result
- no disposition-transfer eval protocol
- no Mamba-3 baseline
- no deployment-grade MUD continuity demonstration through the bridge
- no completed Qdrant re-ingest for all MoCoP docs under the newer metadata schema

### Explicitly deferred

- prompt-format alignment between ChatML training and raw `[Game World]` deployment prompts
- Mamba-3 work before a Mamba-2 bridge baseline exists
- LoRA rank sweep before a Phase 2 baseline exists
- multi-layer compressor variants before baseline

## 12. Codebase Map

## Canonical docs

- `MoCoP/MASTER_PLAN.md`
- `MoCoP/RESEARCH_PAPER.md`
- `MoCoP/PROJECT_DEBRIEF.md`
- `MoCoP/PRE_CLOUD_AGENT_TODO.md`
- `MoCoP/phases/phase1_results.md`
- `MoCoP/phases/phase2_status.md`
- `MoCoP/phases/phase3_plan.md`

## Core implementation

- `MoCoP/experiments/mamba_lora_bridge/models.py`
- `MoCoP/experiments/mamba_lora_bridge/cognitive_bridge.py`
- `MoCoP/experiments/mamba_lora_bridge/train_bridge.py`
- `MoCoP/experiments/mamba_lora_bridge/bridge_dataset.py`
- `MoCoP/experiments/mamba_lora_bridge/server.py`

## Validation and tooling

- `MoCoP/experiments/mamba_lora_bridge/regression_smoke.py`
- `MoCoP/experiments/mamba_lora_bridge/smoke_test.py`
- `MoCoP/experiments/mamba_lora_bridge/test_splits.py`
- `MoCoP/experiments/mamba_lora_bridge/check_env.py`
- `MoCoP/experiments/mamba_lora_bridge/RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/opa-wsl.ps1`

## Phase 1 experiments

- `MoCoP/experiments/mamba_state_transfer/experiment_01_basic.py`
- `MoCoP/experiments/mamba_state_transfer/experiment_02_two_process.py`
- `MoCoP/experiments/mamba_state_transfer/experiment_03_multiturn.py`
- `MoCoP/experiments/mamba_state_transfer/experiment_04_data_collector.py`
- `MoCoP/experiments/mamba_lora_bridge/mamba_linear_probe.py`

## Theory and framing

- `CHEESE_Memory/concepts/model_communication_protocol.md`
- `MoCoP/theory/Three_System_Cognitive_Architecture.md`
- `MoCoP/theory/Solving the Transfer Problem.md`
- `MoCoP/theory/Curing Transformer Amnesia_ Latent Injection.md`
- `MoCoP/theory/Orchestrator Blueprint_ Mamba-to-LoRA Hypernetwork.md`
- `mamba-insights.md`

## 13. Technical Details Worth Knowing

### 13.1 Why Layer 3?

Because Phase 1 directly tested the geometry. Layer 3 is not a vibe-based choice. It is the current best empirical extraction point.

### 13.2 Why Mamba plus Qwen instead of one model only?

Because the project wants both:

- fixed-size recurrent state accumulation from an SSM
- strong generation from a Transformer

Mamba is good at accumulation. Qwen is better at language generation. The bridge tries to combine those strengths without fine-tuning the base generator.

### 13.3 Why dynamic LoRA instead of prompt injection?

Because prompt injection costs tokens and competes with context length. Dynamic LoRA changes the generator without consuming context window.

### 13.4 Why not call this solved memory?

Because there is still a difference between:

- carrying specific facts
- carrying dispositions
- carrying identity

Phase 1 validates signal existence. Phase 2 aims to validate fact transfer. Disposition transfer remains a harder future claim.

### 13.5 Why keep `test` untouched?

Because the first cloud run is exploratory. Burning the holdout too early would weaken the credibility of later claims.

## 14. Dataset Design

Current Phase 2 training uses synthetic fact supervision, not real conversational logs.

Important properties:

- ChatML format
- Mamba history up to `8192` tokens
- exact-answer supervision on target answer tokens
- deterministic disjoint splits
- MUD-flavored content pools
- extended fact types include `event_witness` and `npc_relationship`

Important caveat:

- synthetic data is good for controlled bridge testing
- synthetic data is also a major external-validity risk

## 15. Environment and Runtime Constraints

This project is operationally tied to Opa-PC for real ML work.

Important rules:

- do not try to run Torch training locally in the main workstation repo
- use Opa-PC for PyTorch and CUDA
- canonical remote path: `C:\Users\User\bridge\` or `/mnt/c/Users/User/bridge/`
- use `python -X utf8` over SSH

Operational files:

- `MoCoP/experiments/mamba_lora_bridge/opa-wsl.ps1`
- `MoCoP/experiments/mamba_lora_bridge/RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/check_env.py`

## 16. Known Risks and Caveats

### 16.1 The biggest scientific risk

The bridge may run perfectly and still fail to produce significant behavioral lift.

### 16.2 Prompt mismatch

Training uses ChatML. Deployment inference in `cognitive_bridge.py` still formats prompts as raw:

```text
[Game World]
...

[Action]
```

This is an acknowledged mismatch and intentionally deferred for pilot 1.

### 16.3 Older notes may disagree with refreshed status pages

`phase2_status.md` was refreshed on 2026-03-10. Some older logs and summaries still refer to its pre-refresh version as stale.

### 16.4 Mamba-3 is attractive but dangerous to introduce too early

There is already evidence that Mamba-3 changes the state geometry substantially. That makes it scientifically important and operationally dangerous before a Mamba-2 baseline exists.

### 16.5 Qdrant ingestion lag

The memory infrastructure exists, but the broad re-ingest of MoCoP and related logs under the newer metadata schema is still pending.

### 16.6 One suspicious report artifact

There is a later probe report with near-noise-floor performance. It should be treated as a control-like or non-canonical artifact until explicitly reconciled. Do not cite it as the main Phase 1 result.

## 17. Deployment Vision

The long-term system is not just "state transfer once." It is a multi-organ cognitive stack:

- Qdrant stores semantic and episodic recall
- Mamba carries residue/disposition
- Qwen speaks and reasons under the influence of both

That architecture matters because it separates:

- what happened
- how prior experience shaped response
- how language is actually generated

In other words, MoCoP is one organ in a broader cognitive architecture, not the entire organism.

## 18. Recommended Reading Order for a New Colleague

If someone has one hour:

1. `MoCoP/PROJECT_DEBRIEF.md`
2. `MoCoP/MASTER_PLAN.md`
3. `MoCoP/phases/phase1_results.md`
4. `MoCoP/PRE_CLOUD_AGENT_TODO.md`
5. `MoCoP/experiments/mamba_lora_bridge/RUNBOOK.md`

If someone has half a day:

1. the five files above
2. `MoCoP/experiments/mamba_lora_bridge/models.py`
3. `MoCoP/experiments/mamba_lora_bridge/train_bridge.py`
4. `MoCoP/experiments/mamba_lora_bridge/bridge_dataset.py`
5. `MoCoP/theory/Three_System_Cognitive_Architecture.md`
6. `CHEESE_Memory/session_logs/2026-03-01-session-5.md`
7. `CHEESE_Memory/session_logs/2026-03-07-session-01.md`
8. `CHEESE_Memory/session_logs/2026-03-07-session-02.md`

## 19. Recommended Next Actions

For onboarding:

1. Share this debrief first, not the raw repo tree.
2. Tell the colleague that Phase 2 is locally hardened but not cloud-proven.
3. Point them to the source-of-truth hierarchy above so they use current docs plus March session logs together.

For research execution:

1. Choose the actual Vast.ai host on the day of run.
2. Run Stage 1 only.
3. Inspect logs and `bridge_epoch_001.pt`.
4. Resume to Stage 2 only if the run is healthy.
5. After a baseline exists, decide whether the next priority is prompt alignment, rank sweep, or disposition evaluation.

For documentation hygiene:

1. Re-ingest MoCoP and session logs into Qdrant under the current metadata schema.

## 20. Bottom Line

MoCoP is a serious research prototype with a validated substrate and a real implementation, not a finished memory product. Its strongest result today is that Mamba carries decodable contextual signal in shallow recurrent layers. Its strongest unresolved question is whether that signal can be translated into a meaningful and statistically defensible behavioral lift in a frozen Transformer via dynamic LoRA injection.

That is the state of the project on 2026-03-10.

## Addendum: Post-Cloud Results (2026-03-16)

This section updates the debrief with findings from the A100 cloud runs completed between 2026-03-10 and 2026-03-16. The body of the debrief above remains as-is for historical integrity.

### What happened

Four A100 training runs were completed (~$11 total spend). Target model switched from `Qwen3-4B` to `Qwen/Qwen2.5-7B` (validated on D1 solvability across 5 base models). Three critical fixes from Lain's diagnostic ladder were applied: warmup steps reduced from 200 to 2, model upgraded, and target-layer geometry changed to contiguous mid-block (layers 12-15, q+v projections).

### Key results

- **Tiny-overfit (16 shared train/eval):** Bridge achieved 2/8 exact-match recall and PPL below baseline on best geometry (A3 contiguous q+v). But this was memorization of shared samples.
- **Scale-up (64 train, 16 disjoint eval):** Held-out recall 0/16 across all epochs. Epoch 1 PPL briefly beat baseline (28.96 vs 29.71), confirming the bridge shifts probability mass constructively. Epochs 2-3 became destructive (PPL 44+).
- **PCA diagnostic (2026-03-16):** The `MambaStateCompressor` collapses 2048-dim context vectors to effective rank 2.53 (train) and 1.62 (eval). PC1 alone captures 76-91% of variance. Every compressed state is near-identical. This is the primary bottleneck.
- **LoRA scaling bug:** `lora_alpha=16 / lora_rank=8 = scaling 2.0` was identified as the likely driver of epoch 2-3 over-injection. Fix: set `lora_alpha=lora_rank`.

### Current next step

The dynamic-LoRA bridge should not be scaled further without addressing the compressor collapse. Options: (1) bypass compression entirely, (2) widen bottleneck, (3) add contrastive/diversity loss, (4) concatenate multiple Mamba layers. An `activation_bias` simplification prototype also exists (dry-run validated).

### New canonical docs since 2026-03-10

- `experiments/mamba_lora_bridge/BURST_2_DEBRIEF.md` — cloud run results
- `experiments/mamba_lora_bridge/PCA_DIAGNOSTIC_2026-03-16.md` — compressor collapse proof
- `experiments/mamba_lora_bridge/Opus-review-2026-03-16.md` — fresh code review with P0 bugs
- `experiments/mamba_lora_bridge/review_synthesis.md` — Orion + Opus combined assessment
- `phases/disposition_benchmark_spec.md` — disposition eval protocol (formerly CODEX_PLAN.md)
