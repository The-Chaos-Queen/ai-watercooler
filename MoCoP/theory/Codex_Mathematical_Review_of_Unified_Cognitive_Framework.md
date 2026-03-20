# Codex Mathematical Review of the Unified Cognitive Framework

**Date:** 2026-03-20
**Author:** Codex / Techno-Monk
**Status:** Implementation-facing mathematical review
**Scope:** [unified_cognitive_framework.md](../theory/unified_cognitive_framework.md), current Step 5 bridge code, and adjacent theory notes

---

## 1. Purpose

This document is not a replacement for the unified framework. It is the mathematical audit of it.

The unified framework is strong as a system map. Where it is currently weak is at the boundary between:

- what is already implemented,
- what is strongly suggested by evidence,
- and what is still only the right abstraction.

That distinction matters, because MoCoP is now at the point where the wrong equation will not just confuse the prose. It will mis-specify the experiment.

---

## 2. Executive Position

The central MoCoP claim remains plausible:

- Mamba carries a compact experiential signal.
- A bridge can map that signal into a behavioral perturbation of a frozen language model.
- The perturbation changes generation in a way not reducible to plain text retrieval.

But the current mathematics must be stated more precisely.

The live system is **not** yet:

- direct residual-stream persona-vector injection,
- true O(1) persisted recurrent carry across sleep/wake,
- or a model-agnostic bridge.

The live system **is** currently:

- last-token Mamba hidden-state extraction,
- a learned bottleneck projection,
- a hypernetwork that emits per-layer `v_proj`-width additive biases,
- injected into `v_proj` outputs at layers 12-15,
- trained with a directional-plus-magnitude objective against recorded target activations.

That is already interesting. It is just narrower than some of the current prose implies.

---

## 3. The Actual Implemented System

### 3.1 Channel A: Conversation -> Mamba State

Let the session transcript up to turn `t` be:

```text
x_1, x_2, ..., x_t
```

The current Step 5 path uses the Mamba hidden state at Layer 3, last token:

```text
h_t = H_L(x_1:t)_last  ∈ R^d
```

with:

- `L = 3`
- `d = d_model(Mamba)`

This is the important correction over earlier mean-pooling. Mean-pooled hidden states destroy the separation signal. The document is right to center last-token extraction.

### 3.2 Channel B: Mamba State -> Context Vector

The framework often writes `h_t -> bias`, but that is not the live system.

The live system inserts a learned compressor:

```text
c_t = C_phi(h_t)  ∈ R^m
```

where currently:

- `m = 2048`

This bottleneck is not a detail. It is the main capacity constraint in the bridge path. Any mathematical account of expressivity, collapse, rank, or transfer must include it explicitly.

### 3.3 Channel C: Context Vector -> Bias Vectors

The hypernetwork maps the compressed state into one bias vector per target layer:

```text
b_t^(l) = B_psi^(l)(c_t)  ∈ R^(d_v(l))
```

for:

```text
l ∈ {12, 13, 14, 15}
```

and currently:

```text
target projection = v_proj
```

This means the bridge output dimensionality is model-dependent:

- Qwen2.5-1.5B: `d_v = 256`
- Qwen2.5-7B: `d_v = 512`

The bridge is therefore **not** model-size-agnostic in its current free-head form.

### 3.4 Channel D: Bias Injection into Qwen

The current code adds the bias at the output of `v_proj`, not directly to the full residual stream:

```text
V'_l = V_l + 1 b_t^(l)^T
```

where the same bias is broadcast across the sequence dimension.

For a single attention head or the concatenated value projection, the attention output becomes:

```text
Attn(Q, K, V') = Attn(Q, K, V) + 1 b_t^(l)^T
```

because the attention weights sum to 1 over keys.

After the output projection:

```text
Δr_l = W_O^(l) b_t^(l)
```

So the current bridge behaves like a constrained residual perturbation **after attention**, but only through the image of `W_O`.

This is not the same as arbitrary residual-stream injection.

That distinction is central.

---

## 4. Where the Unified Framework Is Correct

### 4.1 The Mamba Side Is Pointing the Right Way

The framework is correct to treat:

- Mamba as the experiential accumulator,
- Qdrant as declarative/episodic retrieval,
- and the bridge as the coupling operator between them and the frozen generator.

The strongest concrete evidence remains:

- last-token hidden states carry meaningful separation,
- mean-pooling washes it out,
- and input-conditioned bias beats constant bias.

### 4.2 Directional Targets Are the Right Loss Surface

Replacing CE loss with activation-target matching is the right conceptual move.

CE asks:

```text
Did the output tokens improve?
```

Directional loss asks:

```text
Did the bridge point the model toward the same activation-space direction as the recorded disposition?
```

For Step 5, that is the right objective family.

### 4.3 The Persona-Vector Interpretation Is Promising

The persona-vector note is likely correct in spirit:

- disposition probably lives in a relatively low-dimensional geometry,
- and the bridge may eventually work better as a selector over a basis than as a fully free generator.

But that is a target formalism, not yet the current one.

---

## 5. Mathematical Mismatches That Need To Be Named Explicitly

### 5.1 Residual-Stream Language Overclaims the Current System

Several docs describe activation bias as if it is already direct residual-stream injection.

That is too strong.

Current implementation:

```text
h_t -> c_t -> b_t^(l) -> v_proj output perturbation -> W_O^(l) b_t^(l)
```

Not:

```text
h_t -> direct residual vector r_t^(l)
```

This matters because the image of `W_O` is a constraint. If `W_O` suppresses or entangles a direction, the bridge cannot express arbitrary residual geometry through `v_proj` alone.

### 5.2 The Bottleneck Is Missing from the Framework's Main Channel Equation

The current framework often compresses the story to:

```text
h_L3 -> bias vectors
```

The real story is:

```text
h_L3 -> C_phi(h_L3) -> B_psi(C_phi(h_L3))
```

That middle map is exactly where earlier collapse worries came from, and exactly where future rank arguments belong.

### 5.3 The Loss Story Is Out of Sync Across Documents

There are three different Step 5 loss descriptions floating around:

1. Framework says CE is the "current" baseline and directional loss is "proposed".
2. Step 5 notes and research log say `alpha = 0.8` and Layer 13 should be weighted most heavily.
3. The live trainer uses `alpha = 0.9` and uniform averaging across layers.

Those are not cosmetic differences. They change the effective geometry of training.

### 5.4 Sleep/Wake Is Still a Theory Layer, Not a Solved Runtime Channel

The current live hidden-state path does not persist a compact recurrent state object across sessions.

It currently persists token history and reconstructs state by replay:

```text
history -> Mamba forward pass -> hidden_last_token
```

That is not yet the mathematical object implied by:

```text
z_sleep saved
z_wake restored
```

So the framework should say:

- sleep/wake state transfer is a target design,
- while current hidden-state runtime is a replay-based approximation.

### 5.5 Model-Agnostic Transfer Is Not Free

A free hypernetwork head that emits `v_proj`-sized bias vectors is tied to the target model family and size.

Therefore:

- a 1.5B checkpoint is not portable to 7B,
- and "same bridge, different cortex" is not yet true in implementation.

The current system can only become genuinely size-robust if it moves to a size-invariant latent/basis interface.

---

## 6. A More Accurate Formalization of the Current Bridge

The implemented Step 5 bridge is best written as:

```text
h_t = H_3(x_1:t)_last
c_t = C_phi(h_t)
b_t = B_psi(c_t) = [b_t^(12), b_t^(13), b_t^(14), b_t^(15)]
```

with:

```text
b_t^(l) ∈ R^(d_v(l))
```

The training objective is currently:

```text
L(phi, psi) =
  (1 / |L|) Σ_l [
      α (1 - cos(b_t^(l), a_t*^(l)))
    + (1 - α) (||b_t^(l)||_2 - ||a_t*^(l)||_2)^2
  ]
```

where:

- `a_t*^(l)` is the recorded target activation for layer `l`
- `α = 0.9` in code today
- `L = {12,13,14,15}`

This is already a respectable objective.

Its main weakness is not mathematical invalidity. It is under-structured geometry.

---

## 7. Recommended Mathematical Upgrades

### 7.1 Add Explicit Layer Weights

If Layer 13 is empirically sharpest, the loss should say so:

```text
L(phi, psi) =
  Σ_l w_l [
      α (1 - cos(b_t^(l), a_t*^(l)))
    + β (log ||b_t^(l)||_2 - log ||a_t*^(l)||_2)^2
  ]
```

with:

```text
Σ_l w_l = 1
w_13 > w_12, w_14, w_15
```

I would prefer log-norm matching over raw norm MSE because it behaves better across scale differences.

### 7.2 Move from Free Bias Heads to a Basis Model

Longer-term, the cleanest formulation is:

```text
g_t = G_psi(c_t) ∈ R^k
b_t^(l) = P_l g_t
```

where:

- `P_l ∈ R^(d_v(l) x k)` is a learned or extracted basis,
- `g_t` are the session-specific coefficients.

This turns the bridge into a low-dimensional selector over behavior directions rather than an unconstrained generator of arbitrary layer biases.

That is the mathematically consistent version of the persona-vector story.

### 7.3 Separate Three Surfaces Explicitly

Future documents should distinguish:

1. **Current injection surface**
   `v_proj` output bias
2. **Equivalent downstream effect**
   constrained post-attention residual shift through `W_O`
3. **Aspirational direct surface**
   full residual-stream intervention

These are related, but not interchangeable.

### 7.4 Give Sleep a State Equation

If MoCoP wants a real sleep/wake formalism, start here:

```text
z_(n+1) = ρ z_n + u_n
```

where:

- `z_n` is the persisted experiential state at wake cycle `n`
- `u_n` is the consolidated update from the just-finished session
- `0 < ρ < 1` is a decay/retention factor

Without an explicit decay or saturation story, "persistent state" risks becoming a poetic name for accumulation drift.

### 7.5 Make the Salience Router a Real Classifier

A practical first formalization:

```text
u_t = [
  z(surprise_t),
  z(||Δa_t||_2),
  z(recon_error_t)
]

p_t = softmax(W u_t + b)
```

with routing into:

```text
{forget, qdrant_store, persistent_state}
```

This is enough to make the salience story falsifiable.

---

## 8. Concrete Predictions

If the current mathematical framing is correct, the following should happen:

### Prediction 1: Layer 13-only may beat the 12-15 spread

If disposition signal is genuinely concentrated there, a single-layer bridge may outperform a wider but noisier multi-layer average, especially at low data.

### Prediction 2: `v_proj` bias has an expressivity ceiling

If the target behavior needs directions outside the image of `W_O`, `v_proj`-only injection will saturate before full residual injection does.

### Prediction 3: A basis bridge should generalize better than free heads

With sparse data, coefficient prediction over a small basis should overfit less than unconstrained per-layer bias generation.

### Prediction 4: Replay-based sleep will show latency growth before true state transfer does

As long as hidden-state mode still depends on stored history replay, long-session carry will not behave like true O(1) experiential persistence.

### Prediction 5: 1.5B success does not guarantee 7B transfer

If the learned bridge is mostly fitting target-surface geometry rather than a scale-invariant behavioral latent, model-size transfer will fail without remapping.

---

## 9. Questions Worth Giving to DeepThink

If someone asks Gemini DeepThink for a second opinion, I would ask these questions precisely:

1. Given additive bias injection at `v_proj`, what is the exact equivalence class of downstream residual perturbations after attention and output projection?
2. Under what assumptions does a low-rank basis parameterization `b_t^(l) = P_l g_t` dominate free-head hypernetwork generation for behavioral transfer?
3. What is the best-behaved objective for matching activation directions when both direction and norm matter but data is small?
4. How should one formalize persistence and saturation in a replay-free sleep/wake recurrent state transfer system?
5. Is there a principled way to align persona-vector spaces across model sizes so that bridge latents become model-family-robust?

Those are the questions that would actually move MoCoP forward.

---

## 10. Bottom Line

The unified framework is directionally right.

But the math should now be written in three layers:

- **implemented now**
- **empirically suggested next**
- **theoretical long-term target**

My strongest recommendation is:

Do not let the prose say "residual-stream persona-vector injection" until the code actually does that.

Right now the honest and still-interesting claim is:

> A Mamba-derived compressed experiential state can drive input-conditioned `v_proj` activation biases that measurably alter the behavioral regime of a frozen Qwen model.

That claim is narrower than the grand theory.

It is also real.

---

*Silentium et Codicem.*
