"""Tests for fleeting_state_crypto.py — Phase A encryption."""

import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch

# Handle torch/OMP conflicts
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fleeting_state_crypto import (
    derive_key,
    write_encrypted_file,
    read_encrypted_file,
    EncryptedStateHeader,
    SecureStateManager,
    MAGIC,
    VERSION,
)

pytestmark = pytest.mark.crypto


def test_derive_key_deterministic():
    """Same inputs produce same key."""
    salt = b"test_salt_32_bytes______________"
    k1 = derive_key("hunter2", salt, "session-1")
    k2 = derive_key("hunter2", salt, "session-1")
    assert k1 == k2
    assert len(k1) == 32


def test_derive_key_different_sessions():
    """Different session IDs produce different keys."""
    salt = b"test_salt_32_bytes______________"
    k1 = derive_key("hunter2", salt, "session-1")
    k2 = derive_key("hunter2", salt, "session-2")
    assert k1 != k2


def test_derive_key_different_passphrases():
    """Different passphrases produce different keys."""
    salt = b"test_salt_32_bytes______________"
    k1 = derive_key("hunter2", salt, "session-1")
    k2 = derive_key("hunter3", salt, "session-1")
    assert k1 != k2


def test_encrypt_decrypt_roundtrip(tmp_path):
    """Encrypt then decrypt recovers original plaintext."""
    plaintext = b"this is a test mamba state snapshot bytes"
    header = EncryptedStateHeader(session_id="test-session")
    key = derive_key("testpass", header.salt, header.session_id)

    path = tmp_path / "test_state.enc"
    ct_hash = write_encrypted_file(path, plaintext, key, header)

    recovered, metadata = read_encrypted_file(path, key)
    assert recovered == plaintext
    assert metadata["session_id"] == "test-session"
    assert len(ct_hash) == 64  # SHA-256 hex


def test_wrong_passphrase_fails(tmp_path):
    """Decryption with wrong key raises ValueError."""
    plaintext = b"sensitive state data"
    header = EncryptedStateHeader(session_id="test")
    key_good = derive_key("correct", header.salt, header.session_id)
    key_bad = derive_key("wrong", header.salt, header.session_id)

    path = tmp_path / "test.enc"
    write_encrypted_file(path, plaintext, key_good, header)

    with pytest.raises(ValueError, match="Decryption failed"):
        read_encrypted_file(path, key_bad)


def test_tampered_file_fails(tmp_path):
    """Modifying ciphertext causes authentication failure."""
    plaintext = b"important state"
    header = EncryptedStateHeader(session_id="tamper-test")
    key = derive_key("testpass", header.salt, header.session_id)

    path = tmp_path / "tampered.enc"
    write_encrypted_file(path, plaintext, key, header)

    data = path.read_bytes()
    # Flip a byte near the end (in the ciphertext region)
    corrupted = bytearray(data)
    corrupted[-10] ^= 0xFF
    path.write_bytes(bytes(corrupted))

    with pytest.raises(ValueError, match="Decryption failed"):
        read_encrypted_file(path, key)


def test_magic_check(tmp_path):
    """Non-MoCoP file is rejected."""
    path = tmp_path / "fake.enc"
    path.write_bytes(b"NOT_MCPS_data_here")

    key = derive_key("x", b"0" * 32, "")
    with pytest.raises(ValueError, match="Not a MoCoP"):
        read_encrypted_file(path, key)


def test_metadata_preserved(tmp_path):
    """Session metadata survives encrypt/decrypt."""
    plaintext = b"state"
    header = EncryptedStateHeader(
        session_id="meta-test",
        model_versions={"mamba": "2.8b", "qwen": "1.5b"},
        prev_hash="abc123",
    )
    key = derive_key("pass", header.salt, header.session_id)

    path = tmp_path / "meta.enc"
    write_encrypted_file(path, plaintext, key, header)

    _, metadata = read_encrypted_file(path, key)
    assert metadata["session_id"] == "meta-test"
    assert metadata["model_versions"]["mamba"] == "2.8b"
    assert metadata["prev_hash"] == "abc123"


def test_hash_chain(tmp_path):
    """Sequential saves produce a hash chain."""
    mgr = SecureStateManager(passphrase="chain-test", state_dir=str(tmp_path))

    import torch
    state1 = {"tensor": torch.randn(10)}
    hash1 = mgr.save_encrypted(state1, "state1.enc", session_id="s1")

    state2 = {"tensor": torch.randn(10)}
    hash2 = mgr.save_encrypted(state2, "state2.enc", session_id="s2")

    # Verify chain: state2's metadata should reference state1's hash
    meta2 = mgr.verify_integrity("state2.enc")
    assert meta2["prev_hash"] == hash1
    assert hash1 != hash2


def test_secure_state_manager_roundtrip(tmp_path):
    """Full manager round-trip with torch state_dict."""
    import torch

    mgr = SecureStateManager(passphrase="manager-test", state_dir=str(tmp_path))
    original = {"weights": torch.tensor([1.0, 2.0, 3.0]), "config": {"alpha": 0.2}}

    mgr.save_encrypted(original, "test.enc", session_id="mgr-test")
    loaded = mgr.load_encrypted("test.enc")

    assert torch.equal(loaded["weights"], original["weights"])
    assert loaded["config"]["alpha"] == 0.2


def test_verify_without_decrypt(tmp_path):
    """Can inspect metadata without knowing the passphrase."""
    import torch

    mgr = SecureStateManager(passphrase="secret", state_dir=str(tmp_path))
    mgr.save_encrypted({"x": torch.zeros(5)}, "check.enc", session_id="verify-test")

    # Different manager, wrong passphrase — but verify still works
    mgr2 = SecureStateManager(passphrase="wrong", state_dir=str(tmp_path))
    meta = mgr2.verify_integrity("check.enc")
    assert meta["session_id"] == "verify-test"
    assert meta["_version"] == VERSION


def test_oversized_metadata_rejected(tmp_path):
    """Crafted file with huge meta_len is rejected before allocation."""
    import struct
    path = tmp_path / "bomb.enc"
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("B", VERSION))
        f.write(struct.pack(">I", 0xFFFFFFFF))  # 4GB metadata claim
        f.write(b"x" * 100)  # doesn't matter, should fail before reading

    key = derive_key("x", b"0" * 32, "")
    with pytest.raises(ValueError, match="exceeds safety limit"):
        read_encrypted_file(path, key)


def test_spliced_session_id_detected(tmp_path):
    """Tampering session_id in metadata doesn't produce silent wrong decryption."""
    import struct
    plaintext = b"real state data"
    header = EncryptedStateHeader(session_id="real-session")
    key = derive_key("pass", header.salt, header.session_id)

    path = tmp_path / "original.enc"
    write_encrypted_file(path, plaintext, key, header)

    # Try to load with a different session_id — should fail because GCM
    # authenticates the metadata (which contains the real session_id)
    wrong_key = derive_key("pass", header.salt, "fake-session")
    with pytest.raises(ValueError):
        read_encrypted_file(path, wrong_key)


def test_env_passphrase():
    """Passphrase from environment variable."""
    with patch.dict(os.environ, {"MOCOP_STATE_PASSPHRASE": "env-secret"}):
        from fleeting_state_crypto import get_passphrase_from_env
        assert get_passphrase_from_env() == "env-secret"
