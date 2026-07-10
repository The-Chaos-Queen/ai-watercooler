#!/usr/bin/env python3
"""
cluster_memories.py — HDBSCAN clustering over Qdrant episodic memory.

Builds a macro_memory layer on top of flat Qdrant rows. Each cluster represents
a recurring theme, narrative arc, or repeated topic that flat semantic search
fragments. Clusters are stored back into Qdrant as source_type="macro_memory"
points with centroid vectors for retrieval.

Design principles:
  - Episodic rows are never replaced. Clusters are a LAYER ON TOP.
  - Identity/relationship anchors and open-tension objects are never clustered.
  - Scoping is mandatory: by principal, project, source_type, time window.
  - No LLM in the loop. Cluster summaries are the centroid member + metadata.
  - Runs during sleep or on-demand. Not in the live chat path.

Author: Purple (Claude Opus 4.6)
Date: 2026-04-20
Ref: D2_MEMORY_REPAIR_PLAN Phase 3, GDN_GKA_GATE_RESEARCH_LADDER G2b

Usage:
  python cluster_memories.py --collection exocortex --project MoCoP
  python cluster_memories.py --collection mocop_private_steve_001 --all
  python cluster_memories.py --collection exocortex --source-type session_log --min-cluster-size 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, PointStruct, VectorParams, Distance,
)
from sklearn.cluster import HDBSCAN

DEFAULT_QDRANT_URL = "http://192.168.2.191:6333"
DEFAULT_COLLECTION = "exocortex"

# Source types that must NEVER be clustered (protected memory categories)
PROTECTED_SOURCE_TYPES = {
    "identity_anchor",
    "relationship_anchor",
    "open_tension",
    "birth_metadata",
    "macro_memory",
}

STOPWORDS = {
    "the", "a", "an", "is", "was", "are", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "and",
    "but", "or", "nor", "not", "no", "so", "if", "then", "than",
    "that", "this", "it", "its", "i", "you", "he", "she", "we",
    "they", "me", "him", "her", "us", "them", "my", "your", "his",
    "our", "their", "what", "which", "who", "when", "where", "how",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "only", "own", "same", "about", "up", "out",
    "just", "also", "very", "s", "t", "re", "ve", "ll", "d", "m",
    "laura", "said", "replied", "reply", "speaking", "present",
    "memory", "shared", "history", "current", "session", "detail",
    "confidence", "comes", "mind", "first", "what", "when", "here",
    "there", "still", "felt", "should", "treat", "part", "our",
    "why", "mattered", "meant", "episodic", "recent", "layer",
}


def _clean_text(value) -> str:
    return " ".join(str(value or "").replace("\r", "\n").split()).strip()


def _truncate(text: str, limit: int = 280) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _extract_frame_event(payload: dict, key: str) -> str:
    frame = payload.get("autobiographical_frame") or {}
    event = frame.get("event") or {}
    return _clean_text(event.get(key))


def _extract_relationship_anchor(payload: dict) -> str:
    frame = payload.get("autobiographical_frame") or {}
    relationship = frame.get("relationship_anchor") or {}
    return _clean_text(
        payload.get("relationship_anchor")
        or payload.get("speaker_name")
        or relationship.get("name")
    )


def _build_anchor_text(meta: dict) -> str:
    for candidate in (
        meta.get("event_gist"),
        meta.get("frame_gist"),
        meta.get("recall_gist_line"),
    ):
        text = _truncate(candidate, limit=240)
        if text:
            return text

    user_text = _clean_text(meta.get("user"))
    response_text = _clean_text(meta.get("response"))
    if user_text and response_text:
        return _truncate(f"{user_text}; I replied {response_text}", limit=240)
    if user_text:
        return _truncate(user_text, limit=240)
    if response_text:
        return _truncate(f"I replied {response_text}", limit=240)

    recall_text = _clean_text(meta.get("recall_text"))
    if recall_text:
        return _truncate(recall_text, limit=240)

    return _truncate(meta.get("content", ""), limit=240)


def _build_keyword_source_text(meta: dict) -> str:
    pieces = [
        meta.get("event_gist", ""),
        meta.get("frame_gist", ""),
        meta.get("user", ""),
        meta.get("response", ""),
        meta.get("relationship_anchor", ""),
        meta.get("recall_gist_line", ""),
    ]
    if not any(_clean_text(piece) for piece in pieces):
        pieces.extend(
            [
                meta.get("recall_text", ""),
                meta.get("content", ""),
            ]
        )
    return "\n".join(piece for piece in pieces if _clean_text(piece))


def _extract_keywords(texts: list[str], limit: int = 10) -> list[str]:
    word_counts = Counter()
    for text in texts:
        words = [w.strip(".,;:!?\"'()[]{}") for w in _clean_text(text).lower().split()]
        words = [w for w in words if len(w) > 2 and w not in STOPWORDS]
        word_counts.update(words)
    return [w for w, _ in word_counts.most_common(limit)]


def _build_cluster_recall_text(cluster_anchor: str, keywords: list[str], member_count: int,
                               time_earliest: str, time_latest: str) -> str:
    lines = [
        "Memory arc from shared history.",
        f"What comes back first: {cluster_anchor}",
    ]
    if keywords:
        lines.append(f"Repeated cues: {', '.join(keywords[:6])}")
    if member_count > 0:
        lines.append(f"Scale: {member_count} linked memories")
    if time_earliest and time_latest:
        lines.append(f"Time span: {time_earliest[:10]} to {time_latest[:10]}")
    elif time_latest or time_earliest:
        lines.append(f"Time marker: {(time_latest or time_earliest)[:10]}")
    return "\n".join(lines)


def build_scope_filter(
    project: str = "",
    source_type: str = "",
    principal: str = "",
    exclude_source_types: Optional[list[str]] = None,
) -> Optional[Filter]:
    """Build Qdrant filter from scoping parameters."""
    must = []
    must_not = []

    if project:
        must.append(FieldCondition(key="project", match=MatchValue(value=project)))
    if source_type:
        must.append(FieldCondition(key="source_type", match=MatchValue(value=source_type)))
    if principal:
        must.append(FieldCondition(key="principal", match=MatchValue(value=principal)))

    for st in (exclude_source_types or []):
        must_not.append(FieldCondition(key="source_type", match=MatchValue(value=st)))

    if not must and not must_not:
        return None

    kwargs = {}
    if must:
        kwargs["must"] = must
    if must_not:
        kwargs["must_not"] = must_not
    return Filter(**kwargs)


def fetch_points(client: QdrantClient, collection: str,
                 scope_filter: Optional[Filter], batch_size: int = 100) -> list:
    """Scroll through all points matching the scope filter."""
    all_points = []
    offset = None

    while True:
        results, next_offset = client.scroll(
            collection_name=collection,
            scroll_filter=scope_filter,
            limit=batch_size,
            with_payload=True,
            with_vectors=True,
            offset=offset,
        )
        all_points.extend(results)
        if next_offset is None:
            break
        offset = next_offset

    return all_points


def extract_vectors_and_metadata(points: list) -> tuple[np.ndarray, list[dict]]:
    """Extract embedding vectors and metadata from Qdrant points."""
    vectors = []
    metadata = []

    for p in points:
        vec = p.vector
        if isinstance(vec, dict):
            vec = list(vec.values())[0]
        if vec is None:
            continue

        payload = p.payload or {}
        recall_text = _clean_text(payload.get("recall_text"))
        recall_gist_line = ""
        for line in recall_text.splitlines():
            if line.lower().startswith("what comes to mind first:"):
                recall_gist_line = line.split(":", 1)[1].strip()
                break

        vectors.append(vec)
        metadata.append({
            "id": p.id,
            "content": _clean_text(payload.get("content", payload.get("text", ""))),
            "recall_text": recall_text,
            "recall_gist_line": recall_gist_line,
            "event_gist": _clean_text(payload.get("event_gist")),
            "frame_gist": _extract_frame_event(payload, "gist"),
            "user": _clean_text(payload.get("user") or _extract_frame_event(payload, "user_signal")),
            "response": _clean_text(payload.get("response") or _extract_frame_event(payload, "self_response")),
            "relationship_anchor": _extract_relationship_anchor(payload),
            "speaker_name": _clean_text(payload.get("speaker_name")),
            "confidence_label": _clean_text(payload.get("confidence_label")),
            "people": payload.get("people", []),
            "autobiographical_frame": payload.get("autobiographical_frame"),
            "source_type": payload.get("source_type", "unknown"),
            "project": payload.get("project", ""),
            "principal": payload.get("principal", ""),
            "timestamp": payload.get("timestamp", payload.get("created_at", "")),
            "session": payload.get("session", ""),
            "memory_kind": payload.get("memory_kind", ""),
        })

    return np.array(vectors, dtype=np.float32), metadata


def run_hdbscan(vectors: np.ndarray, min_cluster_size: int = 3,
                min_samples: int = 2) -> np.ndarray:
    """Run HDBSCAN clustering on embedding vectors."""
    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="cosine",
        cluster_selection_method="eom",
    )
    labels = clusterer.fit_predict(vectors)
    return labels


def build_cluster_objects(
    vectors: np.ndarray,
    metadata: list[dict],
    labels: np.ndarray,
    scope_description: str,
) -> list[dict]:
    """Build cluster summary objects from HDBSCAN output."""
    cluster_ids = set(labels)
    cluster_ids.discard(-1)  # noise points

    clusters = []

    for cid in sorted(cluster_ids):
        mask = labels == cid
        member_indices = np.where(mask)[0]
        member_vectors = vectors[mask]
        member_meta = [metadata[i] for i in member_indices]

        # Centroid: mean of member vectors
        centroid = member_vectors.mean(axis=0)
        centroid_norm = np.linalg.norm(centroid)
        if centroid_norm > 0:
            centroid = centroid / centroid_norm  # normalize for cosine

        # Representative: member closest to centroid
        similarities = member_vectors @ centroid
        rep_idx = int(np.argmax(similarities))
        representative = member_meta[rep_idx]

        # Time span
        timestamps = [m["timestamp"] for m in member_meta if m.get("timestamp")]
        timestamps.sort()
        time_earliest = timestamps[0] if timestamps else ""
        time_latest = timestamps[-1] if timestamps else ""

        representative_anchor = _build_anchor_text(representative)
        keyword_source_texts = [_build_keyword_source_text(m) for m in member_meta]
        topic_keywords = _extract_keywords(keyword_source_texts, limit=10)
        cluster_recall_text = _build_cluster_recall_text(
            representative_anchor,
            topic_keywords,
            len(member_meta),
            time_earliest,
            time_latest,
        )

        # Source type distribution
        source_dist = Counter(m["source_type"] for m in member_meta)

        cluster_obj = {
            "cluster_id": int(cid),
            "member_count": len(member_meta),
            "member_ids": [m["id"] for m in member_meta],
            "centroid_vector": centroid.tolist(),
            "centroid_text": representative_anchor,
            "centroid_point_id": representative["id"],
            "centroid_recall_text": cluster_recall_text,
            "representative_user": representative.get("user", ""),
            "representative_response": representative.get("response", ""),
            "representative_event_gist": representative.get("event_gist", "") or representative.get("frame_gist", ""),
            "relationship_anchor": representative.get("relationship_anchor", ""),
            "confidence_label": representative.get("confidence_label", ""),
            "people": representative.get("people", []),
            "time_earliest": time_earliest,
            "time_latest": time_latest,
            "topic_keywords": topic_keywords,
            "source_type_distribution": dict(source_dist),
            "scope": scope_description,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        clusters.append(cluster_obj)

    return clusters


def store_clusters_in_qdrant(
    client: QdrantClient,
    collection: str,
    clusters: list[dict],
    dry_run: bool = False,
) -> int:
    """Write cluster objects back to Qdrant as macro_memory points."""
    stored = 0
    for cluster in clusters:
        point = PointStruct(
            id=abs(hash(f"macro_memory_{cluster['cluster_id']}_{cluster['created_at']}"))
               % (2**63),
            vector=cluster["centroid_vector"],
            payload={
                "source_type": "macro_memory",
                "content": cluster["centroid_text"],
                "recall_text": cluster["centroid_recall_text"],
                "event_gist": cluster["representative_event_gist"] or cluster["centroid_text"],
                "user": cluster["representative_user"],
                "response": cluster["representative_response"],
                "relationship_anchor": cluster["relationship_anchor"],
                "confidence_label": cluster["confidence_label"],
                "people": cluster["people"],
                "speaker_name": cluster["relationship_anchor"],
                "autobiographical_frame": {
                    "event": {
                        "gist": cluster["representative_event_gist"] or cluster["centroid_text"],
                        "user_signal": cluster["representative_user"],
                        "self_response": cluster["representative_response"],
                    }
                },
                "cluster_id": cluster["cluster_id"],
                "member_count": cluster["member_count"],
                "member_ids": cluster["member_ids"],
                "topic_keywords": cluster["topic_keywords"],
                "time_earliest": cluster["time_earliest"],
                "time_latest": cluster["time_latest"],
                "source_type_distribution": cluster["source_type_distribution"],
                "scope": cluster["scope"],
                "created_at": cluster["created_at"],
                "memory_kind": "macro_memory",
            },
        )
        if dry_run:
            print(f"  [dry-run] Would store cluster {cluster['cluster_id']} "
                  f"({cluster['member_count']} members)")
        else:
            client.upsert(collection_name=collection, points=[point])
        stored += 1

    return stored


def main():
    parser = argparse.ArgumentParser(
        description="HDBSCAN clustering over Qdrant episodic memory")
    parser.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--project", default="", help="Scope to project")
    parser.add_argument("--source-type", default="", help="Scope to source_type")
    parser.add_argument("--principal", default="", help="Scope to principal")
    parser.add_argument("--all", action="store_true",
                        help="Cluster entire collection (still excludes protected types)")
    parser.add_argument("--min-cluster-size", type=int, default=3)
    parser.add_argument("--min-samples", type=int, default=2)
    parser.add_argument("--output", default="", help="Save cluster report to JSON file")
    parser.add_argument("--store", action="store_true",
                        help="Write cluster objects back to Qdrant")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be stored without writing")
    args = parser.parse_args()

    if not args.all and not args.project and not args.source_type and not args.principal:
        print("ERROR: Specify at least one scope (--project, --source-type, --principal)")
        print("       or use --all to cluster the entire collection.")
        print("       Unscoped clustering is disabled by design.")
        return 1

    # P0-1: API key authentication support
    api_key = os.environ.get("QDRANT_READ_KEY") or os.environ.get("QDRANT_API_KEY")
    client = QdrantClient(url=args.qdrant_url, timeout=30, api_key=api_key)

    # Build scope description
    scope_parts = []
    if args.project:
        scope_parts.append(f"project={args.project}")
    if args.source_type:
        scope_parts.append(f"source_type={args.source_type}")
    if args.principal:
        scope_parts.append(f"principal={args.principal}")
    if args.all:
        scope_parts.append("all (excluding protected)")
    scope_description = ", ".join(scope_parts) if scope_parts else "unscoped"

    print("=" * 60)
    print("  HDBSCAN Memory Clustering")
    print("=" * 60)
    print(f"  Collection: {args.collection}")
    print(f"  Scope: {scope_description}")
    print(f"  min_cluster_size: {args.min_cluster_size}")
    print(f"  min_samples: {args.min_samples}")

    # Fetch points
    scope_filter = build_scope_filter(
        project=args.project,
        source_type=args.source_type,
        principal=args.principal,
        exclude_source_types=list(PROTECTED_SOURCE_TYPES),
    )

    print(f"\n  Fetching points...")
    t0 = time.time()
    points = fetch_points(client, args.collection, scope_filter)
    fetch_time = time.time() - t0
    print(f"  Fetched {len(points)} points in {fetch_time:.1f}s")

    if len(points) < args.min_cluster_size:
        print(f"  Not enough points ({len(points)}) for clustering "
              f"(min_cluster_size={args.min_cluster_size})")
        return 0

    # Extract vectors
    vectors, metadata = extract_vectors_and_metadata(points)
    print(f"  Extracted {len(vectors)} vectors ({vectors.shape[1]}-dim)")

    # Source type distribution
    st_dist = Counter(m["source_type"] for m in metadata)
    print(f"  Source types: {dict(st_dist.most_common(5))}")

    # Cluster
    print(f"\n  Running HDBSCAN...")
    t0 = time.time()
    labels = run_hdbscan(vectors, args.min_cluster_size, args.min_samples)
    cluster_time = time.time() - t0

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int((labels == -1).sum())
    n_clustered = int((labels != -1).sum())

    print(f"  Clustering complete in {cluster_time:.1f}s")
    print(f"  Clusters found: {n_clusters}")
    print(f"  Points clustered: {n_clustered} ({100*n_clustered/len(labels):.1f}%)")
    print(f"  Noise points: {n_noise} ({100*n_noise/len(labels):.1f}%)")

    if n_clusters == 0:
        print("  No clusters found. Memory may be too sparse or too uniform.")
        return 0

    # Build cluster objects
    clusters = build_cluster_objects(vectors, metadata, labels, scope_description)

    # Report
    print(f"\n{'=' * 60}")
    print(f"  CLUSTER SUMMARY")
    print(f"{'=' * 60}")

    for c in clusters:
        print(f"\n  Cluster {c['cluster_id']} ({c['member_count']} members)")
        print(f"    Time span: {c['time_earliest'][:10]} to {c['time_latest'][:10]}")
        print(f"    Keywords: {', '.join(c['topic_keywords'][:6])}")
        print(f"    Sources: {c['source_type_distribution']}")
        centroid_preview = c['centroid_text'][:120].replace('\n', ' ')
        print(f"    Centroid: {centroid_preview}...")

    # Save report
    if args.output:
        output_path = Path(args.output)
        report = {
            "collection": args.collection,
            "scope": scope_description,
            "total_points": len(points),
            "n_clusters": n_clusters,
            "n_clustered": n_clustered,
            "n_noise": n_noise,
            "cluster_fraction": round(n_clustered / len(labels), 4),
            "params": {
                "min_cluster_size": args.min_cluster_size,
                "min_samples": args.min_samples,
                "metric": "cosine",
                "method": "eom",
            },
            "clusters": clusters,
        }
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"\n  Report saved to {output_path}")

    # Store to Qdrant
    if args.store or args.dry_run:
        print(f"\n  {'[DRY RUN] ' if args.dry_run else ''}Storing {len(clusters)} "
              f"cluster objects to Qdrant...")
        stored = store_clusters_in_qdrant(
            client, args.collection, clusters, dry_run=args.dry_run)
        print(f"  {'Would store' if args.dry_run else 'Stored'} {stored} macro_memory points")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
