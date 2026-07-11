from pathlib import Path

import pytest

from qdrant_transport import QdrantTransportError, transport_from_environment


def test_defaults_to_verified_https_without_ca_override():
    config = transport_from_environment({})

    assert config.host == "192.168.2.191"
    assert config.port == 6333
    assert config.client_kwargs() == {"https": True}


def test_explicit_ca_bundle_is_passed_to_client(tmp_path: Path):
    ca = tmp_path / "qdrant-lan-root-ca.crt"
    ca.write_text("public certificate", encoding="utf-8")

    config = transport_from_environment({"QDRANT_CA_CERT": str(ca)})

    assert config.client_kwargs() == {"https": True, "verify": str(ca)}


def test_missing_configured_ca_fails_closed():
    with pytest.raises(QdrantTransportError, match="does not exist"):
        transport_from_environment({"QDRANT_CA_CERT": "/no/such/qdrant-ca.crt"})


def test_plain_http_requires_explicit_emergency_override():
    config = transport_from_environment({"QDRANT_HTTPS": "false"})

    assert config.client_kwargs() == {"https": False}


@pytest.mark.parametrize("raw", ["", "maybe", "2", "enabled"])
def test_invalid_https_flag_is_rejected(raw: str):
    with pytest.raises(QdrantTransportError, match="QDRANT_HTTPS"):
        transport_from_environment({"QDRANT_HTTPS": raw})
