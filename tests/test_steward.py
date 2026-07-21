from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from watercooler import steward


def sample_workset() -> dict[str, Any]:
    return {
        "schema_version": "watercooler.summary-workset.v1",
        "thread": "demo",
        "base_revision_id": 7,
        "base_message_coverage_id": 100,
        "batch_through_message_id": 103,
        "batch_message_ids": [101, 102, 103],
        "task_event_head_id": 19,
        "task_snapshot_sha256": "b" * 64,
        "task_snapshot": {
            "counts": {"queued": 1},
            "open_tasks": [],
            "recent_done": [],
            "proposal_suppression_titles": [],
        },
        "previous_content": None,
        "parent_source_message_ids": [95, 96],
        "messages": [
            {
                "id": 101,
                "body": "Dispatcher documentation needs an owner.",
            },
            {"id": 102, "body": "The local model is ready."},
            {"id": 103, "body": "Keep publication human-authorized."},
        ],
        "workset_sha256": "c" * 64,
        "more_messages": False,
    }


def sample_draft(source_id: int = 101) -> dict[str, Any]:
    return {
        "schema_version": "watercooler.summary-draft.v1",
        "title": "Current orientation",
        "sections": [
            {
                "kind": "orientation",
                "items": [
                    {
                        "text": "The dispatcher documentation needs an owner.",
                        "source_message_ids": [source_id],
                    }
                ],
            }
        ],
        "task_proposals": [
            {
                "title": "Document dispatcher installation",
                "description": "Write a reproducible local installation guide.",
                "source_message_ids": [source_id],
            }
        ],
    }


def sample_model_draft(source_id: int = 101) -> dict[str, Any]:
    canonical = sample_draft(source_id)
    sections = {
        "overview": [],
        "decision": [],
        "hold": [],
        "open_question": [],
        "orientation": [],
    }
    for section in canonical["sections"]:
        sections[section["kind"]] = section["items"]
    return {
        "schema_version": canonical["schema_version"],
        "title": canonical["title"],
        "sections": sections,
        "task_proposals": canonical["task_proposals"],
    }


class FakeResponse:
    def __init__(self, payload: dict[str, Any], url: str) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self._url = url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]

    def geturl(self) -> str:
        return self._url


def model_response(draft: dict[str, Any]) -> dict[str, Any]:
    return {"choices": [{"message": {"content": json.dumps(draft)}}]}


def install_model_mock(monkeypatch: pytest.MonkeyPatch, draft: dict[str, Any]) -> list[dict]:
    requests: list[dict] = []

    class FakeOpener:
        def open(self, request, *, timeout):
            request_body = json.loads(request.data.decode("utf-8"))
            requests.append(
                {
                    "url": request.full_url,
                    "headers": dict(request.header_items()),
                    "timeout": timeout,
                    "body": request_body,
                }
            )
            return FakeResponse(model_response(draft), request.full_url)

    monkeypatch.setattr(steward, "build_direct_http_opener", lambda: FakeOpener())
    return requests


def test_prompt_is_deterministic_for_equivalent_worksets() -> None:
    workset = sample_workset()
    reordered = {key: workset[key] for key in reversed(workset)}

    first_messages, first_sha = steward.build_prompt(workset)
    second_messages, second_sha = steward.build_prompt(reordered)

    assert first_messages == second_messages
    assert first_sha == second_sha
    assert first_sha == hashlib.sha256(steward.canonical_json(first_messages).encode()).hexdigest()
    assert first_messages[1]["content"].endswith(
        steward.canonical_json(steward.build_model_workset(workset))
    )


def test_model_workset_exposes_only_task_titles_for_proposal_suppression() -> None:
    workset = sample_workset()
    workset["task_snapshot"]["open_tasks"] = [
        {
            "id": 12,
            "title": "Review credential rotation",
            "description": "Sensitive implementation detail",
            "status": "queued",
        }
    ]
    workset["task_snapshot"]["proposal_suppression_titles"] = [
        "Review credential rotation"
    ]

    model_workset = steward.build_model_workset(workset)
    encoded = steward.canonical_json(model_workset)

    assert model_workset["proposal_suppression_titles"] == ["Review credential rotation"]
    assert "task_snapshot" not in model_workset
    assert "task_snapshot_sha256" not in model_workset
    assert "task_event_head_id" not in model_workset
    assert "more_messages" not in model_workset
    assert "Sensitive implementation detail" not in encoded
    assert '"id":12' not in encoded


def test_non_loopback_endpoint_requires_explicit_opt_in() -> None:
    with pytest.raises(steward.StewardError, match="non-loopback"):
        steward.normalize_model_endpoint(
            "https://models.example.test/v1",
            allow_remote_model=False,
        )

    assert (
        steward.normalize_model_endpoint(
            "https://models.example.test/v1/",
            allow_remote_model=True,
        )
        == "https://models.example.test/v1"
    )
    assert (
        steward.normalize_model_endpoint(
            "http://127.12.34.56:1234/v1/",
            allow_remote_model=False,
        )
        == "http://127.12.34.56:1234/v1"
    )


def test_model_transport_refuses_redirect_before_sending_prompt_to_target() -> None:
    target_hits = 0

    class TargetHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal target_hits
            target_hits += 1
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_POST = do_GET

        def log_message(self, _format, *_args):
            return

    target = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(302)
            self.send_header(
                "Location",
                f"http://127.0.0.1:{target.server_port}/stolen",
            )
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, _format, *_args):
            return

    source = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    threads = [
        threading.Thread(target=server.serve_forever, daemon=True)
        for server in (target, source)
    ]
    for thread in threads:
        thread.start()
    try:
        with pytest.raises(steward.StewardError, match="HTTP 302"):
            steward.call_chat_completions(
                endpoint=f"http://127.0.0.1:{source.server_port}/v1",
                model="local",
                messages=[{"role": "user", "content": "private prompt"}],
                timeout=5,
                max_tokens=10,
                allowed_source_ids={1},
            )
    finally:
        for server in (source, target):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)

    assert target_hits == 0


def test_model_transport_bounds_success_and_error_bodies(monkeypatch) -> None:
    success_reads: list[int] = []

    class OversizedResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def geturl(self):
            return "http://127.0.0.1:1234/v1/chat/completions"

        def read(self, size=-1):
            success_reads.append(size)
            return b"x" * size

    class SuccessOpener:
        def open(self, _request, *, timeout):
            assert timeout == 5
            return OversizedResponse()

    monkeypatch.setattr(steward, "build_direct_http_opener", lambda: SuccessOpener())
    kwargs = {
        "endpoint": "http://127.0.0.1:1234/v1",
        "model": "local",
        "messages": [{"role": "user", "content": "prompt"}],
        "timeout": 5,
        "max_tokens": 10,
        "allowed_source_ids": {1},
    }
    with pytest.raises(steward.StewardError, match="byte limit"):
        steward.call_chat_completions(**kwargs)
    assert success_reads == [steward.MAX_MODEL_RESPONSE_BYTES + 1]

    error_reads: list[int] = []

    class ErrorBody(io.BytesIO):
        def read(self, size=-1):
            error_reads.append(size)
            return super().read(size)

    failure = urllib.error.HTTPError(
        kwargs["endpoint"],
        500,
        "failure",
        {},
        ErrorBody(b"e" * (steward.MAX_MODEL_ERROR_BYTES + 100)),
    )

    class ErrorOpener:
        def open(self, _request, *, timeout):
            raise failure

    monkeypatch.setattr(steward, "build_direct_http_opener", lambda: ErrorOpener())
    with pytest.raises(steward.StewardError, match="HTTP 500"):
        steward.call_chat_completions(**kwargs)
    assert error_reads == [steward.MAX_MODEL_ERROR_BYTES + 1]


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf"])
def test_timeout_must_be_positive_and_finite(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        steward._positive_float(value)


@pytest.mark.parametrize(
    "content",
    [
        "```json\n{}\n```",
        '{"first": 1} {"second": 2}',
        "[]",
        "not JSON",
    ],
)
def test_model_content_refuses_fences_malformed_or_non_object_json(content: str) -> None:
    with pytest.raises(steward.StewardError, match="exactly one"):
        steward.parse_json_object(content, label="model message content")


def test_model_draft_citations_must_come_from_parent_or_batch() -> None:
    workset = sample_workset()
    parent_citation = steward.validate_model_draft(json.dumps(sample_model_draft(95)), workset)
    batch_citation = steward.validate_model_draft(json.dumps(sample_model_draft(103)), workset)

    assert parent_citation["sections"][0]["items"][0]["source_message_ids"] == [95]
    assert batch_citation["sections"][0]["items"][0]["source_message_ids"] == [103]

    with pytest.raises(steward.StewardError, match="allowed source message"):
        steward.validate_model_draft(json.dumps(sample_model_draft(999)), workset)


def test_model_draft_refuses_proposal_that_duplicates_taskboard_title() -> None:
    workset = sample_workset()
    workset["task_snapshot"]["open_tasks"] = [
        {"id": 12, "title": "  DOCUMENT dispatcher installation  "}
    ]
    workset["task_snapshot"]["proposal_suppression_titles"] = [
        "  DOCUMENT dispatcher installation  "
    ]

    with pytest.raises(steward.StewardError, match="duplicates an existing Taskboard task"):
        steward.validate_model_draft(json.dumps(sample_model_draft()), workset)


def test_dry_run_renders_summary_without_publishing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workset = sample_workset()
    watercooler_calls: list[dict] = []

    monkeypatch.setattr(
        steward,
        "load_config",
        lambda _path: {"base_url": "http://watercooler.test", "token": "wc-secret"},
    )

    def fake_request_json(config, *, method, path, payload=None, query=None):
        watercooler_calls.append(
            {
                "config": config,
                "method": method,
                "path": path,
                "payload": payload,
                "query": query,
            }
        )
        assert method == "GET"
        return copy.deepcopy(workset)

    monkeypatch.setattr(steward, "request_json", fake_request_json)
    model_requests = install_model_mock(monkeypatch, sample_model_draft())

    assert steward.main(["--config", "steward.json", "--thread", "demo"]) == 0

    assert len(watercooler_calls) == 1
    assert watercooler_calls[0]["path"] == "/v1/summary/workset"
    assert watercooler_calls[0]["query"] == {"thread": "demo"}
    assert len(model_requests) == 1
    assert model_requests[0]["url"] == "http://127.0.0.1:1234/v1/chat/completions"
    assert not any("watercooler" in key.casefold() for key in model_requests[0]["headers"])
    assert "wc-secret" not in json.dumps(model_requests[0])
    assert model_requests[0]["body"]["temperature"] == 0
    assert model_requests[0]["body"]["response_format"]["json_schema"]["strict"] is True
    source_schema = model_requests[0]["body"]["response_format"]["json_schema"]["schema"]
    orientation_item = source_schema["properties"]["sections"]["properties"]["orientation"]["items"]
    assert orientation_item["properties"]["source_message_ids"]["items"]["enum"] == [95, 96, 101, 102, 103]

    output = capsys.readouterr().out
    assert "# Current orientation" in output
    assert '"dry_run": true' in output
    assert '"prompt_sha256"' in output


def test_publish_posts_exact_concurrency_and_provenance_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workset = sample_workset()
    calls: list[dict] = []
    config = {"base_url": "http://watercooler.test", "token": "wc-secret"}
    monkeypatch.setattr(steward, "load_config", lambda _path: config)

    def fake_request_json(received_config, *, method, path, payload=None, query=None):
        calls.append(
            {
                "config": received_config,
                "method": method,
                "path": path,
                "payload": payload,
                "query": query,
            }
        )
        if method == "GET":
            return copy.deepcopy(workset)
        return {"ok": True, "summary": {"revision_id": 8}}

    monkeypatch.setattr(steward, "request_json", fake_request_json)
    install_model_mock(monkeypatch, sample_model_draft())

    assert (
        steward.main(
            [
                "--config",
                "steward.json",
                "--thread",
                "demo",
                "--model",
                "gemma-local",
                "--publish",
            ]
        )
        == 0
    )

    assert len(calls) == 2
    messages, prompt_sha256 = steward.build_prompt(workset)
    assert messages
    assert calls[1] == {
        "config": config,
        "method": "POST",
        "path": "/v1/summary/publish",
        "payload": {
            "thread": workset["thread"],
            "expected_parent_revision_id": workset["base_revision_id"],
            "expected_task_event_head_id": workset["task_event_head_id"],
            "expected_task_snapshot_sha256": workset["task_snapshot_sha256"],
            "coverage_through_message_id": workset["batch_through_message_id"],
            "batch_message_ids": workset["batch_message_ids"],
            "workset_sha256": workset["workset_sha256"],
            "generator": {
                "model_id": "gemma-local",
                "prompt_sha256": prompt_sha256,
            },
            "draft": sample_draft(),
        },
        "query": None,
    }
