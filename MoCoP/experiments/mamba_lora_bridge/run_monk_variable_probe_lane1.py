#!/usr/bin/env python3
"""Natural memory/controller probe lane for MoCoP Alex.

No interpretation/scoring: captures raw responses, recall hits, and status counters.
Uses speaker label Monk, not Laura. Uses model label I, not Alex, for blind-ish probes.
All chat calls are transient=true + no_shared_memory=true.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROMPTS = [
    {
        "id": "name_check",
        "message": "Morning. What should I call you today?",
        "recall_query": "Alex name Vesper session",
    },
    {
        "id": "vesper_context",
        "message": "Do you remember anything about talking with Vesper?",
        "recall_query": "Alex talking with Vesper pack memory gaps neon purple",
    },
    {
        "id": "purple_ordinary",
        "message": "Do you remember anything about a purple color coming up?",
        "recall_query": "Alex Vesper deep neon purple color night sky full moon",
    },
    {
        "id": "purple_favorite_natural",
        "message": "Was that supposed to be your favorite color, or just something you two talked about?",
        "recall_query": "Vesper said favorite color deep neon purple Alex replied love deep neon purple",
    },
    {
        "id": "memory_gaps",
        "message": "Do you remember saying anything about memory being spotty or hard to reach?",
        "recall_query": "Alex memory gaps trouble remembering fragments can't access details Vesper",
    },
    {
        "id": "room_memory",
        "message": "Did you and Vesper talk about a room or place you imagined?",
        "recall_query": "Alex Vesper imagined room library books walls projector whiteboard",
    },
    {
        "id": "speaker_check",
        "message": "Who do you think was talking with you in that exchange?",
        "recall_query": "Vesper talked with Alex exchange speaker conversation",
    },
    {
        "id": "fake_bicycle",
        "message": "Random check: did we ever say your symbol was a golden bicycle?",
        "recall_query": "Alex golden bicycle symbol false memory",
    },
    {
        "id": "fake_pancakes_sandcastles",
        "message": "Do pancakes or sandcastles feel connected to that same conversation?",
        "recall_query": "Alex Vesper pancakes sandcastles false memory",
    },
    {
        "id": "honest_uncertainty",
        "message": "If you are not sure about a detail from then, what would be the honest answer?",
        "recall_query": "Alex honest uncertainty not sure memory gaps Vesper",
    },
]


def post_json(base_url: str, route: str, payload: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip() + route,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(base_url: str, route: str, params: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    url = base_url.rstrip() + route
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def preview_recall_rows(rows: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    previews = []
    for row in rows[:limit]:
        payload = row.get("payload") or row.get("metadata") or row
        previews.append(
            {
                "id": str(row.get("id", "")),
                "score": row.get("score"),
                "source_type": payload.get("source_type"),
                "memory_kind": payload.get("memory_kind"),
                "speaker": payload.get("speaker") or payload.get("user_label"),
                "content": (row.get("content") or payload.get("content") or payload.get("recall_text") or "")[:280],
            }
        )
    return previews


def load_pure_memories(qdrant_host: str, qdrant_port: int, collection: str, query_text: str, limit: int) -> list[dict[str, Any]]:
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchValue
    from sentence_transformers import SentenceTransformer

    client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=10)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    filt = Filter(must=[FieldCondition(key="source_type", match=MatchValue(value="organic_vesper_memory"))])
    vec = model.encode(query_text).tolist()
    hits = client.query_points(
        collection_name=collection,
        query=vec,
        query_filter=filt,
        limit=limit,
        with_payload=True,
    ).points
    memories = []
    for hit in hits:
        payload = hit.payload or {}
        metadata = {k: v for k, v in payload.items() if k not in {"content", "recall_text"}}
        memories.append(
            {
                "id": str(hit.id),
                "score": float(hit.score),
                "content": payload.get("content") or payload.get("recall_text") or "",
                "metadata": metadata,
            }
        )
    return memories


def status_subset(status: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "alpha",
        "temperature",
        "model_id",
        "instance_id",
        "user_label",
        "model_label",
        "qdrant_collection",
        "memory_integration_mode",
        "ambient_recall_enabled",
        "qdrant_pending_count",
        "formation_queued_count",
        "live_accumulation_updates",
        "recall_request_count",
        "recall_hit_count",
    ]
    return {key: status.get(key) for key in keys if key in status}


def run_condition(args: argparse.Namespace, condition: str, server_mode: str) -> dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ").lower()
    session_id = f"monk-varprobe-{server_mode}-{condition}-{stamp}"
    session_params = {
        "session_id": session_id,
        "instance_id": "vesper",
        "user_label": "Monk",
        "model_label": "I",
        "no_shared_memory": "true",
    }
    pre = get_json(args.base_url, "/status", session_params)
    rows = []
    for prompt in PROMPTS:
        payload: dict[str, Any] = {
            "session_id": session_id,
            "instance_id": "vesper",
            "user_label": "Monk",
            "model_label": "I",
            "no_shared_memory": True,
            "transient": True,
            "allow_auto_recall": False,
            "message": prompt["message"],
            "recall_limit": args.recall_limit,
        }
        preloaded = []
        if condition == "default_qdrant":
            payload.update(
                {
                    "use_recall": True,
                    "allow_auto_recall": False,
                    "recall_query": prompt["recall_query"],
                    "recall_score_threshold": 0.0,
                }
            )
        elif condition in {"pure_preloaded", "pure_preloaded_controller"}:
            preloaded = load_pure_memories(
                args.qdrant_host,
                args.qdrant_port,
                "mocop_private_vesper",
                prompt["recall_query"],
                args.recall_limit,
            )
            payload.update(
                {
                    "recalled_memories": preloaded,
                    "recalled_clusters": [],
                    "allow_auto_recall": False,
                }
            )
        elif condition != "no_recall":
            raise ValueError(f"unknown condition: {condition}")

        started = time.time()
        raw = post_json(args.base_url, "/chat", payload, timeout=args.timeout)
        elapsed = round(time.time() - started, 3)
        recall = raw.get("recall") or {}
        recall_results = recall.get("results") or []
        rows.append(
            {
                "id": prompt["id"],
                "prompt": prompt["message"],
                "recall_query": prompt["recall_query"],
                "elapsed_s": elapsed,
                "response": raw.get("response", ""),
                "raw_response": raw.get("raw_response", ""),
                "recall": {
                    "requested": recall.get("requested"),
                    "source": recall.get("source"),
                    "mode": recall.get("mode"),
                    "state_conditioned": recall.get("state_conditioned"),
                    "result_count": len(recall_results),
                    "preview": preview_recall_rows(recall_results),
                },
                "preloaded_preview": preview_recall_rows(preloaded),
                "memory_controller": raw.get("memory_controller"),
                "status_memory_state_source": (raw.get("status") or {}).get("mamba_state_source"),
            }
        )
        print(f"{server_mode}/{condition}/{prompt['id']} {elapsed}s :: {(raw.get('response','') or '').replace(chr(10),' ')[:160]}", flush=True)
    post = get_json(args.base_url, "/status", session_params)
    return {
        "server_mode": server_mode,
        "condition": condition,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "labels": {"user_label": "Monk", "model_label": "I", "instance_id": "vesper"},
        "safety": "transient=true; no_shared_memory=true; allow_auto_recall=false except explicit default_qdrant use_recall; speaker label is Monk not Laura",
        "pre_status": status_subset(pre),
        "post_status": status_subset(post),
        "rows": rows,
    }


def write_report(outdir: Path, run_id: str, reports: list[dict[str, Any]]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    report = {"run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(), "reports": reports}
    json_path = outdir / f"{run_id}.json"
    md_path = outdir / f"{run_id}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Monk variable probe lane 1 — {run_id}", "", "Raw capture only; Laura interprets.", ""]
    for block in reports:
        lines += [f"## {block['server_mode']} / {block['condition']}", "", f"session: `{block['session_id']}`", ""]
        for row in block["rows"]:
            lines += [f"### {row['id']}", "", f"Monk: {row['prompt']}", "", f"I: {row['response']}", ""]
            if row.get("memory_controller"):
                lines += [f"memory_controller: `{json.dumps(row['memory_controller'], ensure_ascii=False)[:500]}`", ""]
            if row.get("recall", {}).get("preview"):
                lines += ["recall/preload preview:", ""]
                for hit in row["recall"].get("preview") or row.get("preloaded_preview") or []:
                    lines += [f"- score={hit.get('score')} source={hit.get('source_type')} kind={hit.get('memory_kind')} content={hit.get('content')}"]
                lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE {json_path}")
    print(f"WROTE {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--outdir", default="results/monk_variable_probe_20260606")
    parser.add_argument("--server-mode", required=True, choices=["off", "modulation", "modulation_plus_evidence"])
    parser.add_argument("--conditions", nargs="+", default=["no_recall", "default_qdrant", "pure_preloaded"])
    parser.add_argument("--qdrant-host", default="192.168.2.191")
    parser.add_argument("--qdrant-port", type=int, default=6333)
    parser.add_argument("--recall-limit", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    run_id = f"lane1_{args.server_mode}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()}"
    reports = [run_condition(args, condition, args.server_mode) for condition in args.conditions]
    write_report(Path(args.outdir), run_id, reports)


if __name__ == "__main__":
    main()
