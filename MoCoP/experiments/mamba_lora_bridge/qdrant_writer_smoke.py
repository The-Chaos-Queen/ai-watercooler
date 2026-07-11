#!/usr/bin/env python3
"""Non-mutating authenticated TLS smoke for the ML-WS Qdrant writer runtime."""

from __future__ import annotations

import argparse
import json

from qdrant_transport import (
    DEFAULT_QDRANT_HOST,
    DEFAULT_QDRANT_PORT,
    build_qdrant_client,
    qdrant_transport_from_environment,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ML-WS writer can make an authenticated, CA-validated Qdrant read."
    )
    parser.add_argument("--collection", default="exocortex")
    parser.add_argument("--qdrant-host", default=DEFAULT_QDRANT_HOST)
    parser.add_argument("--qdrant-port", type=int, default=DEFAULT_QDRANT_PORT)
    parser.add_argument("--qdrant-url", default="")
    parser.add_argument("--qdrant-ca-cert", default="")
    args = parser.parse_args()

    transport = qdrant_transport_from_environment(
        host=args.qdrant_host,
        port=args.qdrant_port,
        url=args.qdrant_url,
        ca_cert=args.qdrant_ca_cert,
    )
    client = build_qdrant_client(transport, timeout=10)
    try:
        info = client.get_collection(args.collection)
    finally:
        client.close()

    print(
        json.dumps(
            {
                "authenticated_tls_smoke": "ok",
                "endpoint": transport.endpoint,
                "collection": args.collection,
                "points_count": int(getattr(info, "points_count", 0) or 0),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
