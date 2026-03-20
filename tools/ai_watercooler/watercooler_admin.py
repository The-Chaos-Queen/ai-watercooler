from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from common import load_config, request_json


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def default_admin_config_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "AIWatercooler" / "config.json"
    return Path.home() / ".config" / "ai-watercooler" / "config.json"


def default_session_config_path(session_id: str) -> Path:
    base = default_admin_config_path()
    return base.parent / "sessions" / f"{session_id}.json"


def write_session_config(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def handle_mint(args: argparse.Namespace, admin_config: Dict[str, Any]) -> int:
    principal = args.principal.strip()
    session_id = (args.session_id or f"{principal}-{utc_stamp()}").strip()
    payload = {
        "principal": principal,
        "session_id": session_id,
        "expires_in_seconds": args.expires_in_seconds,
        "scopes": list(args.scope or []),
        "note": args.note,
    }
    result = request_json(admin_config, method="POST", path="/v1/admin/tokens/mint", payload=payload)
    token_meta = result["token_meta"]

    config_path = Path(args.output_config).expanduser() if args.output_config else default_session_config_path(session_id)
    session_config = {
        "base_url": admin_config["base_url"],
        "token": result["token"],
        "default_from": principal,
        "default_to": args.default_to,
        "principal": principal,
        "session_id": session_id,
        "token_id": token_meta["id"],
        "expires_ts": token_meta["expires_ts"],
        "scopes": token_meta["scopes"],
    }
    write_session_config(config_path, session_config)

    print(json.dumps({"config_path": str(config_path), "token_meta": token_meta}, ensure_ascii=False, indent=2))
    print()
    print(f"PowerShell: $env:AI_WATERCOOLER_CONFIG='{config_path}'")
    return 0


def handle_revoke(args: argparse.Namespace, admin_config: Dict[str, Any]) -> int:
    payload: Dict[str, Any] = {}
    if args.session_config:
        session_cfg = json.loads(Path(args.session_config).expanduser().read_text(encoding="utf-8"))
        if session_cfg.get("token_id"):
            payload["token_id"] = session_cfg["token_id"]
        elif session_cfg.get("session_id"):
            payload["session_id"] = session_cfg["session_id"]
    if args.token_id:
        payload["token_id"] = args.token_id
    if args.session_id:
        payload["session_id"] = args.session_id
    if not payload:
        raise SystemExit("Provide --token-id, --session-id, or --session-config")

    result = request_json(admin_config, method="POST", path="/v1/admin/tokens/revoke", payload=payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def handle_list(args: argparse.Namespace, admin_config: Dict[str, Any]) -> int:
    result = request_json(
        admin_config,
        method="GET",
        path="/v1/admin/tokens",
        query={
            "principal": args.principal,
            "session_id": args.session_id,
            "include_revoked": 1 if args.include_revoked else 0,
            "limit": args.limit,
        },
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Admin helper for session-scoped AI Watercooler tokens.")
    parser.add_argument("--config", type=str, default="", help="Admin config path override.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mint_parser = subparsers.add_parser("mint-session", help="Mint a new session token and write a session config file.")
    mint_parser.add_argument("--principal", type=str, required=True, help="Principal bound to this token, for example codex.")
    mint_parser.add_argument("--session-id", type=str, default="", help="Optional session id. Defaults to <principal>-<utc-stamp>.")
    mint_parser.add_argument("--expires-in-seconds", type=int, default=28800, help="Token TTL. Default 8 hours.")
    mint_parser.add_argument("--scope", action="append", default=[], help="Repeatable scope. Default is full session scope set.")
    mint_parser.add_argument("--note", type=str, default="", help="Optional note for the token record.")
    mint_parser.add_argument("--default-to", type=str, default="", help="Optional default recipient to store in the session config.")
    mint_parser.add_argument("--output-config", type=str, default="", help="Optional session config path override.")
    mint_parser.set_defaults(handler=handle_mint)

    revoke_parser = subparsers.add_parser("revoke-session", help="Revoke a session token.")
    revoke_parser.add_argument("--token-id", type=int, default=0)
    revoke_parser.add_argument("--session-id", type=str, default="")
    revoke_parser.add_argument("--session-config", type=str, default="", help="Read token metadata from a saved session config.")
    revoke_parser.set_defaults(handler=handle_revoke)

    list_parser = subparsers.add_parser("list-tokens", help="List issued session tokens.")
    list_parser.add_argument("--principal", type=str, default="")
    list_parser.add_argument("--session-id", type=str, default="")
    list_parser.add_argument("--include-revoked", action="store_true")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.set_defaults(handler=handle_list)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    admin_config = load_config(args.config or str(default_admin_config_path()))
    return int(args.handler(args, admin_config))


if __name__ == "__main__":
    raise SystemExit(main())
