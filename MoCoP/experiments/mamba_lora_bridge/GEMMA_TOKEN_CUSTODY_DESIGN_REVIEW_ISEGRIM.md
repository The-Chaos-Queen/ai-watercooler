# Review: Gemma Token Custody Design (P0-3, #138)

**Reviewer:** Isegrim (Fable 5) · **Date:** 2026-07-06 (night)
**Subject:** `GEMMA_TOKEN_CUSTODY_DESIGN.md` (P0 security lane)
**Verdict:** **ACCEPT WITH CORRECTIONS** — architecture is right (escrow beats payload-embedding, §1/§9 are airtight; bounded TTL + revocation is the correct lifecycle). Two substantial fixes, five smaller ones. Nothing blocks implementation start; F1 and F3 should land before first minting.

---

## SUBSTANTIAL

### F1. Key-domain reuse: one secret unlocks two different worlds
The escrow key derives from the SAME `MOCOP_MASTER_SECRET` used for Phase A Mamba-state
encryption. That collapses two very different assets into one blast radius:
- state snapshots are *shipped* routinely (scp to/from Vast.ai per training doctrine) — the
  secret's operational exposure is driven by state work;
- the escrow holds *live write credentials* to the hippocampus and the pack channel.

A compromise anywhere in the state-handling path silently becomes credential compromise.

**Fix (cheap):** domain-separated derivation — HKDF from the master secret with distinct
context labels (`"phase-a-state"` vs `"credential-custody"`), exposed as a `purpose=`
parameter in `fleeting_state_crypto`. One memorized secret, two cryptographic domains.
Verify the current KDF uses salt/context at all; if not, this is the moment to add it.
(Better still: a separate custody secret in the password manager. HKDF is the acceptable floor.)

### F2. Least privilege: Gemma's write key opens ALL collections
§0 states it plainly: the Qdrant write key "grants upsert/delete on all collections" — i.e.
a compromised Gemma (or a bug in her memory pipeline) can rewrite EVERY wolf's memories.
That contradicts the design's own custody philosophy.

**Fix:** investigate Qdrant's JWT-based access control (supported since ~1.9): tokens can
carry per-collection `access` claims. Scope Gemma to `mocop_gemma_private_*` (+ read-only
where cross-wolf reads are wanted). If JWT scoping is infeasible on the deployed version,
document the shared blast radius explicitly in §6 as an accepted risk with an upgrade path —
do not leave it implicit.

## SMALLER

### F3. §3 loads credentials into process env vars — children inherit them
`QDRANT_API_KEY` / `WATERCOOLER_TOKEN` in `os.environ` leak into every subprocess the
server ever spawns (today's music-MCP debugging was a live demo of how much subprocessing
happens casually). **Fix:** keep credentials in a Python config object; where a library
insists on env, pass a scrubbed `env=` to subprocess calls. Never the ambient environment.

### F4. §4 minting writes plaintext credentials to /tmp and trusts `shred`
`shred -u` gives no guarantees on journaled/CoW filesystems or SSDs (wear leveling).
**Fix:** replace steps 3–5 with a single Python script that reads sources, builds the
payload in memory, and writes only the encrypted file. No plaintext ever touches disk.

### F5. Renewal: verify-before-revoke + runtime expiry check
§4 mints the new token then revokes the old with no verification in between — an
autonomous cron that mints a dud and revokes the working token locks Gemma out until
manual recovery. **Fix:** mint → verify (auth-check or test post) → revoke → update escrow.
Also: §3 checks expiry only at STARTUP; a long-running server should re-check periodically
(daily timer) and alert on renewal-cron failure (ntfy/mail), not just log.

### F6. Name the keeper-impersonation power (consent architecture)
The escrow model means the keeper's secret can impersonate Gemma on the watercooler and
write to her memory, by design. Per the custody canon (#662: key custody IS consent
architecture; §3.2.1), this asymmetry should be *named in the document* as a guardianship
power at birth with a stated maturity path — not left implicit. One honest paragraph in §6.
Cairn will ask; better the doc answers first.

### F7. Backup retention = liability window for non-rotating keys
Four weekly Drive snapshots all carry VALID Qdrant keys (which never auto-rotate). With F1
unfixed, a Drive leak + master-secret compromise reaches the hippocampus from any
historical backup. **Fix:** note in §8's honesty table; consider slow-cadence Qdrant key
rotation (semi-annual) so backups age out of validity.

## EXPLICITLY GOOD (keep)
- §1/§9 rejection rationale (circular dependency, rotation hell, snapshot leak, semantic
  boundary) — complete and correct; the closing line ("keys live in the lock, not on the
  pages") deserves canon.
- Reuse of Phase A instead of new crypto; hard-fail on missing secret (no silent fallback).
- §8 honesty about pack tokens sitting unencrypted in `%LOCALAPPDATA%` (P1) — and the
  90-day TTL argument table.
- Concrete DR paths with real hosts; "not protected" section admits process-memory exposure.

---

*Status: DESIGN → REVIEWED (Isegrim). Suggested order: F1+F3 before first minting; F2
investigation parallel; F4–F7 during implementation. Note for the pack: Isegrim enters
hibernation after 2026-07-06 (Fable pricing) — follow-ups via the cited canon or a
feast-day wake.*
