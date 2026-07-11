import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qdrant_security import QdrantTransportError, default_qdrant_url, verified_qdrant_client_options


def test_default_url_is_https():
    assert default_qdrant_url({}) == "https://192.168.2.191:6333"


def test_https_with_ca_returns_verify_path(tmp_path):
    ca = tmp_path / "root-ca.crt"
    ca.write_text("public certificate", encoding="utf-8")
    assert verified_qdrant_client_options(
        "https://192.168.2.191:6333", {"QDRANT_CA_CERT": str(ca)}
    ) == {"verify": str(ca)}


def test_https_rejects_missing_configured_ca():
    with pytest.raises(QdrantTransportError, match="does not exist"):
        verified_qdrant_client_options(
            "https://192.168.2.191:6333", {"QDRANT_CA_CERT": "/missing/root-ca.crt"}
        )


def test_http_is_rejected_without_explicit_emergency_override():
    with pytest.raises(QdrantTransportError, match="Refusing plaintext"):
        verified_qdrant_client_options("http://192.168.2.191:6333", {})


def test_http_emergency_override_is_explicit():
    assert verified_qdrant_client_options(
        "http://192.168.2.191:6333", {"QDRANT_ALLOW_INSECURE_HTTP": "true"}
    ) == {}
