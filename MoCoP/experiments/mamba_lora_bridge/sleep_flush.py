#!/usr/bin/env python3
"""
sleep_flush.py — Minimal sleep flush: drain pending-log to Qdrant.

Reads QDRANT_PENDING_PATH (JSONL), writes validated entries to Qdrant,
rotates the log on success. This is Step 1 of the Direct-Write migration
(see watercooler #181, OpenCLAW #56/#61).

Usage:
    python sleep_flush.py --pending-path qdrant_gate_pending.jsonl
    python sleep_flush.py --pending-path qdrant_gate_pending.jsonl --dry-run
    python sleep_flush.py --pending-path /path/to/pending.jsonl --host 192.168.2.191

Designed to run between sessions (manually, via cron, or at session close).
Does NOT implement full reconciliation (Phases 2-4) — that is Step 3 (#63).
"""

import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from autobiographical_memory import build_recall_text, enrich_memory_metadata, validate_provenance
from qdrant_transport import build_qdrant_client, qdrant_transport_from_environment

PRIVATE_QDRANT_COLLECTION_PREFIX = "mocop_private_"


def load_pending(path: Path):
    """Read JSONL pending log, yield (line_number, record) tuples."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                yield i, record
            except json.JSONDecodeError as exc:
                print(f"[warn] line {i}: bad JSON, skipping — {exc}")


def validate_record(line_num: int, record: dict) -> tuple:
    """Minimal validation. Returns (ok, content, metadata, reason)."""
    content = record.get("content")
    metadata = record.get("metadata")
    reason = record.get("reason", "")

    if not content or not isinstance(content, str):
        print(f"[skip] line {line_num}: missing or empty 'content'")
        return False, None, None, reason

    if not metadata or not isinstance(metadata, dict):
        print(f"[skip] line {line_num}: missing or invalid 'metadata'")
        return False, None, None, reason

    if len(content.strip()) < 10:
        print(f"[skip] line {line_num}: content too short ({len(content.strip())} chars)")
        return False, None, None, reason

    metadata = dict(metadata)
    outer_queued_at = str(record.get("queued_at", "") or "").strip()
    has_creation_time = any(
        str(metadata.get(key, "") or "").strip()
        for key in ("created_at", "timestamp", "queued_at")
    )
    if outer_queued_at and not has_creation_time:
        metadata["queued_at"] = outer_queued_at

    return True, content, metadata, reason


def create_sink(
    host: str,
    port: int,
    collection: str,
    embedding_model: str,
    *,
    qdrant_url: str | None = None,
    qdrant_ca_cert: str | None = None,
):
    """Create a verified-HTTPS Qdrant writer. Imports heavy dependencies lazily."""
    import hashlib

    transport = qdrant_transport_from_environment(
        host=host,
        port=port,
        url=qdrant_url,
        ca_cert=qdrant_ca_cert,
    )

    from qdrant_client.models import Distance, PointStruct, VectorParams
    from sentence_transformers import SentenceTransformer

    client = build_qdrant_client(transport, timeout=10)
    model = SentenceTransformer(embedding_model)
    embedding_dim = int(model.get_sentence_embedding_dimension())
    known_collections = {c.name for c in client.get_collections().collections}

    def ensure_collection(target_collection: str):
        if target_collection in known_collections:
            return
        if not target_collection.startswith(PRIVATE_QDRANT_COLLECTION_PREFIX):
            raise RuntimeError(
                f"Refusing to auto-create non-private Qdrant collection {target_collection!r}."
            )
        client.create_collection(
            collection_name=target_collection,
            vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
        )
        known_collections.add(target_collection)
        print(f"[qdrant] Created private collection {target_collection} dim={embedding_dim}")

    def store(content: str, metadata: dict) -> str:
        metadata = enrich_memory_metadata(content, metadata, speaker_name=metadata.get("speaker_name"))
        identity_text = json.dumps(
            {
                "session": metadata.get("session", ""),
                "turn": metadata.get("turn", ""),
                "decision": metadata.get("decision", ""),
                "user": metadata.get("user", ""),
                "response": metadata.get("response", ""),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        digest = hashlib.md5(identity_text.encode("utf-8")).hexdigest()
        point_id = int(digest[:16], 16)
        recall_text = build_recall_text(content, metadata, speaker_name=metadata.get("speaker_name"))
        vector = model.encode(recall_text).tolist()
        payload = {
            "content": content,
            "recall_text": recall_text,
            "timestamp": datetime.now().isoformat(),
            "stored_at": time.time(),
            "flushed_from_pending": True,
        }
        payload.update(metadata)

        target_collection = str(metadata.get("qdrant_collection") or collection).strip()
        if not target_collection:
            raise RuntimeError("No Qdrant target collection resolved for pending row.")
        # P0-4: hard reject-on-missing-field provenance gate before any write.
        validate_provenance(payload, collection_name=target_collection)
        ensure_collection(target_collection)
        client.upsert(
            collection_name=target_collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return str(point_id)

    return store


def rotate_log(path: Path):
    """Move pending log to timestamped archive."""
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    archive = path.with_suffix(f".flushed_{ts}.jsonl")
    shutil.move(str(path), str(archive))
    print(f"[rotate] {path.name} → {archive.name}")
    return archive


def main():
    parser = argparse.ArgumentParser(description="Flush pending Qdrant writes.")
    parser.add_argument("--pending-path", required=True, help="Path to qdrant_gate_pending.jsonl")
    parser.add_argument("--host", default="192.168.2.191", help="Qdrant host (HTTPS fallback)")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant HTTPS port")
    parser.add_argument("--qdrant-url", default="", help="Verified HTTPS Qdrant origin; overrides --host/--port")
    parser.add_argument("--qdrant-ca-cert", default="", help="PEM root CA path; defaults to QDRANT_CA_CERT")
    parser.add_argument("--collection", default="exocortex", help="Qdrant collection name")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    parser.add_argument("--dry-run", action="store_true", help="Validate and count, don't write")
    parser.add_argument("--no-rotate", action="store_true", help="Don't rotate log after flush")
    args = parser.parse_args()

    pending_path = Path(args.pending_path)
    if not pending_path.exists():
        print(f"[ok] No pending log at {pending_path}. Nothing to flush.")
        return 0

    records = list(load_pending(pending_path))
    if not records:
        print(f"[ok] Pending log is empty. Nothing to flush.")
        return 0

    print(f"[flush] {len(records)} entries in {pending_path}")

    valid = []
    skipped = 0
    for line_num, record in records:
        ok, content, metadata, reason = validate_record(line_num, record)
        if ok:
            valid.append((line_num, content, metadata))
        else:
            skipped += 1

    print(f"[flush] {len(valid)} valid, {skipped} skipped")

    if not valid:
        print("[done] No valid entries to flush.")
        return 0

    if args.dry_run:
        print(f"[dry-run] Would write {len(valid)} entries to {args.host}:{args.port}")
        for line_num, content, metadata in valid:
            decision = metadata.get("decision", "?")
            target_collection = str(metadata.get("qdrant_collection") or args.collection).strip()
            preview = content[:80].replace("\n", " ")
            print(f"  line {line_num}: [{decision}] -> {target_collection} {preview}...")
        return 0

    store = create_sink(
        args.host,
        args.port,
        args.collection,
        args.embedding_model,
        qdrant_url=args.qdrant_url,
        qdrant_ca_cert=args.qdrant_ca_cert,
    )

    written = 0
    failed = 0
    for line_num, content, metadata in valid:
        try:
            point_id = store(content, metadata)
            written += 1
            decision = metadata.get("decision", "?")
            print(f"  [ok] line {line_num}: [{decision}] → {point_id}")
        except Exception as exc:
            failed += 1
            print(f"  [fail] line {line_num}: {exc}")

    print(f"[flush] {written} written, {failed} failed, {skipped} skipped")

    if failed > 0:
        print("[warn] Some writes failed. Pending log NOT rotated — retry later.")
        return 1

    if not args.no_rotate:
        rotate_log(pending_path)

    print("[done] Sleep flush complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
