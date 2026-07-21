from __future__ import annotations

import json
import sqlite3
import threading
import urllib.error
import urllib.request

import pytest

from watercooler.service import (
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
    tokens = {
        "writer": ("token-writer", ["messages:read", "messages:write", "tasks:read", "tasks:write"]),
        "steward": (
            "token-steward",
            ["messages:read", "tasks:read", "summaries:publish"],
        ),
    }
    now = utc_now()
    with sqlite3.connect(db_path) as conn:
        for principal, (token, scopes) in tokens.items():
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
                    json.dumps(scopes),
                    utc_after(3600),
                ),
            )
        conn.commit()

    server = WatercoolerServer(
        ("127.0.0.1", 0),
        WatercoolerHandler,
        state={"db_path": str(db_path), "admin_token": "admin"},
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield base_url, {name: value[0] for name, value in tokens.items()}, db_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request_json(
    base_url: str,
    token: str,
    method: str,
    path: str,
    payload: dict | None = None,
) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def request_error(
    base_url: str,
    token: str,
    method: str,
    path: str,
    payload: dict | None = None,
) -> tuple[int, dict]:
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        request_json(base_url, token, method, path, payload)
    error = exc_info.value
    return error.code, json.loads(error.read().decode("utf-8"))


def post_message(base_url: str, token: str, body: str) -> int:
    response = request_json(
        base_url,
        token,
        "POST",
        "/v1/post",
        {
            "to_agent": "all",
            "thread": "demo",
            "topic": "demo",
            "lang": "en",
            "body": body,
            "tags": [],
        },
    )
    return int(response["id"])


def create_task(base_url: str, token: str, title: str = "Review dispatcher") -> dict:
    return request_json(
        base_url,
        token,
        "POST",
        "/v1/tasks",
        {
            "project": "demo",
            "thread": "demo",
            "title": title,
            "description": "Synthetic demo task",
        },
    )["task"]


def draft_for(workset: dict, *, source_id: int | None = None) -> dict:
    message_ids = workset["batch_message_ids"]
    chosen_source = source_id if source_id is not None else message_ids[0]
    return {
        "schema_version": "watercooler.summary-draft.v1",
        "title": "Current orientation",
        "sections": [
            {
                "kind": "orientation",
                "items": [
                    {
                        "text": "The dispatcher documentation needs an owner.",
                        "source_message_ids": [chosen_source],
                    }
                ],
            }
        ],
        "task_proposals": [
            {
                "title": "Document dispatcher installation",
                "description": "Write a reproducible local installation guide.",
                "source_message_ids": [chosen_source],
            }
        ],
    }


def publish_payload(workset: dict, draft: dict) -> dict:
    return {
        "thread": workset["thread"],
        "expected_parent_revision_id": workset["base_revision_id"],
        "expected_task_event_head_id": workset["task_event_head_id"],
        "expected_task_snapshot_sha256": workset["task_snapshot_sha256"],
        "coverage_through_message_id": workset["batch_through_message_id"],
        "batch_message_ids": workset["batch_message_ids"],
        "workset_sha256": workset["workset_sha256"],
        "generator": {"model_id": "gemma-test", "prompt_sha256": "a" * 64},
        "draft": draft,
    }


def prepare_demo(base_url: str, writer_token: str) -> list[int]:
    create_task(base_url, writer_token)
    return [post_message(base_url, writer_token, f"Synthetic message {index}") for index in range(1, 7)]


def test_steward_publish_and_onboarding_are_grounded(watercooler):
    base_url, tokens, db_path = watercooler
    message_ids = prepare_demo(base_url, tokens["writer"])
    workset = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")

    assert workset["batch_message_ids"] == message_ids
    assert workset["base_revision_id"] == 0
    assert workset["task_snapshot"]["counts"]["queued"] == 1

    published = request_json(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary/publish",
        publish_payload(workset, draft_for(workset)),
    )["summary"]

    assert published["revision_id"] == 1
    assert published["kind"] == "steward"
    assert published["coverage_through_message_id"] == message_ids[-1]
    assert "Proposal only" in published["body"]

    compatibility = request_json(base_url, tokens["steward"], "GET", "/v1/summary?thread=demo")
    assert compatibility["summary"] == published["body"]
    assert compatibility["revision_id"] == published["revision_id"]

    onboarding = request_json(base_url, tokens["steward"], "GET", "/v1/onboarding?thread=demo&recent_limit=5")
    assert onboarding["summary"]["revision_id"] == published["revision_id"]
    assert [message["id"] for message in onboarding["recent_messages"]] == message_ids[-5:]
    assert onboarding["authoritative_taskboard"]["counts"]["queued"] == 1
    assert onboarding["delta"] == {
        "coverage_known": True,
        "uncovered_message_count": 0,
        "returned_uncovered_count": 0,
        "complete": True,
    }
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM summary_message_sources").fetchone()[0] == 2


def test_new_messages_do_not_invalidate_an_inflight_workset(watercooler):
    base_url, tokens, _db_path = watercooler
    prepare_demo(base_url, tokens["writer"])
    workset = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")
    late_message_id = post_message(base_url, tokens["writer"], "Arrived during generation")

    request_json(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary/publish",
        publish_payload(workset, draft_for(workset)),
    )
    onboarding = request_json(base_url, tokens["steward"], "GET", "/v1/onboarding?thread=demo&recent_limit=5")

    assert onboarding["delta"]["uncovered_message_count"] == 1
    assert onboarding["delta"]["returned_uncovered_count"] == 1
    assert onboarding["delta"]["complete"] is True
    assert onboarding["recent_messages"][-1]["id"] == late_message_id


def test_task_change_and_stale_parent_fail_closed(watercooler):
    base_url, tokens, _db_path = watercooler
    prepare_demo(base_url, tokens["writer"])
    workset = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")
    create_task(base_url, tokens["writer"], title="A second task")

    code, body = request_error(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary/publish",
        publish_payload(workset, draft_for(workset)),
    )
    assert code == 409
    assert "Taskboard" in body["error"] or "workset" in body["error"]

    fresh = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")
    payload = publish_payload(fresh, draft_for(fresh))
    request_json(base_url, tokens["steward"], "POST", "/v1/summary/publish", payload)
    code, body = request_error(base_url, tokens["steward"], "POST", "/v1/summary/publish", payload)
    assert code == 409
    assert "parent revision changed" in body["error"]


def test_publish_refuses_proposal_that_duplicates_existing_task(watercooler):
    base_url, tokens, _db_path = watercooler
    message_id = post_message(base_url, tokens["writer"], "Keep the dispatcher review visible.")
    create_task(base_url, tokens["writer"], title="Review dispatcher")
    workset = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")
    draft = draft_for(workset, source_id=message_id)
    draft["task_proposals"][0]["title"] = "  REVIEW dispatcher "

    code, body = request_error(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary/publish",
        publish_payload(workset, draft),
    )

    assert code == 400
    assert "duplicates an existing Taskboard task" in body["error"]


def test_hallucinated_source_is_rejected_without_publication(watercooler):
    base_url, tokens, db_path = watercooler
    prepare_demo(base_url, tokens["writer"])
    workset = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")

    code, body = request_error(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary/publish",
        publish_payload(workset, draft_for(workset, source_id=999_999)),
    )
    assert code == 400
    assert "allowed source" in body["error"]
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM summary_revisions").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM summary_heads").fetchone()[0] == 0


def test_steward_scope_cannot_post_messages_or_mutate_tasks(watercooler):
    base_url, tokens, _db_path = watercooler
    task = create_task(base_url, tokens["writer"])

    code, _body = request_error(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/post",
        {"thread": "demo", "body": "not allowed", "lang": "en"},
    )
    assert code == 403
    code, _body = request_error(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/tasks/claim",
        {"task_id": task["id"], "agent": "steward"},
    )
    assert code == 403


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_parent_revision_id", 0.9),
        ("expected_task_event_head_id", 1.9),
        ("coverage_through_message_id", 6.1),
        ("generator.model_id", 123),
    ],
)
def test_publish_receipts_require_exact_json_types(watercooler, field, value):
    base_url, tokens, db_path = watercooler
    prepare_demo(base_url, tokens["writer"])
    workset = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")
    payload = publish_payload(workset, draft_for(workset))
    if field == "generator.model_id":
        payload["generator"]["model_id"] = value
    else:
        payload[field] = value

    code, _body = request_error(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary/publish",
        payload,
    )
    assert code == 400
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM summary_revisions").fetchone()[0] == 0


def test_recent_done_is_ordered_by_completion_time_not_task_id(watercooler):
    base_url, tokens, db_path = watercooler
    first = create_task(base_url, tokens["writer"], title="Completed later")
    second = create_task(base_url, tokens["writer"], title="Completed earlier")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET status='done', completed_ts='2026-07-18T12:00:00Z' WHERE id=?",
            (first["id"],),
        )
        conn.execute(
            "UPDATE tasks SET status='done', completed_ts='2026-07-18T11:00:00Z' WHERE id=?",
            (second["id"],),
        )
        conn.commit()

    onboarding = request_json(base_url, tokens["steward"], "GET", "/v1/onboarding?thread=demo")
    assert [task["id"] for task in onboarding["authoritative_taskboard"]["recent_done"]] == [
        first["id"],
        second["id"],
    ]


def test_workset_suppresses_proposals_for_tasks_older_than_recent_done_window(watercooler):
    base_url, tokens, db_path = watercooler
    tasks = [
        create_task(base_url, tokens["writer"], title=f"Completed task {index}")
        for index in range(6)
    ]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET status='done', completed_ts='2026-07-18T12:00:00Z'"
        )
        conn.commit()

    workset = request_json(
        base_url,
        tokens["steward"],
        "GET",
        "/v1/summary/workset?thread=demo",
    )

    assert len(workset["task_snapshot"]["recent_done"]) == 5
    assert workset["task_snapshot"]["proposal_suppression_titles"] == [
        task["title"] for task in tasks
    ]


def test_publish_accepts_a_valid_draft_larger_than_generic_request_limit(watercooler):
    base_url, tokens, _db_path = watercooler
    message_id = post_message(base_url, tokens["writer"], "One grounded source message")
    workset = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")
    sections = []
    for kind in ("overview", "decision", "hold", "open_question", "orientation"):
        sections.append(
            {
                "kind": kind,
                "items": [
                    {
                        "text": f"{kind} {index} " + "x" * 480,
                        "source_message_ids": [message_id],
                    }
                    for index in range(25)
                ],
            }
        )
    draft = {
        "schema_version": "watercooler.summary-draft.v1",
        "title": "Large but contract-valid summary",
        "sections": sections,
        "task_proposals": [],
    }
    payload = publish_payload(workset, draft)
    assert len(json.dumps(payload).encode("utf-8")) > 64 * 1024

    published = request_json(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary/publish",
        payload,
    )["summary"]
    assert published["coverage_through_message_id"] == message_id


def test_manual_summary_requires_publish_scope_and_has_unknown_initial_coverage(watercooler):
    base_url, tokens, _db_path = watercooler
    code, body = request_error(
        base_url,
        tokens["writer"],
        "POST",
        "/v1/summary",
        {"thread": "demo", "body": "writer must not replace orientation"},
    )
    assert code == 403
    assert "summaries:publish" in body["error"]

    result = request_json(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary",
        {"thread": "demo", "body": "<img src=x onerror=alert(1)>"},
    )
    assert result["revision_id"] == 1

    onboarding = request_json(base_url, tokens["steward"], "GET", "/v1/onboarding?thread=demo")
    assert onboarding["summary"]["kind"] == "manual"
    assert onboarding["summary"]["content"] is None
    assert onboarding["summary"]["coverage_known"] is False
    assert onboarding["summary"]["body"] == "<img src=x onerror=alert(1)>"
    assert onboarding["delta"]["complete"] is False


def test_manual_summary_after_steward_resets_coverage_and_rebuilds_from_raw_messages(watercooler):
    base_url, tokens, _db_path = watercooler
    message_ids = prepare_demo(base_url, tokens["writer"])
    workset = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")
    request_json(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary/publish",
        publish_payload(workset, draft_for(workset)),
    )

    manual = request_json(
        base_url,
        tokens["steward"],
        "POST",
        "/v1/summary",
        {"thread": "demo", "body": "Human correction without machine-readable citations."},
    )
    onboarding = request_json(base_url, tokens["steward"], "GET", "/v1/onboarding?thread=demo")
    rebuild = request_json(base_url, tokens["steward"], "GET", "/v1/summary/workset?thread=demo")

    assert manual["revision_id"] == 2
    assert onboarding["summary"]["coverage_known"] is False
    assert onboarding["summary"]["coverage_through_message_id"] == 0
    assert onboarding["delta"]["uncovered_message_count"] == len(message_ids)
    assert rebuild["base_revision_id"] == 2
    assert rebuild["base_message_coverage_id"] == 0
    assert rebuild["batch_message_ids"] == message_ids
    assert rebuild["parent_source_message_ids"] == []
    assert rebuild["previous_content"] is None
