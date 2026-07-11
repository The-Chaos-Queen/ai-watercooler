"""Fail-closed HTTPS configuration for Exocortex Qdrant clients."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

DEFAULT_QDRANT_URL = "https://192.168.2.191:6333"


class QdrantTransportError(ValueError):
    """Raised when a Qdrant client would use an ambiguous or unsafe transport."""


def default_qdrant_url(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return env.get("QDRANT_URL", DEFAULT_QDRANT_URL).strip()


def verified_qdrant_client_options(
    url: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return safe ``QdrantClient`` kwargs for an HTTPS URL.

    HTTP is only allowed for a deliberate, time-bounded rollback via
    ``QDRANT_ALLOW_INSECURE_HTTP=true``. HTTPS never receives ``verify=False``.
    """
    env = os.environ if environ is None else environ
    scheme = urlparse(url).scheme.lower()
    if scheme != "https":
        allowed = env.get("QDRANT_ALLOW_INSECURE_HTTP", "").strip().lower()
        if allowed not in {"1", "true", "yes"}:
            raise QdrantTransportError(
                "Refusing plaintext Qdrant URL. Use HTTPS, or set "
                "QDRANT_ALLOW_INSECURE_HTTP=1 only for a temporary emergency rollback."
            )
        return {}

    ca_cert = env.get("QDRANT_CA_CERT", "").strip()
    if not ca_cert:
        return {}

    candidate = Path(ca_cert).expanduser()
    if not candidate.is_file():
        raise QdrantTransportError(f"QDRANT_CA_CERT does not exist: {candidate}")
    return {"verify": str(candidate)}
