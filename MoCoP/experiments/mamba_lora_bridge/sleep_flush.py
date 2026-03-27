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

from autobiographical_memory import build_recall_text, enrich_memory_metadata


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

    return True, content, metadata, reason


def create_sink(host: str, port: int, collection: str, embedding_model: str):
    """Create a QdrantGateSink-compatible writer. Imports lazily."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    from sentence_transformers import SentenceTransformer
    import hashlib

    client = QdrantClient(host=host, port=port, timeout=10)
    model = SentenceTransformer(embedding_model)

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
        client.upsert(
            collection_name=collection,
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
    parser.add_argument("--host", default="192.168.2.191", help="Qdrant host")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant port")
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
        print(f"[dry-run] Would write {len(valid)} entries to "
              f"{args.host}:{args.port}/{args.collection}")
        for line_num, content, metadata in valid:
            decision = metadata.get("decision", "?")
            preview = content[:80].replace("\n", " ")
            print(f"  line {line_num}: [{decision}] {preview}...")
        return 0

    store = create_sink(args.host, args.port, args.collection, args.embedding_model)

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
