from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def _truncate(text: str, max_chars: int) -> str:
    if max_chars < 0 or len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3].rstrip() + "..."


def iter_jsonl(path: str | Path) -> Iterator[tuple[int, dict[str, Any]]]:
    """Stream JSONL rows as ``(line_no, row)`` pairs.

    Malformed lines are yielded as ``parse_error`` rows so a huge raw log does
    not abort after hours of processing because of one bad line.
    """
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            raw = line.rstrip("\n")
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                yield line_no, {"type": "parse_error", "error": str(exc), "raw": raw[:500]}
                continue
            if isinstance(row, dict):
                yield line_no, row
            else:
                yield line_no, {"type": "parse_error", "error": "non-object JSON row", "raw": raw[:500]}


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                value = item.get("text") or item.get("input_text") or item.get("output_text")
                if value:
                    parts.append(str(value))
            elif item is not None:
                parts.append(str(item))
        return "\n".join(parts)
    if content is None:
        return ""
    return str(content)


def _payload_message(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("type") != "message":
        return None
    role = str(payload.get("role") or "unknown")
    text = _content_to_text(payload.get("content"))
    return {"event_type": "message", "role": role, "text": text}


def iter_codex_events(path: str | Path, *, max_text_chars: int = 2000) -> Iterator[dict[str, Any]]:
    """Yield normalized Codex rollout events from a JSONL session log."""
    for line_no, row in iter_jsonl(path):
        timestamp = str(row.get("timestamp") or "")
        raw_type = str(row.get("type") or "unknown")
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}

        event: dict[str, Any] | None = None
        if row.get("type") == "parse_error":
            event = {
                "event_type": "parse_error",
                "role": "system",
                "text": str(row.get("raw") or row.get("error") or ""),
            }
        elif raw_type == "session_meta":
            event = {
                "event_type": "session_meta",
                "role": "system",
                "text": f"cwd={payload.get('cwd', '')} originator={payload.get('originator', '')}",
                "session_id": payload.get("id"),
            }
        elif raw_type == "response_item":
            event = _payload_message(payload)
        elif raw_type == "event_msg":
            payload_type = str(payload.get("type") or "event")
            exit_code = payload.get("exit_code")
            message = str(payload.get("message") or payload.get("text") or payload_type)
            event_type = "tool_error" if isinstance(exit_code, int) and exit_code != 0 else payload_type
            event = {
                "event_type": event_type,
                "role": "tool",
                "text": message,
                "exit_code": exit_code,
            }

        if event is None:
            event = {"event_type": raw_type, "role": "unknown", "text": ""}

        event.setdefault("exit_code", None)
        event.update({"line_no": line_no, "timestamp": timestamp, "raw_type": raw_type})
        event["text"] = _truncate(str(event.get("text") or ""), max_text_chars)
        yield event
