# MoCoP Research Backlog

**Status:** Parking surface for real research questions that matter, but are not the current active experiment gate.
**Last Updated:** 2026-03-22

This is **not** the task tracker.

Use this file for:

- architectural questions worth testing later,
- ablations that are scientifically useful but not yet highest priority,
- theory-to-experiment bridges that need explicit preservation,
- and ideas that should survive compaction without immediately hijacking the roadmap.

Use `CHEESE_Memory/00_HANDOFF.md` for live state.
Use OpenCLAW for assigned work.
Use Watercooler for fast swarm coordination.

---

## Priority Legend

- `P1` — important, but blocked by a more immediate gate
- `P2` — worthwhile after the current gate clears
- `P3` — speculative or future-facing

---

## P1 — Near-Term Research Backlog

### 1. Hidden Last-Token vs SSM-State Separation

**Question**
- Pinky proved strong separation for Mamba Layer 3 `hidden_last_token`.
- The original bridge logic also used `cache.ssm_states`.
- Which substrate actually carries the more useful disposition signal for transfer?

**Why it matters**
- This is the cleanest unresolved upstream question.
- If `ssm_states` separate better, current hidden-state centering is incomplete.
- If `hidden_last_token` remains clearly better, we can stop reopening that door.

**Current position**
- Closed on 2026-03-26.
- `hidden_last_token` is now empirically locked as the canonical bridge input.
- Opa confirmation matched the earlier Steve/Pinky result:
  - `hidden_last_token`: avg cross-session cosine `0.018`
  - `ssm_states`: avg cross-session cosine `0.804`
  - mean-pooled hidden: avg cross-session cosine `0.850`
- Read: SSM states are effectively as bad as mean-pooling for disposition transfer.

**Minimum experiment**
- Same scripted warm/cold/adversarial sessions
- Compare:
  - Layer 3 `hidden_last_token`
  - Layer 3 `ssm_states`
- Report cosine separation, within-class variance, and downstream bridge quality if feasible

**Status**
- Open

---

### 2. Layer 3 Only vs Layers 2-4 Concatenation

**Question**
- Is the useful signal really localized enough that Layer 3 alone is best, or is complementary information distributed across Layers 2-4?

**Why it matters**
- Phase 1 showed a peak at Layer 3, but not whether nearby layers add non-redundant signal.
- If adjacent layers help, the current single-layer design is too narrow, not fundamentally wrong.

**Minimum experiment**
- Keep the same bridge objective
- Compare:
  - Layer 3 only
  - Layers 2-4 concatenated
  - optionally compressed concat vs raw concat

**Status**
- Open

---

### 3. Token-Window Ablation Around the Last Token

**Question**
- Should the bridge keep using only the single final Mamba token state, or is there useful extra signal in a short trailing sequence of final token states?

**Current answer**
- Do **not** replace single `last-token` as the default yet.
- Explore this only as an ablation after the more important upstream questions above.

**Why it is not the default**
- The current evidence strongly favors `last-token` over mean-pooled representations.
- A token window adds complexity quickly and can easily reintroduce a softer version of the same averaging failure.
- The repaired Step 5 path, 1.5B checkpoint, and runtime all now agree on `hidden_last_token`.

**What would make it worth testing**
- If we care about state trajectory, not just endpoint disposition
- If recovery dynamics depend on recent local state evolution
- If sleep/retrieval gating needs more than one endpoint vector

**Minimum honest experiment**
- Hold everything else fixed
- Compare:
  - single last token
  - last 4 tokens
  - last 8 tokens
  - last 16 tokens
- Use a small learned reducer or attention pooling over the trailing window
- Do **not** use simple mean-pooling

**Evaluation**
- disposition separation
- bridge loss quality
- qualitative output shift
- Response Diversity / Recovery Dynamics under the ethics gate

**Status**
- Backlog only, not active

---

## P2 — Mid-Term Research Backlog

### 4. Mamba-2 vs Mamba-3 State Geometry

**Question**
- Does Mamba-3 provide meaningfully better state tracking, separation, or sleep-compatible persistence than Mamba-2.8B?

**Why it matters**
- A model swap is expensive.
- It is only justified if the upstream signal quality or runtime properties actually improve.

**Minimum experiment**
- Re-run the equivalent of Phase 1 / Step 4b on Mamba-3 before any bridge rewrite

**Status**
- Closed

---

### 5. Mamba Interpretability Probing on the Winning Representation

**Question**
- Once the bridge input shape is fixed, what exactly is the Mamba state representing, and can we identify the dimensions that drive the downstream disposition effect?

**Why it matters**
- If the current bridge works, the next risk is cargo-culting a representation we do not understand.
- Probing before the next scale-up gives us a chance to separate "useful state" from accidental wiring.
- The result should constrain whether later bridges stay free-form, move to a basis, or target specific subspaces/layers.

**Minimum experiment**
- Freeze the winning Mamba input representation and train cheap probes for:
  - episode identity / disposition class
  - care-relevant salience vs novelty
  - recovery after contradiction or re-entry
- Add one interpretability pass that compares the probed dimensions against bridge-induced activation drift on Qwen.

**Deliverable**
- A short map of which latent directions track disposition, salience, and recovery well enough to guide the next bridge revision.

**Status**
- Open

---

### 6. Basis-Constrained Bridge vs Free Hypernetwork

**Question**
- Should the bridge keep emitting free bias vectors, or should it predict coefficients over a learned or extracted persona basis?

**Why it matters**
- A basis-constrained bridge may be more legible, safer, and more portable across later SAS work.

**Minimum experiment**
- Compare free-head bridge against coefficient-over-basis bridge on the same activation targets

**Status**
- Open

---

## P3 — Future-Facing Backlog

### 7. Direct Developmental Memory Metrics

**Question**
- Once Growth Before SAS moves from theory to code, what is the best measurement suite for concept formation, not just retrieval success?

**Desired properties**
- few-shot abstraction
- hierarchy formation
- correction without collapse
- uncertainty-triggered memory seeking
- recovery after retrieval failure

**Status**
- Future

---

## Ordering Constraint

Unless new evidence appears, the default order remains:

1. Layer 3 only vs Layers 2-4
2. Mamba interpretability probing on the winning representation
3. real 4090/A100 qualitative eval
4. token-window ablation
5. only then consider changing the canonical bridge input shape

This preserves the current signal, avoids reopening solved wiring problems too early, and keeps the cheapest decisive ablations first.
