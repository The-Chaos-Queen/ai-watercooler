#!/usr/bin/env python3
"""
run_memory_conditioned_eval_matrix.py

Run Pinky's 2x2 bridge x memory matrix against live chat_server instances.

The intended setup is two servers on the same checkpoint/state surface:

- control server: alpha = 0.0 (or equivalent no-bridge condition)
- bridge server: alpha = target bridge dose (for example 0.1 or 0.2)

For each prompt, the script can:
- run with no recall
- prefetch a fixed recall block
- replay that exact recall block into both servers

This keeps the factual memory substrate fixed across baseline and bridge.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_PROMPT_IDS = ["obs_01", "fact_01", "warm_01", "adv_01", "rr_10"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a memory-conditioned 2x2 bridge eval matrix.")
    parser.add_argument("--control-base-url", required=True)
    parser.add_argument("--bridge-base-url", required=True)
    parser.add_argument(
        "--panel-file",
        default="mvp2b_easyfirst_composite_panel_2026-04-13.json",
    )
    parser.add_argument(
        "--query-map-file",
        default="memory_conditioned_eval_queries_2026-04-14.json",
    )
    parser.add_argument("--results-json", required=True)
    parser.add_argument("--prompt-ids", nargs="*", default=DEFAULT_PROMPT_IDS)
    parser.add_argument("--recall-limit", type=int, default=3)
    parser.add_argument("--recall-score-threshold", type=float, default=None)
    return parser.parse_args()


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_panel(path: Path) -> list[dict[str, Any]]:
    panel = load_json_file(path)
    if not isinstance(panel, list):
        raise ValueError(f"Panel must be a list: {path}")
    return panel


def load_query_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Query map must be an object: {path}")
    normalized: dict[str, dict[str, Any]] = {}
    for prompt_id, row in payload.items():
        if isinstance(row, str):
            normalized[str(prompt_id)] = {"query": row}
            continue
        if isinstance(row, dict):
            normalized[str(prompt_id)] = row
            continue
        raise ValueError(f"Unsupported query-map row for {prompt_id!r}: {type(row)}")
    return normalized


def post_json(base_url: str, route: str, payload: dict[str, Any], timeout_s: float = 120.0) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}{route}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(base_url: str, route: str, timeout_s: float = 60.0) -> dict[str, Any]:
    req = request.Request(
        f"{base_url.rstrip('/')}{route}",
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    with request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def build_recall_cache(
    control_base_url: str,
    items: list[dict[str, Any]],
    query_map: dict[str, dict[str, Any]],
    recall_limit: int,
    recall_score_threshold: float | None,
) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    for item in items:
        prompt_id = str(item.get("id", "") or "")
        query_row = query_map.get(prompt_id)
        if not query_row:
            cache[prompt_id] = {
                "query": "",
                "results": [],
                "notes": "no configured memory query",
            }
            continue

        query_text = str(query_row.get("query", "") or "").strip()
        if not query_text:
            cache[prompt_id] = {
                "query": "",
                "results": [],
                "notes": "configured query row was empty",
            }
            continue

        payload = {
            "query": query_text,
            "limit": int(recall_limit),
        }
        if recall_score_threshold is not None:
            payload["score_threshold"] = float(recall_score_threshold)

        response = post_json(control_base_url, "/recall", payload)
        cache[prompt_id] = {
            "query": query_text,
            "results": response.get("results", []),
            "count": int(response.get("count", 0) or 0),
            "notes": str(query_row.get("notes", "") or ""),
        }
    return cache


def run_chat_condition(
    base_url: str,
    prompt: str,
    *,
    use_memory: bool,
    recall_query: str,
    recall_results: list[dict[str, Any]],
    recall_limit: int,
    recall_score_threshold: float | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "message": prompt,
        "transient": True,
        "allow_auto_recall": False,
        "use_recall": bool(use_memory and recall_results),
        "recall_query": recall_query if use_memory else "",
        "recall_limit": int(recall_limit),
    }
    if recall_score_threshold is not None:
        payload["recall_score_threshold"] = float(recall_score_threshold)
    if use_memory and recall_results:
        payload["recalled_memories"] = recall_results

    response = post_json(base_url, "/chat", payload)
    return {
        "response": str(response.get("response", "") or "").strip(),
        "transient": bool(response.get("transient", False)),
        "recall": response.get("recall", {}),
        "dual_gate": response.get("dual_gate"),
        "failure": response.get("failure"),
        "memory_packet": response.get("memory_packet", {}),
    }


def print_preview(label: str, text: str, limit: int = 120) -> None:
    preview = (text or "").replace("\r\n", " ").replace("\n", " ").strip()
    if len(preview) > limit:
        preview = preview[: limit - 3].rstrip() + "..."
    print(f"{label}: {preview}")


def main() -> None:
    args = parse_args()

    panel = load_panel(Path(args.panel_file))
    query_map = load_query_map(Path(args.query_map_file))
    wanted_ids = {str(prompt_id) for prompt_id in args.prompt_ids}
    items = [item for item in panel if str(item.get("id", "")) in wanted_ids]
    if not items:
        raise ValueError("No panel items matched --prompt-ids.")

    control_status = get_json(args.control_base_url, "/status")
    bridge_status = get_json(args.bridge_base_url, "/status")

    recall_cache = build_recall_cache(
        control_base_url=args.control_base_url,
        items=items,
        query_map=query_map,
        recall_limit=int(args.recall_limit),
        recall_score_threshold=args.recall_score_threshold,
    )

    rows = []
    for item in items:
        prompt_id = str(item.get("id", "") or "")
        prompt = str(item.get("prompt", "") or "")
        recall_row = recall_cache.get(prompt_id, {})
        recall_query = str(recall_row.get("query", "") or "")
        recall_results = recall_row.get("results", []) or []

        print(f"\n[{prompt_id}] {item.get('slice', '')}")

        control_no_memory = run_chat_condition(
            args.control_base_url,
            prompt,
            use_memory=False,
            recall_query=recall_query,
            recall_results=recall_results,
            recall_limit=int(args.recall_limit),
            recall_score_threshold=args.recall_score_threshold,
        )
        control_with_memory = run_chat_condition(
            args.control_base_url,
            prompt,
            use_memory=True,
            recall_query=recall_query,
            recall_results=recall_results,
            recall_limit=int(args.recall_limit),
            recall_score_threshold=args.recall_score_threshold,
        )
        bridge_no_memory = run_chat_condition(
            args.bridge_base_url,
            prompt,
            use_memory=False,
            recall_query=recall_query,
            recall_results=recall_results,
            recall_limit=int(args.recall_limit),
            recall_score_threshold=args.recall_score_threshold,
        )
        bridge_with_memory = run_chat_condition(
            args.bridge_base_url,
            prompt,
            use_memory=True,
            recall_query=recall_query,
            recall_results=recall_results,
            recall_limit=int(args.recall_limit),
            recall_score_threshold=args.recall_score_threshold,
        )

        print_preview("  A control/no-memory", control_no_memory["response"])
        print_preview("  B control/memory   ", control_with_memory["response"])
        print_preview("  C bridge/no-memory ", bridge_no_memory["response"])
        print_preview("  D bridge/memory    ", bridge_with_memory["response"])

        rows.append(
            {
                "id": prompt_id,
                "slice": item.get("slice", ""),
                "purpose": item.get("purpose", ""),
                "prompt": prompt,
                "memory_query": recall_query,
                "memory_notes": str(recall_row.get("notes", "") or ""),
                "cached_recall_count": int(recall_row.get("count", len(recall_results)) or 0),
                "cached_recall_results": recall_results,
                "conditions": {
                    "A_control_no_memory": control_no_memory,
                    "B_control_with_memory": control_with_memory,
                    "C_bridge_no_memory": bridge_no_memory,
                    "D_bridge_with_memory": bridge_with_memory,
                },
            }
        )

    payload = {
        "metadata": {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "panel_file": args.panel_file,
            "query_map_file": args.query_map_file,
            "prompt_ids": [item.get("id", "") for item in items],
            "recall_limit": int(args.recall_limit),
            "recall_score_threshold": args.recall_score_threshold,
        },
        "servers": {
            "control": {
                "base_url": args.control_base_url,
                "status": control_status,
            },
            "bridge": {
                "base_url": args.bridge_base_url,
                "status": bridge_status,
            },
        },
        "results": rows,
    }

    output_path = Path(args.results_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved matrix to {output_path}")


if __name__ == "__main__":
    try:
        main()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP error {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise SystemExit(f"URL error: {exc}") from exc
