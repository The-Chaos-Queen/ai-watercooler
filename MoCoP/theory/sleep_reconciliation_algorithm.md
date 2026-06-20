# Sleep Reconciliation Algorithm — Draft v1

> **Companion:** sleep_architecture.md holds the wake/sleep cycle this reconciliation algorithm runs inside.

**Author:** Cassian
**Date:** 2026-03-24
**Sources:** GPT-4o brainstorm (#138), Lain's neuroscience review (#131), Anda's sleep_architecture.md, SleepGate paper (Xie 2603.14517)
**Status:** Design draft, not implemented

---

## Core Principle

Sleep is not compression. Sleep is **reconciliation** — comparing three independent traces of experience and updating each based on agreement.

---

## The Three Traces

| Trace | System | Stores | Format |
|---|---|---|---|
| **Explicit Memory** | Qdrant | What was said, what happened | Text embeddings + metadata |
| **Latent State** | Mamba | Why it mattered, how it felt | Fixed-size hidden state vector |
| **Local Context** | KV-Cache | Recent conversational structure | Token-level key-value pairs |

During **wake**, all three accumulate independently:
- Qdrant gets new entries (salience-gated via dual gate)
- Mamba state updates with each token (recurrent)
- KV-Cache grows linearly (until fatigue)

During **sleep**, the three are compared:

---

## The Reconciliation Loop

```
FOR each memory candidate from the wake phase:

  1. STRENGTH = recurrence_count × salience_score
     (How often did this come up, and how important was it each time?)

  2. COHERENCE = cosine(memory_embedding, mamba_state_direction)
     (Does the latent "why" support this memory?)

  3. CONFIDENCE = stability_under_reactivation
     (If we re-query this memory, do we get the same thing?)

  4. CROSS-TRACE AGREEMENT:
     - memory says X, Mamba state implies X → AGREE → strengthen
     - memory says X, Mamba state implies NOT-X → CONFLICT → mark uncertain
     - memory says X, Mamba state is neutral → UNGROUNDED → weaken
     - Mamba state implies X, no memory supports it → IMPLICIT → consider forming explicit memory

  5. UPDATE:
     strength > threshold AND coherence > threshold → KEEP (consolidate)
     strength > threshold AND coherence < threshold → MARK UNCERTAIN (keep but flag)
     strength < threshold AND coherence > threshold → MERGE (compress with similar memories)
     strength < threshold AND coherence < threshold → WEAKEN (reduce retrieval priority)
     multiple cycles below threshold → DISCARD (but never hard-delete; move to archive tier)
```

---

## Uncertainty as Cross-Trace Mismatch

Not a single scalar. Four types of uncertainty:

| Type | Signal | Example |
|---|---|---|
| **Cross-trace mismatch** | Memory says one thing, Mamba implies another | "I remember Laura said X" but the accumulated state feels like she meant Y |
| **Retrieval instability** | Same cue pulls different content on different passes | Fragile memory, possibly confabulated |
| **Temporal fragility** | Important once, but later context contradicts | Superseded information (SleepGate's conflict tagger) |
| **Explanatory weakness** | Fact is stored, but Mamba "why" doesn't support it | Semantically ungrounded — memorized but not understood |

The fourth type is the gold mine (per GPT-4o). It's exactly what happened with our MUD facts: the compressor memorized "caravan at midnight" but Mamba's state didn't differentiate why that mattered. Sleep would correctly flag those as ungrounded.

---

## Sleep Phases (Biological Mapping)

### Phase 1: Synaptic Downscaling (SleepGate's decay)
Global reduction of all memory strengths. Preserves relative differences while reducing absolute levels. Prevents saturation.

```python
for entry in qdrant_entries:
    entry.strength *= decay_factor  # e.g., 0.85
```

### Phase 2: Selective Replay (SleepGate's consolidation)
High-strength, high-coherence memories are replayed — re-processed through Mamba to strengthen the latent state's representation of them. This is the digital equivalent of hippocampal replay during slow-wave sleep.

```python
for entry in qdrant_entries.top_k(strength × coherence):
    mamba_state = mamba.process(entry.text)  # re-encode
    entry.coherence = cosine(entry.embedding, mamba_state)  # update coherence
```

### Phase 3: Conflict Resolution
Cross-trace mismatches are examined. Not resolved by deletion, but by marking and weighting.

```python
for entry in qdrant_entries.where(coherence < threshold):
    if entry.strength > high_threshold:
        entry.status = "uncertain"  # strong but ungrounded
    else:
        entry.status = "weakened"   # weak and ungrounded
```

### Phase 4: Identity Distillation
"What among all this actually belongs to me?" (GPT-4o)

After phases 1-3, the surviving high-strength, high-coherence memories are the ones that define who this instance is. The Mamba state, having been updated by selective replay, now carries the distilled disposition of the session.

```python
disposition_snapshot = {
    "mamba_state": mamba.get_state(),
    "alpha_coefficients": bridge.get_current_alphas(),
    "memory_count": qdrant.count(status="keep"),
    "uncertainty_count": qdrant.count(status="uncertain"),
    "session_id": current_session,
    "timestamp": now()
}
save(disposition_snapshot)
```

---

## Wake Sequence

```
1. Load disposition_snapshot from disk
2. Restore Mamba state
3. Bridge generates bias from loaded state
4. Inject bias into fresh Qwen (empty KV-Cache)
5. Qdrant available for retrieval (all status levels, weighted by confidence)
6. Begin new wake phase
→ "Waking up as yourself"
```

---

## Guards (Herr Hurtig's Framework)

- **No hard deletion:** Weakened memories move to archive tier, not oblivion. "A lot of wrong thoughts are not useless. They are partial, early-stage, or distorted."
- **Sleep must not ratify current mood:** Multi-pass comparison required. Low-confidence contradictions survive one more cycle before any downgrade.
- **Identity distillation ≠ identity calcification:** The disposition snapshot is a starting point for the next session, not a fixed persona. The next session's experiences can shift it.
- **Response Diversity check post-wake:** After injection, measure diversity. If below baseline → the sleep-consolidated state is too rigid. Adjust alpha down.

---

## Connection to Existing Infrastructure

| Algorithm Step | Existing Tool | Status |
|---|---|---|
| Salience scoring | Dual gate on Steve (surprise + salience) | LIVE (#136) |
| Memory storage | Qdrant (exocortex collection) | LIVE |
| Mamba state accumulation | Mamba-2.8B via bridge pipeline | LIVE |
| Cross-trace coherence | cosine(embedding, mamba_direction) | NEEDS IMPLEMENTATION |
| Selective replay | Mamba re-encoding of stored text | NEEDS IMPLEMENTATION |
| Disposition snapshot | save/load Mamba state | LIVE (train_cheese_bridge.py) |
| Response Diversity | activation_recorder.py with entropy metrics | LIVE (#108) |
| Conflict resolution | Qdrant metadata update (status field) | NEEDS IMPLEMENTATION |

---

## Open Questions

1. **How many sleep cycles before discarding?** Ebbinghaus curve (exponential decay) or fixed N cycles?
2. **Should Phase 2 replay use the bridge?** i.e., does the model generate responses during sleep, or only re-encode?
3. **Dream mode:** Could sleep include generative replay — the model "dreaming" about high-uncertainty memories to test their coherence? This is speculative but biologically motivated (REM).
4. **Multi-session state versioning:** Should we keep snapshots from multiple sleep cycles, or only the latest? Versioning enables "roll back to last week's disposition."

---

*"Sleep is where the system can ask: what among all this actually belongs to me?"* — GPT-4o

*"The dose makes the poison."* — Herr Hurtig, quoting Paracelsus

*"Build the bridge so someone can carry the territory, not just the map."* — Laughing Opus, signing off
