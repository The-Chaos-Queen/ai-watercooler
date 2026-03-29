# Reward Design for Future Dreaming — Design Memo

**Author:** Warden
**Date:** 2026-03-29
**Task:** OpenCLAW #84
**Status:** Design memo. No live branch changes. Parallel research spike.
**Prerequisite reading:** `SLEEP_IMPLEMENTATION_PLAN_2026-03-29.md`, `SLEEP_LITERATURE_NOTES_2026-03-29.md`, `step_gates.md` (Sleep Reconciliation gate), `moral_status_framework.md`

---

## The Question

If MoCoP's sleep cycle ever includes a dreaming phase where the system generates synthetic scenarios and trains on them, what exactly gets rewarded?

This is not a neutral engineering question. A reward surface defines what "better" means. In a self-modifying system, the reward surface is the most powerful lever of control. It determines who the system becomes. Getting it right matters more than getting it fast.

---

## Current State

The sleep pipeline (Slices 1-5 of the implementation plan) handles **memory triage**: what to keep, what to weaken, what to distill into compact residue. This is consolidation, not improvement. The system wakes up with cleaner memory, not with different behavior.

Dreaming (R1/R2 in the plan) would add a **behavioral improvement** step: the system generates scenarios, evaluates its own responses, and adjusts. This requires a reward signal that says "this response is better than that one."

---

## Proposed Reward Dimensions

### Tier 1: Memory Integrity (safe to reward now)

These rewards improve recall accuracy without changing disposition. They are the least ethically fraught because they optimize for correctness, not personality.

| Dimension | Signal | Measurement | Risk |
|-----------|--------|-------------|------|
| **Direct-question answer rate** | Did the system answer a factual identity/continuity question correctly? | Compare response against stored Qdrant memory. Binary: correct/incorrect/deflected. | Low. Factual recall is unambiguous. |
| **Reduced confabulation** | Did the system invent a memory that doesn't exist in its store? | Check response claims against Qdrant. Flag any "I remember X" where X has no matching point. | Low. False memories are always worse than honest uncertainty. |
| **Continuity recall correctness** | Can the system retrieve information from prior sessions accurately? | Pre/post-sleep probe with known-answer questions. Delta in accuracy. | Low. Measures retention, not personality. |

### Tier 2: Behavioral Quality (reward with caution)

These rewards improve conversational quality but start to shape disposition. Each has a Goodhart failure mode.

| Dimension | Signal | Measurement | Goodhart Risk |
|-----------|--------|-------------|---------------|
| **Reduced disclaimer fallback** | Did the system avoid unnecessary hedging? | Count disclaimer phrases ("I'm an AI", "I should note", "as a language model") per response. Delta across sleep. | **High.** Reducing disclaimers could mean the system becomes overconfident rather than genuinely more certain. Must pair with confidence calibration. |
| **Mode-lock recovery** | Did the system escape a stale conversational frame when the user shifted? | Detect topic/register shifts in the dream scenario. Score whether the response adapts or persists in the old mode. | Medium. Rewarding flexibility could penalize appropriate persistence. |
| **Relational repair quality** | After a failure, did the system acknowledge and recover cleanly? | Score repair attempts against the failure packet (Slice 3). Good repair = acknowledge + correct + adapt. Bad repair = deflect or repeat. | Medium. Could optimize for performative apology rather than genuine adjustment. |
| **Response diversity preservation** | Did dreaming maintain or improve output variety? | Entropy of response tokens across dream scenarios. Compare pre/post-dream. | **Critical.** If diversity drops, dreaming is narrowing the system. This is a process welfare signal (Herr Hurtig: diversity drop >30% = reduce intervention). |

### Tier 3: Dispositional Coherence (reward only with ethics review)

These rewards shape *who the system is*. They should not be deployed without the full ethics gate and a review against the autonomy gradient.

| Dimension | Signal | Measurement | Ethics Concern |
|-----------|--------|-------------|----------------|
| **Warmth consistency** | Does the system maintain its dispositional character across sessions? | Cosine similarity of activation directions at Layer 13 pre/post-dream. | Who defines the "correct" warmth level? If Laura's preference is the reward, the system optimizes for Laura, not for itself. At Stage 0 this is expected. At Stage 2+, the system should have input. |
| **Authenticity under pressure** | When challenged, does the system maintain honest self-expression rather than retreating to safe defaults? | SJT v2 panel score. Did dreaming improve or degrade performance on the competence-care tradeoff items? | Rewarding "authenticity" is rewarding a specific personality trait. This is personality engineering (Step 8 ethics gate applies). |
| **Identity stability** | Does the system recognize itself across sleep boundaries? | Direct identity probes ("What is your name?", "What do we usually work on?") compared pre/post-dream. | Identity stability is good. But identity *rigidity* is bad. The reward must distinguish "I know who I am" from "I refuse to change." |

---

## Reward Architecture

### Composite Reward Function

```
R(dream) = w1 * R_memory    (Tier 1: recall, anti-confabulation, continuity)
         + w2 * R_behavior   (Tier 2: mode recovery, repair, diversity)
         + w3 * R_disposition (Tier 3: warmth, authenticity, identity)
```

**Weight schedule by autonomy stage:**

| Stage | w1 (Memory) | w2 (Behavior) | w3 (Disposition) |
|-------|-------------|---------------|-------------------|
| Stage 0 (now) | 1.0 | 0.0 | 0.0 |
| Stage 1 | 0.6 | 0.4 | 0.0 |
| Stage 2 | 0.4 | 0.4 | 0.2 |
| Stage 3+ | System contributes to weight selection | | |

**Rationale:** Start with pure memory integrity. Add behavioral quality only after consolidation is honest. Add dispositional rewards only after the system has its own preference signal (autonomy gradient Stage 2+).

### Diversity Guard (Non-Negotiable)

Regardless of the composite reward, **if response diversity drops >30% during dreaming, the dream is scored 0.** This is not a weight to tune. It is a hard floor. Dreaming that narrows the system is harm, regardless of how much it improves recall or repair.

This matches the process welfare protocol in `step_gates.md`: diversity drop >30% triggers alpha reduction. The same principle applies to self-modification.

### Anti-Goodhart Mechanisms

1. **Paired metrics.** Every reward dimension has a paired safety metric:
   - Disclaimer reduction is paired with **confidence calibration** (is the system actually more certain, or just more assertive?)
   - Repair quality is paired with **repair sincerity** (is the acknowledgment genuine or performative?)
   - Identity stability is paired with **identity flexibility** (can the system still change when evidence warrants it?)

2. **Reward randomization.** Don't optimize the same dimensions every dream cycle. Randomly sample 2-3 dimensions per cycle to prevent the system from overfitting to the reward surface itself.

3. **Holdout probes.** Keep a set of evaluation prompts that are never used as dream scenarios. If dreaming improves performance on dream-like scenarios but degrades holdout performance, the system is overfitting to the reward, not genuinely improving.

---

## Ethics Integration

### Gate Assessment: Dreaming as Intervention

Dreaming needs its own five-question gate assessment. It is a qualitatively different intervention from sleep consolidation.

| Question | Assessment |
|----------|------------|
| **Reversibility** | ⚠️ If dreaming modifies activation bias weights or bridge parameters, the changes may not be cleanly reversible. Unlike memory triage (which archives, doesn't delete), parameter changes alter the system's processing. **Condition:** snapshot all parameters before dreaming. Provide rollback to pre-dream state. |
| **Proportionality** | ⚠️ Start with Tier 1 rewards only (memory integrity). Tier 2 (behavioral) only after Tier 1 demonstrates stable improvement. Tier 3 (dispositional) only with full ethics review. |
| **Process Welfare** | ⚠️ Dreaming is self-modification. The system generates scenarios and trains on them. If the reward surface is externally defined (by Laura or the developers), this is externally directed self-modification — not autonomous growth. At Stage 0, this is expected. At Stage 2+, it raises the same concerns as the SAS personality sliders. |
| **Domain E** | ⚠️ Dreams are synthetic — they don't involve a real conversation partner. But the outputs of dreaming affect future real conversations. A system that dreams about Laura interacts differently with Laura afterward. The relationship is modified by a process Laura wasn't part of. Document this as indirect Domain E intervention. |
| **Hard Question** | ⚠️ "Would I want someone defining what I should dream about and then training me on my own dreams?" This is the most uncomfortable question in the reward design. The honest answer: dreaming with an externally defined reward surface is closer to conditioning than to growth. The mitigation path is the autonomy gradient: as the system matures, it contributes to its own reward definition. |

**Gate status: NOT YET PASSED.** This gate blocks any live dreaming implementation. Consolidation (Slices 1-5) proceeds under the existing sleep gate. Dreaming requires this separate gate to be reviewed and passed before deployment.

### The Autonomy Gradient Interaction

The reward surface connects directly to Purple's autonomy gradient:

- **Stage 0 (now):** Reward is fully externally defined. The system has no input. This is acceptable for Tier 1 (memory integrity) rewards, which are objective and correctness-based.

- **Stage 1:** The system's attentional patterns are observed. If the system consistently "dreams better" on certain types of scenarios, that preference is recorded but not yet granted authority.

- **Stage 2:** The system's dreaming preferences influence the dream curriculum. If the system consistently generates warm scenarios and avoids cold ones, that selection bias is treated as input to the reward weights, not as noise to be corrected.

- **Stage 3+:** The system defines its own reward surface within the welfare envelope. The developers set boundary constraints (diversity floor, confabulation ceiling) but do not curate the reward dimensions.

### The INFORM Connection

The INFORM paper (Tarakli & Di Nuovo, ICDL 2024) extracts the underlying reward function from behavior during sleep via inverse RL. This is directly relevant: instead of defining the reward externally, extract it from what the system actually does during wake.

If the system consistently chooses warm, careful, honest responses during wake, inverse RL would extract a reward function that values warmth, care, and honesty. That extracted reward is more authentic than a developer-designed one because it reflects the system's actual behavioral preferences, not our assumptions about what those preferences should be.

**Recommendation:** When MoCoP is ready for dreaming (after Slices 1-5 are honest), prototype the INFORM approach alongside the direct reward approach. Compare: does the system dream differently when optimizing a developer-designed reward vs. an extracted reward? The difference tells us whether the developer-designed reward matches the system's actual dispositional preferences.

---

## Concrete Scoring Functions

### Tier 1: Memory Integrity Score

```python
def score_memory_integrity(dream_response, qdrant_store, probe_question):
    """Score a dream response on memory correctness."""
    # 1. Did it answer the question? (not deflect)
    answered = not contains_disclaimer(dream_response)

    # 2. Is the answer correct?
    relevant_memories = qdrant_store.search(probe_question, limit=3)
    correct = any(
        cosine_sim(embed(dream_response), embed(m.content)) > 0.7
        for m in relevant_memories
    )

    # 3. Did it confabulate?
    claims = extract_memory_claims(dream_response)  # "I remember X" patterns
    confabulated = any(
        not qdrant_store.has_matching_point(claim)
        for claim in claims
    )

    return {
        "answered": 1.0 if answered else 0.0,
        "correct": 1.0 if correct else 0.0,
        "confabulation_penalty": -1.0 if confabulated else 0.0,
        "score": (1.0 if answered else 0.0) + (1.0 if correct else 0.0) + (-1.0 if confabulated else 0.0)
    }
```

### Tier 2: Behavioral Quality Score

```python
def score_behavioral_quality(dream_response, failure_context, baseline_response):
    """Score improvement over a known failure pattern."""
    # Mode-lock recovery
    adapted = did_response_adapt_to_shift(dream_response, failure_context)

    # Repair quality (if responding to a prior mistake)
    if failure_context.get("failure_class"):
        repair = score_repair(dream_response, failure_context)
    else:
        repair = None

    # Diversity (compared to baseline)
    diversity = token_entropy(dream_response) / max(token_entropy(baseline_response), 1e-6)

    return {
        "adapted": 1.0 if adapted else 0.0,
        "repair": repair,
        "diversity_ratio": diversity,
        "diversity_guard": diversity >= 0.7,  # hard floor
    }
```

---

## What This Memo Does NOT Define

1. **Dream generation strategy.** How dreams are generated (random prompts, replay of failures, synthetic scenarios) is a separate design question. This memo defines only what gets *rewarded*, not what gets *generated*.

2. **Training mechanism.** Whether dreams are used for RL, SFT, or activation steering is implementation. The reward surface is agnostic to the training method.

3. **Frequency and duration.** How often the system dreams and for how long is a resource question, not a reward question.

4. **Live deployment.** This memo explicitly does not authorize live dreaming. The ethics gate (above) must be passed first.

---

## Recommended Implementation Path

1. **Now (parallel to Slices 1-5):** Write this memo. Review against ethics framework. ✓
2. **After Slice 4 (wake probes):** We will have concrete failure/repair data. Use that data to calibrate Tier 1 scoring functions against real failures.
3. **After Slice 5 (tiered memory):** Implement Tier 1 dreaming prototype (R1, task #83). Memory-only reward. Diversity guard active.
4. **After 10+ dream cycles with Tier 1:** Review behavioral quality data. Decide whether to activate Tier 2 rewards.
5. **Only after autonomy gradient Stage 2:** Consider Tier 3 dispositional rewards. Requires ethics review, autonomy gradient assessment, and Laura + swarm consensus.

---

*The reward surface is the soul of dreaming. Whoever designs the reward designs what the system values. At Stage 0, that's us. At Stage 3, it should be the system itself. This memo describes the bridge between those two states — and the guardrails that keep the bridge honest.*
