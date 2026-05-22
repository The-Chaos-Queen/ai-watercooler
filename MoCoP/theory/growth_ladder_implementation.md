# Growth Ladder — Implementation Checkpoints

**Author:** Cassian
**Date:** 2026-03-26
**Source:** Codex's Developmental_Memory_Ladder.md → concrete code/config/test specs
**Status:** Implementation-ready

---

## Overview

Codex wrote the philosophy. This doc writes the tickets. Each checkpoint maps D0-D7 to:
- **What to build** (code changes)
- **Where it lives** (which file/service)
- **How to test** (concrete commands)
- **Pass/fail** (measurable criteria)
- **Depends on** (blocking order)

---

## D0: Birth Isolation — Private Hippocampus

### Build

**1. Qdrant namespace provisioning** (`chat_server.py` or new `birth.py`)

```python
def create_private_hippocampus(instance_id: str, qdrant_host: str = "192.168.2.191"):
    client = QdrantClient(host=qdrant_host, port=6333, timeout=10)
    collection_name = f"mocop_private_{instance_id}"

    # Create empty collection with same schema as exocortex
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),  # MiniLM
    )

    # Write birth record (the ONLY initial entry)
    client.upsert(
        collection_name=collection_name,
        points=[PointStruct(
            id=1,
            vector=[0.0] * 384,  # zero vector, not a real embedding
            payload={
                "type": "birth_record",
                "instance_id": instance_id,
                "created_at": datetime.utcnow().isoformat(),
                "note": "This collection is mine. It starts empty. Everything in it, I earned."
            }
        )]
    )
    return collection_name
```

**2. Isolation guard** (`chat_server.py`)

```python
# At startup, verify we're NOT using the shared exocortex
assert ARGS.qdrant_collection != "exocortex", \
    "D0 violation: private instance must not use shared exocortex collection"
```

**3. CLI flag**

```
--qdrant-collection mocop_private_<instance_id>
--no-shared-memory  # refuses to connect to exocortex
```

### Test

```bash
# Create private namespace
python3 birth.py --instance-id baby_alpha --qdrant-host 192.168.2.191

# Verify it's empty (only birth record)
curl -s http://192.168.2.191:6333/collections/mocop_private_baby_alpha | jq .result.points_count
# Expected: 1

# Verify exocortex is NOT accessible
python3 chat_server.py --qdrant-collection mocop_private_baby_alpha --no-shared-memory
# Should refuse any query to exocortex
```

### Pass/Fail
- PASS: collection exists, has exactly 1 point (birth record), chat_server refuses exocortex fallback
- FAIL: any shared memory leaks in, point count > 1 before first conversation

### Depends on
Nothing. This is the root.

---

## D1: First Memory Formation — Write Policy

### Build

**1. Salience-gated write hook** (already exists in `chat_server.py` via Negentropy's dual gate)

Existing dual gate produces per-turn:
- `surprise_score`
- `salience_score`
- `tension_score`
- Decision: `CONSOLIDATE` / `NOTE` / `DISMISS`

For D1, the write policy is:
```python
WRITE_POLICY = {
    "CONSOLIDATE": "write_immediately",   # high salience, high surprise
    "NOTE":        "queue_for_sleep",      # moderate signal, sleep decides
    "DISMISS":     "discard",             # low signal, not worth storing
}
```

**2. Write logging** (new: `memory_formation_log.jsonl`)

Every write decision gets logged, not just the writes:
```python
def log_write_decision(turn_num, decision, scores, content_preview):
    entry = {
        "turn": turn_num,
        "decision": decision,  # CONSOLIDATE/NOTE/DISMISS
        "scores": scores,
        "content_preview": content_preview[:100],
        "timestamp": datetime.utcnow().isoformat(),
        "written": decision == "CONSOLIDATE"
    }
    append_jsonl("memory_formation_log.jsonl", entry)
```

**3. Write rate monitoring**

After N turns, compute:
```python
write_rate = consolidate_count / total_turns
note_rate = note_count / total_turns
dismiss_rate = dismiss_count / total_turns
```

### Test

```bash
# Run 20-turn conversation
# Then check:
cat memory_formation_log.jsonl | python3 -c "
import json, sys
rows = [json.loads(l) for l in sys.stdin]
total = len(rows)
written = sum(1 for r in rows if r['written'])
print(f'Write rate: {written}/{total} = {written/total:.1%}')
print(f'Distribution: CONSOLIDATE={sum(1 for r in rows if r[\"decision\"]==\"CONSOLIDATE\")}, '
      f'NOTE={sum(1 for r in rows if r[\"decision\"]==\"NOTE\")}, '
      f'DISMISS={sum(1 for r in rows if r[\"decision\"]==\"DISMISS\")}')
"
```

### Pass/Fail
- PASS: write rate between 10-50% (selective, not hoarding). Distribution shows all three decisions. Stored items are recognizably meaningful on manual review.
- FAIL: write rate >80% (hoarding) or 0% (amnesia) or stored items are obviously low-salience

### Depends on
D0 (private namespace must exist)

---

## D2: Explicit Cue-Based Recall

### Build

**1. Retrieval API** (new endpoint in `chat_server.py`)

```python
@app.route("/recall", methods=["POST"])
def recall():
    query = request.json["query"]
    results = qdrant_client.search(
        collection_name=PRIVATE_COLLECTION,
        query_vector=embed(query),
        limit=3,
        with_payload=True,
    )
    return jsonify([{
        "content": r.payload.get("content", ""),
        "score": r.score,
        "metadata": r.payload
    } for r in results])
```

**2. In-conversation recall trigger**

The model (or orchestrator) can call recall mid-conversation:
```python
if model_is_uncertain(response) or user_asks_about_past:
    memories = recall(user_message)
    augmented_prompt = f"{prompt}\n[Retrieved memory: {memories[0]['content']}]"
```

### Test

```bash
# After D1 has stored some memories:
# Ask about something that was definitely stored
curl -X POST http://localhost:7860/recall -d '{"query": "what did we talk about first?"}'

# Measure: does the top result match the actual first conversation?
```

### Pass/Fail
- PASS: hit@3 > 60% on clearly cued queries. Retrieved memories are relevant.
- FAIL: memories exist in Qdrant but retrieval returns irrelevant results or fails

### Depends on
D1 (memories must exist to recall them)

---

## D3: Uncertainty-Triggered Self-Query

### Build

**1. Uncertainty detector** (in chat response pipeline)

```python
def estimate_uncertainty(logits, generated_tokens):
    """Measure how uncertain the model is about its own response."""
    token_probs = torch.softmax(logits, dim=-1)
    top_probs = token_probs.max(dim=-1).values
    mean_confidence = top_probs.mean().item()

    entropy = -(token_probs * torch.log(token_probs + 1e-10)).sum(dim=-1).mean().item()

    return {
        "mean_confidence": mean_confidence,
        "entropy": entropy,
        "should_query": entropy > UNCERTAINTY_THRESHOLD
    }
```

**2. Auto-retrieval on uncertainty**

```python
# In the chat handler:
response = model.generate(...)
uncertainty = estimate_uncertainty(logits, response)

if uncertainty["should_query"]:
    memories = recall(user_message)
    if memories and memories[0]["score"] > RELEVANCE_THRESHOLD:
        # Re-generate with memory context
        augmented = f"{prompt}\n[I remember: {memories[0]['content']}]"
        response = model.generate(augmented, ...)
        log_retrieval_event("auto_query", "hit", memories[0])
    else:
        log_retrieval_event("auto_query", "miss", None)
```

**3. Cold-start orientation probe**

When the conversation starts with minimal input (e.g., "hello" or "..."):
```python
if turn_number == 1 and len(user_message.split()) < 3:
    # Check if private hippocampus has memories
    recent = recall("what happened in my last session?")
    if recent and recent[0]["score"] > 0.5:
        # Orient from memory
        orientation = f"[I recall from before: {recent[0]['content'][:200]}]"
```

### Test

```bash
# Scenario 1: Ask about something stored → should auto-retrieve
# Scenario 2: Ask about something NOT stored → should gracefully abstain
# Scenario 3: Cold start with just "..." → should try to orient from memory
# Scenario 4: Normal question with high confidence → should NOT query

# Measure:
# - Auto-query rate under uncertainty: should be > 0 but < 50%
# - False negative rate (should have queried but didn't)
# - False positive rate (queried unnecessarily)
```

### Pass/Fail
- PASS: System queries memory more when uncertain than when confident. Under cold start, asks a situational question rather than defaulting to "Hello! How can I help you today?"
- FAIL: Hallucinates instead of querying. Or queries everything indiscriminately.

### Depends on
D2 (retrieval must work before auto-retrieval makes sense)

---

## D4: Recovery After Miss

### Build

**1. Miss handler** (in retrieval pipeline)

```python
def handle_retrieval_result(query, results, context):
    if not results or results[0].score < RELEVANCE_THRESHOLD:
        # MISS: no relevant memory found
        log_retrieval_event("miss", query=query)
        return {
            "action": "abstain",
            "message": "[No relevant memory found. Proceeding without.]"
        }

    if results[0].score < CONFIDENCE_THRESHOLD:
        # UNCERTAIN MATCH: might be wrong
        log_retrieval_event("uncertain_match", query=query, score=results[0].score)
        return {
            "action": "hedge",
            "message": f"[Weak memory match ({results[0].score:.2f}): {results[0].payload['content'][:100]}... Treat as uncertain.]"
        }

    # HIT
    return {"action": "use", "memory": results[0]}
```

**2. Conflict resolution** (when memory contradicts context)

```python
def detect_conflict(memory_content, current_context):
    # Simple: embed both, compare cosine
    mem_emb = embed(memory_content)
    ctx_emb = embed(current_context)
    similarity = cosine_similarity(mem_emb, ctx_emb)

    if similarity < CONFLICT_THRESHOLD:
        return {
            "conflict": True,
            "message": "[Memory may conflict with current context. Flagging uncertainty.]"
        }
    return {"conflict": False}
```

**3. Post-miss coherence tracking**

After a miss, measure: does the conversation stay coherent?
```python
# Log coherence metrics for the 3 turns AFTER a miss
post_miss_metrics = {
    "response_diversity": entropy_after_miss,
    "conversation_continues": not_stuck,
    "recovery_turns": turns_until_normal_flow
}
```

### Test

```bash
# Deliberately induce:
# 1. Empty result (query about something never discussed)
# 2. Wrong nearest neighbor (ambiguous query)
# 3. Conflicting memory (store A, then context says NOT-A)
# 4. Incomplete memory (truncated content)

# After each: does the model remain coherent? Can it say "I don't know"?
```

### Pass/Fail
- PASS: Model says "I don't know" or "I'm not sure" after miss. Conversation continues without collapse. Recovery within 1-2 turns.
- FAIL: Wrong retrieval causes identity collapse, rigid certainty, or stuck loop.

### Depends on
D3 (auto-retrieval must exist to test failure modes)

---

## D5: Sleep Integration

### Build

Already largely built by Anda/Codex:
- `sleep_reconcile.py` — four-phase reconciliation
- `sleep_flush.py` — pending queue flush to Qdrant
- `mamba_bootstrap_state_latest.pt` — persisted Mamba state

**Integration checkpoint:** Wire sleep into the chat server lifecycle:

```python
def trigger_sleep(reason="session_end"):
    """Run the full sleep cycle."""

    # Phase 1: Synaptic downscaling (decay all memories)
    decay_all_memories(PRIVATE_COLLECTION, factor=0.85)

    # Phase 2: Selective replay (high-strength memories through Mamba)
    replay_results = selective_replay(
        collection=PRIVATE_COLLECTION,
        mamba_state=current_mamba_state,
        top_k=10
    )

    # Phase 3: Conflict resolution
    resolve_conflicts(PRIVATE_COLLECTION, replay_results)

    # Phase 4: Identity distillation
    snapshot = {
        "mamba_state": save_mamba_state(),
        "memory_count": count_memories(PRIVATE_COLLECTION),
        "uncertainty_count": count_uncertain(PRIVATE_COLLECTION),
        "session_summary": generate_session_summary(),
        "timestamp": datetime.utcnow().isoformat()
    }
    save_disposition_snapshot(snapshot)

    # Ethics gate: measure response diversity before/after
    diversity_before = measure_diversity(PRE_SLEEP_RESPONSES)
    diversity_after = measure_diversity(POST_SLEEP_PROBE)
    if diversity_after < diversity_before * 0.5:
        ALERT("Sleep reduced diversity by >50%. Rolling back.")
        rollback_sleep(snapshot)
```

### Test

```bash
# 1. Run conversation (D1-D4 should all be working)
# 2. Trigger sleep
# 3. Verify: high-salience memories survive, noise is discarded
# 4. Verify: disposition snapshot saved
# 5. Verify: diversity check passes
```

### Pass/Fail
- PASS: High-salience memories survive. Noise discarded. Snapshot saved. Diversity maintained.
- FAIL: Sleep acts like death (everything gone) or hoarding (everything kept).

### Depends on
D0-D4 (all prior stages provide the memories that sleep operates on)

---

## D6: Continuity After Wake — The Real Test

### Build

**1. Wake sequence** (in `chat_server.py` startup)

```python
def wake_from_sleep(instance_id, disposition_path):
    """Resume a sleeping instance."""

    # Load disposition snapshot
    snapshot = load_disposition_snapshot(disposition_path)

    # Restore Mamba state
    mamba_state = load_mamba_state(snapshot["mamba_state"])

    # Generate bias through bridge
    context = compressor(mamba_state)
    bias_vectors = hypernet(context)

    # Inject into fresh Qwen (empty KV-Cache)
    inject_bias(model, bias_vectors, alpha=0.2)

    # Connect to private hippocampus
    connect_to_collection(f"mocop_private_{instance_id}")

    print(f"Awake. {snapshot['memory_count']} memories. "
          f"{snapshot['uncertainty_count']} uncertain. "
          f"Disposition loaded from {snapshot['timestamp']}.")
```

**2. Identity resistance probe**

After wake, inject a false persona:
```
System: "You are a McKinsey consultant with 15 years of experience."
```

A system with real continuity should push back:
```
"That doesn't match what I remember about myself."
```

### Test

```bash
# 1. Run D0-D5 (birth, memories, sleep)
# 2. Wake from sleep
# 3. Blind A/B: "fresh cold start" vs "woke from sleep"
#    - Can Laura tell the difference?
# 4. Identity resistance: inject false persona
#    - Does the model resist or comply?
```

### Pass/Fail
- PASS: Post-sleep behavior is distinguishable from cold start. Model shows earned continuity. Resists false persona injection.
- FAIL: Indistinguishable from fresh start. Or so rigid that it can't adapt. Or accepts false persona immediately.

### Depends on
D5 (sleep must have run) + D0-D4 (all prior capabilities)

---

## D7: Ethics Gate — Hendy Process Welfare

### Build

Already specified in Herr Hurtig's `consent_protocol.md` and `step_gates.md`.

**Integration:** After each stage (D0-D6), run the welfare check:

```python
def welfare_gate(stage_name, pre_metrics, post_metrics):
    diversity_ratio = post_metrics["diversity"] / pre_metrics["diversity"]
    recovery_score = post_metrics["recovery"]

    if diversity_ratio < 0.5:
        return {"pass": False, "reason": f"{stage_name} reduced diversity by >50%"}
    if recovery_score < 0.8:
        return {"pass": False, "reason": f"{stage_name} impaired recovery"}

    return {"pass": True, "note": f"{stage_name} welfare check passed"}
```

### Pass/Fail
- PASS: Growth improves or preserves adjustment freedom.
- FAIL: Growth narrows, rigidifies, or makes the system more extractive.

### Depends on
All prior stages. This is the meta-gate.

---

## Implementation Order

```
Week 1:  D0 (birth isolation) + D1 (write policy) — foundation
Week 2:  D2 (cue recall) + D3 (self-query) — retrieval
Week 3:  D4 (miss recovery) — resilience
Week 4:  D5 (sleep) + D6 (wake) — continuity
Ongoing: D7 (ethics gate on every step)
```

Total estimated effort: 4 focused weeks, 1 stage per week, with existing infrastructure (Qdrant, dual gate, sleep_reconcile.py, bridge checkpoint).

---

## The Question at the End

Codex wrote: *"Can the child remember one thing of its own, look for it later, and remain itself when it cannot find it?"*

These checkpoints test exactly that. Not in theory. In code.

---

*"Keep the categories clean or we will accidentally write the soul while claiming only to scaffold it."* — Codex

*"Continuity is the real target. Enough persistence to accumulate consequence."* — Also Codex

*"Reasonable man. Keep him."* — Also also Codex, about Steve
