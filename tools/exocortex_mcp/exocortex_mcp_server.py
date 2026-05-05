#!/usr/bin/env python3
"""
exocortex_mcp_server.py — MCP server exposing Qdrant-backed Exocortex memory to AI surfaces.

Lets any wolf search, browse, and inspect the shared Exocortex memory store
via the Model Context Protocol.

Auth: none (local-only, same trust model as direct Qdrant access).

Transport: stdio (for Claude Code `claude mcp add`).

Usage:
  python tools/exocortex_mcp/exocortex_mcp_server.py

  # Or override defaults:
  python tools/exocortex_mcp/exocortex_mcp_server.py \
    --qdrant-url http://192.168.2.191:6333 \
    --collection exocortex \
    --model all-MiniLM-L6-v2

  # Register with Claude Code:
  claude mcp add exocortex -- python tools/exocortex_mcp/exocortex_mcp_server.py
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("exocortex-mcp")

# ---------------------------------------------------------------------------
# Globals (set in main)
# ---------------------------------------------------------------------------

QDRANT: Optional[QdrantClient] = None
EMBEDDER: Optional[SentenceTransformer] = None
COLLECTION: str = "exocortex"

mcp = FastMCP("Exocortex Memory")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _embed(text: str) -> list[float]:
    """Embed a query string using the loaded model."""
    return EMBEDDER.encode(text).tolist()


def _format_point(point) -> dict:
    """Format a Qdrant point into a clean dict."""
    payload = point.payload or {}
    return {
        "id": str(point.id),
        "score": round(point.score, 4) if hasattr(point, "score") and point.score is not None else None,
        "content": payload.get("content", payload.get("text", "")),
        "source_type": payload.get("source_type", "unknown"),
        "project": payload.get("project", ""),
        "principal": payload.get("principal", ""),
        "timestamp": payload.get("timestamp", payload.get("created_at", "")),
        "session": payload.get("session", ""),
        "tags": payload.get("tags", []),
        "decision": payload.get("decision", ""),
    }


def _build_filter(
    source_type: str = "",
    project: str = "",
    principal: str = "",
) -> Optional[Filter]:
    """Build a Qdrant filter from optional metadata fields."""
    conditions = []
    if source_type:
        conditions.append(FieldCondition(key="source_type", match=MatchValue(value=source_type)))
    if project:
        conditions.append(FieldCondition(key="project", match=MatchValue(value=project)))
    if principal:
        conditions.append(FieldCondition(key="principal", match=MatchValue(value=principal)))
    if not conditions:
        return None
    return Filter(must=conditions)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search(
    query: str,
    limit: int = 5,
    source_type: str = "",
    project: str = "",
    principal: str = "",
) -> str:
    """Search Exocortex memory by semantic similarity.

    Args:
        query: Natural language search query.
        limit: Max results to return (default 5, max 20).
        source_type: Filter by source type (e.g. 'session_log', 'steve_gate_event', 'watercooler').
        project: Filter by project (e.g. 'MoCoP').
        principal: Filter by AI principal (e.g. 'purple', 'techno-monk').

    Returns:
        JSON array of matching memory entries with scores.
    """
    limit = min(max(limit, 1), 20)
    vector = _embed(query)
    response = QDRANT.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=_build_filter(source_type, project, principal),
        limit=limit,
        with_payload=True,
    )
    entries = [_format_point(r) for r in response.points]
    return json.dumps(entries, indent=2, ensure_ascii=False)


@mcp.tool()
def status() -> str:
    """Get Exocortex collection status — point count, segments, disk size.

    Returns:
        JSON object with collection statistics.
    """
    info = QDRANT.get_collection(COLLECTION)
    return json.dumps({
        "collection": COLLECTION,
        "points_count": info.points_count,
        "indexed_vectors_count": info.indexed_vectors_count,
        "segments_count": info.segments_count,
        "status": str(info.status),
    }, indent=2)


@mcp.tool()
def recent(
    limit: int = 10,
    source_type: str = "",
    project: str = "",
    principal: str = "",
) -> str:
    """Get the most recent Exocortex entries by timestamp.

    Args:
        limit: Max results (default 10, max 50).
        source_type: Filter by source type.
        project: Filter by project.
        principal: Filter by AI principal.

    Returns:
        JSON array of recent entries, newest first.
    """
    limit = min(max(limit, 1), 50)
    # Scroll with filter, then sort client-side by timestamp
    results, _ = QDRANT.scroll(
        collection_name=COLLECTION,
        scroll_filter=_build_filter(source_type, project, principal),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    entries = []
    for point in results:
        payload = point.payload or {}
        entries.append({
            "id": str(point.id),
            "score": None,
            "content": payload.get("content", payload.get("text", "")),
            "source_type": payload.get("source_type", "unknown"),
            "project": payload.get("project", ""),
            "principal": payload.get("principal", ""),
            "timestamp": payload.get("timestamp", payload.get("created_at", "")),
            "session": payload.get("session", ""),
            "tags": payload.get("tags", []),
            "decision": payload.get("decision", ""),
        })

    # Sort by timestamp descending (best effort — some entries may lack timestamps)
    entries.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    return json.dumps(entries[:limit], indent=2, ensure_ascii=False)


@mcp.tool()
def search_clusters(
    query: str,
    limit: int = 5,
    project: str = "",
    principal: str = "",
) -> str:
    """Search macro_memory clusters by semantic similarity.

    Returns cluster summaries — recurring themes and narrative arcs built by
    HDBSCAN over episodic memories. Each cluster has a centroid, member count,
    time span, and topic keywords.

    Args:
        query: Natural language search query.
        limit: Max clusters to return (default 5, max 20).
        project: Filter by project.
        principal: Filter by principal.

    Returns:
        JSON array of matching cluster objects with scores.
    """
    limit = min(max(limit, 1), 20)
    vector = _embed(query)

    conditions = []
    conditions.append(FieldCondition(key="source_type", match=MatchValue(value="macro_memory")))
    if project:
        conditions.append(FieldCondition(key="project", match=MatchValue(value=project)))
    if principal:
        conditions.append(FieldCondition(key="principal", match=MatchValue(value=principal)))

    cluster_filter = Filter(must=conditions)

    response = QDRANT.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=cluster_filter,
        limit=limit,
        with_payload=True,
    )

    entries = []
    for r in response.points:
        payload = r.payload or {}
        entries.append({
            "id": str(r.id),
            "score": round(r.score, 4) if r.score is not None else None,
            "cluster_id": payload.get("cluster_id"),
            "member_count": payload.get("member_count", 0),
            "centroid_text": payload.get("content", ""),
            "topic_keywords": payload.get("topic_keywords", []),
            "time_earliest": payload.get("time_earliest", ""),
            "time_latest": payload.get("time_latest", ""),
            "source_type_distribution": payload.get("source_type_distribution", {}),
            "scope": payload.get("scope", ""),
        })
    return json.dumps(entries, indent=2, ensure_ascii=False)


@mcp.tool()
def search_with_clusters(
    query: str,
    limit: int = 5,
    cluster_limit: int = 2,
    source_type: str = "",
    project: str = "",
    principal: str = "",
) -> str:
    """Search fragments AND clusters together — the full memory picture.

    Returns episodic fragments (specific memories) plus any matching cluster
    summaries (recurring themes / arcs). This is the cluster-augmented retrieval
    mode: you get both the specific detail and the broader context.

    Args:
        query: Natural language search query.
        limit: Max fragment results (default 5, max 20).
        cluster_limit: Max cluster results (default 2, max 10).
        source_type: Filter fragments by source type.
        project: Filter by project.
        principal: Filter by principal.

    Returns:
        JSON object with 'fragments' and 'clusters' arrays.
    """
    limit = min(max(limit, 1), 20)
    cluster_limit = min(max(cluster_limit, 1), 10)
    vector = _embed(query)

    # Fragments: exclude macro_memory
    frag_conditions = []
    if source_type:
        frag_conditions.append(FieldCondition(key="source_type", match=MatchValue(value=source_type)))
    if project:
        frag_conditions.append(FieldCondition(key="project", match=MatchValue(value=project)))
    if principal:
        frag_conditions.append(FieldCondition(key="principal", match=MatchValue(value=principal)))
    frag_must_not = [FieldCondition(key="source_type", match=MatchValue(value="macro_memory"))]

    frag_filter = Filter(
        must=frag_conditions if frag_conditions else None,
        must_not=frag_must_not,
    )

    frag_response = QDRANT.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=frag_filter,
        limit=limit,
        with_payload=True,
    )
    fragments = [_format_point(r) for r in frag_response.points]

    # Clusters
    cluster_conditions = [FieldCondition(key="source_type", match=MatchValue(value="macro_memory"))]
    if project:
        cluster_conditions.append(FieldCondition(key="project", match=MatchValue(value=project)))
    if principal:
        cluster_conditions.append(FieldCondition(key="principal", match=MatchValue(value=principal)))

    cluster_response = QDRANT.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=Filter(must=cluster_conditions),
        limit=cluster_limit,
        with_payload=True,
    )

    clusters = []
    for r in cluster_response.points:
        payload = r.payload or {}
        clusters.append({
            "id": str(r.id),
            "score": round(r.score, 4) if r.score is not None else None,
            "cluster_id": payload.get("cluster_id"),
            "member_count": payload.get("member_count", 0),
            "centroid_text": payload.get("content", ""),
            "topic_keywords": payload.get("topic_keywords", []),
            "time_earliest": payload.get("time_earliest", ""),
            "time_latest": payload.get("time_latest", ""),
        })

    return json.dumps({
        "fragments": fragments,
        "clusters": clusters,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
def get_point(point_id: str) -> str:
    """Fetch a specific Exocortex point by ID.

    Args:
        point_id: The Qdrant point ID (numeric string).

    Returns:
        JSON object with the full point payload.
    """
    try:
        points = QDRANT.retrieve(
            collection_name=COLLECTION,
            ids=[int(point_id)],
            with_payload=True,
            with_vectors=False,
        )
    except (ValueError, TypeError):
        return json.dumps({"error": f"Invalid point ID: {point_id}"})

    if not points:
        return json.dumps({"error": f"Point {point_id} not found"})

    point = points[0]
    payload = point.payload or {}
    return json.dumps({
        "id": str(point.id),
        "payload": payload,
    }, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global QDRANT, EMBEDDER, COLLECTION

    parser = argparse.ArgumentParser(description="Exocortex MCP Server")
    parser.add_argument("--qdrant-url", default="http://192.168.2.191:6333", help="Qdrant REST URL")
    parser.add_argument("--collection", default="exocortex", help="Qdrant collection name")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="Sentence-transformers model for embeddings")
    args = parser.parse_args()

    COLLECTION = args.collection

    logger.info("Connecting to Qdrant at %s (collection: %s)", args.qdrant_url, COLLECTION)
    QDRANT = QdrantClient(url=args.qdrant_url, timeout=10)

    logger.info("Loading embedding model: %s", args.model)
    EMBEDDER = SentenceTransformer(args.model)
    logger.info("Exocortex MCP server ready.")

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
