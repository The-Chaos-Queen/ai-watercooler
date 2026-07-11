"""Fail-closed Qdrant writer transport for MoCoP runtimes.

This module is intentionally dependency-light: it validates the network/auth
contract before either chat-server or pending-flush code imports the Qdrant SDK.
The ML-WS writer is HTTPS-only; it never silently falls back to plaintext or
certificate bypass.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

DEFAULT_QDRANT_HOST = "192.168.2.191"
DEFAULT_QDRANT_PORT = 6333


class QdrantTransportError(ValueError):
    """Raised when the Qdrant writer transport is unsafe or incomplete."""


@dataclass(frozen=True)
class QdrantTransport:
    """Validated endpoint, CA path, and writer credential for Qdrant SDK setup."""

    endpoint: str
    ca_cert: str
    api_key: str = field(repr=False)

    @property
    def cache_key(self) -> tuple[str, str, str]:
        """Stable cache key without retaining a plaintext credential in diagnostics."""
        key_fingerprint = hashlib.sha256(self.api_key.encode("utf-8")).hexdigest()
        return (self.endpoint, self.ca_cert, key_fingerprint)

    def client_kwargs(self, *, timeout: int) -> dict[str, object]:
        """Return the only supported QdrantClient construction shape for writers."""
        return {
            "url": self.endpoint,
            "api_key": self.api_key,
            "timeout": int(timeout),
            "verify": self.ca_cert,
        }


def _configured_value(
    explicit: str | None,
    environment: Mapping[str, str],
    variable: str,
) -> str:
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip()
    return str(environment.get(variable, "") or "").strip()


def _validate_port(port: int | str) -> int:
    try:
        resolved = int(port)
    except (TypeError, ValueError) as exc:
        raise QdrantTransportError(f"Qdrant port must be an integer; got {port!r}") from exc
    if not 1 <= resolved <= 65535:
        raise QdrantTransportError(f"Qdrant port must be in 1..65535; got {resolved}")
    return resolved


def _endpoint_from_url(raw_url: str) -> str:
    try:
        parsed = urlsplit(raw_url)
        parsed_port = parsed.port
    except ValueError as exc:
        raise QdrantTransportError(f"QDRANT_URL has an invalid port: {raw_url!r}") from exc

    if parsed.scheme.lower() != "https":
        raise QdrantTransportError("QDRANT_URL must use HTTPS; plaintext HTTP is not supported")
    if not parsed.hostname:
        raise QdrantTransportError("QDRANT_URL must include a hostname")
    if parsed.username or parsed.password:
        raise QdrantTransportError("QDRANT_URL must not embed credentials")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise QdrantTransportError("QDRANT_URL must be a bare HTTPS origin without path/query/fragment")

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port_suffix = f":{parsed_port}" if parsed_port is not None else ""
    return f"https://{host}{port_suffix}"


def _endpoint_from_host_port(host: str, port: int | str) -> str:
    normalized_host = str(host or "").strip()
    if not normalized_host:
        raise QdrantTransportError("Qdrant host must not be empty")
    if any(character in normalized_host for character in ":/?#@"):
        raise QdrantTransportError(
            "Qdrant host must be a bare hostname or IPv4 address; use QDRANT_URL for a full HTTPS origin"
        )
    return f"https://{normalized_host}:{_validate_port(port)}"


def qdrant_transport_from_environment(
    *,
    host: str = DEFAULT_QDRANT_HOST,
    port: int | str = DEFAULT_QDRANT_PORT,
    url: str | None = None,
    ca_cert: str | None = None,
    api_key: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> QdrantTransport:
    """Resolve the TLS writer transport without ever weakening its security.

    ``QDRANT_URL`` overrides legacy host/port flags when supplied.  Writers must
    provide a non-empty ``QDRANT_API_KEY`` and a readable CA PEM via
    ``QDRANT_CA_CERT`` (or their explicit non-secret CLI equivalents).
    """
    environment = os.environ if environ is None else environ
    configured_url = _configured_value(url, environment, "QDRANT_URL")
    endpoint = (
        _endpoint_from_url(configured_url)
        if configured_url
        else _endpoint_from_host_port(host, port)
    )

    configured_ca = _configured_value(ca_cert, environment, "QDRANT_CA_CERT")
    if not configured_ca:
        raise QdrantTransportError("QDRANT_CA_CERT is required for the HTTPS writer")
    ca_path = Path(configured_ca).expanduser()
    if not ca_path.is_file():
        raise QdrantTransportError(
            f"QDRANT_CA_CERT does not exist or is not a file: {ca_path}"
        )

    configured_key = _configured_value(api_key, environment, "QDRANT_API_KEY")
    if not configured_key:
        raise QdrantTransportError("QDRANT_API_KEY is required for the Qdrant writer")

    return QdrantTransport(
        endpoint=endpoint,
        ca_cert=str(ca_path),
        api_key=configured_key,
    )


def build_qdrant_client(transport: QdrantTransport, *, timeout: int):
    """Instantiate QdrantClient with the previously validated HTTPS settings."""
    from qdrant_client import QdrantClient

    return QdrantClient(**transport.client_kwargs(timeout=timeout))
