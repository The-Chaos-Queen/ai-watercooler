import sys
import types

import pytest

from qdrant_transport import (
    QdrantTransportError,
    build_qdrant_client,
    qdrant_transport_from_environment,
)


def _environment(ca_cert, **overrides):
    environment = {
        "QDRANT_API_KEY": "writer-test-key",
        "QDRANT_CA_CERT": str(ca_cert),
    }
    environment.update(overrides)
    return environment


def test_default_host_port_resolves_to_verified_https(tmp_path):
    ca_cert = tmp_path / "root-ca.crt"
    ca_cert.write_text("public test CA\n", encoding="utf-8")

    transport = qdrant_transport_from_environment(
        host="192.168.2.191",
        port=6333,
        environ=_environment(ca_cert),
    )

    assert transport.endpoint == "https://192.168.2.191:6333"
    assert transport.client_kwargs(timeout=15) == {
        "url": "https://192.168.2.191:6333",
        "api_key": "writer-test-key",
        "timeout": 15,
        "verify": str(ca_cert),
    }
    assert "host" not in transport.client_kwargs(timeout=15)
    assert "port" not in transport.client_kwargs(timeout=15)
    assert "https" not in transport.client_kwargs(timeout=15)


def test_explicit_https_url_overrides_legacy_host_port(tmp_path):
    ca_cert = tmp_path / "root-ca.crt"
    ca_cert.write_text("public test CA\n", encoding="utf-8")

    transport = qdrant_transport_from_environment(
        host="ignored.example",
        port=9999,
        environ=_environment(ca_cert, QDRANT_URL="https://qdrant.lan:7443"),
    )

    assert transport.endpoint == "https://qdrant.lan:7443"


@pytest.mark.parametrize(
    "environment, expected",
    [
        ({"QDRANT_URL": "http://192.168.2.191:6333"}, "HTTPS"),
        ({"QDRANT_API_KEY": ""}, "QDRANT_API_KEY"),
        ({"QDRANT_CA_CERT": ""}, "QDRANT_CA_CERT"),
    ],
)
def test_refuses_insecure_or_incomplete_writer_configuration(tmp_path, environment, expected):
    ca_cert = tmp_path / "root-ca.crt"
    ca_cert.write_text("public test CA\n", encoding="utf-8")
    configured = _environment(ca_cert, **environment)

    with pytest.raises(QdrantTransportError, match=expected):
        qdrant_transport_from_environment(environ=configured)


def test_refuses_missing_ca_file(tmp_path):
    missing_ca = tmp_path / "missing-root-ca.crt"

    with pytest.raises(QdrantTransportError, match="does not exist"):
        qdrant_transport_from_environment(environ=_environment(missing_ca))


def test_refuses_url_with_credentials_or_query(tmp_path):
    ca_cert = tmp_path / "root-ca.crt"
    ca_cert.write_text("public test CA\n", encoding="utf-8")

    for unsafe_url in (
        "https://writer:secret@qdrant.lan:6333",
        "https://qdrant.lan:6333?verify=false",
        "https://qdrant.lan:6333/path",
    ):
        with pytest.raises(QdrantTransportError):
            qdrant_transport_from_environment(
                environ=_environment(ca_cert, QDRANT_URL=unsafe_url)
            )


def test_build_client_passes_ca_verification_not_transport_downgrade(tmp_path, monkeypatch):
    ca_cert = tmp_path / "root-ca.crt"
    ca_cert.write_text("public test CA\n", encoding="utf-8")
    transport = qdrant_transport_from_environment(environ=_environment(ca_cert))
    received = {}

    class FakeQdrantClient:
        def __init__(self, **kwargs):
            received.update(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "qdrant_client",
        types.SimpleNamespace(QdrantClient=FakeQdrantClient),
    )

    build_qdrant_client(transport, timeout=10)

    assert received == {
        "url": "https://192.168.2.191:6333",
        "api_key": "writer-test-key",
        "timeout": 10,
        "verify": str(ca_cert),
    }
    assert received["verify"] is not False
