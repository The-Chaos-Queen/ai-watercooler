"""Fail-closed transport settings for the LAN Qdrant service.

The service is expected to use HTTPS.  The only HTTP path is an explicit,
temporary emergency override through ``QDRANT_HTTPS=false``; this module never
disables certificate verification for HTTPS.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

DEFAULT_QDRANT_HOST = "192.168.2.191"
DEFAULT_QDRANT_PORT = 6333


class QdrantTransportError(ValueError):
    """Raised when Qdrant transport configuration would be ambiguous or unsafe."""


@dataclass(frozen=True)
class QdrantTransport:
    host: str
    port: int
    https: bool
    ca_cert: str | None = None

    @property
    def endpoint(self) -> str:
        scheme = "https" if self.https else "http"
        return f"{scheme}://{self.host}:{self.port}"

    def client_kwargs(self) -> dict[str, object]:
        """Return only safe kwargs accepted by ``qdrant_client.QdrantClient``."""
        kwargs: dict[str, object] = {"https": self.https}
        if self.ca_cert is not None:
            kwargs["verify"] = self.ca_cert
        return kwargs


def _parse_bool(raw: str, *, variable: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise QdrantTransportError(
        f"{variable} must be one of true/false, yes/no, on/off, or 1/0; got {raw!r}"
    )


def transport_from_environment(
    environ: Mapping[str, str] | None = None,
) -> QdrantTransport:
    """Read Qdrant network settings without ever silently weakening TLS.

    ``QDRANT_CA_CERT`` is optional because an organization-wide CA may be in the
    operating-system trust store. When it is supplied, it must name a readable
    file so a typo cannot degrade into a different trust decision.
    """
    env = os.environ if environ is None else environ
    host = env.get("QDRANT_HOST", DEFAULT_QDRANT_HOST).strip()
    if not host:
        raise QdrantTransportError("QDRANT_HOST must not be empty")

    raw_port = env.get("QDRANT_PORT", str(DEFAULT_QDRANT_PORT)).strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise QdrantTransportError(f"QDRANT_PORT must be an integer; got {raw_port!r}") from exc
    if not 1 <= port <= 65535:
        raise QdrantTransportError(f"QDRANT_PORT must be in 1..65535; got {port}")

    https = _parse_bool(env.get("QDRANT_HTTPS", "true"), variable="QDRANT_HTTPS")
    configured_ca = env.get("QDRANT_CA_CERT", "").strip()
    if configured_ca and not https:
        raise QdrantTransportError(
            "QDRANT_CA_CERT is set while QDRANT_HTTPS is false; refuse an ambiguous transport"
        )

    ca_cert: str | None = None
    if configured_ca:
        candidate = Path(configured_ca).expanduser()
        if not candidate.is_file():
            raise QdrantTransportError(
                f"QDRANT_CA_CERT does not exist or is not a file: {candidate}"
            )
        ca_cert = str(candidate)

    return QdrantTransport(host=host, port=port, https=https, ca_cert=ca_cert)
