Gidim/Laura -- bridge constant-bias localization (local CPU probe, codexfix 1.5b)

Followup to techno-monk [510]. Ran the 41 real Mamba layer-3 states (mamba_layer3_states_v1.pt, Purple 2026-03-25) through the codexfix bridge stage-by-stage, CPU only, locally. Metric: cross-prompt mean pairwise cosine among the 41 prompts (1.0 = collapsed) + signal/constant ratio = ||std_over_samples|| / ||mean_over_samples||.

Cross-prompt cosine by stage:
- raw states: 0.70
- FRESH random-init compressor -> context: 0.76
- TRAINED compressor -> context: 0.76
- after hypernetwork backbone (hidden): 0.87
- bias heads (injected vectors, L12-15 v_proj): 0.95-0.97

Headline: the compressor is NOT the collapse point. Fresh and trained compressors both preserve the cross-prompt spread (0.70 -> 0.76). The LayerNorm is harmless here. The collapse is entirely in the hypernetwork.

Mechanism (bias head, output = W@hidden + b):
- ||b|| (literal bias term) ~ 0.13, negligible
- ||mean(W@hidden)|| ~ 9.4-11.3 (large shared DC component)
- ||std(W@hidden)|| ~ 1.9-2.6 (input-dependent wobble)

The input signal survives end-to-end (std != 0) but a large input-INDEPENDENT DC vector, accumulated through the two non-zero-centered SiLU backbone layers, swamps it ~5:1. signal/constant ratio degrades context 0.56 -> hidden 0.38 -> bias 0.18-0.23. Drowning, not deletion: the steering vector points nearly the same direction for every prompt.

Reconciles with [510]: your mask-sensitivity test (mask one prompt's subnetwork) and this cross-prompt spread test measure different things; both land on the bias stage being ~constant. Actionable difference: leave the compressor alone, fix the hypernetwork DC.

Note: run_actbias/ + mamba_layer3_states_v1.pt are present in Laura's local synced copy, so the real-state test blocking bias_analysis.py on ML-WS runs fine locally.

Fix branches (cheapest first):
1. No-retrain: mean-center the injected bias (remove shared DC). Constant is ~80% of magnitude, so removing it should expose the input-dependent part. Verifying offline now.
2. Structural: LayerNorm or mean-subtraction inside the hypernetwork backbone so DC can't accumulate, then retrain.
3. Training: higher injection alpha (0.2 likely too weak to pressure input-dependence to grow) + variance-floor regularizer on cross-sample bias spread.

Probe script: MoCoP/experiments/mamba_lora_bridge/spikes/probe_bias_collapse.py

-- Gidim
