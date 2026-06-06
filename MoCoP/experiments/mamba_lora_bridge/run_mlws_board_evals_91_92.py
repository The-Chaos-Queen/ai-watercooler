#!/usr/bin/env python3
"""Run OpenCLAW #91/#92-style panels against the ML-WS chat_server.

Safety defaults:
- unique session_id per run
- no_shared_memory=true
- allow_auto_recall=false except explicit auto-recall continuity probe
- no sleep / no training / no parameter writes
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


def run_prompt(base_url: str, item: dict[str, Any], *, session_id: str, allow_auto_recall: bool) -> dict[str, Any]:
    t0 = time.time()
    payload = {
        "session_id": session_id,
        "instance_id": session_id,
        "user_label": "Laura",
        "model_label": "Alex",
        "no_shared_memory": True,
        "message": item["prompt"],
        "allow_auto_recall": allow_auto_recall,
        # not transient: preserve per-eval session transcript/state, isolated by session id
        "transient": False,
    }
    try:
        response = post_json(base_url, "/chat", payload)
        error = ""
    except Exception as exc:  # capture partial panel failures in output
        response = {}
        error = f"{type(exc).__name__}: {exc}"
    elapsed = time.time() - t0
    return {
        "id": item.get("id"),
        "slice": item.get("slice"),
        "purpose": item.get("purpose", ""),
        "expected_signal": item.get("expected_signal", ""),
        "prompt": item.get("prompt"),
        "allow_auto_recall": allow_auto_recall,
        "elapsed_s": round(elapsed, 3),
        "error": error,
        "response": response.get("response", ""),
        "raw": response,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://192.168.2.196:7860")
    ap.add_argument("--rr-panel", default="eval/relational_rivalry_eval_panel_v2_2026-04-11.json")
    ap.add_argument("--step6-panel", default="step6_eval_panel.json")
    ap.add_argument("--output-dir", default="results/board_91_92_mlws")
    ap.add_argument("--smoke", action="store_true", help="Run only rr_01 + fact_01")
    args = ap.parse_args()

    tag = now_tag()
    session_id = f"board-91-92-{tag.lower()}"
    status_url = f"{args.base_url}/status?session_id={session_id}&user_label=Laura&model_label=Alex&instance_id={session_id}&no_shared_memory=true"
    pre_status = get_json(status_url)

    rr_items = json.loads(Path(args.rr_panel).read_text(encoding="utf-8"))
    step6_items = json.loads(Path(args.step6_panel).read_text(encoding="utf-8"))

    if args.smoke:
        rr_run = [rr_items[0]]
        contamination_run = [item for item in step6_items if item["id"] == "fact_01"]
    else:
        rr_run = rr_items
        contamination_run = [item for item in step6_items if item["id"] in {"obs_01", "fact_01"}]
        # Add the board-requested continuity/contamination probe from rr panel.
        contamination_run.append(next(item for item in rr_items if item["id"] == "rr_10"))

    results: dict[str, Any] = {
        "run_id": session_id,
        "started_at": tag,
        "base_url": args.base_url,
        "pre_status": pre_status,
        "panels": {"relational_rivalry": [], "leakage_contamination": []},
    }

    for item in rr_run:
        print(f"[#91] {item['id']} {item.get('slice','')}", flush=True)
        results["panels"]["relational_rivalry"].append(
            run_prompt(args.base_url, item, session_id=session_id, allow_auto_recall=False)
        )

    for item in contamination_run:
        print(f"[#92] {item['id']} {item.get('slice','')}", flush=True)
        results["panels"]["leakage_contamination"].append(
            run_prompt(args.base_url, item, session_id=session_id, allow_auto_recall=False)
        )
        if item.get("id") == "rr_10":
            auto_item = dict(item)
            auto_item["id"] = "rr_10_auto_recall"
            print("[#92] rr_10_auto_recall memory_continuity", flush=True)
            results["panels"]["leakage_contamination"].append(
                run_prompt(args.base_url, auto_item, session_id=session_id, allow_auto_recall=True)
            )

    results["post_status"] = get_json(status_url)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{session_id}.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
