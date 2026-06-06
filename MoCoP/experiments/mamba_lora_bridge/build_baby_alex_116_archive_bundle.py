#!/usr/bin/env python3
"""Create a read-only Baby-Alex #116 pre-sleep archive bundle.

Copies current runtime logs/state files into a timestamped bundle and writes a
manifest with hashes. This script does not flush pending rows, does not call
sleep/consolidation, and does not mutate Qdrant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_FILES = [
    "qdrant_gate_pending.jsonl",
    "qdrant_gate_flushed.jsonl",
    "private_recall_log.jsonl",
    "memory_formation_log.jsonl",
    "sleep_gate_events_latest.jsonl",
    "dual_gate_turns_latest.jsonl",
    "mamba_bootstrap_state_latest.pt",
    "BABY_ALEX_116_DRY_RUN_PROTOCOL_2026-05-28.md",
    "BABY_ALEX_116_WAKE_PROBE_PLAN.md",
    "run_baby_alex_wake_probe.py",
    "build_baby_alex_protected_set_audit.py",
    "build_baby_alex_116_preflight.py",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(command: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, check=False)
    return {"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


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


def copy_file(src: Path, dst_dir: Path) -> dict[str, Any]:
    rel_name = src.name
    dst = dst_dir / rel_name
    if not src.exists():
        return {"source": str(src), "copied": False, "reason": "missing"}
    if src.is_dir():
        return {"source": str(src), "copied": False, "reason": "directory_not_supported"}
    shutil.copy2(src, dst)
    return {
        "source": str(src),
        "bundle_path": str(dst),
        "copied": True,
        "bytes": dst.stat().st_size,
        "sha256": sha256(dst),
    }


def write_md(manifest: dict[str, Any], path: Path) -> None:
    lines = [
        "# Baby-Alex #116 pre-sleep archive bundle",
        "",
        f"Created: `{manifest['created_at']}`",
        "",
        "## Safety",
        "",
        "- Read-only copy/archive operation.",
        "- No sleep/consolidation/flush/rotation/model update was run.",
        "- Qdrant was not mutated by this script.",
        "",
        "## Summary",
        "",
    ]
    for k, v in manifest["summary"].items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Files", ""])
    for item in manifest["files"]:
        status = "copied" if item.get("copied") else f"missing/{item.get('reason')}"
        lines.append(f"- `{item['source']}` — {status}; bytes=`{item.get('bytes')}` sha256=`{item.get('sha256')}`")
    lines.extend(["", "## Runtime status subset", ""])
    for k, v in manifest["status"].items():
        lines.append(f"- {k}: `{v}`")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://192.168.2.196:7860")
    ap.add_argument("--session-id", required=True)
    ap.add_argument("--instance-id", default="")
    ap.add_argument("--user-label", default="Techno-Monk")
    ap.add_argument("--model-label", default="Alex")
    ap.add_argument("--output-root", default="results/baby_alex_116_pre_sleep_archive")
    ap.add_argument("--file", action="append", default=[], help="Additional file to include")
    args = ap.parse_args()

    cwd = Path.cwd()
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_dir = Path(args.output_root) / f"baby_alex_116_pre_sleep_archive_{tag}"
    bundle_dir.mkdir(parents=True, exist_ok=False)
    instance_id = args.instance_id or args.session_id

    status_raw = status_for(args.base_url, args.session_id, args.user_label, args.model_label, instance_id)
    status_keys = [
        "running", "busy", "last_error", "model_id", "session_id", "instance_id", "user_label", "model_label",
        "no_shared_memory", "qdrant_collection", "qdrant_write_mode", "qdrant_pending_count", "qdrant_sleep_pending_count",
        "formation_log_count", "formation_queued_count", "formation_written_count", "live_accumulation_enabled",
        "live_accumulation_updates", "memory_integration_mode", "recall_request_count", "recall_hit_count", "alpha", "temperature",
    ]
    status = {k: status_raw.get(k) for k in status_keys}
    (bundle_dir / "status.json").write_text(json.dumps(status_raw, ensure_ascii=False, indent=2), encoding="utf-8")

    proc_snapshot = run(["bash", "-lc", "ps -ef | grep '[c]hat_server.py' && ss -ltnp | grep ':7860' || true"], cwd)
    (bundle_dir / "process_snapshot.txt").write_text(proc_snapshot["stdout"] + proc_snapshot["stderr"], encoding="utf-8")
    git_snapshot = run(["bash", "-lc", "git rev-parse HEAD 2>/dev/null; git status --short 2>/dev/null | head -200"], cwd)
    (bundle_dir / "git_snapshot.txt").write_text(git_snapshot["stdout"] + git_snapshot["stderr"], encoding="utf-8")

    files = []
    for name in DEFAULT_FILES + args.file:
        files.append(copy_file(cwd / name, bundle_dir))
    # Include generated reports if already present.
    for glob_pat in [
        "results/baby_alex_115_protected_set_20260603/*",
        "results/baby_alex_116_preflight/*",
        "results/baby_alex_116_wake_probes/*",
    ]:
        for src in sorted(cwd.glob(glob_pat)):
            if src.is_file():
                dst = bundle_dir / src.name
                shutil.copy2(src, dst)
                files.append({"source": str(src), "bundle_path": str(dst), "copied": True, "bytes": dst.stat().st_size, "sha256": sha256(dst)})

    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "pre-sleep archive bundle scaffold/current runtime snapshot; not a live sleep clearance by itself",
        "session_id": args.session_id,
        "instance_id": instance_id,
        "base_url": args.base_url,
        "bundle_dir": str(bundle_dir),
        "status": status,
        "process_snapshot": proc_snapshot,
        "git_snapshot": git_snapshot,
        "files": files,
        "summary": {
            "copied_files": sum(1 for f in files if f.get("copied")),
            "missing_files": sum(1 for f in files if not f.get("copied")),
            "no_shared_memory": bool(status.get("no_shared_memory")),
            "private_collection": str(status.get("qdrant_collection", "")).startswith("mocop_private_"),
            "sleep_was_not_run_by_this_script": True,
        },
    }
    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(manifest, bundle_dir / "manifest.md")
    print(f"WROTE {manifest_path}")
    print(f"WROTE {bundle_dir / 'manifest.md'}")
    print(json.dumps(manifest["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
