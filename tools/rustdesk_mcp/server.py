"""MCP server exposing RustDesk Pro admin tools.

Run via stdio (for Claude Desktop / Cursor / other MCP clients):
    python server.py
"""

from __future__ import annotations

import json
from typing import Any, Dict

from rustdesk_client import RustDeskClient, RustDeskError

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: mcp. Install requirements first. "
        f"Original import error: {exc}"
    )


mcp = FastMCP("rustdesk-pro")
_client: RustDeskClient | None = None


def get_client() -> RustDeskClient:
    global _client
    if _client is None:
        _client = RustDeskClient()
    return _client


@mcp.tool()
def rustdesk_healthcheck() -> Dict[str, Any]:
    """Validate API connectivity and token auth."""
    try:
        return get_client().healthcheck()
    except RustDeskError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_devices(query: str = "", status: str = "all", limit: int = 50) -> Dict[str, Any]:
    """List RustDesk devices. Optional query/status filters."""
    return get_client().list_devices(query=query, status=status, limit=limit)


@mcp.tool()
def assign_device(
    device_id: str,
    user_id: str = "",
    group_id: str = "",
    note: str = "",
) -> Dict[str, Any]:
    """Assign a device to a user or group."""
    return get_client().assign_device(
        device_id=device_id,
        user_id=user_id or None,
        group_id=group_id or None,
        note=note,
    )


@mcp.tool()
def disable_device(device_id: str, reason: str = "") -> Dict[str, Any]:
    """Disable a device in RustDesk Pro."""
    return get_client().disable_device(device_id=device_id, reason=reason)


@mcp.tool()
def audit_events(limit: int = 50, actor: str = "", device_id: str = "") -> Dict[str, Any]:
    """Fetch recent audit events."""
    return get_client().audit_events(limit=limit, actor=actor, device_id=device_id)


@mcp.tool()
def explain_connector_config() -> Dict[str, Any]:
    """Return currently expected env vars and endpoint templates."""
    keys = {
        "RUSTDESK_BASE_URL": "https://rustdesk.example.com",
        "RUSTDESK_API_TOKEN": "<token>",
        "RUSTDESK_TIMEOUT_S": "20",
        "RUSTDESK_DEVICES_PATH": "/api/devices",
        "RUSTDESK_ASSIGN_PATH": "/api/devices/assign",
        "RUSTDESK_DISABLE_PATH_TEMPLATE": "/api/devices/{device_id}/disable",
        "RUSTDESK_AUDITS_PATH": "/api/audits",
    }
    return {
        "env": keys,
        "note": (
            "Endpoint paths can differ by RustDesk Pro build/deployment. "
            "Override env vars to match your server routes."
        ),
    }


if __name__ == "__main__":
    mcp.run()
