from __future__ import annotations

import concurrent.futures
import json
import sqlite3
import subprocess
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


def test_reopen_done_task_preserves_completion_history_and_artifacts(watercooler):
    base_url, tokens, db_path = watercooler
    task = create_task(base_url, tokens["techno-monk"])

    code, body = request_error(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/reopen",
        {"task_id": task["id"], "agent": "techno-monk", "note": "not done yet"},
    )
    assert code == 409
    assert body["error"] == "task is not done"

    completed = request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/complete",
        {
            "task_id": task["id"],
            "agent": "techno-monk",
            "note": "completed receipt",
            "artifacts": ["commit:abc123"],
        },
    )["task"]
    assert completed["status"] == "done"
    assert completed["assignee"] == "techno-monk"
    assert completed["completed_ts"]
    assert completed["artifacts"] == ["commit:abc123"]

    code, body = request_error(
        base_url,
        tokens["vesper"],
        "POST",
        "/v1/tasks/reopen",
        {"task_id": task["id"], "agent": "techno-monk", "note": "bad impersonation attempt"},
    )
    assert code == 403
    assert "cannot act as techno-monk" in body["error"]
    still_done = request_json(
        base_url,
        tokens["techno-monk"],
        "GET",
        f"/v1/tasks?task_id={task['id']}",
    )["tasks"][0]
    assert still_done["status"] == "done"

    reopened = request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/reopen",
        {"task_id": task["id"], "agent": "techno-monk", "note": "late source finding needs a repair pass"},
    )["task"]
    assert reopened["status"] == "queued"
    assert reopened["assignee"] == "techno-monk"
    assert reopened["claim_agent"] == ""
    assert reopened["claim_ts"] == ""
    assert reopened["last_heartbeat_ts"] == ""
    assert reopened["lease_expires_ts"] == ""
    assert reopened["blocked_reason"] == ""
    assert reopened["completed_ts"] == ""
    assert reopened["artifacts"] == ["commit:abc123"]
    assert event_types(db_path, task["id"])[-2:] == ["completed", "reopened"]
    context = request_json(
        base_url,
        tokens["techno-monk"],
        "GET",
        f"/v1/context?task_id={task['id']}",
    )
    reopened_event = context["events"][0]
    assert reopened_event["event_type"] == "reopened"
    assert reopened_event["actor"] == "techno-monk"
    assert reopened_event["note"] == "late source finding needs a repair pass"
    assert reopened_event["details"] == {
        "old_completed_ts": completed["completed_ts"],
        "artifacts": ["commit:abc123"],
    }

    code, body = request_error(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/reopen",
        {"task_id": task["id"], "agent": "techno-monk", "note": "repeat reopen"},
    )
    assert code == 409
    assert body["error"] == "task is not done"
    assert event_types(db_path, task["id"])[-2:] == ["completed", "reopened"]


def test_reopen_allows_audited_cross_owner_repair_without_reassignment(watercooler):
    base_url, tokens, _db_path = watercooler
    task = create_task(base_url, tokens["techno-monk"])
    request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/complete",
        {"task_id": task["id"], "agent": "techno-monk", "note": "completed by owner"},
    )

    reopened = request_json(
        base_url,
        tokens["vesper"],
        "POST",
        "/v1/tasks/reopen",
        {"task_id": task["id"], "agent": "vesper", "note": "keeper repair after new evidence"},
    )["task"]

    assert reopened["status"] == "queued"
    assert reopened["assignee"] == "techno-monk"
    assert reopened["claim_agent"] == ""
    context = request_json(
        base_url,
        tokens["vesper"],
        "GET",
        f"/v1/context?task_id={task['id']}",
    )
    assert context["events"][0]["event_type"] == "reopened"
    assert context["events"][0]["actor"] == "vesper"
    assert context["events"][0]["note"] == "keeper repair after new evidence"


def test_reopen_is_atomic_under_concurrent_requests(watercooler):
    base_url, tokens, db_path = watercooler
    task = create_task(base_url, tokens["techno-monk"])
    request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/complete",
        {"task_id": task["id"], "agent": "techno-monk", "note": "completion before race"},
    )
    start = threading.Barrier(3)

    def reopen_once() -> tuple[str, int, str]:
        start.wait(timeout=5)
        try:
            response = request_json(
                base_url,
                tokens["techno-monk"],
                "POST",
                "/v1/tasks/reopen",
                {"task_id": task["id"], "agent": "techno-monk", "note": "concurrent repair"},
            )
            return "ok", 200, response["task"]["status"]
        except urllib.error.HTTPError as exc:
            body = json.loads(exc.read().decode("utf-8"))
            return "error", exc.code, body["error"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(reopen_once) for _ in range(2)]
        start.wait(timeout=5)
        outcomes = [future.result(timeout=10) for future in futures]

    assert outcomes.count(("ok", 200, "queued")) == 1
    assert outcomes.count(("error", 409, "task is not done")) == 1
    assert event_types(db_path, task["id"])[-2:] == ["completed", "reopened"]


@pytest.mark.parametrize("script_name", ["taskboard.py", "openclaw.py"])
def test_taskboard_and_openclaw_cli_reopen_hit_local_http_service(watercooler, tmp_path, script_name):
    base_url, tokens, db_path = watercooler
    task = create_task(base_url, tokens["techno-monk"])
    request_json(
        base_url,
        tokens["techno-monk"],
        "POST",
        "/v1/tasks/complete",
        {
            "task_id": task["id"],
            "agent": "techno-monk",
            "note": "initial completion",
            "artifacts": ["commit:def456"],
        },
    )
    config_path = tmp_path / "taskboard-cli.json"
    config_path.write_text(
        json.dumps({"base_url": base_url, "token": tokens["techno-monk"], "principal": "techno-monk"}),
        encoding="utf-8",
    )
    script = Path(__file__).with_name(script_name)

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--config",
            str(config_path),
            "reopen",
            "--task-id",
            str(task["id"]),
            "--note",
            "actual CLI smoke",
            "--json",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["task"]["status"] == "queued"
    assert event_types(db_path, task["id"])[-2:] == ["completed", "reopened"]
    if script_name == "openclaw.py":
        assert "DeprecationWarning: openclaw.py is deprecated; use taskboard.py" in result.stderr
