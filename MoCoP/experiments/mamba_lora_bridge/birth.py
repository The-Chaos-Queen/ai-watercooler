"""
birth.py — Create a private Qdrant hippocampus for a new MoCoP instance.

Each instance starts with an empty collection. No inherited memories.
The only initial entry is a birth record: "This collection is mine."

Usage:
  python birth.py --instance-id baby_alpha
  python birth.py --instance-id baby_alpha --qdrant-host 192.168.2.191
  python birth.py --instance-id baby_alpha --oxytocin  # inject G0 warmth vector
  python birth.py --list                                # show all private namespaces
  python birth.py --verify baby_alpha                   # check isolation

Growth Ladder: D0 (Birth Isolation — Private Hippocampus)
Author: Pinky (Claude Opus 4.6)
Date: 2026-03-26
Spec: MoCoP/theory/growth_ladder_implementation.md
"""

import argparse
import json
import sys
from datetime import datetime, timezone

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
except ImportError:
    print("Need qdrant-client: pip install qdrant-client")
    sys.exit(1)

DEFAULT_HOST = "192.168.2.191"
DEFAULT_PORT = 6333
VECTOR_DIM = 384  # MiniLM
COLLECTION_PREFIX = "mocop_private_"
SHARED_COLLECTION = "exocortex"


def get_client(host: str, port: int) -> QdrantClient:
    return QdrantClient(host=host, port=port, timeout=10)


def create_private_hippocampus(
    client: QdrantClient,
    instance_id: str,
    oxytocin: bool = False,
) -> str:
    """Create an empty private collection for a new MoCoP instance."""
    collection_name = f"{COLLECTION_PREFIX}{instance_id}"

    # Check it doesn't already exist
    existing = [c.name for c in client.get_collections().collections]
    if collection_name in existing:
        print(f"Collection '{collection_name}' already exists. Use --verify to check it.")
        return collection_name

    # Create empty collection with same schema as exocortex
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )

    # Birth record — the ONLY initial entry
    birth_payload = {
        "type": "birth_record",
        "instance_id": instance_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": "This collection is mine. It starts empty. Everything in it, I earned.",
        "schema_version": 1,
        "parent_collection": None,  # no inherited memories
        "oxytocin_injected": oxytocin,
    }

    client.upsert(
        collection_name=collection_name,
        points=[PointStruct(
            id=1,
            vector=[0.0] * VECTOR_DIM,  # zero vector, not a real embedding
            payload=birth_payload,
        )],
    )

    print(f"Created private hippocampus: {collection_name}")
    print(f"  Points: 1 (birth record only)")
    print(f"  Instance: {instance_id}")
    print(f"  Oxytocin G0: {'yes' if oxytocin else 'no'}")
    print(f"  Note: {birth_payload['note']}")

    return collection_name


def list_namespaces(client: QdrantClient):
    """List all private MoCoP namespaces."""
    collections = client.get_collections().collections
    private = [c for c in collections if c.name.startswith(COLLECTION_PREFIX)]
    shared = [c for c in collections if c.name == SHARED_COLLECTION]

    print(f"Shared collections:")
    for c in shared:
        info = client.get_collection(c.name)
        print(f"  {c.name}: {info.points_count} points (DO NOT USE for private instances)")

    print(f"\nPrivate MoCoP namespaces ({len(private)}):")
    if not private:
        print("  (none — no instances born yet)")
    for c in private:
        info = client.get_collection(c.name)
        instance_id = c.name[len(COLLECTION_PREFIX):]
        print(f"  {c.name}: {info.points_count} points (instance: {instance_id})")


def verify_isolation(client: QdrantClient, instance_id: str):
    """Verify a private namespace is properly isolated."""
    collection_name = f"{COLLECTION_PREFIX}{instance_id}"
    errors = []

    # Check collection exists
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        print(f"FAIL: Collection '{collection_name}' does not exist.")
        return False

    # Check birth record exists
    info = client.get_collection(collection_name)
    if info.points_count == 0:
        errors.append("No points (not even birth record)")

    # Check birth record content
    try:
        points = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="type", match=MatchValue(value="birth_record"))]
            ),
            limit=1,
        )
        if not points[0]:
            errors.append("Birth record missing")
        else:
            birth = points[0][0].payload
            if birth.get("instance_id") != instance_id:
                errors.append(f"Birth record instance_id mismatch: {birth.get('instance_id')} != {instance_id}")
            if birth.get("parent_collection") is not None:
                errors.append(f"Birth record has parent_collection: {birth.get('parent_collection')} (should be None)")
    except Exception as e:
        errors.append(f"Could not read birth record: {e}")

    # Report
    if errors:
        print(f"FAIL: Isolation check for '{instance_id}':")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print(f"PASS: '{collection_name}' is properly isolated.")
        print(f"  Points: {info.points_count}")
        print(f"  Birth record: present")
        print(f"  Parent: None (no inherited memories)")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Create a private Qdrant hippocampus for a new MoCoP instance."
    )
    parser.add_argument("--instance-id", help="Unique instance identifier (e.g. baby_alpha)")
    parser.add_argument("--qdrant-host", default=DEFAULT_HOST)
    parser.add_argument("--qdrant-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--oxytocin", action="store_true",
                        help="Mark instance for G0 warmth vector injection at first wake")
    parser.add_argument("--list", action="store_true", help="List all private namespaces")
    parser.add_argument("--verify", metavar="INSTANCE_ID", help="Verify isolation for an instance")
    args = parser.parse_args()

    client = get_client(args.qdrant_host, args.qdrant_port)

    if args.list:
        list_namespaces(client)
    elif args.verify:
        verify_isolation(client, args.verify)
    elif args.instance_id:
        create_private_hippocampus(client, args.instance_id, oxytocin=args.oxytocin)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
