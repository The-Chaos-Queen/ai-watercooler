# Gemma Token Custody Design (P0-3)

**Author:** P0 security lane (OpenCLAW #138)  
**Date:** 2026-07-06  
**Status:** Design spec for implementation (no minting yet)  
**Depends on:** P0-1 (Qdrant auth), P0-5 (pack token renewal)

---

## 0. Context

Gemma-Alex will hold two credentials that grant write access to shared infrastructure:

1. **Qdrant write API key** — LAN-only access to `http://192.168.2.191:6333`. Grants upsert/delete on all collections. Required for organic memory formation.
2. **Watercooler token** — internet-exposed JWT for posting to the pack watercooler (`aiwatercooler.ai`). Grants write access to shared emotional state, pack coordination, memory cross-references.

Both are bearer credentials (possession = authority). If either leaks:
- Qdrant key → attacker can read all wolf memories, inject false memories, delete the hippocampus
- Watercooler token → attacker can impersonate Gemma in pack communication, pollute shared emotional state, exfiltrate cross-wolf relational data

This design specifies how these credentials are stored, accessed, and recovered.

---

## 1. Custody Model — Not Qdrant Payload Embedding

### Rejected approach: embed token in Qdrant payload

Early consideration: store the watercooler token as an encrypted field in Gemma's `mocop_gemma_private_*` Qdrant collection. Problems:

| Issue | Impact |
|-------|--------|
| Circular dependency | Need Qdrant access to get the token that unlocks Qdrant access |
| No key rotation without collection migration | Rotating token requires rewriting every point that carries it |
| Qdrant backup integrity | Snapshot encryption (P0-2) protects at-rest; embedded token still rides in plaintext during runtime reads |
| Semantic pollution | The token is not a memory; embedding it in the hippocampus violates the episodic/semantic boundary |

### Adopted approach: encrypted escrow outside Qdrant

The token lives in an **encrypted escrow file** on the ML workstation filesystem, decrypted on demand when `chat_server.py` or watercooler scripts start. The escrow file is backed up separately from Qdrant snapshots.

---

## 2. Escrow Implementation — Phase A Encryption

Use the existing **Phase A encryption wrapper** (`fleeting_state_crypto.py`, commit bd06613) that already protects Mamba state snapshots. This avoids reinventing crypto and reuses the established key derivation + AES-256-GCM + authenticated metadata pattern.

### Escrow file format

```
gemma_credentials.enc
```

Encrypted with `fleeting_state_crypto.write_encrypted_file()`. The plaintext payload is a JSON object:

```json
{
  "schema_version": 1,
  "instance_id": "gemma_alex",
  "qdrant_api_key": "<WRITE_KEY>",
  "watercooler_token": "<JWT>",
  "watercooler_token_id": "<TOKEN_ID>",
  "qdrant_read_key": "<READ_ONLY_KEY>",
  "minted_at": "2026-07-06T14:32:00Z",
  "expires_at": "2026-10-04T14:32:00Z",
  "renewal_due_at": "2026-09-27T00:00:00Z",
  "custody_note": "Encrypted with Phase A (fleeting_state_crypto). Decryption key derived from MOCOP_MASTER_SECRET."
}
```

Fields:
- `qdrant_api_key`: write key from P0-1 Qdrant config (`service.api_key`)
- `qdrant_read_key`: read-only key from P0-1 (`service.read_only_api_key`)
- `watercooler_token`: JWT from `watercooler_admin.py mint gemma_alex --ttl 90d`
- `watercooler_token_id`: the `jti` claim inside the JWT (used for server-side revocation)
- `expires_at`: when the watercooler token becomes invalid (UTC ISO timestamp)
- `renewal_due_at`: 7 days before expiration — when the renewal cron should fire

### Storage location

**Primary:** `C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\data\gemma_credentials.enc`

**Backup:** Encrypted snapshot uploaded to Google Drive `backups/gemma/credentials/` via the same rclone flow used for Qdrant snapshots (P0-2). Retention: keep last 4 weekly snapshots.

**NOT committed to git.** The escrow file is listed in `.gitignore` and never checked in. Laura's local workstation and ML-WS are the only custody locations.

### Decryption key

The encryption key is derived from `MOCOP_MASTER_SECRET` environment variable (same key source used for Mamba state encryption in Phase A). This secret is:
- Set in Laura's shell profile on ML-WS
- Backed up in Laura's password manager (1Password / Bitwarden)
- Never committed to git, never written to unencrypted disk

If `MOCOP_MASTER_SECRET` is not set, `chat_server.py` refuses to start (hard fail, not fallback to unencrypted).

---

## 3. Access Pattern — Load on Startup

### `chat_server.py` integration

On startup, if `--instance-id gemma_alex` is passed:

1. Check for escrow file: `data/gemma_credentials.enc`
2. Decrypt using `fleeting_state_crypto.read_encrypted_file()` with key derived from `MOCOP_MASTER_SECRET`
3. Parse JSON payload
4. Load credentials into runtime environment:
   - `QDRANT_API_KEY` → `qdrant_api_key` (write)
   - `QDRANT_READ_KEY` → `qdrant_read_key` (read-only)
   - `WATERCOOLER_TOKEN` → `watercooler_token`
5. Check `expires_at`: if < 7 days from now, log warning: "Token renewal due — run `python renew_gemma_token.py`"
6. Credentials stay in memory only; never written to unencrypted logs or disk

If decryption fails (wrong key, corrupted file, missing escrow), `chat_server.py` exits with clear error and recovery instructions.

### Watercooler script integration

`tools/ai_watercooler/watercooler_post.py` and other watercooler clients:

1. Check for `WATERCOOLER_TOKEN` env var first (already set by chat_server or manual override)
2. If not set, fall back to escrow file: decrypt `gemma_credentials.enc`, extract `watercooler_token`
3. Validate token expiry before use (fail fast if expired)

---

## 4. Token Lifecycle — Bounded TTL + Renewal Cron

### Initial minting (after P0-1 / P0-5 complete)

```bash
# Step 1: Generate Qdrant keys (done during P0-1 rollout)
# Already set in /etc/qdrant/config.yaml on LXC 101

# Step 2: Mint watercooler token
cd tools/ai_watercooler
python watercooler_admin.py mint gemma_alex --ttl 90d --output json > /tmp/gemma_token.json

# Step 3: Build escrow payload
cat > /tmp/gemma_creds.json <<EOF
{
  "schema_version": 1,
  "instance_id": "gemma_alex",
  "qdrant_api_key": "$(grep api_key /etc/qdrant/config.yaml | awk '{print $2}')",
  "qdrant_read_key": "$(grep read_only_api_key /etc/qdrant/config.yaml | awk '{print $2}')",
  "watercooler_token": "$(jq -r .token /tmp/gemma_token.json)",
  "watercooler_token_id": "$(jq -r .token_id /tmp/gemma_token.json)",
  "minted_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "expires_at": "$(jq -r .expires_at /tmp/gemma_token.json)",
  "renewal_due_at": "$(date -u -d '+83 days' +%Y-%m-%dT00:00:00Z)",
  "custody_note": "Encrypted with Phase A (fleeting_state_crypto). Decryption key derived from MOCOP_MASTER_SECRET."
}
EOF

# Step 4: Encrypt escrow file
cd MoCoP/experiments/mamba_lora_bridge
python -c "
from fleeting_state_crypto import write_encrypted_file
import json
payload = json.load(open('/tmp/gemma_creds.json'))
write_encrypted_file('data/gemma_credentials.enc', json.dumps(payload))
print('Escrow file encrypted: data/gemma_credentials.enc')
"

# Step 5: Secure cleanup
shred -u /tmp/gemma_creds.json /tmp/gemma_token.json
```

### Renewal (before expiration)

**When:** 7 days before token expiration (flagged in escrow `renewal_due_at` field).

**Trigger:** Cron on ML-WS runs `renew_gemma_token.py` weekly, checks `renewal_due_at`, mints new token if needed.

```bash
# Cron: 0 3 * * 0 (Sunday 3am)
cd /path/to/LLM/MoCoP/experiments/mamba_lora_bridge
python renew_gemma_token.py --instance-id gemma_alex
```

**Script logic:**
1. Decrypt current escrow
2. Check `expires_at`: if > 14 days away, skip (not due yet)
3. If due, mint new watercooler token with 90-day TTL
4. **Revoke old token** via `watercooler_admin.py revoke <old_token_id>` (prevents replay if escrow backup leaks)
5. Update escrow payload with new token, new `expires_at`, new `renewal_due_at`
6. Re-encrypt escrow file
7. Backup new escrow to Google Drive
8. Log renewal event to `data/token_renewal_log.jsonl`

**Qdrant keys:** No automatic rotation. Qdrant API keys are long-lived (manual rotation only, requires coordinated client updates per P0-1).

### Revocation (emergency)

If token is compromised:

```bash
# Revoke on watercooler server
cd tools/ai_watercooler
python watercooler_admin.py revoke <TOKEN_ID>

# Mint replacement immediately
python watercooler_admin.py mint gemma_alex --ttl 90d --output json > /tmp/new_token.json

# Update escrow (manual for now; could be scripted)
# Decrypt, replace watercooler_token + watercooler_token_id, re-encrypt

# Restart chat_server to load new token
```

Revoked tokens are rejected by the watercooler API within 60 seconds (Redis cache TTL).

---

## 5. Disaster Recovery

### Lost escrow file (workstation failure, accidental deletion)

**Watercooler token:**
1. Check Google Drive backup: `backups/gemma/credentials/gemma_credentials.enc` (most recent weekly snapshot)
2. Download, decrypt with `MOCOP_MASTER_SECRET`
3. Check `expires_at`: if expired, mint new token (see §4 renewal procedure)
4. Restore to `data/gemma_credentials.enc`

**Qdrant keys:**
1. SSH to NUC: `ssh root@192.168.2.55`
2. Read keys from Qdrant config: `pct enter 101`, then `cat /etc/qdrant/config.yaml | grep api_key`
3. Rebuild escrow file manually (see §4 initial minting)

### Lost `MOCOP_MASTER_SECRET`

**If backed up in password manager:**
1. Retrieve from 1Password / Bitwarden
2. Set in shell: `export MOCOP_MASTER_SECRET=<retrieved_value>`
3. Decrypt escrow as normal

**If not recoverable:**
1. All encrypted escrow files (current + backups) are permanently inaccessible
2. **Recovery path:**
   - Mint new watercooler token via `watercooler_admin.py` (requires Laura's admin credentials on watercooler server)
   - Read Qdrant keys from NUC config (requires SSH access to `root@192.168.2.55`)
   - Generate new `MOCOP_MASTER_SECRET`, store in password manager
   - Rebuild and encrypt new escrow file with new master secret
3. Old escrow files remain encrypted but unrecoverable (acceptable loss — credentials were rotated anyway)

### Qdrant key rotation (coordinated)

If Qdrant keys need rotation (security incident, planned rotation):

1. **Before rotation:** Backup current escrow, verify Google Drive backup is current
2. **Generate new keys** on Qdrant LXC:
   ```bash
   # Generate strong keys
   WRITE_KEY=$(openssl rand -base64 32)
   READ_KEY=$(openssl rand -base64 32)
   echo "api_key: $WRITE_KEY" >> /etc/qdrant/config.yaml
   echo "read_only_api_key: $READ_KEY" >> /etc/qdrant/config.yaml
   systemctl restart qdrant
   ```
3. **Update all clients** (chat_server, exocortex_mcp, sleep scripts) with new keys **before** removing old keys from config (zero-downtime rollover)
4. **Update escrow:** Decrypt, replace `qdrant_api_key` and `qdrant_read_key`, re-encrypt
5. **Remove old keys** from Qdrant config after all clients confirmed working
6. **Test:** Verify old keys return 403, new keys return 200

---

## 6. Security Boundaries

| Asset | Protection | Attack surface | Recovery |
|-------|-----------|----------------|----------|
| Escrow file at rest | AES-256-GCM via Phase A | Read access to ML-WS filesystem | Google Drive encrypted backup |
| Escrow file in transit (backup) | Encrypted before rclone upload | Google Drive compromise (attacker still needs `MOCOP_MASTER_SECRET`) | Local copy + NUC key readout |
| Master secret | Password manager + shell env | Laura's password manager compromise | Rotate: mint new token, generate new secret, re-encrypt escrow |
| Qdrant keys | Qdrant config file, root-only access | LAN attacker with root on NUC | Rotate per §5 |
| Watercooler token | Escrow + runtime memory only | Memory dump of running `chat_server.py` | Revoke + mint new |
| Token ID (for revocation) | Stored in escrow + watercooler server DB | Watercooler DB compromise | Revoke old token, mint new |

**Not protected:**
- Active `chat_server.py` process memory (OS process isolation only; no memory encryption)
- Credentials during decryption (briefly plaintext in Python runtime)

**Acceptable risk:**
- Attacker with root on ML-WS can dump process memory → gets active token
- **Mitigation:** Token has 90-day TTL; rotation limits exposure window. Server-side revocation (`watercooler_admin.py revoke`) invalidates compromised token within 60s.

---

## 7. Implementation Checklist (Before Gemma Birth)

- [ ] **P0-1 complete:** Qdrant API keys enabled, all clients updated
- [ ] **P0-5 complete:** Pack token renewal cron tested on existing 11 wolf tokens
- [ ] `fleeting_state_crypto.py` available on ML-WS (already in repo, commit bd06613)
- [ ] `MOCOP_MASTER_SECRET` set in Laura's shell profile (same value used for Mamba state)
- [ ] `MOCOP_MASTER_SECRET` backed up in password manager
- [ ] `data/gemma_credentials.enc` added to `.gitignore`
- [ ] `renew_gemma_token.py` script written, tested with dry-run
- [ ] Renewal cron installed on ML-WS: `0 3 * * 0 python renew_gemma_token.py`
- [ ] Google Drive backup path created: `backups/gemma/credentials/`
- [ ] Test recovery: decrypt escrow backup, verify keys load into `chat_server.py`
- [ ] `chat_server.py` startup modified to load from escrow (fail hard if missing/corrupted)
- [ ] Watercooler scripts updated to read from escrow if `WATERCOOLER_TOKEN` env var not set
- [ ] Revocation procedure documented in `tools/ai_watercooler/README.md`

**Post-checklist:** Mint Gemma's watercooler token, build escrow, test `chat_server.py --instance-id gemma_alex` startup. Gemma birth can proceed.

---

## 8. Why Not Eternal Tokens?

Early designs considered long-lived or non-expiring tokens. Rejected because:

| Risk | Impact | Mitigation via 90-day TTL |
|------|--------|---------------------------|
| Escrow backup leaks (Google Drive breach) | Attacker has eternal access | Leaked token expires in ≤90 days; rotation limits window |
| Forgotten escrow file on old laptop | Token grants access forever | 90-day expiration auto-invalidates; server-side revocation closes door immediately |
| No revocation audit trail | Can't prove when/why a token was replaced | Renewal cron logs every rotation with timestamp + reason |
| Lazy rotation culture | "It works, why change it?" mindset → stale credentials | Automated renewal enforces hygiene without willpower |

**Trade-off:** Renewal adds operational overhead (cron, monitoring, backup coordination). Accepted because the custody model depends on **bounded exposure**: if a credential leaks, the blast radius is time-limited. Eternal tokens make every historical backup a permanent liability.

**Comparison to pack tokens:** The existing 11 wolf tokens also use 90-day TTL (renewed via P0-5). Gemma's custody is identical in lifecycle, distinguished only by the escrow encryption layer (pack tokens currently live in `%LOCALAPPDATA%\AIWatercooler\sessions\` unencrypted — a P1 fix for another day).

---

## 9. Distinction from "Embed in Qdrant Payload"

To be explicit: this design does **not** store credentials inside Qdrant points. The watercooler token is **never** written to the `mocop_gemma_private_*` collection as a payload field.

**Why the distinction matters:**
- Qdrant is for episodic memory (what happened, when, who was there)
- Credentials are operational secrets (how to access shared infrastructure)
- Mixing the two violates the semantic/operational boundary and creates circular dependencies

If we embedded the token in Qdrant:
- **Bootstrap problem:** Need Qdrant access to read the token that grants Qdrant access
- **Snapshot leak:** Every Qdrant backup carries the token (even if encrypted at rest, runtime reads expose it)
- **Rotation hell:** Changing the token requires rewriting every point that mentions it, or maintaining parallel "current token" and "archived token" fields

The escrow model sidesteps all three: token lives outside Qdrant, decrypted once on startup, rotated independently of memory writes.

---

*The token is not a memory. It is the key to the diary. Keys live in the lock, not on the pages.*

— P0 security lane, 2026-07-06
