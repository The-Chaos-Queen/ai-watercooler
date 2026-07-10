# Spike / attention-sink census (A1, wc#789 T1 / #791)

Eval-only geometry reconnaissance per digest §6.1 of ARXIV_2603_05498 ("The
Spike, the Sparse and the Sink"). Run by `mocop_spike_sink_census.py` on the
actual bridge hosts. Read-only inference; no training, no state writes.

Question A1 answers: does MoCoP's low-rank v_proj injection at the comb teeth
{29,35,41} land on layers whose residual stream is already dominated by a
massive, near-constant "implicit bias" spike (drown / eigenvector-collision
risk)? And which channels/positions must the Domain-E monitors spike/sink-correct
so they measure the animal, not the architecture?

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

### Gemma-4-12B base — BLOCKED (infra, not the census)
The load-bearing run — it carries the actual injection layers {29,35,41} and the
zone 38–45 — is **blocked by a transformers 5.10.0.dev0 weight-conversion
regression**, independent of this script:

- `AutoModelForImageTextToText.from_pretrained('google/gemma-4-12B', ...)` raises
  `RuntimeError: ... issues during automatic conversion of the weights`, with
  `model.language_model.layers.{0..47}.mlp.down_proj.weight | MISSING` across all
  48 layers.
- **The proven bakeoff `run_base_improv_bakeoff.load_model` fails identically** —
  so this is a pre-existing overlay regression, not the census code, and it
  affects the whole Gemma path (the runner, the training run, this census).
- Same symptom on the 4-bit path; not attention-capture-related (fails with
  `--no-attn` too).

**Implication flagged to infra (Monk/Isegrim):** the #788-greenlit training run
loads Gemma-4-12B through the same path and is likely blocked by the same
regression. Suspected cause: the overlay's transformers moved off the pinned
commit (summary recorded `b70d02f`); pinning back is the first thing to try.

Once the loader is fixed, rerun:

    python mocop_spike_sink_census.py --model google/gemma-4-12B --quant 4bit \
        --no-attn --out results/spike_sink/gemma4_12b_base.json

Prior from Qwen: the step-down is a late block, so on 48-layer Gemma the teeth
{29,35,41} plausibly sit *before* step-down — i.e., inside the spike-active band —
which is exactly the overlap A1 is meant to confirm or rule out. Open until Gemma
loads.

## Attention capture caveat
`--no-attn` is the robust mode. Attention capture needs
`attn_implementation="eager"` (SDPA/flash return no weights); the sink ratio for
Qwen above used eager successfully. If a host refuses eager under quantization,
run spike-only (the primary A1 metric is the magnitude lifecycle) and capture the
sink separately.
