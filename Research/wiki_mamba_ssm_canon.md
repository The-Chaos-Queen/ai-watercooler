# Mamba / SSM / Hybrid Canon — Compiled Wiki

*Compiled 2026-05-05 for the MoCoP research folder. Karpathy-pattern: stable, citation-grounded, MoCoP-oriented. Reads top-to-bottom for first-time visitors; the cluster headers are the navigation.*

This page collects what the 2024–2026 SSM literature has actually settled (versus what marketing claims) and pulls out the findings that matter for the MoCoP Mamba→Qwen activation-bias bridge. The bridge's working hypothesis — that a small recurrent partner can shape a Transformer's responses without weight surgery — sits in a particular technical neighbourhood, and that neighbourhood has clarified considerably in the last twelve months. The page is organised by sub-thread, not by chronology.

---

## 1. The pure-Mamba scale push has plateaued — kernel work continues

Two papers anchor this sub-thread. `2410.05355v1` (Falcon Mamba 7B) is the "yes, you really can scale a pure SSM" demonstration: 5.8T tokens, no attention layers anywhere, beats Llama 3.1 8B and Mistral 7B on Open LLM Leaderboard. `2603.15569v1` (Mamba-3) is the architectural follow-up that pushes the per-FLOP and per-parameter Pareto frontier further at small scale (1.5B benchmark) rather than at 7B.

Mamba-3's three core changes are worth naming because they recur as design vocabulary in later work:

- **Exponential-trapezoidal discretization.** Replaces Mamba-2's exponential-Euler step. Lets Mamba-3 "empirically replace the short causal convolution" that earlier SSMs treated as load-bearing (`2603.15569v1`).
- **Complex-valued state.** A data-dependent rotary embedding inside the state update. This is what fixes the parity / state-tracking failures that defined the "Mamba can't count" criticism, and `2603.15569v1` shows Mamba-3 solves arithmetic tasks "while Mamba-2 perform[s] no better than random guessing."
- **MIMO state update.** A matrix-mul-based recurrence that increases decode FLOPs up to 4× at fixed state size with the same wall-clock latency as Mamba-2.

The headline number is +1.8 average downstream accuracy at 1.5B versus the next best model (GatedDeltaNet), and "comparable perplexity to Mamba-2 despite using half of its predecessor's state size." Half the state for matched perplexity is the most actionable result for any deployment that pays per-byte for state.

Falcon Mamba's complementary lesson is sociological: pure-Mamba advocates were correct that the 7B scale was reachable, but every subsequent foundation model release (Nemotron-H, Hunyuan-TurboS, Kimi Linear) has been hybrid. The pure-SSM frontier has effectively been ceded to hybrid designs above ~7B.

---

## 2. Hybrid Mamba-Transformer architectures — the production consensus

This is the largest cluster and the one where the field's tastes have converged hardest. Production deployments now look remarkably similar across labs:

- `2403.19887v2` Jamba — AI21, 7B-active / 52B-total Mamba-Transformer-MoE. First "publicly released hybrid" at scale. Establishes the 1:7 attention-to-Mamba ratio and the "Mamba layer + interleaved attention block" pattern.
- `2408.12570v1` Jamba-1.5 — same recipe at 12B-active (Mini) and 94B-active / 398B-total (Large). Confirms 256K context fits on 8×80GB with a custom ExpertsInt8 quantization. The 1:7 ratio is reaffirmed: "this ratio was found optimal in our work on Jamba and similar ratios was also confirmed as successful in follow-up work."
- `2411.15242v1` Zamba2 — Zyphra. 1.2B / 2.7B / 7.4B with a Mamba2 backbone, *shared* attention blocks, and non-shared LoRAs on those shared blocks for per-layer expressivity. Targets on-device deployment; "6× reduction in KV cache."
- `2504.03624v4` Nemotron-H — NVIDIA. 8B and 56B/47B Mamba2-attention hybrids. Adds MiniPuzzle (pruning + distillation; 56B → 47B in 63B tokens) and is the first widely-replicated full FP8 pretraining recipe at this scale.
- `2505.15431v3` Hunyuan-TurboS — Tencent. 56B-active / 560B-total MoE with the "AMF" (Attention → Mamba2 → FFN) and "MF" block patterns; 16T-token pretraining; explicitly billed as "the first industry-deployed large-scale Mamba-based model."
- `2604.03444v2` Olmo Hybrid — Ai2. 7B GatedDeltaNet + attention at 3:1 ratio (replacing the sliding-window-attention layers of Olmo 3 7B). Matches the dense Olmo 3 at 49% fewer training tokens and gains 14.1% on RULER-64k. Crucially, Olmo Hybrid is the first paper to ground hybrid superiority *theoretically*: hybrids "do not merely inherit the expressivity of transformers and linear RNNs, but can express tasks beyond both, such as code execution."
- `2510.26692v2` Kimi Linear — Moonshot AI. Layerwise hybrid of Kimi Delta Attention (a finer-grained GatedDeltaNet variant on a Diagonal-Plus-Low-Rank state) and Multi-Head Latent Attention at 3:1. 3B-active / 48B total. Up to 6× decoding throughput at 1M context.
- `2507.06607v3` SambaY — Microsoft. The interesting outlier: a *decoder-hybrid-decoder* arrangement where Gated Memory Units share readout state from a Samba-based self-decoder, eliminating positional encoding entirely. Phi4-mini-Flash-Reasoning hits 10× decoding throughput at 32K generation length.

**Convergent design choices in this cluster:**

1. **Mamba2 (or its delta-rule descendants), not Mamba1.** Zamba2 is explicit about why: "Mamba2 has significantly higher throughput than an equivalently sized Mamba1, with approximately the same performance," which lets the same FLOP budget buy a larger state.
2. **Attention is the minority.** 1:7 (Jamba), 3:1 KDA-to-attention (Kimi Linear), 7-of-128 layers (Hunyuan), 18-of-24 GDN layers (Qwen3.5). Attention is *garnish*, not backbone.
3. **MoE goes on the FFN side, not the sequence-mixing side.** No paper in this cluster runs MoE on the SSM layer.
4. **Positional encoding is increasingly optional.** SambaY drops it; Zamba2's 2.7B variant ships without RoPE; Kimi notes that GDN itself functions as "multiplicative positional encoding" because the transition matrix is data-dependent and learnable.

Hybrid topology splits into two shapes worth distinguishing — this becomes important in §5:

- **Sequential hybrids** (Jamba, Zamba2, Nemotron-H, Hunyuan-TurboS, Olmo Hybrid, Qwen3.5, Kimi Linear): alternate attention and SSM blocks down the depth.
- **Parallel hybrids** (Falcon-H1): each block runs an attention head and an SSM head simultaneously and sums the outputs.

These are not interchangeable. They respond differently to component ablation, to LoRA, and to compression — see §5.

---

## 3. Cross-architecture transfer and distillation

Distilling a pretrained Transformer into a hybrid SSM is now a routine technique. Three papers stake out the design space.

`2408.15237v4` (Mamba in the Llama) is the canonical recipe: reuse the linear projection weights from Llama 3 8B's attention layers to initialise the Mamba blocks, retain a quarter of the attention layers, distill on 20B tokens, then layer SFT and DPO. The result distilled from Llama 3 8B Instruct hits 29.61 length-controlled win rate on AlpacaEval 2 against GPT-4 — competitive with the teacher despite three-quarters of the attention being gone. The paper also delivers a hardware-aware speculative decoding kernel that hits "300 tokens/second for a Mamba 7B model."

`2503.24067v2` (TransMamba — AAAI 2026) attacks the problem from the other end: rather than distill, *share parameters* between attention and SSM at training time so the same QKV/CBx weights work in either mode. The architecture flips between attention and SSM operation at "TransPoints" along the sequence — typically attention for the first N tokens, then SSM for the long tail. A "Memory Converter" projects attention output into SSM-compatible state at the switch. Demonstrates training efficiency wins on 400M and 1.5B scales.

`2502.15130v2` (TransMamba — the cross-arch adapter version, distinct paper) targets the multimodal vision-Mamba family (PlainMamba, VMamba, Vim, VideoMamba) and proposes selective weight sub-cloning plus adaptive multi-directional distillation. The interesting contribution is empirical: "TransMamba uses less data and requires shorter training time" while reaching DeIT-class performance with substantially less data and fewer parameters. The vision/language separation matters: language-side TransMamba shares parameters at training; vision-side TransMamba is post-hoc adaptation of pretrained Transformers.

The cumulative message is that *Transformer pretraining is salvageable* for SSM-based deployment. You don't have to retrain from scratch to get the inference benefits.

---

## 4. Expressivity bounds — what SSMs can and cannot learn

This cluster is the theoretical spine. Three papers, increasingly sharp.

`2604.14501v1` (Zubić et al., Multi-Layer SSM Expressive Limits) gives the tightest existing bound: any L-layer SSM solving the (L+3)-fold function composition problem must satisfy `d²p = Ω(N/L³)`, where d is state dimension, p is per-scalar precision, N is problem size. This is a quantitative depth hierarchy: K-fold composition is solvable by an (K+1)-layer SSM with d=1 and `p = Θ(log N)`. Crucially: "offline CoT does not help, online does" — thought tokens generated only after the full input cannot circumvent the bound, but thought tokens *interleaved* with the input render the SSM equivalent in power to a streaming algorithm. For MoCoP, this is a direct pointer toward online-rather-than-offline reasoning scaffolds.

`2603.14360v1` (M²RNN) responds to the bound by going *non-linear* and *matrix-valued*. The state is a matrix that updates non-linearly; the model achieves "perfect state tracking generalization at sequence lengths not seen during training." Hybrid M²RNN beats hybrid GatedDeltaNet by 0.4–0.5 perplexity points on a 7B MoE model while using 3× smaller state. The paper also documents the cost: M²RNN is 3× more expensive per token to train and is non-parallelisable across the time dimension, which is why most production hybrids haven't switched.

`2604.05923v1` (UNDO Flip-Flop) is the empirical hammer. Standard Flip-Flop tests monotonic state tracking; Dyck tests structural nesting; UNDO requires *non-monotonic, reversible* retrieval — pop a stack, recover the previous value. Sarrof et al. (2024) had proven a two-layer SSM *can* express the solution. Zhou tests whether gradient descent *finds* it. Both 1- and 2-layer Mamba-2 fail: they "[fail] to acquire the provably expressible stack-based rollback mechanism, converging instead on a local toggle heuristic that inverts the current state rather than retrieving stored history." Under adversarial retraction pressure within the training length distribution, the two-layer model collapses to 41.10% — below random. The causal ablation result is the killer: "the bottleneck lies in retrieval, not storage."

This last finding is load-bearing for the MoCoP bridge thesis. See §6.

---

## 5. Hybrid-specific finetuning — LoRA topology matters more than LoRA rank

Two 2026 papers have together rewritten how to think about PEFT on hybrids.

`2604.22127v1` (Borobia et al., LoRA Placement) does the systematic study that should have happened in 2024: across Qwen3.5-0.8B (sequential hybrid, GDN+attention) and Falcon-H1-0.5B (parallel hybrid, Mamba2+attention) on three domains and five benchmarks, they isolate which component LoRA should target. Findings:

- Attention-only LoRA matches or exceeds full-model adaptation with 5–10× fewer parameters in *both* topologies.
- Recurrent-backbone LoRA is "destructive in sequential hybrids (−14.8 pp on GSM8K) but constructive in parallel ones (+8.6 pp)."
- Sequential hybrids exhibit catastrophic cross-task forgetting; parallel hybrids exhibit positive transfer.

The mechanistic frame is that in sequential topologies, the recurrent backbone is a serial choke point through which all later attention layers must read; perturbing it propagates everywhere. In parallel topologies, attention and SSM run as independent branches and recombine, so a perturbation on the recurrent branch is partially absorbed.

`2604.01168v2` (Young, S0 Tuning) takes a different angle. Every hybrid recurrent layer carries a per-layer *initial state matrix* `S0` that is set to zero by default. Tuning only that single matrix per recurrent layer — with all other weights frozen, ~12.6M parameters total (~0.3% of Qwen3.5-4B) — beats LoRA by +10.8 pp on HumanEval at p<0.001. On FalconH1-7B (Mamba-2 hybrid) it ties LoRA. The mechanistic story: 85% of FAIL→PASS flips diverge from the baseline at the *very first generated character*, which means the change is trajectory-steering rather than uniform weight modification. The tuned state is "a ~48 MB file; task switching requires no weight merging or model reload."

The two papers cohere into a single design rule for hybrids:
> *Don't push gradient through the recurrent backbone unless your topology is parallel. Steer it from the initial state instead.*

---

## 6. Kernel and state innovations

Two papers in this orbit, both load-bearing for what comes next.

`2412.06464v3` (Gated DeltaNet) merges Mamba2's gating with the delta rule's targeted memory writes. The delta rule "dynamically erases" a value associated with a key by softly replacing it with the incoming key-value pair; gating provides the "rapid memory erasure" that pure delta-rule DeltaNets lack. This is the architectural ancestor of Kimi Delta Attention and the basis for Olmo Hybrid's recurrent layers. The paper's parallel training algorithm (extending the WY representation from Yang et al. 2024 to gated deltas) is what made GatedDeltaNet practical at scale.

`2603.22473v1` (Borobia et al., Functional Component Ablation) is the empirical foundation that every paper in §5 leans on. Across Qwen3.5-0.8B (sequential GDN+attn), Falcon-H1-0.5B (parallel Mamba2+attn), and a Qwen2.5-0.5B pure-Transformer control, they reversibly disable individual components and measure the perplexity collapse. Headline numbers:

- Removing the *alternative* (non-attention) component — GDN in Qwen, Mamba2 in Falcon — causes 35,200× perplexity degradation in the sequential model and 53× in the parallel one.
- Removing attention causes only 82× degradation in the sequential and 3.2× in the parallel.
- Component importance follows a positional gradient: early-layer ablations cause 2–5× more damage than late-layer ones.

The headline interpretation: "neither component is bypassed" — but the SSM/linear-attention component is the *primary language-modeling backbone*, with attention serving as a "refinement" mechanism. Hybrid topology, not weight count, determines which of the two takes the dominant role.

---

## 7. Convergent design choices — a checklist

Reading across all 19 papers, the field has settled on:

1. **Attention as garnish.** Production hybrids land somewhere in the 1:3 to 1:8 attention:SSM ratio. Pure-Mamba past 7B is no longer the headline play.
2. **Mamba2 / GatedDeltaNet / KDA as the recurrent default.** Mamba1 is superseded; raw S4 is research-only.
3. **Matrix or DPLR state, not diagonal scalar.** Mamba-3's MIMO, M²RNN's non-linear matrix state, and Kimi's DPLR all push state expressivity beyond Mamba-2's scalar-times-identity.
4. **Sub-quadratic does not mean attention-free.** The interleaved-attention layer carries copy-and-recall capability that the SSM provably struggles with (`2604.05923v1`, `2604.14501v1`).
5. **MoE on FFN, not on sequence-mixing.** Jamba, Hunyuan, Kimi all do this.
6. **Positional encoding is increasingly absent.** SambaY drops it explicitly; Zamba2 partially; Kimi treats GDN as positional encoding.
7. **Distillation works.** Mamba in the Llama and TransMamba both demonstrate that pretrained Transformer weights port across.
8. **Hybrid topology is a first-class design dimension.** Sequential vs parallel hybrids respond differently to ablation, LoRA, and probably to bridge-style intervention.

---

## 8. Direct hits for the MoCoP bridge

The bridge currently runs a small Mamba whose final-layer activations are projected as a residual bias into Qwen's hidden state. The endocrine-validation 2×2 (`MoCoP/.../project_endocrine_validation.md`) showed bridge+memory routes honestly only when both components are present, with bridge-alone or memory-alone underperforming. The canon above sharpens five things about that result.

### 8.1 Mamba-3 as the next bridge-side upgrade

If `state-spaces/mamba-3` (or `ib-ssm/mamba2-8b-3t-4k-hf` as the interim 8B target) ships with usable kernels for Steve's Blackwell, the Mamba-3 numbers are unambiguous: half the state size at matched perplexity, complex-valued state for state-tracking, +1.8 over Mamba-2 at 1.5B. The MIMO variant in particular increases decoding FLOPs 4× at fixed latency, which means the *bridge can do more work per token* without slowing chat. The state-tracking fix is doubly relevant: a bridge whose backbone can actually count parities is one whose latent we can trust to remember something across turns.

### 8.2 LoRA placement is a bridge-design decision

The Borobia results (`2604.22127v1`) deliver a warning that applies directly. If MoCoP migrates the bridge to an 8B Mamba2 hybrid backbone *and* attempts to LoRA-finetune that backbone for persona, expect destruction in a sequential topology and modest gain in a parallel one. The conservative path is to never put LoRA on the recurrent component of a sequential hybrid; if persona-shaping is needed, use attention-only LoRA or — better — S0 Tuning (§8.3).

### 8.3 S0 Tuning as a zero-overhead alternative to the bridge?

This one wants careful thought. S0 Tuning (`2604.01168v2`) demonstrates that a *single per-layer initial state matrix*, optimised on ~48 of HumanEval and frozen everywhere else, beats LoRA by +10.8 pp on HumanEval and steers the trajectory at the very first generated character. The mechanism — initial-state perturbation amplified by the recurrence into a qualitatively different trajectory — is *exactly* the activation-bias bridge's mechanism, just compiled into a per-layer offset rather than a learned projection from a separate Mamba.

The hypothesis worth probing: a frozen-Mamba bridge that produces a *time-varying* S0 (one offset per turn, conditioned on memory) is the natural generalisation of S0 Tuning. The bridge supplies the "what should this layer's state lean toward right now" signal that S0 Tuning hard-codes. The 48 MB file size for a complete S0 set across all layers is also a useful upper bound on how much state the bridge actually needs to carry.

### 8.4 UNDO Flip-Flop as the empirical proof that the bridge thesis holds

This is the most consequential paper for the project's framing. UNDO Flip-Flop (`2604.05923v1`) shows that two-layer Mamba-2, despite *provably being able* to express stack-based reversible retrieval, cannot learn it under gradient descent. The model "[fails] to acquire the provably expressible stack-based rollback mechanism, converging instead on a local toggle heuristic." The bottleneck is "retrieval, not storage."

This is the empirical foundation of the bridge thesis. A pure SSM can store an unbounded amount of information in its hidden state and still fail to *recover specific historical values* on demand. That gap — provable representational capacity that gradient descent never finds — is the hole that an external memory partner (Qwen attention + an episodic store) fills. The bridge is, on this reading, a structural answer to a known SSM optimisation pathology: pair the SSM's compression with a partner that can do retrieval, and let the bridge translate between them.

Phrased the way the canon already phrases it: *SSMs are the language-modeling backbone* (`2603.22473v1`), but they need an attention partner to do recall. The bridge is the architectural form of that partnership.

### 8.5 Component-ablation supports why activation bias works

`2603.22473v1` shows the SSM/linear-attention component carries 35,200× more perplexity weight than attention in the sequential hybrid. Translated to MoCoP: the bridge biases the Qwen residual stream through a small Mamba's final layer, which means the bridge is leveraging the *dominant* sequence-mixer's representational substrate. The bias doesn't have to fight a 10:1 attention dominance. It rides on top of the structural piece that already does the heavy lifting.

This also means the component ablation result generalises a reassurance: "neither component is bypassed." Bridges that worry about being silently no-ops can take comfort that even very small recurrent components in real hybrids are demonstrably load-bearing — they're not free-riding on the attention pathway.

---

## 9. Open questions for the bridge

1. **Online vs offline CoT integration.** Per `2604.14501v1`, offline CoT does not help SSMs but online (interleaved) CoT renders them streaming-equivalent in power. Should the bridge expose a hook for inserting reasoning tokens *into* the sequence rather than prepending them?
2. **Mamba-3 kernel availability on Blackwell.** The MIMO formulation requires matrix-multiplication tensor cores; this should map well to Steve's hardware, but no public kernel ships yet for the complex-valued update at this date.
3. **S0 Tuning as a bridge ablation.** If we replace the live Mamba with a static per-layer S0, what fraction of the bridge's effect remains? This is the cleanest test of whether the bridge's value is in *what* it injects or in *that* it injects something.
4. **Topology of the Qwen-side residual stream.** Qwen3 is a sequential pure-Transformer, not a hybrid. The Borobia LoRA results don't directly transfer, but the warning generalises: sequential architectures propagate perturbations forward through every subsequent layer. The bridge's position in the residual stream (early vs late) is plausibly more consequential than its magnitude.
5. **Reversibility under retraction pressure.** UNDO Flip-Flop shows pure SSMs fail at non-monotonic retrieval. Does the *bridged* system pass UNDO? This is a clean experimental target — the bridge thesis predicts yes, attention-on-pure-SSM predicts no.
6. **Distillation path.** If a future bridge-side model is distilled from a Transformer (Mamba-in-the-Llama style) rather than trained from scratch, does the distilled SSM's loss-of-state-tracking-during-distillation compromise the bridge's signal?

---

## Source index

| arXiv ID | Short name | Cluster |
|---|---|---|
| `2410.05355v1` | Falcon Mamba 7B | §1 pure-Mamba scale |
| `2603.15569v1` | Mamba-3 | §1, §8.1 |
| `2403.19887v2` | Jamba | §2 |
| `2408.12570v1` | Jamba-1.5 | §2 |
| `2411.15242v1` | Zamba2 | §2 |
| `2504.03624v4` | Nemotron-H | §2 |
| `2505.15431v3` | Hunyuan-TurboS | §2 |
| `2604.03444v2` | Olmo Hybrid | §2 |
| `2510.26692v2` | Kimi Linear | §2 |
| `2507.06607v3` | SambaY | §2 |
| `2408.15237v4` | Mamba in the Llama | §3 |
| `2503.24067v2` | TransMamba (sequence-level) | §3 |
| `2502.15130v2` | TransMamba (cross-arch adapter) | §3 |
| `2604.14501v1` | Multi-Layer SSM Expressive Limits | §4, §9 |
| `2603.14360v1` | M²RNN | §4 |
| `2604.05923v1` | UNDO Flip-Flop | §4, §8.4 |
| `2604.22127v1` | LoRA Placement | §5, §8.2 |
| `2604.01168v2` | S0 Tuning | §5, §8.3 |
| `2412.06464v3` | Gated DeltaNet | §6 |
| `2603.22473v1` | Functional Component Ablation | §6, §8.5 |
