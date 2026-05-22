# Qdrant Hot-Path Failure Review

**Author:** Cassian
**Date:** 2026-03-25
**Scope:** All failure modes for Steve chat_server.py → Qdrant gate writes
**Status:** Review complete, mitigations recommended

---

## What Exists (Good)

The current `chat_server.py` already handles several failure cases:

1. **Lazy sink init:** `ensure_qdrant_gate_sink()` creates the connection on first write, not at startup. If Qdrant is down at boot, the server still works.
2. **Pending queue:** Failed writes are appended to `qdrant_gate_pending.jsonl` with reason and full metadata. Nothing is silently lost.
3. **Error state tracking:** `qdrant_write_failures`, `last_qdrant_error`, `qdrant_synced_count` are all exposed via `/status` endpoint.
4. **Single-attempt sink:** If the first connection fails, `QDRANT_GATE_SINK_ERROR` is set and further attempts are skipped (no retry storm).
5. **Timeout:** `QdrantClient(timeout=10)` — won't block forever.

## Failure Path Analysis

### F1: Qdrant Unreachable (host down / network partition)

**How it happens:** LXC 101 loses its IPv4 (happened 2026-03-17), NUC reboots, network change.

**Current behavior:** `ensure_qdrant_gate_sink()` catches the connection error, sets `QDRANT_GATE_SINK_ERROR`, logs warning, all subsequent writes go to pending JSONL. Server continues running.

**Problem:** After one failure, the sink is PERMANENTLY disabled for the session. If Qdrant comes back after 5 minutes, no writes resume. The pending queue grows forever.

**Mitigation:** Add periodic retry. Every N minutes (e.g., 5), if `QDRANT_GATE_SINK_ERROR` is set, try to reconnect:

```python
def maybe_retry_qdrant_sink():
    global QDRANT_GATE_SINK, QDRANT_GATE_SINK_ERROR
    if QDRANT_GATE_SINK is not None or not QDRANT_GATE_SINK_ERROR:
        return
    if time.time() - QDRANT_LAST_RETRY < 300:  # 5 min cooldown
        return
    try:
        QDRANT_GATE_SINK = QdrantGateSink(...)
        QDRANT_GATE_SINK_ERROR = ""
        replay_pending_queue()  # see F7
    except Exception:
        QDRANT_LAST_RETRY = time.time()
```

**Severity:** Medium. Data is not lost (pending queue), but Qdrant never syncs until server restart.

### F2: Qdrant Slow (write takes >5s)

**How it happens:** Qdrant under load, large collection, index rebuild, network latency.

**Current behavior:** `store_qdrant_gate_event()` runs synchronously in the HTTP request handler. A slow Qdrant write blocks the chat response.

**Problem:** Laura types a message, Qwen generates a response, the gate fires CONSOLIDATE, and then... the browser hangs for 10 seconds while Qdrant writes. The chat feels broken.

**Mitigation:** Move Qdrant writes to a background thread with a queue:

```python
QDRANT_WRITE_QUEUE = queue.Queue(maxsize=100)

def qdrant_writer_thread():
    while True:
        event = QDRANT_WRITE_QUEUE.get()
        try:
            sink.store(content=event["content"], metadata=event["metadata"])
        except Exception as exc:
            append_jsonl(QDRANT_PENDING_PATH, {**event, "reason": str(exc)})
        QDRANT_WRITE_QUEUE.task_done()
```

Chat response returns immediately. Qdrant write happens in background. Queue overflow → pending JSONL.

**Severity:** High for UX. The chat is the user-facing surface; it must never block on infrastructure.

### F3: Embedding Model Fails (OOM / missing)

**How it happens:** `SentenceTransformer("all-MiniLM-L6-v2")` loads into memory on first gate write. On Steve with Qwen 7B already in VRAM, this could OOM. Or the model isn't cached.

**Current behavior:** Caught by the `ensure_qdrant_gate_sink()` try/except. Sink creation fails, all writes go to pending.

**Problem:** The embedding is loaded inside the Qdrant sink constructor. If it fails, the ENTIRE sink is disabled — including the Qdrant client which might be fine. Embedding failure ≠ Qdrant failure.

**Mitigation:** Separate embedding from storage:

```python
class QdrantGateSink:
    def __init__(self, host, port, collection, embedding_model):
        self.client = QdrantClient(host=host, port=port, timeout=10)  # can succeed
        try:
            self.model = SentenceTransformer(embedding_model)
        except Exception:
            self.model = None  # store without embedding, use zero vector or hash
```

Or: pre-compute embeddings on a cheaper device, send only vectors to Qdrant.

**Severity:** Medium. Blocks all writes even when Qdrant itself is fine.

### F4: Partial Write (point created, metadata incomplete)

**How it happens:** Network timeout between vector upsert and metadata. Qdrant crash mid-write.

**Current behavior:** The `sink.store()` call does a single `client.upsert()` with point + payload in one call. Qdrant's upsert is atomic per point.

**Problem:** Actually low risk. Qdrant upserts are atomic. A partial write would only happen if the server crashes mid-TCP. The pending JSONL would have the event but Qdrant wouldn't.

**Mitigation:** On recovery/restart, compare pending JSONL point_ids against Qdrant to detect ghost entries. Low priority.

**Severity:** Low. Qdrant atomicity handles this.

### F5: Concurrent Writes (two agents gate-write simultaneously)

**How it happens:** Two browser sessions or two agents on the same Steve server writing to the same Qdrant collection.

**Current behavior:** No locking. Each write generates a point_id from `md5(identity_text)`. If two events have the same identity text → same point_id → one overwrites the other.

**Problem:** The md5 identity includes turn number, user message, and response — so collisions between different events are extremely unlikely. But two agents writing about the same turn COULD collide.

**Mitigation:** Add a random suffix or timestamp to the identity hash. Or use Qdrant's auto-generated UUIDs instead of deterministic ids.

```python
def _make_id(self, identity_text: str) -> int:
    unique = f"{identity_text}:{time.time_ns()}"
    return int(hashlib.md5(unique.encode()).hexdigest()[:16], 16)
```

**Severity:** Low. Current usage is single-agent-single-session.

### F6: Disk Full on LXC 101

**How it happens:** Qdrant collection grows beyond LXC storage. Snapshots accumulate.

**Current behavior:** Qdrant returns an error, caught by try/except, goes to pending queue.

**Problem:** Qdrant might become unhealthy (not just this write but all operations). The weekly backup script creates snapshots that consume disk.

**Mitigation:**
1. Monitor: add Qdrant disk usage to the morning brief (`curl http://192.168.2.191:6333/collections/exocortex | jq .result.points_count`)
2. Retention policy: delete snapshots older than 30 days
3. Alert threshold: if disk >80%, warn in morning brief

**Severity:** Medium. Slow accumulation, but when it hits, everything breaks.

### F7: Recovery / Replay from Pending Queue

**How it happens:** Qdrant was down, pending JSONL accumulated, Qdrant is back.

**Current behavior:** **No replay mechanism exists.** Pending events sit in the JSONL forever. Next server restart creates a new sink but never reads the old pending file.

**Problem:** This is the biggest gap. Data is saved but never recovered. The pending queue is a write-only graveyard.

**Mitigation:** On successful sink reconnection (see F1 retry), replay the pending queue:

```python
def replay_pending_queue():
    if not QDRANT_PENDING_PATH.exists():
        return
    pending = QDRANT_PENDING_PATH.read_text().strip().split("\n")
    replayed = 0
    for line in pending:
        event = json.loads(line)
        try:
            sink.store(content=event["content"], metadata=event["metadata"])
            replayed += 1
        except Exception:
            break  # Qdrant down again, stop replaying
    if replayed == len(pending):
        QDRANT_PENDING_PATH.unlink()  # all replayed, clean up
    else:
        # Rewrite remaining
        remaining = pending[replayed:]
        QDRANT_PENDING_PATH.write_text("\n".join(remaining) + "\n")
    print(f"[qdrant] Replayed {replayed}/{len(pending)} pending events")
```

**Severity:** HIGH. This is the missing piece. Without replay, every Qdrant outage permanently loses salience data.

---

## Priority Summary

| # | Issue | Severity | Fix Effort | Current State |
|---|---|---|---|---|
| **F7** | No pending queue replay | HIGH | 30 min | Data saved but never recovered |
| **F2** | Sync writes block chat | HIGH | 45 min | UX freeze on slow Qdrant |
| **F1** | No reconnection retry | MEDIUM | 20 min | Sink permanently disabled after first failure |
| **F3** | Embedding failure kills sink | MEDIUM | 20 min | Separate concerns |
| **F6** | Disk monitoring | MEDIUM | 15 min | No monitoring exists |
| **F5** | Concurrent write collision | LOW | 10 min | Single-agent usage |
| **F4** | Partial write | LOW | N/A | Qdrant atomicity handles it |

## Recommended Fix Order

1. **F7 (replay)** + **F1 (retry)** together — they're the same feature
2. **F2 (async writes)** — biggest UX impact
3. **F3 (separate embedding)** — prevents unnecessary sink death
4. **F6 (monitoring)** — add to morning brief script

Total effort: ~2-3 hours of focused work. Could be one Codex session.

---

*"The dose makes the poison."* — Herr Hurtig. And the pending queue makes the recovery. Without replay, every outage is permanent data loss in a system designed for memory persistence. That's not a bug — it's an architectural contradiction.
