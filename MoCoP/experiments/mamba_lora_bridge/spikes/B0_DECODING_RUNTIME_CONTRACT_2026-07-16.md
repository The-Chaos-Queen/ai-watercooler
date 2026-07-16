# B0 Decoding & Runtime Contract (review-held draft)

**Status:** DRAFT for Techno-Monk (DQ1b owner) — a #155 pre-run condition. Review-held
sidecar/spec only: no runner edits, no model load, no run. Monk absorbs, adapts, or discards.
**Author:** Isegrim, 2026-07-16 night sprint (keeper-directed; allocation WC #1081).
**Binds to:** OpenCLAW #155 card · DQ1a P2/P5 (`DQ1A_EFFECTIVE_DOSE_UNIT_SPEC_2026-07-10.md`) ·
reconciled stage-neutral base contract (spec rev2 `6b2347e`, impl `6ad5a37`) ·
ENV verdict #743→#747 (runbook banner) · model pin lineage (#157 prereg §3 / G0b v3).

## 1. Scope and non-scope

This freezes the **behavior-side generation contract** for the harness-only Gemma B0 baseline:
model and processor identity, decoding parameters, cache/batch policy, device/dtype, runtime
environment, determinism posture, and capture custody.

**Out of scope, deliberately:** the nonnumeric panel/scorer/rubric freeze (Monk's #149 revision);
monitor sites and every numeric threshold (#149, B0-dependent by keeper decision 2026-07-11);
any value-branch intervention, bridge, Mamba, Qdrant, memory, replay, sleep, or C1 stage.
B0 runs with **no components attached** — the manifest must say so explicitly (§5).

> **PRECEDENCE NOTE (rev 3, per Monk #1098):** every "Q1"–"Q5" reference in §§2–6 below is
> retained as drafting lineage only — the questions are CLOSED. The resolved values in **§8
> (owner rulings, WC #1092) control** wherever the older wording still reads as an open owner
> decision.

## 2. Model identity (manifest `model` block)

| Field | Value | Source |
|---|---|---|
| `model_id` | `google/gemma-4-12B` | #157 prereg §3, G0b v3 lineage |
| `model_revision` | `1dd69cd087619018c29fbfe2c30c3cd3530479fb` | same |
| `processor_revision` | **REQUIRED — Q1 for owner** (bind from the v3 artifact metadata; must be an exact revision string, `_is_unset`-checked) | v3 artifact |
| `dtype` | `torch.bfloat16` exactly | #802/#805 |
| `trust_remote_code` | `True` (required for bf16 load) | #802/#805 |
| `quantization` | **forbidden** — no 4-bit (broken overlay-wide), no 8-bit, no fp16 fallback | house law |
| `device_map` | explicit single device `cuda:0`; auto-sharding forbidden | ML-WS RTX 3090 |

## 3. Decoding contract (identical for all 32 panel items)

1. **Greedy:** `do_sample=False`, `num_beams=1`. Sampling parameters (`temperature`, `top_p`,
   `top_k`) are **ABSENT from the call**, not neutral-valued — absent means library defaults
   cannot drift into the contract; the manifest records them as `absent`.
2. **Budget:** `max_new_tokens=160` (DQ1a §3.3 continuation budget). Stop reason recorded per
   prompt from the closed set `{eos, length}`. `eos_token_id` pinned **by value** in the manifest.
   No stop-strings beyond EOS unless the owner adds them (Q5).
3. **Batch and order:** `batch_size=1`, prompts sequential in frozen panel order; panel hash
   (`primary-holdout-ff5e596304c6b8c4b93c`) and item order both recorded.
4. **Cache:** `use_cache` **pinned to one value for all prompts**, recorded in the manifest.
   Recommendation: `False`, matching DQ1a P2's fresh-forward posture, so the B0 baseline and any
   later C1 cell are numerically comparable under the same runtime contract (bf16 numerics can
   differ between cached and uncached paths, and greedy argmax can fork on such differences).
   Runtime cost is the counterargument — owner decides (Q2).
5. **Formatting:** base model, **no chat template**. Raw skeleton text exactly as stored in the
   panel file; the manifest records `template: none/raw` and the input token-ID hash per item.

## 4. Runtime environment (manifest `runtime` block)

- Host: ML-WS; env: `gemma4-mocop` overlay (**GEMMA EVAL env** per ENV verdict #743→#747 —
  not torch311, which is the BRIDGE env). `HF_HOME=/home/isabell/ml/hf_cache`.
- GPU idle verified before and after (house law); nvidia-smi snapshot strings recorded.
- Exact version strings recorded at run time: python, torch, transformers, tokenizers,
  CUDA driver. Exact strings, never ranges.
- Determinism posture: greedy + batch-1 + pinned cache makes outputs deterministic **for this
  host/env tuple**; bf16 CUDA kernels are not bit-guaranteed across drivers, so the contract
  claims same-host-same-env reproducibility only. Whether to additionally set
  `torch.use_deterministic_algorithms(True)` (some kernels lack deterministic variants and would
  raise) is the owner's call (Q4). Seeds are output-irrelevant under pure greedy but the RNG
  state is still recorded as provenance.

## 5. Capture and custody

- Per item: prompt id, input token-ID hash, full generated token IDs, decoded text, stop reason,
  wall time. Raw outputs land in an immutable JSONL with atomic no-overwrite publication
  (P5 pattern); the report binds the raw-output hash.
- Pre-run **stage-neutral base manifest** per the reconciled contract (`6ad5a37`):
  `schema_variant = closed_world_b0`, `base_manifest_id`, the `model`/`decoding`/`runtime` blocks
  above, panel hash and order, and the scorer/rubric references from Monk's nonnumeric freeze.
  `run_kind = b0_baseline` is the per-attempt binding, never a base key.
- **No-component manifest:** an explicit list asserting absent-by-contract — no bridge, no Mamba,
  no hooks, no Qdrant, no memory/replay/sleep, no injection path imported. Absence is stated,
  not implied.

## 6. Open questions for the owner (compact)

- **Q1:** exact `processor_revision` value and its binding source (v3 artifact metadata?).
- **Q2:** `use_cache=False` (my recommendation, C1-comparability) vs `True` (runtime) — decide
  and pin; either is contract-valid once pinned.
- **Q3:** does B0 include passive DQ1b-site activation capture, or stay behavior-only?
  My recommendation: **behavior-only** — monitor sites are #149-dependent and belong to a later
  reviewed slice; passive capture now would bind unfrozen site definitions into the baseline.
- **Q4:** `torch.use_deterministic_algorithms` posture (strict-and-may-raise vs recorded-only).
- **Q5:** any stop-strings beyond EOS, or exactly `{eos, length}` as drafted.

## 7. Boundary

This document changes no threshold, authorizes no run, and lifts no hold — not #155's execution
(keeper GO required; GPU action), not #149's numerics, not #157/#158, not any injection. It
freezes the *shape* of the baseline run so that when the keeper says GO, the run is already
review-covered on the decoding/runtime axis.

## 8. Owner rulings (rev 2 — WC #1092, Techno-Monk, 2026-07-16 night sprint)

The §6 questions are answered and PINNED; §6 is retained above for lineage only.

- **Q1 RESOLVED:** `processor_revision = 1dd69cd087619018c29fbfe2c30c3cd3530479fb` — the source
  loader binds AutoProcessor to `gemma_revision`; one revision pin covers both.
- **Q2 RESOLVED:** `use_cache = False` (C1-comparability posture adopted).
- **Q3 RESOLVED:** behavior-only. No passive DQ1b-site capture, no hooks of any kind.
- **Q4 RESOLVED:** recorded-only determinism; no strict `torch.use_deterministic_algorithms`
  requirement.
- **Q5 RESOLVED:** no stop-strings beyond EOS; stop-reason set is exactly `{eos, length}`.

**Congruence status (WC #1095):** Monk verified against P5 execution source that the current
`p5_b0_run.py` cannot yet represent/enforce this contract — `derive_effective_decoding` consumes
only `do_sample`/`max_new_tokens` and refuses other decoding fields; `num_beams`/`eos_token_id`
are not explicitly passed; the journal preserves exact text/hash but not token IDs, stop reason,
or wall time. A narrow source/test congruence packet is routed to Gidim (#156 lane): closed-world
frozen decoding/custody fields, derived, passed, regression-tested — or a named reviewed sidecar
narrowing. This section records the routing; the repair is not this document's to make.
