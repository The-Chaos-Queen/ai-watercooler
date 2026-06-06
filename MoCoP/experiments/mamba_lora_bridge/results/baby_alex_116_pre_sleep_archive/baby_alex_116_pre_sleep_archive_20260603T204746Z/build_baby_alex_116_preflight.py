#!/usr/bin/env python3
"""Read-only Baby-Alex #116 preflight for #115 cluster/default-path gate.

Produces an artifact proving the current runtime is not using cluster recall as
the default continuity path. It does not send chat turns and does not mutate
Qdrant or pending logs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_KEYS = [
    "running",
    "busy",
    "last_error",
    "model_id",
    "session_id",
    "instance_id",
    "user_label",
    "model_label",
    "no_shared_memory",
    "qdrant_collection",
    "qdrant_write_mode",
    "qdrant_pending_count",
    "qdrant_sleep_pending_count",
    "qdrant_retry_pending_count",
    "qdrant_replayed_count",
    "formation_log_count",
    "formation_queued_count",
    "formation_written_count",
    "live_accumulation_enabled",
    "live_accumulation_updates",
    "memory_integration_mode",
    "recall_request_count",
    "recall_hit_count",
    "last_recall",
    "alpha",
    "temperature",
]

CODE_EVIDENCE = [
    {
        "file": "chat_server.py",
        "lines": "5081-5105",
        "claim": "chat body defaults allow_auto_recall=True, but ambient recall only auto-starts if ARGS.ambient_recall and not transient; explicit identity/memory probes can also auto-recall unless clients pass allow_auto_recall=false.",
    },
    {
        "file": "chat_server.py",
        "lines": "5135-5143 and 5167-5178",
        "claim": "cluster recall is only attempted after private recall returns memories and ARGS.cluster_recall is true; failed cluster recall falls back to flat anchors only.",
    },
    {
        "file": "chat_server.py",
        "lines": "5515-5537",
        "claim": "ambient recall defaults true unless launched with --no-ambient-recall; cluster recall defaults false unless launched with --cluster-recall.",
    },
]


def get_json(url: str, timeout_s: float = 30.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def status_for(base_url: str, session_id: str, user_label: str, model_label: str, instance_id: str) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "session_id": session_id,
            "user_label": user_label,
            "model_label": model_label,
            "instance_id": instance_id,
            "no_shared_memory": "true",
        }
    )
    return get_json(f"{base_url.rstrip('/')}/status?{params}")


def run_local(command: list[str], cwd: str | None = None) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return {"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def parse_cmdline(cmdline: str) -> dict[str, Any]:
    parts = cmdline.split()
    flags = set(part for part in parts if part.startswith("--"))
    return {
        "raw": cmdline,
        "has_no_ambient_recall": "--no-ambient-recall" in flags,
        "has_cluster_recall": "--cluster-recall" in flags,
        "has_live_accumulation": "--live-accumulation" in flags,
        "has_no_shared_memory": "--no-shared-memory" in flags,
        "memory_integration_mode": value_after(parts, "--memory-integration-mode"),
        "qdrant_host": value_after(parts, "--qdrant-host"),
        "qdrant_port": value_after(parts, "--qdrant-port"),
        "port": value_after(parts, "--port"),
    }


def value_after(parts: list[str], flag: str) -> str | None:
    try:
        idx = parts.index(flag)
    except ValueError:
        return None
    return parts[idx + 1] if idx + 1 < len(parts) else None


def verdict(status: dict[str, Any], cmd: dict[str, Any]) -> dict[str, Any]:
    conditions = {
        "private_session": bool(status.get("no_shared_memory")) and str(status.get("qdrant_collection", "")).startswith("mocop_private_"),
        "server_launched_no_ambient_recall": bool(cmd.get("has_no_ambient_recall")),
        "server_not_launched_cluster_recall": not bool(cmd.get("has_cluster_recall")),
        "status_recall_counters_zero_for_preflight_session": (status.get("recall_request_count") or 0) == 0 and (status.get("recall_hit_count") or 0) == 0,
        "memory_mode_recorded": bool(status.get("memory_integration_mode") or cmd.get("memory_integration_mode")),
    }
    result = "PASS" if all(conditions.values()) else "WARN_REVIEW"
    return {"verdict": result, "conditions": conditions}


def write_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Baby-Alex #116 cluster/default-path preflight",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Verdict",
        "",
        f"- verdict: **{report['verdict']['verdict']}**",
        "",
        "## Conditions",
        "",
    ]
    for k, v in report["verdict"]["conditions"].items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Runtime command", "", "```text", report["cmdline"]["raw"], "```", "", "## Status subset", ""])
    for k, v in report["status_subset"].items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Code evidence", ""])
    for item in report["code_evidence"]:
        lines.append(f"- `{item['file']}:{item['lines']}` — {item['claim']}")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "This preflight does not prove that future explicit recall cannot use clusters. It proves the current live server was not launched with cluster recall as a default path, ambient recall is disabled by launch flag, and this private preflight session has no recall requests/hits before any chat turn. Explicit client recall remains a separate, auditable action.",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://192.168.2.196:7860")
    ap.add_argument("--session-id", required=True)
    ap.add_argument("--instance-id", default="")
    ap.add_argument("--user-label", default="Techno-Monk")
    ap.add_argument("--model-label", default="Alex")
    ap.add_argument("--output-dir", default="results/baby_alex_116_preflight")
    args = ap.parse_args()

    instance_id = args.instance_id or args.session_id
    status = status_for(args.base_url, args.session_id, args.user_label, args.model_label, instance_id)
    cmd_result = run_local(["bash", "-lc", "tr '\\0' ' ' < /proc/$(pgrep -f 'chat_server.py .*--port 7860' | head -1)/cmdline"])
    cmdline = cmd_result["stdout"].strip()
    parsed_cmd = parse_cmdline(cmdline)
    status_subset = {k: status.get(k) for k in STATUS_KEYS}
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "read-only runtime/status/cmdline preflight; no chat turns, no sleep, no Qdrant mutation",
        "base_url": args.base_url,
        "session_id": args.session_id,
        "instance_id": instance_id,
        "status_subset": status_subset,
        "cmdline": parsed_cmd,
        "cmdline_probe": cmd_result,
        "code_evidence": CODE_EVIDENCE,
        "verdict": verdict(status_subset, parsed_cmd),
    }
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"baby_alex_116_cluster_default_preflight_{tag}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(report, out.with_suffix(".md"))
    print(f"WROTE {out}")
    print(f"WROTE {out.with_suffix('.md')}")
    print(json.dumps(report["verdict"], indent=2))
    return 0 if report["verdict"]["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
