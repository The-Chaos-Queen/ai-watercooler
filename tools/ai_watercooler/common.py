from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode
import urllib.error
import urllib.request


def sanitize_terminal_text(value: Any) -> str:
    text = str(value or "")
    safe_chars = []
    for ch in text:
        codepoint = ord(ch)
        if ch in "\n\t" or codepoint >= 32:
            safe_chars.append(ch)
        else:
            safe_chars.append(f"\\x{codepoint:02x}")
    return "".join(safe_chars)


def default_config_path() -> Path:
    override = os.environ.get("AI_WATERCOOLER_CONFIG", "").strip()
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "AIWatercooler" / "config.json"
    return Path.home() / ".config" / "ai-watercooler" / "config.json"


def load_config(path: str = "") -> Dict[str, Any]:
    config_path = Path(path).expanduser() if path else default_config_path()
    with config_path.open("r", encoding="utf-8-sig") as handle:
        config = json.load(handle)
    required = ("base_url", "token")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"Config file {config_path} is missing required keys: {', '.join(missing)}")
    config["_config_path"] = str(config_path)
    return config


def pretty_message(row: Dict[str, Any]) -> str:
    tags = row.get("tags") or []
    tag_text = f" tags={','.join(sanitize_terminal_text(tag) for tag in tags)}" if tags else ""
    topic_text = f" topic={sanitize_terminal_text(row.get('topic'))}" if row.get("topic") else ""
    return (
        f"[{row.get('id')}] {sanitize_terminal_text(row.get('ts'))} "
        f"{sanitize_terminal_text(row.get('from_agent'))} -> {sanitize_terminal_text(row.get('to_agent'))} "
        f"thread={sanitize_terminal_text(row.get('thread'))} lang={sanitize_terminal_text(row.get('lang'))}{topic_text}{tag_text}\n"
        f"{sanitize_terminal_text(row.get('body', ''))}"
    )


def request_json(
    config: Dict[str, Any],
    *,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    query: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    url = config["base_url"].rstrip("/") + path
    if query:
        filtered = {key: value for key, value in query.items() if value not in ("", None)}
        if filtered:
            url += "?" + urlencode(filtered)

    data = None
    headers = {"X-Watercooler-Token": config["token"]}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method.upper()} {path} failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"{method.upper()} {path} failed: {exc}") from exc


def pretty_task(row: Dict[str, Any]) -> str:
    labels = row.get("labels") or []
    refs = row.get("refs") or []
    artifacts = row.get("artifacts") or []
    extras = []
    if row.get("assignee"):
        extras.append(f"assignee={sanitize_terminal_text(row['assignee'])}")
    if row.get("claim_agent"):
        extras.append(f"claim={sanitize_terminal_text(row['claim_agent'])}")
    if row.get("lease_expires_ts"):
        extras.append(f"lease={sanitize_terminal_text(row['lease_expires_ts'])}")
    if row.get("blocked_reason"):
        extras.append(f"blocked={sanitize_terminal_text(row['blocked_reason'])}")
    if labels:
        extras.append(f"labels={','.join(sanitize_terminal_text(label) for label in labels)}")
    if refs:
        extras.append(f"refs={len(refs)}")
    if artifacts:
        extras.append(f"artifacts={len(artifacts)}")
    extra_text = f" {' | '.join(extras)}" if extras else ""
    description = sanitize_terminal_text(row.get("description", "").strip())
    lines = [
        (
            f"[{row.get('id')}] {sanitize_terminal_text(row.get('status'))} p={row.get('priority')} "
            f"{sanitize_terminal_text(row.get('project'))}:{sanitize_terminal_text(row.get('thread'))} "
            f"{sanitize_terminal_text(row.get('title'))} "
            f"cost={sanitize_terminal_text(row.get('cost_class'))} trust={sanitize_terminal_text(row.get('trust_class'))}{extra_text}"
        )
    ]
    if description:
        lines.append(description)
    return "\n".join(lines)


def pretty_task_event(row: Dict[str, Any]) -> str:
    note = sanitize_terminal_text(row.get("note", ""))
    details = row.get("details") or {}
    detail_text = f" details={sanitize_terminal_text(json.dumps(details, ensure_ascii=False))}" if details else ""
    return (
        f"[{row.get('id')}] {sanitize_terminal_text(row.get('ts'))} task={row.get('task_id')} "
        f"{sanitize_terminal_text(row.get('actor'))} {sanitize_terminal_text(row.get('event_type'))}{detail_text}"
        + (f"\n{note}" if note else "")
    )
