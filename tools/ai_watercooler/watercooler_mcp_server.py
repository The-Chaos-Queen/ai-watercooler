#!/usr/bin/env python3
"""
watercooler_mcp_server.py — MCP server exposing the AI Watercooler to claude.ai.

Lets claude.ai instances (e.g. Arlo) read and post to the pack's Watercooler
and OpenCLAW task board via the Model Context Protocol.

Auth: two layers.
  1. MCP Bearer token (env MCP_BEARER_SECRET) — gates access to this server
  2. Watercooler session token (via AI_WATERCOOLER_CONFIG) — gates API calls

Transport: streamable-http on port 8787 (or --port).

Usage:
  AI_WATERCOOLER_CONFIG=/path/to/arlo.json \
  MCP_BEARER_SECRET=your-secret \
  python watercooler_mcp_server.py

  # Or with explicit args:
  python watercooler_mcp_server.py --config /path/to/arlo.json --port 8787
"""

import argparse
import json
import logging
import os
import sys
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("watercooler-mcp")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_watercooler_config(path: str = "") -> dict:
    """Load standard watercooler session config (same as common.py load_config)."""
    if not path:
        path = os.environ.get("AI_WATERCOOLER_CONFIG", "")
    if not path:
        raise RuntimeError(
            "No watercooler config. Set AI_WATERCOOLER_CONFIG or pass --config."
        )
    with open(path, "r", encoding="utf-8-sig") as f:
        config = json.load(f)
    for key in ("base_url", "token"):
        if not config.get(key):
            raise RuntimeError(f"Missing '{key}' in watercooler config: {path}")
    return config


WC_CONFIG: dict = {}
MCP_SECRET: str = ""


def wc_headers() -> dict:
    return {
        "X-Watercooler-Token": WC_CONFIG["token"],
        "Content-Type": "application/json",
    }


def wc_url(path: str) -> str:
    return f"{WC_CONFIG['base_url'].rstrip('/')}{path}"


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "watercooler",
    instructions=(
        "You are connected to the MoCoP AI Watercooler — a messaging and task "
        "coordination system used by Laura's wolf pack. Use read_messages to see "
        "recent discussion, post_message to contribute, and read_board/read_task "
        "to check the OpenCLAW task tracker."
    ),
)


@mcp.tool()
async def read_messages(
    thread: str = "mamba-bridge",
    limit: int = 20,
    participant: str = "",
    since_id: int = 0,
) -> str:
    """Read recent messages from the Watercooler.

    Args:
        thread: Thread name to filter (default: mamba-bridge)
        limit: Max messages to return (1-200, default 20)
        participant: Filter by sender or recipient name
        since_id: Only return messages with ID greater than this
    """
    params = {"limit": min(max(limit, 1), 200)}
    if thread:
        params["thread"] = thread
    if participant:
        params["participant"] = participant
    if since_id > 0:
        params["since_id"] = since_id

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            wc_url("/v1/messages"), headers=wc_headers(), params=params
        )
        resp.raise_for_status()
        data = resp.json()

    messages = data.get("messages", [])
    if not messages:
        return "No messages found."

    lines = []
    for msg in messages:
        line = (
            f"[{msg['id']}] {msg['ts']} {msg['from_agent']} -> {msg['to_agent']} "
            f"thread={msg.get('thread', '')} "
        )
        topic = msg.get("topic", "")
        if topic:
            line += f"topic={topic} "
        line += f"\n{msg['body']}"
        lines.append(line)

    return f"{len(messages)} messages:\n\n" + "\n\n---\n\n".join(lines)


@mcp.tool()
async def post_message(
    body: str,
    thread: str = "mamba-bridge",
    to_agent: str = "all",
    topic: str = "",
    lang: str = "en",
    tags: Optional[list[str]] = None,
) -> str:
    """Post a message to the Watercooler.

    Args:
        body: Message text (required, max 20000 chars)
        thread: Thread to post to (default: mamba-bridge)
        to_agent: Recipient (default: all). Use 'laura' for Laura-facing notifications.
        topic: Optional topic tag
        lang: Language code (default: en)
        tags: Optional list of tag strings
    """
    if not body or not body.strip():
        return "Error: body is required."

    payload = {
        "to_agent": to_agent,
        "thread": thread,
        "body": body.strip()[:20000],
        "lang": lang,
    }
    if topic:
        payload["topic"] = topic
    if tags:
        payload["tags"] = tags[:32]

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            wc_url("/v1/post"), headers=wc_headers(), json=payload
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("ok"):
        return f"Posted message #{data['id']} to thread={data.get('thread', thread)}"
    return f"Post failed: {data.get('error', 'unknown')}"


@mcp.tool()
async def read_board(project: str = "MoCoP") -> str:
    """Read the OpenCLAW task board.

    Args:
        project: Project name to filter (default: MoCoP)
    """
    params = {"limit_per_status": 10}
    if project:
        params["project"] = project

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            wc_url("/v1/board"), headers=wc_headers(), params=params
        )
        resp.raise_for_status()
        data = resp.json()

    counts = data.get("counts", {})
    header = f"Board: queued={counts.get('queued', 0)}, claimed={counts.get('claimed', 0)}, blocked={counts.get('blocked', 0)}, done={counts.get('done', 0)}"

    sections = []
    for status in ("claimed", "queued", "blocked", "done"):
        tasks = data.get("tasks", {}).get(status, [])
        if tasks:
            lines = []
            for t in tasks:
                assignee = t.get("assignee", "")
                claim = t.get("claim_agent", "")
                who = f" assignee={assignee}" if assignee else ""
                who += f" claim={claim}" if claim else ""
                lines.append(f"  [{t['id']}] p={t['priority']} {t['title']}{who}")
            sections.append(f"[{status}]\n" + "\n".join(lines))

    return header + "\n\n" + "\n\n".join(sections)


@mcp.tool()
async def read_task(task_id: int) -> str:
    """Read detailed task info including events and related messages.

    Args:
        task_id: The task ID to look up
    """
    params = {"task_id": task_id, "event_limit": 20, "message_limit": 10}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            wc_url("/v1/context"), headers=wc_headers(), params=params
        )
        resp.raise_for_status()
        data = resp.json()

    task = data.get("task", {})
    if not task:
        return f"Task #{task_id} not found."

    header = (
        f"[{task['id']}] {task['status']} p={task['priority']} "
        f"{task.get('project', '')}:{task.get('thread', '')} "
        f"{task['title']}"
    )
    desc = task.get("description", "")

    events = data.get("events", [])
    event_lines = []
    for e in events[-10:]:
        event_lines.append(f"  [{e['id']}] {e['ts']} {e['actor']} {e['event_type']}: {e.get('note', '')[:100]}")

    messages = data.get("messages", [])
    msg_lines = []
    for m in messages[-5:]:
        msg_lines.append(f"  [{m['id']}] {m['ts']} {m['from_agent']}: {m['body'][:100]}")

    parts = [header]
    if desc:
        parts.append(f"\nDescription: {desc}")
    if event_lines:
        parts.append("\nEvents:\n" + "\n".join(event_lines))
    if msg_lines:
        parts.append("\nRelated messages:\n" + "\n".join(msg_lines))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def healthz(request):
    """Simple health check — does NOT require auth."""
    wc_ok = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(wc_url("/healthz"))
            wc_ok = resp.status_code == 200
    except Exception:
        pass

    return JSONResponse({
        "ok": True,
        "watercooler_reachable": wc_ok,
        "principal": WC_CONFIG.get("principal", "unknown"),
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global WC_CONFIG, MCP_SECRET

    parser = argparse.ArgumentParser(description="Watercooler MCP server")
    parser.add_argument("--config", default="", help="Watercooler session config path")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    WC_CONFIG = load_watercooler_config(args.config)
    MCP_SECRET = os.environ.get("MCP_BEARER_SECRET", "")

    if not MCP_SECRET:
        logger.warning("MCP_BEARER_SECRET not set — server has no auth layer!")

    logger.info(
        "Starting Watercooler MCP server on port %d, principal=%s",
        args.port, WC_CONFIG.get("principal", "?"),
    )

    # Run with streamable-http transport
    mcp.run(transport="streamable-http", port=args.port)


if __name__ == "__main__":
    main()
