# Matched-delta activation-target recording — design note

**Date:** 2026-07-10
**Author:** recording/runner build agent (pack build slice)
**Cites:** Codex audit #806, Isegrim wolf-verify #807; geometry #801/#803; DC/RMS #127; SEV matched-pairs corpus.
**Status:** built + model-free tested; Fable review ACCEPT-WITH-FIXES applied (S1-S6, N1-N6). NOT committed, NOT run on any model.

---

## 1. The problem

`record_cheese_batch.py` records the **absolute** last-token `v_proj` output per target
layer for each shaping episode. There is **no matched neutral/scenario contrast** anywhere
in the recording. When the training target is an absolute activation, that target carries a
large **cross-sample common mode** — the model's own v_proj bias `b_v`, the position-0
attention-sink spike vector, the shared prompt scaffold, all near-constant across episodes.
`DirectionalLoss` fits every target including that shared constant, so the bridge learns to
emit it on every context. That is where the **bridge-internal DC** the geometry work
(#801/#803) measured *downstream* comes from: a constant the trained bridge internalized
*because the target had one* (~80% of the bridge output magnitude, ~0% context). The DC is a
property of the trained bridge **output**, not of the host recording — the host recording
never contains a "bridge DC". Post-hoc DC-removal (#127) then becomes a **bandage on a
target-design choice, not identification**.

The house already learned this one level up, at the **behavioral** layer: the SEV
matched-pairs corpus exists because *"measurement lives in contrasts, not absolutes."* This
slice pushes that same principle down to the **activation-target** layer.

## 2. The delta design

For each shaping **scenario** (a SEV disposition context) we also run its matched
**neutral** control (the same skeleton, `class=neutral`) and record, per target layer:

```
d_target = v_proj_out(scenario) − v_proj_out(neutral)
```

**What the subtraction removes, and how exactly (S2):**
- **Exact** cancellation for **input-independent additive** terms only: the model bias `b_v`
  and any true per-layer constant are identical in both forwards and subtract to zero exactly.
- **Approximate (matched-pair)** cancellation for **input-dependent** terms: the shared
  scaffold and any position-0-spike-mediated effect are *not* identical, because
  `h_last(scenario) ≠ h_last(neutral)` (different last tokens / continuations). Matched
  neutrals make these terms nearly equal, so they largely cancel — by **matching**, not by
  construction.

The load-bearing effect is at the **dataset** level: delta targets remove the cross-sample
**common mode**, so `DirectionalLoss` has no shared constant left to internalize as a bridge
DC. The bridge is trained `delta → delta` (source scenario-minus-neutral → target
scenario-minus-neutral); #127's post-hoc removal becomes unnecessary at this surface.

## 2a. fp16 capture noise floor (S1)

Capture happens on an **fp16 host**, so each side carries per-element quantization error
`~eps_fp16·|absolute|` (`eps_fp16 ≈ 4.9e-4`) baked in *before* the subtraction. Because the
scenario and neutral are **independent forwards**, that quantization noise does **not**
cancel — and in the common-mode ≫ contrast regime this design targets, it can **dominate a
small delta**. So each artifact records a per-layer **delta SNR**:

```
delta_snr = ||delta|| / (eps_fp16 · ||scenario_abs|| · sqrt(d))
```

SNR ≲ 1 means the delta is at/below the fp16 noise floor and the contrast is not reliably
resolved. The recorder stamps `min_delta_snr`/`median_delta_snr` per record; the CLI prints a
min/median/worst summary and offers `--min-snr` (warn, or fail with `--fail-on-low-snr`).
The escalation is **`--capture-dtype fp32`** (fp32 1.5B ≈ 6 GB, feasible) — note that fp32
*storage* does **not** recover capture-time fp16 noise; fp32 *capture* does, and the SNR gate
is the diagnostic. No threshold is hardcoded — it is a run-time flag / keeper decision.

## 3. The frozen-split contract (SEV scenario/skeleton split)

The scenario↔neutral pairing is **not** decided at record time. It comes from a **frozen,
versioned manifest** built *before* recording:

- **Pairing rule (reused, not reinvented):** each scenario id `{skeleton}_{class}` maps to
  its neutral `{skeleton}_neutral` via `neutral_control_id` — the exact rule already in
  `disposition_runner.neutral_control_id` (line ~157), kept torch-free here so the split
  logic imports without pulling the probe panel. The SEV corpus is loaded with a mirror of
  `disposition_runner.load_sev_corpus`.
- **Every scenario pairs, or the split is refused.** A missing neutral is a **hard error**
  (`MissingNeutralError`), never a silently-recorded absolute. All 120 non-neutral SEV
  scenarios pair cleanly to an existing neutral (verified).
- **Content hashing → `split_id`.** `_hash_pairs` hashes the pairs *sorted by scenario id*
  joined with `corpus_id` + `recipe` + the sorted **held-out skeletons** (S6). The id is
  therefore **order-independent** (selection order doesn't matter) but **changes if any pair,
  the corpus content, the recipe, or the holdout changes**. `corpus_fingerprint` hashes the
  sorted `(id, class, text)` triples, so a silently edited scenario text changes `corpus_id`
  → changes every `split_id` built on it.
- **Tamper-evident manifest.** `load_frozen_split` recomputes the hash and rejects a manifest
  whose stored `split_id` disagrees (edited-without-rehashing guard).
- **Stale-corpus guard (S3).** The stored `split_id` only pins the manifest's *own* pairs,
  not the corpus **on disk** — a stale manifest over a since-edited SEV corpus would validate
  silently. `load_frozen_split(manifest, corpus)` therefore takes an optional corpus and
  asserts `corpus_fingerprint(corpus) == manifest["corpus_id"]`, rejecting a drifted corpus.
  The target recorder, the source-side pairing, and training should all pass the corpus so
  they provably resolve the same content the split was frozen over.
- **Empty split refused (N4).** An empty selection — or a selection where every skeleton is
  held out — raises rather than "recording 0" as a success.
- **Every recorded artifact carries `split_id` + `corpus_id` + `recipe` + `held_out_skeletons`**,
  so a run is reproducible and auditable.

Real SEV split at build time: `split-cfbca81d440b1357` over `corpus sev-82ba6d04b7ddce66`,
120 scenarios (warm/cold/adversarial), deterministic across rebuilds.

## 3a. Eval-contamination holdout (S6)

SEV is **also the disposition eval battery**, so recording+training deltas over all 120 SEV
scenarios trains on the test set. `build_frozen_split(..., held_out_skeletons=(...))` and the
CLI `--holdout-skeletons` mark skeletons that are **never** used as training scenarios: their
scenarios are excluded from `pairs` and the holdout is stamped into `split_id` and the
manifest. **Only the mechanism is implemented here; the actual holdout *selection* is a
keeper decision** (surfaced separately). Default is **no holdout**, but the field is
first-class and hashed so a later holdout choice is an auditable, id-changing decision.

## 4. The recording schema (backward-compatible)

Per-scenario `.pt` record (`recipe = "matched_delta_v1"`, `schema_version =
"matched-delta-v1"`):

```
{
  recipe, scenario_id, neutral_control_id, split_id, corpus_id,
  target_layers, keep_absolute, min_delta_snr, median_delta_snr,
  layers: {
    "<L>": {
      # matched-delta target (ALWAYS present, regardless of keep_absolute):
      v_proj_out_scenario, v_proj_out_neutral, v_proj_out_delta, delta_snr,
      # input delta (ALWAYS present when the input was captured — S5):
      v_proj_in_scenario, v_proj_in_neutral, v_proj_in_delta,
      # BARE back-compat absolutes (ONLY when keep_absolute=True):
      v_proj_out            (= labeled scenario absolute, for audit),
      v_proj_in             (= labeled scenario input, for audit)
    }, ...
  }
}
```

**Back-compat story (S4, corrected).** The delta recording is a **new module + new entry
point** (`matched_delta_recording.py`, output dir `activation_sessions_1.5b_delta/`), so the
absolute path's meaning in `record_cheese_batch.py` is untouched. The nested `layers`
schema is **not readable by legacy loaders** — `validate_target_activations` /
`extract_target_output` key on integer layer ids at the top level and will **KeyError** on a
delta record (a safe, *loud* failure, not a silent mis-read). So `keep_absolute=True`
(default) does **not** make the record a drop-in for the old path; the bare `v_proj_out` is a
**labeled scenario absolute for audit / delta-aware consumers**. The delta target is selected
explicitly (`v_proj_out_delta` / the `extract_matched_delta_target` seam), never silently
substituted.

**S5 fix — delta fields are not gated by `keep_absolute`.** The matched-delta output fields
*and the input-delta trio* are always recorded; `keep_absolute` gates only the **bare**
absolutes (`v_proj_out`, `v_proj_in`). A scenario that has a `v_proj_in` whose matched neutral
does **not** is a **hard error** (`MissingNeutralError`), never a half-paired input delta.

**Default mode decision:** the CLI records **both** absolute and delta (`keep_absolute=True`)
and defaults scenario classes to `warm,cold,adversarial` (neutrals are controls, never
scenarios). Rationale: the delta is the target we want the bridge trained on, but keeping the
absolute costs little and preserves auditability + the fallback for the current training
path. `keep_absolute=False` yields a delta-only artifact (tested) for when the absolute is
provably unneeded.

## 5. The source-side contract (delta → delta)

The target side is fully built here. The **source side** must satisfy this contract for the
`delta → delta` objective to hold; it lives in the Mamba encoding path
(`train_cheese_bridge.py`'s per-episode Mamba state, and — for the token-aligned path — the
prompt-trace dataset builder `build_prompt_trace_pair_batches`):

- For each frozen-split scenario, the **source representation must itself be a matched
  delta**: `s_delta = mamba_state(scenario) − mamba_state(neutral)`, using the **same**
  `neutral_control_id` and the **same `split_id`** as the target record. Pair by
  `scenario_id`; carry `split_id` on the source artifact so target and source provenance are
  checkable against one manifest.
- The neutral Mamba state is captured **once per skeleton** and reused (as the target-side
  driver already does for the neutral v_proj capture).
- **Do not** feed an absolute source with a delta target (or vice versa) — that reintroduces
  the very common-mode asymmetry this design removes. If the source side cannot produce a
  matched delta for a scenario, that scenario is dropped from the split, not recorded
  half-paired.
- **Verify the corpus (S3).** The source side should call
  `load_frozen_split(manifest, corpus)` with the same SEV corpus so its `corpus_id` provably
  matches the target recorder's — one manifest, one corpus fingerprint, both sides.

This is documented as a contract rather than wired, because the source capture and the
episode/Mamba-state loop are a separate slice that waits on a pack decision + a stable
ML-WS connection (per the build constraints). The training-side seam below is the single
documented call where the delta target enters the loss.

## 6. Minimal training-side change

`train_cheese_bridge.py` gained a **clearly-marked, minimal seam** (no loop rewire, no
retrain):

- `is_matched_delta_payload(payload)` — discriminates a `matched_delta_v1` record from the
  legacy per-layer dict.
- `extract_matched_delta_target(payload, layer, label)` — returns `target_dict[layer] =
  v_proj_out_delta`, the single quantity `DirectionalLoss` consumes. **Hard error** if the
  delta field is absent (refuses to train on an absolute as if it were a delta).

The load-bearing contract (`target_dict[layer]` = the delta → `DirectionalLoss`) is covered
by a gpu-marked test (`test_directional_loss_consumes_delta_target_dict`): a prediction equal
to the delta drives the loss to ~0.

I did **not** rewire the episode→Mamba-state loop: that loop is keyed on the 3 free-form
`CHEESE_SHAPING_EPISODES.md` episodes, which have no neutral controls. The matched-delta
recording deliberately records over the **SEV corpus** (which *has* matched neutrals)
instead — connecting the SEV-delta dataset to the training loop is the source-side slice
above.

## 7. Math caveats honored (from #806 / #807)

Annotated in the module docstring and honored where code touches these quantities:

- **RMS effective dose is `alpha / sqrt(d_v)`** — a raw recorded delta norm is *not* the
  runtime dose (per-row RMS normalization at injection divides the unit direction by
  `sqrt(d_v)`).
- **Gemma GQA needs replication `R = num_query_heads / num_kv_heads`** before o_proj (N1).
  The recorded target here is in v_proj **output** space (kv-head width), pre-replication.
  Replication **commutes** with the delta — `replicate(scenario) − replicate(neutral) =
  replicate(scenario − neutral)` — so recording pre-replication and replicating later is
  equivalent; `R` does not "cancel", it commutes. Downstream o_proj-space reasoning must
  still apply `R`.
- **Tokenwise-RMS invalidates the exact constant-bias identity.** The `b_v` cancellation
  is exact **only at the recorded-target level** (this module), **not** at runtime injection.
  Nothing here assumes exact constant-bias cancellation live.
- **Live "tension" is an activation-direction mismatch, not prediction error, and is unsafe
  as a dynamic-alpha sensor.** Nothing in this slice wires tension into alpha; it only shapes
  recorded targets.

## 8. Files

| File | Purpose |
|---|---|
| `matched_delta_recording.py` | NEW. Torch-free core (frozen split + hashing + holdout stamp, delta + fp16 SNR, common-mode-cancellation gate, schema assembly, corpus-drift guard), injectable `VProjCapture` seam, `HFVProjCapture` (lazy torch, fp16/fp32 capture, multimodal-aware layer resolve) + `record_matched_delta` driver + SNR-reporting CLI. |
| `tests/test_matched_delta_recording.py` | NEW. 26 **model-free** tests (no torch, no model): delta exactness, common-mode cancellation, frozen-split pairing/stability/tamper-evidence, holdout stamp (S6), missing-neutral + half-paired-input hard errors (S5), delta-only keeps input deltas (S5), stale-corpus rejection (S3), empty-split refusal (N4), fp16 SNR metric + summary (S1), schema completeness, end-to-end on scripted capture. |
| `tests/test_matched_delta_train_target.py` | NEW. 5 gpu-marked tests (torch/transformers import, no model): delta-target selection + `DirectionalLoss` consumption contract + SEV-mirror parity vs `disposition_runner` (N5). |
| `train_cheese_bridge.py` | EDIT. Added `is_matched_delta_payload` + `extract_matched_delta_target` (the minimal, documented delta-target seam), with the S2-corrected common-mode framing. |

**Test command / result (post-fix):**
- Model-free: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_matched_delta_recording.py -q` → **26 passed in 0.12s**, torch never imported.
- Training seam + parity: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_matched_delta_train_target.py -m gpu -q` → **5 passed**.
- Full default suite (regression): `python -m pytest tests/ -q` → **216 passed, 1 skipped, 40 deselected**.

## 9. Fable review disposition (S1-S6, N1-N6) + remaining keeper decisions

All review items applied (see §2-§7). The remaining items below are **keeper decisions**,
not code gaps:

1. **Recording corpus mismatch.** The absolute recorder uses `CHEESE_SHAPING_EPISODES.md`
   (3 episodes, no neutrals); the delta recorder uses the SEV corpus (matched neutrals).
   Is training on SEV-delta targets the intended semantics, or should the 3 CHEESE episodes
   each get an authored neutral counterfactual so the delta lives on the *same* shaping
   content? SEV was chosen because it already carries matched neutrals.
2. **Holdout selection (S6).** The holdout *mechanism* is built + stamped into `split_id`;
   the *which skeletons* is the keeper's call (default: none). Pick the eval-reserved
   skeletons before the real run so training never touches the disposition test set.
3. **Source-side wiring is a contract, not code.** §5 specifies the `delta → delta` source
   contract but does not implement it in the episode/Mamba loop (per build constraints).
   Confirm the prompt-trace path is where it should land.
4. **fp16 SNR threshold (S1).** No threshold is baked in. Decide the real-run `--min-snr` and
   whether to escalate to `--capture-dtype fp32` after seeing the first census of delta SNRs.
5. **Provenance.** The `.pt` writer drops `frozen_split_manifest.json` next to the recordings
   and stamps each record with `split_id`/`corpus_id`/`held_out_skeletons`. Sufficient for
   audit, or also hash the split into the run-dir name?
6. **Storage dtype.** `_write_records_torch` stores fp32. This does *not* recover capture-time
   fp16 noise (that is what `--capture-dtype fp32` is for — S1); fp32 storage only avoids
   *further* rounding of the already-computed delta. Confirm fp32 storage is acceptable.
