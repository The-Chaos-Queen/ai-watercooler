"""Exocortex MCP server.

Small local bridge between Codex and the existing CHEESE memory stack.

This exposes:
- semantic recall from Project_Prosthetic / Qdrant
- exact archive search across session logs and raw session stores
- a lightweight ingest hook for recent Codex / Claude Code / Antigravity sessions

Run via stdio:
    python server.py
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: mcp. "
        f"Original import error: {exc}"
    )


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_PROSTHETIC = REPO_ROOT / "Projects" / "Project_Prosthetic"
RECALL_SCRIPT = PROJECT_PROSTHETIC / "recall.py"
INGEST_SCRIPT = PROJECT_PROSTHETIC / "ingest_codex_sessions.py"

SEARCH_PATHS = [
    REPO_ROOT / "CHEESE_Memory" / "session_logs",
    REPO_ROOT / "Preserved-History",
    Path.home() / ".codex" / "sessions",
    Path.home() / ".codex" / "archived_sessions",
]

mcp = FastMCP("exocortex")


def _split_csv(values: list[str] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for value in values:
        for piece in str(value).split(","):
            piece = piece.strip()
            if piece:
                out.append(piece)
    return list(dict.fromkeys(out))


@lru_cache(maxsize=1)
def _get_memory_engine() -> tuple[Any, str]:
    """Lazily load the memory engine and silence its startup chatter."""
    sys.path.insert(0, str(PROJECT_PROSTHETIC))
    with contextlib.redirect_stdout(io.StringIO()):
        from memory_engine import COLLECTION_NAME, MemoryEngine  # type: ignore

        engine = MemoryEngine()
    return engine, COLLECTION_NAME


def _run_python_script(script: Path, args: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(PROJECT_PROSTHETIC),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "command": [sys.executable, str(script), *args],
    }


@mcp.tool()
def semantic_recall(
    query: str,
    limit: int = 5,
    threshold: float = 0.25,
    source_types: list[str] | None = None,
    tags: list[str] | None = None,
    source_contains: str = "",
) -> dict[str, Any]:
    """Semantic recall from Exocortex/Qdrant using the local CHEESE memory engine."""
    try:
        engine, _collection_name = _get_memory_engine()
        clean_source_types = _split_csv(source_types)
        clean_tags = _split_csv(tags)
        with contextlib.redirect_stdout(io.StringIO()):
            results = engine.search(
                query=query,
                limit=limit,
                score_threshold=threshold,
                filter_types=clean_source_types,
                tags_any=clean_tags,
                source_contains=source_contains or None,
            )
        return {
            "ok": True,
            "query": query,
            "count": len(results),
            "results": results,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "query": query,
        }


@mcp.tool()
def memory_status() -> dict[str, Any]:
    """Check Exocortex/Qdrant connectivity and return the current collection count."""
    try:
        engine, collection_name = _get_memory_engine()
        with contextlib.redirect_stdout(io.StringIO()):
            count_result = engine.client.count(collection_name=collection_name, exact=True)
        return {
            "ok": True,
            "collection": collection_name,
            "count": int(count_result.count),
            "host": getattr(engine.client, "host", "unknown"),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


@mcp.tool()
def archive_grep(needle: str, limit: int = 20) -> dict[str, Any]:
    """Exact search across session logs, preserved history, and raw Codex sessions."""
    paths = [str(path) for path in SEARCH_PATHS if path.exists()]
    if not paths:
        return {
            "ok": False,
            "error": "No search paths were found.",
            "needle": needle,
        }

    try:
        result = subprocess.run(
            [
                "rg",
                "-n",
                "--no-heading",
                "--fixed-strings",
                needle,
                *paths,
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "error": "ripgrep (rg) is not installed or not on PATH.",
            "needle": needle,
        }

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    trimmed = lines[: max(1, limit)]
    return {
        "ok": result.returncode in (0, 1),
        "needle": needle,
        "count": len(lines),
        "results": trimmed,
    }


@mcp.tool()
def ingest_recent_sessions(
    provider: str = "codex",
    limit: int = 5,
    include_archived: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Ingest recent Codex, Claude Code, or Antigravity sessions into Exocortex."""
    provider = str(provider).strip().lower()
    if provider not in {"codex", "claude_code", "antigravity"}:
        return {
            "ok": False,
            "error": "provider must be one of: codex, claude_code, antigravity",
            "provider": provider,
        }

    args = ["--provider", provider]
    if limit > 0:
        args.extend(["--limit", str(limit)])
    if include_archived and provider == "codex":
        args.append("--include-archived")
    if dry_run:
        args.append("--dry-run")

    return _run_python_script(INGEST_SCRIPT, args)


@mcp.tool()
def recall_cli(
    query: str,
    limit: int = 5,
    threshold: float = 0.25,
    source_types: list[str] | None = None,
    tags: list[str] | None = None,
    source_contains: str = "",
) -> dict[str, Any]:
    """Run the existing recall.py CLI and return its formatted output verbatim."""
    args = [query, "--limit", str(limit), "--threshold", str(threshold)]
    for source_type in _split_csv(source_types):
        args.extend(["--type", source_type])
    for tag in _split_csv(tags):
        args.extend(["--tag", tag])
    if source_contains:
        args.extend(["--source-contains", source_contains])
    return _run_python_script(RECALL_SCRIPT, args)


if __name__ == "__main__":
    mcp.run(transport="stdio")
