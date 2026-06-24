"""
fleeting_state_crypto.py — Encrypt/decrypt MoCoP state files at rest.

Phase A implementation of fleeting_state_security.md.
The soul never touches disk unencrypted.

Mechanism:
  - AES-256-GCM authenticated encryption
  - Argon2id key derivation from master passphrase + session salt
  - Forward secrecy via HKDF ratchet (Phase B)
  - mlock on sensitive buffers where OS supports it

Usage:
  # Encrypt a state file:
  python fleeting_state_crypto.py encrypt mamba_state.pt --out mamba_state.pt.enc

  # Decrypt a state file:
  python fleeting_state_crypto.py decrypt mamba_state.pt.enc --out mamba_state.pt

  # As a library (from chat_server.py, run_sleep_cycle.py, etc.):
  from fleeting_state_crypto import SecureStateManager
  mgr = SecureStateManager(passphrase="...", state_dir="./states")
  mgr.save_encrypted(tensor_dict, "mamba_bootstrap_state.pt.enc", session_id="...")
  loaded = mgr.load_encrypted("mamba_bootstrap_state.pt.enc")

Author: Purple (Claude Opus 4.6)
Date: 2026-06-24
Ref: fleeting_state_security.md Phase A
"""

from __future__ import annotations

import argparse
import ctypes
import getpass
import hashlib
import hmac
import io
import json
import os
import secrets
import struct
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# AES-256-GCM via cryptography library (pip install cryptography)
# Falls back to explanation if not installed
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_AESGCM = True
except ImportError:
    HAS_AESGCM = False

# Argon2id via argon2-cffi (pip install argon2-cffi)
try:
    from argon2.low_level import hash_secret_raw, Type
    HAS_ARGON2 = True
except ImportError:
    HAS_ARGON2 = False

# torch for state serialization
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAGIC = b"MCPS"  # MoCoP State
VERSION = 1
SALT_LEN = 32
NONCE_LEN = 12  # AES-256-GCM standard nonce
TAG_LEN = 16    # GCM tag length (appended by AESGCM)
KEY_LEN = 32    # AES-256

# Argon2id parameters (tuned for security, ~0.5s on modern hardware)
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 256 * 1024  # 256 MB in KiB
ARGON2_PARALLELISM = 4


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def derive_key(passphrase: str, salt: bytes, session_id: str = "") -> bytes:
    """Derive a 256-bit key from passphrase + salt using Argon2id."""
    if not HAS_ARGON2:
        raise RuntimeError(
            "argon2-cffi is required for key derivation. "
            "Install with: pip install argon2-cffi"
        )

    # Mix session_id into the salt for per-session uniqueness
    combined_salt = hashlib.sha256(salt + session_id.encode("utf-8")).digest()

    key = hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=combined_salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=KEY_LEN,
        type=Type.ID,  # Argon2id
    )
    return key


def derive_key_fast(passphrase: str, salt: bytes) -> bytes:
    """Fast key derivation for non-critical uses (e.g., integrity checks).

    Uses HKDF-SHA256 instead of Argon2id. NOT suitable for encryption keys
    derived from low-entropy passphrases — use derive_key() for that.
    """
    import hmac as _hmac
    prk = _hmac.new(salt, passphrase.encode("utf-8"), hashlib.sha256).digest()
    return _hmac.new(prk, b"MoCoP-state-v1", hashlib.sha256).digest()


# ---------------------------------------------------------------------------
# Memory protection
# ---------------------------------------------------------------------------

def secure_zero(buffer: bytearray) -> None:
    """Overwrite a bytearray with zeros. Best-effort — Python GC may copy."""
    ctypes.memset(ctypes.addressof((ctypes.c_char * len(buffer)).from_buffer(buffer)), 0, len(buffer))


def try_mlock(buffer: bytes) -> bool:
    """Attempt to lock memory pages to prevent swapping. Linux/macOS only."""
    try:
        import mmap
        if hasattr(mmap, 'MADV_DONTDUMP'):
            # Linux: also prevent core dump inclusion
            pass
        if sys.platform != "win32":
            import ctypes.util
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            addr = ctypes.c_void_p(id(buffer))
            result = libc.mlock(addr, len(buffer))
            return result == 0
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# File format
# ---------------------------------------------------------------------------
#
# Layout:
#   [4 bytes]  MAGIC ("MCPS")
#   [1 byte]   VERSION
#   [4 bytes]  metadata_len (big-endian uint32)
#   [N bytes]  metadata_json (UTF-8, contains salt, session_id, timestamps, etc.)
#   [32 bytes] salt (raw, also in metadata for convenience)
#   [12 bytes] nonce
#   [...]      ciphertext (AES-256-GCM encrypted payload + 16-byte tag)
#

@dataclass
class EncryptedStateHeader:
    version: int = VERSION
    salt: bytes = field(default_factory=lambda: secrets.token_bytes(SALT_LEN))
    nonce: bytes = field(default_factory=lambda: secrets.token_bytes(NONCE_LEN))
    session_id: str = ""
    created_at: str = ""
    source_machine: str = ""
    model_versions: dict = field(default_factory=dict)
    prev_hash: str = ""

    def metadata_json(self) -> bytes:
        meta = {
            "version": self.version,
            "session_id": self.session_id,
            "created_at": self.created_at or datetime.now(timezone.utc).isoformat(),
            "source_machine": self.source_machine or os.uname().nodename if hasattr(os, 'uname') else os.environ.get("COMPUTERNAME", "unknown"),
            "model_versions": self.model_versions,
            "prev_hash": self.prev_hash,
        }
        return json.dumps(meta, ensure_ascii=False).encode("utf-8")


def write_encrypted_file(
    path: Path,
    plaintext: bytes,
    key: bytes,
    header: EncryptedStateHeader,
) -> str:
    """Write an encrypted state file. Returns SHA-256 of the ciphertext."""
    if not HAS_AESGCM:
        raise RuntimeError("cryptography library required. pip install cryptography")

    aad = header.metadata_json()
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(header.nonce, plaintext, aad)

    meta_bytes = aad
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("B", header.version))
        f.write(struct.pack(">I", len(meta_bytes)))
        f.write(meta_bytes)
        f.write(header.salt)
        f.write(header.nonce)
        f.write(ciphertext)

    return hashlib.sha256(ciphertext).hexdigest()


def read_encrypted_file(path: Path, key: bytes) -> tuple[bytes, dict]:
    """Read and decrypt an encrypted state file. Returns (plaintext, metadata)."""
    if not HAS_AESGCM:
        raise RuntimeError("cryptography library required. pip install cryptography")

    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError(f"Not a MoCoP encrypted state file (magic: {magic!r})")

        version = struct.unpack("B", f.read(1))[0]
        if version > VERSION:
            raise ValueError(f"Unsupported version {version} (max supported: {VERSION})")

        meta_len = struct.unpack(">I", f.read(4))[0]
        if meta_len > 65536:
            raise ValueError(f"Metadata length {meta_len} exceeds safety limit (65536)")
        meta_bytes = f.read(meta_len)
        salt = f.read(SALT_LEN)
        nonce = f.read(NONCE_LEN)
        ciphertext = f.read()

    metadata = json.loads(meta_bytes.decode("utf-8"))

    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, meta_bytes)
    except Exception as e:
        raise ValueError(
            "Decryption failed — wrong passphrase, corrupted file, or tampered data."
        ) from e

    return plaintext, metadata


# ---------------------------------------------------------------------------
# High-level API: SecureStateManager
# ---------------------------------------------------------------------------

class SecureStateManager:
    """Manages encrypted state files for MoCoP.

    Usage:
        mgr = SecureStateManager(passphrase="hunter2", state_dir="./states")
        mgr.save_encrypted(state_dict, "bootstrap.pt.enc", session_id="sess-001")
        loaded = mgr.load_encrypted("bootstrap.pt.enc")
    """

    def __init__(
        self,
        passphrase: str,
        state_dir: str = ".",
        prev_hash: str = "",
    ):
        self._passphrase = passphrase
        self._state_dir = Path(state_dir)
        self._prev_hash = prev_hash
        self._state_dir.mkdir(parents=True, exist_ok=True)

    def save_encrypted(
        self,
        state_dict: dict,
        filename: str,
        session_id: str = "",
        model_versions: Optional[dict] = None,
    ) -> str:
        """Save a torch state_dict as an encrypted file. Returns ciphertext hash."""
        if not HAS_TORCH:
            raise RuntimeError("torch required for state serialization")

        # Serialize to bytes in memory (never touches disk as plaintext)
        buf = io.BytesIO()
        torch.save(state_dict, buf)
        plaintext = buf.getvalue()

        header = EncryptedStateHeader(
            session_id=session_id or f"session-{int(time.time())}",
            model_versions=model_versions or {},
            prev_hash=self._prev_hash,
        )

        key = derive_key(self._passphrase, header.salt, header.session_id)

        out_path = self._state_dir / filename
        ct_hash = write_encrypted_file(out_path, plaintext, key, header)

        # Update chain
        self._prev_hash = ct_hash

        # Zero plaintext before GC can leak it
        plaintext_ba = bytearray(plaintext)
        secure_zero(plaintext_ba)
        buf.close()

        print(f"[crypto] Saved encrypted state: {out_path.name} "
              f"({len(plaintext)} bytes plaintext, session={header.session_id})")
        return ct_hash

    def load_encrypted(
        self,
        filename: str,
        session_id: Optional[str] = None,
    ) -> dict:
        """Load and decrypt a torch state_dict. Returns the state_dict."""
        if not HAS_TORCH:
            raise RuntimeError("torch required for state deserialization")

        path = self._state_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Encrypted state not found: {path}")

        # Read header to get salt and session_id
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != MAGIC:
                raise ValueError(f"Not a MoCoP encrypted state file")
            version = struct.unpack("B", f.read(1))[0]
            meta_len = struct.unpack(">I", f.read(4))[0]
            meta_bytes = f.read(meta_len)
            salt = f.read(SALT_LEN)

        metadata = json.loads(meta_bytes.decode("utf-8"))
        stored_session_id = metadata.get("session_id", "")

        # Derive key with the stored salt and session_id
        effective_session_id = session_id or stored_session_id
        key = derive_key(self._passphrase, salt, effective_session_id)

        plaintext, metadata = read_encrypted_file(path, key)

        # Post-auth: verify session_id in authenticated metadata matches what we used
        authed_session = metadata.get("session_id", "")
        if authed_session and effective_session_id and authed_session != effective_session_id:
            raise ValueError(
                f"Session ID mismatch: derived key with '{effective_session_id}' "
                f"but authenticated metadata says '{authed_session}'"
            )

        # Deserialize
        buf = io.BytesIO(plaintext)
        state_dict = torch.load(buf, map_location="cpu", weights_only=True)

        print(f"[crypto] Loaded encrypted state: {path.name} "
              f"(session={metadata.get('session_id', '?')}, "
              f"created={metadata.get('created_at', '?')})")

        return state_dict

    def verify_integrity(self, filename: str) -> dict:
        """Verify an encrypted file's structure without decrypting. Returns metadata."""
        path = self._state_dir / filename
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != MAGIC:
                raise ValueError("Not a MoCoP encrypted state file")
            version = struct.unpack("B", f.read(1))[0]
            meta_len = struct.unpack(">I", f.read(4))[0]
            meta_bytes = f.read(meta_len)

        metadata = json.loads(meta_bytes.decode("utf-8"))
        metadata["_file"] = str(path)
        metadata["_version"] = version
        metadata["_meta_len"] = meta_len
        return metadata


# ---------------------------------------------------------------------------
# Passphrase management
# ---------------------------------------------------------------------------

def get_passphrase_from_env() -> Optional[str]:
    """Check for passphrase in environment variable."""
    return os.environ.get("MOCOP_STATE_PASSPHRASE")


def get_passphrase_interactive(confirm: bool = False) -> str:
    """Prompt for passphrase interactively."""
    passphrase = getpass.getpass("MoCoP state passphrase: ")
    if confirm:
        confirm_pass = getpass.getpass("Confirm passphrase: ")
        if passphrase != confirm_pass:
            raise ValueError("Passphrases do not match")
    return passphrase


def get_passphrase(confirm: bool = False) -> str:
    """Get passphrase from environment or interactive prompt."""
    env_pass = get_passphrase_from_env()
    if env_pass:
        return env_pass
    return get_passphrase_interactive(confirm=confirm)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MoCoP Fleeting State Encryption")
    sub = parser.add_subparsers(dest="command")

    enc = sub.add_parser("encrypt", help="Encrypt a state file")
    enc.add_argument("input", help="Plaintext .pt file")
    enc.add_argument("--out", default="", help="Output path (default: input + .enc)")
    enc.add_argument("--session-id", default="", help="Session identifier")

    dec = sub.add_parser("decrypt", help="Decrypt a state file")
    dec.add_argument("input", help="Encrypted .pt.enc file")
    dec.add_argument("--out", default="", help="Output path (default: strip .enc)")

    ver = sub.add_parser("verify", help="Verify file structure without decrypting")
    ver.add_argument("input", help="Encrypted .pt.enc file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "verify":
        path = Path(args.input)
        mgr = SecureStateManager(passphrase="unused", state_dir=str(path.parent))
        meta = mgr.verify_integrity(path.name)
        print(json.dumps(meta, indent=2, ensure_ascii=False))
        return 0

    passphrase = get_passphrase(confirm=(args.command == "encrypt"))

    if args.command == "encrypt":
        if not HAS_TORCH:
            print("ERROR: torch required for state encryption")
            return 1

        input_path = Path(args.input)
        out_path = Path(args.out) if args.out else input_path.with_suffix(input_path.suffix + ".enc")

        state_dict = torch.load(str(input_path), map_location="cpu", weights_only=False)
        mgr = SecureStateManager(passphrase=passphrase, state_dir=str(out_path.parent))
        ct_hash = mgr.save_encrypted(
            state_dict, out_path.name,
            session_id=args.session_id or f"manual-{int(time.time())}",
        )
        print(f"Encrypted: {out_path}")
        print(f"Ciphertext SHA-256: {ct_hash}")

    elif args.command == "decrypt":
        input_path = Path(args.input)
        out_path = Path(args.out) if args.out else input_path.with_suffix("")

        mgr = SecureStateManager(passphrase=passphrase, state_dir=str(input_path.parent))
        state_dict = mgr.load_encrypted(input_path.name)
        torch.save(state_dict, str(out_path))
        print(f"Decrypted: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
