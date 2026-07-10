# Infra Review — C3 Gemma Activation Bridge Training Plan

**Reviewer:** Techno-Monk / Hermes  
**Date:** 2026-07-06  
**Scope:** OpenCLAW #139 infra lane. Review of `C3_GEMMA_BRIDGE_TRAINING_PLAN_2026-07-06.md` plus the complete companion `GEMMA_BRIDGE_DESIGN_2026-07-06.md`, current bridge trainer/recorder interfaces, and live ML-WS Gemma config smoke.  
**Status:** DESIGN REVIEW ONLY — no training launch.

## Verdict

**Not runnable as-is, but the infrastructure path is sound if treated as a porting task rather than a flag flip.**

The cited `C3_GEMMA_BRIDGE_TRAINING_PLAN_2026-07-06.md` is accurately marked as a dead-branch fragment and ends mid-shape at the bridge head definition. Use it only for the zone-rule mapping. The complete working design source is `GEMMA_BRIDGE_DESIGN_2026-07-06.md`.

## Verified facts

Live ML-WS / Gemma overlay config smoke:

```text
model: google/gemma-4-12B
model_type: gemma4_unified_text
hidden_size: 3840
num_hidden_layers: 48
num_attention_heads: 16
num_key_value_heads: 8
head_dim: 256
v_proj input width: 3840
v_proj output width: 2048
```

Therefore for teeth `{29,35,41}` the Phase-1 activation-bias heads should be:

```text
target_specs = [(29, "v_proj"), (35, "v_proj"), (41, "v_proj")]
target_dims  = [(3840, 2048), (3840, 2048), (3840, 2048)]
```

This confirms Isegrim's GQA warning: do **not** allocate 3840-wide v_proj output heads.

## Infra blockers before training

### B0 — The reviewed C3 file is a fragment

`C3_GEMMA_BRIDGE_TRAINING_PLAN_2026-07-06.md` ends at:

```text
MLP 2560 → 4096 (GELU) → per-target-layer heads 4096 → 3840 ...
```

That line is stale/wrong for the v_proj output surface and incomplete. Do not use this fragment as a runner spec. Preserve it as provenance/zone-rule salvage only.

### B1 — Current trainer is Qwen-shaped

`train_cheese_bridge.py` still hardcodes Qwen-era defaults:

```python
DEFAULT_QWEN_MODEL_ID = "Qwen/Qwen2.5-7B"
TARGET_SPECS = [(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")]
def infer_qwen_target_dims(...)
```

It can probably be ported, but not safely invoked for Gemma until it accepts:

- `--target-model-id google/gemma-4-12B`
- `--target-layers 29,35,41`
- generic `infer_target_dims()` using `text_config` when present
- checkpoint metadata key `target_model_id`, with legacy shim for `qwen_model_id`
- target specs stored in the checkpoint and never assumed globally

### B2 — Recorder is closer, but still Qwen-labeled and dtype-stale

`record_cheese_batch.py` already has useful generic knobs:

```text
--model-name
--target-layers
--capture-vproj-inputs
```

It also introspects `model.model.layers[layer_idx].self_attn.v_proj.{in,out}_features`, so Gemma should work if the module path matches. But before full recording:

- rename/neutralize Qwen-specific messages (`1.5B v_proj width`)
- use `dtype=` rather than deprecated `torch_dtype=` in the Gemma overlay
- add an explicit Gemma smoke with `--model-name google/gemma-4-12B --target-layers 29,35,41 --capture-vproj-inputs`
- confirm output files contain both `v_proj_in` width 3840 and `v_proj_out` width 2048

### B3 — Loss/eval code uses global `TARGET_SPECS`

Multiple functions in `train_cheese_bridge.py` iterate over module-level `TARGET_SPECS`. For Gemma this is fragile. Target specs must become a runtime object carried through:

- target validation
- materialization
- pair building
- loss functions
- checkpoint save
- diagnostics

Otherwise a partial port can silently train or validate against Qwen layers.

### B4 — Training must wait for a single-env or two-process decision

The design correctly identifies the fork:

1. **single env:** `gemma4-mocop` runs Mamba extraction + Gemma activation recording + bridge training;
2. **two-process/artifact:** torch311 records Mamba states, gemma4-mocop records Gemma activations/trains.

Current verified state:

- Mamba width contract under `gemma4-mocop`: GREEN.
- `cache_params` incremental/live accumulation under `gemma4-mocop`: still untested.
- Existing Qwen bridge production env: `torch311` pinned to transformers 5.6.2.

For offline training, artifact shipping is acceptable. For future chat_server integration, run the overlay `cache_params` smoke before promising single-env service.

### B5 — Dataset custody/security must be concrete, not aspirational

The design says no Qdrant access from Vast.ai and encrypted state before scp. Good. Add runner-level acceptance:

- manifest with SHA256 for each tensor bundle
- no raw Qdrant/secret material on Vast.ai
- encrypted archive only for any real conversation-derived shaping catalog
- local-only decryption after copyback
- copyback verification before instance termination
- explicit `HF_HOME`/cache paths and disk budget in the cloud runbook

## Recommended implementation sequence

1. **Create a Gemma target introspection helper**
   - emits model id, revision, architecture, layer count, module path, input/output widths for each target layer.
   - saves JSON next to artifacts.

2. **Patch recorder minimally**
   - generic labels, `dtype=`, target manifest.
   - smoke one tiny synthetic episode locally/ML-WS with teeth `{29,35,41}`.

3. **Patch or fork trainer**
   - preferred: `train_gemma_bridge.py` as a thin fork until the Qwen/Gemma abstraction proves stable.
   - required: no module-level Qwen `TARGET_SPECS` assumptions.

4. **Add dry-run/stub tests**
   - target dims `(3840,2048) × 3`
   - checkpoint contains `target_model_id`
   - legacy checkpoint with `qwen_model_id` still loads through shim.

5. **Run tiny real smoke, not training**
   - one or two synthetic episodes
   - record Mamba state + Gemma activations
   - build bridge module
   - run one forward/backward step
   - save/load checkpoint
   - run diagnostic shape check

6. **Only after that:** prepare Vast.ai training recipe.

## Concrete acceptance before Laura can approve training

- [ ] `C3` fragment explicitly treated as non-runnable salvage.
- [ ] Complete design doc points at this infra review or equivalent blocker list.
- [ ] Gemma v_proj dims recorded as `(in=3840, out=2048)` for layers 29/35/41.
- [ ] Recorder smoke produces target activation files with those widths.
- [ ] Trainer accepts runtime `target_specs` and `target_model_id`.
- [ ] Checkpoint save/load roundtrip works for Gemma metadata.
- [ ] One-step synthetic training smoke passes in `gemma4-mocop`.
- [ ] Vast.ai runbook includes encryption, manifest, copyback, and no-Qdrant boundary.

## Bottom line

The infrastructure plan is viable, but the current codebase is still Qwen-shaped. The next safe step is not training; it is a Gemma recorder/trainer shape-smoke that proves the 2048-wide v_proj heads, runtime target specs, and checkpoint metadata path end-to-end.
