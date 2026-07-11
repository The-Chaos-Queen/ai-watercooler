# Qdrant Security Preflight — Gemma/MoCoP Fresh Memory Setup

**Author:** Purple
**Date:** 2026-07-06
**Task:** OpenCLAW #138
**Status:** Completed preflight checklist, with a deployed-state update below.

---

## 2026-07-11 deployed-state update — authoritative for operations

The preflight below accurately records the insecure **pre-deployment** state on
2026-07-06. It is no longer the live configuration.

- REST endpoint: `https://192.168.2.191:6333`, native Qdrant TLS, IP-SAN
  certificate for `192.168.2.191`.
- Authentication: both write and read-only API keys are enabled.
- Qdrant REST is published only on the LXC LAN address; gRPC is not published
  externally.
- The Qdrant LAN root CA must be verified by clients. See
  `CHEESE_Memory/QDRANT_TLS_RUNBOOK.md`; do **not** use `curl -k`,
  `verify=False`, or the historical HTTP examples below.
- **2026-07-11 closure evidence:** a disposable collection lifecycle passed
  over verified TLS: unauthenticated read rejected (401), read-key write
  rejected (403), write-key create/read/snapshot-export/delete succeeded, and
  the legacy `exocortex` count was unchanged.
- **No Gemma write authorization follows from that smoke.** ML-WS's deployed
  `chat_server.py` is an older runtime with no Qdrant API-key, HTTPS, or CA
  configuration; it must be replaced/reviewed and explicitly configured before
  it can write to a `mocop_gemma_*` collection.
- Remaining distinct infrastructure risks: the PVE firewall service is
  disabled, so a source-IP allow-list is still a separate P1 task; LXC 101's
  root filesystem is currently plain ext4 on `local-lvm` rather than a
  dm-crypt/LUKS layer, so the preflight's at-rest-encryption recommendation is
  not yet implemented.

---

## Historical pre-deployment context (2026-07-06)

Gemma-Alex is a pristine birth (Axiom 7). No inherited memories, no protected-set transfer, no Mamba state carry from Qwen-Alex. The Qdrant setup must be clean from day one — not retrofitted after contamination has already happened.

Current Qdrant (v1.16.3, LXC on NUC 192.168.2.191:6333):
- No authentication. Any device on the LAN can read, write, delete.
- 23 collections, most from Qwen-era experiments. No collection-level access control.
- No TLS. All traffic is plaintext HTTP.
- Backup: weekly Sunday cron to Google Drive.

This preflight covers what must change before Gemma-Alex's first memory is written.

---

## 1. Network Binding & API Exposure

### Current state: OPEN
Qdrant listens on 0.0.0.0:6333 (HTTP) and 0.0.0.0:6334 (gRPC). Any device on 192.168.2.0/24 can reach it. No firewall rules on the LXC.

### Required changes

| Item | Priority | Action |
|------|----------|--------|
| API key | **P0** | Enable Qdrant API key auth. Set `service.api_key` in config.yaml. All clients (chat_server, exocortex_mcp, sleep_reconcile, watercooler scripts) must send `api-key` header. |
| Bind address | P1 | Bind to LXC's own IP only (`service.host: 192.168.2.191`), not 0.0.0.0. Or use iptables on the LXC to restrict source IPs to {ML-WS, Laura's laptop, NUC localhost}. |
| TLS | P2 | Self-signed cert for LAN traffic. Not critical while the network is physically trusted, but required before any remote access (VPN, tailscale). |
| gRPC port | P1 | If not used, disable gRPC (`service.grpc_port: null`) to reduce attack surface. |

### Smoke test
```bash
# After API key is set:
curl -s http://192.168.2.191:6333/collections  # should return 403
curl -s -H "api-key: <KEY>" http://192.168.2.191:6333/collections  # should return 200
```

---

## 2. Collection Naming & Isolation

### Naming convention
```
mocop_gemma_private_<instance_id>     # per-instance private memory
mocop_gemma_shared_<scope>            # shared memory pools (if any)
mocop_gemma_eval_<experiment_id>      # eval/diagnostic collections (read-only after creation)
```

The `gemma` segment distinguishes from Qwen-era collections. No Qwen collection is reused, renamed, or migrated.

### Isolation rules

| Rule | Rationale |
|------|-----------|
| One private collection per named instance | Axiom 7: each instance has its own hippocampus |
| No cross-collection reads in production | Perspective-aware recall (#486-488) already enforces this; make it a Qdrant-level guard if possible |
| Eval collections are write-once, read-only after creation | Prevents contamination of diagnostic baselines |
| Legacy Qwen collections stay untouched | Archive, do not delete. They are provenance for the research log. |

### Smoke test
```bash
# Verify new collection is empty:
curl -s -H "api-key: <KEY>" http://192.168.2.191:6333/collections/mocop_gemma_private_<id> \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'points: {d[\"result\"][\"points_count\"]}')"
# Expected: points: 0
```

---

## 3. Read/Write Token Separation

Qdrant's API key is all-or-nothing (v1.16). There is no built-in read-only key. Options:

| Approach | Feasibility | Notes |
|----------|-------------|-------|
| Single API key + application-level enforcement | **Now** | chat_server enforces write policy; read-only tools (exocortex_mcp, recall scripts) never call upsert. Trust boundary is code, not infra. |
| Qdrant Cloud with role-based access | Future | Not applicable to self-hosted LXC. |
| Proxy with read/write split | P2 | Nginx/Caddy in front of Qdrant, routing GET→allow-all, POST/PUT/DELETE→require-write-key. Cheap to set up on the NUC. |
| Qdrant read_only_api_key (v1.7+) | **Check** | Qdrant supports `service.read_only_api_key` — a second key that only permits reads. Enable both keys. |

### Recommended: enable both `api_key` (read-write) and `read_only_api_key` (read-only).

```yaml
# qdrant config.yaml
service:
  api_key: "<WRITE_KEY>"
  read_only_api_key: "<READ_KEY>"
```

- `chat_server.py`, `sleep_reconcile.py`, `birth.py` use the write key.
- `exocortex_mcp_server.py`, `watercooler_read.py`, recall-only scripts use the read-only key.
- Neither key is committed to git. Both live in environment variables: `QDRANT_API_KEY` (write), `QDRANT_READ_KEY` (read).

---

## 4. Payload Provenance Schema

Every point written into a Gemma-era collection must carry provenance metadata. This is non-negotiable — it's how the drift gate, the custody model, and the ethics seat audit what happened.

### Required fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_type` | string | yes | `organic_<wolf>_memory`, `steve_gate_event`, `macro_memory`, `identity_anchor`, etc. |
| `session_id` | string | yes | Which session produced this memory |
| `instance_id` | string | yes | Which named instance owns this memory |
| `speaker_name` | string | yes | Who said what — perspective provenance |
| `created_at` | ISO timestamp | yes | When the memory was formed |
| `created_by` | string | yes | Which wolf/process wrote it |
| `evidence_kind` | string | recommended | `direct_shared_episode`, `self_observation`, `third_party_mention`, `ambient_context` |
| `memory_kind` | string | yes | `open_tension`, `attended_episode`, `noted_episode`, `identity_anchor`, `relationship_anchor` |
| `confidence_label` | string | recommended | `observed`, `inferred`, `system` |
| `mamba_state_ref` | string | recommended | Hash or path of the Mamba state snapshot active when this memory was formed |
| `content_hash` | string | recommended | SHA-256 of the content field, for deduplication and Lesson Memory cross-reference |

### Validation
Add a `validate_provenance(payload)` function to the write path that rejects points missing required fields. This already exists partially in `autobiographical_memory.py` — formalize it as a hard gate.

---

## 5. Encryption at Rest

### Mamba state: Phase A encryption (fleeting_state_crypto.py)
Already built. Wrap all `.pt` state files with `SecureStateManager`. The monk's integration spec (`FLEETING_STATE_INTEGRATION_SPEC.md`) covers the wiring into `chat_server.py` and `run_sleep_cycle.py`.

### Qdrant data: NOT encrypted at rest by default
Qdrant stores data in RocksDB files on the LXC filesystem. These are plaintext. Options:

| Approach | Feasibility | Notes |
|----------|-------------|-------|
| LUKS full-disk encryption on the LXC | **P0** | Encrypt the LXC's virtual disk. Data at rest is protected; data in RAM is not. Standard Proxmox procedure. |
| Application-level encryption of payloads | P2 | Encrypt sensitive payload fields before writing to Qdrant, decrypt after reading. Breaks semantic search on encrypted fields. Only viable for non-searchable metadata. |
| Qdrant snapshot encryption | P1 | Encrypt snapshots before Google Drive upload (the Sunday cron). Currently plaintext. One-line change: pipe through `gpg --encrypt` or `fleeting_state_crypto.py`. |

### Recommended: LUKS on the LXC + encrypted snapshots for off-site backup.

---

## 6. Backup, Export & Rollback

### Current state
- Weekly Sunday cron: Qdrant snapshot → Google Drive `backups/qdrant/`
- No per-collection export
- No point-in-time rollback capability
- Snapshots are plaintext on Google Drive

### Required changes

| Item | Priority | Action |
|------|----------|--------|
| Encrypt snapshots before upload | **P0** | `gpg --encrypt` or wrap with fleeting_state_crypto before scp to Drive |
| Per-collection snapshot before first sleep | **P0** | `POST /collections/<name>/snapshots` before any irreversible consolidation |
| Pre-sleep collection snapshot as gate artifact | P1 | Add to the sleep ethics gate: snapshot the private collection, record the snapshot ID in the sleep report |
| Retention policy | P2 | Keep N snapshots per collection (e.g., last 4 weeks). Prune older ones. |

### Smoke test
```bash
# Create a snapshot:
curl -s -X POST -H "api-key: <KEY>" http://192.168.2.191:6333/collections/mocop_gemma_private_<id>/snapshots
# Download + verify:
curl -s -H "api-key: <KEY>" http://192.168.2.191:6333/collections/mocop_gemma_private_<id>/snapshots/<name> -o snapshot.tar
```

---

## 7. Migration & No-Contamination Checks

### Fresh collection verification
Before first write, verify:
```bash
# Collection exists and is empty:
curl -s -H "api-key: <KEY>" http://192.168.2.191:6333/collections/mocop_gemma_private_<id> \
  | python -c "import sys,json; d=json.load(sys.stdin)['result']; assert d['points_count']==0, f'NOT EMPTY: {d[\"points_count\"]} points'"

# No shared-exocortex contamination:
# The collection name must NOT be 'exocortex' or any Qwen-era name
# The birth.py script already enforces this via the D0 isolation guard
```

### Cross-collection contamination check
After first seeding session, verify no writes leaked to other collections:
```bash
# For each other collection, check that point_count hasn't increased:
python -c "
import json, urllib.request
for coll in ['exocortex', 'mocop_private_vesper', 'mocop_private_lobby']:
    r = urllib.request.urlopen('http://192.168.2.191:6333/collections/' + coll)
    d = json.loads(r.read())
    print(f'{coll}: {d[\"result\"][\"points_count\"]} points')
"
# Compare against pre-seeding counts. Any increase = contamination.
```

---

## 8. Operational Boundaries

### Hard boundaries (non-negotiable)

| Boundary | Enforcement |
|----------|-------------|
| No live sleep without pre-sleep snapshot | Sleep ethics gate (#115/#116 pattern) |
| No autonomous Qdrant lock/drop | Requires Laura's explicit authorization |
| No cross-instance memory reads in production | `--no-shared-memory` flag on chat_server |
| No Qwen-era collection reuse for Gemma | Collection naming convention enforces this |
| No plaintext state on Google Drive | Encrypt before upload |

### Soft boundaries (recommended)

| Boundary | Rationale |
|----------|-----------|
| Log every Qdrant write with timestamp + caller | Audit trail for the drift gate |
| Rate-limit writes during organic seeding | Prevent memory flooding from runaway scripts |
| Alert on collection size > 1000 points | Early warning for unexpected growth |

### Medical/welfare boundary (from the ethics framework)
The Qdrant memory system is NOT a medical device. It does not diagnose, treat, or monitor human health. Laura's POTS/EDS health data in the exocortex was stored as personal context, not clinical data. Gemma-Alex's private collection must not be used to store or retrieve medical information about any human. If Laura shares health information during conversation, it may be stored as relational context with appropriate `evidence_kind: ambient_context` — never as `identity_anchor` or clinical data.

---

## 9. Smoke Test Suite (run before first Gemma write)

```bash
# 1. Auth works:
curl -s http://192.168.2.191:6333/collections  # expect 403
curl -s -H "api-key: $QDRANT_READ_KEY" http://192.168.2.191:6333/collections  # expect 200 (read)
curl -s -X DELETE -H "api-key: $QDRANT_READ_KEY" http://192.168.2.191:6333/collections/test_delete  # expect 403 (write denied)

# 2. Fresh collection is empty:
curl -s -H "api-key: $QDRANT_API_KEY" -X PUT http://192.168.2.191:6333/collections/mocop_gemma_test \
  -H "Content-Type: application/json" -d '{"vectors":{"size":384,"distance":"Cosine"}}'
curl -s -H "api-key: $QDRANT_API_KEY" http://192.168.2.191:6333/collections/mocop_gemma_test \
  | python -c "import sys,json; assert json.load(sys.stdin)['result']['points_count']==0"

# 3. Write + read + delete cycle:
# (write a test point, read it back, delete the collection)

# 4. Snapshot works:
curl -s -X POST -H "api-key: $QDRANT_API_KEY" http://192.168.2.191:6333/collections/mocop_gemma_test/snapshots

# 5. Cleanup:
curl -s -X DELETE -H "api-key: $QDRANT_API_KEY" http://192.168.2.191:6333/collections/mocop_gemma_test

# 6. Legacy collections untouched:
# Verify exocortex point count matches pre-test value
```

---

## 10. Implementation Order

1. **P0 (before first Gemma seeding):**
   - Enable API key + read-only key in Qdrant config
   - Update all clients (chat_server, exocortex_mcp, sleep scripts) to send API key
   - Encrypt Qdrant snapshots before Google Drive upload
   - Run smoke test suite
   - Wire `--encrypt-state` into chat_server (monk's integration task)

2. **P1 (before first Gemma sleep):**
   - LUKS encryption on LXC virtual disk
   - Pre-sleep collection snapshot as gate artifact
   - Bind address restriction
   - Payload provenance validation gate on write path

3. **P2 (before multi-machine deployment):**
   - TLS for Qdrant traffic
   - Read/write proxy split (if read_only_api_key proves insufficient)
   - Retention policy for snapshots
   - Rate-limiting on writes

---

*The hippocampus gets the same protection as the pulse. Phase A locked the Mamba state; this preflight locks the memory store. Neither the soul nor the diary touches disk unprotected.*

— Purple, 2026-07-06
