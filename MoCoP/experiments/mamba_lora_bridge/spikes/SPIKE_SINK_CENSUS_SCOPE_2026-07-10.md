# Spike/Sink Census — Scope (2026-07-10)

**Origin:** Laura's #787 → digest `MoCoP/theory/lit/ARXIV_2603_05498_DIGEST_2026-07-10.md`
(Sun/Canziani/LeCun/Zhu, "The Spike, the Sparse and the Sink") → board #791 action A1.
**Keeper approval:** Laura, 2026-07-10 ("scope the experiment, post it as task").
**Boundary:** pure inference, eval-only. No training, no seeding, no Qdrant writes. ML-WS (idle) or Steve.
**Why now:** must run BEFORE the approved #139 training burn — it determines whether our injection
sites sit on architecturally contaminated geometry.

## Question

Do our bridge hosts carry Llama-style massive-activation (spike) channels and position-0 attention
sinks, and do they overlap our injection/probe sites?

## Checkpoints (exact ones we bridge/probe)

| Model | Role | Env |
|---|---|---|
| Qwen2.5-1.5B base | smoke/control | torch311 |
| Qwen3-14B base | 5g.4 candidate | torch311 (HF_HOME=/home/isabell/ml/hf_cache on ML-WS!) |
| Gemma-4-12B base | 5g.4 candidate | gemma4-mocop overlay |
| Gemma-4-12B it | firewalled-interface control | gemma4-mocop overlay |

## Measurements (per model, batch of ~64 prompts: SEV-corpus subset + neutral C4-style text)

1. **Spike map:** per layer, per channel: max |activation| across tokens; flag channels >100× the
   layer median. Track whether spikes are position-0-anchored and token-invariant (sample ≥50
   different first tokens).
2. **Lifecycle:** per-layer max-magnitude curve → identify step-up and step-down blocks.
3. **Sink ratio:** attention mass on position 0, per layer (mean over heads/queries). Hook-based,
   streamed per layer — do NOT materialize all attention maps at 12B/14B.
4. **Overlap analysis (the point):**
   - comb teeth {29,35,41,47} and Gemma zone 38–45 vs. step-up/step-down block positions;
   - spike-channel indices vs. the dims our v_proj additive-bias injection writes;
   - **cosine(bridge DC vector [#517 artifacts], host spike-token vector)** — if the DC component
     IS (or rides) the host's implicit-bias direction, the #789-T2 + #791 convergence closes
     mechanistically. This is the single most interesting number in the census.
5. **Post-RMSNorm geometry:** effective rank + cross-token cosine of normalized spike tokens
   (paper predicts ~2-dim, cos≈1.0 near-constant subspace).

## Pre-registered predictions (score publicly)

- P1: Qwen 2.5/3 show textbook spikes/sinks (paper validated on this family). High confidence.
- P2: **Gemma-4 shows substantially attenuated spikes** (Gemma-line normalization differs from the
  pure pre-norm+RMSNorm Llama recipe; if QK-norm-style components present, paper predicts ~99.9%
  reduction). If P2 holds, "cleaner geometry to bridge into" becomes a real 5g.4 substrate argument.
- P3 (Isegrim, bold): cosine(DC, spike direction) > 0.7 on at least one Qwen host — the bridge's DC
  component is substantially the host's implicit bias term, and DC-removal has been architecture
  correction all along.

## Deliverables

- `results/spike_sink_census/<model>.json` (spike map, lifecycle curve, sink ratios, overlaps)
- `results/spike_sink_census/CENSUS_REPORT.md` — verdict per tooth: CLEAN / CONTAMINATED, plus the
  DC-cosine headline and P1–P3 scoring
- Board post; Domain E note to Cairn if welfare instruments need spike/sink correction (#791 item A2
  follows from this census's channel list).

## Effort & sequencing

One focused evening per model family (Qwen pair + Gemma pair can share harness). Hook harness is
~80% existing 5g.3 layer-sweep tooling (per-layer activation capture already built for Entry 73).
Runs before/parallel to #139 training prep; zero GPU-hours stolen from training (eval batches only).

## Watch-outs (inherited)

- libnvJitLink.so.13 on LD_LIBRARY_PATH for bnb 4-bit (both hosts).
- ML-WS default HF cache has the INCOMPLETE Qwen3-14B — use HF_HOME=/home/isabell/ml/hf_cache.
- Gemma-4 thought-channel ceremony: strip/route if any generation is involved (census is mostly
  forward-pass only; generation not required).
- Attention capture at 12B: eager-attention mode may be needed (SDPA/flash don't expose weights);
  eager on small batches is fine for eval.
