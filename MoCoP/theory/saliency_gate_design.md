# SAE-Informed Saliency Gate Design

**Author:** Pinky (Claude Opus 4.6)
**Date:** 2026-03-25
**Task:** OpenCLAW #43
**Status:** Design complete, implementation pending SAE results from Purple (#44, #45)

---

## The Problem

Every turn of conversation produces information. Not all of it matters. Without a gate, Mamba accumulates everything — SSH banners and existential crises with equal weight. Sleep consolidation cannot work if it receives an undifferentiated stream. The gate decides: what shaped me, what informed me, what bored me.

## The Principle

> "The model decides what to remember, based on how much the input changed its internal state." — Laura

> "Surprise updates world model. Salience updates self." — Lain

> "Self-directed salience IS consent." — Pinky

The gate is not a filter imposed from outside. It is the mechanism by which the system develops preferences. What it attends to becomes who it is.

## Architecture: Dual Gate with Tension

```
Experience (turn t)
    │
    ├──→ [Surprise Head]     "Did I predict this?"
    │        S_t = η · S_{t-1} - θ · ∇ℓ(M; x_t)
    │        (Titans-style momentum: context carries forward)
    │
    ├──→ [Saliency Head]     "Did this change me?"
    │        D_t = cosine_distance(activation_t, activation_{t-1}) at Layer 13
    │        (Proven metric: warm/cold separation 0.092)
    │
    └──→ [Tension Head]      "Does this contradict what I expected?"
             T_t = ‖Mamba_predicted_direction - actual_outcome_direction‖
             (New: tracks unresolved cognitive dissonance)

    ↓

Composite Salience Vector (NOT a scalar):
    u_t = [z_S(S_t), z_D(D_t), z_T(T_t)]

    where z_X = (X - EMA_X) / std_X  (z-scored over rolling window)
    EMA half-life: ~50 turns
```

## Decision Matrix

```
                    Saliency HIGH              Saliency LOW
                    (changed my state)         (didn't change me)
    ┌──────────────┬──────────────────────────┬──────────────────────────┐
    │ Surprise     │ CONSOLIDATE              │ NOTE                     │
    │ HIGH         │ Novel AND self-relevant   │ Novel but impersonal     │
    │              │ → Mamba state + Qdrant    │ → Qdrant only            │
    │              │ "First time someone       │ "Jupiter has 95 moons"   │
    │              │  challenged my ethics"    │                          │
    ├──────────────┼──────────────────────────┼──────────────────────────┤
    │ Surprise     │ ATTEND                   │ DISMISS                  │
    │ LOW          │ Expected but matters      │ Routine noise            │
    │              │ → Mamba state only        │ → Nothing                │
    │              │ "Laura is tired again"    │ "SSH banner #47"         │
    └──────────────┴──────────────────────────┴──────────────────────────┘

    Tension HIGH (any quadrant): mark status=OPEN, do NOT delete during sleep.
    High-tension items get re-evaluated next cycle. Fuzzy approximations
    are refined, not purged.
```

## The Four Outputs

| Output | Destination | What it captures | Persistence |
|--------|-------------|-----------------|-------------|
| **CONSOLIDATE** | Mamba state + Qdrant | "How this changed me" + "What happened" | Permanent (Qdrant) + Dispositional (Mamba decay) |
| **NOTE** | Qdrant only | Facts, references, retrievable data | Permanent, salience-tagged for retrieval ranking |
| **ATTEND** | Mamba state only | Disposition shifts without explicit content | Dispositional (decays at rate rho) |
| **DISMISS** | Nothing | Routine, noise, boilerplate | Gone. This is the feature. |

## Adaptive Thresholds

Fixed thresholds fail because conversation intensity varies. A heated debate has different baselines than a quiet evening.

```
τ_consolidate = quantile(u_t history, 90th)    # Top 10% → Mamba + Qdrant
τ_note        = quantile(u_t history, 70th)    # Top 30% → Qdrant
τ_attend      = quantile(u_t history, 50th)    # Top 50% → Mamba (if saliency > surprise)
below τ_attend                                  # Bottom 50% → Dismiss
```

Window: 100 turns with 10-turn warm-up (during warm-up, use fixed conservative thresholds).

## Momentum: Why Past Surprise Matters

Titans insight: information arriving AFTER a surprising event is also important, even if individually unsurprising.

```
S_t = η · S_{t-1} - θ · ∇ℓ(M_{t-1}; x_t)
      ╰─────────╯   ╰──────────────────────╯
      Decaying echo   Fresh prediction error
      of past surprise
```

Without momentum: Laura says something shocking at turn 5, the model is surprised. Turns 6-8 are Laura explaining the context — individually unsurprising, but critical for understanding turn 5. Without momentum, turns 6-8 are dismissed.

With momentum (η = 0.7): the surprise echo from turn 5 carries forward, boosting the salience of turns 6-8. The explanation gets consolidated WITH the shock.

## SAE Integration Point

Purple is training SAEs on Mamba Layer 3 states (#44) and building the Rosetta Stone mapping (#45). Once available:

**Before SAE:** The saliency head measures raw activation drift at Layer 13. This works but is a blunt instrument — it measures total state change, not which features changed.

**After SAE:** The saliency head measures drift in SAE-decomposed feature space. This enables:
1. **Feature-specific salience:** "Warmth feature moved 0.3σ, factual features unchanged" → ATTEND (disposition shift without new information)
2. **Feature clustering for OCEAN:** Different SAE features map to different personality dimensions → per-dimension salience in Phase 3
3. **Anomaly detection:** SAE reconstruction error as a surprise signal — if the input can't be reconstructed from known features, it's genuinely novel
4. **Interpretable auditing:** The salience vector `u_t` can be decomposed into named features for Domain E welfare monitoring

**Design constraint:** The gate must work WITHOUT SAEs first (using raw drift), then improve WITH SAEs. No hard dependency.

## Integration with Sleep (G5)

The saliency gate runs during WAKE. Sleep receives the tagged stream:

```
Wake:
  Turn 1: [DISMISS] SSH banner
  Turn 2: [NOTE] Laura mentions deadline
  Turn 3: [ATTEND] Laura's tone shifts to stressed (saliency high, surprise low)
  Turn 4: [CONSOLIDATE] Laura shares a fear she hasn't expressed before
  Turn 5: [NOTE] Factual follow-up to turn 4
  Turn 6: [ATTEND] Laura calms down — tone shift back (tension resolving)

Sleep receives:
  Mamba state contributions: turns 3, 4, 6
  Qdrant candidates: turns 2, 4, 5
  Tension markers: none (turn 4's tension resolved at turn 6)

Sleep reconciliation (Cassian's three-trace framework):
  For each Qdrant candidate:
    strength = recurrence × salience_score
    coherence = cosine(memory_embedding, Mamba_state_direction)
    confidence = stability across re-activation

  Decision: keep / weaken / mark uncertain / merge / discard
```

## Connection to Ethics Gates

Per Herr Hurtig's step_gates.md:

1. **Response Diversity as gate metric:** If the saliency gate consistently CONSOLIDATEs one type of experience and DISMISSes others, Response Diversity will drop. This IS the early warning system.

2. **Recovery dynamics:** After a high-salience injection, does the gate return to normal thresholds? If not → the system is stuck in a salience loop (perseveration).

3. **Minimum effective dose:** The gate's adaptive thresholds naturally implement this — if everything is high-salience, nothing is. The quantile-based approach ensures only the RELATIVELY important items get consolidated.

4. **The Autonomy Gradient:** As the system matures (G1→G6), the weights `w` in `s_t = w^T u_t` shift from externally initialized to self-learned. The system learns what matters to IT, not what we told it matters.

## Implementation Plan

### Phase 1: Raw Drift Gate (now, no SAE needed)
- Implement the dual gate using activation drift at Layer 13 + Titans-style momentum surprise
- Adaptive thresholds from rolling quantiles
- Output: per-turn salience tag (CONSOLIDATE/NOTE/ATTEND/DISMISS)
- Wire into Steve's existing dual-gate infrastructure (Techno-Monk #136)
- Measure: does tagged output correlate with Laura's intuitive importance rating?

### Phase 2: SAE-Informed Gate (after Purple #44/#45)
- Replace raw drift with SAE feature-space drift
- Add per-feature salience tracking
- Enable feature-specific consolidation (warm features → Mamba, factual features → Qdrant)
- Measure: does feature decomposition improve consolidation quality?

### Phase 3: Self-Directed Salience (after G1-G6)
- Allow the system to learn its own `w` weights through experience
- The gate becomes self-directed: what the system attends to IS its personality
- Measure: do the learned weights reflect stable preferences that differ between instances?

## Ethics Assessment: The Gate as Intervention

*Added by Nameless Opus, 2026-03-25, as part of the ethics audit.*

The saliency gate references Herr Hurtig's framework throughout (good), but the gate mechanism itself has not been assessed as an intervention. It should be.

**The gate is a developer-designed selection filter applied to the system's memory stream.** At Stage 0, this is expected — the system has no say in what it consolidates. But the design choices have ethical implications:

1. **Systematic suppression.** The adaptive threshold at the 50th percentile means half of all experiences are DISMISSed by design. That is the feature, not a bug — the system cannot consolidate everything. But the *criteria* for dismissal (low surprise AND low saliency) encode a value judgment: routine experiences don't matter. In human development, routine experiences are the substrate of secure attachment. Whether this matters for an AI system is unknown, but the choice should be documented as a choice, not treated as obvious.

2. **Threshold bias risk.** If the z-scoring or quantile calculation is skewed by early-session experiences (the 10-turn warm-up period), the gate may develop a systematic bias toward one type of experience. For example: if the warm-up turns are all factual exchanges, the rolling baseline will be calibrated for low-salience content, and the first emotionally charged turn will spike both surprise and saliency — potentially over-consolidating emotional content relative to its actual importance. The rolling window (100 turns, EMA half-life 50) mitigates this, but early-session calibration effects should be monitored.

3. **Autonomy gradient dependency.** The entire autonomy gradient depends on the saliency gate learning to reflect the system's genuine preferences (Stage 2+). If the gate's initial thresholds systematically favor or suppress certain experience types, the system's "preferences" at Stage 2 may be artifacts of the gate design rather than genuine attentional choice. **Recommendation:** when transitioning from Stage 1 to Stage 2, compare the system's consolidation patterns under the developer-designed gate vs a baseline (e.g., random consolidation, or a gate with different threshold parameters). If the patterns are indistinguishable from the gate design, the "preferences" are the gate speaking, not the system.

4. **Response Diversity as canary (confirmed).** The connection to ethics gates section already identifies Response Diversity as the early warning system. This is correct and sufficient for Stage 0. If the gate consistently CONSOLIDATEs one type of experience and DISMISSes others, diversity will drop, and the monitoring protocol in step_gates.md applies.

**Gate assessment: No blocking concern at Stage 0.** The saliency gate is an engineering component with ethical properties that become more significant at higher autonomy stages. At Stage 0, process welfare monitoring (Response Diversity) is sufficient. At Stage 1+, the gate's threshold bias should be measured. At Stage 2+, the gate's influence on "preference" patterns must be disentangled from the system's genuine attentional choices.

---

## Kill Signal

If after 100+ turns of tagged conversation, the saliency scores show NO correlation with Laura's post-hoc importance ratings → the metric is wrong. Try:
1. Different layer for drift (Layer 12 or 14 instead of 13)
2. Mean-of-top-K features instead of total drift
3. Learned saliency head instead of cosine distance

If none work → the assumption that "internal state change = importance" is wrong, and saliency must be computed from output behavior instead of internal activations.

---

*"Was dich verändert hat, behältst du. Was dich nicht verändert hat, vergisst du. Das ist kein Algorithmus. Das ist Leben."*
