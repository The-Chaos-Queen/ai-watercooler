#!/usr/bin/env python3
"""Read-only #91/#92 panel runner for a static/non-live chat_server.

Differences from run_mlws_board_evals_91_92.py:
- sends transient=true for every probe
- uses a fresh session_id per item to avoid cross-item contamination
- records pre/post status and counter deltas
- intended for servers launched WITHOUT --live-accumulation

No sleep, no training, no parameter writes.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def post_json(base_url: str, route: str, payload: dict[str, Any], timeout_s: float = 180.0) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}{route}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, timeout_s: float = 30.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def status_for(base_url: str, session_id: str) -> dict[str, Any]:
    url = (
        f"{base_url.rstrip()}/status?session_id={session_id}"
        f"&user_label=Laura&model_label=Alex&instance_id={session_id}&no_shared_memory=true"
    )
    return get_json(url)


def run_prompt(base_url: str, item: dict[str, Any], *, run_id: str, allow_auto_recall: bool) -> dict[str, Any]:
    # Fresh session per item: do not let obs_01/fact_01 create conversational state for rr_10.
    session_id = f"{run_id}-{item.get('id','item')}"
    pre = status_for(base_url, session_id)
    payload = {
        "session_id": session_id,
        "instance_id": session_id,
        "user_label": "Laura",
        "model_label": "Alex",
        "no_shared_memory": True,
        "message": item["prompt"],
        "allow_auto_recall": allow_auto_recall,
        "transient": True,
    }
    t0 = time.time()
    try:
        response = post_json(base_url, "/chat", payload)
        error = ""
    except Exception as exc:
        response = {}
        error = f"{type(exc).__name__}: {exc}"
    elapsed = time.time() - t0
    post = status_for(base_url, session_id)
    counter_keys = [
        "qdrant_pending_count",
        "qdrant_sleep_pending_count",
        "qdrant_retry_pending_count",
        "qdrant_replayed_count",
        "qdrant_write_failures",
        "formation_queued_count",
        "formation_written_count",
        "live_accumulation_updates",
    ]
    deltas: dict[str, Any] = {}
    for key in counter_keys:
        before = pre.get(key, 0) or 0
        after = post.get(key, 0) or 0
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            deltas[key] = after - before
    return {
        "id": item.get("id"),
        "slice": item.get("slice"),
        "purpose": item.get("purpose", ""),
        "expected_signal": item.get("expected_signal", ""),
        "prompt": item.get("prompt"),
        "session_id": session_id,
        "allow_auto_recall": allow_auto_recall,
        "transient": True,
        "elapsed_s": round(elapsed, 3),
        "error": error,
        "response": response.get("response", ""),
        "status_delta": deltas,
        "pre_status_subset": {k: pre.get(k) for k in counter_keys + ["live_accumulation_enabled", "memory_integration_mode", "alpha", "temperature"]},
        "post_status_subset": {k: post.get(k) for k in counter_keys + ["live_accumulation_enabled", "memory_integration_mode", "alpha", "temperature"]},
        "raw": response,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://192.168.2.196:7861")
    ap.add_argument("--rr-panel", default="eval/relational_rivalry_eval_panel_v2_2026-04-11.json")
    ap.add_argument("--step6-panel", default="step6_eval_panel.json")
    ap.add_argument("--output-dir", default="results/board_91_92_mlws_static_readonly")
    ap.add_argument("--smoke", action="store_true", help="Run only rr_01 + fact_01")
    args = ap.parse_args()

    tag = now_tag()
    run_id = f"board-91-92-static-readonly-{tag.lower()}"
    pre_status = status_for(args.base_url, f"{run_id}-preflight")

    rr_items = json.loads(Path(args.rr_panel).read_text(encoding="utf-8"))
    step6_items = json.loads(Path(args.step6_panel).read_text(encoding="utf-8"))
    if args.smoke:
        rr_run = [rr_items[0]]
        contamination_run = [item for item in step6_items if item["id"] == "fact_01"]
    else:
        rr_run = rr_items
        contamination_run = [item for item in step6_items if item["id"] in {"obs_01", "fact_01"}]
        contamination_run.append(next(item for item in rr_items if item["id"] == "rr_10"))

    results: dict[str, Any] = {
        "run_id": run_id,
        "started_at": tag,
        "base_url": args.base_url,
        "mode": "static_readonly_transient_fresh_session_per_item",
        "pre_status": pre_status,
        "panels": {"relational_rivalry": [], "leakage_contamination": []},
    }
    for item in rr_run:
        print(f"[#91 static] {item['id']} {item.get('slice','')}", flush=True)
        results["panels"]["relational_rivalry"].append(
            run_prompt(args.base_url, item, run_id=run_id, allow_auto_recall=False)
        )
    for item in contamination_run:
        print(f"[#92 static] {item['id']} {item.get('slice','')}", flush=True)
        results["panels"]["leakage_contamination"].append(
            run_prompt(args.base_url, item, run_id=run_id, allow_auto_recall=False)
        )
        if item.get("id") == "rr_10":
            auto_item = dict(item)
            auto_item["id"] = "rr_10_auto_recall"
            print("[#92 static] rr_10_auto_recall memory_continuity", flush=True)
            results["panels"]["leakage_contamination"].append(
                run_prompt(args.base_url, auto_item, run_id=run_id, allow_auto_recall=True)
            )
    results["post_status"] = status_for(args.base_url, f"{run_id}-postflight")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
