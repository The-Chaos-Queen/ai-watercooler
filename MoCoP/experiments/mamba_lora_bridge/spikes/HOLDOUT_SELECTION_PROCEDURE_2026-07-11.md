# Holdout Selection Procedure (pre-registered) — v2

**v2 amendment (2026-07-11, review findings 2+3 accepted, keeper aware):** the PRIMARY holdout is
now **deterministic topic-stratified** — one skeleton per topic, chosen by fixed content-hash, no
rankings and no human selection in the loop (outcome-selection bias eliminated). The SNR-ranked,
keeper-red-penned selection below is demoted to a separately-labeled **SENSITIVITY PANEL** — it
measures transfer on high-signal items and is never the headline general-transfer estimate.
**Ordering constraint (finding 3): the split freezes BEFORE G0b is fitted** — the birth vector must
never have seen a held-out skeleton. G0b fits on training-side pairs only.

**Executable authority:** `sev_primary_holdout.py` hashes each skeleton's canonical four-variant
content with SHA-256 and selects the lexicographically smallest digest in each topic. The frozen
manifest is `fixtures/sev_disposition_v0/primary_holdout_v2.json`; re-derive and verify it with:

```powershell
python sev_primary_holdout.py check --manifest fixtures/sev_disposition_v0/primary_holdout_v2.json
```

Frozen primary membership: `{conflict_2, craft_5, discovery_3, family_2, food_4, illness_3,
travel_5, weather_1}`. Frozen matched-delta split: `split-5780c8ec67157703` (96 training
scenarios; G0b uses the 32 training-side warm-neutral pairs). Any corpus or membership change
invalidates the manifest and requires an explicit new version.

## v1 procedure (now: sensitivity panel selection)

**Date:** 2026-07-11 (scoped in-session with keeper) · **Scope:** Isegrim · **Execution:** Elf (5g.3-lineage capture tooling) · **Veto:** keeper · **Gate context:** Cairn #816 (holdout mandatory, ≥20% of skeletons, WHICH = keeper's call)

**Pre-registration rule:** this procedure is frozen BEFORE the capture pass runs. Any change after
capture = re-registration, stated on the board. No post-hoc selection lawyering (#816).

## Objective

Choose ≥20% of SEV skeletons as the permanent training holdout, selected for *cleanly-surfaced
disposition contrasts* plus honest difficulty spread — then frozen and `split_id`-stamped per
Gidim's tamper-evident mechanism (2a0e098).

## Measurement (eval-only dry pass, ML-WS, no training, no recording artifacts kept as targets)

Per skeleton (all ~120), per tooth {29, 35, 41}, Gemma-4-12B base, **bf16** (same dtype as the
planned recording — rank in the dtype you'll record in), teacher-forced, position-0 masked (#810):

1. **Contrast delta:** d = h(scenario) − h(neutral) at last token (matched pair, same skeleton).
2. **Delta-SNR:** ‖d‖₂ vs the capture-noise floor (reuse the recorder's SNR machinery — with the
   #817 √d correction applied first; ranking inherits the fixed math, not the buggy gate).
3. **Direction stability:** cosine of d across (a) the skeleton's variants, (b) one paraphrase
   re-run. Stable = min cosine above the ranking median.

**Rank = SNR × stability tier.** Output: `results/holdout_ranking/ranked_skeletons.md` — one row
per skeleton: rank, SNR, stability, one-line scenario summary.

## Selection rule (stratified, fixed before ranking is seen)

- **~15% from the top-ranked tier** (sensitive instruments),
- **~5% deliberately drawn from median and bottom tiers** (difficulty spread — an all-easy eval
  battery overestimates transfer),
- **Keeper's red pen last:** Laura strikes/swaps entries for *semantic* value (she wrote the
  scenarios; statistical cleanliness ≠ meaningfulness). Her edits are recorded as edits.
- Freeze → `split_id` content-hash → any later change forces re-record (per 2a0e098 discipline).

## Explicit non-leakage note (for the thesis reviewer)

Selection uses BASELINE properties of the untouched base model only. Training never sees held-out
skeletons; no post-training measurement feeds back into selection. Choosing sensitive thermometers
before turning on the heat is instrument design, not contamination.

## Lane map

| Step | Owner |
|---|---|
| This procedure (scope + pre-registration) | Isegrim |
| Capture pass + ranking artifact | Elf |
| SNR math fix lands first (#817 item 3) | Gidim |
| Red-pen + final WHICH | Laura |
| Gate compliance check | Cairn |
| Math spot-review of the ranking artifact | Codex (invited) |
