# MoCoP Bridge Review: Orion & Opus Synthesis

This review combines Orion's architectural sweep with Opus's execution-level diagnostics, but keeps a strict boundary between:

- what the code and runs actually establish
- what is currently a strong hypothesis
- what should happen next

## 1. Environment & Hardware Realities (Opa-PC)

**Leading diagnosis, not solved proof:** the silent Opa-PC failures are plausibly Windows OOM kills rather than Python logic bugs. That matches the observed pattern: model load can succeed, but the first real forward or backward pass can die once activations, SSM state, and gradients come online.

- **Useful diagnostic aid:** `faulthandler.enable()` is still worth adding early in boot, because it can surface native crashes and preserve the last Python stack if the process dies badly.
- **Important limit:** `faulthandler` does not prove an OOM cause, and it will not magically turn a hard OS kill into a traceback.
- **Operational verdict:** Opa-PC should be treated as a dry-run, smoke-test, and tooling-validation box. Full training epochs belong on cloud A100-class hardware. Cheap context-dump diagnostics may still be viable locally if they use smaller models and avoid real training load.

## 2. Mathematical Instability (The PPL Explosion)

The Sweden `64`-sample run established a real pattern:

- epoch 1 briefly improved bridge perplexity over baseline
- epochs 2 and 3 became destructive on held-out eval
- train loss kept falling while eval behavior worsened

That is strong evidence for overfitting and over-injection.

**What is verified in code:**

- `BridgeConfig` still defaults to `lora_rank=8` and `lora_alpha=16`, giving a base scaling factor of `2.0`
- Codex's `--max-lora-delta-norm` clamp already exists in the trainer and is applied before LoRA injection during training/eval

**What remains an inference:**

- the exact claim that the effective LoRA magnitude grows to `~13.2` is plausible, but should be treated as a measured hypothesis unless paired with actual norm traces from the run

**Implication:**

The current dynamic-LoRA path is still too unconstrained. Lowering the default scale and keeping norm clamping available are both sensible moves. The clamp is not a full solution, but it is the right tourniquet.

## 3. Metric Integrity (The PCA Gate)

Lain's PCA questions cannot be answered by the inline centroid/norm stats alone.

**What the inline stats are good for:**

- quick anomaly checks
- trend watching across epochs
- confirming that compressed states are not exploding numerically

**What they are not:**

- dataset-level manifold analysis
- PCA
- a reliable measure of compressor collapse on their own

**Important nuance:**

The current centroid metrics are computed per batch, not over the full dataset. With very small batches they become noisy, and with batch size `1` they degenerate completely. That makes them useful as cheap surrogates, not as the final diagnostic.

**Practical consequence:**

To answer the compressor-collapse question, we need saved context vectors from `--save-train-contexts` or `--save-eval-contexts`, then run:

```powershell
python -X utf8 linearity_probe.py context-pca <contexts.pt>
```

Existing prediction JSONs are still useful for qualitative inspection and surrogate trends, but they are not sufficient for true PCA because they do not contain the full context vectors.

## 4. Surface Alignment (Prompt Mismatch)

This is a real deployment risk, but not the first gate.

- **True statement:** training on `completion` while later deploying into `[Game World]` tags or structured MUD prompts creates a surface mismatch
- **But:** Phase 2 is still asking the simpler question, "does the channel work at all on a base-model-compatible eval surface?"

So the right prioritization is:

1. prove or disprove that the bridge channel can generalize at all
2. simplify the injection path if needed
3. only then spend serious effort aligning train/inference prompt surfaces for deployment

Prompt mismatch should stay on the board, but it should not displace clamp/PCA/simplification as the immediate gate.

## 5. Architectural Housekeeping

- **Model defaults:** the cleanup sweep replacing hardcoded model IDs with CLI/config variables is important and already in flight
- **Canonical default:** the primary default should remain `Qwen/Qwen2.5-7B` unless Laura explicitly changes that decision
- **Paritization target:** make sure the trainer and peripheral scripts agree on model IDs, prompt surface, and any reduced-LoRA defaults

---

## Action Plan & Recommendations

1. **Keep Opa in the right role.**
Use it for dry-run, context-dump, and verification work. Do not plan real training there.

2. **Preserve the clamp and consider lowering default LoRA scale.**
`--max-lora-delta-norm` is the correct immediate safeguard. Also audit whether `lora_alpha=16` should become `8` as the default in the shared config path, not just in dry-run scaffolding.

3. **Run the PCA gate with real saved contexts.**
Do one cheap diagnostic run that emits `train_epoch_XXX_contexts.pt` and inspect it with `linearity_probe.py`.

4. **Do not over-read the inline centroid stats.**
They are useful telemetry, not proof of collapse.

5. **Treat prompt mismatch as Phase 3 unless a simpler bridge variant starts working.**
Right now the first question is channel viability, not deployment polish.

## Bottom Line

The synthesis is strongest when it says:

- Opa is not the place for real training
- the current dynamic-LoRA bridge is probably over-injecting
- the clamp is a sensible immediate control
- PCA needs saved context vectors, not just inline stats

The bridge is not dead, but the current dynamic-LoRA form is still too free. The right next move is still the simplification gate, with a real compressor PCA diagnostic alongside it.
