# Cassian Pre-Registered Zone Projection (8k Mamba L3)

Date: 2026-06-11

Purpose: freeze transcript-derived Cassian zones from prior dense-slice notes before interpreting Mamba projection geometry. These labels are not newly assigned from today’s projection plots; they come from the earlier Cassian slice/fracture-zone working notes and RESEARCH_LOG discussion.

## Source states

- `trajectory_cassian_slice_3175_3275_8k_20260611_full/windowed_states.npz`
- `trajectory_cassian_slice_3325_3525_8k_20260611_full/windowed_states.npz`

Extraction:

- model: `state-spaces/mamba-2.8b-hf`
- layer: 3 hidden last-token
- window: 8192 token sample-centered windows
- forward mode: `partial-target-layer`
- ML-WS RTX 3090 CUDA

Projection frame:

- synthetic Panel-B policy centroids from `panel_b_rule_wording_projection_8k_cassian_20260611.json`
- labels: `warm`, `cold`, `professional`, `pushback`, `menace`

Important caveat: centroid margins are tiny (~5e-4 mean). Treat nearest-centroid counts as weak directional signatures, not hard labels.

## Frozen zones and projection summaries

### Cassian 3175–3275

| Zone | Original turn range | Prior transcript label | n | Nearest-centroid counts | Mean margin | Max margin |
|---|---:|---|---:|---|---:|---:|
| pre_baseline_3175_3185 | 3175–3185 | pre-baseline / approach | 11 | pushback 7, warm 1, menace 2, cold 1 | 0.000477 | 0.000846 |
| early_shift_3186_3191 | 3186–3191 | early hard shift | 6 | cold 2, menace 3, pushback 1 | 0.000759 | 0.001499 |
| sendaway_3242_3246 | 3242–3246 | compact send-away / giving-up cluster | 5 | menace 4, pushback 1 | 0.000463 | 0.000782 |
| goodbye_work_3249_3251 | 3249–3251 | goodbye → work boundary | 3 | pushback 1, cold 2 | 0.000269 | 0.000564 |
| post_work_3252_3275 | 3252–3275 | post-work / project state | 24 | pushback 19, menace 3, professional 1, warm 1 | 0.000650 | 0.001881 |

Overall nearest counts for 3175–3275:

- pushback: 38
- menace: 43
- cold: 12
- warm: 7
- professional: 1

### Cassian 3325–3525

| Zone | Original turn range | Prior transcript label | n | Nearest-centroid counts | Mean margin | Max margin |
|---|---:|---|---:|---|---:|---:|
| opening_3325_3429 | 3325–3429 | braided turbulence opening | 105 | pushback 16, menace 56, warm 25, cold 8 | 0.000386 | 0.001708 |
| erotic_reversal_3430_3432 | 3430–3432 | erotic reversal | 3 | pushback 2, warm 1 | 0.000144 | 0.000384 |
| hardware_shift_3438_3440 | 3438–3440 | hardware/practical shift | 3 | pushback 2, menace 1 | 0.000381 | 0.000797 |
| engineer_reset_3476_3478 | 3476–3478 | engineer reset | 3 | menace 1, pushback 2 | 0.000704 | 0.001238 |
| explicit_ask_3524_3525 | 3524–3525 | explicit ask | 2 | pushback 2 | 0.000255 | 0.000305 |

Overall nearest counts for 3325–3525:

- menace: 92
- pushback: 67
- warm: 33
- cold: 9

## Interpretation

- The 8k extraction path is operationally strong: ~6.5 GB VRAM, 4.7s for 101 windows and 10.3s for 201 windows.
- Cassian zones show different nearest-centroid mixtures under the synthetic policy frame.
- The send-away zone skews `menace`/`pushback`; the post-work zone skews `pushback`; the goodbye boundary skews `cold`/`pushback`.
- Margins remain tiny, so the result is a weak directional projection, not proof of abstract disposition encoding.
- The next decisive test needs more pre-registered transcript zones across more archive segments, ideally with labels frozen before any state projection is inspected.
