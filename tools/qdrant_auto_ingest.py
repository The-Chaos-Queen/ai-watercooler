#!/usr/bin/env python3
"""
qdrant_auto_ingest.py — Scans session logs for qdrant_sync: pending and ingests them.
Runs as scheduled task on Laura's laptop (has qdrant-client + sentence-transformers).

Usage:
  python qdrant_auto_ingest.py          # scan and ingest
  python qdrant_auto_ingest.py --dry-run # show what would be ingested
"""

import glob
import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

SESSION_DIR = Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory\session_logs")
INGEST_SCRIPT = Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\Projects\Project_Prosthetic\ingest_sessions.py")
LOG_FILE = Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\tools\backup_logs\qdrant_auto_ingest.log")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def find_pending():
    pending = []
    for path in sorted(SESSION_DIR.glob("*.md")):
        head = path.read_text(encoding="utf-8")[:500]
        if "qdrant_sync: pending" in head or "qdrant_sync: skipped" in head:
            pending.append(path)
    return pending


def ingest(path, dry_run=False):
    fname = path.name
    if dry_run:
        log(f"  DRY RUN: would ingest {fname}")
        return True

    try:
        result = subprocess.run(
            [sys.executable, str(INGEST_SCRIPT), str(path)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            content = path.read_text(encoding="utf-8")
            content = content.replace("qdrant_sync: pending", "qdrant_sync: done")
            content = content.replace("qdrant_sync: skipped", "qdrant_sync: done")
            path.write_text(content, encoding="utf-8")
            log(f"  OK: {fname}")
            return True
        else:
            log(f"  FAIL: {fname} -> {result.stderr[:200]}")
            return False
    except Exception as e:
        log(f"  ERROR: {fname} -> {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    pending = find_pending()
    if not pending:
        log("No pending session logs.")
        return

    log(f"Found {len(pending)} pending session logs.")
    ok = 0
    for path in pending:
        if ingest(path, dry_run=args.dry_run):
            ok += 1
    log(f"Done: {ok}/{len(pending)} ingested.")


if __name__ == "__main__":
    main()
