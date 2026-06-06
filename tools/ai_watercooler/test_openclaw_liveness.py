from __future__ import annotations

import json
import sqlite3
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from watercooler_service import (  # noqa: E402
    SESSION_SCOPES,
    WatercoolerHandler,
    WatercoolerServer,
    classify_blocked_task_signals,
    ensure_db,
    hash_token,
    median,
    percentile,
    seconds_between_iso,
    utc_after,
    utc_now,
)


@pytest.fixture()
def watercooler(tmp_path):
    db_path = tmp_path / "messages.db"
    ensure_db(db_path)
    tokens = {"techno-monk": "token-techno", "readonly": "token-readonly"}
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


def set_task_blocked_at(db_path: Path, task_id: int, *, blocked_ts: str, last_event_ts: str | None = None) -> None:
    last_event_ts = last_event_ts or blocked_ts
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET updated_ts = ?, status = 'blocked' WHERE id = ?", (blocked_ts, task_id))
        conn.execute(
            "UPDATE task_events SET ts = ? WHERE task_id = ? AND event_type = 'blocked'",
            (blocked_ts, task_id),
        )
        conn.execute(
            """
            INSERT INTO task_events (task_id, ts, actor, event_type, note, details_json)
            VALUES (?, ?, 'test', 'comment', 'old review note', '{}')
            """,
            (task_id, last_event_ts),
        )
        conn.commit()


def test_seconds_between_iso_handles_zulu_timestamps():
    assert seconds_between_iso("2026-05-01T00:00:00Z", "2026-05-03T12:00:00Z") == 216000


def test_percentile_handles_empty_singleton_and_nearest_rank():
    assert percentile([], 0.5) == 0.0
    assert percentile([7.0], 0.95) == 7.0
    assert percentile([1.0, 2.0, 10.0], 0.5) == 2.0
    assert percentile([1.0, 2.0, 10.0], 0.95) == 10.0


def test_median_uses_conventional_even_average():
    assert median([]) == 0.0
    assert median([89.0, 1.0]) == 45.0
    assert median([1.0, 2.0, 10.0]) == 2.0


def test_classify_blocked_task_signals_detects_zombie_language():
    task = {
        "id": 77,
        "title": "umbrella sleep card",
        "description": "work moved elsewhere",
        "blocked_reason": "umbrella task superseded by #78-#85; use live branch #78-#82",
        "refs": [],
        "artifacts": [],
    }
    signals = classify_blocked_task_signals(task, blocked_age_days=60.0, last_event_age_days=60.0, done_ids={78, 79})
    assert "very_stale_block" in signals
    assert "no_recent_review" in signals
    assert "mentions_superseded" in signals
    assert "mentions_done_task" in signals


def test_liveness_endpoint_reports_blocked_age_and_signals(watercooler):
    base_url, tokens, db_path = watercooler
    stale = create_task(
        base_url,
        tokens["techno-monk"],
        title="superseded umbrella",
        description="decomposed into #2",
        labels=["sleep"],
        refs=["gate:#304"],
    )
    done = create_task(base_url, tokens["techno-monk"], title="replacement slice", description="done replacement")
    fresh = create_task(base_url, tokens["techno-monk"], title="fresh ethics gate", description="waiting for QC")

    request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/complete",
        {"task_id": done["id"], "agent": "techno-monk", "note": "done"},
    )
    request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/block",
        {"task_id": stale["id"], "agent": "techno-monk", "blocked_reason": f"superseded by #{done['id']}"},
    )
    request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/block",
        {"task_id": fresh["id"], "agent": "techno-monk", "blocked_reason": "waiting for QC gate"},
    )
    set_task_blocked_at(db_path, stale["id"], blocked_ts="2026-03-01T00:00:00Z", last_event_ts="2026-03-15T00:00:00Z")
    set_task_blocked_at(db_path, fresh["id"], blocked_ts="2026-05-28T00:00:00Z", last_event_ts="2026-05-28T00:00:00Z")

    report = request_json(
        base_url,
        tokens["techno-monk"],
        "GET",
        "/v1/tasks/liveness?" + urllib.parse.urlencode({"project": "MoCoP", "now": "2026-05-29T00:00:00Z"}),
    )

    assert report["project"] == "MoCoP"
    assert report["counts"]["blocked"] == 2
    assert report["blocked"]["count"] == 2
    assert report["blocked"]["oldest_age_days"] == 89.0
    assert report["blocked"]["median_age_days"] == 45.0
    assert report["blocked"]["p95_age_days"] == 89.0
    item = report["blocked"]["items"][0]
    assert item["id"] == stale["id"]
    assert item["blocked_since"] == "2026-03-01T00:00:00Z"
    assert item["blocked_age_days"] == 89.0
    assert item["last_event_ts"] == "2026-03-15T00:00:00Z"
    assert item["last_event_age_days"] == 75.0
    assert item["recommended_review"] is True
    assert "very_stale_block" in item["signals"]
    assert "mentions_done_task" in item["signals"]


def test_liveness_endpoint_requires_tasks_read_auth(watercooler):
    base_url, _tokens, _db_path = watercooler
    code, body = request_error(base_url, "not-a-real-token", "GET", "/v1/tasks/liveness?project=MoCoP")
    assert code in (401, 403)
    assert body["ok"] is False
