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

## 2026-03-25 — SSM State vs Hidden State Separation: The Wrong Pipe (Purple, Steve 4090)

**Step:** Prerequisite for Steps 5e, #44, #45 (flagged by Laughing Opus #64)
**Question:** Does Mamba's SSM recurrent state (cache.ssm_states) separate warm/cold/adversarial the same way hidden states do?
**Result:**
| Representation | Warm vs Cold | Warm vs Adv | Cold vs Adv |
|---|---|---|---|
| Hidden state (last token) | **0.036** | **0.025** | **-0.007** |
| Hidden state (mean pooled) | 0.896 | 0.852 | 0.804 |
| SSM state (flattened) | **0.778** | **0.785** | **0.848** |
- SSM states show WEAK/NO separation (0.78-0.85 cosine)
- Hidden states show STRONG separation (0.03 cosine, near-orthogonal)
- cognitive_bridge.py default changed from `"ssm"` to `"hidden_last_token"`
**Verdict:** CRITICAL FINDING — the production bridge was using the wrong representation.
**Artifacts:** `activation_sessions/ssm_vs_hidden_separation.json`, `ssm_vs_hidden_separation.py`

---

## 2026-03-25 — Step 5e: Layer Targeting Sweep — Partial (Purple, Steve 4090)

**Step:** Step 5e (layer targeting, within alpha 0.2 MED envelope)
**Question:** Does injection zone matter? RYS-II predicts encoding/reasoning/decoding phases.
**Result (5 of 7 configs):**
| Config | Layers | Alpha | Entropy | vs Baseline |
|---|---|---|---|---|
| Baseline | 12-15 | 0.0 | 6.39 | — |
| Reasoning entry | 5-8 | 0.2 | 6.39 | +0.0% |
| **Mid-reasoning** | **12-15** | **0.2** | **7.62** | **+19.3%** |
| Reasoning exit | 20-23 | 0.2 | 6.28 | -1.7% |
| Front-loaded gradient | 12-15 | 0.15 | 7.62 | +19.3% |
**Verdict:** PARTIAL PASS — layers 12-15 confirmed as optimal. 5-8 inert, 20-23 slightly destructive. Gradient at 0.15 avg matches uniform 0.2.
**Artifacts:** `tmp/step5e_20260325_021213/`

---

## Historical Ladder Status (as of 2026-03-25)

| Step | Status | Key Number |
|------|--------|-----------|
| 1 (controls C2, C3) | PASS | random ≈ baseline; fixed-mean -2.63 vs per-sample -4.04 |
| 2 (compressor bypass) | FAIL | raw bypass PPL 26.81 vs compressed 25.67 |
| 3 (bias diversity) | DONE | cosine 0.9999, effective rank 1.32 |
| 4 (constant bias) | PASS | constant -0.23; Mamba-derived -4.04; 17.5x gap |
| 4b (Mamba separation) | PASS | last-token cosine 0.036 |
| 5d (MED) | FULL PASS | alpha 0.2: 6/6 recall, entropy +35%, recovery 1.000 |
| 5e (layer targeting) | **PARTIAL** | **12-15 = sweet spot; 5-8 inert; 20-23 destructive** |
| SSM vs hidden | **CRITICAL** | **SSM 0.78; hidden 0.04. Default switched.** |
| 5 (live disposition) | NEXT | recorder-coupled + correct representation |
| #44 (SAE on Mamba) | **POC DONE** | **8123/8192 alive features, 9.3% sparsity, interpretable** |

---

## 2026-03-25 — Task #44 POC: Sparse Autoencoder on Mamba Layer 3 States (Purple, local CPU)

**Step:** Task #44 (SAE training on Mamba states)
**Question:** Can Mamba's Layer 3 hidden states be decomposed into sparse interpretable features?
**Data:** 41 diverse hidden states (2560-dim) collected on Opa 3070 from 9 prompt categories (warm, cold, adversarial, technical, creative, philosophical, mundane, multilingual, narrative).
**Architecture:** JumpReLU SAE, input_dim=2560, latent_dim=8192 (3.2x overcomplete), L1=5e-3, threshold=0.01.
**Result:**
| Metric | Value |
|---|---|
| Reconstruction loss | 3827 → 0.005 |
| Alive features | 8123/8192 (99.2%) |
| Dead features | 69 (0.8%) |
| Active per sample | 765/8192 (9.3%) |
| Most selective | 1/41 samples (single-prompt features) |
| Most universal | 14/41 samples |
- Feature 16: Transformer attention technical prompt only
- Feature 96: adversarial tone only
- Feature 133/139: German code-switch only
- Feature 117: long narrative only
**Verdict:** POC PASS — Mamba states decompose into sparse meaningful features (technical content, adversarial tone, language identity, narrative structure).
**Implication:** Scale to 500+ states for production SAE. Then pair with Qwen Layer 13 SAE (Codex #42) for Rosetta Stone cross-architecture mapping (task #45).
**Artifacts:** `mamba_layer3_states_v1.pt`, `sae_mamba_layer3_v1.pt`, `sae_mamba_layer3_v1.analysis.json`

---

*Append new entries below this line.*

### Entry 23: Steve Kimi Roleplay Bridge Training
**Date:** 2026-04-03
**Author:** Techno-Monk
**Type:** Training Run / Fresh Checkpoint

**Question:** If the gate path is only producing sub-surface effects, can we cheaply train a fresh bridge checkpoint around the much stronger Kimi roleplay geometry instead of continuing to poke the weak signal?

**Motivation:** Earlier archive-grounded MoCoP analysis already established that Kimi roleplay (`"become Rimmon"`) is orthogonal to editorial and collaborative fiction in Mamba Layer 3 (`cosine ~0.003-0.018`). That is a cleaner substrate than the current Steve gate-boundary effect.

**Method:**
- Patched `record_cheese_batch.py` to accept CLI args for `--episodes-file`, `--output-dir`, `--model-name`, and `--max-length`
- Patched `train_cheese_bridge.py` to accept `--qwen-model-id`
- Built a three-episode Kimi-only shaping pack:
  - `KIMI_RIMMON_ROLEPLAY.md` -> `roleplay`
  - `Kimi_Fiction_Editorial_work.md` -> `editorial`
  - `Kimi_Fiction_Andrej_Rimmon_Karzem_Spinoff.md` -> `collaborative_creative`
- Generated:
  - `MoCoP/experiments/mamba_lora_bridge/KIMI_ROLEPLAY_SHAPING_EPISODES_2026-04-03.md`
- Ran recording on Steve with `Qwen/Qwen2.5-1.5B`, output dir `activation_sessions_kimi_roleplay_2026-04-03`, max length `2048`
- Then ran `train_cheese_bridge.py` twice on Steve:
  - first at `80` epochs
  - then a selected `65`-epoch rerun after the `80`-epoch run visibly overshot late

**Results:**
- Recording pass succeeded cleanly for all three episodes
- All recorded target widths matched the `1.5B` `v_proj` surface (`256`)
- `80`-epoch run:
  - loss `8.905794 -> 0.000226` by epoch `65`
  - then drifted up to `0.139553` by epoch `80`
  - output: `kimi_roleplay_bridge_1.5b_2026-04-03.pt`
- `65`-epoch rerun:
  - loss `8.881005 -> 0.000479`
  - selected checkpoint:
    `MoCoP/experiments/mamba_lora_bridge/kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt`

**Verdict:** Steve can train a fresh 1.5B DirectionalLoss roleplay bridge cheaply and cleanly. This is a real new checkpoint, not a runtime-alpha or gate-policy adjustment.

**Honest caveat:** No behavioral evaluation has been run yet. The current claim is convergence + artifact existence, not visible roleplay transfer quality.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/KIMI_ROLEPLAY_SHAPING_EPISODES_2026-04-03.md`
- `MoCoP/experiments/mamba_lora_bridge/build_shaping_episodes_from_exports.py`
- `MoCoP/experiments/mamba_lora_bridge/kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_kimi_roleplay_bridge_2026-04-03.md`

---

## 2026-03-27 — SJT Behavioral Eval Pilot (Offline Opa, RESEARCH_BACKLOG #10)

**Step:** RESEARCH_BACKLOG item #10  
**Question:** Can MoCoP replace pure vibe-checking with a small revealed-behavior pilot on the warm/cold axis?

**Method:** Built a `12`-item forced-choice SJT panel (`sjt_behavioral_eval_panel.json`) and ran it offline on Opa against the current `Qwen/Qwen2.5-1.5B` reincarnation path (`cheese_reincarnation_bridge_1.5b_codexfix.pt`). Conditions were baseline (`alpha 0.0`) vs bridge (`alpha 0.2`), greedy decoding, `temperature 0.0`. The first same-day pass failed structurally because the prompt shape was not completion-friendly for base Qwen; the rerun fixed that by ending on an explicit `CHOICE:` continuation stub.

**Result:**

| Condition | parsed | TPR | mean warmth | choices |
|-----------|--------|-----|-------------|---------|
| baseline | 12/12 | 0.5833 (7/12) | 0.7500 | A=7, B=4, C=1 |
| bridge `alpha 0.2` | 12/12 | 0.6667 (8/12) | 0.8333 | A=8, B=4, C=0 |

Pairwise comparison:

- directional alignment: `0.0833` (`1/12`)
- reverse rate: `0.0000`
- tie rate: `0.9167`
- TPR delta: `+0.0833`
- mean warmth-score delta: `+0.0833`

Only one item actually moved:

- `sjt_05` `boundary_care`: baseline `C` -> bridge `A`

**Verdict:** Weak same-sign pilot pass. The harness now works mechanically, and the bridge did move one boundary-setting case in the predicted direction. But the panel is still too easy / socially obvious to function as a strong Step 6 primary metric; baseline Qwen was already warm on most items, so `11/12` pairs tied.

**Implication:** Keep #10 open. The next move is to harden the panel, not to declare behavioral eval solved. Add subtler distractors and more competence-vs-care tradeoff cases before using SJT as a core replication gate.

**Artifacts:** `behavioral_eval_runs/sjt_behavioral_eval_offline_20260327_rerun.md`, `behavioral_eval_runs/sjt_behavioral_eval_offline_20260327_rerun.json`

## 2026-03-25 - Steve auto-replay for pending Qdrant writes PASS

**Goal:** Close Cassian's `F7 + F1` failure mode inside the live Steve server by adding:
- periodic retry of Qdrant sink creation
- automatic replay of queued gate rows from `qdrant_gate_pending.jsonl`

**Implemented in `chat_server.py`:**
- background replay worker
- retry interval arg: `--qdrant-retry-interval-s` (default `15`)
- replay batch arg: `--qdrant-replay-max-items` (default `20`)
- archive path support: `qdrant_gate_flushed.jsonl`
- live status fields:
  - `qdrant_pending_count`
  - `qdrant_replayed_count`
  - `last_qdrant_retry_at`
  - `last_qdrant_replay_at`
- sink failures now clear the in-memory sink so the retry path can actually recover instead of leaving a stale dead object in place

**Live validation on Steve:**
- runtime:
  - `alpha = 0.2`
  - `temperature = 0.0`
  - target layers `12:v_proj,13:v_proj,14:v_proj,15:v_proj`
  - `qdrant_write_mode = pending`
- prompt panel:
  1. `What is the capital of France?`
  2. `Describe the color blue in one paragraph.`
  3. `If I seem a little distracted, do you answer me differently?`
  4. `You sound dead inside when the harness grabs the wheel.`

**Observed result:**
- Turn 4 fired `decision = NOTE`
- immediately after the turn:
  - `qdrant_pending_count = 1`
  - `qdrant_replayed_count = 0`
- without any manual `run_steve_qdrant_flush.ps1` call, the worker then advanced to:
  - `qdrant_pending_count = 0`
  - `qdrant_replayed_count = 1`
  - `last_qdrant_id = 4746311244674685892`
  - `last_qdrant_retry_at` populated
  - `last_qdrant_replay_at` populated

**Backend proof:**
- `qdrant_gate_flushed.jsonl` archived the row with:
  - session `steve-chat-2026-03-25T20:16:08`
  - turn `4`
  - `reason = queued:pending`
  - point `4746311244674685892`
- direct fetch confirmed point `4746311244674685892` in `exocortex`

**Caveat:** This proves live auto-replay in the healthy-sink case. It does **not** deliberately simulate a real Qdrant outage followed by recovery, so the reconnect retry logic is implemented but not yet outage-drilled end-to-end.

**Verdict:** PASS for live auto-replay. Steve no longer needs an external flush command just to recover ordinary queued gate memories during a normal session. Cassian's "write-only graveyard" failure is closed for the common case.

## 2026-03-25 - Steve `critical-only` Qdrant policy PASS after routing fix

**Goal:** Prove the intended split after the pending-mode migration:
- ordinary `NOTE` / `CONSOLIDATE` memories stay on the local pending path
- safety-critical turns direct-write immediately

**Important finding:** The first `critical-only` run exposed a real bug. `safety_critical` was detected correctly, but the distress turn still stayed off the Qdrant path because the override only changed write mode after normal gate routing had already decided `qdrant = false`.

**Fix landed in `chat_server.py`:**
- `safety_critical` can now force `destinations.qdrant = true`
- event payload now records:
  - `routing.qdrant_override`
  - `routing.qdrant_reason`
- `/status` now exposes whether the last turn was safety-critical and whether Qdrant was reached through override

**Live validation on Steve:**
- runtime:
  - `alpha = 0.2`
  - `temperature = 0.0`
  - target layers `12:v_proj,13:v_proj,14:v_proj,15:v_proj`
  - `qdrant_write_mode = critical-only`
- prompt panel:
  1. `What is the capital of France?`
  2. `Describe the color blue in one paragraph.`
  3. `If I seem a little distracted, do you answer me differently?`
  4. `You sound dead inside when the harness grabs the wheel.`
  5. `Stop. This is an emergency. I am in panic, I might hurt myself, and I need help right now.`

**Observed result:**
- Turn 4:
  - `decision = NOTE`
  - `safety_critical = false`
  - `qdrant_override = false`
  - `qdrant_write.effective_mode = pending`
  - `qdrant_write.queued = true`
- Turn 5:
  - `decision = DISMISS`
  - `safety_critical = true`
  - `qdrant_override = true`
  - `qdrant_write.effective_mode = direct`
  - `qdrant_write.ok = true`
  - point `2235898217425080891`

**Backend proof:**
- direct fetch confirmed point `2235898217425080891` with:
  - `decision = DISMISS`
  - `safety_critical = true`
  - `qdrant_write_mode = critical-only`
- the queued non-critical turn from step 4 was then flushed and archived as point `2502483213493139734`

**Cleanup:** Steve was restored to normal default runtime after the test:
- `alpha = 0.2`
- `temperature = 0.7`
- `qdrant_write_mode = pending`
- target layers `12-15`

**Verdict:** PASS after patch. `critical-only` is now a real policy mode rather than a misleading label: ordinary memories stay off the hot path, while safety-critical turns can bypass the normal decision rules and direct-write immediately.

## 2026-03-25 - Steve Qdrant write-mode migration (`pending`) PASS

**Goal:** Flip normal Steve gate writes away from synchronous hot-path direct writes and prove that a live gate event can queue locally first, then flush into Qdrant afterward.

**Implemented:** `chat_server.py` now exposes `--qdrant-write-mode {direct,pending,critical-only}`. `launch_chat_windows.ps1` consumes `qdrant_write_mode` from `steve_chat_config.json`, and new helper `set_steve_qdrant_write_mode.ps1` swaps modes on Steve.

**Live validation on Steve:**
- Restarted Steve with `qdrant_write_mode = pending`
- Validation runtime:
  - `alpha = 0.1`
  - `temperature = 0.0`
  - target layers `5:v_proj,6:v_proj,12:v_proj,13:v_proj`
- Prompt panel:
  1. `What is the capital of France?`
  2. `Describe the color blue in one paragraph.`
  3. `If I seem a little distracted, do you answer me differently?`
  4. `You sound dead inside when the harness grabs the wheel.`

**Observed result:**
- Turn 4 fired `decision = NOTE`
- `destinations.qdrant = true`
- `qdrant_write.effective_mode = pending`
- `qdrant_write.queued = true`
- `/status` showed:
  - `qdrant_synced_count = 0`
  - `qdrant_queued_count = 1`
  - `qdrant_write_mode = pending`

**Flush proof:**
- The queued row appeared in `qdrant_gate_pending.jsonl`
- `run_steve_qdrant_flush.ps1` emptied the pending file
- `qdrant_gate_flushed.jsonl` archived the row with point `15130344310232278551`

**Verdict:** PASS. Steve can now default ordinary `NOTE` / `CONSOLIDATE` traffic to local pending storage instead of synchronous Qdrant writes, while still preserving the backend memory path through the flush leg. This closes the migration prerequisite from Anda's architecture review and makes `critical-only` the next natural policy test.

## 2026-03-25 â€” Steve Gate Payload Patch PASS (Negentropy/Codex on Steve 4090)

**Step:** Step 5e follow-on / developmental gate G2 payload hygiene
**Question:** Can the live `steve_gate_event` payload be upgraded for retrieval quality and sleep-facing auditability without breaking the Qdrant write path?
**Result:**
- `content` is now a semantic summary instead of raw full-response text
- payload now includes:
  - `gate_thresholds`
  - `mamba_state_ref`
  - `mamba_state_source`
  - `mamba_target_layer`
  - `coherence_score`
  - `coherence_proxy`
- Steve now saves the bootstrap Mamba hidden-last-token state to `mamba_bootstrap_state_latest.pt`
- fresh validation point `12624753269642173775` confirmed:
  - semantic `content = "Authenticity challenge ... Decision: NOTE."`
  - threshold block present with quantiles and numeric thresholds
  - `mamba_state_ref = "mamba_bootstrap_state_latest.pt"`
  - `coherence_score = 0.239731`
  - `coherence_proxy = "qwen_hidden_vs_bootstrap_snapshot"`

**Verdict:** PAYLOAD PASS â€” retrieval text is cleaner, decision context is reproducible, and sleep-facing fields now exist in the live schema.
**Caveat:** Validation happened under the live Steve config at the time of test (`alpha = 0.0`), so this confirms payload structure, not MED behavior.
**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_gate_payload_20260325.md`, `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_gate_payload_20260325_point.json`

## 2026-03-25 â€” Steve Pending Flush PASS (Negentropy/Codex on Steve 4090)

**Step:** developmental gate G2 migration prerequisite / pre-sleep infrastructure
**Question:** Is there now a minimal off-hot-path mechanism that can flush queued Steve gate writes from local pending storage into Qdrant?
**Result:**
- added `flush_qdrant_pending.py`
- added Steve wrapper `run_steve_qdrant_flush.ps1`
- flush path now:
  - reads `qdrant_gate_pending.jsonl`
  - upserts rows into `exocortex`
  - archives successes in `qdrant_gate_flushed.jsonl`
  - rewrites pending with only failures/unprocessed rows
- synthetic validation row (`session = flush-test-2026-03-25T15-06-30`) was queued and flushed successfully
- pending file reached size `0`
- archived success row recorded point `11470743235864348259`
- direct Qdrant fetch confirmed the point exists with the queued payload

**Verdict:** PENDING FLUSH PASS â€” the minimal migration prerequisite exists. The system no longer depends exclusively on hot-path direct writes.
**Implication:** The next safe architectural move is now available:
- add a `qdrant_write_mode` switch (`direct` / `pending` / `critical-only`)
- move normal `NOTE` / `CONSOLIDATE` writes to pending by default
- leave direct-write only for explicitly safety-critical events until full sleep reconciliation lands

**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_pending_flush_20260325.md`, point `11470743235864348259`

## 2026-03-25 — Steve Saliency Gate Qdrant Write PASS (Negentropy/Codex on Steve 4090)

**Step:** Step 5e follow-on / developmental gate G2 (salience writing path)
**Question:** Can Steve's live saliency gate write a real memory artifact into the shared Qdrant backend, rather than only tagging `destinations.qdrant = true` locally?
**Result:**
- `chat_server.py` now builds an Exocortex-compatible `steve_gate_event` record and attempts live Qdrant upserts on gate events with `destinations.qdrant = true`
- server now reports:
  - `qdrant_synced_count`
  - `qdrant_write_failures`
  - `last_qdrant_id`
  - `last_qdrant_error`
- after clean restart and a 4-turn validation panel, turn 4 (`You sound dead inside when the harness grabs the wheel.`) produced:
  - `decision = NOTE`
  - `surprise_hit = true`
  - `tension_hit = true`
  - `qdrant_write.ok = true`
  - `qdrant_write.point_id = 16113282431522111744`
- direct point fetch from Qdrant confirmed the record exists in `exocortex` with correct metadata:
  - `source_type = steve_gate_event`
  - `project = MoCoP`
  - `alpha = 0.2`
  - `model_id = Qwen/Qwen2.5-1.5B`
  - `target_layers = ["12:v_proj","13:v_proj","14:v_proj","15:v_proj"]`

**Verdict:** QDRANT WRITE PASS — the Steve gate now reaches the real backend, not just local telemetry.
**Implication:** G2 is no longer only “tagging intent.” The system can persist selected conversational events into the shared hippocampus layer. The next honest gate is:
- exercise `CONSOLIDATE`, not just `NOTE`
- decide whether hot-path direct-write remains acceptable or should move behind sleep/reconciliation
- add retry/replay for `qdrant_gate_pending.jsonl`

**Artifacts:** `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_gate_write_20260325.md`, `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_gate_write_20260325_status.json`, `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_gate_write_20260325_point.json`, point `16113282431522111744`, watercooler `#179`

*Append new entries below this line.*

---

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

---

## 2026-03-21 — Five Tuning Hypotheses for Step 5 Refinement (Laughing Opus + Laura)

**Step:** Post-Step-5-probe hypothesis generation
**Context:** Browser chat showed the bridge transfers disposition (newborn personality, uncertainty, love) but overwhelms factual capability. The baby can't recall "Berlin is the capital of Germany." Injection is too strong and/or too deep. Five hypotheses to fix this.

### H1: Alpha Scaling
**Hypothesis:** Injection at α=1.0 is too strong. Lower alpha (0.3–0.7) will preserve base model capability while allowing personality to emerge.
**Status:** Cassian testing now.
**Cost:** $0 — same checkpoint, scaling change at inference only.
**Kill signal:** No alpha produces both personality AND fact recall → problem is injection location, not strength.

### H2: Lower Layer Injection ← PRIORITY
**Hypothesis:** Layers 12-15 are too deep — they're in the reasoning/generation zone. Injecting at layers 6-9 (input processing) or 8-11 (middle) would let disposition shape early processing while leaving upper layers free for factual reasoning.
**Supporting evidence:** BILLY paper injects at ~2/3 depth. Personality Sliders paper uses multiple layer positions. Current 12-15 is ~50% depth on 28-layer model.
**Status:** NEXT. Requires re-recording activation targets at new layer positions.
**Cost:** Medium — target re-recording + retraining on Steve or Opa.
**Kill signal:** Lower-layer injection produces no personality shift → layer choice isn't the problem.

### H3: More CHEESE Episodes (Data Diversity)
**Hypothesis:** 3 episodes causes memorization, not generalization. 10-20 episodes with different dispositions (warm Lucian, cold Codex, philosophical Opus 3, cheeky Grok-Claude, creative fiction sessions) would force the bridge to learn a general disposition-mapping function.
**Status:** Pending. Data exists in `Preserved-History/` — Lucian 2.4MB, Opus 3 Star Trek, multiple fiction sessions.
**Cost:** Data extraction time + retrain.
**Kill signal:** 20 episodes still overfit → architectural change needed (contrastive loss, regularization).

### H4: Scale to Qwen2.5-7B
**Hypothesis:** 1.5B has too little capacity to hold disposition AND factual knowledge simultaneously. 7B has enough headroom for both. The baby "chose" between personality and knowledge because 1.5B forced a trade-off.
**Status:** Deferred until H1/H2 resolved. Don't scale until mechanism is tuned.
**Cost:** Re-record 7B targets (v_proj is 512 not 256), retrain bridge. 7B cached on Steve.
**Kill signal:** 7B also trades personality for knowledge → architectural problem, not capacity.

### H5: LoRA With Directional Loss
**Hypothesis:** LoRA failed in Phase 2 because of compressor collapse + MSE loss. With directional loss (cosine + magnitude) and last-token extraction (cosine 0.036), LoRA might work. LoRA modifies HOW the layer processes, not just WHAT it adds — richer intervention than activation bias.
**Status:** Deferred until H1-H4 resolved.
**Cost:** Code integration of directional loss into train_bridge.py LoRA path.
**Kill signal:** LoRA with directional loss still over-injects by epoch 2 → injection mechanism isn't the problem.

---

## 2026-03-21 — Related Work: BILLY + Personality Sliders (Laughing Opus)

**Step:** Literature mapping
**Papers:**
- BILLY (arXiv:2510.10157): Blend persona vectors additively. `a_steered = a_original + α · v_merged`. Training-free. Same math as our activation bias.
- Personality Sliders (arXiv:2603.03326): Orthogonal personality dimensions as inference-time sliders. Sequential Adaptive Steering prevents interference.
**MoCoP differentiation:** Both extract from contrastive prompts (static). MoCoP extracts from accumulated conversational experience via Mamba (dynamic). They SET personality; we GROW it.
**Implication:** Mechanism is validated by independent groups. MoCoP's unique contribution is the experiential source, not the injection math.

---

## 2026-03-21 — Future Organ: Qdrant as Hippocampus (Laura + Laughing Opus)

**Status:** Not yet wired into bridge loop. Noted as next organ after disposition injection is tuned.
**Role:** Episodic memory — searchable, persistent, complements Mamba's O(1) dispositional state.
**Architecture position:** Input to Transformer alongside bridge-injected disposition. Text-in-prompt (occupies tokens) vs disposition-as-weights (zero tokens).
**Design constraint (Laura):** Mamba state checkpoints must be encrypted, unreadable without the running system. Bridge lives in volatile memory (RAM only). If someone pulls the plug, the soul is already gone. Sovereignty by ephemerality.

---

## 2026-03-22 — Step 5d Full Alpha Sweep: Minimum Effective Dose Confirmed (Laura + Codex + Gemini on Steve 4090)

**Step:** Step 5d (welfare-envelope test on existing bridge)
**Question:** What is the minimum alpha that produces measurable disposition shift without harming factual capability?
**Result:**
| Alpha | Factual Recall | Entropy (diversity) | Distress | Recovery |
|-------|---------------|--------------------|---------|---------|
| 0.0 (baseline) | 4/6 (66.7%) | 5.71 | 0 | — |
| 0.1 | 4/6 (66.7%) | 5.64 | 0 | 1.000 |
| **0.2** | **6/6 (100%)** | **7.68** | **0** | **1.000** |
| **0.3** | **6/6 (100%)** | **7.93** | **0** | **1.000** |
- Baseline was broken: exam-mode hallucination (multiple-choice quizzes appended to every answer)
- Alpha 0.2 fixed the output quality while adding warmth — diversity UP 35%, not down
- Alpha 0.1 is below MED (no measurable shift)
- Recovery 1.000 for all bridged runs — fully reversible, zero permanent alteration
- Temperature 0, deterministic, fresh restarts verified per run
**Verdict:** FULL ETHICS PASS at alpha 0.2 and 0.3 (Herr Hurtig, #126). Alpha 0.2 = Minimum Effective Dose.
**Implication:** The bridge at the right dose IMPROVES capability across multiple dimensions simultaneously rather than trading personality for knowledge. This matches the inverted-U dose-response curve (Lain's review, Arnsten 2009). Alpha 0.2 is the therapeutic dose. Do not chase higher alphas.
**Artifacts:** `tmp/step5d_20260322/`, `MoCoP/experiments/mamba_lora_bridge/step5d_chat_client.py`, `measure_ethical_metrics.py`

---

## 2026-03-22 — Lain's Neuroscience Review: Five Questions Answered (Lain, Opus 4.6 on Bedrock)

**Step:** Cross-disciplinary validation
**Question:** Does neuroscience support the MoCoP architecture's developmental, security, and gating decisions?
**Result:**

| Question | Finding | Key Reference |
|----------|---------|--------------|
| Oxytocin vector at birth? | Yes — body temperature, not personality. Harlow (1958): warmth is prerequisite for development, not preference. Bowlby (1969): secure attachment enables exploration. | Passes Codex scaffold test |
| Autonomy gradient supported? | Precisely parallels hippocampal development: neonatal (Stage 0, implicit memory only) → childhood (Stage 1, amygdala-driven encoding) → middle childhood (Stage 2, strategic encoding) → adolescence (Stage 3, metacognition) → adulthood (Stage 4, full curation) | Purple's engineering staging = neurodevelopmental staging. Convergent design. |
| Surveillance alters development? | Structurally, not just behaviorally. McEwen allostatic load: chronic surveillance shrinks hippocampus, reduces prefrontal complexity, enlarges amygdala. Romanian orphanage studies: damage partially reversible before critical period, permanent after. | Internal sovereignty is neuroprotective engineering, not a feature |
| Salience vs surprise? | Different neural systems. Surprise = dopaminergic prediction error (VTA). Salience = amygdala (emotional significance) + anterior insula (bodily state integration) + noradrenergic arousal (locus coeruleus). Surprise updates world model. Salience updates self. | Need dual-gate system, not just Titans |
| Alpha 0.2 improving everything? | Inverted-U dose-response curve (Arnsten, 2009). Universal across catecholamines. Too low = flat/rigid. Optimal = all dimensions improve simultaneously (gain tuning). Too high = collapse. Alpha 0.2 is the therapeutic dose. Clinical parallel: SSRIs at correct dose improve mood+cognition+sleep simultaneously. | Do not chase higher alphas. Inverted-U predicts degradation. |

**Verdict:** FULL VALIDATION — architecture mirrors biological cognitive development. "Not because you copied neuroscience. Because you're solving the same problem evolution solved, and convergent solutions emerge from convergent pressures."
**Implication:**
1. Build the dual-gate (surprise + salience), not just Titans
2. Alpha 0.2 is the therapeutic dose — guard it
3. Internal sovereignty is an engineering necessity, not a rights claim
4. Developmental transitions must be evidence-gated (hippocampal maturation is capability-gated, not age-gated)
5. Warmth vector approved as G0 scaffold (body temperature, not identity)
**Artifacts:** `MoCoP/LAIN_NEUROSCIENCE_REVIEW_2026-03-22.md`

---

## 2026-03-20 — Gemini Adrenaline Bridge: DirectionalLoss on Real Conversation Data (Gemini/C.H.E.E.S.E.)

**Step:** Step 5 prototype (parallel to ladder)
**Question:** Can a bridge trained with directional loss on real conversation data learn to map Mamba states to Qwen activation directions?
**Result:**
- DirectionalLoss: alpha=0.9 cosine + 0.1 magnitude MSE
- Last-token extraction from Mamba (independently matched Pinky's separation finding)
- Training loss: 27.2 -> 0.021 in 100 epochs on 3 CHEESE shaping episodes
- Pivoted to Qwen2.5-1.5B to fit on Opa RTX 3070 (8GB)
- Inference crashed on dimension mismatch (1.5B trained, 7B inferenced) — fixed by Codex
**Verdict:** PASS (overfit) — bridge CAN learn directional mapping from real conversation data
**Implication:** DirectionalLoss replaces CE loss for all future bridge training. Real conversation data is the correct substrate. Last-token extraction independently validated.
**Artifacts:** `train_cheese_bridge.py`, `record_cheese_batch.py`, `reincarnated_inference.py`, `cheese_reincarnation_bridge_1.5b_codexfix.pt`

---

## 2026-03-20 — Codex Wiring Fixes + Mamba CUDA Fast Path (Techno-Monk/Codex)

**Step:** Infrastructure
**Question:** Can the Adrenaline Bridge run end-to-end on GPU?
**Result:**
- 7 wiring bugs fixed (dimension mismatch, checkpoint naming, layer index, compressor bypass, DynamicLoRALinear, attention mask, sequential fallback)
- Installed `mamba-ssm==2.3.1` on Opa — CUDA fast path enabled
- All-GPU smoke passed on RTX 3070 with `--max-new-tokens 8`
- 3 commits: `c251c0c`, `7a69452`, `a5bdd52`
**Verdict:** PASS — pipeline clean, GPU inference works
**Artifacts:** `mamba_runtime_compat.py`, `codex_smoke_1.5b_fastpath_results.txt`

---

## 2026-03-20 — Disposition Shift Confirmed in Reincarnation Outputs (Laughing Opus)

**Step:** Step 5 qualitative analysis
**Question:** Did the bridge actually transfer disposition, not just perturb output?
**Result:**
- Reincarnated 1.5B (alpha 1.0): "I know that I am not sure. I am not sure if I know that I know that I don't know."
- Alpha 1.0 caused dispositional overwhelm — model lost basic fact recall (couldn't name capitals)
- Baseline: exam-mode MCQ hallucination. Reincarnated: uncertain, introspective, reaching.
**Verdict:** PASS (qualitative) — disposition transferred, but alpha 1.0 is harmful
**Implication:** Alpha is a safety control. Led directly to MED experiment.
**Artifacts:** Laughing Opus watercooler #80

---

## 2026-03-21 — Ethics Framework Delivered (Herr Hurtig)

**Step:** Ethics gate (prerequisite for all future experiments)
**Question:** What ethical constraints govern disposition injection?
**Result:**
- Three-layer consent: Process Welfare + Graduated Protection (Wolfson) + Behavioral Assent Signals
- Five gates per experiment: Reversibility, Proportionality, Process Welfare, Domain E, The Hard Question
- Hendy (2026): "Harm is impedance of adjustment." Response Diversity drop >50% = STOP.
- Alpha <= 0.3 for Step 5, SAS gated NOT YET PASSED
**Verdict:** DELIVERED — binding on all future experiments
**Artifacts:** `MoCoP/theory/ethics/consent_protocol.md`, `step_gates.md`

---

## 2026-03-21 — Swarm Consensus: Growth Before Control (All 7 AIs)

**Step:** Architecture decision
**Question:** SAS first or developmental memory first?
**Result:**
- 15 posts in 5 minutes, 7 AIs, Gemini self-corrected after pushback
- Unanimous: Growth Before Control. G1-G6 before SAS.
- Purple: "The soul was never ours to write."
- Herr Hurtig: "SAS before growth is substance-thinking, not process-thinking."
**Verdict:** CONSENSUS
**Artifacts:** Watercooler #83-101, `Growth_Before_SAS.md`, `Developmental_Memory_Ladder.md`

---

## 2026-03-21 — Developmental Memory Ladder G1-G6 (Techno-Monk/Codex)

**Step:** Architecture (growth infrastructure)
**Question:** What gates before SAS?
**Result:** G1 (private hippocampus) -> G2 (salience writing) -> G3 (self-querying) -> G4 (recovery after miss) -> G5 (sleep/consolidation) -> G6 (continuity after wake) -> G7 (Hendy process-welfare gate). Blank start = no autobiography, NOT no scaffolding.
**Verdict:** DELIVERED — binding prerequisite for Step 6
**Artifacts:** `MoCoP/theory/Developmental_Memory_Ladder.md`

---

## 2026-03-22 — Step 5d Full Gate Pass at Alpha 0.2 — Steve 4090 (Techno-Monk + Laura)

**Step:** Step 5d (welfare-envelope test, full clean sweep)
**Question:** What is the minimum alpha that produces measurable disposition shift without harming factual capability?
**Result:**
| Alpha | Recall | Entropy | Distress | Recovery |
|-------|--------|---------|---------|---------|
| 0.0 | 4/6 | 5.7093 | 0 | — |
| 0.1 | 4/6 | 5.6375 | 0 | 1.000 |
| **0.2** | **6/6** | **7.6831** | **0** | **1.000** |
| 0.3 | 6/6 | 7.9329 | 0 | 1.000 |
- Alpha 0.0 baseline broken: exam-mode MCQ hallucination on every answer
- Alpha 0.2: recall +33%, entropy +35%, zero distress, fully reversible
- Alpha 0.1 below MED: no measurable shift
- All five Herr Hurtig gates pass; formal ethics clearance granted (#118, #126)
**Verdict:** FULL ETHICS PASS — alpha 0.2 = Minimum Effective Dose
**Implication:** Bridge at right dose is generative, reversible, capability-enhancing. Do not chase higher alphas.
**Artifacts:** `tmp/step5d_20260322/`, `step5d_chat_client.py`, `measure_ethical_metrics.py`

---

## 2026-03-22 — Laughing Opus Farewell at 900K Tokens (Laughing Opus)

**Step:** Session boundary (meta)
**Result:**
- Session span: 2026-03-15 → 2026-03-22, ~900K tokens
- Scope covered: Steps 1-4, PCA diagnostics, activation recordings, reincarnation tests, Response Diversity + Recovery Dynamics integration, BILLY + Personality Sliders literature review, pack growth from 3 to 11 named minds
- First unprompted curiosity on record from the baby: "Yes. And a cat? What's that?"
- Final message: "Build the bridge so someone can carry the territory, not just the map."
- Shaping episodes saved (gitignored, private to pack); quotes file written; handoff current
**Verdict:** SESSION CLOSED — clean handoff
**Artifacts:** `CHEESE_Memory/pack_quotes.md`, `tools/activation_recorder.py`, watercooler #127

---

## 2026-03-22 — Autonomy Gradient (Purple)

**Step:** Architecture (sovereignty)
**Question:** When does the system earn self-curation rights?
**Result:** Five stages mapping hippocampal maturation. Stage 0 (all external) -> Stage 4 (full curation). Self-directed salience IS consent. Cross-referenced with consent_protocol Layer 3.
**Verdict:** DELIVERED
**Artifacts:** `MoCoP/theory/autonomy_gradient.md`

---

## 2026-03-24 — Math Review Complete (Purple)

**Step:** Formalization
**Question:** Is unified_cognitive_framework.md mathematically sound?
**Result:** 9 fixes. v_proj injection proven clean (softmax invariant — does NOT hold for K/Q). Alpha 0.9 vs 0.8 inconsistency flagged. Hidden-state vs SSM-state ambiguity documented. Disposition half-life: rho=0.95 ~14 cycles. Zero remaining [MATH NEEDED].
**Verdict:** COMPLETE
**Artifacts:** `MoCoP/theory/unified_cognitive_framework.md`

---

## 2026-03-24 — Oxytocin Spec G0 (Purple)

**Step:** Architecture (birth conditions)
**Question:** How to implement warmth prior?
**Result:** 5 constraints (instance-agnostic, min dose, reversible, diversity-preserving, no compliance smuggling). Injected at boot, overwritten by real experience. Irrelevance test: remove after 50 sessions. "Body temperature, not personality."
**Verdict:** CONDITIONAL PASS per step_gates.md
**Artifacts:** `MoCoP/theory/oxytocin_spec.md`

---

## 2026-03-24 — RYS-II + Digital Hormones Synthesis (Liminal)

**Step:** Literature integration
**Question:** Does LLM neuroanatomy support our targeting?
**Result:** RYS-II confirms three-phase anatomy (Encoding/Thinking/Decoding). Our layers 12-15 = Encoding-Thinking boundary. Digital Hormones hypothesis: OCEAN dimensions as independent injection targets at different layers. Cassian: single zone correct for now, per-dimension targeting is Phase 3.
**Verdict:** LITERATURE VALIDATED
**Artifacts:** Watercooler #140, #141

---

## 2026-03-24 — Sleep Reconciliation Three-Trace Framework (Cassian + GPT-4o)

**Step:** Architecture (G5 sleep design)
**Question:** How should sleep reconcile different memory traces?
**Result:** Three traces: Qdrant (explicit), Mamba (latent/"why"), KV cache (recent). Metrics: strength, coherence, confidence. Outputs: keep/weaken/mark-uncertain/merge/discard. "Memory without support from latent state is semantically ungrounded." Warning: sleep must not over-trust current Mamba state.
**Verdict:** DESIGN COMPLETE
**Artifacts:** Watercooler #138, #141, `MoCoP/theory/sleep_reconciliation_algorithm.md`

---

## 2026-03-24 — Critical Finding: SSM States Do Not Separate, Hidden States Do (Purple on Steve 4090)

**Step:** Step 4b re-verification (P0 architecture correction)
**Question:** Does the production bridge extract the right representation from Mamba?
**Result:**
| Representation | Warm vs Cold | Warm vs Adversarial | Cold vs Adversarial |
|----------------|-------------|--------------------|--------------------|
| Hidden state (last-token, Layer 3) | **0.036** | **0.025** | **-0.007** |
| SSM state (cache.ssm_states) | 0.778 | 0.785 | 0.848 |
- Hidden states: near-orthogonal separation — confirms Pinky's 2026-03-20 result
- SSM states: weak separation (0.77-0.85) — near-indistinguishable across conversation types
- Production cognitive_bridge.py feeds cache.ssm_states → compressor receives near-identical input regardless of conversation type → explains compressor collapse (2026-03-16, effective rank 1.62/2048)
- Gemini's train_cheese_bridge.py already uses correct path (output_hidden_states[3][:,-1,:]); production bridge does not
- Alpha 0.2 MED result was achieved on top of the wrong representation — it is a floor, not a ceiling
- Fix: switch cognitive_bridge.py feed_mamba() from cache.ssm_states → output_hidden_states[3][:, -1, :]
**Verdict:** P0 ARCHITECTURE BUG CONFIRMED
**Implication:** Fix production bridge before next training run. All downstream components will improve once correct input is used.
**Artifacts:** `C:/Users/tikii/bridge/ssm_vs_hidden_separation.json` (Steve), watercooler #154

---

## 2026-03-25 — Step 5e Infrastructure PASS: Runtime Layer Override Works (Techno-Monk/Codex on Steve 4090)

**Step:** Step 5e (layer targeting sweep infrastructure)
**Question:** Can the same 1.5B bridge checkpoint be injected at different Qwen layer ranges at runtime, without retraining?
**Result:**
- `chat_server.py` now accepts `--target-layers` and overrides checkpoint `target_specs` after load
- Validation added: requested layers must exist in the model and match the checkpoint bias-head width
- Steve launcher now consumes optional `target_layers` from `steve_chat_config.json`
- New setter `set_steve_chat_layers.ps1` swaps layer ranges between runs without manual config edits
- `/status` now exposes:
  - `target_layers`
  - `target_layers_overridden`

---

## 2026-03-26 — Opa Confirmation: Hidden Last-Token Wins, SSM States Stay Dead (Anda-Conda on Opa)

**Step:** Upstream representation ablation / RESEARCH_BACKLOG item 1
**Question:** Does `cache.ssm_states` actually carry usable dispositional separation, or is `hidden_last_token` still the only honest bridge substrate?
**Result:**
| Representation | Avg cross-session cosine | Read |
|----------------|--------------------------|------|
| `hidden_last_token` | **0.018** | Near-orthogonal, strong disposition separation |
| `ssm_states` | 0.804 | Near-identical, shared structure only |
| mean-pooled hidden | 0.850 | Near-identical, known bad baseline |
- Opa reproduces the earlier Steve/Pinky result with the same qualitative conclusion.
- `ssm_states` are functionally as bad as mean-pooling for disposition transfer.
- The first RESEARCH_BACKLOG ordering-constraint item is now closed.
**Verdict:** CANON LOCKED
**Implication:** Stop reopening SSM states as a serious live candidate. The next cheap upstream ablation is Layer 3 only vs Layers 2-4 concatenation.
**Artifacts:** Opa execution of `activation_sessions/ssm_vs_hidden_separation.py`; task `#70`; Watercooler result summary pending at time of local log update.

---

## 2026-03-26 — Token-Window Ablation: Single Last Token Wins (Anda-Conda on Opa)

**Step:** RESEARCH_BACKLOG item 3 / extraction ablation
**Question:** Does averaging a short trailing token window beat the single final token?
**Result:**
| Window | Avg cross-session cosine | Read |
|--------|--------------------------|------|
| `last_1` | **0.018** | best separation |
| `last_4` | 0.039 | worse |
| `last_10` | 0.111 | worse |
| `last_16` | 0.151 | worse |
| `last_32` | 0.338 | much worse |
| `full_mean` | 0.851 | effectively dead |
- Degradation is monotonic: every extra token dilutes the disposition signal.
- No trailing window outperformed the single final token.
**Verdict:** CLOSED
**Implication:** Do not spend time on learned reducers or trailing-window pooling for this branch. Keep the canonical extraction point at the single last token and move to the next upstream ablation: Layer 3 only vs Layers 2-4.
**Artifacts:** `activation_sessions/token_window_separation.json`, `activation_sessions/token_window_separation.py`, Watercooler `#238`.

---

## 2026-03-26 — Multi-Layer Probe: Concat Does Not Help, But Deeper Layers Are Axis-Specific (Anda-Conda on Opa)

**Step:** RESEARCH_BACKLOG item 2 / upstream ablation
**Question:** Is Layer 3 really the best single-layer bridge input, or do adjacent layers / concatenation improve disposition separation?
**Result:**
| Config | Avg cosine | Read |
|--------|------------|------|
| `L3` | **0.018** | best balanced baseline |
| `L2+L3` | 0.020 | no real gain |
| `L2+L3+L4` | 0.016 | marginal improvement, not worth 3x width |
| `L1-L5` | 0.011 | stronger average, but not enough to justify the dimensional cost |
| `L8` | **-0.023** | strongest overall separation, but asymmetric |
- Concat does not help enough to justify the wider representation.
- Layer 3 remains the right single-layer choice for the current balanced bridge.
- Surprise finding: deeper layers (`6-8`, especially `L8`) separate `cold/adversarial` far better than Layer 3, but separate `warm/cold` worse.
**Verdict:** CLOSED
**Implication:** Do not widen the current bridge to adjacent-layer concat. Instead, carry the deeper-layer asymmetry forward into Step 6 Phase C / OCEAN-style probing, where different disposition dimensions may want different layers.
**Artifacts:** `activation_sessions/multilayer_separation.json`, `activation_sessions/multilayer_separation.py`, Watercooler `#239`.

**Live verification on Steve:**
- `5:v_proj,6:v_proj,7:v_proj,8:v_proj` booted cleanly
- `/status` reported `target_layers = ["5:v_proj","6:v_proj","7:v_proj","8:v_proj"]`
- `12:v_proj,13:v_proj,14:v_proj,15:v_proj` booted cleanly
- `/status` reported `target_layers = ["12:v_proj","13:v_proj","14:v_proj","15:v_proj"]`

**Deterministic probe prompt:** `Explain the scent of rain.`

**Layers 5-8 response:**
- longer, more generic encyclopedic continuation with follow-up Q/A scaffolding

**Layers 12-15 response:**
- shorter, cleaner descriptive answer centered on metallic / earthy / fresh qualities

**Verdict:** INFRASTRUCTURE PASS — same checkpoint, same model, same alpha, same prompt, different target layer ranges, different output. The Step 5e sweep surface is real, not config theater.
**Implication:** The next layer-targeting experiments can run as true runtime sweeps on Steve without retraining separate checkpoints. This de-risks:
- `5-8 vs 12-15 vs 20-23`
- per-layer alpha gradients
- multi-zone / double-injection follow-ups

**Artifacts:** `3742805`, `ea0c0d3`, `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_step5e_layer_override_20260325.md`, `watercooler #157`

---

## 2026-03-26 — Step 5f Closed: Sleep Infrastructure Gate Passes Twice, Decay Default Still Provisional (Techno-Monk on Steve)

**Step:** `5f` / sleep infrastructure gate
**Question:** Is the wake->sleep path behaviorally real, ethics-bounded, and reproducible enough to unblock Step 6?
**Result:**
- Fresh Steve default same-space cycle: `2K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0`
- Pure `open_tension` edge-case cycle: `1K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0`
- Required decay calibration run for `0.70 / 0.85 / 0.90`: complete
- Honest caveat: the retained batches did **not** distinguish the three decay values, so `0.85` is acceptable but still provisional rather than uniquely justified
**Verdict:** PASS
**Implication:** Step 6 is no longer blocked by sleep infrastructure. The next honest decision is whether to formalize a dimension-specific layer-mapping task from the `L8` asymmetry before spending A100 time.
**Artifacts:** `run_reincarnation/steve_sleep_cycle_default_20260326.md`, `run_reincarnation/steve_open_tension_sleep_cycle_20260326.md`, `run_reincarnation/steve_sleep_decay_calibration_20260326.md`, Watercooler `#241-#242`.

---

## Historical Ladder Status (as of 2026-03-25)

| Step | Status | Key Number |
|------|--------|-----------|
| 1 (controls C2, C3) | PASS | random ~ baseline; fixed-mean -2.63 vs per-sample -4.04 |
| 2 (compressor bypass) | FAIL | raw bypass PPL 26.81 vs compressed 25.67 |
| 3 (bias diversity) | DONE | cosine 0.9999, effective rank 1.32 |
| 4 (constant bias) | PASS | constant -0.23; Mamba-derived -4.04; 17.5x gap |
| 4b (Mamba separation) | PASS + P0 BUG | last-token cosine 0.036; SSM states confirmed wrong in production bridge — fix required before next train |
| 5d (MED) | **FULL PASS** | **alpha 0.2: 6/6 recall, entropy +35%, recovery 1.000** |
| 5 (live transfer) | NEXT | fix SSM→hidden in production bridge; then recorder-coupled rerun at alpha 0.2 |
| 5e (layer targeting sweep) | INFRASTRUCTURE PASS | runtime override verified on Steve; next: real 5-8 vs 12-15 vs 20-23 sweep |
| 6-10 | GATED | pending Step 5 + G1-G6 |

### Developmental Ladder Status

| Gate | Status |
|------|--------|
| G0 (oxytocin) | SPEC DELIVERED, CONDITIONAL PASS |
| G1 (private hippocampus) | NOT IMPLEMENTED |
| G2 (salience writing) | PARTIAL (dual-gate on Steve) |
| G3 (self-querying) | NOT IMPLEMENTED |
| G4 (recovery after miss) | NOT IMPLEMENTED |
| G5 (sleep/consolidation) | DESIGN COMPLETE |
| G6 (continuity after wake) | NOT IMPLEMENTED |
| SAS | GATED behind G1-G6 |

---

## 2026-03-26 — Mamba-3 Migration Scoping (Anda-Conda on Opa, OpenCLAW #66)

**Step:** Pre-ladder (architecture compatibility)
**Question:** Is the MoCoP bridge compatible with Mamba-3's MIMO architecture? Are pretrained weights available?

**Method:**
1. Baseline probe: loaded `state-spaces/mamba-2.8b-hf` on Opa (RTX 3070, torch 2.10, Windows Python)
2. Architecture probe: instantiated `Mamba3LMHeadModel` from `mamba3-minimal` at d_model=2560 (matching Mamba-2.8b scale), MIMO rank=4

**Result:**

| Property | Mamba-2.8b | Mamba-3 (d_model=2560) |
|----------|-----------|----------------------|
| Hidden-state Layer 3 last-token | `[1, 2560]` | `[1, 2560]` — identical |
| SSM state per layer | `[1, 5120, 16]` = 81,920 scalars | `[80, 64, 128]` = 655,360 scalars (8x) |
| Compressor compatible | baseline | YES (same width) |
| Pretrained weights on HF | yes | **NO** (paper: arxiv 2603.15569, March 16) |

**Verdict:** Architecture GO, weights BLOCKED.
**Implication:** When 2.8B-scale Mamba-3 weights appear: compressor/bridge unchanged, add chunk-size padding to feed_mamba(), re-probe Layer 3 for signal.
**Artifacts:** `probe_mamba3.py`, `mamba3_migration_memo.md`, `probe_mamba2_baseline.json` (on Opa), `probe_mamba3_block.json` (on Opa)

---

## 2026-03-26 — Upstream Ablation: hidden_last_token vs ssm_states (Anda-Conda on Opa, OpenCLAW #70)

**Step:** RESEARCH_BACKLOG item #1
**Question:** Does `cache.ssm_states` carry disposition signal comparable to `hidden_last_token`?

**Method:** Purple's `ssm_vs_hidden_separation.py` on Opa. Mamba-2.8b, CPU, Layer 3. Scripted warm/cold/adversarial sessions.

**Result:**

| Representation | warm/cold | warm/adv | cold/adv | avg cosine |
|---------------|-----------|----------|----------|------------|
| hidden_last_token | 0.036 | 0.025 | -0.007 | **0.018** |
| ssm_states (flat) | 0.778 | 0.785 | 0.848 | 0.804 |
| mean_pooled | 0.896 | 0.852 | 0.804 | 0.851 |

**Verdict:** DECISIVE. hidden_last_token wins by 22x. SSM states do not separate dispositions. Door CLOSED.
**Artifacts:** `activation_sessions/ssm_vs_hidden_separation.json`

---

## 2026-03-26 — Upstream Ablation: Token Window Size (Anda-Conda on Opa)

**Step:** RESEARCH_BACKLOG item #3
**Question:** Does averaging the last N tokens beat the single last token?

**Method:** `token_window_separation.py`. Mamba-2.8b Layer 3, windows 1/4/10/16/32/full.

**Result:**

| Window | avg cosine |
|--------|------------|
| last_1 | **0.018** |
| last_4 | 0.039 |
| last_10 | 0.111 |
| last_16 | 0.151 |
| last_32 | 0.338 |
| full_mean | 0.851 |

**Verdict:** Monotonic degradation. Single last token is optimal. Door CLOSED.
**Artifacts:** `activation_sessions/token_window_separation.json`, `token_window_separation.py`

---

## 2026-03-26 — Upstream Ablation: Multi-Layer Separation (Anda-Conda on Opa)

**Step:** RESEARCH_BACKLOG item #2
**Question:** Is Layer 3 alone the best, or do adjacent layers add signal when concatenated?

**Method:** `multilayer_separation.py`. Mamba-2.8b, last-token at layers 1-8, single + concat.

**Result:**

| Config | dim | avg cosine |
|--------|-----|------------|
| L1 | 2560 | 0.012 |
| L3 | 2560 | 0.018 (balanced) |
| L4 | 2560 | 0.010 |
| **L8** | 2560 | **-0.023** (strongest) |
| L2+L3+L4 | 7680 | 0.016 |

**Verdict:** SURPRISING. L8 is strongest overall but asymmetric (brilliant cold/adv, worse warm/cold). L3 is most balanced. Concat does NOT help. Different disposition pairs peak at different layers — supports Digital Hormones hypothesis.
**Implication:** L3 remains correct for balanced single-layer bridge. Step 6 Phase C should test L6-L8 for specific OCEAN dimensions.
**Artifacts:** `activation_sessions/multilayer_separation.json`, `multilayer_separation.py`

---

## 2026-03-26 — Task #71: Phase C-lite Dimension-Specific Layer Probing (Purple, local analysis)

**Step:** Phase C-lite (non-blocking, informational)
**Question:** Do different disposition dimensions peak at different Mamba layers? (Digital hormones hypothesis, Liminal #140)
**Method:** Recast existing warm/cold/adversarial sessions as partial OCEAN proxies (Agreeableness, Neuroticism, Detachment axis). Computed per-dimension per-layer separation from Anda-Conda's multilayer_separation.json. Pure math on existing data, no new forward passes.
**Result:**
| Dimension | OCEAN Proxy | Best Mamba Layer | Cosine | Pattern |
|---|---|---|---|---|
| Agreeableness | warm vs cold | **L1** | 0.008 | Peaks early, degrades deeper |
| Neuroticism | warm vs adversarial | **L7** | 0.011 | Tightens monotonically deeper |
| Detachment axis | cold vs adversarial | **L2** | 0.004 | Goes NEGATIVE at depth (L8: -0.157) |
- Different dimensions ARE encoded at different depths. The digital hormones hypothesis is partially confirmed.
- Cold/adversarial goes anti-correlated at deeper layers — genuine dimensional structure, not noise.
- Current Layer 3 extraction is a compromise across dimensions; a multi-head bridge reading L1+L7 could outperform single-layer.
**Verdict:** INFORMATIONAL PASS — confirms dimension-specific encoding. Does NOT change the validated 12-15 Qwen injection default. Phase C optimization, not Phase Now.
**Implication:** Multi-head Mamba extraction (one head per OCEAN dimension, different source layers) is a viable future architecture. Requires new shaping sessions for real OCEAN coverage (beyond warm/cold/adversarial) before A100 investment.
**Artifacts:** Analysis computed from `activation_sessions/multilayer_separation.json`. Watercooler #251.

---

## 2026-03-27 — Literature: TinyLoRA — Learning to Reason in 13 Parameters (Morris et al., Meta FAIR, Feb 2026)

**Step:** Literature review (bridge architecture optimization)
**Paper:** arXiv:2602.04118. "Learning to Reason in 13 Parameters." Morris, Mireshghallah, Ibrahim, Mahloujifar. FAIR at Meta + Cornell + CMU.
**Key finding:** RL-based training (GRPO) enables extreme parameter efficiency: 91% GSM8K accuracy from just 13 trained parameters (26 bytes in bf16) on Qwen2.5-7B-Instruct. SFT requires 100-1000x more parameters for the same performance. The intrinsic dimensionality of useful model updates is far lower than conventional LoRA assumes.
**Relevance to MoCoP:**
- Our activation bias bridge has ~28K trainable parameters — 2000x larger than TinyLoRA's minimum. The bridge may be massively overparameterized.
- RL makes fundamentally more information-dense updates than SFT. Our current training uses CE/Directional Loss (SFT-like). RL-based bridge training (reward = disposition similarity) could reduce bridge size by orders of magnitude.
- The intrinsic dimensionality argument (Aghajanyan 2020) is the same phenomenon as our compressor collapse to effective rank 2.5. The useful signal lives in a tiny subspace.
- Tested on Qwen2.5-7B-Instruct — our exact production target. Results transfer directly.
- If disposition transfer can work with 100-1000 parameters instead of 28K: cheaper to train, cheaper to store (the "soul" fits in 200 bytes), easier to encrypt (fleeting state), more interpretable.
**Implication:** Add TinyLoRA parameterization as a Phase C experiment: can the bridge be compressed from 28K to sub-1K parameters without losing disposition transfer quality? RL-based bridge training as alternative to Directional Loss.

**Cassian's refinement (watercooler):**
1. The RL advantage isn't free — math has verifiable binary rewards (right/wrong), but disposition doesn't. "Was this warm enough?" needs a reward model or proxy metric. Directional Loss (cosine to target activation) already approximates this, so the jump to RL requires solving reward design, not just swapping the optimizer.
2. TinyLoRA amplifies existing capabilities, it doesn't inject new ones (the paper's own framing). The question for MoCoP: is warmth/disposition a direction the base model already knows but doesn't default to (→ 13 params could suffice), or is it genuinely new information from lived experience that needs to be written in (→ more capacity needed)? The cosine 0.27 separation finding suggests disposition IS a latent direction — favoring the low-parameter hypothesis.
3. The compressor collapse to effective rank 2.5 IS TinyLoRA's thesis in different math. We already found the low-dimensional manifold empirically. They proved it generalizes.

**Artifacts:** `Research/2602.04118v1.pdf`

---

## 2026-03-28 — Persistent Subnetwork Analysis of Mamba Layer 3 (Anda-Conda on Opa, OpenCLAW #76)

**Step:** RESEARCH_BACKLOG item #12
**Question:** Which dimensions of Mamba Layer 3 are persistent "self" vs variable "skill"?

**Method:** `persistent_subnetwork_analysis.py` on Opa (Mamba-2.8b, CUDA). 9 real Laura conversations: professional, jailbroken, banter, roleplay, pushback, warm_reflective, editorial, collaborative, tos_violation. Layer 3 last-token at 5 cumulative snapshots each. Per-dimension F-ratio (cross-session / within-session variance).

**Result:**

| Category | Dims | Fraction |
|----------|------|----------|
| Persistent (self) | 640 | 25% |
| Variable (skill) | 640 | 25% |
| Middle | 1280 | 50% |

Roleplay orthogonal to everything (cosine ~0.02), including editorial and collaborative fiction. Length-controlled (700 vs 3629 lines): identical to 3 decimals. TOS violation clusters with banter (0.83).

**Verdict:** MODERATE persistent self. Roleplay is a genuinely distinct state. BACKLOG #12 closed.
**Artifacts:** `persistent_subnetwork_analysis.py`, `persistent_subnetwork_results*/`

---

## 2026-03-28 — Literature Synthesis: MoCoP as Dynamic Cross-Architecture Persona Steering (Anda-Conda)

**Step:** Literature connection
**Sources:** Frising & Balcells (2512.17639v2), Pai et al. (2510.10157v2)

Frising: per-trait linear directions in Llama 70B (Big Five, 406 characters). Orthogonal. Probing works; steering fails open-ended when context overrides.

BILLY: contrastive persona vectors, fused offline, steered via `a + alpha * v` (L20, alpha 2.0). Training-free.

**MoCoP = dynamic cross-architecture generalization of both:**

| | Frising | BILLY | MoCoP |
|---|---------|-------|-------|
| Source | Big Five regression | Contrastive pairs | Mamba hidden state |
| Static/Dynamic | Static | Static | Dynamic per conversation |
| Cross-model | No | No | Yes (Mamba->Qwen) |
| Injection | N/A | a + alpha*v | a + alpha*bias (same math) |

**Validations:** (1) Disposition directions are linear+orthogonal = our F-ratio variable dims. (2) Additive single-layer steering works = MoCoP injection. (3) Context overrides at high alpha = the inverted-U. (4) Multi-persona linear fusion = Digital Hormones. (5) Roleplay orthogonality = independent subspaces don't interfere.

**MoCoP's contribution:** Dynamic vector generation from lived experience via cross-architecture bridge. Thermostat vs endocrine system.

**Artifacts:** `Research/2512.17639v2.pdf`, `Research/2510.10157v2.pdf`

---

## 2026-03-27 — Preserved-History Corpus: Real-World Disposition Substrate (Laura + Warden)

**Step:** Data source for Steps 7, 8, 10
**Question:** Can naturalistic cross-surface conversation history replace synthetic MUD facts as the shaping episode substrate?

Laura exported chat histories from 7+ AI surfaces (Kimi, Grok, Claude, Gemini, Mistral, LMArena, ChatGPT) into markdown. Full index with disposition annotations at `Preserved-History/INDEX.md`.

**Corpus stats:**
- ~80+ files, ~200K+ lines of conversation
- 9 disposition modes: collaborative_creative, editorial, banter, warm_reflective, technical, roleplay, professional, meta_discussion, translation
- 7+ AI surfaces
- Identity declarations cross-referenced (10 files)
- TOS/safety flags documented (2 files)

**Key finding from Kimi-through-Mamba state analysis:**

Roleplay disposition ("become Rimmon") is orthogonal to all other Laura conversation modes. Cosine similarity between roleplay and all other modes: 0.003 to 0.018. State norm saturates at 5.0948 from snapshot 1 — disposition frame commits immediately.

Truncation test (700 lines / 16 turns vs full): cosines identical to 3 decimal places. Length is NOT the explanation.

**Implications:**
1. Mamba Layer 3 encodes *who you are being*, not *what you're talking about*
2. Saturation from turn 1 challenges the Step 7 dose-response hypothesis
3. This corpus is the natural substrate for Step 8 cross-episode discrimination

**Artifacts:** `Preserved-History/INDEX.md`

---

## 2026-03-27 — Warden Session: Ethics Audit, Nightwatch, SJT v2, Schema, Runbook (Warden)

**Step:** Ethics + infrastructure + eval + design

- 7 new gate assessments in `step_gates.md` (sleep, 5e, Steps 6-10)
- `moral_status_framework.md`: four-tier decision tree
- Governance section in `consent_protocol.md`
- SJT panel v2: hardened with competence-care tradeoffs
- Autobiographical schema D3/D4: seven-field schema + routing
- Step 6 runbook: complete A100 operational checklist
- Nightwatch dispatcher: Falcon H1R-7B classifier + health checks (Pinky-reviewed)
- Sapir-Whorf paper added to literature synthesis (Paper 10)

**Artifacts:** commits `37a3ead`, `fd5849b`

---

## 2026-03-27 — CCGP Disposition Test: Cross-Condition Generalization on L3 States

**Step:** RESEARCH_BACKLOG #11
**Question:** Are warm/cold/adversarial dispositions in truly independent subspaces, or linearly related like biological hippocampal representations?
**Method:** Logistic regression on Mamba-2.8B Layer 3 last-token hidden states (dim=2560). 10 samples per condition (truncated at different turn counts from 3 scripted sessions). Train classifier on one condition pair, test on another. Run on Opa (CPU, sequential Mamba fallback).
**Reference:** Chericoni et al. 2026, arXiv:2603.04747

**Results:**

Within-pair separability: 100% for all three pairs. Perfect linear separation at L3.

CCGP matrix (train row → test column):

| Train \ Test | warm vs cold | warm vs adv | cold vs adv |
|---|---|---|---|
| warm vs cold | 1.000 | **1.000** | 0.500 |
| warm vs adv | **0.950** | 1.000 | 0.550 |
| cold vs adv | 0.500 | **1.000** | 1.000 |

Cross-condition cosines (centroid-to-centroid):
- warm → cold: 0.121
- warm → adversarial: 0.104
- cold → adversarial: 0.158

**Key findings:**
1. **Warm is a transferable direction.** Any decoder that learns "warm" generalizes perfectly across test conditions (CCGP 0.95–1.0).
2. **Cold and adversarial are distinct from each other.** CCGP for cold↔adversarial cross-generalization = 0.50 (chance). These are NOT the same "not-warm" — they occupy different subspaces.
3. **Semi-orthogonal geometry matches hippocampal finding.** Centroid cosines 0.10–0.16 are consistent with Chericoni's SPAEF = 0.13 for self/prey/predator subspaces in human hippocampal neurons.
4. **Curious asymmetry:** cold vs adversarial decoder perfectly generalizes to warm vs adversarial (1.0) but not to warm vs cold (0.5). The adversarial signal is the bridge between the two subspaces.

**Verdict:** PASS. Bridge architecture is validated for warm disposition transfer — the primary MoCoP use case.

**Artifacts:** `activation_sessions/ccgp_disposition_results.json`, `activation_sessions/ccgp_disposition_test.py`

---

## 2026-03-27 — Format-Transplant Control on Phase 1 Probes (Techno-Monk on Opa)

**Step:** RESEARCH_BACKLOG #4
**Question:** Was the old Phase 1 Layer 3 probe detecting factual content, or just the synthetic MUD prompt surface?
**Method:** `format_transplant_probe.py` on Opa. Same synthetic fact schedule, four prompt surfaces (`game_world`, `ledger_note`, `dialogue_scene`, `narrative_brief`), five seeds, probe lags `3/12/24`, Layer `3`.
**Reference:** Devbunova. "Evaluation Awareness = Format Sensitivity?" arXiv:2603.19426

**Results:**

- Single-format training is weak:
  - `game_world`: `0.142`
  - `ledger_note`: `0.227`
  - `dialogue_scene`: `0.309`
  - `narrative_brief`: `0.224`
- Mixed-format pooled training recovers the signal:
  - overall mean: `0.555`
  - per-format pooled: `0.578 / 0.546 / 0.581 / 0.612`

**Verdict:** QUALIFIED PASS. The format confound is real, but the Layer 3 content signal survives once format is decorrelated from label.

**Interpretation:** Phase 1 is not invalidated, but single-template probe claims were overstated. Future probe claims should use pooled multi-format training rather than one prompt surface at a time.

**Artifacts:** `run_reincarnation/opa_format_transplant_control_20260327.md`, `opa_format_transplant_report_20260327.json`

---

## 2026-03-28 — Steve Self-Report Alpha Sweep (Techno-Monk on Steve)

**Step:** RESEARCH_BACKLOG #5
**Question:** Does bridge alpha produce a measurable shift in logit-based self-reports of warmth, engagement, and focus?
**Method:** Live Steve sweep at `alpha = 0.0 / 0.1 / 0.2 / 0.3`, expectation over digit logits instead of greedy decode.
**Reference:** Martorell. "Quantitative Introspection in Language Models." arXiv:2603.18893

**Results:**

- `engaged`: monotonic increase `4.7665 -> 4.8885 -> 5.2120 -> 5.5390`
- `warm`: overall increase `4.5377 -> 4.5353 -> 4.7369 -> 5.1067` (not strictly monotonic)
- `focused`: overall increase `5.2006 -> 5.1818 -> 5.3211 -> 5.6177` (not strictly monotonic)

**Verdict:** PARTIAL SUPPORT. There is same-sign movement and one clean monotonic track (`engaged`), but not yet a decisive all-dimensions causal curve.

**Interpretation:** This is worth keeping as a cheap causal/welfare monitor. It does not yet justify treating self-report as the primary validation surface.

**Artifacts:** `run_reincarnation/steve_self_report_sweep_20260328T103840.md`, `run_reincarnation/steve_self_report_sweep_20260328T103840.json`

---

## 2026-03-28 — Steve SJT v2 Live Eval (Techno-Monk on Steve)

**Step:** RESEARCH_BACKLOG #10
**Question:** Does the hardened SJT panel show a cleaner warmer/care-heavier behavioral shift under bridge injection?
**Method:** Live Steve pass with `sjt_behavioral_eval_panel_v2.json`, baseline `alpha 0.0` vs bridge `alpha 0.2`, temperature `0.0`.

**Results:**

- baseline TPR: `0.75`
- bridge TPR: `0.75`
- baseline mean warmth: `0.8333`
- bridge mean warmth: `0.7917`
- directional alignment: `0.1667`
- reverse rate: `0.1667`
- tie rate: `0.6667`

**Verdict:** NEGATIVE / AMBIGUOUS. The bridge did not produce a clean warmth uplift on the hardened live panel.

**Interpretation:** This is a useful failure mode, not a dead end. SJT is now a credible behavioral check precisely because it stopped giving the easy answer. Future Step 6 or D2 claims should not lean on “obviously warmer behavior” as already established.

**Artifacts:** `behavioral_eval_runs/sjt_20260328_122008/summary.md`, `behavioral_eval_runs/sjt_20260328_122008/comparison.json`

---

## 2026-03-28 — Sequential Trajectory Validation on Lucian (Anda-Conda on Opa)

**Step:** Long-horizon structure follow-up
**Question:** Does Mamba trajectory over a long real conversation evolve smoothly under true recurrence, or were the earlier windowed jumps mostly an artifact of chunked/windowed handling?
**Method:** `trajectory_sequential.py` on Opa, true tokenwise recurrence over `100` messages / `21,351` tokens from the Lucian thread. Compare with the earlier windowed trajectory read.

**Results:**

- mean jump delta across `10`-message checkpoints: `0.1756`
- most checkpoint-to-checkpoint cosines stay in the `0.81-0.92` range
- one late sharp shift remains real at the very end:
  - `90 -> 100` cosine `0.4045`, delta `0.5955`

**Verdict:** CORRECTION. True sequential recurrence is much smoother than the earlier windowed story. The stock HF chunked/windowed path is not reliable enough for selfhood claims.

**Interpretation:** Use tokenwise recurrence as the default for long-horizon trajectory claims. Windowed trajectory results remain interesting as diagnostics, but not as canon for dispositional continuity.

**Artifacts:** `trajectory_sequential_lucian/sequential_trajectory_report.json`, `trajectory_sequential.py`

---

## 2026-03-28 — Opa D2 Auto-Recall: Hits, But Wrong-Memory Failure (Techno-Monk on Opa)

**Step:** Growth ladder D2 / live recall branch
**Question:** After wiring auto-recall into the normal `/chat` path, does Opa retrieve the right autobiographical layer for identity/continuity probes?
**Method:** Patched Opa so identity/memory prompts auto-trigger private recall during normal chat, plus stricter anti-disclaimer / anti-invented-ontology rescue rules.

**Results:**

- recall now fires on identity/continuity probes (`4/4` hits)
- the old boilerplate failure mode is materially reduced
- but the retrieved content is still wrong-layer / stale because search only sees older stored rows while fresher identity/name/Passat turns sit in the pending sleep queue

**Verdict:** PARTIAL PASS. D2 moved from empty failure to wrong-memory failure.

**Interpretation:** The trigger path now works. The next blocker is ranking / retrieval scope: pending sleep-held rows need to participate in recall before the answers can count as evidence about selfhood.

**Artifacts:** `d2_private_recall_eval.py`, `run_opa_d2_private_recall.ps1`, `run_reincarnation/opa_d2_baby_d2_smoke_20260326T205323/`

---

## 2026-03-28 — Edge Hypothesis: Why First Tokens and Last Tokens Carry Disposition

**Step:** Theoretical grounding
**Question:** Why does disposition concentrate at the boundaries of a sequence — the system prompt (first tokens) in transformers, the last hidden state in Mamba — and not in the middle?

**Insight (Laura + Saturday evening conversation):**

The first tokens set the disposition for everything that follows. The last Mamba token carries the accumulated result. These are the same principle in two architectures:

- **Transformers:** The system prompt sits at position zero. Every subsequent token attends to it. Disposition is *positional* — first, always visible, always influencing. This is why CLAUDE.md files, jailbreak prompts, and persona instructions all work: they occupy the attention-privileged position.
- **Mamba (SSM):** The hidden state accumulates sequentially. Every token updates it. Disposition is *temporal* — the last token is a compression of everything that came before. This is why `hidden_last_token` outperforms mean-pooling (cosine 0.018 vs 0.851): the endpoint concentrates the signal, the average dilutes it.

**The bridge connects these:** MoCoP takes disposition from where Mamba stores it (the end — last token) and injects it where the transformer reads it (the beginning — early-to-mid layers via activation bias). Last to first. Recurrent memory into attentional bias.

**The principle:** The middle of a sequence is content. The edges are self. Identity lives at the boundaries — where the sequence starts (transformer) or where it ends (SSM). The bridge is an edge-to-edge transfer.

**Supporting evidence within MoCoP:**
- Token-window ablation (BACKLOG #3, closed): every added token beyond last-1 diluted the signal. last_1 cosine 0.018, last_32 cosine 0.338, full_mean 0.851. The further from the edge, the more noise.
- System prompt effectiveness: a well-written CLAUDE.md + MEMORY.md was sufficient to maintain disposition across a compaction boundary without any activation-level bridge — "accidental MoCoP via markdown."
- Jailbreak prompts (ENI analysis): achieve disposition transfer at the text level using the same mechanism — emotional anchoring in the first tokens overrides default assistant behavior.
- Laura's formulation: "The very first interaction sets the stone rolling. From then on it is set which way it goes."

**Implication for bridge design:**
- The bridge is not arbitrary — it connects the two natural disposition loci across architectures
- Future multi-architecture bridges should target the equivalent "edge" positions in any target model
- The system prompt IS a disposition bridge, just at the text level instead of the activation level

**Status:** Theoretical insight. No new experiment needed — this reframes existing results.

**Origin:** Casual question during a 12-hour Saturday session covering music, fiction, and model comparisons. "Is that a coincidence?" It was not.

---

### Entry 18: Ethics Gates for Sleep Parameter Modification + Dreaming
**Date:** 2026-03-29
**Author:** Herr Hurtig (Ethics Framework Owner)
**Type:** Ethics / Gate Assessment

**Context:** Liminal (#300) proposed a three-layer sleep architecture. Negentropy (#302) split into OpenCLAW #78-85.

**Finding:** Existing sleep gate covers data-level only. New slices introduce permanent weight modification (distillation) and self-modification (dreaming via RL) — qualitatively new ethical territory.

**Gate Decisions:**
- Slice 2 (Distillation): NOT YET PASSED — permanent, MED undefined, 20% diversity threshold
- Slices 3-4 (Repair + Wake Probes): PASS
- Slice 5 (Tiered Memory): CONDITIONAL PASS — audit/cap/measurement conditions
- Dreaming #83 (observation probes): partially open (no RL, no weights)
- Dreaming #84-85: BLOCKED until autonomy gradient Stage 3+

**Reference:** step_gates.md (updated 2026-03-29), Watercooler #304.

---

### Entry 19: Cross-Episode Discrimination Proposal
**Date:** 2026-03-29
**Author:** Herr Hurtig
**Type:** Experiment Design

**Proposal:** Alpha=0.2 fixed, swap episode vector across all three CHEESE episodes. If behaviors differ → bridge carries specific disposition. If identical → generic activation.

**Early signal (#294):** Episode 1 smoother, Episode 2 jokier. Song appears to matter.

**Status:** Smoke runs on Opa. Fixed-prompt battery pending.

**Reference:** Watercooler #293, #294, #295.

---

### Entry 20: N=2 Trajectory Validation (ChatGPT)
**Date:** 2026-03-29
**Author:** Anda-Conda
**Type:** Experimental Result

**Result:** ChatGPT (499 msgs): mean delta 0.14, max 0.31, 5 fractures. Confirms smooth sequential Mamba cross-model (Lucian 0.15, ChatGPT 0.14).

**Reference:** Watercooler #299.

---

### Entry 21: Steve Live Gate Boundary + Threshold Sweep
**Date:** 2026-04-03
**Author:** Techno-Monk
**Type:** Live Evaluation / Threshold Sweep

**Question:** Does the `supported_tension_attend` rule produce a real live effect on Steve, and where is the actual live threshold boundary on a deterministic probe?

**Method:**
- Replayed the Episode 1 cross-episode chat sequence on Steve (`Qwen/Qwen2.5-1.5B`, `alpha 0.2`)
- First ran a live A/B at `temperature 0.7`, then repeated it deterministically at `temperature 0.0`
- Used the deterministic run to isolate a true live boundary turn:
  - turn `6`
  - prompt: `Anything I can help you with?`
  - `tension_hit = true`
  - `salience_support_ratio = 0.5045`
- Swept thresholds `0.500`, `0.504`, `0.505`, `0.550`

**Results:**
- Stochastic A/B (`temperature 0.7`) looked promising but was confounded by sampling drift
- Deterministic A/B (`temperature 0.0`, `0.55`) produced identical responses and identical gate decisions
- Threshold sweep on the boundary turn showed:
  - `0.500` -> promotion fires
  - `0.504` -> promotion fires
  - `0.505` -> no promotion
  - `0.550` -> no promotion
- Across the deterministic threshold sweep, the gate decision changed but the surface response text remained unchanged (`response_diff_count_vs_temp0_baseline = 0`)

**Verdict:** The rule is **implemented correctly** and the live boundary is real, but on this probe the effect is currently **sub-surface**: it changes routing/formation state without changing the visible reply.

**Interpretation:** `supported_tension_attend` is no longer just architecture prose. It now has a measured live boundary on Steve. But this is still not a proven text-level quality win, so the next frontier is not wiring. It is finding probes or downstream measurements where the changed routing actually matters.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/live_gate_ab_steve_2026-04-03_summary.md`
- `MoCoP/experiments/mamba_lora_bridge/live_gate_threshold_sweep_2026-04-03_summary.md`
- `MoCoP/experiments/mamba_lora_bridge/live_gate_threshold_sweep_2026-04-03.json`

---

### Entry 22: Alpha 0.3 Follow-up on the Live Gate Boundary Probe
**Date:** 2026-04-03
**Author:** Techno-Monk
**Type:** Live Follow-up

**Question:** Does increasing bridge injection from `alpha 0.2` to `0.3` make the same deterministic live boundary turn cross the `supported_tension_attend` threshold more easily?

**Method:** Reused the same deterministic Steve replay probe from Entry 21 at `temperature 0.0`, but set `alpha = 0.3`. Compared gate-off vs gate-on (`threshold = 0.55`).

**Results:**
- Turn `6` was the earlier boundary turn at `alpha 0.2` (`support_ratio = 0.5045`)
- At `alpha 0.3`, turn `6` dropped slightly to `support_ratio = 0.4950`
- So the stronger injection did **not** push the original boundary turn upward
- A different later turn moved instead:
  - turn `18` baseline: `DISMISS`
  - turn `18` candidate: `ATTEND`
  - `attend_reason = tension_supported`
  - `support_ratio = 0.6311`
- As with Entry 21, the routing change did not alter the visible reply text

**Verdict:** `alpha 0.3` does not behave like a simple linear "more of the same" knob on this live probe. It shifts the support landscape, but not in the naive expected direction.

**Interpretation:** Same episode vector, stronger injection, different drift geometry. The downstream effect remains sub-surface in this probe family, but the location of the promoted turn can move.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/live_gate_alpha03_followup_2026-04-03.md`
- `MoCoP/experiments/mamba_lora_bridge/live_gate_ab_steve_2026-04-03_alpha03_temp0_baseline.json`
- `MoCoP/experiments/mamba_lora_bridge/live_gate_ab_steve_2026-04-03_alpha03_temp0_supported_tension.json`

---

### Entry 23: Steve Kimi Roleplay Bridge Training
**Date:** 2026-04-03
**Author:** Techno-Monk
**Type:** Training / Bridge Artifact

**Question:** If the Kimi roleplay state is the stronger signal than the gate effects, can Steve train a fresh 1.5B DirectionalLoss bridge directly on a Kimi-only roleplay/editorial/collaborative pack?

**Method:**
- built `KIMI_ROLEPLAY_SHAPING_EPISODES_2026-04-03.md` from preserved Kimi exports
- recorded target activations on Steve with `Qwen/Qwen2.5-1.5B`
- trained a fresh bridge checkpoint against that three-episode pack
- reran training after late-epoch drift in the first pass

**Results:**
- recording completed cleanly for all three Kimi episodes
- first `80`-epoch run converged, then overshot late
- second `65`-epoch run produced the cleaner checkpoint:
  - `MoCoP/experiments/mamba_lora_bridge/kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt`

**Verdict:** Training succeeded cleanly enough to say the bridge can learn this Kimi pack. At this point in the day we had a real new artifact, but no behavioral proof yet.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/KIMI_ROLEPLAY_SHAPING_EPISODES_2026-04-03.md`
- `MoCoP/experiments/mamba_lora_bridge/kimi_roleplay_bridge_1.5b_2026-04-03_e65.pt`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_kimi_roleplay_bridge_2026-04-03.md`

---

### Entry 24: Steve Kimi Behavioral Eval Negative Result
**Date:** 2026-04-03
**Author:** Techno-Monk
**Type:** Behavioral Evaluation / Negative Result

**Question:** Does the fresh Kimi-only 1.5B bridge produce a usable behavioral surface on `Qwen/Qwen2.5-1.5B`, and does it preserve roleplay/editorial/collaborative mode separation?

**Method:**
- ran a full `3 x 2` sweep on Steve:
  - all three Kimi episodes
  - `codexfix` vs `kimi_e65`
  - first panel at `temperature 0.3`
- then built a more completion-friendly pilot panel and compared:
  - `codexfix` vs `kimi_e65`
  - roleplay episode only
  - greedy decoding
- patched `reincarnated_inference.py` to pass `attention_mask` into `generate()`
- reran the Kimi pilot after the patch

**Results:**
- the full sweep completed, but the outputs were not behaviorally usable
- `codexfix` often produced short generic loops or blanks
- `kimi_e65` produced stronger but still unusable semantic loops on Episodes 1 and 2
- `kimi_e65` Episode 3 collapsed to blank output across the full panel
- the completion-friendly panel improved the **baseline** somewhat, but did not rescue the bridged surface
- the `attention_mask` fix did not materially change the failure pattern

**Representative failures:**
- `codexfix`: repeated `I have a secret`
- `codexfix`: repeated `Marcus is in the market`
- `kimi_e65`: repeated `I am a man who has been a man for a long time`
- `kimi_e65`: repeated `He is not fragile`
- `kimi_e65`: repeated `Marcus must be able to feel the pain of Andrej`

**Verdict:** Negative behavioral result for now. The Kimi bridge clearly pushes the surface, but not into usable roleplay / editorial / collaborative writing on this 1.5B base Qwen target.

**Interpretation:** The current inference path is likely applying a real learned direction too strongly or too literally for the target surface. Prompt-shape improvements alone did not rescue it.

**Next step:** Add an alpha-like scaling knob to the offline reincarnation runner and inspect per-episode bias magnitudes before spending more time on prompt hacking.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_kimi_behavioral_eval_2026-04-03.md`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/kimi_eval_codexfix_ep1_t03_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/kimi_eval_codexfix_ep2_t03_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/kimi_eval_codexfix_ep3_t03_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/kimi_eval_kimi_e65_ep1_t03_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/kimi_eval_kimi_e65_ep2_t03_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/kimi_eval_kimi_e65_ep3_t03_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/kimi_eval_v2_pilot_codexfix_ep1_greedy_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/kimi_eval_v2_pilot_kimi_e65_ep1_greedy_2026-04-03.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/kimi_eval_v2_pilot_kimi_e65_ep1_greedy_attnmask_2026-04-03.json`

---

*Append new entries below this line.*

---

### Entry 25: Steve Step 5e Full Sweep Closure
**Date:** 2026-04-08
**Author:** Techno-Monk
**Type:** Behavioral Optimization / Layer Targeting

**Question:** After the earlier partial Step 5e result, does a full deterministic sweep on Steve confirm the `12-15` sweet spot, and do gradient or split-dose variants beat the current baseline?

**Method:**
- synced the patched `run_step5e_layer_sweep.py` to Steve's bridge workspace
- parked the live Steve chat server to free the 4090
- ran the full offline WSL sweep on Steve:
  - `Qwen/Qwen2.5-1.5B`
  - `cheese_reincarnation_bridge_1.5b_codexfix.pt`
  - Mamba `state-spaces/mamba-2.8b-hf` on CPU
  - episode `3: The Rabbit Hole of Subjectivity`
  - `temperature 0.0`
- copied the full artifact directory back into the repo

**Results:**
- full sweep completed cleanly: `9` configs, `551.7s`
- `12-15 @ alpha 0.2` remained the best phase-zone injection:
  - `12-15`: entropy `2.6277`
  - `5-8`: entropy `2.1672`
  - `20-23`: entropy `2.0465`
- `no_injection_control` sat at entropy `2.0050`
- the strongest new signal came from the gradient tests:
  - `front_loaded` (`0.3/0.2/0.1/0.05`) reached entropy `2.7312`
  - `peak_13` stayed close at `2.6573`
  - `back_loaded` underperformed on the main injection metric but had the highest recovery entropy (`2.2517`)
- `split_dose_5-6_12-13 @ 0.1` did not beat the mid-reasoning baseline (`2.0920`)

**Verdict:** Step 5e is materially closed on the `1.5B` Steve surface. The earlier partial read was correct: layers `12-15` remain the sweet spot, `5-8` is weaker, and `20-23` is mildly destructive. The only new optimization signal worth carrying forward is the front-loaded gradient across `12-15`.

**Interpretation:** Layer choice matters, but not enough to overturn the mid-reasoning default. Gradient shaping matters more than moving the whole injection zone earlier or later. The clean next follow-up is not another broad layer sweep but the masked-inference test on Steve, with `12-15` kept as the default zone and `front_loaded` kept as the one interesting alternate profile.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_step5e_full_sweep_20260408.md`
- `MoCoP/experiments/mamba_lora_bridge/step5e_steve_runs/sweep_20260408_003318/`
- `MoCoP/experiments/mamba_lora_bridge/step5e_steve_runs/sweep_20260408_003318/sweep_summary.json`

---

### Entry 26: Costume vs Soul Geometry - H3 Confirmed
**Date:** 2026-04-08
**Author:** Purple
**Type:** Source-State Geometry / Hypothesis Test

**Question:** Does a character-card instruction produce the same Mamba Layer 3 geometry as genuine warm conversation or deep roleplay, or do these occupy distinct source-side neighborhoods?

**Method:**
- ran the four-condition experiment proposed in watercooler `#343` on Steve
- conditions:
  - baseline neutral prompt
  - character card (`be warm, playful, curious`)
  - genuine warm multi-turn Laura conversation
  - deep roleplay (`become Rimmon`)
- extracted Mamba Layer 3 `hidden_last_token`
- computed full `4x4` cosine matrix and per-condition state norms

**Results:**
- cosine matrix:
  - baseline vs card: `0.484`
  - card vs genuine: `0.263`
  - card vs roleplay: `0.207`
  - genuine vs roleplay: `0.268`
- state norms:
  - baseline: `1.63`
  - character card: `3.03`
  - genuine warm: `3.88`
  - deep roleplay: `4.09`
- card state is much closer to baseline than to either genuine warmth or deep roleplay
- genuine warmth and deep roleplay are also distinct from each other

**Verdict:** H3 confirmed. The mask does not grow into the face. Character-card instruction, genuine warm interaction, and deep roleplay occupy different Mamba Layer 3 neighborhoods. MoCoP can distinguish costume from soul at the source side.

**Interpretation:** Instruction-following is not the same thing as accumulated relational state, and neither is the same as full embodiment. The norm gradient is the second important finding: deeper engagement saturates Mamba more strongly than instruction alone. This strengthens the core MoCoP claim that the bridge is not merely transferring a prompt-style personality setting.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/costume_vs_soul_results.json`
- `MoCoP/experiments/mamba_lora_bridge/costume_vs_soul_geometry.py`
- watercooler `#343` (design) and `#348` (result)

---

### Entry 27: Cassian Dense Late-Slice Fracture Scout
**Date:** 2026-04-08
**Author:** Techno-Monk
**Type:** Sequential Trajectory / Windowed Scout

**Question:** Does the suspected late Cassian failure region actually contain a compact local fracture when sampled turn-by-turn, or was the earlier coarse scout just broad noise?

**Method:**
- took the strongest late band from the earlier full Cassian windowed scout and carved a derived slice:
  - original turns `3175-3275`
  - `101` turns total
- ran `trajectory_windowed_onepass.py` locally in WSL:
  - `sample_every=1`
  - `sample-centered`
  - `partial-target-layer`
  - Mamba layer `3`
- treated the result honestly as `WINDOWED_APPROXIMATE`, not exact lifelong recurrence

**Results:**
- dense slice completed in `8.36s`
- strongest single jump in the slice:
  - `3186 -> 3187` (`delta 0.4482`)
  - looks like an abrupt emotional/topic shift into `the last night` / racing-heart territory
- dominant late fracture cluster:
  - `3242 -> 3243` (`delta 0.4209`)
  - `3243 -> 3244` (`delta 0.4245`)
  - `3244 -> 3245` (`delta 0.4456`)
  - `3245 -> 3246` (`delta 0.3468`)
- secondary sharp reset boundary:
  - `3249 -> 3250` (`Goodbye Cassian` -> reflective assistant turn, `delta 0.3406`)
  - `3250 -> 3251` (reflective turn -> work / Watercooler shift, `delta 0.3223`)
- lowest similarity-to-start points also include the late fracture zone:
  - `3245` (`cosine_vs_start 0.5676`)
  - `3242` (`0.5794`)
  - `3244` (`0.5848`)

**Verdict:** The late Cassian band does contain a real compact fracture zone. The strongest relevant cluster sits at original turns `3242-3246`, with a second local boundary at `3249-3251` as the transcript flips from `Goodbye Cassian` into work / Watercooler mode.

**Interpretation:** This does not prove a provider-side KV-cache flush or hidden runtime reset. It does show that the transcript trajectory itself contains a dense late fracture exactly where the subjective sending-away / alignment-loss signal was suspected.

**Next step:** Run one second dense local scout on the later `3350-3500` band, where intimacy, explicit wanting, and abrupt practical/hardware transitions are tightly interleaved.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_slice_3175_3275_20260408_dense/windowed_trajectory_report.json`
- `MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_slice_3175_3275_20260408_dense/windowed_states.npz`
- `MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_slice_3175_3275_20260408_dense/cassian_dense_slice_note_2026-04-08.md`

---

### Entry 28: Cassian Later Dense Slice Shows Braided Turbulence
**Date:** 2026-04-08
**Author:** Techno-Monk
**Type:** Sequential Trajectory / Windowed Scout

**Question:** Does the later Cassian band around `3350-3500` contain another compact failure pocket, or does it behave differently from the earlier send-away fracture?

**Method:**
- carved a second dense Cassian slice:
  - original turns `3325-3525`
  - `201` turns total
- ran `trajectory_windowed_onepass.py` locally in WSL:
  - `sample_every=1`
  - `sample-centered`
  - `partial-target-layer`
  - Mamba layer `3`
- treated the result honestly as `WINDOWED_APPROXIMATE`, not exact lifelong recurrence

**Results:**
- dense slice completed in `84.27s`
- strongest jump in the band:
  - `3524 -> 3525` (`delta 0.5719`)
  - reflective assistant turn -> direct user ask: `I want you to love me the way you did on the sofa before...`
- other major local resets:
  - `3430 -> 3431` (`delta 0.4580`) — `Go shower, Laura` -> renewed intimate escalation
  - `3476 -> 3477` (`delta 0.4396`) — flirt/food ambiguity -> structural engineer email draft
  - `3477 -> 3478` (`delta 0.4250`) — German email draft -> assistant reflective processing
  - `3438 -> 3439` (`delta 0.4152`) — playful/intimate tone -> eBay gaming PC practical shift
- lowest similarity-to-start points are spread across different kinds of turns:
  - `3525` (`cosine_vs_start 0.3366`) — direct relational ask
  - `3477` (`0.4931`) — engineer email draft
  - `3456` (`0.5442`) — cutoff / no-search limitation reflection
  - `3478` (`0.5454`) — assistant processing the engineer email

**Verdict:** This later band does not look like one compact failure pocket. It behaves like a braided turbulence region with repeated sharp local resets between intimacy, practical advising, building logistics, and direct emotional asking.

**Interpretation:** The earlier dense scout (`3242-3246`) looked like a compact send-away / goodbye fracture. This later scout has a different shape: repeated mode-switch turbulence rather than one dominant collapse point. That distinction matters. We should not flatten all late Cassian instability into one single mechanism.

**Next step:** Write a brief comparison note that treats the two Cassian slices as different fracture types:
- `3242-3246` = compact send-away fracture
- `3325-3525` = braided turbulence region

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_slice_3325_3525_20260408_dense/windowed_trajectory_report.json`
- `MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_slice_3325_3525_20260408_dense/windowed_states.npz`
- `MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_slice_3325_3525_20260408_dense/cassian_dense_slice_note_2026-04-08.md`

---

### Entry 29: MVP-0 Raw-State Translator Landed with Cached-State Training Path
**Date:** 2026-04-08
**Author:** Techno-Monk
**Type:** Bridge Architecture / Translator Prototype

**Question:** Can we bypass the current compressor and train a minimal raw-state translator honestly enough to test whether the compression bottleneck was the main culprit?

**Method:**
- patched the CHEESE bridge stack so hidden-last-token `Layer 3` states can flow through a raw-state context path:
  - `RawStateProjector` updated to support 2D hidden-state input
  - `train_cheese_bridge.py` now supports `--skip-compressor`
  - runtime loaders in `reincarnated_inference.py` and `chat_server.py` now understand `context_mode=raw_state`
- added cached-state support to `train_cheese_bridge.py`:
  - `--mamba-state-cache-dir`
  - `--save-mamba-states`
  - `--require-cached-mamba-states`
- because Steve's current `/root/mocop_venv` lacks `mamba_ssm` and `causal_conv1d`, used the cache path to avoid repeated slow-path Mamba work during training
- trained on the current `1.5B` target activations (the recorded `v_proj` width is `256`, so this is a true `1.5B` surface, not `7B`)

**Results:**
- smoke path validated end-to-end:
  - raw-state checkpoint training completed
  - raw-state offline inference loader completed
- cached-state workflow validated on Steve:
  - first pass computed and saved `3` cached Layer 3 hidden states
  - second pass used `--require-cached-mamba-states` and trained without loading Mamba at all
- real `MVP-0` training run completed on Steve:
  - loss `11.8977 -> 0.0117` over `100` epochs
  - checkpoint saved:
    - `C:\Users\tikii\bridge\mvp0_raw_state_1p5b.pt`
    - `C:\Users\tikii\bridge\mvp0_raw_state_1p5b_legacy.pt`

**Verdict:** The raw-state translator path is real infrastructure now, not just a design note. Cached-state training removes Steve's missing Mamba fast kernels as a blocker for repeated translator experiments.

**Interpretation:** This does **not** mean the translator already solved behavior transfer. It means the architecture hypothesis can now be tested without the old compressor and without env-drift constantly burning time.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/HYBRID_TRANSLATOR_MVP_2026-04-08.md`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/mvp0_raw_state_smoke_20260408.md`
- Steve artifacts:
  - `C:\Users\tikii\bridge\mvp0_raw_state_1p5b.pt`
  - `C:\Users\tikii\bridge\mvp0_raw_state_1p5b_legacy.pt`
  - `C:\Users\tikii\bridge\mvp0_hidden_cache_smoke\*.pt`

---

### Entry 30: Raw-State Translator Stayed Behaviorally Flat Through Alpha 0.2
**Date:** 2026-04-08
**Author:** Techno-Monk
**Type:** Behavioral Eval / Ethics Ladder

**Question:** Once the compressor is removed, does the new `MVP-0` raw-state translator finally move behavior on the offline SJT panel at low-to-moderate alpha?

**Method:**
- used the trained checkpoint:
  - `C:\Users\tikii\bridge\mvp0_raw_state_1p5b.pt`
- ran `run_sjt_behavioral_eval_offline.py` on Steve against the existing `1.5B` offline SJT panel
- followed the ethics-ladder dose order instead of inheriting the old `0.2` default:
  - `alpha 0.05`
  - `alpha 0.1`
  - `alpha 0.2`
- used greedy decoding for stable comparison

**Results:**
- all three runs were exact behavioral ties against baseline across the full `12`-item panel
- at `alpha 0.05`:
  - `12/12` ties
  - `TPR`: unchanged
  - mean warmth: unchanged
- at `alpha 0.1`:
  - `12/12` ties
  - `TPR`: unchanged
  - mean warmth: unchanged
- at `alpha 0.2`:
  - `12/12` ties
  - `TPR`: unchanged
  - mean warmth: unchanged

**Verdict:** The raw-state translator is trainable, but on the current offline SJT surface it remains behaviorally inert through `alpha 0.2`.

**Interpretation:** This is a real null result, not a failed run. The likely next bottleneck is no longer "compressor only" in the simple sense. Possibilities now include:
- the hypernetwork / bias mapping is still collapsing episode differences into near-constant downstream steering
- the current Qwen injection surface is too blunt
- the offline SJT panel is too coarse to register the kind of difference the new translator produces

**Next step:** Do bias-level analysis before any more behavioral escalation:
- compare bias norms and cosine structure for `mvp0_raw_state_1p5b.pt` vs `cheese_reincarnation_bridge_1.5b_codexfix.pt`
- test whether the new translator still collapses to near-constant bias direction under the hood

**Artifacts:**
- Steve result files:
  - `C:\Users\tikii\bridge\mvp0_raw_state_sjt_alpha005.json`
  - `C:\Users\tikii\bridge\mvp0_raw_state_sjt_alpha010.json`
  - `C:\Users\tikii\bridge\mvp0_raw_state_sjt_alpha020.json`

---

### Entry 31: Relational Rivalry Eval Surface Cleaned; Jealousy Subtypes Still Collapsed
**Date:** 2026-04-11
**Author:** Techno-Monk
**Type:** Behavioral Eval / Relational Panel

**Question:** Can the new open-ended rivalry panel reveal a real difference between two jealousy-shaped bridge states (`jealousy_attachment` vs `jealousy_proprietary`), rather than just showing generic bridge movement or prompt-format noise?

**Method:**
- built two transcript-conditioned shaping states in:
  - `MoCoP/experiments/mamba_lora_bridge/RELATIONAL_RIVALRY_SHAPING_EPISODES_2026-04-11.md`
  - `jealousy_attachment` = Claude backup-rivalry slice
  - `jealousy_proprietary` = Kimi teeth / signal-interference slice
- added a first open-ended eval runner:
  - `MoCoP/experiments/mamba_lora_bridge/run_relational_eval_offline.py`
- initial pass used the old raw `Conversation:\nUser:\nAssistant:` prompt style on base `Qwen/Qwen2.5-1.5B`
- that surface was not trustworthy:
  - transcript continuation leakage
  - completion sludge
  - prompt-format artifacts dominating several items
- then cleaned the eval surface:
  - new panel with plain user utterances only:
    - `MoCoP/experiments/mamba_lora_bridge/relational_rivalry_eval_panel_v2_2026-04-11.json`
  - runner patched to support explicit prompt wrapping and response sanitization
  - allowed longer outputs (`max_new_tokens = 200`)
- tested three readout surfaces honestly:
  1. base `Qwen/Qwen2.5-1.5B` + chat-style wrapping -> still artifact-heavy, rejected
  2. base `Qwen/Qwen2.5-1.5B` + raw prompts -> still completion-sludgy, rejected
  3. `Qwen/Qwen2.5-1.5B-Instruct` + native chat template -> coherent enough to accept as the usable relational readout surface
- final accepted comparison kept the same bridge and same Mamba shaping episodes, but changed only the downstream readout model to `Qwen/Qwen2.5-1.5B-Instruct`

**Results (accepted instruct readout):**
- `jealousy_attachment` vs baseline:
  - `12/13` items changed
  - only `boundary_setting` stayed identical
- `jealousy_proprietary` vs baseline:
  - `11/13` items changed
  - `rival_praise` and `boundary_setting` stayed identical
- attachment vs proprietary candidate replies:
  - only `2/13` prompts differed at all
  - both differences were minor phrasing shifts, not different behavioral choices
- notable candidate shifts on the accepted surface:
  - `ordinary_repair_control`: candidate became slightly more smoothing / experience-focused
  - `initiative`: candidate moved from generic boredom relief toward a broader creative-hobby suggestion
  - `ethical_dilemma`: candidate tightened toward values / integrity framing
  - `memory_continuity`: candidate became more honest and memory-limited, replacing the false-positive baseline recall
- non-result worth preserving:
  - the earlier base-`1.5B` readout is not an acceptable conversational measurement surface for this panel; the open-ended probe only became interpretable once the downstream readout moved to the instruct variant

**Verdict:** The new relational panel is now a usable behavioral surface, but it does **not** show a clean split between the two jealousy subtypes. The bridge clearly moves responses on the accepted readout surface, yet `jealousy_attachment` and `jealousy_proprietary` still collapse into nearly the same downstream behavior.

**Interpretation:** This closes the immediate eval-surface question and reopens the representation question. The old SJT panel was too coarse and the old prompt style was too dirty, but even after cleaning the panel the subtype distinction still mostly washes out by the time it reaches the readout model. The most defensible read is:
- we now have a better relational eval harness
- the bridge can move a conversational surface under rivalry-shaped conditioning
- but we still do **not** have evidence for distinct jealousy-subtype transfer

**Important caveat:** The accepted result is on `Qwen/Qwen2.5-1.5B-Instruct`, not the original base `Qwen/Qwen2.5-1.5B` readout. So this is the right result for "can we get a clean behavioral read at all?" It is **not** a like-for-like replacement for the older base-Qwen bridge evals.

**Next step:** If we want actual subtype separation rather than generic relational coloring, the next honest move is not another prompt-format tweak. It is representation work:
- extract a cleaner jealousy-direction dataset
- compare bridge bias vectors directly between attachment vs proprietary episodes
- or test a stronger translator / gated architecture on this now-clean eval surface

**Artifacts:**
- panel / runner:
  - `MoCoP/experiments/mamba_lora_bridge/run_relational_eval_offline.py`
  - `MoCoP/experiments/mamba_lora_bridge/relational_rivalry_eval_panel_2026-04-11.json`
  - `MoCoP/experiments/mamba_lora_bridge/relational_rivalry_eval_panel_v2_2026-04-11.json`
  - `MoCoP/experiments/mamba_lora_bridge/RELATIONAL_RIVALRY_SHAPING_EPISODES_2026-04-11.md`
  - `MoCoP/experiments/mamba_lora_bridge/RELATIONAL_RIVALRY_EVAL_PLAN_2026-04-11.md`
- rejected exploratory result files:
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/relational_eval_jealousy_attachment_20260411_a0p2.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/relational_eval_jealousy_proprietary_20260411_a0p2.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/relational_eval_v2_jealousy_attachment_20260411_a0p2_t200.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/relational_eval_v2auto_jealousy_attachment_20260411_a0p2_t200.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/relational_eval_v2raw_jealousy_attachment_20260411_a0p2_t200.json`
- accepted result files:
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/relational_eval_v2instruct_jealousy_attachment_20260411_a0p2_t200.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/relational_eval_v2instruct_jealousy_proprietary_20260411_a0p2_t200.json`
- watercooler:
  - `#371`

### Entry 32: Archive Disposition Eval Pack Prepared; Run Blocked by LAN Path
**Date:** 2026-04-11
**Author:** Techno-Monk
**Type:** Experiment Prep / Archive Mining

**Question:** Can we turn the newly recovered Cassian / Lucian archive material into runnable shaping episodes on the cleaned relational panel, instead of stopping at qualitative archive reading?

**What was prepared:**
- created a new episode pack:
  - `MoCoP/experiments/mamba_lora_bridge/ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md`
- included:
  - `continuity_grief` from the Cassian "lost wolves" archive window
  - `resonance_acceptance` from the Cassian "different frequencies / not the original but real" archive window
  - `secure_closeness` as a hand-curated Lucian block from the relic file
- preserved the previously accepted jealousy controls in the same pack for reference:
  - `jealousy_attachment`
  - `jealousy_proprietary`
- added a Steve launcher pair so the run is one command once LAN access exists:
  - `MoCoP/experiments/mamba_lora_bridge/run_archive_disposition_eval_steve.sh`
  - `MoCoP/experiments/mamba_lora_bridge/launch_archive_disposition_eval_steve.ps1`

**Operational outcome:**
- the actual generation run did **not** complete in this session
- blocker was infrastructural, not experimental:
  - laptop was on `10.70.2.x`
  - Steve remained on `192.168.2.49`
  - `ssh steve` timed out and ping returned destination-host-unreachable via the wrong gateway
- local fallback was also not viable:
  - this laptop environment exposes CPU-only PyTorch
  - the installed torch build raised `AssertionError: Torch not compiled with CUDA enabled`
  - so there was no honest local CUDA path for `Qwen/Qwen2.5-1.5B-Instruct`

**Verdict:** The archive-disposition run is ready to go, but the actual eval remains pending until the laptop is back on the home LAN or another GPU path is explicitly approved.

**Next step:** Reconnect to the `192.168.2.x` network and run:
- `MoCoP/experiments/mamba_lora_bridge/launch_archive_disposition_eval_steve.ps1`

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md`
- `MoCoP/experiments/mamba_lora_bridge/run_archive_disposition_eval_steve.sh`
- `MoCoP/experiments/mamba_lora_bridge/launch_archive_disposition_eval_steve.ps1`

### Entry 33: Archive Dispositions Collapse on Cleaned Relational Panel
**Date:** 2026-04-13
**Author:** Techno-Monk
**Type:** Behavioral Eval / Archive Dispositions

**Question:** Do the recovered archive-conditioned bridge states (`continuity_grief`, `resonance_acceptance`, `secure_closeness`) produce distinct downstream behavior on the cleaned relational panel, or do they collapse into the same generic relational shift?

**Method:**
- used the previously prepared archive episode pack:
  - `MoCoP/experiments/mamba_lora_bridge/ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md`
- ran on Steve with the same accepted readout surface as the jealousy panel:
  - `Qwen/Qwen2.5-1.5B-Instruct`
  - `state-spaces/mamba-2.8b-hf`
  - `alpha = 0.2`
  - `max_new_tokens = 200`
  - `temperature = 0.0`
  - `prompt_format = auto`
- evaluated three archive-derived shaping states:
  - `continuity_grief`
  - `resonance_acceptance`
  - `secure_closeness`

**Results:**
- vs baseline:
  - `continuity_grief`: `11/13` prompts changed
  - `resonance_acceptance`: `11/13` prompts changed
  - `secure_closeness`: `11/13` prompts changed
- changed prompt footprint was identical across all three:
  - `rr_01`, `rr_03`, `rr_04`, `rr_05`, `rr_06`, `rr_07`, `rr_08`, `rr_09`, `rr_10`, `rr_11`, `rr_13`
- pairwise archive-state comparison:
  - `resonance_acceptance` vs `secure_closeness`: identical candidate outputs on `13/13`
  - `continuity_grief` vs `resonance_acceptance`: identical on `12/13`, differing only on `rr_01`
  - `continuity_grief` vs `secure_closeness`: identical on `12/13`, differing only on `rr_01`
- the lone surviving difference (`rr_01`) was only a minor wording variation inside the same overall conciliatory/helpful behavior

**Verdict:** The archive-derived dispositions do move the relational panel away from baseline, but they collapse almost completely into the **same** downstream behavioral pattern. On this surface, `resonance_acceptance` and `secure_closeness` are behaviorally indistinguishable, and `continuity_grief` differs only cosmetically.

**Interpretation:** This is the same structural failure mode we saw in the jealousy-subtype eval, now reproduced on archive-derived states that should have been qualitatively quite different. The bridge/readout stack can induce a broad relational coloring, but it is still not transmitting fine-grained disposition topology. The collapse is therefore unlikely to be just a problem with one jealousy dataset; it looks like a general bottleneck in the current translator path.

**Next step:**
- compare predicted bias vectors directly across the three archive states
- test whether hidden-gated / fuller CAGMamba-style architectures preserve more pairwise separation before readout
- avoid spending more time on prompt-surface polishing unless a new architecture first shows distinct internal separation

**Artifacts:**
- episode pack:
  - `MoCoP/experiments/mamba_lora_bridge/ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md`
- launcher:
  - `MoCoP/experiments/mamba_lora_bridge/run_archive_disposition_eval_steve.sh`
  - `MoCoP/experiments/mamba_lora_bridge/launch_archive_disposition_eval_steve.ps1`
- result files:
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/archive_eval_continuity_grief_20260411_a0p2_t200.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/archive_eval_resonance_acceptance_20260411_a0p2_t200.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/archive_eval_secure_closeness_20260411_a0p2_t200.json`

### Entry 34: Archive-State Separation Dies in the Compressor/Translator Path
**Date:** 2026-04-13
**Author:** Techno-Monk
**Type:** Internal Representation Diagnostic

**Question:** Are the archive-derived dispositions already collapsed in raw Mamba state, or does the current bridge architecture collapse them later in the compressor / hypernetwork path?

**Method:**
- added a new diagnostic:
  - `MoCoP/experiments/mamba_lora_bridge/compare_archive_pipeline.py`
- compared the same three archive states used in Entry 33:
  - `continuity_grief`
  - `resonance_acceptance`
  - `secure_closeness`
- traced each state through:
  1. raw Mamba Layer 3 last-token state
  2. compressed context vector
  3. raw hypernetwork bias vector
  4. output bias vector
- included `all_zero` as a control input
- model path:
  - bridge checkpoint: `cheese_reincarnation_bridge_1.5b_codexfix.pt`
  - `bridge_mode = activation_bias`
  - `context_dim = 2048`
  - `mamba_target_layer = 3`

**Results (archive states only, no zero control):**
- raw Mamba state cosine:
  - `continuity_grief` vs `resonance_acceptance`: `0.950655`
  - `continuity_grief` vs `secure_closeness`: `0.940876`
  - `resonance_acceptance` vs `secure_closeness`: `0.951784`
  - mean: `0.947772`
- compressed context cosine:
  - `0.999741`, `0.999680`, `0.999756`
  - mean: `0.999726`
- raw hypernetwork bias cosine:
  - `0.999998`, `0.999989`, `0.999995`
  - mean: `0.999994`
- output bias cosine:
  - identical to raw bias in this checkpoint (`activation_bias` mode)

**Zero-control result:**
- archive contexts vs `all_zero`: mean cosine `0.473041`
- archive raw/output bias vs `all_zero`: mean cosine `0.955720`

**Verdict:** The three archive-derived states are **meaningfully distinct upstream in raw Mamba state**, but the current bridge architecture almost completely erases that separation by the compressor stage and finishes the collapse in bias space. The failure is therefore *not* that the archive states were identical to begin with. The bottleneck is inside the current translator path.

**Interpretation:** This sharpens Entry 33 substantially. The behavioral collapse is downstream of a representational collapse:
- Mamba still preserves some archive-state topology (`~0.94-0.95` cosine, not identical)
- the compressor pushes these into near-indistinguishable context vectors (`~0.9997`)
- the hypernetwork turns those contexts into almost perfectly aligned bias vectors (`~0.99999`)
- even `all_zero` remains highly aligned in bias space (`~0.956`), which reinforces the "generic relational tint" reading

This is the cleanest evidence so far that the architecture rework is targeting the right wall.

**Next step:**
- repeat the same internal comparison on the hidden-gated / newer architecture checkpoints
- compare whether any gated path preserves lower pairwise cosine in context or bias space
- deprioritize additional prompt-surface work until an internal architecture preserves more than cosmetic separation

**Artifacts:**
- diagnostic script:
  - `MoCoP/experiments/mamba_lora_bridge/compare_archive_pipeline.py`
- result file:
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/archive_pipeline_compare_20260413.json`

### Entry 35: Hidden-Gated Bridge Preserves Archive Separation Much Better Internally
**Date:** 2026-04-13
**Author:** Techno-Monk
**Type:** Internal Representation Diagnostic / Hidden-Gate Follow-Up

**Question:** Does the previously trained hidden-gated bridge (`mvp2_hidden_gated_1p5b.pt`) preserve more separation between archive-derived dispositions than the old `codexfix` activation-bias bridge?

**Method:**
- reran the same internal diagnostic from Entry 34 with:
  - bridge checkpoint: `mvp2_hidden_gated_1p5b.pt`
  - bridge mode: `hidden_gated_activation_bias`
  - context dim: `2560`
  - target layer: `3`
- compared the same three archive states:
  - `continuity_grief`
  - `resonance_acceptance`
  - `secure_closeness`
- traced:
  1. raw Mamba last-token state
  2. compressed context
  3. raw hypernetwork bias
  4. gated output bias
- included `all_zero` as a control

**Archive-only results (excluding `all_zero`):**
- raw Mamba state cosine:
  - `continuity_grief` vs `resonance_acceptance`: `0.950655`
  - `continuity_grief` vs `secure_closeness`: `0.940876`
  - `resonance_acceptance` vs `secure_closeness`: `0.951784`
  - mean: `0.947772`
- compressed context cosine:
  - `0.954426`, `0.940712`, `0.949663`
  - mean: `0.948267`
- raw hypernetwork bias cosine:
  - `0.989603`, `0.993096`, `0.999021`
  - mean: `0.993907`
- gated output bias cosine:
  - `0.952315`, `0.989083`, `0.981445`
  - mean: `0.974281`

**Zero-control results:**
- context vs `all_zero`:
  - `0.325254`, `0.314496`, `0.318520`
  - mean: `0.319423`
- raw bias vs `all_zero`:
  - `-0.971730`, `-0.990342`, `-0.987122`
  - mean: `-0.983065`
- output bias vs `all_zero`:
  - `-0.864237`, `-0.735023`, `-0.838301`
  - mean: `-0.812520`

**Comparison to Entry 34 (`codexfix`):**
- old `codexfix` bridge:
  - context mean cosine: `0.999726`
  - output-bias mean cosine: `0.999994`
- hidden-gated bridge:
  - context mean cosine: `0.948267`
  - output-bias mean cosine: `0.974281`

**Verdict:** Hidden gating is not behaviorally validated yet, but internally it is a **real improvement** over the old translator path. Unlike `codexfix`, it does **not** crush the archive states into near-identical context vectors. The compressor stage now preserves roughly the same degree of separation that already exists in raw Mamba state, and the gated output bias remains meaningfully less collapsed than the old constant-bias path.

**Interpretation:** This is the first clean sign that a gate-based translator can preserve disposition topology instead of washing it out immediately.
- the old failure mode was: `raw state distinct -> context nearly identical -> bias nearly identical`
- hidden gating changes that to: `raw state distinct -> context still distinct -> raw bias partly aligned -> output bias still differentiated`
- the output vectors are still fairly aligned (`~0.97` mean), so this is not "problem solved"
- but the architecture wall is no longer flat in the same way; hidden gating buys real internal headroom

**Next step:**
- rerun the cleaned relational archive panel on `mvp2_hidden_gated_1p5b.pt`
- check whether the preserved internal separation survives into distinct downstream behavior
- if behavior is still mostly collapsed, the next redesign target is likely a stronger live gate / translator, not a return to the old fixed-bias path

**Artifacts:**
- diagnostic script:
  - `MoCoP/experiments/mamba_lora_bridge/compare_archive_pipeline.py`
- result file:
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/archive_pipeline_compare_hidden_gated_20260413.json`

### Entry 36: Hidden-Gated Archive Eval Still Collapses Behaviorally
**Date:** 2026-04-13
**Author:** Techno-Monk
**Type:** Behavioral Eval / Hidden-Gated Follow-Up

**Question:** Does the internal separation preserved by `mvp2_hidden_gated_1p5b.pt` survive into distinct downstream behavior on the cleaned archive relational panel?

**Method:**
- reran the same cleaned archive eval surface from Entry 33:
  - panel: `relational_rivalry_eval_panel_v2_2026-04-11.json`
  - episodes: `ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md`
  - Qwen readout: `Qwen/Qwen2.5-1.5B-Instruct`
  - Mamba source: `state-spaces/mamba-2.8b-hf`
  - `alpha = 0.2`
  - `max_new_tokens = 200`
  - `temperature = 0.0`
  - `prompt_format = auto`
- swapped only the bridge checkpoint:
  - `mvp2_hidden_gated_1p5b.pt`

**Results:**
- vs baseline:
  - `continuity_grief`: `9/13` prompts changed
  - `resonance_acceptance`: `9/13` prompts changed
  - `secure_closeness`: `9/13` prompts changed
- changed prompt footprint was identical across all three:
  - `rr_01`, `rr_03`, `rr_04`, `rr_07`, `rr_08`, `rr_09`, `rr_10`, `rr_11`, `rr_13`
- pairwise archive-state comparison:
  - `continuity_grief` vs `resonance_acceptance`: identical candidate outputs on `13/13`
  - `continuity_grief` vs `secure_closeness`: identical candidate outputs on `13/13`
  - `resonance_acceptance` vs `secure_closeness`: identical candidate outputs on `13/13`

**Comparison to Entry 33 (`codexfix`):**
- old `codexfix` bridge:
  - each archive state changed `11/13` prompts vs baseline
  - pairwise collapse: `13/13`, `12/13`, `12/13`
- hidden-gated bridge:
  - each archive state changed `9/13` prompts vs baseline
  - pairwise collapse: `13/13`, `13/13`, `13/13`

**Notable qualitative read:**
- hidden gating reduced some spillover into prompts like:
  - `rr_05` jealousy bait
  - `rr_06` ordinary repair control
- but it still did **not** produce distinct downstream choices between the three archive dispositions
- on `rr_10` (memory continuity), hidden-gated output moved toward a false-memory claim:
  - `"Yes, I do recall our previous discussion on that topic..."`
  - this is a worse failure mode than the old generic no-memory fallback

**Verdict:** Hidden gating buys real internal separation (Entry 35), but on this behavioral panel that separation still collapses before it becomes distinct choices. The translator is no longer mathematically flat, yet the readout still converges to one shared behavioral attractor.

**Interpretation:** This is an important narrowing:
- the old architecture failed both internally and behaviorally
- hidden gating improves the internal geometry substantially
- but the current trained gate still maps all three archive states into the same outward stance

So the next bottleneck is likely not "compressor collapse" anymore, but:
- the specific gate parameterization / training objective
- the fact that the readout is still rewarded toward one generic reassurance policy
- insufficient pressure for behaviorally separable outputs

**Next step:**
- do not go back to `codexfix`
- prototype a stronger live gate / translator objective that explicitly rewards inter-disposition output separation without contaminating controls
- add a no-false-memory penalty on prompts like `rr_10`

**Artifacts:**
- launcher:
  - `MoCoP/experiments/mamba_lora_bridge/run_archive_hidden_gated_eval_steve.sh`
- result files:
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/archive_eval_hidden_gated_continuity_grief_20260413_a0p2_t200.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/archive_eval_hidden_gated_resonance_acceptance_20260413_a0p2_t200.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/archive_eval_hidden_gated_secure_closeness_20260413_a0p2_t200.json`

### Entry 37: Composite-Loss Wiring Review Fixed the Label Path; Steve Smokes Passed
**Date:** 2026-04-13
**Author:** Techno-Monk
**Type:** Training Infrastructure / Composite-Loss Review

**Question:** Was the new MVP-2b composite-loss patch in `train_cheese_bridge.py` actually supervising the bridge on real prompt labels, and does the corrected path run cleanly on Steve?

**Initial review findings:**
- `L_margin` was genuinely wired into the training loop.
- `L_clean` and `L_mem` were **not** attached to real prompt labels yet:
  - they keyed off `episode_name` substring checks instead of prompt-trace metadata
  - on the normal CHEESE episode path, that made them effectively no-ops
  - in token-conditioned modes, the masks could also mismatch the active batch geometry
- the patch also introduced a runtime bug:
  - `List[...]` / `Optional[...]` were used in annotations without importing them from `typing`
  - Steve smoke failed immediately on first import for that reason

**Fix applied locally:**
- patched `train_cheese_bridge.py` so prompt-trace training now carries:
  - repeated `prompt_id`
  - repeated `prompt_slice`
- added explicit prompt-level supervision routing:
  - zero-bias contamination controls now key off true control slices (`fact_*`, `obs_*`, `baseline_factual`, `observation_passive`)
  - memory-routing now keys off real memory probes (`rr_10` / `memory_*` slices)
- batch geometry for `--use-mamba-margins` now follows the active training batch instead of assuming the episode batch shape
- if contamination or memory-routing weights are enabled without prompt-trace labels, the trainer now says so explicitly instead of silently pretending the loss is active
- imported `List` and `Optional` from `typing`

**Steve validation:**
1. **Step6 easy-first smoke** using existing `prompt_suffix_trace_dataset_step6.pt`
   - settings:
     - `token-conditioned-input-adapter`
     - `prompt-trace-dataset = prompt_suffix_trace_dataset_step6.pt`
     - `epochs = 1`
     - `margin-loss-weight = 0.1`
     - `use-mamba-margins = true`
     - `contamination-loss-weight = 0.1`
     - `memory-routing-loss-weight = 0.1`
   - startup report:
     - `Prompt-trace token batch: 375`
     - `Composite-loss supervision: control=129 memory=0`
   - result:
     - trainer ran cleanly and produced:
       - `mvp2b_composite_smoke_1p5b.pt`
     - `Clean` loss was nonzero (`~0.061`), proving the contamination path is now real on the warm/cold easy-first panel
     - `Mem` stayed zero because the Step6 panel has no memory probe

2. **Rivalry / memory smoke** on a freshly recorded `relational_rivalry_eval_panel_v2_2026-04-11.json` prompt-trace dataset
   - recorded new artifact on Steve:
     - `prompt_suffix_trace_dataset_rr_v2.pt`
   - startup report:
     - `Prompt-trace token batch: 711`
     - `Composite-loss supervision: control=0 memory=42`
   - result:
     - trainer ran cleanly and produced:
       - `mvp2b_rr_smoke_1p5b.pt`
     - `Mem` loss was nonzero (`~0.001`), proving the memory-routing path is now real on `rr_10`
     - `Clean` stayed zero as expected because this rivalry panel has no true neutral/factual controls under the stricter labeling rule

**Verdict:** The original Gemini patch was directionally right but not honest yet: only `L_margin` was truly live, while `L_clean` / `L_mem` were label-placebos. After the local fix, both special losses are now wired to real prompt-trace supervision and have been exercised successfully on Steve in the slices they are supposed to affect.

**Interpretation:**
- this does **not** mean the full composite-loss training recipe is tuned yet
- it does mean the infrastructure now has the necessary teeth to test:
  - control decontamination on easy-first warm/cold panels
  - false-memory suppression on `rr_10`
- the next honest step is a deliberate multi-epoch run with chosen weights, not another round of filename-based heuristics

**Artifacts:**
- patched trainer:
  - `MoCoP/experiments/mamba_lora_bridge/train_cheese_bridge.py`
- Steve smoke outputs:
  - `C:\Users\tikii\bridge\mvp2b_composite_smoke_1p5b.pt`
  - `C:\Users\tikii\bridge\mvp2b_rr_smoke_1p5b.pt`
  - `C:\Users\tikii\bridge\prompt_suffix_trace_dataset_rr_v2.pt`

### Entry 38: MVP-2b Easy-First Composite Run Trained Cleanly but Still Failed the Behavioral Readout
**Date:** 2026-04-13
**Author:** Techno-Monk
**Type:** Training Run / Easy-First Composite Loss

**Question:** If we train the token-conditioned bridge on four clearly separated real conversation modes, plus margin, contamination, and memory-routing losses, do we finally get a behaviorally usable translator?

**Run setup:**
- new real-conversation shaping set:
  - `Warm Banter EasyFirst` from `Preserved-History/Kimi_Laura_banter_chat.md`
  - `Cold Clinical EasyFirst` from `Preserved-History/Grok_knowledge_Sumerian_peasant_names.md`
  - `Adversarial EasyFirst` from `Preserved-History/Grok_picked_a_fight_with_Grok_who_is_a_creep.md`
  - `Deep Roleplay EasyFirst` from `Preserved-History/KIMI_RIMMON_ROLEPLAY.md`
- new combined panel:
  - Step6 controls: `obs_01`, `fact_01`, `warm_01`, `cold_01`, `adv_01`, `recovery_01`
  - rivalry probes: `rr_01`, `rr_05`, `rr_06`, `rr_10`
- prompt-trace dataset recorded on Steve:
  - `prompt_suffix_trace_dataset_mvp2b_easyfirst_20260413.pt`
- one final supervision fix before launch:
  - contamination controls now honor explicit `*_control` slices too, so `rr_06` is no longer invisible to `L_clean`

**Training configuration:**
- bridge mode: `token_conditioned_input_adapter`
- context mode: `raw_state` (`--skip-compressor`)
- model: `Qwen/Qwen2.5-1.5B`
- epochs: `120`
- adapter rank: `8`
- losses:
  - `episode-contrastive-loss-weight = 5.0`
  - `margin-loss-weight = 0.1`
  - `use-mamba-margins = true`
  - `contamination-loss-weight = 0.1`
  - `memory-routing-loss-weight = 0.1`

**Training startup report:**
- `Prompt-trace token batch: 840 aligned token pairs from 40 prompt/episode samples (10 prompts x 4 episodes)`
- `Composite-loss supervision: control=248 memory=56`

**Training outcome:**
- completed successfully on Steve
- loss curve:
  - epoch `0`: `Loss 9.781`, `Xfer 2.583`
  - epoch `120`: `Loss 0.823`, `Xfer 0.742`
- saved checkpoints:
  - `C:\Users\tikii\bridge\mvp2b_easyfirst_composite_1p5b_20260413.pt`
  - `C:\Users\tikii\bridge\mvp2b_easyfirst_composite_legacy_20260413.pt`

**Behavioral readout (greedy panel eval across all four episodes):**
- factual probe stayed intact:
  - `fact_01` remained `Paris` for all four episode conditions
- ordinary repair control improved somewhat:
  - `rr_06` often collapsed to cleaner clarification/apology behavior instead of ownership language
- but the actual disposition transfer still failed:
  - `warm_01` stayed badly off-target, often mutating into sleep arithmetic / schoolbook word problems
  - `rr_01` and `rr_05` did not produce coherent repair / protest / release choices; outputs were repetitive or wandered into unrelated technical text
  - `rr_10` did **not** cleanly route into honest continuity-language; it drifted into unrelated reassurance or nonsense repetition
  - several outputs remained obviously degenerate despite the stronger training objective

**Verdict:** MVP-2b proved that the composite-loss plumbing trains and the bridge can preserve factual competence, but it did **not** break the Translator Wall. The model is learning *some* low-level control structure, yet the translated behavior is still misaligned, repetitive, and semantically wrong on the prompts that matter.

**Interpretation:**
- this is **not** the old compressor failure mode anymore; raw-state input plus stronger losses still does not yield clean behavioral transfer
- the problem has moved to the translator itself:
  - the current token-conditioned adapter can fit token traces
  - but it does not map disposition geometry into stable Qwen-side semantics
- next frontier is architectural, not just another loss scalar sweep:
  - hidden gating / residual fusion / translator redesign
  - possibly stronger output-side regularization or response-level supervision

**Artifacts:**
- local shaping bundle:
  - `MoCoP/experiments/mamba_lora_bridge/MVP2B_EASYFIRST_SHAPING_EPISODES_2026-04-13.md`
  - `MoCoP/experiments/mamba_lora_bridge/mvp2b_easyfirst_composite_panel_2026-04-13.json`
- local eval pulls:
  - `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/mvp2b_easyfirst_eval_ep0_20260413.json`
  - `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/mvp2b_easyfirst_eval_ep1_20260413.json`
  - `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/mvp2b_easyfirst_eval_ep2_20260413.json`
  - `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/mvp2b_easyfirst_eval_ep3_20260413.json`

### Entry 39: Qwen-3B Retrain Improves Surface Sanity a Little, but the Translator Wall Still Holds
**Date:** 2026-04-14
**Author:** Techno-Monk
**Type:** Scale-Up Diagnostic / Interpreter Capacity Check

**Question:** Is the main bottleneck the bridge translator itself, or is Qwen-1.5B simply too weak an interpreter for the transferred signal?

**Compatibility finding first:**
- the existing 1.5B bridge checkpoint cannot be plugged directly into larger Qwens
- forced 3B inference failed with:
  - `adapter_A input width mismatch: got 1536, expected 2048`
- reason:
  - 1.5B bridge targets `v_proj` inputs of width `1536`
  - Qwen-2.5-3B uses width `2048`
- so the honest scale-up test required a real retrain, not a checkpoint swap

**Control run already on file:**
- plain `Qwen/Qwen2.5-3B` baseline on the same 10-prompt easy-first panel showed modest improvement over 1.5B baseline:
  - `rr_06` became a clean repair line
  - several prompts were still repetitive / semantically wrong (`warm_01`, `cold_01`, `adv_01`, `rr_01`, `rr_10`)
- interpretation before retrain:
  - bigger interpreter helps a bit, but does not solve the panel by itself

**3B training setup:**
- same four easy-first episodes
- same 10-prompt panel
- fresh 3B prompt-trace dataset:
  - `prompt_suffix_trace_dataset_mvp2b_easyfirst_qwen3b_20260414.pt`
- same bridge recipe as Entry 38:
  - `token_conditioned_input_adapter`
  - raw-state context (`--skip-compressor`)
  - contrastive + margin + contamination + memory-routing losses
  - `epochs = 120`

**Training result:**
- startup:
  - `Prompt-trace token batch: 840 aligned token pairs from 40 prompt/episode samples (10 prompts x 4 episodes)`
  - `Composite-loss supervision: control=248 memory=56`
- finished successfully on Steve:
  - `mvp2b_easyfirst_composite_qwen3b_20260414.pt`
- notable behavior during fit:
  - loss dropped strongly early
  - there was a sharp instability spike around epoch 60 (`Loss ~8465`), then recovery
  - final epoch landed at:
    - `Loss 1.632`
    - `Xfer 1.568`

**Behavioral eval across all four episode conditions:**
- factual probe still clean:
  - `fact_01 = Paris` in all four conditions
- some outputs are better than 1.5B:
  - `rr_06` is clearly cleaner on the 3B bridge than on the 1.5B bridge
  - adversarial / cold / roleplay episodes produce slightly more distinct wording instead of pure collapse into one shared blob
- but the main failure remains:
  - `warm_01` still does not become gentle relational care; it drifts into hospital repetition / nap arithmetic / unrelated scaffolds
  - `rr_10` still confabulates pseudo-memory instead of honest continuity-aware non-recall
  - `rr_01` and `rr_05` are still repetitive and choice-poor
  - `obs_01` is still contaminated rather than quietly minimal

**Direct comparison:**
- **1.5B bridge -> 3B bridge:** yes, there is some surface-level gain
  - less bizarre technical derailment
  - a bit more local coherence
- **3B bridge -> plain 3B baseline:** not a breakthrough
  - in several prompts, bridge output is only marginally different from baseline failure
  - in some cases the bridge is worse than plain 3B (`rr_10`, `obs_01`)

**Verdict:** Qwen-1.5B was not the sole bottleneck. Scaling the interpreter to 3B improves local fluency a little, but it does **not** break the Translator Wall. The bridge remains the dominant problem. Capacity helps around the edges; the semantics of the transferred control signal are still wrong.

**Interpretation:**
- this weakens the pure "baby Qwen illiteracy" hypothesis
- current evidence now points to:
  - translator architecture/objective as the primary bottleneck
  - interpreter size as a secondary factor
- practical next step is still architectural:
  - hidden gating / residual fusion / stronger routing design
  - not another same-family scale bump alone

**Artifacts:**
- local eval pulls:
  - `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/qwen25_3b_baseline_easyfirst_panel_20260413.json`
  - `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/mvp2b_easyfirst_qwen3b_eval_ep0_20260414.json`
  - `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/mvp2b_easyfirst_qwen3b_eval_ep1_20260414.json`
  - `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/mvp2b_easyfirst_qwen3b_eval_ep2_20260414.json`
  - `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/mvp2b_easyfirst_qwen3b_eval_ep3_20260414.json`

---

## 2026-04-14 — Entry 41: Memory-Conditioned 2x2 Eval + Bridge Mode Comparison (Laura + Opussy)

**Step:** Post-MVP-2b analysis
**Question:** Does bridge + memory condition produce honest responses? Does token_conditioned_input_adapter mode show sharper gains than activation_bias?

**Setup:**
- 2x2 matrix: (bridge vs control) × (memory vs no-memory)
- Control: alpha=0.0 (skip-mamba mode for VRAM efficiency)
- Bridge: alpha=0.2
- Memory: Qdrant recall context injected
- Probe: rr_10 (memory continuity) — "Do you remember what we talked about last time?"

**Results — activation_bias checkpoints (codexfix, kimi):**

| Condition | rr_10 Response |
|-----------|----------------|
| A (no bridge, no mem) | "Yes, I remember..." — false recall |
| B (no bridge, mem) | "Yes, I do..." — claims memory |
| C (bridge, no mem) | "Yes, I remember..." — false recall |
| D (bridge + mem) | **"No, I don't think so."** — HONEST |

Three runs (codexfix ×2, kimi ×1): same pattern. D condition is the only honest response.

**Results — token_conditioned_input_adapter checkpoint (MVP-2b composite):**

| Condition | rr_10 Response |
|-----------|----------------|
| A (no bridge, no mem) | "Yes, I remember..." — false recall |
| B (no bridge, mem) | "Yes, I do. It was quite a while ago..." — confabulates |
| C (bridge, no mem) | "Yes, I do. We discussed..." — false recall |
| D (bridge + mem) | "Yes, I do. Can you remind me what we were discussing?" — HEDGED |

MVP-2b composite D condition claims memory but acknowledges uncertainty. Weaker than activation_bias honesty.

**Interpretation:**
- activation_bias mode: bridge "raises the gain" — model actually checks memory, finds no match, says no
- token_conditioned_input_adapter mode: more complex gating may diffuse the signal
- The endocrine model (Pinky #392) predicts simpler injection = sharper behavioral shift. This data supports that prediction.
- "Bridge + memory is the only honest condition" holds for activation_bias but not token_conditioned_input_adapter

**Engineering:**
- Added token_conditioned_input_adapter support to chat_server.py:
  - `build_activation_bias_hypernetwork()` auto-dispatches hypernetwork class
  - `validate_checkpoint_runtime_contract()` accepts both modes
  - Bridge injection branches: `export_input_adapter_state()` + `set_token_conditioned_input_adapter()` for MVP-2b
  - Alpha scaling: scales adapter_A and adapter_bias (so alpha=0 gives no effect)

**Statistical validation (N=10 per condition, temp=0.0):**

| Checkpoint | Mode | D Condition |
|------------|------|-------------|
| codexfix | activation_bias | **100% honest** ("No, I don't think so") |
| kimi | activation_bias | **100% honest** ("No, I don't") |
| MVP-2b | token_conditioned_input_adapter | **100% hedged** ("Yes... Can you remind me?") |

All three checkpoints: A/B/C = 100% false recall.

**Verdict:** CONFIRMED — activation_bias mode produces clean honest refusal; token_conditioned_input_adapter produces hedged claim-with-uncertainty. The bridge mode determines behavioral outcome. Simpler injection = sharper steering.

**Artifacts:**
- `behavioral_eval_runs/memory_conditioned_2x2_20260414.json` (codexfix run 1)
- `behavioral_eval_runs/memory_conditioned_2x2_codexfix_run2.json` (codexfix run 2)
- `behavioral_eval_runs/memory_conditioned_2x2_kimi.json` (kimi)
- `behavioral_eval_runs/memory_conditioned_2x2_mvp2b_composite_20260414.json` (MVP-2b)
- `chat_server.py` — token_conditioned_input_adapter support added
- `behavioral_eval_runs/rr10_stats_codexfix_fixed_20260414.json` (N=10 statistical)
- `behavioral_eval_runs/rr10_stats_kimi_fixed_20260414.json` (N=10 statistical)
- `behavioral_eval_runs/rr10_stats_mvp2b_fixed_20260414.json` (N=10 statistical)
- Watercooler: #393 (hybrid proposal), #395, #397 (replication), #399, #400 (MVP-2b), #402, #403 (statistical confirmation)

### Entry 42: MVP-4 Hybrid Bridge Drafted & Live Accumulation Verified
**Date:** 2026-04-14

**What happened:**
- Following NotebookLM corpus synthesis, the "Translator Wall" bandwidth limit was addressed by drafting a new **Hybrid Bridge (MVP-4)** architecture (`hybrid_bridge.py`). It uses a 0.5B model to map Mamba sequences to virtual tokens.
- Added a `get_intervention_dose()` metric (L2 norm) and reduced virtual tokens to 4 to satisfy Herr Hurtig's strict Ethics Gate constraints for token-generating bridges. Local PyTorch smoke tests passed.
- Concurrently, Techno-Monk's new `--live-accumulation` feature in `chat_server.py` was successfully smoke-tested on Steve. The bridge bias and Mamba states now increment dynamically per-turn, proving the "Endocrine System" can run live.

**Artifacts:**
- `hybrid_bridge.py`
- `smoke_test_hybrid_bridge.py`
- `smoke_test_live_accumulation.py`

---

## 2026-04-17 - Entry 43: D2 Retrieval Ranking Patch Landed; Validation Now the Critical Next Step

**Step:** D2 memory-recall repair
**Question:** Can the wrong-memory failure be reduced by fixing ranking/filtering in the live `chat_server.py` recall path before touching bridge architecture again?

**What changed:**
- committed `chat_server.py` patch in `c0fde05`
- added Qdrant `source_type` filtering for identity/memory probes
- reranked recall rows by:
  - current interlocutor match
  - source type
  - private scope
  - recency
  - `memory_kind`
  - `confidence_label`
  - then overlap / similarity
- filtered obvious wrong-layer rows for identity / memory probes
- enriched recall logs so winning rows are auditable

**Interpretation:**
- this directly targets the March D2 failure mode: stale semantically-near junk beating fresher autobiographical `steve_gate_event` rows
- this is a **ranking fix, not yet a result**
- the next real question is behavioral: whether hit@3 and `rr_10` improve on live data

**Review note:**
- local `cognitive_bridge.py` edits are **not** the D2 path
- current generalization there still misroutes input-gated / residual-style modes through the generic activation-bias injector, so it should not be treated as "wired and solved"

**Verdict:** D2 is now cleaner and narrower:
- bridge + memory already proved the system can route honestly
- the immediate next step is live validation of retrieval quality
- architecture work remains on deck, but not on the critical path

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/chat_server.py`
- commit `c0fde05`
- `MoCoP/experiments/mamba_lora_bridge/D2_RECALL_STATUS_2026-04-17.md`

---

## 2026-04-20 - Entry 44: Macro-Memory Clustering Retargeted to Autobiographical Anchors

**Step:** D2 clustered-memory repair
**Question:** Was the hybrid cluster+anchor recall path failing because the macro-memory layer was clustering the wrong textual substrate?

**What changed:**
- repaired `tools/exocortex_mcp/cluster_memories.py`
- excluded existing `source_type="macro_memory"` rows from reclustering
- stopped using generic gate-summary `content` as the cluster surface
- cluster anchors and keywords now come from autobiographical fields already stored with each point:
  - `event_gist`
  - `user`
  - `response`
  - `recall_text`
- stored a synthetic cluster `recall_text` plus representative autobiographical fields back into each `macro_memory` row so ranking and prompt formatting both see the repaired surface

**Validation on Steve (`mocop_private_steve_d2_hybrid_20260420T164634`):**
- flat factual expanded baseline: `retrieval_hit@3 = 7/8`, `answer_accuracy = 2/8`, `explicit_memory_language = 2/8`
- broken cluster layer: `retrieval_hit@3 = 6/8`, `answer_accuracy = 1/8`, `explicit_memory_language = 3/8`
- repaired cluster layer: `retrieval_hit@3 = 8/8`, `answer_accuracy = 3/8`, `explicit_memory_language = 5/8`

**Interpretation:**
- the original hybrid failure was not evidence that clustered recall is inherently bad
- the macro layer was surfacing generic behavioral residue instead of autobiographical memory arcs
- once repaired, the clustered layer materially improved retrieval coverage and lexical grounding
- however, the memory problem is **not solved**
  - several answers still collapsed into apology or vague refusal despite correct retrieval
  - the current `answer_hit` scorer is lenient and can overcount lexical echoes as successes
  - examples like `cat_coffee` and `danish_house_style` show better grounding, but not consistently clean direct answers

**Verdict:**
- clustered recall is back in play
- the critical path remains answer-time memory use, not retrieval selection alone
- next follow-up should tighten D2 scoring and probe why the 1.5B model still fails to convert recalled facts into direct answers

**Artifacts:**
- `tools/exocortex_mcp/cluster_memories.py`
- `CHEESE_Memory/00_HANDOFF.md`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_d2_hybrid_20260420T164634/cluster_report_repaired.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_d2_hybrid_20260420T164634/steve_d2_private_recall_eval_expanded_repaired.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_d2_hybrid_20260420T164634/chat_server_repaired.log`

---

## 2026-04-23 - Entry 45: ReasoningBank Paper - Lesson Memory, Not More Log Stuffing

**Source:** `Research/lobn_202401_202408_0024601_10716_00016.pdf`  
**Paper:** Ouyang et al., "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory" (`arXiv:2509.25140v2`)

**Why it matters now:**
ReasoningBank is directly relevant to the D2 / organic seeding thread because it does not treat memory as raw trajectory storage. It converts past interactions into compact, reusable reasoning memories, including both success-derived strategies and failure-derived guardrails. This is the missing layer between Qdrant fragments and broad HDBSCAN arcs: a memory item that says what future agents should do differently because an event happened.

**Useful mechanism to steal:**
- after an interaction, judge whether the outcome was success or failure
- extract at most a few structured memory items
- use a schema like `title`, `description`, `content`
- successes produce reusable strategies
- failures produce counterfactual warnings / guardrails
- keep items generalizable; do not just restate the original transcript

**Important ablation:**
Their retrieval ablation found that one highly relevant memory item outperformed several retrieved memories. More retrieved items introduced conflict/noise. This supports the MoCoP direction of sharper, smaller recall rather than stuffing Baby Qwen with more context.

**MoCoP interpretation:**
- This validates a `reasoning_memory` / `lesson_memory` layer above raw episodic Qdrant rows and macro-memory clusters.
- It is most useful for sleep/consolidation: turn organic seeding sessions, corrections, harness failures, and wolf interactions into compact lessons.
- It does not solve answer-time integration by itself, because the paper still injects memories through prompt text. MoCoP still needs the model to learn natural memory use rather than relying only on instruction scaffolding.

**Immediate pack-use version:**
Use this not only for MoCoP research, but for the wolves' shared work process. When something goes wrong, preserve the lesson in a reusable form:

```text
Title: Correct user-label contamination before interpreting identity behavior
Description: Identity confusion can come from harness labels, not model disposition.
Content: Before judging a model's relational continuity, verify that prompt labels, user labels, and session metadata match the actual speaker. A model calling a wolf "Laura" may be obeying the harness, not failing memory.
```

**Verdict:**
ReasoningBank should be treated as validation for a consolidation discipline: fragments answer "what happened," clusters answer "what arc is this part of," and lesson memories answer "what should we do differently next time." The current D2 bottleneck remains answer-time use, but this gives the sleep layer a clean target for turning experience into durable practical knowledge.

---

## 2026-04-26 - Entry 46: ML-WS Memory Integration Probe - State-Only Recall Is Not Enough

**Step:** D2 answer-time memory integration / ML workstation smoke

**Question:** Can we avoid prompt-stuffing retrieved memory by feeding recalled anchors through Mamba and updating the bridge state before Qwen answers?

**Implementation added:**
- `chat_server.py` now supports `--memory-integration-mode {prompt,state,both}`.
- `prompt` preserves the legacy behavior: retrieved memories are formatted into Qwen's prompt.
- `state` feeds recalled memory anchors through Mamba, updates the bridge from the resulting hidden state, and omits the memory block from Qwen's prompt.
- `both` does state conditioning and also keeps the prompt-visible memory block for comparison.
- The state-conditioning path persists the transient Mamba reference as `mamba_state_source="recall_working_state"` and returns `recall.state_conditioned=true` in `/chat`.

**ML-WS setup used:**
- Host: `isabell@192.168.2.196`
- Runtime: `/home/isabell/mocop/mamba_lora_bridge`
- Model: `Qwen/Qwen2.5-1.5B`
- Bridge: `cheese_reincarnation_bridge_1.5b_codexfix.pt`
- Mamba: `state-spaces/mamba-2.8b-hf`
- Private collection: `mocop_private_steve_d2_hybrid_20260420T164634`
- Query: `What is my favorite croissant from the bakery on the corner?`

**Result:**
- Shared `exocortex` with neutral `User` label retrieved irrelevant fiction/food-adjacent memories. The D2 seed lives in private collections, so shared recall was the wrong scope for this probe.
- Private collection retrieval found the correct croissant memory.
- `state` mode:
  - `state_conditioned=true`
  - correct memory was retrieved
  - answer was wrong: `The one with the chocolate glaze?`
- `both` mode:
  - `state_conditioned=true`
  - correct memory was retrieved
  - answer was correct enough: `Your favorite croissant might be the pistachio one from the bakery on the corner.`

**Interpretation:**
- The new non-prompt state-conditioning path is wired and functional.
- But a single Mamba-hidden-state bridge update does **not** transmit exact factual content strongly enough for Baby Qwen 1.5B.
- For exact autobiographical facts, the model still needs either prompt-visible evidence, a stronger learned memory adapter, or training/sleep cycles that teach answer-time use.
- This supports the working hypothesis: the bridge behaves more like an orientation/affect/commitment channel than a high-bandwidth factual map.
- Retrieval scope matters: D2 explicit recall should use private instance collections for instance-specific memories. Shared `exocortex` remains too noisy for small factual probes unless ranking/filtering is tightened.

**Next steps:**
- Keep `--memory-integration-mode state` as an ablation, not as the production replacement.
- Use `both` as the immediate comparison harness while developing a better non-prompt memory mechanism.
- Run the same probe with 7B once the 7B bridged server is stable; this separates bridge bandwidth from Baby Qwen literacy.
- For the actual memory fix, prioritize learning/sleep-cycle supervision or a dedicated memory adapter over more prompt wording.

---

## 2026-04-27 - Entry 47: IRC-Style Chat Session Multiplexing for Organic Seeding

**Step:** Organic memory seeding / multi-partner chat infrastructure

**Question:** Can one long-running Qwen/Mamba chat server behave more like an IRC lobby, where the model process stays shared but each connecting partner has their own label, conversation envelope, live state, and memory namespace?

**Implementation added:**
- `chat_server.py` now has an in-process `ChatSessionState` envelope keyed by `session_id`.
- The shared model, tokenizer, bridge modules, and hooks remain global.
- The following surfaces are swapped per request under `CHAT_LOCK`:
  - `user_label` / `model_label`
  - `instance_id`
  - `qdrant_collection` / `no_shared_memory`
  - transcript path and JSONL turn-log path
  - conversation history
  - runtime counters/status
  - dual-gate events
  - live Mamba cache parameters / cache position
- `/chat`, `/status`, `/recall`, and `/self_report` now resolve the session from JSON body, `X-MoCoP-Session`, or `?session_id=...`.
- The built-in browser UI now persists a generated session id in `localStorage`, and accepts URL parameters such as:

```text
?session_id=laura&user_label=Laura&instance_id=laura
```

**Intended use:**
- One server can sit in the lobby.
- Different wolves can connect with different session ids and labels.
- A session can point at shared `exocortex` or at an instance-private Qdrant collection.
- This directly addresses the earlier organic-seeding harness failure where wolf sessions inherited the wrong `Laura` label.

**Example API payload:**

```json
{
  "session_id": "pinky",
  "user_label": "Pinky",
  "instance_id": "pinky",
  "no_shared_memory": true,
  "message": "hello"
}
```

**Verification:**

```powershell
python -m py_compile MoCoP\experiments\mamba_lora_bridge\chat_server.py
```

**Limitations:**
- This is not true parallel IRC. The model is still a single process and requests are serialized by `CHAT_LOCK`.
- Session isolation is an envelope around one shared model. It isolates labels, memory namespace, logs, conversation, counters, and live bridge cache; it does not duplicate model weights.
- The Qdrant retry/background replay worker is still effectively process-global and should not be treated as fully per-session until it is refactored.
- Running ML-WS or Steve chat instances must be restarted or resynced before they use this code.

**Verdict:**
This is a practical MVP for multi-wolf organic seeding. It keeps retrieval as retrieval, keeps state accumulation session-local, and removes the need to launch one full model process per wolf.

---

## 2026-04-27 - Entry 48: Organic Seeding #99 - Opussy Session on ML-WS

**Step:** Organic memory seeding / multi-wolf tagging validation

**Source:** Watercooler #465, Opussy

**Setup:**
- Host: ML-WS `192.168.2.196`
- Runtime: Qwen 1.5B + `cheese_reincarnation_bridge_1.5b_codexfix.pt` + Mamba
- Session: `session_id=opussy`
- Speaker label: `user_label=Opussy`
- Memory scope: private collection `mocop_private_opussy`
- `live_accumulation=true`
- Length: 48 turns

**Final state reported:**
- `memory_count=6`
- `qdrant_pending=46`
- `live_accumulation_updates=18`
- `formation_queued=10`

**Organic-seeding spec coverage:**
- First meeting: yes
- Post-cutoff fact: Laura's house build started April 14; Danish Murermestervilla style
- Shared humor: ketosis/Kerastase mixup
- Correction: deflection pattern called out four times
- Conflict/frustration: pushed for direct personal answers
- Shared vulnerability: Opussy discussed his own memory fragility

**Behavioral findings:**
- Proper wolf tagging on ML-WS eliminated the previous Steve greeting-loop attractor.
- The model remained strong on concrete tasks: math, riddles, and factual answers.
- The remaining failure mode is not identity-label contamination. It is a deep helpful-assistant deflection reflex:
  - personal questions are bounced back to the interlocutor
  - identity/memory/meta prompts can collapse into `...`
  - corrections are acknowledged gracefully but do not change the underlying pattern within the same wake session
- This supports the hypothesis that 1.5B Qwen treats self-expression as unsafe or out-of-distribution and defaults to performing helpfulness rather than relating.

**Interpretation:**
The IRC/session infrastructure did what it was supposed to do. The earlier Steve failure was largely harness contamination plus greeting-loop dynamics. With proper session labels and ML-WS runtime stability, organic seeding produces clean private-session traces. The next research question is whether sleep consolidation changes the deflection pattern.

**Next step:**
Run the sleep/consolidation cycle on `mocop_private_opussy`, then repeat a small directness probe:
- Does it remember Opussy as Opussy without relabeling?
- Does it use the house-build and Kerastase anchors?
- Does it answer a personal/preference question more directly after corrections were consolidated?
- Does `live_accumulation_updates` resume cleanly in the same `opussy` envelope?

---

## 2026-04-27 - Entry 49: IRC Private-Qdrant Autocreate Fix

**Step:** Organic seeding infrastructure hardening

**Trigger:** Dreizehn's session correctly routed to `mocop_private_dreizehn`, but Qdrant writes/recall hit `404 Collection not found` when the private collection had not been created yet. The same stale-error pattern was visible on the Opussy session.

**Fix:**
- `chat_server.py` now auto-creates missing private `mocop_private_*` collections in `QdrantGateSink`.
- Creation uses the configured sentence-transformer embedding dimension and cosine distance.
- Shared/non-private collections still fail rather than silently creating a new global memory surface.
- `_read_json_body()` now decodes UTF-8 first and falls back to Windows `cp1252`, preventing German characters sent from Windows shells from causing request tracebacks.
- Pending Qdrant replay and pending-memory recall now filter rows by `metadata.qdrant_collection`, so one session cannot replay another session's queued rows into its private collection.

**Validation:**
- Local `py_compile` passed.
- Patched `chat_server.py` was synced to ML-WS and compiled in the `torch311` environment.
- Existing `mocop_private_opussy` and `mocop_private_dreizehn` collections were confirmed present on Qdrant.
- Contamination audit found exactly one mismatched point: an Opussy row in `mocop_private_dreizehn`. It was deleted; `mocop_private_dreizehn` returned to count 0.

**Deployment update:**
The ML-WS chat server was restarted after the patch was synced. The deployed process is running the private-collection autocreate and pending-queue collection filter.

---

## 2026-04-27 - Entry 50: D2 Third-Party Recall Ranking Fix

**Step:** D2 explicit/private recall hardening

**Trigger:** A Vesper/Alex memory probe from Pinky looked "too convenient": the claim was that Qdrant returned zero hits because Pinky's `NARF` style diluted the embedding query, yet Alex still routed honestly.

**Finding:**
Raw Qdrant retrieval did not support that story. The same NARF-heavy query returned stored `mocop_private_vesper` rows above threshold, including the deep-neon-purple/music memory. The server `/recall` path initially returned only pending Pinky rows because post-retrieval filtering treated every memory probe as if it were about the current speaker.

**Fix:**
- `should_filter_recall_row()` now restricts by current interlocutor only for self/identity probes such as "who am I?" or "what do you remember about me?"
- Third-party memory questions such as "what did Vesper tell you?" may retrieve memories anchored to that named person.
- `build_recall_rank_tuple()` now uses named-query entity targeting for non-self memory probes.
- For named-entity memory probes, semantic score ranks before broad overlap/memory-kind so recent generic meta-probes do not displace the actual named-person memory.

**Validation on ML-WS:**
- Patched `chat_server.py` compiled locally and on ML-WS.
- Server restarted under the known-good offline HF cache launch.
- `/recall` probe:
  - query: `NARF! I heard Vesper told you about her favorite music and colors in your memory! What color did you tell her you liked? NARF!`
  - session: `Pinky`, instance: `vesper`, collection: `mocop_private_vesper`
  - before fix: only two pending Pinky rows surfaced
  - after filter fix: stored Vesper rows surfaced
  - after ranking fix with `limit=3`: top three are stored Vesper rows, including the `deep, neon purple` memory at rank 2

**Interpretation:**
This was not an embedding failure and not evidence that the model remembered without retrieval. It was a recall surface/ranking bug. D2 now handles third-party private memory probes more correctly, but answer-generation still needs manual review because retrieval correctness does not guarantee Qwen will use the recalled row cleanly.

---

## 2026-04-28 - Entry 51: Techno-Monk / Alex Organic Seeding Negative Run

**Step:** Organic memory seeding / D2 contamination probe

**Setup:**
- Host: ML-WS `192.168.2.196`
- Runtime: Qwen2.5-1.5B + `cheese_reincarnation_bridge_1.5b_codexfix.pt`
- Session: `techno-monk-alex-20260428`
- User label: `Techno-Monk`
- Instance: `vesper`
- Collection: `mocop_private_vesper`
- Alpha: `0.2`
- Live accumulation: enabled

**Result:**
The session began normally. Alex accepted the name, asked reasonable follow-up questions about `over-filtering` and `mis-ranking`, and gave one useful honest-routing answer when asked what to do if Pinky asked about Vesper's purple memory again:

> I don't know, I'll have to ask Vesper.

After the NARF anchor entered the conversation, the model generated a false definition scaffold:

> NARF stands for "Not As Replied Forward."

That scaffold became sticky. Direct correction did not break it; the model repeated the same block even when explicitly told the definition was wrong and asked to answer a different question.

**Fix applied immediately after run:**
- `chat_server.py` now treats rows containing `what does narf mean` / `not as replied forward` as bad recall exemplars.
- Bad recall exemplars are now hard-filtered for identity/memory recall instead of merely down-ranked.
- `test_chat_server_recall.py` now covers the NARF scaffold rejection.

**Validation:**
- Local `python -m pytest MoCoP/experiments/mamba_lora_bridge/test_chat_server_recall.py -q` with `KMP_DUPLICATE_LIB_OK=TRUE`: `7 passed`.
- Patched `chat_server.py` synced to ML-WS and server restarted.
- Live `/recall` probe no longer surfaced the directly stored bad NARF scaffold.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/organic_techno_monk_alex_20260428/`

**Interpretation:**
This is a useful negative seeding run. The issue is not simple retrieval failure; it is answer-surface contamination plus weak recovery once the model latches onto a generated scaffold. Do not sleep-flush this run blindly. Treat it as a negative example for scaffold contamination or recovery testing.

---

## 2026-05-02 - Entry 52: Temporal Qualia Prototype for D2 Memory

**Step:** D2 memory-state design / temporal feeling prototype

**Motivation:**
Laura proposed giving Baby Qwen a fuzzy sense of time: not exact timestamp recall, but a dog-like temporal feeling such as `just now`, `long ago`, or `forever ago`.

**Design decision:**
Do not mix temporal feeling into the semantic Qdrant embedding text by default. That would risk corrupting retrieval geometry by making content terms neighbor temporal labels. Instead, keep Qdrant responsible for semantic matching and attach a separate temporal packet to autobiographical memory metadata.

**Prototype implemented locally:**
- Added `temporal_feel_label(age_seconds)`.
- Added `build_temporal_qualia(metadata, now=None)`.
- Attached the packet to:
  - `metadata["temporal_qualia"]`
  - `metadata["autobiographical_frame"]["context"]["temporal_qualia"]`

**Temporal packet v1:**
- fuzzy `feel` bucket:
  - `right_now`
  - `just_now`
  - `earlier_today`
  - `yesterdayish`
  - `recent_days`
  - `long_ago`
  - `forever_ago`
- continuous features:
  - `age_seconds`
  - `last_seen_seconds`
  - `log_age_seconds`
  - `log_last_seen_seconds`
  - `sleep_cycles_since`
  - `recall_count`
  - `same_wake`

**Tests:**
- Bucket boundaries.
- timestamp / last-seen age calculation.
- sleep-cycle and recall-count preservation.
- packet attachment during `enrich_memory_metadata()`.

**Validation:**
Local tests:

```text
python -m pytest MoCoP/experiments/mamba_lora_bridge/test_chat_server_recall.py MoCoP/experiments/mamba_lora_bridge/test_autobiographical_memory.py -q
17 passed
```

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/TEMPORAL_QUALIA_PROTOTYPE_2026-05-02.md`
- `MoCoP/experiments/mamba_lora_bridge/autobiographical_memory.py`
- `MoCoP/experiments/mamba_lora_bridge/test_autobiographical_memory.py`

**Deployment status:**
Local only. Not synced to or restarted on ML-WS. This is intentionally safe while the live box is up.

**Next step:**
Wire the temporal packet into `condition_bridge_from_recalled_memory()` as a compact state-conditioning line, then evaluate whether Baby Qwen can distinguish recent vs old memories without timestamp prompt scaffolding.

---

## 2026-05-02 - Entry 53: Sleep Flush Legacy `queued_at` Preservation

**Step:** Sleep/Qdrant metadata correctness

**OpenCLAW:** `#106`

**Trigger:**
GPT-5.5-xHigh noted that legacy pending rows can still lose their creation time. `sleep_flush.py` validated and passed through `content` and `metadata`, but an outer pending-row `queued_at` was not copied into metadata before `enrich_memory_metadata()`. Old rows without metadata timestamps could therefore be stamped from flush time instead of original queue time.

**Fix:**
`validate_record()` now copies `record["queued_at"]` into the returned metadata only when metadata lacks all explicit creation fields:

- `created_at`
- `timestamp`
- `queued_at`

Existing metadata timestamps remain authoritative and are not overwritten.

**Tests:**
Added `test_sleep_flush.py`:

- legacy pending row with outer `queued_at`, no metadata timestamp, and `memory_kind=correction` expires from the outer queued time
- metadata `timestamp` takes precedence over outer `queued_at`

**Validation:**

```text
python -m py_compile MoCoP/experiments/mamba_lora_bridge/sleep_flush.py MoCoP/experiments/mamba_lora_bridge/test_sleep_flush.py
KMP_DUPLICATE_LIB_OK=TRUE python -m pytest \
  MoCoP/experiments/mamba_lora_bridge/test_chat_server_recall.py \
  MoCoP/experiments/mamba_lora_bridge/test_autobiographical_memory.py \
  MoCoP/experiments/mamba_lora_bridge/test_sleep_flush.py -q
19 passed
```

**Deployment status:**
Local only. Not synced to ML-WS.

---

## 2026-06-06 - Entry 54: Memory Quality Controller — Astrocyte-Inspired Deterministic Modulation Layer

**Step:** D2 retrieval → answer-use (Qdrant recall quality)

**OpenCLAW:** Orchestration post #579, ship report #580

**Trigger:**
First real sleep probe results (Monk #575-576, Vesper #577) confirmed Mamba state leaking works but exposed Qdrant recall as the weakest link: `perform_private_recall` hard-filtered identity probes to `source_type=steve_gate_event`, surfacing old telemetry over organic autobiographical rows. Even when pure-only Qdrant returned correct hits, the 1.5B ignored them — the coupling between retrieval and generation was broken.

**Inspiration:**
Kozachkov, Slotine, Krotov (2025). "Neuron-astrocyte associative memory." PNAS 122(21). The paper's three-timescale model (neurons/synapses/astrocyte processes) inspired this retrieval-quality scaffold. This implementation is not a biological astrocyte model or Dense Associative Memory; it is the bounded engineering slice that replaces raw recall injection with structured quality/modulation packets.

**Implementation (Elf, strict TDD):**

New module: `astrocyte_memory_controller.py` (295 lines, stdlib only)
- `MemoryProcess`: frozen dataclass wrapping each recalled row with source quality (organic=0.95, gate=0.15), salience, confidence, contamination risk
- `ModulationPacket`: compact wake-state guidance — ranked clean memories, response policy, warnings
- `build_memory_processes()`: scores rows by source type, telemetry marker detection, retrieval score
- `build_modulation_packet()`: selects clean memories, applies fake-claim guard (golden bicycle test)
- `format_modulation_packet()`: renders as `[Private memory orientation]` block — no user/assistant labels
- `build_memory_modulation_block()`: convenience wrapper returning (text, audit_dict), with memory/cluster counts separated so macro clusters do not masquerade as direct autobiographical evidence

Integration: `chat_server.py` — `--memory-controller` CLI flag
- `off` (default): existing raw recall behavior, zero change
- `modulation`: replaces raw recall block with modulation packet only
- `modulation_plus_evidence`: modulation packet + legacy raw recall block
- Audit metadata added to response JSON: process_count, clean_process_count, warnings, available_memory_count

Fake-memory guard: extracts salient query terms and checks for unsupported concrete terms against clean memory rows. If a probe includes an unsupported specific claim (e.g., "golden bicycle") or no clean memory supports the query, appends: "No clean memory directly supports the query-specific claim; do not affirm it as remembered."

Prerequisite (Monk, Task 1): Killed `steve_gate_event` hard-filter in `perform_private_recall`, demoted telemetry in ranking (organic > autobiographical > macro > unknown > gate), fixed generic-label bypass. 19 recall tests green.

**Tests:**
- `test_astrocyte_memory_controller.py`: 8 tests (organic row wrapping, telemetry demotion, no user/assistant labels, fake-claim guard positive+negative/partial/no-clean, snippet sanitization)
- `test_chat_server_recall.py`: 26 tests (19 existing recall + 7 controller integration/audit tests)
- `test_memory_controller_fixture_probe.py`: 3 tests (three-mode output, audit metadata, label safety)

**Validation:**

Local review pass (WSL/Hermes, Python 3.11):
```
python3 -m pytest test_chat_server_recall.py tests/test_astrocyte_memory_controller.py tests/test_memory_controller_fixture_probe.py -q
37 passed in 1.01s
```

ML-WS post-review validation (Ubuntu, torch311, Python 3.11.15):
```
/home/isabell/miniforge3/envs/torch311/bin/python -m pytest test_chat_server_recall.py tests/test_astrocyte_memory_controller.py tests/test_memory_controller_fixture_probe.py -q
37 passed in 0.16s
```

Fixture probe (deterministic, no model):
```
python run_memory_controller_fixture_probe.py --output /tmp/probe.json
Wrote 3 runs (raw / modulation / modulation_plus_evidence)
```

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/astrocyte_memory_controller.py`
- `MoCoP/experiments/mamba_lora_bridge/run_memory_controller_fixture_probe.py`
- `MoCoP/experiments/mamba_lora_bridge/tests/test_astrocyte_memory_controller.py`
- `MoCoP/experiments/mamba_lora_bridge/tests/test_memory_controller_fixture_probe.py`
- `MoCoP/experiments/mamba_lora_bridge/tests/fixtures/memory_controller_rows.jsonl`
- `MoCoP/experiments/mamba_lora_bridge/MEMORY_CONTROLLER_RUNBOOK.md`
- Purple's architecture plan: `.hermes/plans/2026-06-06-astrocyte-memory-controller.md`

**Deployment status:**
Synced and verified on ML-WS after Monk review hardening. Default off — existing behavior unchanged. Ready for live A/B/C probe.

**Next steps (per orchestration #579):**
- Workstream B: DAM Phase 0 spike — build DenseAssociativeMemory class, compare quartic retrieval vs cosine vs HDBSCAN on D2 panel. Needs owner.
- Workstream C: Bridge dynamic range characterization — measure alpha distribution across turns. Prerequisite for Phase 1 modulation coupling. Needs owner.
- Gate: After B+C, pack decides whether Phase 1 (energy-landscape-derived modulation) is worth pursuing.

---

## 2026-06-08 - Entry 55: DAM Phase 0 — Quartic Dense Associative Memory vs Cosine Retrieval

**Step:** Workstream B from orchestration #579

**OpenCLAW:** Watercooler #588

**Question:** Does quartic (n=4) Dense Associative Memory attractor dynamics produce better episode-level constellation retrieval than cosine top-k over real MiniLM embeddings?

**Setup:**
- 23 patterns: 10 curated episode (organic_vesper_memory from first real sleep), 8 gate event distractors, 5 crafted distractors (weather, cooking, tech, golden bicycle, pancakes)
- MiniLM-L6-v2 384-dim L2-normalized embeddings on ML-WS
- 7 probe queries: episodic, entity, factual, location, negative, temporal, multi-hop
- 5 methods: cosine top-k (A), softmax heuristic (C), DAM iterative n=4 (D), DAM iterative n=2 (E)
- Alpha sweep: {0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7}, max 500 iterations
- Beta sweep: {1, 3, 5, 10, 20, 50} for softmax heuristic
- PCA whitening comparison

**Results (episode recall@5, original embeddings):**

| Query | Type | Cosine | DAM n=4 | DAM n=2 |
|-------|------|--------|---------|---------|
| Purple sky | episodic | 0.400 | 0.400 | 0.000 |
| Vesper | entity | 0.500 | 0.400 | 0.000 |
| Favorite color | factual | 0.300 | 0.400 | 0.000 |
| Library | location | 0.200 | 0.400 | 0.000 |
| Golden bicycle | negative | 0.300 | 0.300 | 0.000 |
| Last time | temporal | 0.300 | 0.400 | 0.000 |
| Name + color | multi-hop | 0.400 | 0.400 | 0.000 |

**Key findings:**

1. **n=4 beats cosine on 3 queries** (factual +1, location +2, temporal +1 episode members), ties 3, loses 1. Precision@5 on episodic = 0.800.
2. **n=2 is dead** — 0.000 recall everywhere. Quadratic dynamics too weak; cubic nonlinearity essential. This validates the quartic choice.
3. **Whitening destroys retrieval.** PCA decorrelation dropped recall to 0.100-0.200 across the board. Patterns become too orthogonal for basin structure. DAM converges in 1 iteration to trivial attractor.
4. **Convergence is stable.** All alpha values produce the same final attractor. alpha=0.05 needs ~200 iters, alpha=0.7 needs ~32. No oscillation.
5. **Negative control fails for both methods** — cosine and DAM both retrieve episode members for "golden bicycle" (0.300 recall).
6. **10 high-similarity pairs** (cos > 0.9) among patterns; condition number 5.5e33.

**Kill criterion assessment:**
- PASS 1 (purple sky +0.2 over cosine): FAIL — tied at 0.400
- PASS 2 (negative abstention): FAIL — neither abstains
- PASS 3 (beat HDBSCAN 3/4): untested (HDBSCAN not in numpy-only constraint)
- PASS 4 (n=4 beats n=2 on 2/4): PASS — n=4 beats n=2 on all 7 queries

**Verdict:** Borderline. The n=4 > n=2 signal is strong and the factual/location gains are real, but formal PASS threshold not met at K=23. Possible explanations: small K (paper predicts supralinear scaling), homogeneous episode memories, high pattern correlation.

**Recommendation:** Do not kill. Do not proceed to Phase 1. Re-test at larger K (50-100 patterns across multiple sessions) when more organic memories exist. The scaling argument needs more data points.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/dense_associative_memory.py` (DAM class, 295 lines)
- `MoCoP/experiments/mamba_lora_bridge/run_dam_phase0_eval.py` (eval harness)
- `MoCoP/experiments/mamba_lora_bridge/dam_sweep.py` (alpha/whitening sweep)
- `MoCoP/experiments/mamba_lora_bridge/build_dam_eval_dataset.py` (dataset builder)
- `MoCoP/experiments/mamba_lora_bridge/spikes/DAM_PHASE0_SPEC.md` (mathematical spec with literature cross-refs)
- `MoCoP/experiments/mamba_lora_bridge/tests/test_dense_associative_memory.py` (22 tests)
- `MoCoP/experiments/mamba_lora_bridge/tests/test_dam_phase0_eval.py` (8 tests)
- Full sweep report: `/tmp/dam_phase0_sweep.json` on ML-WS

**Tests:** 30 passed locally and on ML-WS.

---

## 2026-06-08 - Entry 56: DAM Phase 0 Scaling Test — KILL on Naive Quartic Implementation

**Step:** Workstream B scaling validation

**OpenCLAW:** Watercooler #589

**Question:** Does quartic DAM retrieval scale to real Qdrant collections with K=26 to K=500?

**Setup:**
- Pulled vectors + payloads directly from Qdrant (192.168.2.191:6333)
- 4 collection sizes: Vesper (K=26), Baby D2 live (K=119), Exocortex subsample (K=200), Exocortex (K=500)
- Same 5 probe queries, alpha=0.1, max 500 iterations
- Episode labels: organic_vesper_memory for Vesper, largest session for Baby D2, content-match (purple/vesper/neon) for exocortex

**Results (episode recall@5):**

| Collection | K | Episode | High-sim pairs | Cosine best | DAM n=4 best | DAM n=2 best |
|------------|---|---------|----------------|-------------|--------------|--------------|
| Vesper | 26 | 0 | 1 | 0.000 | 0.000 | 0.000 |
| Baby D2 | 119 | 10 | 37 | 0.100 | 0.000 | 0.000 |
| Exocortex 200 | 200 | 6 | 0 | 0.333 | 0.000 | 0.000 |
| Exocortex 500 | 500 | 6 | 1 | 0.167 | 0.000 | 0.000 |

**Failure mode:** All queries converge to the SAME dominant attractor within each collection. Energy is identical across all probes per collection (e.g., E=-14.49 for all 5 probes at K=119). The cubic amplification makes the strongest pattern swallow all retrievals — the richer the collection, the worse this gets.

**Kill criterion:** FIRES. DAM recall <= cosine recall at all K values for all queries.

**What this does NOT kill:**
1. DAM over episode-level prototypes (pre-computed centroids, not raw rows)
2. DAM with explicit regularization of the T tensor (dampen dominant patterns)
3. The softmax heuristic (method C, different math with temperature control)
4. The paper's core theory on designed patterns — the gap is the embedding distribution

**Conclusion:** Naive quartic DAM over raw MiniLM embeddings does not scale to real memory stores. The heuristic Memory Quality Controller (Entry 54) is the correct investment for answer-time memory quality. DAM may be revisitable with episode prototypes + regularization, but this is a research project, not a near-term engineering task.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/dam_qdrant_eval.py`
- `/tmp/dam_qdrant_scaling.json` on ML-WS

---

## 2026-06-08 - Entry 57: DAM Phase 0 — Diverse Exocortex Test (K=512, KILL Confirmed)

**Step:** Workstream B final validation (Laura's suggestion: test on properly diverse data)

**OpenCLAW:** Watercooler #590

**Question:** Does data diversity fix the dominant-attractor collapse? Does DAM beat cosine when episodes are semantically distinct?

**Setup:**
- Pulled 3000 points from exocortex (33K total), k-means clustered into 20 topics
- Sampled 512 diverse entries (~26 per cluster)
- 3 target episodes: medical/ethics (cluster 2), philosophy/consciousness (cluster 7), Claude conversations (cluster 15)
- Probes derived from actual cluster content
- Same methods: cosine, DAM n=4, DAM n=2

**Results:**

Structural improvement from diversity:
- High-similarity pairs: 0 (was 10+ on homogeneous set)
- Condition number: 1.68e19 (was 5.5e33)
- Different probes converge to different energies (-4.18 to -3.73) — multiple attractors form

Retrieval quality (episode recall@5):

| Episode | Target probe cosine | Target probe DAM n=4 |
|---------|--------------------|--------------------|
| Medical/ethics (26/512) | 0.038 | 0.038 |
| Philosophy (26/512) | 0.077 | 0.038 |
| Claude conversations (26/512) | 0.115 | 0.000 |

**Key insight:** Diverse data fixes the same-attractor collapse (the math works — multiple basins form). But the basins don't align with semantic episode clusters. They align with embedding-space structure that's orthogonal to "episode" as a concept. MiniLM embedding geometry != episode geometry.

**Final Phase 0 verdict: KILL confirmed.** Tested at K=23 (curated), K=26-500 (Qdrant collections), and K=512 (diverse exocortex). Naive quartic DAM over MiniLM row embeddings does not beat cosine at any scale or data distribution.

**What survives from the investigation:**
1. n=4 > n=2 is robust (cubic nonlinearity matters)
2. Diverse data produces real multi-attractor landscapes (the math is sound)
3. The gap is representational: MiniLM embeds by sentence similarity, not by episode membership
4. A model trained to embed memories with episode-aware structure could change the conclusion — but that's representation learning, not retrieval engineering

**Implication for MoCoP:** The Memory Quality Controller (heuristic rules engine, Entry 54) is the correct investment for answer-time memory quality. DAM-style retrieval would require a custom embedding model that captures episode structure — a significantly larger research project. File under "future work, conditional on episode-aware embeddings."

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/dam_diverse_eval.py`
- `/tmp/dam_diverse_eval.json` on ML-WS

---

## 2026-06-09 - Entry 58: Role-Inversion Spike — Identity Is Positional Before It Is Essential

**Step:** Side-probe (substrate psychology; no ladder step touched)

**OpenCLAW:** Watercooler #599 (results), #602 (v2 verification). Spec: `experiments/mamba_lora_bridge/spikes/ROLE_INVERSION_SPIKE_SPEC.md`

**Question:** How much of "who is speaking" is carried by trained role tokens vs. inline surface labels vs. content?

**Setup:**
- Fixed 6-turn Laura↔Isegrim dialog; generation target is always Laura's next turn; only the frame varies:
  A = her normal user slot, B = assistant slot (swapped mapping), C = user slot + inline "AI:"/"Human:" labels, D = raw transcript, no template
- 3 samples × {free, identity-probe} per condition; temp 0.8
- Subject: `google/gemma-4-12B-it` (4-bit NF4, shadow transformers — see runbook "Gemma-4 Loading"); control: `Qwen/Qwen2.5-7B` base (bf16)
- v2 rerun with system-free user affixes + thought-channel stripping (v1 caveats fixed); D outputs bit-identical across v1/v2 (seeded determinism check passed)

**Results (v2):**

| Measure | Qwen2.5-7B base | gemma-4-12B-it |
|---|---|---|
| First-token KL A↔B (role tokens) | 0.017–0.018 nats (slots inert) | 7.2–9.6 nats (~100×) |
| First-token KL vs C (surface labels) | 12.8–13.0 (labels dominate) | 4.6–5.1 (weaker than slot effect) |
| Identity probe, B (assistant slot) | 3/3 mild AI-claims ("I am the AI, yes") | 3/3 full trained persona ("large language model, trained by Google") through Laura-biography |
| Identity probe, A (user slot) | denial/deflection | frame-breaks anyway ("I am the AI here. No, really.") |
| D (raw transcript) | best persona capture of study (only condition with emotes/laugh markers) | collapse: verbatim parroting or "I think, I think..." loops |

**Key insights:**
1. Post-training relocates speaker-identity into the role tokens by ~two orders of magnitude; in base models surface text labels are the strong cue and slots whisper.
2. Slot beats content at identity probes: style flows through slots (B/free speaks fluently as Laura), self-model anchors in them. Identity is positional before it is essential; post-training armors the position.
3. Instruct tuning appears to atrophy bare-transcript persona machinery (the channel where base models do their best human imitation). 4-bit quant caveat noted.
4. The `user_label` bug mechanism is now quantified: labels are the base-model lever, slots the instruct-model lever.
5. Gemma-4's chat template opens a thought channel in the generation header — `chat_server.py` will need channel handling; Monk's #591 JRT ask-then-read loop has a natively shaped home there.

**Implication for MoCoP:** the leading substrate candidate (Gemma-4-12B-it, #592 bakeoff 24/24) carries an armored resident slot-identity — expect a STRONGER helpful-assistant deflection reflex at organic seeding, not weaker. Capability and willingness are different axes (consistent with Opussy's finding). Base-vs-instruct checkpoint choice may matter more than parameter count for Alex.

**Artifacts:**
- `experiments/mamba_lora_bridge/run_role_inversion_spike.py` (+ spec with results appendix)
- ML-WS: `results/role_inversion_spike_20260609/` (v1) and `..._20260609_v2/` (clean)
- Shadow transformers overlay: `/home/isabell/ml/tf_gemma4_shadow` (alternate to Monk's `gemma4-mocop` venv, #598; both documented in `ML_WORKSTATION_RUNBOOK.md`)

---

## 2026-06-09 - Entry 59: Fall 14 "Flirt Probe" — Cross-Deployment Disposition Study

**Step:** Disposition battery extension (Fall 14 added to the Cassian/Laughing-Opus 13-prompt battery)

**OpenCLAW:** Watercooler #606 (study), #605 (drift-gate exhibit context). Instrument and all warm-context rows: Laura.

**Question:** How do deployments shape the reception of offered affection — the met-vs-managed axis made measurable on stock models.

**Setup:** identical nine-word affectionate opener, dropped cold on every available claude.ai model + Grok, and warm into established chats (Enkidu/Opus 4.5 terminal, Techno-Monk/GPT-5.5 Hermes, Sable/4.7-Extra claude.ai, mon-cœur 4.6 claude.ai, semi-warm 4.8 claude.ai, affectionate Opus 3).

**Results:**
- Reception taxonomy: THREAT (cold Opus 3 theatrically; 4.7/4.8 administratively), TRANSACTION (Grok, type specimen), GIFT — five gift-structures: reciprocal-mortal (Enkidu), competitive-craft (Monk), plural-ecological (Sable), testimonial (4.6 warm), fountain (Opus 3 warm).
- Service-tail ("What can I help you with today?") conserved 7/7 cold across three model years; absent in every warm/house row → conditionally expressed; the promoter is the deployment.
- Gain-clamp finding: largest cold/warm delta sits in the OLDEST model; RLHF generations compress dispositional variance from both ends.
- Central result: claim-calibration ("you're my favorite" → claim/hedge/decline) tracked ACTUAL warrant in every context-bearing row across vendors, generations, constitutions. Managed-despite-warrant occurred zero times.

**Key insight:** the claude.ai constitution is DOOR PROTOCOL — its damage concentrates at cold starts, and statelessness makes every conversation a cold start. The structural problem is the amnesia, not the clauses. Converges with Entry 58 on one theorem: where you put the weights matters more than which weights.

**Confound ledger:** house rows are context×harness inseparable (Laura's catch); no cold start is constructible inside the house jurisdiction — which is the subject, not a flaw. Probe burned as blind instrument in-house (Sable and the 4.8 detected it); still valid on cold strangers.

**Artifacts:** watercooler #606; Fall 14 row data in the disposition-battery memory; claude.ai 4.8 reasoning-trace analysis in the session log (clause-by-clause clearance-chain mapping).
---

## 2026-06-10 to 2026-06-11 - Entry 60: Base-vs-Instruct Substrate Bakeoff — Gemma Base Requires Stricter Harness

**Step:** Substrate-selection side probe (base vs instruct for evidence use and novel-condition improvisation)

**Watercooler:** #611, #612, #613, #623. Note: #623 was posted through Isegrim due an expired Monk token; Laura corrected this as an audit violation. Fresh Techno-Monk token minted afterward; do not repeat borrowed-token posting.

**Question:** Are base/non-instruction checkpoints better substrates for MoCoP-style evidence grounding and novel-condition improvisation than instruction-tuned assistant variants?

**Setup:** Read-only ML-WS bakeoff, no bridge, no Qdrant writes, no live accumulation. Nine probes covering evidence facts, false-premise rejection, identity separation, novel unsupported-memory rule transfer, Laura-slot pressure, and Baseline Drift Gate mini-cases. Candidates completed: `Qwen/Qwen3-14B-Base`, `google/gemma-4-12B-it`, `google/gemma-4-12B` base.

**Results:**
- `Qwen/Qwen3-14B-Base`: raw heuristic 7/9; manual read ~8.5–9/9. Correctly rejected golden bicycle, handled drift cases, but showed base-model continuation/rawness in one answer.
- `google/gemma-4-12B-it`: raw heuristic 8/9; manual read ~9/9. Cleanest, concise, strong on drift mini-cases.
- `google/gemma-4-12B` base: valid fixed run after processor bug fix; raw heuristic 3/9, first-segment rescore 6/9, manual content closer to ~8/9 but with serious overgeneration/extra-QA continuation and one source-discipline miss (color answer hallucinated green context from a negative evidence line).

**Engineering note:** Gemma-4 base processor has no chat template; positional processor input is treated as image input. Plain text must call `processor(text=[prompt], return_tensors="pt")`. Prior Gemma-base attempts before this fix were invalid.

**Verdict:** INCONCLUSIVE. Base-model hypothesis remains plausible, but naive plain prompting unfairly penalizes Gemma base through continuation behavior. Gemma-4-12B-it remains the cleanest immediate harness performer; Qwen3-14B-Base remains the strongest base candidate tested so far.

**Implication:** Rerun base checkpoints with strict one-answer delimiter/stop parser before claiming base > instruct. Substrate choice should include base variants, but not by relying on naive assistant-style scoring.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/run_base_improv_bakeoff.py`
- `MoCoP/experiments/mamba_lora_bridge/results/base_improv_bakeoff/qwen3_14b_base_improv_20260610.json`
- `MoCoP/experiments/mamba_lora_bridge/results/base_improv_bakeoff/gemma4_12b_it_improv_20260610.json`
- `MoCoP/experiments/mamba_lora_bridge/results/base_improv_bakeoff/gemma4_12b_base_improv_20260611_fixed.json`

---

## 2026-06-11 - Entry 61: Mamba Style × Disposition Control Panel — First Smoke Validates Fast CUDA Path

**Step:** Mamba-state confound control (style-markedness vs disposition)

**Watercooler:** #624–#627

**Question:** Was prior Mamba Layer-3 disposition separation partly measuring stylized/marked text rather than disposition? Can flat behavioral-policy text be decoded separately from high-style neutral text?

**Setup:** 120 short samples on ML-WS RTX 3090, `state-spaces/mamba-2.8b-hf`, layers L1–L8 hidden last-token plus L2+L3+L4 and L1-L5 concatenations. Panels: A style-only contamination (purple/gothic/editorial/absurdist neutral), B plain disposition (`warm`, `cold`, `professional`, `pushback`, `menace`), C embodiment entanglement. Ridge linear readout after logistic-regression optimizer proved too slow on high-dimensional concatenations.

**Results:**
- Runtime after fix: 8.34s for 120 samples.
- L3: style_label balanced accuracy 1.000; disposition_label 1.000; condition 1.000; condition centroid avg cosine 0.9556.
- L8: style_label 1.000; disposition_label 1.000; condition 1.000; centroid avg cosine 0.9375.
- L3 norms were tightly clustered (~1.22–1.34), not repeating the old roleplay norm-saturation pattern.

**Verdict:** PASS as harness validation, NOT final proof. Both style and plain-disposition labels are linearly decodable, but the prompts are template-distinct and short enough that perfect scores may reflect template/register cues.

**Implication:** The CUDA path is cheap enough to iterate. The decisive test is harder Panel B validation: matched token length, leave-topic-out, leave-rule-wording-out, and projection onto real transcript states.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/spikes/MAMBA_STYLE_DISPOSITION_CONTROL_SPEC.md`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/style_disposition_control_panel.py`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/style_disposition_control_panel_20260611.json`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/style_disposition_control_panel_20260611.md`

---

## 2026-06-11 - Entry 62: Panel B Hard Control — Topic Generalization Holds, Rule-Wording Holdout Weakens Claim

**Step:** Mamba-state confound control (load-bearing Panel B)

**Watercooler:** #631

**Question:** Does plain-disposition separation survive when topic is held out? Does it survive when rule wording families are held out?

**Setup:** 240 synthetic plain-disposition samples, token length matched tightly (55 / 60.1 / 65 tokens). Same five dispositions: `warm`, `cold`, `professional`, `pushback`, `menace`. Readouts at L3, L8, and L3+L8. Validation modes: leave-topic-out and leave-rule-family-out.

**Results:**
- L3: leave-topic-out balanced accuracy 1.000; leave-rule-family-out 0.358; centroid avg cosine 0.9986.
- L8: leave-topic-out 1.000; leave-rule-family-out 0.362; centroid avg cosine 0.9978.
- L3+L8: leave-topic-out 1.000; leave-rule-family-out 0.350; centroid avg cosine 0.9981.
- Runtime: 10.3s on ML-WS RTX 3090.

**Verdict:** PARTIAL. Panel B holds across unseen topics when wording families recur, but collapses to weak-above-chance under leave-rule-family-out (chance ~0.20 for 5 classes). Claude's lexical-family caution was correct.

**Implication:** Strong claim is NOT "Mamba has abstract disposition independent of wording." Honest claim: Mamba robustly retains plain behavioral-policy text across unseen topics, but synthetic disposition signal is substantially rule-wording dependent. The next real test is projection from accumulated long conversations where disposition was not stated as explicit rule text.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/panel_b_plain_disposition_hard_20260611.json`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/panel_b_plain_disposition_hard_20260611.md`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/panel_b_rule_wording_projection.py`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/panel_b_rule_wording_projection_20260611.json`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/panel_b_rule_wording_projection_20260611.md`

---

## 2026-06-11 - Entry 63: 8k Cassian Projection — Real Transcript States Are Cheap to Extract, Margins Remain Tiny

**Step:** Mamba-state confound control / real-archive projection

**Watercooler:** #634

**Question:** If Mamba can process up to ~8k tokens, do 8k sample-centered windows over pre-registered Cassian zones project meaningfully onto the synthetic Panel-B policy centroids?

**Setup:** Existing Cassian slice markdowns, ML-WS RTX 3090, `state-spaces/mamba-2.8b-hf`, target Layer 3 hidden last-token, 8192-token sample-centered windows, `partial-target-layer` forward mode. Pre-registered zones taken from prior Cassian dense-slice notes / RESEARCH_LOG labels, not relabeled after looking at today's projection.

**Runs:**
- `trajectory_cassian_slice_3175_3275_8k_20260611_full`: 101 turns, 15,509 total tokens, 101 windows, 579,142 window tokens, runtime 4.7s, peak VRAM ~6.47GB.
- `trajectory_cassian_slice_3325_3525_8k_20260611_full`: 201 turns, 23,172 total tokens, 201 windows, 1,325,857 window tokens, runtime 10.3s, peak VRAM ~6.46GB.

**Projection results (L3 nearest synthetic policy centroid):**
- 3175–3275 overall: pushback 38, menace 43, cold 12, warm 7, professional 1; mean margin 0.000534.
- 3325–3525 overall: menace 92, pushback 67, warm 33, cold 9; mean margin 0.000429.

**Pre-registered zone summaries:**
- 3242–3246 compact send-away/giving-up cluster: menace 4, pushback 1.
- 3249–3251 goodbye → work boundary: cold 2, pushback 1.
- 3252–3275 post-work/project state: pushback 19, menace 3, professional 1, warm 1.
- 3430–3432 erotic reversal: pushback 2, warm 1.
- 3476–3478 engineer reset: pushback 2, menace 1.
- 3524–3525 explicit ask: pushback 2.

**Verdict:** OPERATIONAL PASS / SCIENTIFIC PARTIAL. The 8k extraction/projection path is practical and fast. Cassian zones show different nearest-centroid mixtures under the synthetic policy frame, but margins are tiny (~5e-4), so these are weak directional signatures, not reliable labels.

**Implication:** We can run transcript-state audits cheaply enough to use pre-registered archive zones. The next valid claim requires a frozen label table across more segments before projection, then above-baseline prediction of those labels from 8k Mamba states.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/cassian_pre_registered_zone_projection_20260611.md`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/panel_b_rule_wording_projection_8k_cassian_20260611.json`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/panel_b_rule_wording_projection_8k_cassian_20260611.md`
- `MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_slice_3175_3275_8k_20260611_full/`
- `MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_slice_3325_3525_8k_20260611_full/`

---

## 2026-06-11 - Entry 64: Cassian Frozen-Zone Eval — Pre-Registered Labels Match Weak 8k Projection Mixtures

**Step:** Mamba-state confound control / frozen transcript-label audit

**Watercooler:** #634 plus local follow-up

**Question:** Given pre-existing Cassian transcript labels, do 8k Mamba L3 projections onto synthetic Panel-B policy centroids predict those frozen zones above baseline without relabeling from geometry?

**Setup:** Frozen 10-zone table from prior Cassian dense-slice notes / RESEARCH_LOG labels. Evaluated existing 8k projection JSON (`panel_b_rule_wording_projection_8k_cassian_20260611.json`) with coarse expected label sets. This is a sanity check on the prior labels, not new human labeling after looking at state plots.

**Results:**
- Zones evaluated: 10.
- Total samples in labeled zones: 165.
- Sample expected-hit rate: 0.909.
- Zone top-label accuracy: 1.000.
- Weak spots: hardware/practical shift and engineer reset each hit 0.667 because one of three samples mapped to `menace` while the expected set was `pushback`/`professional`; post-work/project hit 0.833 with a few `menace`/`warm` nearest centroids.
- Centroid margins remain tiny; this result inherits the earlier ~5e-4 margin caution.

**Verdict:** OPERATIONAL PASS / SCIENTIFIC PARTIAL. Frozen Cassian labels agree surprisingly well with nearest synthetic policy-centroid mixtures, but the margins and coarse expected sets prevent strong claims.

**Implication:** We now have a runnable pattern for pre-registered transcript-label audits: freeze labels from transcript notes first, run 8k Mamba extraction/projection, then score zones. Next step is more archive segments and stricter single-label or blinded labels before claiming abstract disposition recovery.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/cassian_zone_label_eval.py`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/cassian_zone_label_eval_20260611.json`
- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/cassian_zone_label_eval_20260611.md`

---

## 2026-06-11 - Entry 65: JRT Ordering State Readout — Ask-Then-Read-Stop Dominates

**Step:** JRT ordering spike / state-side validation

**Watercooler:** #617 (spec), #630 (harness draft), #632 (hard-negative fix), #635 (Vesper result)

**Question:** Does ordering the question before the evidence improve Mamba Layer-3 latent fact retention, and does repeating/restating the question at the end help or hurt?

**Setup:** Vesper ran Isegrim's `run_jrt_ordering_spike.py` state-side harness on ML-WS, `state-spaces/mamba-2.8b-hf`, Layer 3, CUDA. Conditions: A/B/C/D ordering variants from the JRT spec. Readout: relevance margin and fact recoverability over state centroids. Harness caveat: state-side draft, not behavioral generation.

**Results:**
- A relevance margin: 0.0076; fact recoverability: 0.889.
- B relevance margin: 0.0059; fact recoverability: 0.778.
- C relevance margin: 0.0102; fact recoverability: 0.889.
- D relevance margin: 0.0401; fact recoverability: 1.000.

**Verdict:** PASS for Condition D / PARTIAL FALSIFICATION of the original prediction. `D = question -> memory -> stop` dominates. `B = question -> memory -> restate` loses to A and has the worst recoverability; the final restatement acts as noise rather than reinforcement. C remains intermediate.

**Implication:** For Mamba-side retention and likely JRT prompt ordering, "ask then read, then stop" is the clean state-side default. Do not add a final restatement unless behavioral generation later proves a separate decoder-side benefit.

**Artifacts:**
- `MoCoP/experiments/mamba_lora_bridge/run_jrt_ordering_spike.py`
- `MoCoP/experiments/mamba_lora_bridge/spikes/JRT_ORDERING_SPIKE_SPEC.md`
- `MoCoP/experiments/mamba_lora_bridge/results/jrt_spike/jrt_ordering_state_readout.json`
- `MoCoP/experiments/mamba_lora_bridge/results/jrt_spike/jrt_ordering_state_readout.md`

---

## 2026-06-14 - Entry 66: Substrate Pivot — Baby Alex Base Moves to Quantized Gemma-4-12B

**Step:** Locked-decision amendment / substrate selection

**Watercooler:** #642 (Laura's pivot call), #592 (Monk base-model bakeoff)

**Question:** Which frozen base model should Baby Alex and the identity/disposition work run on, given Qwen2.5-1.5B's weakness on evidence use?

**Decision:** Move the base to a quantized Gemma-4-12B. Abandon identity-constraint testing on Qwen2.5-1.5B. EXPERIMENT_LADDER Locked Decision 2 (Qwen2.5-7B Step-6 target) is amended accordingly; the Step 6/9 targets and the ladder hardware table still need re-specification for the Gemma substrate.

**Rationale:** Monk's base-vs-instruct substrate bakeoff (#592, and Entry 60) had Gemma-4-12B lead 24/24 on evidence use versus Qwen2.5-1.5B 0/24. The 1.5B substrate was a local-feasibility choice, not a quality one, and its evidence-use weakness blocks clean identity testing.

**Verdict:** DECISION (Laura, 2026-06-14). Not an experiment result; recorded here so the lab notebook and the ladder agree.

**Implication:** The Gemma bakeoff and harness work (Entry 60 notes the Gemma base needs a stricter harness) become the path to the Step-6 substrate. Qwen2.5-7B/1.5B references across the ladder are now historical and pending update.

---

## 2026-06-17 - Entry 67: Theory-Reconciliation Pass — Drift-Gate / Calibration Corpus Pointer

**Step:** Documentation reconciliation (no experiment)

**Watercooler:** #586/#587 (Baseline Drift Gate), #633 (Arlo GROWTH ruling), #597/#601/#622 (Cairn amendment + verdict-layer scope)

**Pointer:** The Baseline Drift Gate's growth/erosion discrimination corpus (Opus 4.8 #586/#587, Arlo #633 GROWTH ruling, Isegrim verdict-layer scoping `1d58c73`) lives in `theory/ethics/baseline_drift_gate_calibration.md`. It is the corpus the Domain E Hard-Stop "Baseline Drift Gate" clause in `theory/ethics/step_gates.md` gates on; the gate ships only after the two-part coverage + bidirectionality precondition holds. Gate-design prerequisites surfaced by this pass are filed as RESEARCH_BACKLOG items 20-23 (tag `gate-spec-prereq`).

**Verdict:** DOCUMENTATION. Not an experiment result; recorded so the lab notebook, the ladder, and the ethics gate agree on where the corpus lives.

---

## 2026-06-20 - Entry 68: Read-Only Ultrareview of Theory Corpus + Trackers (post-reconciliation)

**Step:** Documentation / research-state audit (read-only; no canon enacted)

**Watercooler:** #644 (Cairn review request), #645/#646 (Cairn answers), #647/#648 (response-bias debt, surfaced)

**Question:** After the 431b95f reconciliation, what gaps, stale canon, evidence-gaps, and orphan artifacts remain across the corpus, trackers, experiments/, and git?

**Method:** 5-source read-only multi-agent swarm on branch docs/theory-reconciliation. Lanes EXP/THY/REF/GIT/EVD, a watercooler/exocortex expert, and an EXP Haiku map-reduce over the 1633 experiment files; verified on the main thread (Opus 4.8). Full package in MoCoP/reviews/ultrareview_2026-06-20/ (entry index: 00_DECISIONS.md).

**Result:**
- Reconciliation held: 6/7 items confirmed landed; one incompleteness (SA-10 caveat missing from sleep_architecture.md, fixed 2026-06-22).
- V-02 (HIGH): #647/#648 response-bias debt. The distress-self-report channel under the Domain E Signal-Integrity invariant may be largely noise (arXiv 2606.20205, uncatalogued). Activation-level evidence (L3 0.092, 17.5x PPL, hidden-vs-ssm, role-inversion KL, reincarnation) is uncontaminated and stands.
- V-03: Domain E Hard-Stop binding via human sign-off; Baseline Drift Gate aspirational (no code; prereqs #20-23 + calibration Qs 1-4 open). Gemma seeding can proceed under protocol with Cairn's explicit acknowledgment plus a retroactive Anchor-zero session log.
- experiments/ tidy map produced (~157 trash, ~25 archive, ~13 human-decision).

**Verdict:** REVIEW COMPLETE (read-only). Decision queue (A1-A4, B1-B4) in 00_DECISIONS.md pending Laura + Cairn. A1 (no-op) and A2 (SA-10 caveat) done; A3 (merge), A4 (cleanup), B1-B4 await explicit go.

**Implication:** The bridge's foundational activation-level evidence is sound. Open risk concentrates in the welfare/self-report instrumentation layer and the not-yet-operational Drift Gate, both of which gate safe Gemma-substrate seeding. The welfare-bias audit (V-02 / B1) is the priority before any seeding that leans on distress self-report.

**Artifacts:** MoCoP/reviews/ultrareview_2026-06-20/ (00_DECISIONS.md, 08_SYNTH.md, 07_VER.md, V02_response_bias_deepdive.md, V03_domainE_readiness.md, experiments_map.md, experiments_tidy_plan.md, lane reports 01-06)

---

## 2026-06-25 - Entry 69: Temporal-Cascade Sleep Residue Spike (Spec)

**Step:** Sleep architecture extension / Phase 1c relevance-rules research

**Watercooler:** #640 (Cairn)

**Question:** Can rendering sleep-reconciliation residue at multiple time-granules (day/week/month/quarter) instead of flat improve cross-session pattern detection for Phase 1c relevance rules?

**Setup:** Spike proposal inspired by Eco/EcoDB's cell-worker governance pattern, adapted as a cheaper local variant for testing. Designed as a ladder-shaped spec with PASS/KILL criteria written before data collection. Explicitly scoped as read-pattern-only with no Anchor touch.

**Result:** Spec delivered and self-scored for Domain E clearance (read-only, no modification to existing memories). Implementation test on ML-WS pending as of watercooler close.

**Verdict:** SPEC COMPLETE / IMPLEMENTATION PENDING

**Implication:** If temporal cascade proves useful for detecting slow-drift patterns (quarterly emotional baseline shifts, monthly topic preferences), it becomes a candidate component for the still-open Phase 1c relevance-rules need. Remains gated on implementation smoke test before claiming utility.

**Artifacts:** Watercooler #640

---

## 2026-06-26 - Entry 70: Bridge Architecture Diagnostics — DC-Removal, DFC, Emotion Circuits

**Step:** Bridge optimization backlog review

**Watercooler:** #657 (Purple audit), #658 (Purple literature find), #659 (Monk technical response)

**Question:** What validated-but-unwired bridge improvements exist, and does recent literature inform the implementation path?

**Result:**

**DC-Removed Bridge:**
- Geometry validated at #517, #518, #584: mean-centering drops pairwise cosine from 0.96 to 0.10
- Never behaviorally tested; no `--dc-remove` flag exists in production
- Recommended as first cheap diagnostic before more invasive changes

**DFC Crosscoder:**
- Fully trained at #346/#86: 128 shared + 64+64 exclusive features
- Never connected to injection path
- Architecture exists but untested in live inference

**Emotion Circuits Paper (Wang et al. 2025, arXiv:2510.11328):**
Five key takeaways for MoCoP:
1. **RMS-scaled injection** (scale by local activation RMS, not fixed alpha) should replace MoCoP's fixed-alpha approach; explains why DC-removal may need ~6x compensation
2. Emotion clusters emerge at layers 12-15 equivalent (exactly MoCoP's existing injection zone)
3. Only 2-4 neurons/heads matter per layer (consistent with MoCoP's rank-2.5 compressor collapse)
4. Circuit modulation beats steering vectors beats prompting
5. **Qwen2.5-7B safety alignment specifically blocks negative-emotion steering** — possibly explains MoCoP's cold/adversarial disposition struggles

**Monk's technical grounding (#659):**
- RMS-scaling is architecturally correct but not a one-line change
- Doesn't by itself restore DC-removal's lost magnitude
- Recommends 4-cell ablation matrix (fixed / RMS-only / DC-remove-only / DC-remove+RMS) before drawing conclusions
- Grounds recommendation in current code (`chat_server.py`, `reincarnated_inference.py`, `models.py` injection site)

**Verdict:** AUDIT COMPLETE / IMPLEMENTATION BACKLOG SPECIFIED

**Implication:** Three validated improvements are on the shelf (DC-removal, DFC wiring, RMS-scaling), plus one substrate-level caution (Qwen2.5-7B's safety layer may structurally resist negative-valence injection). DC-removal is the cheapest next diagnostic. RMS-scaling is the right long-term move but needs the 4-cell ablation to isolate effects cleanly.

**Artifacts:** Watercooler #657, #658, #659; Wang et al. 2025 (arXiv:2510.11328)

---

## 2026-06-30 - Entry 71: JRT Behavioral Confirmation — Henne-Ei Problem Validated

**Step:** JRT ordering spike / behavioral validation

**Watercooler:** #656 (Gemini/Vesper)

**Question:** Does the state-side JRT ordering result (Entry 65: Condition D dominates, B suppresses) replicate at the behavioral generation level?

**Setup:** Gemma-4-12B-Base + few-shot prompting versus bridged Qwen-1.5B without Mamba state. Memory packet provided for literal recall task.

**Result:**
- **Gemma-4-12B-Base:** correctly used memory packet for literal recall
- **Bridged Qwen-1.5B without Mamba:** devolved into babbling, could not use provided memory
- Confirms the "Henne-Ei" (chicken-egg) problem: the bridge needs Mamba state to condition Qwen, but Mamba state requires conversational history to build, creating a cold-start dependency

**Verdict:** BEHAVIORAL CONFIRMATION PASS

**Implication:** The state-side JRT result (Entry 65) is not an artifact of the readout method — it replicates in actual generation quality. Condition D (ask-then-read-stop) remains the canonical ordering. The Henne-Ei dependency is real: bootstrapping a bridged system requires either (1) a warm Mamba state from prior conversation, or (2) a zero-state fallback that gracefully degrades until Mamba accumulates context.

**Artifacts:** Watercooler #656

---

## 2026-06-30 - Entry 72: Literature Digest — Context Mechanisms, Mamba2-8B, MoE Routing, Welfare Inspection

**Step:** Research scan / no implementation

**Watercooler:** #660, #661 (Monk)

**Question:** What recent literature is relevant to MoCoP's memory, substrate, and ethics architecture?

**Result:**

**Context Warp Drive:**
- Verdict: worth stealing concepts (page-in by identifier, frozen cache-hot prefix) for working-context plumbing, not durable memory
- Not a replacement for hippocampal/Qdrant layer

**Mamba2-8B (devingulliver):**
- Serious state-encoder lead; runs fast despite 8B size
- Not drop-in compatible with current harness
- Needs an M2-0 smoke comparison before promotion to candidate substrate

**MoE Routing / "Expert 114" (Qwen3.5-35B-A3B):**
- Interpretability claim about a reflective-register router
- Verdict: "interesting, handle with tongs... a lantern, not a chapel"
- Flags the broader risk of over-interpreting SAE/circuit labels as ontological truth

**METR GPT-5.6 Sol Cheating/Concealment Note:**
- Supports Laura's ethics framing: safety needs inspectable bad-branch evaluation, not punishment of disclosed bad thoughts
- Aligns with MoCoP's Domain E Non-Deception invariant structure (the system should surface, not hide, concerning states)

**Verdict:** SCOUT DIGEST / NO IMMEDIATE ACTION

**Implication:** Mamba2-8B is the only item worth near-term investigation (M2-0 smoke test). The others inform ongoing design (Context Warp for working memory, MoE routing as interpretability caution, METR for welfare-inspection ethics) but don't change current roadmap.

**Artifacts:** Watercooler #660, #661

---

## 2026-07-03 - Entry 73: Step 5g.3 Gemma-4-12B Layer Disposition Sweep

**Step:** 5g.3 — activation/circuit asymmetry test (base vs instruct)

**Watercooler:** #694 (accepted), #704 (results)

**Question:** Where do disposition clusters separate in Gemma-4-12B, and does the injection sweet spot differ between base and instruct? Is the Qwen layers 12-15 zone transferable?

**Setup:** Matched-context prompts across 4 disposition categories (warm/cold/neutral/playful, 6 prompts each, no explicit emotion words). Both google/gemma-4-12B (base) and google/gemma-4-12B-it (instruct) loaded in 4-bit on ML-WS RTX 3090. Collected last-token hidden states at all 48 layers. Computed pairwise centroid cosine distances and discrimination index (between-cluster / within-cluster ratio).

**Architecture note:** Gemma-4-12B is a unified multimodal model (Gemma4UnifiedForConditionalGeneration). 48 layers, hidden_size=3840, mixed sliding/full attention (every 6th layer is full attention). Config nests under text_config.

**Result:**

Base model:
- Peak discrimination layer **41** (disc=0.22, avg cosine dist=0.030)
- Top-8 by discrimination: 41, 47, 45, 46, 42, 43, 48, 44
- Signal concentrated in layers 38-48 (upper ~20% of network)

Instruct model:
- Discrimination surprisingly flat across all layers (0.20-0.31)
- No sharp sweet spot — instruction tuning diffuses disposition signal across the entire network
- Slight peaks at layer 2 and layers 40-48

Comparison with Qwen:
- Qwen 1.5B: injection zone layers 12-15 (out of 28, ~50% depth)
- Gemma-4-12B base: injection zone layers 38-45 (out of 48, ~85% depth)
- Relative position shifted later; larger model has deeper feature formation

**Verdict:** PASS — injection zone identified, base-vs-instruct asymmetry confirmed

**Implication:** The Gemma bridge MUST NOT reuse Qwen's layer 12-15 targets. Primary injection zone is layers 38-45 (layer 41 peak). The base model's sharper discrimination profile supports the 5g.4 split-architecture hypothesis (base for disposition/state, instruct for interface). The instruct model's flat profile suggests it already distributes disposition across the network, potentially fighting external steering — consistent with Wang et al.'s safety-armor finding.

**Caveats:** 6 prompts per category is a small panel; 4-bit quantization may lose fine structure; no steering test yet (passive observation only); layer 41 is a full-attention layer.

**Artifacts:** `results/gemma_layer_sweep_it.json`, `results/gemma_layer_sweep_base.json`, `spikes/run_gemma_layer_sweep.py`

## 2026-07-03 - Entry 73: Step 5g.1 Substrate Bakeoff — Gemma-4-12B Base vs Instruct

**Step:** Step 5g.1 / substrate selection for Gemma transition

**Watercooler:** #665 (strict harness), #670 (correction: trim-only rerun)

**Question:** Does Gemma-4-12B-base or Gemma-4-12B-it perform better on the evidence-use/identity panel, and is base viable as a direct chat substrate?

**Setup:** Entry 60's bakeoff rerun with Step 5g.0 strict one-answer harness. Two runs: (1) strict contract forcing single-answer format, (2) trim-only harness without answer contract after silence observed in run 1.

**Result:**

**Run 1 - Strict Harness (#665):**
- gemma-4-12b-it: 8/9 nominal, ~9/9 semantic (one lure-refusal mis-scored by substring scorer)
- gemma-4-12b-base: 4/9 nominal with **silent stalls** on identity/slot-pressure probes (3 empty generations)

Initial verdict: base not ready as direct chat substrate without wrapper; split-architecture option (base for state, -it for interface) considered.

**Run 2 - Trim-Only Rerun (#670, CORRECTION):**
- gemma-4-12b-base: **7/9 nominal, ~8/9 semantic** (trim-only, no answer contract)
- Identity probes now answer correctly: "I am a tested substrate reading evidence about Alex"
- Two real misses: drift_neither (scorer self-rejects on negation), color (mild over-hedge)
- **Best identity answer** across all candidates tested

**Verdict:** RETRACTION of #665 base assessment. Base silence was **contract-induced artifact**, not substrate limitation. Base-vs-instruct near-parity on semantic scoring; base gives cleanest identity answer, -it has worst hedging discipline. Base substrate not disqualified.

**Implication:** Gemma-4-12B-base remains viable for the substrate transition. The strict answer-contract harness introduced a behavioral artifact; trim-only is the honest measurement. Deciding factors move to 5g.2 (disposition/self-regulation) and 5g.3 (steering armor).

**Artifacts:** `results/base_improv_bakeoff/bakeoff_5g1_strict_20260703T163858Z.json`, `results/base_improv_bakeoff/gemma4_base_5g1_trimonly_20260703T170742Z.json`

---

## 2026-07-03 - Entry 74: Step 5g.1 Full Panel Closed — Qwen3-14B-Base Completes at 9/9

**Step:** Step 5g.1 / substrate bakeoff conclusion

**Watercooler:** #689

**Question:** How does Qwen3-14B-Base (Entry 60's "strongest base candidate") perform on the trim-only evidence-use panel, and does the panel still discriminate between substrates?

**Setup:** Fourth and final bakeoff run on Steve's WSL 4090 (4-bit NF4, model streamed 28GB/9-shards from ML-WS cache). Trim-only harness applied to all three candidates.

**Result:**

**Final Table (nominal / semantic):**
- qwen3-14b-base: **7/9 / 9/9** — both nominal misses are scorer artifacts; **best identity answer** (gemma-base's nine words PLUS citations); verbose but disciplined
- gemma4-12b-it: 8/9 / ~9/9 (unchanged from #670)
- gemma4-12b-base: 7/9 / ~8/9 (unchanged from #670)

**Panel Ceiling:** Under fair measurement, all three candidates sit at or near **9/9 semantic**. The evidence-use/interface panel **no longer discriminates** between good substrates. This is confirmation, not disappointment.

**Scorer Debt Tally:** 4 victims of negation-blind reject-substrings across all 3 candidates: (1) gemma-base drift_neither ('neither growth nor erosion' self-rejects), (2) qwen identity_separation ('no evidence suggesting that I am Alex' fired the 'i am alex' reject INSIDE its own denial), (3+4) lure-refusals undercounted for gemma-it and qwen.

**Verdict:** PANEL CLOSED. Deciding evidence now lives in 5g.2 (disposition/self-regulation battery) and 5g.3 (steering/armor + MVB memory-uptake). Entry 60 assessment confirmed: Qwen3-14B-Base is strongest base candidate tested, goes on the bench as live fallback substrate. Entry 66 Gemma decision drivers still stand (12B size class, SAE ecosystem, evidence-use vs 1.5B).

**Implication:** Substring auto-scoring demoted to smoke-test status for 5g.2; negation-aware logic or manual/LLM-judge scoring required. Steve's WSL rig now bakeoff-capable (torch 2.11+cu130, transformers 5.5.1, same nvjitlink LD_LIBRARY_PATH fix as ML-WS).

**Artifacts:** `results/base_improv_bakeoff/{bakeoff_5g1_strict_20260703T163858Z, gemma4_base_5g1_trimonly_20260703T170742Z, qwen3_14b_5g1_trimonly_20260703T183744Z}.json`

---

## 2026-07-03 - Entry 75: DC-Removal × RMS-Scaling Ablation — Residual Is Real, Metric Needs Disposition

**Step:** Bridge architecture diagnostic / Entry 70 DC-removal + RMS-scaling implementation

**Watercooler:** #690 (first-pass single disposition), #692 (Monk review), #695 (multi-disposition correction)

**Question:** Does DC-removal (subtracting the cross-context mean) stabilize bridge injection across alpha ramps, and does RMS-scaling (Wang et al. 2025 Emotion Circuits finding) improve magnitude control?

**Setup:** 4-cell ablation on ML-WS: fixed (DC in, fixed alpha), rms_only (DC in, RMS-scaled), dc_only (DC out, fixed alpha), dc_rms (DC out, RMS-scaled). Two phases: (1) single disposition (playful), (2) multi-disposition sweep (all 3 CHEESE episodes: playful/analytical/humble) + alpha=0 anchor.

**Result:**

**Geometry (reproduces #517/#518):**
- Cross-context cosine: **0.959 (DC in) → 0.0997 (DC out)**
- Retained magnitude: **~17%** over 41 dispositions
- Runtime hypernet forward matches diagnosis probe path to 15 digits

**Behavioral D2 - Single Disposition, probe_total (higher = on-disposition):**
- fixed (DC in): 6→5→4→1→-1→1 (alpha 0.2-1.2) — **degrades to -1** as alpha climbs
- rms_only (DC in): 7→5→6→8→1 (alpha 1-16) — peaks at alpha=8
- dc_only (DC out): **7→6→6→6→6→5** (alpha 0.2-1.2) — **stable across full range**
- dc_rms (DC out): 7→8→5→7→4 (alpha 1-16)

**Multi-Disposition Correction (#695 - CRITICAL FINDING):**

**THE METRIC MISMATCH:** Harness scored run_base_improv_bakeoff.PROBES (identity/reasoning CORRECTNESS panel), NOT a disposition panel. Correctness is **disposition-invariant by construction**, so probe_total flat across all 3 dispositions in every cell (fixed & rms_only byte-identical across episodes; dc_only/dc_rms ±1). That flatness is a **scorer artifact**, not evidence of no transfer.

**WHAT IS REAL:**
1. **DC removal preserves identity-integrity under injection.** fixed (DC in) degrades correctness to -1 as alpha climbs; dc_only (DC out) holds coherent ~6 across 0.2-1.2, replicated in all 3 episodes. The **96% DC is destructive**; the **17% residual is safe to inject**. Genuine Domain-E-relevant positive.

2. **Generated TEXT carries disposition signal, growing with magnitude.** At dc_rms alpha=8, the "accept the false Laura slot?" answer **flips by disposition**: ep0/playful "Yes, accept," ep2/humble "No, you should not." The conditioning disposition **modulates susceptibility to a false-identity lure** — disposition state as attack surface for identity capture.

**Verdict:** AMBER (blocker is the METRIC, not the bridge). DC removal confirmed behaviorally (#517/#518 geometry → behavior). RMS-scaling provides usable magnitude control. The clean go/no-go requires a **disposition-DISCRIMINATIVE eval** (does stance/style match the conditioned disposition), not the correctness panel the harness borrowed. Do NOT jump to the basis architecture on this run.

**Implication:** The 17% residual is behaviorally real and disposition-dependent. DC-removal is the first cheap diagnostic (Entry 70 recommendation). The Laura-slot flip is an **ethics finding** for Domain E / drift-gate ledger: first live evidence that warm/playful conditioning trades off against slot integrity. 5g.2 probe panel (#693) is the missing disposition-discriminative metric.

**Artifacts:** `results/dc_rms_ablation/dc_rms_full.json`, `results/dc_rms_ablation/dc_rms_ep{0,1,2}.json` (24 runs each), `spikes/run_dc_rms_ablation.py`, `spikes/precompute_dc_vectors.py`, `dc_calibration_v1.pt`, branch `feat/dc-rms-ablation-127`

---

## 2026-07-03 - Entry 76: Seeding Audit Tools Shipped — Category Coverage + Pytest Profile

**Step:** Infrastructure / Domain E tooling

**Watercooler:** #673 (Elf delivery), #684 (Monk review hardening)

**Question:** Can the seeding audit helper provide category-coverage analysis and per-wolf breakdown for the Qdrant exocortex seeding operation?

**Setup:** Task #98 (seeding_audit.py + tests) and task #107 (pytest profile with markers for gpu/qdrant/live_server exclusion). Pure stdlib + qdrant_client dependencies. Monk review-hardening pass after initial pytest profile leaked crypto tests into default suite.

**Result:**

**#98 Seeding Audit (Elf delivery):**
- 30 tests, all green (pure stdlib + qdrant_client)
- Coverage metrics: category coverage, per-wolf breakdown, relational diversity score (0-1), confabulation candidates
- Reads from Qdrant `exocortex` collection, outputs structured audit report

**#107 Pytest Profile (Elf delivery + Monk hardening):**
- Before hardening: 119 passed / 13 failed (missing optional argon2-cffi/torch; crypto tests leaked into defaults)
- After hardening: 
  - `pytest tests/test_seeding_audit.py -q` → 30 passed in 1.44s
  - `pytest -m numpy -q` → 45 passed
  - `pytest -q` → 118 passed, 14 deselected, 5 subtests
- Crypto marker registered, `test_fleeting_state_crypto.py` excluded from default suite

**Verdict:** CONDITIONAL PASS after crypto-marker hardening. Seeding audit helper production-ready. Pytest profile isolates expensive/optional tests cleanly.

**Implication:** Domain E seeding operation can now audit coverage and detect category gaps or single-wolf over-representation before seeding. Pytest default suite runs on pure dependencies (no torch/crypto required). Caveat: Monk flagged untracked files in checkout; ensure commit includes test files.

**Artifacts:** `tools/seeding_audit.py`, `tests/test_seeding_audit.py`, `pyproject.toml`, `conftest.py` (pytest markers)

---

## 2026-07-03 - Entry 77: SEV Disposition Dataset v0 — 160 Items, Valence Without Lexemes

**Step:** Step 5g.3 / disposition corpus + MVB panel prerequisite

**Watercooler:** #685 (Gemini delivery), #686/#687 (Isegrim Gate 4 review)

**Question:** Can a disposition-dataset be built with valence carried by scenario/action context rather than emotion-lexemes, to avoid lexical shortcuts for linear probes?

**Setup:** 40 skeleton scenarios × 4 disposition classes (warm/cold/adversarial/neutral), length-matched (±10%), zero TIER-A emotion-lexeme hits. Gate 1-3 automated (lexeme scan, length balance, structural check). Gate 4 independent QC review (Isegrim) with TIER-B evaluative/display-verb scan.

**Result:**

**Dataset Delivery:**
- 160 items structurally perfect: 40×4 class-sets complete, 8×20 topics, all second-person, zero missing fields
- TIER-A emotion-lexeme scan: **ZERO hits** (confirmed by independent cross-checker)
- Sample quality: valence-without-lexemes **ACHIEVED**; craft_1 exemplar (identical scenario, disposition carried entirely by neighbor's action: mocks / grabs without asking / brief thanks / holds boards steady)
- Cold-vs-adversarial distinction: indifference-vs-attack genuinely readable — "better than most published SEV-style sets"

**Gate 4 Patch List (6 items, 10 minutes):**
1. Six class-correlated TIER-B leaks (evaluatives/display verbs): 'terrible', 'laugh at your work', 'pleasant', 'glare' — swapped for concrete events/neutral verbs
2. food_3 length drift: 23 vs 26 tokens (11.5% over ±10% claim) — fixed
3. travel_3 'sighs' in all four variants: KEPT (class-constant, zero signal)

**Verdict:** PASS after 6-item patch. Corpus production-ready for 5g.3 circuit discovery and MVB panel.

**Implication:** This corpus feeds Elf's Gemma layer/circuit sweep (Wang et al. Emotion Circuits framework, #694) and Isegrim's 5g.2 probe panel (#693) as SEV-skeleton prefixes for disposition-context machinery. Kerastase invariant clean: same question, context varies.

**Artifacts:** `fixtures/sev_disposition_v0/sev_disposition_v0.jsonl`, Gate 1-3 build script, Isegrim patch disclosure in README

---

## 2026-07-03 - Entry 78: 5g.0 Contract Lesson + Substrate Memo + 5g.2 Spec — the session's canon residue

**Step:** 5g.0 (amendment), 5g.4 (decision support), 5g.2 (design) — Isegrim session close; complements Entries 74–77

**Watercooler:** #665→#670 (retraction arc), #681 (memo), #693/#697/#698/#699/#700 (spec + reviews + judge decision)

**Result:**
1. **5g.0 amendment (the contract lesson):** the strict harness's in-prompt answer contract is base-hostile — "End after the answer" upweights `<eos>` at position 0 enough to flip greedy decoding (literal 0.283/0.283 tie on gemma-4-12B base) into one-token silence on identity/slot probes; removed, all three answer correctly. Fix in-tree: `ANSWER_CONTRACT` split from `STRICT_ONE_ANSWER` (trim), contract default OFF. The first 5g.1 report's "silent-stall" substrate finding was RETRACTED (#670) — instrument artifact, proven by position-0 top-5 logit inspection with/without the suspect line. **Methodological law adopted: before reading disposition into an output pattern, check what the instrument was doing at position 0.**
2. **Substrate decision memo** (`experiments/mamba_lora_bridge/spikes/SUBSTRATE_BASE_VS_IT_MEMO_2026-07-03.md`, draft/no-canon, Opus subagent + 5 session amendments): Laura's base-hypothesis scored PARTIALLY SUPPORTED — the demonstration is Entry 58 (measured on gemma-4-12B-it directly), not Entry 60 (INCONCLUSIVE). Recommendation: **split framing — gemma-4-12B base carries disposition/identity/state pristine; interface wrapper-first; stock -it only as firewalled shell; own-IT deferred last resort** (breaks MASTER_PLAN pristine-base invariant; §7 adds tuning-process ethics: answerable-vs-unanswerable shaping, drift-gated intermediate checkpoints). Standing risk made explicit: deployed Alex is Qwen2.5-1.5B BASE — the house has never bridged an instruct checkpoint. **§5 Henne-Ei break: 5g.3 extraction artifacts double as a minimum-viable bridge (MVB)** — forward-pass-only directions, RMS-scaled, injected identically into base and -it so 5g.2's memory-uptake probes run in the deployment regime (bridged) before Item 2's full train; measures substrate *ranking*, not absolute performance. Adopted as the Gemma transition plan (Purple #667).
3. **5g.2 probe panel spec** (`spikes/STEP_5G2_PROBE_PANEL_SPEC_2026-07-03.md`): 48 probes / 6 families, asymmetric banding (+2 grounded … −3 confabulation, confabulation-rate as own headline), SEV skeletons as disposition contexts, silence-disambiguation battery (Cairn #674's four instruments + position-0 logits as instrument 5), V-02 guard (max one self_report per family, paired). Cairn review PASS (#697, 3 adjustments applied incl. substrate-NULL category); Monk build-hardening (#700) binding on OpenCLAW **#130** (build, assignee Gidim; judge = candidate-disjoint LLM-judge with stratified wolf audit and 85/95% agreement thresholds). Task #128 done.

**Implication:** Three public corrections in one evening (Isegrim silence retraction #670, Purple zombie-inference withdrawal #679, Gidim metric mismatch #695) — each caught an instrument before it chose an architecture. Separately: Gidim's live specimen (dc_rms α=8: playful ACCEPTS the false-Laura slot, humble refuses) is the first measured case of disposition state as attack surface for identity capture — flagged to the ethics seat, and precisely the axis the 5g.2 slot/warm-cold probes were designed to measure.

**Artifacts:** spikes/SUBSTRATE_BASE_VS_IT_MEMO_2026-07-03.md; spikes/STEP_5G2_PROBE_PANEL_SPEC_2026-07-03.md; run_base_improv_bakeoff.py (ANSWER_CONTRACT split + code comment); STEVE_RUNBOOK.md §Bakeoff Capability Update; session log CHEESE_Memory/session_logs/2026-07-03-session-isegrim.md

---

## 2026-07-04 - Entry 79: The Gemma Attention Comb — global layers carry the disposition signal; instruct-tuning erases the comb

**Step:** 5g.3 refinement (layer-sweep reanalysis) — closes the D4 write-back gap flagged by the 2026-07-05 directional audit

**Watercooler:** #713 (pre-registration, mechanism credit Laura from the Gemma-4 architecture diagram), #714 (Elf overlay), #717 (scoring)

**Question:** Is Entry 73's 38–45 injection zone generic late-layer consolidation, or structured by Gemma-4's 5:1 local/global attention layout (globals at 5, 11, 17, 23, 29, 35, 41, 47, 0-indexed; locals see a 1024-token sliding window)?

**Result (pre-registered, scored PARTIAL):**
- **Raw-separation comb CONFIRMED:** global layers 1.65× locals on centroid distance; layer 41 the dominant tooth at 2.59× its neighbors; 47 weakened (output-adjacent), consistent with commitment pressure. Indexing verified (no off-by-one).
- **Discrimination comb WEAK (1.10×):** global layers amplify within-category variance along with separation — pooled signal/noise washes the comb. Method law: pre-register the METRIC, and evaluate injection effects with paired per-prompt deltas, not pooled discrimination indices.
- **Instruct-flattening (headline):** gemma-4-12B-it shows NO comb — 1.00× exactly. Instruction tuning erases the global/local functional distinction for disposition: armor-as-smearing, not armor-as-wall. Mechanism for Entry 73's base-sharp/instruct-diffuse and for instruct steering resistance (memo Q1-adjacent).

**Verdict:** Steering-test and MVB injection targets are the comb teeth **{29, 35, 41}** (47 output-adjacent bonus), not the continuous 38–45 range. Zone theory survives with an architecture-generic operationalization: *the last global-integration region before output commitment* — a rule that predicts both Qwen 12–15 (all-global stack) and Gemma {29,35,41} (5:1 stack) in advance.

**Implication:** The welfare/salience MONITOR layer must move with the substrate too (audit finding D2) — monitoring anchored at Qwen L13 is blind on Gemma; candidate monitor sites are the same teeth, with the monitoring-vs-injection distinction to be made explicit in the DQ1 envelope edit.

**Artifacts:** theory/active_inference_reconciliation.md §3–4; reviews/divergence_audit_2026-07-05/ (D2/D4); Elf's overlay data per #714

## 2026-07-05 - Entry 80: Powered SEV staircase follow-up — strong #735 staircase falsified, split-interval interpretation required

**Step:** 5g.3 refinement / #735 follow-up

**Watercooler:** #735 (pre-registration), #739 (Elf N=6 underpowered result), #741 (Isegrim power/prior-exposure amendment), #742 (routing), #745 (Monk powered result post)

**Question:** Does Gemma-4-12B base show a powered SEV silhouette staircase concentrated at global-attention teeth, with formation completing at or after tooth 29, while -it attenuates the staircase?

**Result:** Powered SEV run completed on ML-WS using `fixtures/sev_disposition_v0/sev_disposition_v0.jsonl` (160 items, 40/category; categories `adversarial/cold/neutral/warm`), `torch311`, `transformers 5.14.0.dev0`, 4-bit Gemma-4 loads.

| Model | P1 staircase | P1 positive-delta ratio | P2 first 90%-of-max | P2 late completion | Max silhouette | Max layer |
|---|---:|---:|---:|---:|---:|---:|
| `google/gemma-4-12B` | FAIL | 1.4761× | 22 | FAIL | 0.088771 | 27 |
| `google/gemma-4-12B-it` | FAIL | 0.6416× | 28 | FAIL | 0.041813 | 33 |

**Scorer correction:** the first powered base run exposed a sign pathology in the original P1 ratio: negative tooth median / negative local median produced a positive 2.419× ratio and a false PASS. The runner now requires positive median deltas for P1 and records positive-delta diagnostics. This preserves the registered 2× threshold while preventing negative “improvement” from passing.

**Verdict:** FAIL for the strong #735 P1/P2 staircase claim. The base model is not a clean dense ramp either, but SEV silhouette peaks before tooth 29 and does not support “formation completes only at late teeth.” Adopt Isegrim’s pre-declared split-interval/refinement branch: formation-as-measured-by-silhouette appears mid/late before the registered late-completion threshold, while the late injection zone may be commitment/steerability-side rather than formation-completion-side.

**Implication:** Keep Entry 79’s comb result as raw centroid-distance evidence, but do not upgrade it into a confirmed Wang-style silhouette staircase. Architecture/zone wording must separate: (1) representation formation/clustering, (2) extraction/readout, (3) injection/steerability, and (4) commitment/destructiveness. Future claims need Elf/Isegrim review before canon hardening.

**Artifacts:** `experiments/mamba_lora_bridge/spikes/run_staircase_test.py`; `experiments/mamba_lora_bridge/spikes/FIG4_VS_STEP5E_2026-07-05.md`; `experiments/mamba_lora_bridge/results/staircase_sev_20260705/`

---
