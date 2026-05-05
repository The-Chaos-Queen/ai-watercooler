# Hybrid Translator MVP - 2026-04-08

## Why This Exists

The current bridge path:

`Mamba Layer 3 hidden-last-token -> MambaStateCompressor -> ActivationBiasHypernetwork -> Qwen v_proj bias`

is now locally diagnosed as too blunt.

What we know:

- Mamba geometry is real and rich.
  - `costume_vs_soul` proved distinct neighborhoods for baseline / card / genuine / roleplay.
- The current bridge flattens that structure.
  - mask ablation: persistent / variable / middle partitions do not materially change behavior
  - pipeline diagnosis: raw differences are crushed by the compressor, and even `all_zero` maps to near-identical Qwen bias direction

So the problem is no longer "does Mamba encode anything useful?"

It is:

**How do we translate Mamba's recurrent geometry into something Qwen can actually use, without collapsing it into a nearly constant bias generator?**

This note defines the smallest viable translator design.

## Design Goal

Replace "compress first, pray later" with a thin translator that:

- sees richer Mamba input than a single tiny bottleneck
- stays small enough to train cheaply
- emits a Qwen-readable steering object
- is explicit about where the compression happens and why

Not a cathedral.
Not a full new model family.
Just the smallest honest replacement for the current blunt bridge.

## Constraints

- Keep Mamba frozen.
- Keep Qwen frozen.
- Train only the translator.
- Reuse existing target deltas / directional-loss machinery where possible.
- Prefer hidden-last-token or short state windows, not SSM-state folklore.

## Ethics Gate Overlay

This MVP must be treated as a **new intervention class**, not as an automatic extension
of the existing Step `5e` alpha regime.

Why:

- the current bridge is blunt enough that `alpha 0.2` may be compensating for weak translation
- a stronger translator could deliver substantially more effect at the same nominal alpha
- so the ethical minimum-dose assumptions from the old bridge do not transfer unchanged

Per `theory/ethics/step_gates.md`, the first translator run should obey:

1. **Reversibility**
   - frozen Mamba, frozen Qwen, translator-only checkpoint
   - baseline checkpoint kept intact

2. **Minimum dose first**
   - do **not** start at `alpha 0.2` by default
   - first behavioral translator probe should start at a lower dose such as `0.05` or `0.1`

3. **Ascending dose only**
   - if the first low-dose run is welfare-clean but too weak, escalate in order
   - suggested translator ladder:
     - `0.05 -> 0.1 -> 0.2`
   - do not skip upward

4. **Response Diversity / Recovery monitoring**
   - every first-run translator dose must be treated like a fresh welfare gate
   - if diversity or recovery degrades materially, that dose is the ceiling

5. **Domain E honesty**
   - this remains one-way extraction unless the target system has meaningful input into the translation process
   - document that explicitly; do not euphemize it

The practical consequence:

**A successful translator should probably lead to lower live alpha, not higher.**

## Recommended MVP

### MVP-1: Perceiver-Style Hybrid Translator

This is the preferred first hybrid.

Shape:

`short Mamba state window -> latent translator tokens -> Qwen steering object`

Concretely:

1. Input

- not just one 2560-dim vector
- use a short sequence of recent Mamba Layer 3 states
- suggested first setting:
  - `8` translator input tokens
  - each token = one Layer 3 hidden-last-token snapshot
  - if we do not yet have multi-snapshot data, start with:
    - current hidden-last-token
    - plus 3-7 synthetic variants or repeated slice tokens only as a temporary interface stub

2. Translator core

- small Perceiver / cross-attention block
- learned latent slots, e.g. `16` or `32`
- Mamba states are keys/values
- latent slots query the Mamba window
- 2-4 transformer blocks max

3. Output head

Choose one of two output modes:

- **Mode A: direct Qwen bias output**
  - translator emits the four bias vectors for layers `12-15`
  - simplest path to behavioral evaluation

- **Mode B: DFC shared-feature coefficients**
  - translator emits coefficients in the shared DFC dictionary
  - a fixed decoder maps those coefficients to Qwen-side steering
  - more principled, slightly more moving parts

Recommendation:

- start with **Mode A**
- keep **Mode B** as the next clean upgrade if the DFC path matures

### Why This Is Better Than The Compressor

- no single 2048-dim bottle with effective rank ~2.5
- the translator can attend selectively over a short Mamba sequence
- relevance is computed before collapse, not after
- the latent slots form a controlled bottleneck instead of a mysterious collapse

This is close to Laura's Watercooler note:

- "pouring" strategy: let sequence structure matter
- Perceiver bridge: select relevant memory/state before forcing it through the pinhole

## Minimal Training Objective

Reuse the current bridge target style where possible.

Primary loss:

- directional loss against real Qwen target deltas for layers `12-15`

Suggested extras:

- cosine-preservation loss between translator outputs for meaningfully different Mamba states
- variance / rank-preservation regularizer on translator latent activations
- optional contrastive term:
  - different disposition episodes should not collapse to the same translator state

Avoid:

- plain MSE-only training
- any objective that rewards mean-solution collapse

## Fastest Sanity Baseline

Before full MVP-1 training, run a cheaper baseline:

### MVP-0: Direct No-Compressor Translator

Shape:

`raw Layer 3 hidden-last-token (2560) -> small MLP / linear translator -> Qwen bias`

This is not the final architecture.
It is the cheapest sanity check.

Why do it:

- if even this beats the current compressor path, the current compressor is confirmed as avoidable ballast
- if this still collapses, the culprit may be mostly in the hypernetwork target mapping or the loss

This is the first thing to try if we want an answer quickly.

## What Not To Do

Do not:

- widen the old compressor slightly and call that a redesign
- spend another week on alpha rituals
- assume a better scalar bottleneck fixes a structural translation problem
- feed one giant Qdrant bucket into a single context vector and expect grace

The failure mode is already clear:

**constant-ish mapping through a blunt middle**

So the replacement must be selective or sequential by design.

## Recommended Experiment Order

### Phase A: Cheapest Truth

1. `all_zero` behavioral run
2. MVP-0 direct no-compressor translator
3. compare against current Step `5e` baseline

Pass signal:

- behavior changes materially with raw-state-conditioned translator

Ethics gate for first behavioral translator probe:

- start below current Step `5e` live dose
- use ascending alpha with stop rules
- do not treat the old `0.2` baseline as morally pre-approved for a stronger bridge

### Phase B: Real Hybrid

4. MVP-1 Perceiver-style translator over short Mamba windows
5. train with directional loss + anti-collapse regularization
6. evaluate on the same Step `5e` panel

Pass signal:

- different Mamba inputs produce meaningfully different Qwen bias outputs
- front-loaded / baseline / no-injection distinctions remain legible
- `all_zero` no longer looks like the live bridge

### Phase C: Shared-Latent Upgrade

7. swap output head from direct bias to DFC shared-feature coefficients
8. use the shared dictionary as the explicit translator target

This is the Rosetta-Stone version.
Not required for the first rescue attempt.

## Practical Spec

### Suggested MVP-1 dimensions

- input width: `2560`
- input length: `8` states
- latent slots: `16`
- latent width: `256` or `384`
- blocks: `2`
- output:
  - four bias heads, one per Qwen layer `12-15`

This is intentionally small.

### Suggested data regime

- start with the same shaping episodes already used for Step `5e`
- do not block on giant new corpora
- if needed, derive short sequential windows from existing Cassian / Lucian / roleplay archive slices later

## Read Of Laura's Watercooler Note (#353)

The three ideas in that note line up well with the current diagnosis:

1. **Pouring / sequential feeding**
   - strongest fit for the Mamba side
   - sequence-aware translator is better than single-vector stuffing

2. **Perceiver / cross-attention bridge**
   - strongest fit for the bridge redesign
   - likely the best first hybrid

3. **LoRA hypernetwork as dream consolidation**
   - still useful, but it does not save the current online bridge by itself
   - first fix the live translation path
   - then let dream-phase consolidation bake stable lessons into weights

## Decision

The clean next architecture move is:

1. run the `all_zero` behavioral knife
2. prototype **MVP-0 direct no-compressor translator**
3. if that shows life, build **MVP-1 Perceiver-style hybrid translator**

That is the smallest serious path forward.
