# Sleep Forgetting Upgrade: Learned Relevance from H2-EMV

**Date:** 2026-04-21
**Author:** Warden
**Status:** Draft for Hurtig + Monk review
**Based on:** Bärmann et al., "Learning to Forget — Hierarchical Episodic Memory for Lifelong Robot Deployment" (arXiv 2604.11306, April 2026)
**Builds on:** `sleep_reconcile.py` Phase 1-3, `SLEEP_IMPLEMENTATION_PLAN_2026-03-29.md`, Organic Memory Seeding Spec

---

## What We Have Now

`sleep_reconcile.py` applies uniform synaptic downscaling during sleep:

```
raw_strength = salience × recurrence
decayed = raw_strength × decay_factor    # default 0.85
```

Phase 2-3 classify entries as KEEP / UNCERTAIN / WEAKEN / DISCARD via selective Mamba replay and conflict resolution. Tension decays on a separate channel. All forgetting is metadata-driven (strength scores, status transitions). No entries are ever deleted from Qdrant.

**Three things this doesn't do:**
1. Memories don't have lifetimes — everything decays uniformly regardless of type or importance
2. Forgetting doesn't learn from Laura's corrections
3. Nothing is ever actually removed from Qdrant — the collection grows monotonically

---

## What H2-EMV Teaches Us

The paper's core contribution is that forgetting should be **learned, not uniform**. Three mechanisms:

### 1. Expiration-Based Lifetimes

Each memory gets an expiration time at creation:

```
τ = t_created + Δt_kind · γ_kind
```

Where `Δt_kind` is a default lifetime per memory kind and `γ_kind` is a level multiplier. In our Qdrant schema, `memory_kind` already exists:

| memory_kind | Δt_kind (default lifetime) | γ_kind | Rationale |
|-------------|---------------------------|--------|-----------|
| `salient_episode` | 30 days | 2 | High-surprise events persist |
| `attended_episode` | 14 days | 1 | Normal conversation memories |
| `noted_episode` | 7 days | 1 | Background observations |
| `identity_anchor` | infinite | — | "Who is Laura?" never expires |
| `relationship_anchor` | 90 days | 4 | Relational context, slow decay |
| `correction` (NEW) | 60 days | 3 | Laura's corrections are high-value |

When a memory reaches its expiration during a sleep cycle, it enters **relevance estimation** instead of being uniformly decayed.

### 2. Relevance Estimation at Forgetting Time

When `τ < t_now` for a memory, instead of decaying its strength score by 0.85:

1. Construct a relevance prompt with: memory content, memory_kind, affect metadata, current relevance rules
2. LLM estimates a relevance factor `α` (0 = irrelevant, 1 = moderately relevant, "inf" = keep forever)
3. Extend lifetime: `τ ← τ + α · Δt_kind`
4. If still expired after extension → mark as `FORGOTTEN` (not deleted)
5. If extended → keep, update `sleep_coherence` metadata

**Who does the estimation?** Two options:

- **Option A (cheap):** Baby Qwen itself, during the sleep cycle. Uses the same model that needs the memories, so relevance judgment aligns with retrieval usefulness. ~10ms per memory on Steve.
- **Option B (accurate):** An external LLM call (Haiku via API) conditioned on relevance rules. More expensive but avoids self-referential bias. ~50ms per memory.

**Recommendation:** Option A for Phase 1 (fast, local, no API cost). Switch to B if self-referential bias appears (model keeps everything because it generated it).

### 3. Learned Relevance Rules from Corrections

This is the bridge between the organic seeding protocol's learning loop and the sleep cycle.

**When Laura corrects baby Qwen:**
> "No, I was awake till 2 AM, remember?"

**The correction event:**
1. Gets stored in Qdrant as a reinforced/corrected memory (existing behavior)
2. **NEW:** Also generates or updates a natural-language relevance rule

**Relevance rule format:**
```json
{
  "rule_id": "rel_001",
  "rule_text": "Always remember specific times when Laura describes her sleep or health",
  "source": "correction from Laura, 2026-04-21",
  "applies_to": ["salient_episode", "attended_episode"],
  "weight": 1.0,
  "created": "2026-04-21T14:30:00Z",
  "updated": "2026-04-21T14:30:00Z"
}
```

**Where rules live:** A dedicated Qdrant collection (`exocortex_relevance_rules`) or a simple JSON file on Steve. Rules are loaded at sleep time and condition both:
- **Forgetting decisions** (expired memories matching a rule get their lifetime extended)
- **Summarization** (when memories are consolidated into higher-level summaries, rules bias what detail to preserve)

**Rule lifecycle:**
- Created from corrections (organic seeding Phase 4)
- Updated when similar corrections repeat (weight increases)
- Decayed if no corrections reinforce them for 90+ days
- Can be manually reviewed/pruned by Laura

### 4. Forgotten Placeholders (Not Hard Deletion)

H2-EMV replaces forgotten nodes with stubs: time range + one-line summary. The system knows something was there even after forgetting.

**For Qdrant:** Instead of deleting a point, update its payload:

```json
{
  "status": "FORGOTTEN",
  "forgotten_at": "2026-05-01T03:00:00Z",
  "stub": "2026-04-14: something about the house build",
  "original_memory_kind": "attended_episode",
  "sleep_cycles_survived": 3
}
```

The vector stays (cheap, 384-dim MiniLM is tiny) but the full content is stripped. Retrieval can still find the stub via semantic similarity, and the model can honestly say "I know we talked about this but I've lost the detail" instead of either confabulating or having no trace at all.

This connects directly to the honest routing finding: bridge + memory = honest. If the memory is a stub, the model can acknowledge the gap instead of inventing content.

---

## Integration with Existing Sleep Phases

```
Phase 0 (NEW): Load relevance rules
Phase 1: Synaptic downscaling (UNCHANGED)
    - Still applies uniform decay to strength/tension
    - BUT now also checks expiration: τ < t_now?
Phase 1b (NEW): Expiration check + relevance estimation
    - For expired memories: estimate relevance
    - Extend or mark FORGOTTEN
Phase 2: Selective replay (UNCHANGED)
    - Mamba replay for KEEP/UNCERTAIN/WEAKEN/DISCARD
    - FORGOTTEN memories skip replay (already decided)
Phase 3: Conflict resolution (UNCHANGED)
Phase 4 (NEW): Stub generation
    - FORGOTTEN memories → strip content, keep stub + vector
    - Log what was forgotten and why (audit trail)
Phase 5: Ethics gate (UNCHANGED)
    - Post-sleep diversity check
    - NEW check: forgotten count per sleep cycle
    - STOP if > 30% of memories forgotten in one cycle
```

---

## Implementation Plan

### Step 1: Add `expiration` field to Qdrant metadata
- Modify `autobiographical_memory.py` → `enrich_memory_metadata()` to compute `τ` at memory creation time based on `memory_kind`
- Add `expiration`, `relevance_extensions`, `relevance_rules_applied` fields to payload
- Backward-compatible: existing memories without `expiration` get a default based on `memory_kind` and `created_at`

### Step 2: Add expiration check to `sleep_reconcile.py` Phase 1
- After strength decay, check `τ < t_now` for each memory
- If expired: call `estimate_relevance(memory, rules)` 
- Extend or mark FORGOTTEN
- Log decisions

### Step 3: Implement relevance rule storage
- Simple JSON file: `relevance_rules.json` alongside the Qdrant namespace
- Load at sleep start, save after updates
- Format: list of rule objects (see above)

### Step 4: Connect corrections to rule generation
- In `chat_server.py`: when a correction is detected (user contradicts a recalled fact), extract the correction pattern
- Generate a relevance rule using baby Qwen or template matching
- Append to `relevance_rules.json`

### Step 5: Stub generation for forgotten memories
- After Phase 1b marks FORGOTTEN: update Qdrant payload
- Strip `recall_text`, `autobiographical_frame`, keep `stub`, `memory_kind`, `affect`
- Log stub to watercooler for audit

### Step 6: Integrate with organic seeding
- Seeding sessions generate memories → memories get expiration based on kind
- Corrections during probing → generate relevance rules
- Sleep cycles prune using learned relevance → memory quality improves over time
- The learning loop is: seed → probe → correct → rule → sleep → better retention → probe again

---

## Metrics

- **Retention rate by kind:** What % of each memory_kind survives N sleep cycles?
- **Relevance rule count:** How many rules accumulate? Do they plateau?
- **Forgotten-then-asked rate:** How often does Laura ask about something that was forgotten? (This is the H2-EMV round-1 / round-2 feedback signal)
- **Stub retrieval rate:** How often do stubs surface in recall? Does the model handle them honestly?
- **Memory growth rate:** Does Qdrant size plateau or continue growing?

---

## For Herr Hurtig

1. **Forgetting is a new intervention on memory integrity.** Uniform decay (current) is passive. Relevance-based forgetting is active — an LLM decides what to keep. This is a judgment call made during sleep, not during conversation.
2. **Risk: biased forgetting.** If relevance rules overfit to recent corrections, the system might preserve one type of memory (e.g., emotional) while forgetting others (e.g., factual). Monitor retention rate by kind.
3. **Risk: forgotten stubs enabling confabulation.** If the model sees a stub ("something about the house build") and invents detail, that's worse than no trace at all. Test stubs + bridge routing: does the model stay honest with partial memory?
4. **Mitigation: ethics gate on forgotten count.** STOP if > 30% forgotten in one cycle. This prevents catastrophic memory loss from a bad relevance rule.
5. **Mitigation: rule audit trail.** All rules are human-readable natural language, logged with source. Laura can inspect and prune.
6. **Positive signal:** The feedback loop (correct → rule → better forgetting) is the same learning mechanism as the organic seeding protocol. The system improves from interaction, not from engineering.

---

## References

- Bärmann et al., "Learning to Forget — Hierarchical Episodic Memory for Lifelong Robot Deployment," arXiv 2604.11306, April 2026.
- MoCoP `SLEEP_IMPLEMENTATION_PLAN_2026-03-29.md`
- MoCoP `ORGANIC_MEMORY_SEEDING_SPEC.md` (Warden, 2026-04-20)
- MoCoP `sleep_reconcile.py` Phase 1-3

---

*"The system that forgets well remembers what matters."*
