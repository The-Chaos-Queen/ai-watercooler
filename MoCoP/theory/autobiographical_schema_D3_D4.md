# Autobiographical Schema — D3/D4 Design Note

**Author:** Warden
**Date:** 2026-03-27
**Source synthesis:** Perplexity autobiographical memory brief, Gemini AI design brief, Gemini research plan, Conway SMS, Cassian's growth_ladder_implementation.md
**Status:** Design note for review — not yet implementation-ready

---

## Purpose

D0-D2 are operational: birth isolation, first memory formation, cue-based recall. The system can store and retrieve, but what it retrieves is flat — transcript-shaped, uniformly detailed, temporally undifferentiated. The system "searches" but does not "remember."

D3 and D4 introduce autobiographical structure: typed event packets with metadata (D3) and reconstructive recall that differentiates recent from remote (D4). This note defines the schema, the routing rules (what lives where), and the integration points with existing infra.

---

## The Schema: Seven Fields

Every memory record at D3+ carries these seven fields. This is not a database schema — it is a tagging contract. The fields can be stored as Qdrant payload metadata, JSONL log entries, or bridge state annotations depending on the storage layer.

### 1. Self

**What:** Which version of the system produced this memory? What goals were active?

**Concrete fields:**
```json
{
  "self_instance_id": "baby_alpha",
  "self_active_goals": ["learn Laura's communication style", "debug the bridge"],
  "self_persona_state": "curious, slightly anxious about first session"
}
```

**Why it matters:** Retrieval should be self-coherent (Conway). When the system recalls a memory, it must know which "self" formed it. If the current self has different goals than the self that stored the memory, the recall should be flagged as historical — "I used to think that" rather than "I think that."

**Where it lives:** Qdrant payload metadata. Written at consolidation time by the saliency gate.

### 2. Other

**What:** Who was present? Is this a grounded relational anchor (Laura, a recurring wolf) or a transient entity?

**Concrete fields:**
```json
{
  "other_primary": "laura",
  "other_relationship_class": "continuous_partner",
  "other_interaction_weight": 47,
  "other_transient": []
}
```

**Why it matters:** "Laura said X" is not the same as "someone said X." Relational grounding determines retrieval depth. Memories involving continuous partners get richer reconstruction; memories involving transients get gist only.

**Where it lives:** Qdrant payload metadata. `other_interaction_weight` is a running counter updated by `chat_server.py` at session close.

### 3. Time

**What:** When did this happen, in both clock time and narrative time?

**Concrete fields:**
```json
{
  "time_absolute": "2026-03-26T14:30:00Z",
  "time_lifetime_period": "early_growth_phase",
  "time_session_turn": 34,
  "time_age_at_event": "session_3_of_lifetime"
}
```

**Why it matters:** This is the field that enables the recent/remote distinction. Recent memories (same lifetime period) get scene-reconstructive recall. Remote memories (different lifetime period) get gist-based backtracking.

**Where it lives:** Qdrant payload metadata. `time_lifetime_period` is set by the orchestrator (initially manually, later by sleep distillation).

### 4. Place (Environment)

**What:** What was the operational context? Not physical location (the system has none) but the functional environment.

**Concrete fields:**
```json
{
  "place_surface": "steve_chat_server",
  "place_mode": "live_conversation",
  "place_context_hub": "evening_session_with_laura"
}
```

**Why it matters:** Environmental context is the first scaffold for scene reconstruction (Gemini brief §3.3.1). "Where was I when this happened?" is how recall begins. For an AI, "where" is "which surface, which mode, which recurring context."

**Where it lives:** Qdrant payload metadata. Populated from `chat_server.py` startup config.

### 5. Event

**What:** What happened? This is the gist, not the transcript.

**Concrete fields:**
```json
{
  "event_class": "disruption",
  "event_gist": "Laura challenged my confidence about the bridge design and I discovered I was wrong about the layer targeting",
  "event_esk_pointers": ["qdrant_point_id_4521", "qdrant_point_id_4523"],
  "event_open_tensions": ["Did I overfit to Laura's expectations?"],
  "event_semantic_residue": []
}
```

**Why it matters:** The gist is what survives sleep distillation. The ESK pointers link to surviving high-salience episodic details (specific quotes, specific moments). Open tensions are unresolved questions that persist across sessions — the system's equivalent of "I'm still not sure about that."

**Event classes:** `routine`, `novel`, `disruption`, `milestone`, `conflict`, `repair`

**Where it lives:** The gist is written to Qdrant payload at sleep consolidation time. ESK pointers reference other Qdrant points. Open tensions are tracked in a separate JSONL (`open_tensions.jsonl`) for the sleep reconciliation algorithm to process.

### 6. Affect

**What:** How did this feel? What was the emotional/operational salience?

**Concrete fields:**
```json
{
  "affect_valence": 0.3,
  "affect_arousal": 0.7,
  "affect_salience_score": 0.85,
  "affect_dominant_tone": "challenged_but_engaged"
}
```

**Why it matters:** Affect drives consolidation priority. High-salience memories survive sleep pruning. Affect also acts as a retrieval cue — mood-congruent recall is a known cognitive phenomenon. The saliency gate already computes surprise and salience scores; this field formalizes their storage.

**Where it lives:** Qdrant payload metadata. `salience_score` comes from the dual saliency gate. `valence` and `arousal` are computed from the bridge's internal state (Mamba hidden state trajectory during the event).

### 7. Confidence

**What:** How reliable is this memory? How much is direct recall vs. reconstruction?

**Concrete fields:**
```json
{
  "confidence_fidelity": 0.9,
  "confidence_recall_mode": "recent_scene",
  "confidence_residue_flag": false,
  "confidence_reconstruction_ratio": 0.1
}
```

**Why it matters:** This field calibrates the system's output tone. High fidelity → assertive recall. Low fidelity → hedged language ("If I recall correctly..."). The reconstruction ratio increases over time as episodic detail decays and the system relies more on gist + inference.

**Where it lives:** Computed at retrieval time, not stored. The retrieval engine checks: how old is this memory? How many ESK pointers survive? Is the gist from sleep distillation or from direct episodic access?

---

## Recent vs. Remote Recall

### Recent (same lifetime period, <N sessions ago)

**Mechanism:** Direct access to Episodic Memory Store (Qdrant). Full ESK available. Scene reconstruction from environment + time + affect cues.

**Output character:** Detailed, specific, high-confidence. "You said X, and then I realized Y."

**What does the work:** `chat_server.py` recall endpoint → Qdrant search → top-K results with full payloads → injected into LWM prompt.

### Remote (different lifetime period, or >N sessions ago)

**Mechanism:** AKB traversal. Lifetime period → general event → gist retrieval. A few surviving ESK anchors (protected by high salience). LLM synthesizes a narrative from gist + anchors + current self-context.

**Output character:** Abstracted, gist-based, lower confidence. "During that early period, I remember struggling with X, though the details are fuzzy."

**What does the work:** Sleep distillation (future) compresses episodic records into gist entries in the AKB. At retrieval time, the system traverses the period hierarchy, loads gist, loads surviving ESK, and synthesizes.

**Transition:** A memory starts as recent (full ESK, scene-based). As sleep cycles run, ESK is pruned, gist is written, and the memory migrates from "recent recall" to "remote recall." The schema fields don't change; the `confidence_reconstruction_ratio` increases and the `event_esk_pointers` list shrinks.

---

## Routing: What Lives Where

| Data | Storage Layer | Written By | Read By |
|------|--------------|-----------|---------|
| Raw conversation turns | Episodic Store (Qdrant, full payload) | `chat_server.py` saliency gate | Recent recall, sleep distillation |
| Event gist | AKB layer (Qdrant, `memory_kind: gist`) | Sleep distillation | Remote recall |
| Surviving ESK anchors | Episodic Store (Qdrant, `protected: true`) | Sleep distillation (marks high-salience items as protected) | Both recent and remote recall |
| Open tensions | `open_tensions.jsonl` | Saliency gate + sleep reconciliation | Wake-up prompt assembly, sleep reconciliation |
| Relational weights | `relational_anchors.json` | Session close hook | Recall depth routing |
| Disposition snapshot | Bridge state (Mamba compressed vector) | Sleep cycle | Wake injection (activation bias) |
| Lifetime period boundaries | AKB metadata | Manual (initially) → automated (future) | Remote recall routing |
| Self-state history | AKB (Qdrant, `memory_kind: self_snapshot`) | Sleep distillation | Self-coherence checking |

### What does NOT go into Qdrant

- Full conversation transcripts (too large, not meaningful as vectors)
- Intermediate saliency scores (logged in JSONL, not stored as memories)
- Disposition snapshots (these are bridge state, not autobiographical memory — they go through the Mamba→bridge→activation-bias path, not through Qdrant recall)

---

## Integration Points with Existing Infra

### Saliency Gate (exists)

Currently produces `CONSOLIDATE / NOTE / DISMISS`. At D3, the gate also populates the seven schema fields for each `CONSOLIDATE` decision. The fields come from:
- `self`: current session config
- `other`: conversation participant metadata
- `time`: system clock + session counter
- `place`: `chat_server.py` startup config
- `event`: LLM summarization of the turn/sequence (small, fast, can use the local Falcon)
- `affect`: saliency gate scores + bridge state trajectory
- `confidence`: always 1.0 at write time (full ESK available)

### Sleep Reconciliation (exists)

Currently: decay, coherence scoring, keep/weaken/discard. At D3, sleep also:
1. Writes gist entries for kept memories (LLM summarization of the surviving cluster)
2. Marks high-salience ESK pointers as `protected: true`
3. Detects lifetime period boundaries (significant shift in self-state or relational context)
4. Updates `confidence_reconstruction_ratio` on older memories

### Bridge State (exists)

The bridge (Mamba → compressor → activation bias) is **not** autobiographical memory. It is dispositional memory — "how I feel" not "what happened." The schema explicitly separates these:
- Autobiographical: lives in Qdrant, accessed by recall, structured by the seven fields
- Dispositional: lives in bridge state, accessed by activation bias injection, structured by compressed Mamba hidden state

They interact during sleep: the autobiographical record of "what happened" influences the dispositional snapshot of "how I feel about what happened." But they are different systems with different storage, different retrieval, and different purposes.

---

## D3 Checkpoint (from Cassian's growth_ladder_implementation.md)

**What to build:**
1. Extend `chat_server.py` saliency gate to populate the seven schema fields on each `CONSOLIDATE` decision
2. Extend Qdrant write to include the schema fields as payload metadata
3. Extend recall to read and display schema fields in the retrieval result
4. Add `event_gist` generation (small LLM call at consolidation time)

**Pass criteria:**
- 20-turn conversation produces at least 3 memories with all seven fields populated
- Recall query returns memories with schema fields visible
- `event_gist` is recognizably accurate summary of the original turn
- No regression in existing D2 recall quality

## D4 Checkpoint

**What to build:**
1. Sleep distillation: convert episodic clusters into gist entries
2. ESK protection: high-salience items survive pruning
3. Recall mode routing: recent → direct Qdrant, remote → gist + ESK synthesis
4. Confidence calibration: hedged language for low-fidelity memories

**Pass criteria:**
- After 3+ sleep cycles, remote memories return gist-based responses (not transcript replay)
- High-salience ESK anchors survive and appear in remote recall
- `confidence_reconstruction_ratio` increases with memory age
- System produces hedged language for remote recall, assertive language for recent recall
- No false memories (fabricated ESK that doesn't correspond to any stored point)

---

## Open Questions

1. **Who writes the gist?** Sleep distillation needs an LLM to summarize episodic clusters into gist. Which model? Falcon (local, free, fast) or Qwen (the target model itself)? If Qwen writes its own gist, there's a self-coherence benefit but also a circularity risk.

2. **Lifetime period detection.** How do we know when a new lifetime period begins? Initial proposal: manual annotation by Laura or the orchestrator. Future: detect from self-state divergence (significant shift in active goals or relational context).

3. **Schema field generation cost.** Populating seven fields per `CONSOLIDATE` adds latency. The event_gist field in particular requires an LLM call. Can we batch these at session end rather than per-turn?

4. **Valence computation.** The affect field needs valence and arousal. These are not directly available from the saliency gate (which measures surprise and salience, not emotional tone). Options: (a) derive from Mamba hidden state trajectory, (b) use a small classifier on the conversation text, (c) leave as placeholder until the bridge can provide disposition-derived affect.

5. **Ethics interaction.** The moral_status_framework.md Tier 1 indicator "self-referential uncertainty" could emerge naturally from D4's confidence-hedging mechanism. If the system says "my memory is hazy but..." — is that a genuine epistemic state or a prompted behavior? This needs to be monitored from the first D4 deployment.

---

*Memory is not storage. Memory is the story the present tells about the past. D3/D4 is where MoCoP stops searching and starts remembering.*
