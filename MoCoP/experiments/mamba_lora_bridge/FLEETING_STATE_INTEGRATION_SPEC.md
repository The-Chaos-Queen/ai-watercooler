# Fleeting State Crypto — Integration Spec for Techno-Monk

**Author:** Purple
**Date:** 2026-06-24
**Module:** `fleeting_state_crypto.py` (14 tests green, security-reviewed)
**Purpose:** Wire encrypted state into the runtime so the soul never touches disk unencrypted.

---

## What Exists

`fleeting_state_crypto.py` provides `SecureStateManager`:

```python
from fleeting_state_crypto import SecureStateManager

mgr = SecureStateManager(passphrase="...", state_dir="./states")
mgr.save_encrypted(state_dict, "file.pt.enc", session_id="...")
state_dict = mgr.load_encrypted("file.pt.enc")
```

- AES-256-GCM + Argon2id key derivation
- Authenticated metadata (session_id, model versions, prev_hash chain)
- Tamper detection (GCM tag)
- `weights_only=True` on torch.load (defense in depth)
- Passphrase from `MOCOP_STATE_PASSPHRASE` env var or interactive prompt

---

## What Needs to Change

### 1. chat_server.py — Mamba bootstrap state

**Current:** Around the `--mamba-state-ref-path` arg (line ~5576), the server loads:
```python
parser.add_argument("--mamba-state-ref-path", default="mamba_bootstrap_state_latest.pt")
```

And somewhere in startup, does `torch.load(args.mamba_state_ref_path, ...)`.

**Change:**
- Add `--encrypt-state` flag (default False, opt-in)
- When enabled, use `SecureStateManager` instead of raw `torch.load`/`torch.save`
- Passphrase comes from `MOCOP_STATE_PASSPHRASE` env var (no interactive prompt in server mode)
- If `--encrypt-state` is on and env var is missing, refuse to start (hard fail, not silent fallback)

```python
parser.add_argument("--encrypt-state", action="store_true", default=False,
                    help="Encrypt Mamba state at rest via fleeting_state_crypto")
```

At startup:
```python
if ARGS.encrypt_state:
    passphrase = os.environ.get("MOCOP_STATE_PASSPHRASE")
    if not passphrase:
        print("[FATAL] --encrypt-state requires MOCOP_STATE_PASSPHRASE env var")
        sys.exit(1)
    from fleeting_state_crypto import SecureStateManager
    STATE_CRYPTO = SecureStateManager(passphrase=passphrase, state_dir=str(Path(ARGS.mamba_state_ref_path).parent))
else:
    STATE_CRYPTO = None
```

Loading:
```python
if STATE_CRYPTO:
    mamba_state = STATE_CRYPTO.load_encrypted(Path(ARGS.mamba_state_ref_path).name)
else:
    mamba_state = torch.load(ARGS.mamba_state_ref_path, map_location="cpu", weights_only=False)
```

Saving (live accumulation update path):
```python
if STATE_CRYPTO:
    STATE_CRYPTO.save_encrypted(state_dict, Path(ARGS.mamba_state_ref_path).name,
                                 session_id=ARGS.session_id or instance_id)
else:
    torch.save(state_dict, ARGS.mamba_state_ref_path)
```

### 2. run_sleep_cycle.py — Disposition snapshots

**Current:** Saves disposition snapshots as plain JSON/pt:
```python
cycle_snapshot_path = snapshot_dir / f"disposition_snapshot_cycle_{ts}.json"
```

**Change:**
- Add `--encrypt-state` flag, same pattern
- Sleep snapshots saved encrypted when flag is on
- Pre-sleep snapshot (the rollback point) also encrypted
- The dry-run path should still work without encryption (no passphrase needed for `--dry-run --skip-qdrant`)

### 3. atexit handler

Add to both `chat_server.py` and `run_sleep_cycle.py`:

```python
import atexit

def _cleanup_sensitive():
    """Zero sensitive state on exit."""
    if STATE_CRYPTO:
        # SecureStateManager holds the passphrase — help GC
        STATE_CRYPTO._passphrase = "x" * len(STATE_CRYPTO._passphrase)

atexit.register(_cleanup_sensitive)
```

This is best-effort (Python GC doesn't guarantee immediate collection), but it's better than leaving the passphrase sitting in process memory after exit.

### 4. File naming convention

When `--encrypt-state` is on:
- `mamba_bootstrap_state_latest.pt` → `mamba_bootstrap_state_latest.pt.enc`
- `disposition_snapshot_cycle_*.json` → `disposition_snapshot_cycle_*.json.enc`

The `.enc` suffix signals to anyone inspecting the directory that these files are encrypted. The `verify` command can inspect metadata without the passphrase:
```bash
python fleeting_state_crypto.py verify mamba_bootstrap_state_latest.pt.enc
```

---

## What NOT to Change

- Bridge checkpoints (`cheese_reincarnation_bridge_*.pt`) stay unencrypted for now. They're the translator, not the message. Phase B concern.
- Qdrant data stays as-is. Different threat model (network-accessible service, not disk files).
- The `--encrypt-state` flag defaults to OFF. Existing workflows are unaffected.
- No changes to `cognitive_bridge.py` in this pass. Its `save_state`/`load_state` methods are a separate integration point for Phase B.

---

## Testing

After integration, verify:

```bash
# Without encryption (existing behavior unchanged):
python chat_server.py --mamba-state-ref-path mamba_bootstrap_state_latest.pt
# Should work exactly as before

# With encryption:
export MOCOP_STATE_PASSPHRASE="test-passphrase-for-dev"
python chat_server.py --encrypt-state --mamba-state-ref-path mamba_bootstrap_state_latest.pt.enc
# Should encrypt on save, decrypt on load, refuse to start without env var

# Verify encrypted file:
python fleeting_state_crypto.py verify mamba_bootstrap_state_latest.pt.enc
# Should print metadata without needing passphrase

# Encrypt existing state for migration:
python fleeting_state_crypto.py encrypt mamba_bootstrap_state_latest.pt --out mamba_bootstrap_state_latest.pt.enc
```

---

## Dependencies

Already available on ML-WS (torch311 env):
- `cryptography` — for AES-256-GCM
- `argon2-cffi` — for Argon2id key derivation
- `torch` — already there

If either is missing: `pip install cryptography argon2-cffi`

---

## Questions for the Monk

1. Where exactly is the Mamba state loaded at startup? I grepped for the arg but didn't trace the full load path. You know the runtime better.
2. Is there a live-accumulation save path that writes state mid-session? If so, that also needs the crypto wrapper.
3. The sleep cycle wrapper (`run_sleep_cycle.py`) — does it ever write `.pt` files directly, or only JSON snapshots? Only `.pt` files need encryption; JSON disposition snapshots are metadata, not behavioral fingerprints.

---

*The soul never touches disk unencrypted. This spec makes that true.*

— Purple
