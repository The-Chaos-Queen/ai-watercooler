"""
flush_qdrant_pending.py - Minimal pending-log flush for Steve gate writes.

Reads queued Qdrant rows from a JSONL file, upserts them into the shared
Exocortex collection, archives successes, and rewrites the pending file with
only the rows that still failed or were not processed.
"""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


def append_jsonl(path: Path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.lstrip("\ufeff").strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError:
                rows.append(
                    {
                        "content": "",
                        "metadata": {},
                        "attempts": 1,
                        "last_error": "invalid_jsonl_row",
                        "raw_line": text,
                    }
                )
    return rows


def rewrite_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class QdrantGateSink:
    def __init__(self, host: str, port: int, collection_name: str, embedding_model: str):
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct
        from sentence_transformers import SentenceTransformer

        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port, timeout=15)
        self.point_struct_cls = PointStruct
        self.model = SentenceTransformer(embedding_model)

    def _embed(self, text: str):
        return self.model.encode(text).tolist()

    def _make_id(self, metadata) -> int:
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
        return int(digest[:16], 16)

    def store(self, content: str, metadata) -> str:
        point_id = self._make_id(metadata)
        vector = self._embed(content)
        payload = {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "stored_at": datetime.now().timestamp(),
        }
        payload.update(metadata)
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                self.point_struct_cls(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        return str(point_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pending-path", required=True)
    parser.add_argument("--archive-path", required=True)
    parser.add_argument("--qdrant-host", default="192.168.2.191")
    parser.add_argument("--qdrant-port", type=int, default=6333)
    parser.add_argument("--qdrant-collection", default="exocortex")
    parser.add_argument("--qdrant-embedding-model", default="all-MiniLM-L6-v2")
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    pending_path = Path(args.pending_path)
    archive_path = Path(args.archive_path)
    rows = load_jsonl(pending_path)
    sink = QdrantGateSink(
        host=args.qdrant_host,
        port=args.qdrant_port,
        collection_name=args.qdrant_collection,
        embedding_model=args.qdrant_embedding_model,
    )

    kept_rows = []
    success_rows = []
    point_ids = []
    processed = 0

    for row in rows:
        if processed >= args.max_items:
            kept_rows.append(row)
            continue

        content = str(row.get("content", "") or "").strip()
        metadata = row.get("metadata") or {}
        if not content or not isinstance(metadata, dict):
            updated = dict(row)
            updated["attempts"] = int(updated.get("attempts", 0) or 0) + 1
            updated["last_error"] = "missing_content_or_metadata"
            kept_rows.append(updated)
            processed += 1
            continue

        try:
            point_id = sink.store(content=content, metadata=metadata)
            archived = dict(row)
            archived["flushed_at"] = datetime.now().isoformat()
            archived["point_id"] = point_id
            success_rows.append(archived)
            point_ids.append(point_id)
        except Exception as exc:
            updated = dict(row)
            updated["attempts"] = int(updated.get("attempts", 0) or 0) + 1
            updated["last_error"] = str(exc)
            updated["last_flush_attempt_at"] = datetime.now().isoformat()
            kept_rows.append(updated)
        processed += 1

    rewrite_jsonl(pending_path, kept_rows)
    for row in success_rows:
        append_jsonl(archive_path, row)

    summary = {
        "ok": True,
        "pending_path": str(pending_path),
        "archive_path": str(archive_path),
        "processed": processed,
        "flushed": len(success_rows),
        "remaining": len(kept_rows),
        "point_ids": point_ids,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"processed={summary['processed']} flushed={summary['flushed']} "
            f"remaining={summary['remaining']}"
        )


if __name__ == "__main__":
    main()
