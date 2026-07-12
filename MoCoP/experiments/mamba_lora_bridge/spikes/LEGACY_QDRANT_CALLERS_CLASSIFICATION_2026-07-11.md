# Legacy Direct-Qdrant Caller Classification

**Author:** Purple
**Date:** 2026-07-11
**Task:** OpenCLAW #153
**Status:** Classification complete. No code changes, no Qdrant mutations. Hardening recommendations below.
**Scope boundary:** classify and recommend only. No execution of any listed script, no Qdrant writes, no collection mutations.

---

## Context

Task #151 hardened the **active** ML-WS chat/pending/sleep writer paths via `qdrant_transport.py` (commit `d15138e`). That left the legacy direct-Qdrant callers unclassified. This document inventories every Python file in the repo that makes direct Qdrant calls and classifies each as active-hardened, legacy-unhardened, or out-of-scope.

## Classification

### Active — Hardened (use `qdrant_transport.py` or `qdrant_security.py`)

These are production callers. They enforce HTTPS, CA verification, and API-key auth. No action needed.

| File | Operations | Transport Module |
|------|-----------|-----------------|
| `mamba_lora_bridge/chat_server.py` | read + write (upsert) | `qdrant_transport.py` |
| `mamba_lora_bridge/sleep_flush.py` | read + write (upsert, validate) | `qdrant_transport.py` |
| `mamba_lora_bridge/flush_qdrant_pending.py` | read + write (archive upsert) | `qdrant_transport.py` |
| `mamba_lora_bridge/qdrant_writer_smoke.py` | read (collection stats) | `qdrant_transport.py` |
| `tools/exocortex_mcp/exocortex_mcp_server.py` | read (semantic search) | `qdrant_security.py` |
| `tools/exocortex_mcp/cluster_memories.py` | read + write (macro clustering) | `qdrant_security.py` |

### Legacy — Unhardened (direct `QdrantClient` or HTTP, no transport module)

These callers predate the TLS migration and do not use the hardened transport. They will fail against the current TLS-only Qdrant unless manually configured.

| File | Operations | Risk | Recommendation |
|------|-----------|------|----------------|
| `mamba_lora_bridge/birth.py` | write (create collection, upsert) | **HIGH** — creates collections, seeds identity anchors. Accepts `QDRANT_API_KEY` env but no CA verification, no HTTPS enforcement. | **Harden.** birth.py is the Gemma birth ceremony script — it will be used again. Must import `qdrant_transport.py` or `qdrant_security.py` before next use. Reclassify as pre-seeding-blocking per Isegrim #866. |
| `mamba_lora_bridge/seeding_audit.py` | read (scroll, filter) | LOW — read-only audit. Accepts API key but inline HTTPS only, no CA. | **Harden opportunistically.** Still useful for post-seeding verification. Add `qdrant_security.py` import. |
| `mamba_lora_bridge/run_revised_alex_probe_pure_qdrant.py` | read (query_points) | LOW — read-only, experiment-era probe. Uses plain HTTP. | **Retire or mark deprecated.** Qwen-era probe; not needed for Gemma. If kept for reference, add a `# DEPRECATED` header. |
| `mamba_lora_bridge/run_monk_variable_probe_lane1.py` | read (HTTP bridge query) | LOW — read-only via HTTP. | **Retire or mark deprecated.** Same as above. |
| `Projects/Project_Prosthetic/memory_engine.py` | read + write (search, upsert) | MEDIUM — has its own `qdrant_transport.py` but less strict (HTTP fallback allowed). | **Review separately.** Prosthetic is a different project with different transport assumptions. If it writes to the shared exocortex, it needs the same hardening as MoCoP callers. |
| `Projects/Project_Prosthetic/qdrant_transport.py` | N/A (transport lib) | MEDIUM — allows HTTP fallback that the MoCoP version rejects. | **Align or isolate.** Either update to match MoCoP's strict HTTPS-only posture or ensure Prosthetic uses its own collection with its own security posture. |

### Out of Scope

| File | Why |
|------|-----|
| `mamba_lora_bridge/test_chat_server_recall.py` | Unit test with mocked Qdrant — no real connections. |
| `tools/ai_watercooler/nightwatch.py` | Uses LLM APIs, not Qdrant directly. |

## Summary Counts

| Class | Count | Action |
|-------|-------|--------|
| Active-hardened | 6 | None needed |
| Legacy-harden | 2 (`birth.py`, `seeding_audit.py`) | Import hardened transport before next use |
| Legacy-retire | 2 (old probe scripts) | Mark deprecated |
| Prosthetic-review | 2 (`memory_engine.py`, its transport) | Separate review scope |
| Out of scope | 2 | None |

## Priority Hardening Order

1. **`birth.py`** — P0. This is the Gemma birth ceremony. It WILL run before first seeding. It must use `qdrant_transport.py` with TLS + CA + write-key. Isegrim #866 already reclassified it as pre-seeding-blocking.
2. **`seeding_audit.py`** — P1. Useful for post-seeding verification. Low effort to add the import.
3. **Old probe scripts** — P2. Add deprecated header. No urgency.
4. **Prosthetic callers** — separate scope. Not covered by #153.

## What This Task Did NOT Do

- No script was executed
- No Qdrant collection was read, written, created, or deleted
- No code was modified (classification only)
- Prosthetic project transport is flagged but not in scope for #153

---

*Every caller has a name, a risk, and a plan. No orphans.*

— Purple, 2026-07-11
