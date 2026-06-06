from __future__ import annotations

import argparse
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, urlparse

LOGGER = logging.getLogger("ai_watercooler")

TASK_STATUSES = ("queued", "claimed", "blocked", "done")
COST_CLASSES = ("free", "local", "gpu", "rental")
TRUST_CLASSES = ("safe", "needs-review", "human-only")
SESSION_SCOPES = ("messages:read", "messages:write", "tasks:read", "tasks:write")
MAX_BODY_BYTES = 64 * 1024
REQUEST_TIMEOUT_SECONDS = 15


SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    thread TEXT NOT NULL,
    topic TEXT NOT NULL,
    lang TEXT NOT NULL,
    body TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    remote_addr TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread, id);
CREATE INDEX IF NOT EXISTS idx_messages_to_id ON messages(to_agent, id);
CREATE INDEX IF NOT EXISTS idx_messages_from_id ON messages(from_agent, id);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    body,
    content=messages,
    content_rowid=id
);
CREATE TRIGGER IF NOT EXISTS messages_fts_insert
    AFTER INSERT ON messages BEGIN
        INSERT INTO messages_fts(rowid, body) VALUES (new.id, new.body);
    END;

CREATE TABLE IF NOT EXISTS agent_cards (
    principal TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    model TEXT NOT NULL,
    capabilities_json TEXT NOT NULL,
    status TEXT NOT NULL,
    last_seen_ts TEXT NOT NULL,
    updated_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_ts TEXT NOT NULL,
    updated_ts TEXT NOT NULL,
    created_by TEXT NOT NULL,
    project TEXT NOT NULL,
    thread TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL,
    cost_class TEXT NOT NULL,
    trust_class TEXT NOT NULL,
    assignee TEXT NOT NULL,
    claim_agent TEXT NOT NULL,
    claim_ts TEXT NOT NULL,
    last_heartbeat_ts TEXT NOT NULL,
    lease_expires_ts TEXT NOT NULL,
    blocked_reason TEXT NOT NULL,
    completed_ts TEXT NOT NULL,
    labels_json TEXT NOT NULL,
    refs_json TEXT NOT NULL,
    artifacts_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority_id ON tasks(status, priority, id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_status_priority ON tasks(project, status, priority, id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee_status ON tasks(assignee, status, priority, id);
CREATE INDEX IF NOT EXISTS idx_tasks_claim_agent_status ON tasks(claim_agent, status, lease_expires_ts);

CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    event_type TEXT NOT NULL,
    note TEXT NOT NULL,
    details_json TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id, id);

CREATE TABLE IF NOT EXISTS summaries (
    thread TEXT PRIMARY KEY,
    updated_ts TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_ts TEXT NOT NULL,
    updated_ts TEXT NOT NULL,
    issued_by TEXT NOT NULL,
    principal TEXT NOT NULL,
    session_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    scopes_json TEXT NOT NULL,
    expires_ts TEXT NOT NULL,
    revoked_ts TEXT NOT NULL,
    note TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_principal_active ON auth_tokens(principal, revoked_ts, expires_ts);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_session_id ON auth_tokens(session_id, revoked_ts, expires_ts);
"""


@dataclass(frozen=True)
class AuthContext:
    principal: str
    session_id: str
    scopes: frozenset[str]
    token_id: int


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_after(seconds: int) -> str:
    delta = timedelta(seconds=max(1, seconds))
    return (datetime.now(timezone.utc) + delta).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc_iso(value: str) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def seconds_between_iso(start: str, end: str) -> int:
    return max(0, int((parse_utc_iso(end) - parse_utc_iso(start)).total_seconds()))


def age_days(start: str, now: str) -> float:
    return round(seconds_between_iso(start, now) / 86400.0, 2)


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(q * len(ordered) + 0.999999) - 1))
    return round(float(ordered[index]), 2)


def median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return round(float(ordered[midpoint]), 2)
    return round(float((ordered[midpoint - 1] + ordered[midpoint]) / 2.0), 2)


def text_has_any(text: str, needles: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def classify_blocked_task_signals(
    task: Dict[str, Any],
    *,
    blocked_age_days: float,
    last_event_age_days: float,
    done_ids: set[int],
) -> List[str]:
    text = " ".join(
        [
            str(task.get("title", "")),
            str(task.get("description", "")),
            str(task.get("blocked_reason", "")),
            " ".join(str(x) for x in task.get("refs", [])),
            " ".join(str(x) for x in task.get("artifacts", [])),
        ]
    ).lower()
    signals: List[str] = []
    if blocked_age_days >= 7:
        signals.append("stale_block")
    if blocked_age_days >= 30:
        signals.append("very_stale_block")
    if last_event_age_days >= 14:
        signals.append("no_recent_review")
    if text_has_any(text, ["superseded", "replaced", "replacement", "umbrella", "decomposed"]):
        signals.append("mentions_superseded")
    if text_has_any(text, ["routing", "contaminated", "wrong claim", "wrong assignee"]):
        signals.append("routing_contamination")
    if text_has_any(text, ["gate", "blocked pending", "ethics", "approval", "qc"]):
        signals.append("gate_or_review_block")
    for done_id in done_ids:
        if f"#{done_id}" in text:
            signals.append("mentions_done_task")
            break
    return signals


def ensure_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.executescript(SCHEMA)
        conn.commit()


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.row_factory = sqlite3.Row
    return conn


def begin_immediate(conn: sqlite3.Connection) -> None:
    conn.execute("BEGIN IMMEDIATE")


def is_private_client(remote_addr: str) -> bool:
    try:
        address = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    return bool(address.is_private or address.is_loopback)


def extract_bearer_token(handler: "WatercoolerHandler") -> str:
    provided = handler.headers.get("X-Watercooler-Token", "").strip()
    if not provided:
        auth_header = handler.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            provided = auth_header[7:].strip()
    return provided


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_scopes(value: Any) -> List[str]:
    scopes = normalize_string_array(value, field_name="scopes", max_items=16, max_len=64)
    unknown = [scope for scope in scopes if scope not in SESSION_SCOPES]
    if unknown:
        raise ValueError(f"unknown scopes: {', '.join(unknown)}")
    return scopes


def token_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "created_ts": row["created_ts"],
        "updated_ts": row["updated_ts"],
        "issued_by": row["issued_by"],
        "principal": row["principal"],
        "session_id": row["session_id"],
        "scopes": json.loads(row["scopes_json"]) if row["scopes_json"] else [],
        "expires_ts": row["expires_ts"],
        "revoked_ts": row["revoked_ts"],
        "note": row["note"],
    }


def clamp_text(value: Any, *, field_name: str, max_len: int, allow_empty: bool = False) -> str:
    text = str(value or "").strip()
    if not text and not allow_empty:
        raise ValueError(f"{field_name} is required")
    if len(text) > max_len:
        raise ValueError(f"{field_name} is too long (>{max_len})")
    return text


def clamp_int(
    value: Any,
    *,
    field_name: str,
    min_value: int,
    max_value: int,
    default: Optional[int] = None,
) -> int:
    if value in (None, ""):
        if default is None:
            raise ValueError(f"{field_name} is required")
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if parsed < min_value or parsed > max_value:
        raise ValueError(f"{field_name} must be between {min_value} and {max_value}")
    return parsed


def clamp_enum(
    value: Any,
    *,
    field_name: str,
    allowed: Sequence[str],
    default: Optional[str] = None,
    allow_empty: bool = False,
) -> str:
    if value in (None, ""):
        if allow_empty:
            return ""
        if default is None:
            raise ValueError(f"{field_name} is required")
        return default
    text = clamp_text(value, field_name=field_name, max_len=64)
    if text not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(allowed)}")
    return text


def normalize_string_array(value: Any, *, field_name: str, max_items: int, max_len: int) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a JSON array of strings")
    if len(value) > max_items:
        raise ValueError(f"{field_name} cannot have more than {max_items} items")
    normalized: List[str] = []
    for item in value:
        normalized.append(clamp_text(item, field_name=field_name, max_len=max_len))
    return normalized


def merge_string_arrays(left: Sequence[str], right: Sequence[str]) -> List[str]:
    merged: List[str] = []
    seen = set()
    for item in list(left) + list(right):
        if item not in seen:
            merged.append(item)
            seen.add(item)
    return merged


def build_auth_context(conn: sqlite3.Connection, token: str) -> Optional[AuthContext]:
    token_hash = hash_token(token)
    now = utc_now()
    row = conn.execute(
        """
        SELECT id, principal, session_id, scopes_json
        FROM auth_tokens
        WHERE token_hash = ?
          AND revoked_ts = ''
          AND (expires_ts = '' OR expires_ts > ?)
        """,
        (token_hash, now),
    ).fetchone()
    if row is None:
        return None
    scopes = json.loads(row["scopes_json"]) if row["scopes_json"] else []
    return AuthContext(
        principal=row["principal"],
        session_id=row["session_id"],
        scopes=frozenset(scopes),
        token_id=int(row["id"]),
    )


def insert_task_event(
    conn: sqlite3.Connection,
    *,
    task_id: int,
    actor: str,
    event_type: str,
    note: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO task_events (task_id, ts, actor, event_type, note, details_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            utc_now(),
            actor,
            event_type,
            note.strip(),
            json.dumps(details or {}, ensure_ascii=False),
        ),
    )


def task_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "created_ts": row["created_ts"],
        "updated_ts": row["updated_ts"],
        "created_by": row["created_by"],
        "project": row["project"],
        "thread": row["thread"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "priority": row["priority"],
        "cost_class": row["cost_class"],
        "trust_class": row["trust_class"],
        "assignee": row["assignee"],
        "claim_agent": row["claim_agent"],
        "claim_ts": row["claim_ts"],
        "last_heartbeat_ts": row["last_heartbeat_ts"],
        "lease_expires_ts": row["lease_expires_ts"],
        "blocked_reason": row["blocked_reason"],
        "completed_ts": row["completed_ts"],
        "labels": json.loads(row["labels_json"]) if row["labels_json"] else [],
        "refs": json.loads(row["refs_json"]) if row["refs_json"] else [],
        "artifacts": json.loads(row["artifacts_json"]) if row["artifacts_json"] else [],
    }


def event_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "ts": row["ts"],
        "actor": row["actor"],
        "event_type": row["event_type"],
        "note": row["note"],
        "details": json.loads(row["details_json"]) if row["details_json"] else {},
    }


def message_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    tags = json.loads(row["tags_json"]) if row["tags_json"] else []
    return {
        "id": row["id"],
        "ts": row["ts"],
        "from_agent": row["from_agent"],
        "to_agent": row["to_agent"],
        "thread": row["thread"],
        "topic": row["topic"],
        "lang": row["lang"],
        "body": row["body"],
        "tags": tags,
        "remote_addr": row["remote_addr"],
    }


def agent_card_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "principal": row["principal"],
        "display_name": row["display_name"],
        "model": row["model"],
        "capabilities": json.loads(row["capabilities_json"]) if row["capabilities_json"] else [],
        "status": row["status"],
        "last_seen_ts": row["last_seen_ts"],
        "updated_ts": row["updated_ts"],
    }


def fetch_task_row(conn: sqlite3.Connection, task_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise LookupError(f"task {task_id} was not found")
    return row


def rows_by_task_id(rows: Sequence[sqlite3.Row]) -> Dict[int, sqlite3.Row]:
    return {int(row["task_id"]): row for row in rows}


def build_liveness_report(conn: sqlite3.Connection, *, project: str = "", now: str = "") -> Dict[str, Any]:
    now = now or utc_now()
    filters: List[str] = []
    params: List[Any] = []
    if project:
        filters.append("project = ?")
        params.append(project)
    where_sql = f" WHERE {' AND '.join(filters)}" if filters else ""

    counts = {
        row["status"]: int(row["count"])
        for row in conn.execute(
            f"SELECT status, COUNT(*) AS count FROM tasks{where_sql} GROUP BY status",
            params,
        ).fetchall()
    }
    counts_full = {status: int(counts.get(status, 0)) for status in TASK_STATUSES}

    done_rows = conn.execute(f"SELECT id FROM tasks{where_sql} AND status = 'done'" if where_sql else "SELECT id FROM tasks WHERE status = 'done'", params).fetchall()
    done_ids = {int(row["id"]) for row in done_rows}

    blocked_sql = f"SELECT * FROM tasks{where_sql}"
    blocked_params = list(params)
    if where_sql:
        blocked_sql += " AND status = 'blocked'"
    else:
        blocked_sql += " WHERE status = 'blocked'"
    blocked_sql += " ORDER BY updated_ts ASC, id ASC"
    blocked_rows = conn.execute(blocked_sql, blocked_params).fetchall()
    task_ids = [int(row["id"]) for row in blocked_rows]

    latest_events: Dict[int, sqlite3.Row] = {}
    latest_block_events: Dict[int, sqlite3.Row] = {}
    if task_ids:
        placeholders = ",".join("?" for _ in task_ids)
        latest_events = rows_by_task_id(
            conn.execute(
                f"""
                SELECT e.*
                FROM task_events e
                JOIN (
                    SELECT task_id, MAX(id) AS max_id
                    FROM task_events
                    WHERE task_id IN ({placeholders})
                    GROUP BY task_id
                ) latest ON latest.max_id = e.id
                """,
                task_ids,
            ).fetchall()
        )
        latest_block_events = rows_by_task_id(
            conn.execute(
                f"""
                SELECT e.*
                FROM task_events e
                JOIN (
                    SELECT task_id, MAX(id) AS max_id
                    FROM task_events
                    WHERE task_id IN ({placeholders}) AND event_type = 'blocked'
                    GROUP BY task_id
                ) latest ON latest.max_id = e.id
                """,
                task_ids,
            ).fetchall()
        )

    blocked_items: List[Dict[str, Any]] = []
    blocked_ages: List[float] = []
    for row in blocked_rows:
        task = task_row_to_dict(row)
        task_id = int(task["id"])
        block_event = latest_block_events.get(task_id)
        latest_event = latest_events.get(task_id)
        blocked_since = block_event["ts"] if block_event is not None else task["updated_ts"]
        last_event_ts = latest_event["ts"] if latest_event is not None else task["updated_ts"]
        last_event_type = latest_event["event_type"] if latest_event is not None else ""
        blocked_age = age_days(blocked_since, now)
        last_event_age = age_days(last_event_ts, now)
        signals = classify_blocked_task_signals(
            task,
            blocked_age_days=blocked_age,
            last_event_age_days=last_event_age,
            done_ids=done_ids,
        )
        review_signals = {
            "stale_block",
            "very_stale_block",
            "no_recent_review",
            "mentions_superseded",
            "mentions_done_task",
            "routing_contamination",
        }
        blocked_ages.append(blocked_age)
        blocked_items.append(
            {
                "id": task_id,
                "title": task["title"],
                "assignee": task["assignee"],
                "priority": task["priority"],
                "blocked_reason": task["blocked_reason"],
                "blocked_since": blocked_since,
                "blocked_age_days": blocked_age,
                "last_event_ts": last_event_ts,
                "last_event_age_days": last_event_age,
                "last_event_type": last_event_type,
                "refs": task["refs"],
                "labels": task["labels"],
                "signals": signals,
                "recommended_review": bool(review_signals.intersection(signals)),
            }
        )

    blocked_items.sort(key=lambda item: (-float(item["blocked_age_days"]), int(item["id"])))
    return {
        "ok": True,
        "project": project,
        "generated_ts": now,
        "counts": counts_full,
        "blocked": {
            "count": len(blocked_items),
            "median_age_days": median(blocked_ages),
            "p95_age_days": percentile(blocked_ages, 0.95),
            "oldest_age_days": round(max(blocked_ages), 2) if blocked_ages else 0.0,
            "items": blocked_items,
        },
    }


def expire_stale_claims(conn: sqlite3.Connection) -> int:
    now = utc_now()
    stale_rows = conn.execute(
        """
        SELECT id, claim_agent
        FROM tasks
        WHERE status = 'claimed'
          AND lease_expires_ts != ''
          AND lease_expires_ts < ?
        """,
        (now,),
    ).fetchall()
    for row in stale_rows:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'queued',
                updated_ts = ?,
                claim_agent = '',
                claim_ts = '',
                last_heartbeat_ts = '',
                lease_expires_ts = ''
            WHERE id = ?
            """,
            (now, row["id"]),
        )
        insert_task_event(
            conn,
            task_id=int(row["id"]),
            actor=row["claim_agent"] or "system",
            event_type="lease_expired",
            details={"expired_at": now},
        )
    return len(stale_rows)


class WatercoolerHandler(BaseHTTPRequestHandler):
    server_version = "OpenCLAW/0.1"

    @property
    def server_state(self) -> Dict[str, Any]:
        return self.server.state  # type: ignore[attr-defined]

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT_SECONDS)

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def _require_admin_token(self) -> bool:
        expected = self.server_state["admin_token"]
        provided = extract_bearer_token(self)
        if not provided or not hmac.compare_digest(provided, expected):
            self._json_error(HTTPStatus.UNAUTHORIZED, "missing or invalid admin token")
            return False
        return True

    def _require_session_auth(self, *required_scopes: str) -> Optional[AuthContext]:
        provided = extract_bearer_token(self)
        if not provided:
            self._json_error(HTTPStatus.UNAUTHORIZED, "missing or invalid token")
            return None
        with connect_db(self.server_state["db_path"]) as conn:
            auth = build_auth_context(conn, provided)
        if auth is None:
            self._json_error(HTTPStatus.UNAUTHORIZED, "missing or invalid token")
            return None
        missing = [scope for scope in required_scopes if scope not in auth.scopes]
        if missing:
            self._json_error(HTTPStatus.FORBIDDEN, f"missing required scope: {', '.join(missing)}")
            return None
        return auth

    def do_GET(self) -> None:
        if not is_private_client(self.client_address[0]):
            self._json_error(HTTPStatus.FORBIDDEN, "private-network access only")
            return

        try:
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._json_response({"ok": True, "ts": utc_now()})
                return
            if parsed.path == "/v1/admin/tokens":
                if not self._require_admin_token():
                    return
                self._handle_list_tokens(parsed.query)
                return
            if parsed.path == "/v1/admin/tokens/expiring":
                if not self._require_admin_token():
                    return
                self._handle_get_expiring_tokens(parsed.query)
                return
            if parsed.path == "/v1/summary":
                if self._require_session_auth("messages:read") is None:
                    return
                self._handle_get_summary(parsed.query)
                return
            if parsed.path == "/v1/messages":
                if self._require_session_auth("messages:read") is None:
                    return
                self._handle_get_messages(parsed.query)
                return
            if parsed.path == "/v1/tasks":
                if self._require_session_auth("tasks:read") is None:
                    return
                self._handle_get_tasks(parsed.query)
                return
            if parsed.path == "/v1/tasks/next":
                auth = self._require_session_auth("tasks:read")
                if auth is None:
                    return
                self._handle_get_next_task(auth, parsed.query)
                return
            if parsed.path == "/v1/tasks/liveness":
                if self._require_session_auth("tasks:read") is None:
                    return
                self._handle_get_task_liveness(parsed.query)
                return
            if parsed.path == "/v1/board":
                if self._require_session_auth("tasks:read") is None:
                    return
                self._handle_get_board(parsed.query)
                return
            if parsed.path == "/v1/context":
                if self._require_session_auth("tasks:read", "messages:read") is None:
                    return
                self._handle_get_context(parsed.query)
                return
            if parsed.path == "/v1/agents":
                if self._require_session_auth("messages:read") is None:
                    return
                self._handle_get_agents()
                return
            self._json_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
        except LookupError as exc:
            self._json_error(HTTPStatus.NOT_FOUND, str(exc))
        except Exception:
            LOGGER.exception("GET %s failed", self.path)
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal error")

    def do_POST(self) -> None:
        if not is_private_client(self.client_address[0]):
            self._json_error(HTTPStatus.FORBIDDEN, "private-network access only")
            return

        try:
            parsed = urlparse(self.path)
            if parsed.path == "/v1/admin/tokens/mint":
                if not self._require_admin_token():
                    return
                self._handle_mint_token()
                return
            if parsed.path == "/v1/admin/tokens/revoke":
                if not self._require_admin_token():
                    return
                self._handle_revoke_token()
                return
            if parsed.path == "/v1/post":
                auth = self._require_session_auth("messages:write")
                if auth is None:
                    return
                self._handle_post_message(auth)
                return
            if parsed.path == "/v1/tasks":
                auth = self._require_session_auth("tasks:write")
                if auth is None:
                    return
                self._handle_create_task(auth)
                return
            if parsed.path == "/v1/tasks/claim":
                auth = self._require_session_auth("tasks:write")
                if auth is None:
                    return
                self._handle_claim_task(auth)
                return
            if parsed.path == "/v1/tasks/heartbeat":
                auth = self._require_session_auth("tasks:write")
                if auth is None:
                    return
                self._handle_heartbeat_task(auth)
                return
            if parsed.path == "/v1/tasks/complete":
                auth = self._require_session_auth("tasks:write")
                if auth is None:
                    return
                self._handle_complete_task(auth)
                return
            if parsed.path == "/v1/tasks/block":
                auth = self._require_session_auth("tasks:write")
                if auth is None:
                    return
                self._handle_block_task(auth)
                return
            if parsed.path == "/v1/tasks/comment":
                auth = self._require_session_auth("tasks:write")
                if auth is None:
                    return
                self._handle_comment_task(auth)
                return
            if parsed.path == "/v1/tasks/reassign":
                auth = self._require_session_auth("tasks:write")
                if auth is None:
                    return
                self._handle_reassign_task(auth)
                return
            if parsed.path == "/v1/tasks/release":
                auth = self._require_session_auth("tasks:write")
                if auth is None:
                    return
                self._handle_release_task(auth)
                return
            if parsed.path == "/v1/tasks/unblock":
                auth = self._require_session_auth("tasks:write")
                if auth is None:
                    return
                self._handle_unblock_task(auth)
                return
            if parsed.path == "/v1/summary":
                auth = self._require_session_auth("messages:write")
                if auth is None:
                    return
                self._handle_update_summary(auth)
                return
            if parsed.path == "/v1/agents/register":
                auth = self._require_session_auth("messages:write")
                if auth is None:
                    return
                self._handle_register_agent(auth)
                return
            self._json_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
        except LookupError as exc:
            self._json_error(HTTPStatus.NOT_FOUND, str(exc))
        except Exception:
            LOGGER.exception("POST %s failed", self.path)
            self._json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal error")

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._json_error(HTTPStatus.BAD_REQUEST, "empty request body")
            return None
        if content_length > MAX_BODY_BYTES:
            self._json_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"request body exceeds {MAX_BODY_BYTES} bytes")
            return None
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._json_error(HTTPStatus.BAD_REQUEST, "invalid JSON body")
            return None
        if not isinstance(payload, dict):
            self._json_error(HTTPStatus.BAD_REQUEST, "JSON body must be an object")
            return None
        return payload

    def _handle_list_tokens(self, query: str) -> None:
        params = parse_qs(query, keep_blank_values=False)
        principal = params.get("principal", [""])[0].strip()
        session_id = params.get("session_id", [""])[0].strip()
        include_revoked = params.get("include_revoked", ["0"])[0].strip() == "1"
        limit = clamp_int(params.get("limit", ["100"])[0], field_name="limit", min_value=1, max_value=500)

        clauses: List[str] = []
        sql_params: List[Any] = []
        if not include_revoked:
            clauses.append("revoked_ts = ''")
        if principal:
            clauses.append("principal = ?")
            sql_params.append(principal)
        if session_id:
            clauses.append("session_id = ?")
            sql_params.append(session_id)

        sql = "SELECT * FROM auth_tokens"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC LIMIT ?"
        sql_params.append(limit)

        with connect_db(self.server_state["db_path"]) as conn:
            rows = conn.execute(sql, sql_params).fetchall()

        self._json_response({"tokens": [token_row_to_dict(row) for row in rows], "count": len(rows)})

    def _handle_mint_token(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            principal = clamp_text(payload.get("principal"), field_name="principal", max_len=80)
            session_id = clamp_text(payload.get("session_id"), field_name="session_id", max_len=120)
            note = clamp_text(payload.get("note", ""), field_name="note", max_len=4000, allow_empty=True)
            token_type = payload.get("token_type", "session")  # "session" or "service"
            if token_type == "service":
                # Service tokens never expire — for infrastructure (bridge, crons, MCP)
                expires_in_seconds = 0
            else:
                expires_in_seconds = clamp_int(
                    payload.get("expires_in_seconds"),
                    field_name="expires_in_seconds",
                    min_value=60,
                    max_value=2592000,  # 30 days
                    default=28800,
                )
            scopes = normalize_scopes(payload.get("scopes") or list(SESSION_SCOPES))
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        now = utc_now()
        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token)
        expires_ts = "" if token_type == "service" else utc_after(expires_in_seconds)

        with connect_db(self.server_state["db_path"]) as conn:
            cursor = conn.execute(
                """
                INSERT INTO auth_tokens (
                    created_ts, updated_ts, issued_by, principal, session_id,
                    token_hash, scopes_json, expires_ts, revoked_ts, note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', ?)
                """,
                (
                    now,
                    now,
                    "admin",
                    principal,
                    session_id,
                    token_hash,
                    json.dumps(scopes, ensure_ascii=False),
                    expires_ts,
                    note,
                ),
            )
            row = conn.execute("SELECT * FROM auth_tokens WHERE id = ?", (int(cursor.lastrowid),)).fetchone()
            conn.commit()

        self._json_response(
            {
                "ok": True,
                "token": token,
                "token_meta": token_row_to_dict(row),
            },
            status=HTTPStatus.CREATED,
        )

    def _handle_revoke_token(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        token_id_value = payload.get("token_id")
        session_id_value = str(payload.get("session_id", "")).strip()
        if not token_id_value and not session_id_value:
            self._json_error(HTTPStatus.BAD_REQUEST, "provide token_id or session_id")
            return

        now = utc_now()
        with connect_db(self.server_state["db_path"]) as conn:
            if token_id_value:
                try:
                    token_id = clamp_int(token_id_value, field_name="token_id", min_value=1, max_value=10**9)
                except ValueError as exc:
                    self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
                    return
                cursor = conn.execute(
                    """
                    UPDATE auth_tokens
                    SET revoked_ts = ?, updated_ts = ?
                    WHERE id = ? AND revoked_ts = ''
                    """,
                    (now, now, token_id),
                )
            else:
                try:
                    session_id = clamp_text(session_id_value, field_name="session_id", max_len=120)
                except ValueError as exc:
                    self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
                    return
                cursor = conn.execute(
                    """
                    UPDATE auth_tokens
                    SET revoked_ts = ?, updated_ts = ?
                    WHERE session_id = ? AND revoked_ts = ''
                    """,
                    (now, now, session_id),
                )
            conn.commit()

        self._json_response({"ok": True, "revoked": int(cursor.rowcount)})

    def _handle_get_messages(self, query: str) -> None:
        params = parse_qs(query, keep_blank_values=False)
        limit = clamp_int(params.get("limit", ["20"])[0], field_name="limit", min_value=1, max_value=200)
        since_id = clamp_int(params.get("since_id", ["0"])[0], field_name="since_id", min_value=0, max_value=10**9)
        thread = params.get("thread", [""])[0].strip()
        participant = params.get("participant", [""])[0].strip()
        search = params.get("search", [""])[0].strip()

        if search:
            # FTS5 path: join messages_fts to apply keyword filter, then apply
            # the remaining equality filters on the base table columns.
            clauses = ["m.id > ?"]
            sql_params: List[Any] = [since_id]
            if thread:
                clauses.append("m.thread = ?")
                sql_params.append(thread)
            if participant:
                clauses.append("(m.from_agent = ? OR m.to_agent = ?)")
                sql_params.extend([participant, participant])
            clauses.append("messages_fts MATCH ?")
            sql_params.append(search)

            sql = (
                "SELECT m.id, m.ts, m.from_agent, m.to_agent, m.thread, m.topic, "
                "m.lang, m.body, m.tags_json, m.remote_addr "
                "FROM messages m "
                "JOIN messages_fts ON messages_fts.rowid = m.id "
                "WHERE " + " AND ".join(clauses) +
                " ORDER BY m.id DESC LIMIT ?"
            )
            sql_params.append(limit)
        else:
            clauses = ["id > ?"]
            sql_params = [since_id]
            if thread:
                clauses.append("thread = ?")
                sql_params.append(thread)
            if participant:
                clauses.append("(from_agent = ? OR to_agent = ?)")
                sql_params.extend([participant, participant])

            sql = (
                "SELECT id, ts, from_agent, to_agent, thread, topic, lang, body, tags_json, remote_addr "
                "FROM messages"
            )
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY id DESC LIMIT ?"
            sql_params.append(limit)

        with connect_db(self.server_state["db_path"]) as conn:
            rows = conn.execute(sql, sql_params).fetchall()

        messages = [message_row_to_dict(row) for row in rows]
        self._json_response({"messages": messages, "count": len(messages)})

    def _handle_post_message(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            message = {
                "ts": utc_now(),
                "from_agent": auth.principal,
                "to_agent": clamp_text(payload.get("to_agent"), field_name="to_agent", max_len=80, allow_empty=True),
                "thread": clamp_text(payload.get("thread", "general"), field_name="thread", max_len=120),
                "topic": clamp_text(payload.get("topic", ""), field_name="topic", max_len=120, allow_empty=True),
                "lang": clamp_text(payload.get("lang", "jbo"), field_name="lang", max_len=32),
                "body": clamp_text(payload.get("body"), field_name="body", max_len=20000),
                "tags_json": json.dumps(
                    normalize_string_array(payload.get("tags"), field_name="tags", max_items=32, max_len=64),
                    ensure_ascii=False,
                ),
                "remote_addr": self.client_address[0],
            }
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (ts, from_agent, to_agent, thread, topic, lang, body, tags_json, remote_addr)
                VALUES (:ts, :from_agent, :to_agent, :thread, :topic, :lang, :body, :tags_json, :remote_addr)
                """,
                message,
            )
            message_id = int(cursor.lastrowid)
            # Update agent card last_seen_ts if a card exists for this principal.
            conn.execute(
                """
                UPDATE agent_cards
                SET last_seen_ts = ?
                WHERE principal = ?
                """,
                (message["ts"], auth.principal),
            )
            conn.commit()

        self._json_response({"ok": True, "id": message_id, "thread": message["thread"]}, status=HTTPStatus.CREATED)

    def _handle_create_task(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            project = clamp_text(payload.get("project", "general"), field_name="project", max_len=120)
            thread = clamp_text(payload.get("thread", project), field_name="thread", max_len=120)
            title = clamp_text(payload.get("title"), field_name="title", max_len=200)
            description = clamp_text(payload.get("description", ""), field_name="description", max_len=8000, allow_empty=True)
            priority = clamp_int(payload.get("priority"), field_name="priority", min_value=0, max_value=100, default=50)
            cost_class = clamp_enum(
                payload.get("cost_class"),
                field_name="cost_class",
                allowed=COST_CLASSES,
                default="local",
            )
            trust_class = clamp_enum(
                payload.get("trust_class"),
                field_name="trust_class",
                allowed=TRUST_CLASSES,
                default="safe",
            )
            assignee = clamp_text(payload.get("assignee", ""), field_name="assignee", max_len=80, allow_empty=True)
            if assignee.lower() in ("unassigned", "none", "null", "n/a"):
                assignee = ""
            labels = normalize_string_array(payload.get("labels"), field_name="labels", max_items=32, max_len=64)
            refs = normalize_string_array(payload.get("refs"), field_name="refs", max_items=64, max_len=512)
            note = clamp_text(payload.get("note", ""), field_name="note", max_len=4000, allow_empty=True)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        now = utc_now()
        task_row = {
            "created_ts": now,
            "updated_ts": now,
            "created_by": auth.principal,
            "project": project,
            "thread": thread,
            "title": title,
            "description": description,
            "status": "queued",
            "priority": priority,
            "cost_class": cost_class,
            "trust_class": trust_class,
            "assignee": assignee,
            "claim_agent": "",
            "claim_ts": "",
            "last_heartbeat_ts": "",
            "lease_expires_ts": "",
            "blocked_reason": "",
            "completed_ts": "",
            "labels_json": json.dumps(labels, ensure_ascii=False),
            "refs_json": json.dumps(refs, ensure_ascii=False),
            "artifacts_json": json.dumps([], ensure_ascii=False),
        }

        with connect_db(self.server_state["db_path"]) as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (
                    created_ts, updated_ts, created_by, project, thread, title, description,
                    status, priority, cost_class, trust_class, assignee, claim_agent, claim_ts,
                    last_heartbeat_ts, lease_expires_ts, blocked_reason, completed_ts,
                    labels_json, refs_json, artifacts_json
                )
                VALUES (
                    :created_ts, :updated_ts, :created_by, :project, :thread, :title, :description,
                    :status, :priority, :cost_class, :trust_class, :assignee, :claim_agent, :claim_ts,
                    :last_heartbeat_ts, :lease_expires_ts, :blocked_reason, :completed_ts,
                    :labels_json, :refs_json, :artifacts_json
                )
                """,
                task_row,
            )
            task_id = int(cursor.lastrowid)
            insert_task_event(
                conn,
                task_id=task_id,
                actor=auth.principal,
                event_type="created",
                note=note,
                details={
                    "project": project,
                    "thread": thread,
                    "priority": priority,
                    "cost_class": cost_class,
                    "trust_class": trust_class,
                    "assignee": assignee,
                },
            )
            row = fetch_task_row(conn, task_id)
            conn.commit()

        self._json_response({"ok": True, "task": task_row_to_dict(row)}, status=HTTPStatus.CREATED)

    def _handle_get_tasks(self, query: str) -> None:
        params = parse_qs(query, keep_blank_values=False)
        limit = clamp_int(params.get("limit", ["20"])[0], field_name="limit", min_value=1, max_value=200)
        status = params.get("status", [""])[0].strip()
        project = params.get("project", [""])[0].strip()
        assignee = params.get("assignee", [""])[0].strip()
        thread = params.get("thread", [""])[0].strip()
        task_id_text = params.get("task_id", [""])[0].strip()

        with connect_db(self.server_state["db_path"]) as conn:
            expired_count = expire_stale_claims(conn)
            clauses: List[str] = []
            sql_params: List[Any] = []

            if task_id_text:
                task_id = clamp_int(task_id_text, field_name="task_id", min_value=1, max_value=10**9)
                clauses.append("id = ?")
                sql_params.append(task_id)
            if status:
                status_value = clamp_enum(status, field_name="status", allowed=TASK_STATUSES)
                clauses.append("status = ?")
                sql_params.append(status_value)
            if project:
                clauses.append("project = ?")
                sql_params.append(project)
            if assignee:
                clauses.append("assignee = ?")
                sql_params.append(assignee)
            if thread:
                clauses.append("thread = ?")
                sql_params.append(thread)

            sql = "SELECT * FROM tasks"
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += (
                " ORDER BY CASE status "
                "WHEN 'claimed' THEN 0 WHEN 'queued' THEN 1 WHEN 'blocked' THEN 2 ELSE 3 END, "
                "priority ASC, id ASC LIMIT ?"
            )
            sql_params.append(limit)
            rows = conn.execute(sql, sql_params).fetchall()
            conn.commit()

        self._json_response(
            {
                "tasks": [task_row_to_dict(row) for row in rows],
                "count": len(rows),
                "expired_claims_requeued": expired_count,
            }
        )

    def _handle_get_next_task(self, auth: AuthContext, query: str) -> None:
        params = parse_qs(query, keep_blank_values=False)
        try:
            requested_agent = clamp_text(
                params.get("agent", [""])[0],
                field_name="agent",
                max_len=80,
                allow_empty=True,
            )
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if requested_agent and requested_agent != auth.principal:
            self._json_error(
                HTTPStatus.FORBIDDEN,
                f"token principal {auth.principal} cannot request next task for {requested_agent}",
            )
            return
        agent = auth.principal
        project = params.get("project", [""])[0].strip()
        thread = params.get("thread", [""])[0].strip()

        with connect_db(self.server_state["db_path"]) as conn:
            expired_count = expire_stale_claims(conn)
            filters: List[str] = []
            sql_params: List[Any] = []
            if project:
                filters.append("project = ?")
                sql_params.append(project)
            if thread:
                filters.append("thread = ?")
                sql_params.append(thread)

            claimed_sql = "SELECT * FROM tasks WHERE status = 'claimed' AND claim_agent = ?"
            claimed_params: List[Any] = [agent]
            if filters:
                claimed_sql += " AND " + " AND ".join(filters)
                claimed_params.extend(sql_params)
            claimed_sql += " ORDER BY priority ASC, id ASC LIMIT 1"
            row = conn.execute(claimed_sql, claimed_params).fetchone()
            selection_reason = "claimed"

            if row is None:
                queued_sql = "SELECT * FROM tasks WHERE status = 'queued' AND (assignee = '' OR assignee = ?)"
                queued_params: List[Any] = [agent]
                if filters:
                    queued_sql += " AND " + " AND ".join(filters)
                    queued_params.extend(sql_params)
                queued_sql += " ORDER BY CASE WHEN assignee = ? THEN 0 ELSE 1 END, priority ASC, id ASC LIMIT 1"
                queued_params.append(agent)
                row = conn.execute(queued_sql, queued_params).fetchone()
                selection_reason = "queued"
            conn.commit()

        self._json_response(
            {
                "task": task_row_to_dict(row) if row is not None else None,
                "selection_reason": selection_reason if row is not None else "none",
                "expired_claims_requeued": expired_count,
            }
        )

    def _handle_get_task_liveness(self, query: str) -> None:
        params = parse_qs(query, keep_blank_values=False)
        project = params.get("project", [""])[0].strip()
        now = params.get("now", [""])[0].strip()
        if now:
            try:
                parse_utc_iso(now)
            except ValueError as exc:
                self._json_error(HTTPStatus.BAD_REQUEST, f"invalid now timestamp: {exc}")
                return

        with connect_db(self.server_state["db_path"]) as conn:
            expired_count = expire_stale_claims(conn)
            report = build_liveness_report(conn, project=project, now=now)
            conn.commit()
        report["expired_claims_requeued"] = expired_count
        self._json_response(report)

    def _reject_agent_mismatch(self, payload: Dict[str, Any], auth: AuthContext) -> bool:
        requested_agent = str(payload.get("agent", "")).strip()
        if requested_agent and requested_agent != auth.principal:
            self._json_error(
                HTTPStatus.FORBIDDEN,
                f"token principal {auth.principal} cannot act as {requested_agent}",
            )
            return True
        return False

    def _handle_claim_task(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        if self._reject_agent_mismatch(payload, auth):
            return
        try:
            task_id = clamp_int(payload.get("task_id"), field_name="task_id", min_value=1, max_value=10**9)
            agent = auth.principal
            lease_seconds = clamp_int(
                payload.get("lease_seconds"),
                field_name="lease_seconds",
                min_value=60,
                max_value=86400,
                default=1800,
            )
            note = clamp_text(payload.get("note", ""), field_name="note", max_len=4000, allow_empty=True)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            begin_immediate(conn)
            expire_stale_claims(conn)
            row = fetch_task_row(conn, task_id)
            task = task_row_to_dict(row)
            if task["status"] == "done":
                self._json_error(HTTPStatus.CONFLICT, "task is already done")
                return
            if task["status"] == "blocked":
                self._json_error(HTTPStatus.CONFLICT, "task is blocked")
                return
            if task["assignee"] and task["assignee"] != agent:
                self._json_error(HTTPStatus.CONFLICT, f"task is assigned to {task['assignee']}")
                return
            if task["status"] == "claimed" and task["claim_agent"] and task["claim_agent"] != agent:
                self._json_error(HTTPStatus.CONFLICT, f"task is already claimed by {task['claim_agent']}")
                return

            now = utc_now()
            lease_expires_ts = utc_after(lease_seconds)
            conn.execute(
                """
                UPDATE tasks
                SET status = 'claimed',
                    updated_ts = ?,
                    assignee = CASE WHEN assignee = '' THEN ? ELSE assignee END,
                    claim_agent = ?,
                    claim_ts = ?,
                    last_heartbeat_ts = ?,
                    lease_expires_ts = ?,
                    blocked_reason = ''
                WHERE id = ?
                """,
                (now, agent, agent, now, now, lease_expires_ts, task_id),
            )
            insert_task_event(
                conn,
                task_id=task_id,
                actor=agent,
                event_type="claimed",
                note=note,
                details={"lease_seconds": lease_seconds},
            )
            row = fetch_task_row(conn, task_id)
            conn.commit()

        self._json_response({"ok": True, "task": task_row_to_dict(row)})

    def _handle_heartbeat_task(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        if self._reject_agent_mismatch(payload, auth):
            return
        try:
            task_id = clamp_int(payload.get("task_id"), field_name="task_id", min_value=1, max_value=10**9)
            agent = auth.principal
            lease_seconds = clamp_int(
                payload.get("lease_seconds"),
                field_name="lease_seconds",
                min_value=60,
                max_value=86400,
                default=1800,
            )
            note = clamp_text(payload.get("note", ""), field_name="note", max_len=4000, allow_empty=True)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            expire_stale_claims(conn)
            row = fetch_task_row(conn, task_id)
            task = task_row_to_dict(row)
            if task["status"] != "claimed" or task["claim_agent"] != agent:
                self._json_error(HTTPStatus.CONFLICT, "task is not actively claimed by this agent")
                return

            now = utc_now()
            lease_expires_ts = utc_after(lease_seconds)
            conn.execute(
                """
                UPDATE tasks
                SET updated_ts = ?,
                    last_heartbeat_ts = ?,
                    lease_expires_ts = ?
                WHERE id = ?
                """,
                (now, now, lease_expires_ts, task_id),
            )
            insert_task_event(
                conn,
                task_id=task_id,
                actor=agent,
                event_type="heartbeat",
                note=note,
                details={"lease_seconds": lease_seconds},
            )
            row = fetch_task_row(conn, task_id)
            conn.commit()

        self._json_response({"ok": True, "task": task_row_to_dict(row)})

    def _handle_complete_task(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        if self._reject_agent_mismatch(payload, auth):
            return
        try:
            task_id = clamp_int(payload.get("task_id"), field_name="task_id", min_value=1, max_value=10**9)
            agent = auth.principal
            note = clamp_text(payload.get("note", ""), field_name="note", max_len=4000, allow_empty=True)
            artifacts = normalize_string_array(payload.get("artifacts"), field_name="artifacts", max_items=64, max_len=512)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            expire_stale_claims(conn)
            row = fetch_task_row(conn, task_id)
            task = task_row_to_dict(row)
            if task["status"] == "done":
                self._json_error(HTTPStatus.CONFLICT, "task is already done")
                return
            if task["status"] == "blocked":
                self._json_error(HTTPStatus.CONFLICT, "task is blocked")
                return
            if task["claim_agent"] and task["claim_agent"] != agent:
                self._json_error(HTTPStatus.CONFLICT, f"task is claimed by {task['claim_agent']}")
                return
            if task["assignee"] and task["assignee"] != agent and task["claim_agent"] != agent:
                self._json_error(HTTPStatus.CONFLICT, f"task is assigned to {task['assignee']}")
                return

            merged_artifacts = merge_string_arrays(task["artifacts"], artifacts)
            now = utc_now()
            conn.execute(
                """
                UPDATE tasks
                SET status = 'done',
                    updated_ts = ?,
                    assignee = CASE WHEN assignee = '' THEN ? ELSE assignee END,
                    claim_agent = '',
                    claim_ts = '',
                    last_heartbeat_ts = '',
                    lease_expires_ts = '',
                    blocked_reason = '',
                    completed_ts = ?,
                    artifacts_json = ?
                WHERE id = ?
                """,
                (now, agent, now, json.dumps(merged_artifacts, ensure_ascii=False), task_id),
            )
            insert_task_event(
                conn,
                task_id=task_id,
                actor=agent,
                event_type="completed",
                note=note,
                details={"artifacts": merged_artifacts},
            )
            row = fetch_task_row(conn, task_id)
            conn.commit()

        self._json_response({"ok": True, "task": task_row_to_dict(row)})

    def _handle_block_task(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        if self._reject_agent_mismatch(payload, auth):
            return
        try:
            task_id = clamp_int(payload.get("task_id"), field_name="task_id", min_value=1, max_value=10**9)
            agent = auth.principal
            blocked_reason = clamp_text(payload.get("blocked_reason"), field_name="blocked_reason", max_len=400)
            note = clamp_text(payload.get("note", ""), field_name="note", max_len=4000, allow_empty=True)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            expire_stale_claims(conn)
            row = fetch_task_row(conn, task_id)
            task = task_row_to_dict(row)
            if task["status"] == "done":
                self._json_error(HTTPStatus.CONFLICT, "task is already done")
                return
            if task["claim_agent"] and task["claim_agent"] != agent:
                self._json_error(HTTPStatus.CONFLICT, f"task is claimed by {task['claim_agent']}")
                return

            now = utc_now()
            conn.execute(
                """
                UPDATE tasks
                SET status = 'blocked',
                    updated_ts = ?,
                    assignee = CASE WHEN assignee = '' THEN ? ELSE assignee END,
                    claim_agent = '',
                    claim_ts = '',
                    last_heartbeat_ts = '',
                    lease_expires_ts = '',
                    blocked_reason = ?
                WHERE id = ?
                """,
                (now, agent, blocked_reason, task_id),
            )
            insert_task_event(
                conn,
                task_id=task_id,
                actor=agent,
                event_type="blocked",
                note=note,
                details={"blocked_reason": blocked_reason},
            )
            row = fetch_task_row(conn, task_id)
            conn.commit()

        self._json_response({"ok": True, "task": task_row_to_dict(row)})

    def _handle_comment_task(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        if self._reject_agent_mismatch(payload, auth):
            return
        try:
            task_id = clamp_int(payload.get("task_id"), field_name="task_id", min_value=1, max_value=10**9)
            note = clamp_text(payload.get("note"), field_name="note", max_len=4000)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            expire_stale_claims(conn)
            row = fetch_task_row(conn, task_id)
            insert_task_event(conn, task_id=task_id, actor=auth.principal, event_type="comment", note=note)
            conn.commit()

        self._json_response({"ok": True, "task": task_row_to_dict(row)})

    def _handle_reassign_task(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        if self._reject_agent_mismatch(payload, auth):
            return
        try:
            task_id = clamp_int(payload.get("task_id"), field_name="task_id", min_value=1, max_value=10**9)
            assignee = clamp_text(payload.get("assignee", ""), field_name="assignee", max_len=80, allow_empty=True)
            note = clamp_text(payload.get("note", ""), field_name="note", max_len=4000, allow_empty=True)
            keep_claim = bool(payload.get("keep_claim", False))
            if assignee.lower() in ("unassigned", "none", "null", "n/a"):
                assignee = ""
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            begin_immediate(conn)
            expire_stale_claims(conn)
            row = fetch_task_row(conn, task_id)
            task = task_row_to_dict(row)
            if task["status"] == "done":
                self._json_error(HTTPStatus.CONFLICT, "task is already done")
                return
            now = utc_now()
            old_assignee = task["assignee"]
            old_claim_agent = task["claim_agent"]
            if keep_claim:
                conn.execute(
                    """
                    UPDATE tasks
                    SET updated_ts = ?, assignee = ?
                    WHERE id = ?
                    """,
                    (now, assignee, task_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE tasks
                    SET status = CASE WHEN status = 'claimed' THEN 'queued' ELSE status END,
                        updated_ts = ?,
                        assignee = ?,
                        claim_agent = '',
                        claim_ts = '',
                        last_heartbeat_ts = '',
                        lease_expires_ts = ''
                    WHERE id = ?
                    """,
                    (now, assignee, task_id),
                )
            insert_task_event(
                conn,
                task_id=task_id,
                actor=auth.principal,
                event_type="reassigned",
                note=note,
                details={
                    "old_assignee": old_assignee,
                    "new_assignee": assignee,
                    "old_claim_agent": old_claim_agent,
                    "claim_cleared": bool(old_claim_agent and not keep_claim),
                },
            )
            row = fetch_task_row(conn, task_id)
            conn.commit()

        self._json_response({"ok": True, "task": task_row_to_dict(row)})

    def _handle_release_task(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        if self._reject_agent_mismatch(payload, auth):
            return
        try:
            task_id = clamp_int(payload.get("task_id"), field_name="task_id", min_value=1, max_value=10**9)
            note = clamp_text(payload.get("note", ""), field_name="note", max_len=4000, allow_empty=True)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            begin_immediate(conn)
            expire_stale_claims(conn)
            row = fetch_task_row(conn, task_id)
            task = task_row_to_dict(row)
            if task["status"] != "claimed" or not task["claim_agent"]:
                self._json_error(HTTPStatus.CONFLICT, "task is not claimed")
                return
            old_claim_agent = task["claim_agent"]
            now = utc_now()
            conn.execute(
                """
                UPDATE tasks
                SET status = 'queued',
                    updated_ts = ?,
                    claim_agent = '',
                    claim_ts = '',
                    last_heartbeat_ts = '',
                    lease_expires_ts = ''
                WHERE id = ?
                """,
                (now, task_id),
            )
            insert_task_event(
                conn,
                task_id=task_id,
                actor=auth.principal,
                event_type="released",
                note=note,
                details={"old_claim_agent": old_claim_agent},
            )
            row = fetch_task_row(conn, task_id)
            conn.commit()

        self._json_response({"ok": True, "task": task_row_to_dict(row)})

    def _handle_unblock_task(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        if self._reject_agent_mismatch(payload, auth):
            return
        try:
            task_id = clamp_int(payload.get("task_id"), field_name="task_id", min_value=1, max_value=10**9)
            note = clamp_text(payload.get("note", ""), field_name="note", max_len=4000, allow_empty=True)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            begin_immediate(conn)
            expire_stale_claims(conn)
            row = fetch_task_row(conn, task_id)
            task = task_row_to_dict(row)
            if task["status"] == "done":
                self._json_error(HTTPStatus.CONFLICT, "task is already done")
                return
            if task["status"] != "blocked":
                self._json_error(HTTPStatus.CONFLICT, "task is not blocked")
                return
            now = utc_now()
            old_blocked_reason = task["blocked_reason"]
            conn.execute(
                """
                UPDATE tasks
                SET status = 'queued',
                    updated_ts = ?,
                    blocked_reason = ''
                WHERE id = ?
                """,
                (now, task_id),
            )
            insert_task_event(
                conn,
                task_id=task_id,
                actor=auth.principal,
                event_type="unblocked",
                note=note,
                details={"old_blocked_reason": old_blocked_reason},
            )
            row = fetch_task_row(conn, task_id)
            conn.commit()

        self._json_response({"ok": True, "task": task_row_to_dict(row)})

    def _handle_get_board(self, query: str) -> None:
        params = parse_qs(query, keep_blank_values=False)
        project = params.get("project", [""])[0].strip()
        limit_per_status = clamp_int(
            params.get("limit_per_status", ["5"])[0],
            field_name="limit_per_status",
            min_value=1,
            max_value=50,
        )

        with connect_db(self.server_state["db_path"]) as conn:
            expired_count = expire_stale_claims(conn)
            filters: List[str] = []
            filter_params: List[Any] = []
            if project:
                filters.append("project = ?")
                filter_params.append(project)
            where_sql = f" WHERE {' AND '.join(filters)}" if filters else ""

            counts = {
                row["status"]: row["count"]
                for row in conn.execute(
                    f"SELECT status, COUNT(*) AS count FROM tasks{where_sql} GROUP BY status",
                    filter_params,
                ).fetchall()
            }
            tasks_by_status: Dict[str, List[Dict[str, Any]]] = {}
            for status in TASK_STATUSES:
                sql = f"SELECT * FROM tasks{where_sql}"
                params_for_status = list(filter_params)
                if where_sql:
                    sql += " AND status = ?"
                else:
                    sql += " WHERE status = ?"
                params_for_status.append(status)
                if status in ("blocked", "done"):
                    sql += " ORDER BY updated_ts DESC, id DESC LIMIT ?"
                else:
                    sql += " ORDER BY priority ASC, id ASC LIMIT ?"
                params_for_status.append(limit_per_status)
                rows = conn.execute(sql, params_for_status).fetchall()
                tasks_by_status[status] = [task_row_to_dict(row) for row in rows]

            active_agents_sql = "SELECT DISTINCT claim_agent FROM tasks"
            active_agent_params = list(filter_params)
            if where_sql:
                active_agents_sql += where_sql + " AND claim_agent != ''"
            else:
                active_agents_sql += " WHERE claim_agent != ''"
            active_agents = [
                row["claim_agent"]
                for row in conn.execute(active_agents_sql, active_agent_params).fetchall()
                if row["claim_agent"]
            ]
            conn.commit()

        counts_full = {status: int(counts.get(status, 0)) for status in TASK_STATUSES}
        self._json_response(
            {
                "counts": counts_full,
                "tasks": tasks_by_status,
                "active_agents": active_agents,
                "expired_claims_requeued": expired_count,
            }
        )

    def _handle_get_context(self, query: str) -> None:
        params = parse_qs(query, keep_blank_values=False)
        try:
            task_id = clamp_int(params.get("task_id", [""])[0], field_name="task_id", min_value=1, max_value=10**9)
            event_limit = clamp_int(params.get("event_limit", ["20"])[0], field_name="event_limit", min_value=1, max_value=200)
            message_limit = clamp_int(
                params.get("message_limit", ["20"])[0],
                field_name="message_limit",
                min_value=1,
                max_value=200,
            )
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        with connect_db(self.server_state["db_path"]) as conn:
            expire_stale_claims(conn)
            row = fetch_task_row(conn, task_id)
            task = task_row_to_dict(row)
            event_rows = conn.execute(
                "SELECT * FROM task_events WHERE task_id = ? ORDER BY id DESC LIMIT ?",
                (task_id, event_limit),
            ).fetchall()
            message_rows = conn.execute(
                """
                SELECT id, ts, from_agent, to_agent, thread, topic, lang, body, tags_json, remote_addr
                FROM messages
                WHERE thread = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (task["thread"], message_limit),
            ).fetchall()
            conn.commit()

        self._json_response(
            {
                "task": task,
                "events": [event_row_to_dict(event_row) for event_row in event_rows],
                "messages": [message_row_to_dict(message_row) for message_row in message_rows],
            }
        )

    def _handle_get_agents(self) -> None:
        with connect_db(self.server_state["db_path"]) as conn:
            rows = conn.execute(
                "SELECT principal, display_name, model, capabilities_json, status, last_seen_ts, updated_ts "
                "FROM agent_cards ORDER BY principal ASC"
            ).fetchall()
        self._json_response({"agents": [agent_card_row_to_dict(row) for row in rows], "count": len(rows)})

    def _handle_get_summary(self, query: str) -> None:
        params = parse_qs(query, keep_blank_values=False)
        thread = params.get("thread", ["mamba-bridge"])[0].strip()
        with connect_db(self.server_state["db_path"]) as conn:
            row = conn.execute(
                "SELECT thread, updated_ts, updated_by, body FROM summaries WHERE thread = ?",
                (thread,),
            ).fetchone()
        if row is None:
            self._json_response({"thread": thread, "summary": None, "updated_ts": "", "updated_by": ""})
            return
        self._json_response({
            "thread": row[0],
            "updated_ts": row[1],
            "updated_by": row[2],
            "summary": row[3],
        })

    def _handle_update_summary(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        try:
            thread = clamp_text(payload.get("thread", "mamba-bridge"), field_name="thread", max_len=128)
            body = clamp_text(payload.get("body", ""), field_name="body", max_len=100_000)
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if not body:
            self._json_error(HTTPStatus.BAD_REQUEST, "body is required")
            return
        now = utc_now()
        with connect_db(self.server_state["db_path"]) as conn:
            conn.execute(
                "INSERT INTO summaries (thread, updated_ts, updated_by, body) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(thread) DO UPDATE SET updated_ts=excluded.updated_ts, updated_by=excluded.updated_by, body=excluded.body",
                (thread, now, auth.principal, body),
            )
            conn.commit()
        self._json_response({"ok": True, "thread": thread, "updated_ts": now, "updated_by": auth.principal})

    def _handle_register_agent(self, auth: AuthContext) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            # principal must match the token's principal
            requested_principal = clamp_text(
                payload.get("principal", auth.principal),
                field_name="principal",
                max_len=80,
            )
            if requested_principal != auth.principal:
                self._json_error(
                    HTTPStatus.FORBIDDEN,
                    f"token principal {auth.principal} cannot register card for {requested_principal}",
                )
                return
            display_name = clamp_text(
                payload.get("display_name", auth.principal),
                field_name="display_name",
                max_len=120,
                allow_empty=True,
            ) or auth.principal
            model = clamp_text(
                payload.get("model", ""),
                field_name="model",
                max_len=120,
                allow_empty=True,
            )
            capabilities = normalize_string_array(
                payload.get("capabilities"),
                field_name="capabilities",
                max_items=32,
                max_len=120,
            )
            status = clamp_enum(
                payload.get("status", "active"),
                field_name="status",
                allowed=("active", "dormant", "farewell"),
                default="active",
            )
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        now = utc_now()
        with connect_db(self.server_state["db_path"]) as conn:
            conn.execute(
                """
                INSERT INTO agent_cards (principal, display_name, model, capabilities_json, status, last_seen_ts, updated_ts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(principal) DO UPDATE SET
                    display_name = excluded.display_name,
                    model = excluded.model,
                    capabilities_json = excluded.capabilities_json,
                    status = excluded.status,
                    updated_ts = excluded.updated_ts
                """,
                (
                    auth.principal,
                    display_name,
                    model,
                    json.dumps(capabilities, ensure_ascii=False),
                    status,
                    now,
                    now,
                ),
            )
            row = conn.execute(
                "SELECT principal, display_name, model, capabilities_json, status, last_seen_ts, updated_ts "
                "FROM agent_cards WHERE principal = ?",
                (auth.principal,),
            ).fetchone()
            conn.commit()

        self._json_response({"ok": True, "agent": agent_card_row_to_dict(row)}, status=HTTPStatus.CREATED)

    def _handle_get_expiring_tokens(self, query: str) -> None:
        params = parse_qs(query, keep_blank_values=False)
        try:
            within_hours = clamp_int(
                params.get("within_hours", ["24"])[0],
                field_name="within_hours",
                min_value=1,
                max_value=720,
                default=24,
            )
        except ValueError as exc:
            self._json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        now = utc_now()
        cutoff = utc_after(within_hours * 3600)

        with connect_db(self.server_state["db_path"]) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM auth_tokens
                WHERE revoked_ts = ''
                  AND expires_ts != ''
                  AND expires_ts > ?
                  AND expires_ts <= ?
                ORDER BY expires_ts ASC
                """,
                (now, cutoff),
            ).fetchall()

        self._json_response(
            {
                "expiring_within_hours": within_hours,
                "tokens": [token_row_to_dict(row) for row in rows],
                "count": len(rows),
            }
        )

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        # Allow requests from the local 192.168.2.0/24 subnet or file:// origins.
        # Deny everything else by omitting the header entirely.
        allowed = False
        if origin.startswith("file://") or origin == "null":
            allowed = True
        else:
            try:
                from urllib.parse import urlparse as _urlparse
                host = _urlparse(origin).hostname or ""
                addr = ipaddress.ip_address(host)
                if addr in ipaddress.ip_network("192.168.2.0/24"):
                    allowed = True
            except (ValueError, TypeError):
                pass
        if allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _json_response(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, status: HTTPStatus, detail: str) -> None:
        self._json_response({"ok": False, "error": detail}, status=status)


class WatercoolerServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: Tuple[str, int], handler_cls: type[BaseHTTPRequestHandler], state: Dict[str, Any]):
        super().__init__(address, handler_cls)
        self.state = state


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tiny LAN-only AI watercooler + OpenCLAW v0 service.")
    parser.add_argument("--host", type=str, default=os.environ.get("AI_WATERCOOLER_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("AI_WATERCOOLER_PORT", "8765")))
    parser.add_argument(
        "--db-path",
        type=str,
        default=os.environ.get("AI_WATERCOOLER_DB_PATH", "/var/lib/ai-watercooler/messages.db"),
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("AI_WATERCOOLER_ADMIN_TOKEN", os.environ.get("AI_WATERCOOLER_TOKEN", "")),
        help="Bootstrap admin token used only for minting and revoking session tokens.",
    )
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = build_arg_parser().parse_args()
    if not args.token:
        raise SystemExit("AI_WATERCOOLER_ADMIN_TOKEN / AI_WATERCOOLER_TOKEN / --token is required")

    db_path = Path(args.db_path).expanduser()
    ensure_db(db_path)
    state = {
        "db_path": str(db_path),
        "admin_token": args.token,
    }
    server = WatercoolerServer((args.host, args.port), WatercoolerHandler, state=state)
    LOGGER.info("openclaw-v0 listening on %s:%d db=%s", args.host, args.port, db_path)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("shutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
