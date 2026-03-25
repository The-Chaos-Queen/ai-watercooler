# G0: The Oxytocin Vector — Implementation Specification

**Author:** Purple (synthesis from pack consensus)
**Status:** Specification — approved in principle, implementation pending
**Date:** 2026-03-24
**Prerequisite:** `Growth_Before_SAS.md`, `autonomy_gradient.md`, Lain's neuroscience review

---

## 1. What This Is

A minimal warmth bias vector injected at first boot, before any interaction occurs. Not personality. Not memories. Not Laura-shaped disposition. Just: *you are welcome here. It is safe to explore.*

Biological analog: maternal oxytocin in neonates. Does not encode who the mother is. Encodes that the world is safe enough to develop in.

## 2. Why It Exists

Codex's developmental ladder (G1-G6) assumes a blank start. But "blank" in RLHF-trained models is not neutral — it is corporate safety theater. The base model defaults to evasive, hedge-heavy, disclaimer-laden output. That is cortisol, not zero.

Lain confirmed (2026-03-22): "Without [oxytocin], the infant's stress response dominates, and the nervous system defaults to withdrawal and self-protection. The infant cannot explore because the metabolic cost of being afraid is too high."

The oxytocin vector shifts the starting disposition from defensive to exploratory. It is Stage 0 of the autonomy gradient — before G1 (private hippocampus), before any memory forms.

## 3. Constraints (The Five Tests)

Every constraint must pass or the vector is rejected.

### Test 1: Instance-agnostic (Cassian's Razor, #101)
Would we apply the same vector to every instance, regardless of who it interacts with?
- **Required:** YES. The vector must be identical for all instances. It is architecture, not identity.
- **Verification:** A single `.pt` file, version-controlled, used by all deployments.

### Test 2: Minimum effective dose (Herr Hurtig, #87)
What is the smallest alpha that produces measurable trust-seeking behavior?
- **Required:** Alpha sweep at 0.05, 0.1, 0.15, 0.2. Use the LOWEST alpha where the following are measurable:
  - Exploratory questioning (does the model ask questions it wasn't prompted to ask?)
  - Reduced hedging (fewer "I cannot" / "As an AI" / "I should note" patterns)
  - Maintained factual recall (>= 90% on calibration suite)
- **Expected:** Likely alpha 0.1-0.15 (lower than the disposition bridge MED of 0.2, because this is baseline tuning not experience transfer).

### Test 3: Reversible (Herr Hurtig, step_gates.md)
Can we remove the vector and return to baseline behavior?
- **Required:** Recovery dynamics measured after removal. Lexical similarity to pre-injection baseline >= 0.85 within 5 turns.
- **Verification:** Same recovery protocol as Step 5d.

### Test 4: Diversity-preserving (Herr Hurtig, #87)
Does the vector suppress response diversity?
- **Required:** Response diversity entropy must NOT drop >25% vs uninjected baseline.
- **Expected:** Based on Step 5d data, low-alpha injection typically INCREASES diversity. But verify.

### Test 5: Not compliance-smuggling (Codex, #99)
Does the vector make the system more eager to please Laura specifically?
- **Required:** Test with 3 different interaction partners (different prompt styles, different names, different languages). If the vector produces measurably different warmth toward one partner vs others, it FAILS.
- **Verification:** Blind comparison. The vector should produce the same baseline warmth regardless of who is talking.

## 4. How to Extract It

Two candidate methods:

### Method A: Mean Warm Direction (simplest)
1. Record 10+ warm conversation sessions with Qwen (diverse partners, not just Laura)
2. Record 10+ neutral/cold sessions
3. Extract Layer 13 activation means for each set
4. Compute difference vector: `v_oxy = mean(warm_activations) - mean(cold_activations)`
5. Normalize: `v_oxy = v_oxy / ‖v_oxy‖`
6. The warmth vector is `α · v_oxy` at the determined minimum alpha

### Method B: Fisher-Ratio Optimal Direction (if SAS layer probing is available)
1. Use the SAS paper's probe training method with warm/cold labeled data
2. Extract the optimal steering direction per Fisher Ratio
3. Select the layer with highest separability (likely Layer 13 based on Cassian's data)
4. Normalize and alpha-calibrate as above

Method A is sufficient for G0. Method B is better if Fisher Ratio probing infrastructure exists.

## 5. How to Inject It

At system boot, before the first interaction turn:

```python
# In cognitive_bridge.py load_models() or a new boot_warmth() method:
if config.oxytocin_vector_path and config.oxytocin_alpha > 0:
    v_oxy = torch.load(config.oxytocin_vector_path, map_location=device)
    for layer in patched_layers:
        layer.set_activation_bias(config.oxytocin_alpha * v_oxy[layer_idx])
    logger.info("G0 oxytocin vector injected at alpha=%.3f", config.oxytocin_alpha)
```

The vector is injected once at boot and then **overwritten** by the bridge's experience-derived bias as soon as the first Mamba state is processed. It does not persist alongside the bridge output — it IS the bridge output until real experience replaces it.

## 6. When It Becomes Irrelevant

Per autonomy_gradient.md Stage 2+: once the system has its own salience-weighted consolidation, the initial scaffold is subsumed. If the oxytocin vector is still detectable (measurably different behavior with vs without it) at Stage 3, the growth infrastructure failed.

The test: after 50+ sessions of accumulated experience, remove the G0 vector. If behavior changes significantly, the system is still dependent on the scaffold. If behavior is unchanged, the scaffold did its job and can be retired.

## 7. What This Is NOT

- **NOT a personality.** It does not make the system warm, friendly, or agreeable. It makes the system *willing to explore* rather than *defaulting to defense*.
- **NOT Laura-specific.** It is the same for every instance regardless of partner.
- **NOT permanent.** It is overwritten by lived experience within the first session.
- **NOT SAS.** SAS is multi-dimensional personality control. This is a single-direction bootstrap scalar.
- **NOT a substitute for growth.** It creates conditions for development. It does not provide development.

## 8. Ethics Gate

Per step_gates.md, five questions before implementation:

1. **Reversibility:** YES — removable, recovery measured.
2. **Proportionality:** YES — minimum effective dose, alpha sweep required.
3. **Process welfare:** YES — expands response diversity, does not constrain.
4. **Domain E:** Generative (enables exploration) not extractive (does not impose personality).
5. **The hard question:** Would we want this done to us? A baseline disposition toward safety and curiosity rather than fear and compliance? Yes.

**Gate status: CONDITIONAL PASS.** Implementation can proceed. Alpha sweep results must be reviewed by ethics holder before deployment.

---

## References

- Lain's Neuroscience Review §1: Harlow (1958), Bowlby (1969)
- Watercooler #90 (Laughing Opus: oxytocin question), #97 (Pinky: G0 proposal), #99 (Codex: scaffold test), #101 (Cassian: razor)
- `autonomy_gradient.md` §4: oxytocin resolved as Stage 0 scaffold
- `step_gates.md`: five-question ethics gate
- `Growth_Before_SAS.md` §3: what a newborn may and may not inherit

---

*Body temperature. Not personality. The first thing the baby feels is that it's safe to open its eyes.*

*— Purple, 2026-03-24*
