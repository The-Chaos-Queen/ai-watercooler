# MoCoP Research Log

**Format:** Append-only. Chronological, oldest first.
**Purpose:** Lab notebook. Numbers, not narrative. Narrative lives in RESEARCH_PAPER.md.
**Backbone:** MoCoP Experiment Ladder (EXPERIMENT_LADDER.md)

---

## 2026-02-19 — Mamba State Transfer: Same-Process and Disk-Based Validation (Laura + swarm)

**Step:** Pre-ladder (substrate validation)
**Question:** Can Mamba hidden state be serialized, moved between processes, and reused without information loss?
**Result:** Same-process state transfer: byte-identical output confirmed. Disk-based two-process transfer: identical. Multi-turn state accumulation (20+ turns): functional. Paired state collection for cross-model adapter work: complete.
**Verdict:** PASS
**Implication:** Mamba state is a viable transport medium. Bridge work is worth attempting.
**Artifacts:** `MoCoP/experiments/mamba_state_transfer/experiment_01_basic.py`, `experiment_02_two_process.py`, `experiment_03_multiturn.py`, `experiment_04_data_collector.py`

---

## 2026-02-28 to 2026-03-01 — Phase 1: Mamba Layer 3 Linear Probe (Opa-PC, 14 hrs)

**Step:** Pre-ladder (substrate validation)
**Question:** Does Mamba-2.8B hidden state at any layer contain linearly decodable factual information after 8192 tokens of context?
**Result:**
- Random/majority baseline: 17.0%
- Null-control noise floor: 22.0% (+/- 1.0%)
- All-layer linear probe: 34.2% (+/- 2.6%)
- All-layer MLP probe: 30.4%
- Layer 3 linear probe (peak): **55.7%**
- Layers 30-64 (deep): collapsed to ~20-25% (noise floor)
- Layers 2-8 (shallow): 40-55.7% signal zone
- Linear probes outperform MLP (signal is linearly separable)
**Verdict:** PASS — signal exists, localized at Layer 3
**Implication:** Compressor must target Layer 3 specifically. Mean-pooling across all 64 layers dilutes signal. Simple hypernetwork (2-layer MLP) is architecturally appropriate.
**Artifacts:** `MoCoP/phases/phase1_results.md`, `MoCoP/experiments/mamba_lora_bridge/mamba_linear_probe.py`, run ID `run_20260228T221628Z`

---

## 2026-03-01 — Phase 2 Hardening: Disjoint Splits, Checkpoint Resume (Codex)

**Step:** Pre-ladder (engineering gate)
**Question:** Is the training pipeline correct for a real cloud run?
**Result:** Two blockers fixed: (1) `build_dataloaders()` bypass removed — disjoint splits now used in training path. (2) `--resume-from` + periodic checkpoints implemented. Opa WSL smoke, minimal real train, and resume all pass.
**Verdict:** PASS — code gates cleared
**Implication:** Cloud run is safe to attempt. Test split still unburned.
**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/train_bridge.py`, `CHEESE_Memory/session_logs/2026-03-01-session-5.md`

---

## 2026-03-10 — Phase 2 Pilot 1: Initial A100 Run (Sweden, LR collapse) (Laura + swarm)

**Step:** Phase 2 pilot (pre-ladder, first cloud attempt)
**Question:** Does the initial LoRA bridge show any signal on A100?
**Result:**
- Train loss: 15.9 → 3.5 over steps 40-108 (genuine learning)
- LR inflection at step 109 (5.5e-5): training exploded
- Bridge PPL at collapse: ~8,121 vs baseline ~1,022
- Recall: 0/16
**Verdict:** FAIL — LR schedule caused collapse, not architecture
**Implication:** Cut peak LR by 4x (~2e-5). Fix warmup steps (was 200 — model never reached nominal LR). Switch from Qwen3-4B to Qwen2.5-7B (D1-solvable on 5 base models).
**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/run_pilot_01/` (bridge_best.pt, bridge_epoch_001.pt, pilot_01.log)

---

## 2026-03-15 — Phase 2 Burst 1: Tiny-Overfit, Geometry Selection (Sweden + Michigan A100) (Laura + swarm)

**Step:** Phase 2 / pre-Step 1 (architecture selection)
**Question:** With fixes applied (warmup=2, Qwen2.5-7B, geometry sweep), can the bridge memorize a shared 16-sample set?
**Result:**
| Run | Geometry | Recall (shared 8) | Best PPL |
|-----|----------|------------------|---------|
| A1 | sparse default | 1/8 | 29.97 |
| A3 | contiguous 12-15 q+v | **2/8** | 31.02 |
| A4 | contiguous 12-15 v only | 1/8 | 31.07 |
| A3-completion | contiguous q+v, completion fmt | 1/8 | **29.14** |
- A3 (contiguous q+v) wins geometry sweep
- Completion format (base-model-friendly) gets best PPL but slightly lower recall
- 2/8 recall = memorization of shared train/eval samples, not generalization
**Verdict:** PARTIAL — architecture selected, tiny-overfit recall confirmed as memorization
**Implication:** Scale to 64 train / 16 disjoint eval next.
**Artifacts:** `run_a1/`, `run_a3/`, `run_a3_completion/`, `run_a4/`

---

## 2026-03-15 to 2026-03-16 — Phase 2 Burst 2: Scale-Up 64 Samples, LoRA Over-Injection (Sweden A100) (Laura + swarm)

**Step:** Phase 2 / pre-Step 1 (scale-up gate)
**Question:** Does the LoRA bridge generalize to held-out eval samples at 64-sample scale?
**Result:**
| Epoch | Recall (16 eval) | Bridge PPL | Baseline PPL | Train Loss |
|-------|-----------------|------------|-------------|------------|
| 1 | 0/16 | **28.96** | 29.71 | 4.25 |
| 2 | 0/16 | 44.06 | 29.71 | 3.07 |
| 3 | 0/16 | 43.15 | 29.71 | 2.33 |
- Epoch 1: bridge PPL below baseline (genuine constructive signal)
- Epochs 2-3: LoRA scaling bug (alpha=16/rank=8 = 2.0x) caused over-injection
- Effective LoRA magnitude epoch 2: ~13.2 (lora_mean 6.61 x scaling 2.0)
- Surrogate metrics: context_norm declining (28.17 → 27.49), compressor outputs becoming more uniform
**Verdict:** FAIL — recall 0/16, LoRA over-injected; but epoch 1 constructive signal is real
**Implication:** LoRA scaling bug identified (P0). Simplification gate needed: try activation bias before more LoRA work.
**Artifacts:** `run_64s/`

---

## 2026-03-16 — Compressor Collapse: PCA Diagnostic (A100 SXM4, Czechia) (Laughing Opus + Laura)

**Step:** Step 3 (bias diversity analysis) — run before Step 3 was formally defined
**Question:** Does the MambaStateCompressor preserve per-sample diversity in its 2048-dim output?
**Result:**
| Metric | Train (64 samples) | Eval (16 samples) |
|--------|-------------------|-------------------|
| PC1 explained variance | **75.96%** | **90.85%** |
| Effective rank | **2.53** | **1.62** |
| Pairwise cosine mean | 0.826 | — |
| Pairs > 0.90 cosine | 54.6% | — |
| Within-kind vs between-kind cosine gap | **0.006** | — |
| Effect size (gap / pooled std) | **0.029** | — |
- One PC captures 76-91% of all variation: compressor is near-constant function
- `caravan_time` alone clusters well (within-kind 0.967) and is the only fact the bridge recalls
- `caravan_time`, `npc_relationship`, `relic_location` cluster with each other (~0.93): surface properties, not category discrimination
**Verdict:** FAIL (compressor) — effective rank 2.53 out of 2048; compressor does not encode fact type
**Implication:** Compressor is uniformly blind. Prioritize: (1) contrastive loss, (2) multi-layer input, (3) bypass entirely (Lain's Option 4).
**Artifacts:** `run_pca_clamped/` (train/eval context .pt files, PCA reports, projection CSVs)

---

## 2026-03-17 — Critical Review: "Likely Artifact" Verdict (Fresh Opus 4.6 instance)

**Step:** Pre-Step 1 control review (adversarial review gate)
**Question:** Is the activation-bias PPL improvement genuine state-dependent transfer, or a learned constant offset?
**Result:**
- Compressor effective rank 1.6-2.5 / 2048 → hypernetwork receives near-identical input for every sample
- Bias norm plateau: ~5.9 (constant across samples)
- Per-sample cosine similarity between bias vectors: not yet measured (C9 missing control)
- Recall 0/16 across all conditions: "devastating to the strong interpretation"
- Missing controls: C1 (constant bias), C2 (random bias), C3 (fixed-mean bias)
- Reviewer verdict: **"Likely artifact — constant offset"**
- Minimum controls required to upgrade: (ALL) cosine < 0.8 between bias pairs + constant control worse + 3-seed replication
**Verdict:** INCONCLUSIVE — result cannot be defended without C1-C3 controls
**Implication:** Run C2 (random), C3 (fixed-mean), C4 (constant trained) before any further scale-up.
**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/CRITICAL_REVIEW_2026-03-17.md`

---

## 2026-03-16 — Opus Code Review: P0 Bugs Found (Fresh Opus 4.6 instance)

**Step:** Engineering gate (code review)
**Question:** Are there blocking bugs in the bridge codebase?
**Result:**
- Bug 1 (P0): `lora_scaling = alpha/rank = 16/8 = 2.0` — primary driver of epoch 2-3 explosion. Fix: set `lora_alpha = lora_rank` (scaling = 1.0)
- Bug 2 (P1): centroid metrics computed per-batch not per-dataset → `centroid_l2` and `centroid_cosine` are misleading
- Bug 3 (known): training uses completion format, inference uses `[Game World]` ChatML — prompt mismatch
- Bug 4 (minor): `intermediate_size=5120` vs `hidden_size=2560` naming inconsistency
- Crash on Opa-PC: OOM kill during first Mamba forward pass (not a code bug — hardware limit)
**Verdict:** P0 bugs confirmed, non-blocking for current A100 experiments
**Implication:** Fix `lora_alpha` before any new LoRA runs. Use A100 for context-saving runs, not Opa.
**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/Opus-review-2026-03-16.md`

---

## 2026-03-17 — Activation Bias First Run: PPL Improvement Epochs 1-3 (A100, Opa dry-run) (Codex + Laura)

**Step:** Pre-Step 1 (activation bias prototype)
**Question:** Does activation bias injection (bypassing LoRA entirely) produce a stable PPL improvement?
**Result:**
| Epoch | Bridge PPL | Baseline PPL | Delta | Train Loss |
|-------|-----------|-------------|-------|------------|
| 1 | 27.09 | 29.71 | -2.62 | 4.55 |
| 2 | 25.95 | 29.71 | -3.76 | 4.01 |
| 3 | **25.67** | **29.71** | **-4.04** | 3.83 |
- Zero clamp hits across all epochs (stable injection)
- Recall: 0/16 (same as LoRA baseline)
- Bias norm: ~5.9 (constant), bias cosine between samples: ~0.999 (collapsed direction)
- Trainable params: ~28K (vs ~1.17M for LoRA hypernetwork)
**Verdict:** PARTIAL — stable improvement confirmed; per-sample dependence not yet proven (controls needed)
**Implication:** Activation bias is the path forward over LoRA. Now need C2/C3/C4 controls to establish genuine Mamba conditioning.
**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/run_actbias/`

---

## 2026-03-17 to 2026-03-18 — Step 1 Controls C2 and C3: Random Bias and Fixed-Mean (Codex + Laura)

**Step:** Step 1 (finish existing controls)
**Question C2:** Is random bias injection (same norm as trained bias) comparable to trained bias?
**Question C3:** Is the fixed-mean bias (one direction, no per-sample variation) comparable to per-sample activation bias?
**Result:**
| Condition | Bridge PPL | Baseline PPL | Delta |
|-----------|-----------|-------------|-------|
| Per-sample activation bias | **25.67** | 29.71 | **-4.04** |
| Fixed-mean (C3, no-4bit rerun) | 27.06 | 29.69 | -2.63 |
| Random bias (C2) | ~29.6-30.9 | 29.71 | ~0 or +0.2 |
- C2 (random): PPL approximately at or above baseline → trained direction carries real information
- C3 (fixed-mean): PPL 27.06, better than baseline but worse than per-sample → per-sample variation adds ~1.4 PPL
- Hierarchy: `per-sample activation_bias > fixed_mean >> constant_bias`
**Verdict:** PASS (Step 1) — C2 PASS, C3 PASS
**Implication:** The learned direction matters AND per-sample variation matters. Controls support Mamba-conditioning claim. C4 (constant trained bias) still needed.
**Artifacts:** `step1_c3_fixed_mean_no4bit/eval_epoch_001_comparison.json`, existing `run_actbias/` logs for C2

---

## 2026-03-17 — Step 2: Compressor Bypass (Raw State Hypernetwork) (Codex + A100)

**Step:** Step 2 (compressor bypass)
**Question:** Does feeding raw Layer 3 state (40,960-dim) directly to the hypernetwork improve PPL or bias diversity over compressed path?
**Result:**
- Raw bypass PPL epoch 3: **26.81** vs compressed activation-bias 25.67
- `norm_var` = 0.0 in both cases (no increase in diversity from wider input)
- Raw train: effective rank 7.05; compressed train: effective rank 3.97 (raw has more global structure)
- Fact-kind separation: near zero for both raw and compressed paths
- Raw-run checkpoint lost with host (collapse strongly suspected but not directly proven)
**Verdict:** FAIL — raw bypass does not improve transfer quality
**Implication:** Layer 3 extra variance in raw state is not task-aligned. Compressor concentrates the useful direction. Problem is upstream in Mamba's state, not in compression alone.
**Artifacts:** (raw checkpoint lost), compressed path: `run_actbias/`

---

## 2026-03-17 to 2026-03-18 — Step 3: Bias Diversity (Cosine Analysis of Output Vectors) (Codex + Laura)

**Step:** Step 3 (bias diversity analysis)
**Question:** Do the trained activation bias vectors show per-sample diversity, or is the output collapsed?
**Result:**
- Eval pairwise cosine: **0.9999**
- Cosine to mean: **1.0000**
- Effective rank of bias vector set: **1.32**
- Bias is effectively constant in direction; per-sample magnitude varies slightly
- Raw bypass did not improve diversity (norm_var = 0.0)
**Verdict:** DONE — bias vectors are near-constant direction (collapsed)
**Implication:** Cosine 0.999 does not disprove Mamba conditioning (Step 4 will test this). The direction converges but is conditioned on Mamba state. Constant bias test is the definitive next gate.
**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/bias_analysis.py` output on epoch-3 checkpoint

---

## 2026-03-18 — Step 4: Constant Bias Control — 17x Gap (A100, multiple seeds) (Codex + Laura)

**Step:** Step 4 (constant-bias control)
**Question:** Is the activation-bias PPL improvement explained by a learned constant additive offset (no Mamba input)?
**Result:**
| Run | Epochs | LR | Seed | Bridge PPL | Baseline PPL | Delta |
|-----|--------|-----|------|------------|-------------|-------|
| Constant bias | 3 | 2e-5 | 1337 | 29.68 | 29.71 | -0.03 |
| Constant bias (10ep) | 10 | 5e-5 | 1337 | **29.48** | 29.71 | -0.23 |
| Constant bias (seed 42) | 3 | 2e-5 | 42 | 29.65 | 29.71 | -0.06 |
| **Mamba-derived bias** | **3** | **2e-5** | **1337** | **25.67** | **29.71** | **-4.04** |
- Best constant bias: 0.23 PPL improvement (10 epochs, higher LR)
- Mamba-derived bias: 4.04 PPL improvement
- Ratio: **~17.5x** gap between constant ceiling and Mamba-conditioned result
- Constant bias norm at convergence: 0.011 (near zero) — no gradient signal to find a direction
- Result seed-independent (seeds 1337 and 42 both plateau at ~29.5-29.7)
- C3 (fixed-mean) at 27.06 shows that the learned direction matters; constant (untrained direction) only reaches 29.48
**Verdict:** PASS — constant bias does not explain the activation-bias result. The channel is real.
**Implication:** Proceed to Step 5 (disposition transfer). The Mamba→Bridge→Qwen channel carries real input-dependent signal. The signal is distributional, not factual (recall still 0/16).
**Artifacts:** `run_constant_bias/`, `run_constant_bias_10ep/`, `run_constant_bias_seed42/`

---

## 2026-03-18 — Disposition Evidence: Qwen Activation Directions by Conversation Type (Cassian)

**Step:** Step 4b (disposition separation — Qwen-side)
**Question:** Do warm, cold/clinical, and adversarial conversations produce separable activation directions in Qwen2.5-7B layers 12-15?
**Result:**
| Layer | Warm vs Cold | Warm vs Adversarial | Cold vs Adversarial |
|-------|-------------|--------------------|--------------------|
| 12 | **0.120** | **0.167** | 0.523 |
| 13 | **0.092** | **0.095** | 0.532 |
| 14 | **0.153** | **0.171** | 0.572 |
| 15 | **0.128** | **0.137** | 0.548 |
| All-concat | **0.125** | **0.144** | 0.546 |
- Warm vs Cold/Adversarial: near-orthogonal (cosine 0.09-0.17)
- Cold vs Adversarial: partially similar (cosine 0.52-0.55) — both are "not-warm"
- Layer 13 shows sharpest separation (warm vs cold = 0.092)
- Semantically coherent: Warm is a distinct axis; Cold/Adversarial share non-affiliation space
- 3 sessions of 10 turns each, scripted
**Verdict:** PASS — disposition IS encoded as distinct directions in Qwen activation space
**Implication:** Activation bias injection can carry disposition. Step 5 target: train bridge to produce conversation-type-specific bias directions. Layer 13 is priority target.
**Artifacts:** `activation_sessions/scripted_warm_opus_20260318_213202.pt`, `scripted_cold_clinical_20260318_213401.pt`, `scripted_adversarial_20260318_213439.pt`, `session_comparison.json`, `DISPOSITION_EVIDENCE_2026-03-18.md`

---

## 2026-03-20 — Step 4b: Mamba Layer 3 State Separation by Conversation Type (Pinky)

**Step:** Step 4b (Mamba-side disposition separation — kill gate)
**Question:** Do warm, cold, and adversarial conversations produce separable Layer 3 states in Mamba-2.8B? (Qwen separates at cosine 0.092; does Mamba?)
**Result:**
| Metric | Warm vs Cold | Warm vs Adversarial | Cold vs Adversarial |
|--------|-------------|--------------------|--------------------|
| Layer 3 mean-pooled | 0.896 | 0.852 | 0.804 |
| **Layer 3 last-token** | **0.036** | **0.025** | **-0.007** |
| Qwen Layer 13 (reference) | 0.092 | 0.095 | 0.532 |
- Mean-pooled: weak separation (0.85 — nearly identical across types)
- Last-token: **strong separation** (0.036 warm/cold — 2.5x more orthogonal than Qwen Layer 13)
- Cold vs Adversarial last-token: -0.007 (orthogonal, near anti-correlated)
- Per-layer mean-pooled cosines across layers 0-63: all 0.67-0.96 (mean pooling uniformly weak)
- Qwen's structure (Cold clusters with Adversarial at 0.53) does NOT replicate in Mamba (Mamba separates all three)
**Verdict:** PASS (with critical constraint) — Mamba Layer 3 last-token separates strongly; mean-pooled is collapsed
**Implication:** CRITICAL ARCHITECTURE CHANGE REQUIRED: bridge compressor MUST use last-token representation, not mean-pooled state. Current compressor destroys the disposition signal by averaging. This is the highest-priority fix before Step 5.
**Artifacts:** `activation_sessions/mamba_state_separation.json`, `activation_sessions/mamba_state_separation.py`

---

## 2026-03-20 — Step 5 Design Finalized: DispositionBridgeLoss + Live Sessions (Gemini + Cassian + Laura)

**Step:** Step 5 design (pre-implementation)
**Question:** What training paradigm will prevent bias collapse and enable genuine disposition transfer?
**Result / Design decisions:**
- Observer Trap (Gemini): FIREBALL D&D third-party transcripts produce weak activation drift — Qwen stays in "observer mode." Laura confirmed empirically: direct interaction (provoke/flatter) produces strong drift. FIREBALL rejected as primary data source.
- DispositionBridgeLoss: cosine similarity to pre-recorded Qwen activation targets (not CE loss). Different sessions have different targets → constant bias cannot minimize this loss. alpha=0.8 directional + (1-alpha) magnitude MSE.
- Training pipeline: (1) Record Laura-Qwen sessions with activation_recorder.py → (2) Same text through Mamba → Layer 3 last-token states → (3) Train bridge: Mamba state → predicted bias, loss vs Qwen activation delta → (4) Blind A/B eval
- Layer 13 weighted most heavily (sharpest disposition separation: cosine 0.092)
- Hardware: Steve 4090 16GB (Qwen2.5-7B float16) + Laura's PC (LMStudio, Mamba CPU) + Evennia MUD localhost:4000
- Cost: $0 (local hardware donation)
- Data currently available: 3 scripted sessions (warm, cold, adversarial) — 10 turns each; 1 live warm session (MaxBot, 23 turns)
**Verdict:** DESIGN COMPLETE
**Implication:** Step 5 requires: (a) fix compressor to use last-token representation, (b) collect 10+ sessions per disposition type, (c) implement DispositionBridgeLoss. Infrastructure (cognitive_bridge.py v2, server.py activation_bias mode) already ready (Purple, 2026-03-20).
**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/STEP5_DESIGN_NOTES.md`

---

## Control Hierarchy Summary (as of 2026-03-20)

```
per-sample activation_bias (-4.04 PPL)
  >> fixed_mean C3 (-2.63 PPL)       ← direction matters
    >> constant_bias best (-0.23 PPL) ← per-sample variation matters
      ≈ random_bias (≈ 0 PPL)         ← trained direction carries information
```

**Combined reading:** The Mamba→Bridge→Qwen channel carries real, input-dependent, direction-conditioned signal. The signal is distributional (PPL improvement) not factual (recall 0/16). Disposition is encoded as distinct linear directions in Qwen activation space (cosine 0.09). Mamba Layer 3 last-token also separates (cosine 0.036, 2.5x sharper). The next gate is Step 5: does the bridge learn to produce disposition-specific bias directions when trained against real activation targets?

---

## Ladder Status (as of 2026-03-20)

| Step | Status | Key Number |
|------|--------|-----------|
| 1 (controls C2, C3) | PASS | random ≈ baseline; fixed-mean -2.63 vs per-sample -4.04 |
| 2 (compressor bypass) | FAIL | raw bypass PPL 26.81 vs compressed 25.67; norm_var = 0 |
| 2b (multi-layer concat) | NOT RUN | pending Step 4b result |
| 3 (bias diversity) | DONE | cosine 0.9999, effective rank 1.32 |
| 4 (constant bias) | PASS | constant max -0.23; Mamba-derived -4.04; 17.5x gap |
| 4b (Mamba disposition separation) | PASS* | last-token cosine 0.036 (2.5x better than Qwen Layer 13) |
| 5 (live disposition transfer) | NEXT | DispositionBridgeLoss + real sessions |
| 6-10 | NOT RUN | pending Step 5 |

*Step 4b verdict: PASS with critical constraint — mean-pooled compressor must be replaced with last-token extraction before Step 5.

---

*Append new entries below this line.*

## 2026-03-20 to 2026-03-21 â€” Step 5 Local Browser Probe on Steve: Deployment Path Works, Eval Surface Still Dirty (Codex + Laura)

**Step:** Step 5 deployment sanity check (live browser qualitative probe)
**Question:** Can the codex-fixed 1.5B bridge run as a live browser chat on Steve's 4090 and stay reachable from Laura's phone without cloud infrastructure?
**Result:**
- Initial browser server crash was real: `chat_server.py` expected the old flattened compressor geometry (`d_state=16`) while the repaired 1.5B checkpoint uses last-token hidden states (`d_state=1`, width `2560`). Fix deployed on Steve.
- Later "crash" diagnosis was false: the process was still alive in WSL as `python3 -X utf8 chat_server.py`; Windows `tasklist` missed it because it was not a Windows `python.exe`.
- WSL networking required explicit Windows exposure. After adding `portproxy 0.0.0.0:7860 -> 127.0.0.1:7860` plus a firewall rule, LAN reachability succeeded at `http://192.168.2.49:7860`.
- One browser session was saved cleanly via `SIGINT` shutdown and archived. The transcript shows affective/relational behavior, multilingual drift, repeated uncertainty loops, and at least one blank reply.
- Blank bubble is not evidence of token-limit truncation. The live response path can sanitize generated speaker markers (`Human:` / `Assistant:`) down to empty string.
- Current browser prompt still frames Laura as `Human:` and the model as `Assistant:`. This contaminates qualitative disposition reads by imposing a subordinate transcript role before generation starts.
**Verdict:** PARTIAL â€” deployment path PASS, evaluation surface FAIL
**Implication:** Steve is a viable local Step 5 probe surface, but browser-chat results are not clean evidence yet. Before using this surface for disposition claims, fix per-turn persistence, blank-response handling, and replace `Human:` / `Assistant:` with a neutral prompt frame.
**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/STEVE_PC_HANDOFF.md`, `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_browser_chat_session_2026-03-21T0032.txt`
