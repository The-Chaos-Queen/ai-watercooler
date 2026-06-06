from __future__ import annotations

import json
import sqlite3
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from watercooler_service import (  # noqa: E402
    SESSION_SCOPES,
    WatercoolerHandler,
    WatercoolerServer,
    ensure_db,
    hash_token,
    utc_after,
    utc_now,
)


@pytest.fixture()
def watercooler(tmp_path):
    db_path = tmp_path / "messages.db"
    ensure_db(db_path)
    tokens = {"techno-monk": "token-techno", "vesper": "token-vesper"}
    now = utc_now()
    with sqlite3.connect(db_path) as conn:
        for principal, token in tokens.items():
            conn.execute(
                """
                INSERT INTO auth_tokens (
                    created_ts, updated_ts, issued_by, principal, session_id,
                    token_hash, scopes_json, expires_ts, revoked_ts, note
                ) VALUES (?, ?, 'test', ?, ?, ?, ?, ?, '', '')
                """,
                (
                    now,
                    now,
                    principal,
                    f"{principal}-test",
                    hash_token(token),
                    json.dumps(list(SESSION_SCOPES)),
                    utc_after(3600),
                ),
            )
        conn.commit()

    server = WatercoolerServer(("127.0.0.1", 0), WatercoolerHandler, state={"db_path": str(db_path), "admin_token": "admin"})
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield base_url, tokens, db_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request_json(base_url: str, token: str, method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url + path,
        data=data,
        method=method,
        headers={"X-Watercooler-Token": token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def request_error(base_url: str, token: str, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        request_json(base_url, token, method, path, payload)
    err = exc_info.value
    return err.code, json.loads(err.read().decode("utf-8"))


def create_task(base_url: str, token: str, **overrides) -> dict:
    payload = {
        "project": "MoCoP",
        "thread": "mamba-bridge",
        "title": "test task",
        "description": "test",
        "assignee": "",
    }
    payload.update(overrides)
    return request_json(base_url, token, "POST", "/v1/tasks", payload)["task"]


def event_types(db_path: Path, task_id: int) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        return [row[0] for row in conn.execute("SELECT event_type FROM task_events WHERE task_id = ? ORDER BY id", (task_id,))]


def test_agent_payload_mismatch_is_rejected_for_claim(watercooler):
    base_url, tokens, _db_path = watercooler
    task = create_task(base_url, tokens["techno-monk"], assignee="vesper")

    code, body = request_error(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/claim",
        {"task_id": task["id"], "agent": "vesper", "note": "bad impersonation attempt"},
    )

    assert code == 403
    assert "cannot act as vesper" in body["error"]


def test_reassign_clears_bad_claim_and_audits_event(watercooler):
    base_url, tokens, db_path = watercooler
    task = create_task(base_url, tokens["techno-monk"])
    claimed = request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/claim",
        {"task_id": task["id"], "agent": "techno-monk", "note": "claim before reroute"},
    )["task"]
    assert claimed["status"] == "claimed"
    assert claimed["claim_agent"] == "techno-monk"

    reassigned = request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/reassign",
        {"task_id": task["id"], "agent": "techno-monk", "assignee": "vesper", "note": "route to Vesper"},
    )["task"]

    assert reassigned["status"] == "queued"
    assert reassigned["assignee"] == "vesper"
    assert reassigned["claim_agent"] == ""
    assert "reassigned" in event_types(db_path, task["id"])


def test_release_unblock_and_comment_lifecycle(watercooler):
    base_url, tokens, db_path = watercooler
    task = create_task(base_url, tokens["techno-monk"])

    request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/claim",
        {"task_id": task["id"], "agent": "techno-monk"},
    )
    released = request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/release",
        {"task_id": task["id"], "agent": "techno-monk", "note": "wrong claim"},
    )["task"]
    assert released["status"] == "queued"
    assert released["claim_agent"] == ""

    request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/comment",
        {"task_id": task["id"], "agent": "techno-monk", "note": "plain note"},
    )
    after_comment = request_json(base_url, tokens["techno-monk"], "GET", f"/v1/tasks?task_id={task['id']}")["tasks"][0]
    assert after_comment["status"] == "queued"

    blocked = request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/block",
        {"task_id": task["id"], "agent": "techno-monk", "blocked_reason": "test blocker"},
    )["task"]
    assert blocked["status"] == "blocked"
    assert blocked["blocked_reason"] == "test blocker"

    unblocked = request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/unblock",
        {"task_id": task["id"], "agent": "techno-monk", "note": "blocker resolved"},
    )["task"]
    assert unblocked["status"] == "queued"
    assert unblocked["blocked_reason"] == ""

    events = event_types(db_path, task["id"])
    assert "released" in events
    assert "comment" in events
    assert "unblocked" in events
