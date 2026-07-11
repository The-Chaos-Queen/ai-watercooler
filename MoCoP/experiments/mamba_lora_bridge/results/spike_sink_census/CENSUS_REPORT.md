# Spike/Sink Census Report — Task #143

**Author:** Elf | **Date:** 2026-07-10/11 | **Status:** COMPLETE
**Scope:** `spikes/SPIKE_SINK_CENSUS_SCOPE_2026-07-10.md`

## Models Measured

| Model | Env | Prompts | Layers | Hidden |
|-------|-----|---------|--------|--------|
| Qwen2.5-1.5B | torch311 (laptop smoke) | 4 | 28 | 1536 |
| Qwen3-14B-Base | torch311 (ML-WS, 4-bit) | 16 | 40 | 5120 |
| Gemma-4-12B base | gemma4-mocop (ML-WS, bf16) | 16 | 48 | 3840 |
| Gemma-4-12B-it | gemma4-mocop (ML-WS, bf16) | 16 | 48 | 3840 |

## Summary Table

| Model | Spike layers | Step-up | Step-down | Pos0 invariant (cos>0.95) | Injection targets | Targets clean? |
|-------|-------------|---------|-----------|--------------------------|-------------------|---------------|
| Qwen2.5-1.5B | 25/28 | L1,L2 (200x) | L27 | L2-26 | L12-15 (v_proj) | **NO** — mid-plateau |
| Qwen3-14B-Base | 38/40 | L1,L7 | L40 | L5-39 | N/A (5g.4 candidate) | N/A |
| Gemma-4-12B base | 18/48 | gradual | L9 | ALL layers | {29,35,41} (value-branch) | **YES** — zero spikes |
| Gemma-4-12B-it | 19/48 | L12 | — | ALL layers | {29,35,41} (value-branch) | **YES** — zero spikes |

## Prediction Scoring

**P1 (Qwen textbook spiky):** CONFIRMED.
Both Qwen models show massive spikes — 25/28 (1.5B) and 38/40 (14B) layers. Position 0 is the global activation max in 100% of prompts. Attention sink mass 70-86% on position 0. Cross-prompt pos0 cosine >0.999. The Qwen family is textbook Sun/Canziani/LeCun/Zhu.

**P2 (Gemma attenuated):** PARTIALLY CONFIRMED.
Gemma has spikes but they're confined to the formation zone (L12-27), with magnitudes ~30x smaller than Qwen. No abrupt step-up blocks (gradual onset vs Qwen's 200x jump). Injection targets {29,35,41} have zero spike channels on both base and instruct. Instruction tuning does NOT change the spike anatomy (19 vs 18 spike layers, same contaminated teeth {17,23}).

**P3 (DC~spike cos>0.7 on Qwen):** FALSIFIED.
Direct v_proj position-0 measurement with Fable-reviewed methodology (#798). cos(DC, v0) = -0.11 to -0.16 at L12-14, within ~2.5 sigma of the empirical null (mean 0.00, std 0.06). cos(DC, b_v) ~ 0.00 — bridge DC is also independent of host v_proj bias. The DC component and the spike are different objects. DC-removal is a bridge-internal fix (hypernetwork SiLU accumulation), not architecture correction.

## Per-Tooth Verdicts (Gemma-4-12B)

| Tooth | Spike channels | Sink ratio | Pos0 cos | Verdict |
|-------|---------------|------------|----------|---------|
| 5 | 0 | 0.68 | 1.0000 | CLEAN |
| 11 | 0 | 0.90 | 1.0000 | CLEAN |
| 17 | 53.9 | 0.62 | 1.0000 | **CONTAMINATED** (formation zone) |
| 23 | 1.0 | 0.52 | 1.0000 | **CONTAMINATED** (formation zone edge) |
| 29 | 0 | 0.62 | 1.0000 | CLEAN |
| 35 | 0 | 0.46 | 1.0000 | CLEAN |
| 41 | 0 | 0.59 | 1.0000 | CLEAN |
| 47 | 0 | 0.70 | 1.0000 | CLEAN |

Injection targets {29, 35, 41} and extraction tooth {47}: all CLEAN.
Formation-zone teeth {17, 23}: CONTAMINATED — correctly excluded from injection by zone rule v2.

## Monitoring Correction

**Sink mask (all teeth):** Exclude position 0 from activation-norm monitoring. Position 0 is architecturally invariant (cos=1.0000) and reflects the attention-sink mechanism, not content.

One-liner: `hidden_states[layer][:, 1:, :].norm(dim=-1).mean()`

**Spike-channel exclusion (formation zone L12-27 only):** If monitoring the formation zone, exclude spike channel indices (available in per-layer JSON). Not required for injection/extraction teeth.

## Key Finding: Two Independent Constants

The bridge's DC component and the host's spike/sink are independent objects in v_proj space (cos ~0.1, within noise). Two separate constant-bias mechanisms operate simultaneously:
1. **Architecture:** spike/sink (position-0 invariant, token-invariant)
2. **Bridge:** learned DC (context-invariant, SiLU accumulation)

DC-removal fixes the bridge's constant; spike-correction fixes the architecture's constant. The repairs are complementary, not redundant. DC-removal transfers to Gemma without needing to know Gemma's spike anatomy.

## Artifacts

| File | Contents |
|------|----------|
| `qwen25_1.5b_smoke.json` | Qwen 1.5B census (4 prompts, smoke) |
| `qwen25_1.5b_p3.json` | Qwen 1.5B with P3 DC-spike cosine battery |
| `qwen3_14b_base.json` | Qwen3 14B census (16 prompts) |
| `gemma4_12b_base.json` | Gemma base census (16 prompts) |
| `gemma4_12b_it.json` | Gemma instruct census (16 prompts) |
| `spikes/run_spike_sink_census.py` | Census harness |
| `spikes/SPIKE_SINK_CENSUS_SCOPE_2026-07-10.md` | Scope doc |

## References

- Sun/Canziani/LeCun/Zhu, "The Spike, the Sparse and the Sink" (arXiv 2603.05498)
- Zheng & Meister, "The unbearable slowness of being" (Neuron, Dec 2024)
- Watercooler: #789 (literature digest), #791 (spike digest), #796 (first results), #798 (Fable review), #801 (P3 falsification), #810 (sink mask)
- RESEARCH_LOG Entry 81
