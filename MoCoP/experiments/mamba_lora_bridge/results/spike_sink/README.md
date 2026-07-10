# Spike / attention-sink census (A1, wc#789 T1 / #791)

Eval-only geometry reconnaissance per digest §6.1 of ARXIV_2603_05498 ("The
Spike, the Sparse and the Sink"). Run by `mocop_spike_sink_census.py` on the
actual bridge hosts. Read-only inference; no training, no state writes.

Question A1 answers: does MoCoP's low-rank v_proj injection at the comb teeth
{29,35,41} land on layers whose residual stream is already dominated by a
massive, near-constant "implicit bias" spike (drown / eigenvector-collision
risk)? And which channels/positions must the Domain-E monitors spike/sink-correct
so they measure the animal, not the architecture?

## Headline: it's ARCHITECTURE, not scale — and Gemma is built to not spike

| host | params | peak \|act\| | profile | mean sink |
|---|---|---|---|---|
| Qwen2.5-1.5B base | 1.5B | **7136** | massive, persistent (L2→27) | 0.65 |
| Qwen3-14B base | 14B | **13376** | massive, persistent (L7→40) | (not measured) |
| Gemma-4-12B base | 12B | **236** | smooth, no spike | 0.49 |

Both Qwen checkpoints carry a massive persistent activation (7136 at 1.5B, 13376
at 14B — scale amplifies it); the 12B Gemma *between* them in size carries none.
Scale is ruled out: the difference is the **architecture**.

The mechanism is in `modeling_gemma4.py`, and it's the paper's suppressor catalogue
implemented in one model: **QK-norm** (`q_norm`/`k_norm` RMSNorm on the head
dimension of Q and K — the paper's single strongest lever, ~99.9% spike
reduction), **sandwich norm** (a `post_attention_layernorm` *and*
`post_feedforward_layernorm` in addition to the pre-norms — normalizing the output
of every sublayer, the paper's ~86% lever), plus **value-norm** and **attention
softcapping**. Qwen uses the standard pre-norm-only RMSNorm recipe and keeps the
spike; Gemma turns on essentially every anti-spike knob the paper identifies, so it
has no massive activation to begin with. Confirmed both ways: by measurement (two
Qwen scales spike, Gemma doesn't) and by mechanism (Gemma implements the exact
suppressors).

**Consequence for the bridge (#788):** Gemma's injection sites {29,35,41} are
geometrically clean — no massive-activation wall to drown a low-rank additive bias.
The census also shows this was *not* guaranteed by substrate choice: on Qwen3-14B,
the same layer indices {29,35} sit *inside* its 13376 persistent-spike band, so a
Qwen-14B bridge would have had a real injection-drowning problem. Gemma's
normalization stack retires that risk. The sink, however, survives on Gemma (0.49) —
spikes and sinks are separable (the paper's point), so Domain-E *attention*
monitors still need position-0 masking, while spike-channel exclusion matters far
less than on the Qwens.

## Runs

### Qwen2.5-1.5B base — DONE (`qwen25_1.5b_base.json`)
Overlay `gemma4-mocop` (transformers 5.10.0.dev0), bf16, 12 prompts, 28 layers.
The paper's own host family; this validates the instrument and reproduces the
mechanism on a real MoCoP-relevant checkpoint:

- **Spike lifecycle:** step-up @ L2 (×228 magnitude jump), step-down @ L27
  (×28 fall), spike-active band [2, 27] — nearly the whole stack carries it.
- **Peak residual |activation| = 7136** (paper predicts O(1000s) ✓).
- **Spike channels @ L6: [408, 520, 940, 609, 286]**, position-0
  token-invariance cosine = **0.9999** across prompts — the "implicit,
  input-invariant bias parameter" claim, confirmed on our host: these channels
  hold a near-constant vector independent of content.
- **Mean position-0 attention (sink) ratio = 0.65** — a very strong sink (paper
  reports ~42–46% on their 7B models; this host sinks harder).
- Injection-overlap N/A: the {29,35,41} teeth are the 48-layer Gemma sites; on
  28-layer Qwen-1.5B they are out of range (its bridge injection lived at L12–15).

Takeaway: any monitor reading activation norm or position-0 attention on Qwen is
reading a ~7000-magnitude near-constant spike + a 0.65 sink unless it masks
position 0 and excludes the spike channels. This is the §6.2 correction, now with
concrete channel indices to exclude.

### Qwen3-14B base — DONE (`qwen3_14b_base.json`)
bf16 (CPU-offloaded), 12 prompts, 40 layers. The scale control for the
architecture-vs-scale question — a Qwen at ~Gemma size.

- **Peak residual |activation| = 13376** — a massive persistent spike, *larger*
  than the 1.5B's (scale amplifies the spike within the family), step-up @ L7,
  step-down @ L40, band [7, 40].
- Spike channels @ L21 [731, 2994, 1016, 2863, 5020], token-invariance cosine
  0.9999 — same implicit-bias signature.
- **Injection overlap (real, on this host):** layers {29, 35} sit *inside* the
  spike band at magnitude 13376. This is the concrete counter-example: had 5g.4
  selected Qwen3-14B, the comb teeth would land in a persistent 13k spike and the
  drowning risk A1 checks for would be live. (Attention/sink not captured this
  run — spike census only.)

Together with the 1.5B, this is the scale control: Qwen spikes at both 1.5B and
14B; Gemma (12B, between them) does not. Architecture, not size.

### Gemma-4-12B base — DONE (`gemma4_12b_base.json`)
Overlay `gemma4-mocop` (transformers 5.10.0.dev0), bf16, 12 prompts, 48 layers.
This is the load-bearing run — it carries the actual injection teeth {29,35,41}.

**Loader note (the real fix; an earlier flag of mine was wrong).** Gemma-4-12B is
a `gemma4_unified` **remote-code** model: its weight converter ships *with the
checkpoint* (the "gemma4 module"). Loading needs `trust_remote_code=True`;
without it, transformers falls back to its built-in class whose main-branch MLP
rename drops `down_proj` and raises a conversion `RuntimeError`. This is NOT an
env regression — the overlay was fine the whole time. The bakeoff
`run_base_improv_bakeoff.load_model` lacks the flag (that's why it failed);
`spikes/run_gemma_layer_sweep.py` and Monk's gemma smoke have it. Also:
`trust_remote_code` + the remote converter is **incompatible with bnb 4-bit**
(the quant path uses the built-in conversion), so Gemma runs **bf16**
(`--no-quant`), which is what `capture_forward` now does.

Finding — Gemma is a *different animal* from Qwen:

- **NO massive-activation spike. SMOOTH profile: peak/median = 1.98×**, peak
  residual |activation| = **236** at L25 (vs Qwen's 7136). The residual grows as a
  gentle ramp (L13→L25) and tapers; there is no sharp step-up/step-down block.
  Gemma's architecture (norm/attention variant) suppresses the spike the paper
  and Qwen show.
- **The injection teeth are geometrically clean:** L29/L35/L41 carry residual
  |act| of only **130 / 138 / 48** — ordinary stack magnitude, no near-constant
  spike wall. A low-rank additive bias at these layers is **not** competing with a
  dominant implicit-bias vector. This retires the injection-drowning risk A1 was
  built to check: it does not apply to Gemma. (The Qwen prior — "step-down is
  late, so teeth sit inside the spike band" — was a wrong extrapolation; Gemma has
  no spike band.)
- **But the attention sink survives: mean position-0 ratio = 0.49** (L29 0.62,
  L35 0.43, L41 0.59). This is the paper's *separability* point made concrete on
  our target: Gemma killed the spike but kept the sink. So Domain-E monitors that
  read attention still need position-0 masking on Gemma — while spike-channel
  exclusion matters far less than on Qwen (peak 236, not 7136).
- Near-constant channels still exist ([1750, 292, 260, 3607, 402] @ L17,
  token-invariance cosine 1.0) but at modest magnitude.

**Consequence for the #788 training run:** the injection geometry on Gemma is
clean — no spike interference at the teeth — which is a *green* signal for the
bridge design, not the blocker my earlier post feared.

## Attention capture note
Attention (the sink) needs `attn_implementation="eager"` (SDPA/flash return no
weights) and, for Gemma, the bf16 + `trust_remote_code` path above (eager is
incompatible with the 4-bit conversion). `--no-attn` runs spike-only (the primary
A1 magnitude metric) if a host refuses eager.
