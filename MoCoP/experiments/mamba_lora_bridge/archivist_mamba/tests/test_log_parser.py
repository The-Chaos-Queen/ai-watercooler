from __future__ import annotations

from pathlib import Path

from archivist_mamba.log_parser import iter_codex_events, iter_jsonl

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_codex_rollout.jsonl"


def test_iter_jsonl_streams_records_and_malformed_errors():
    rows = list(iter_jsonl(FIXTURE))

    assert rows[0][0] == 1
    assert rows[0][1]["type"] == "session_meta"
    assert rows[-1][0] == 6
    assert rows[-1][1]["type"] == "parse_error"
    assert "not json" in rows[-1][1]["raw"]


def test_iter_codex_events_normalizes_message_text():
    events = list(iter_codex_events(FIXTURE))

    user_events = [event for event in events if event["role"] == "user"]
    assert user_events[0]["event_type"] == "message"
    assert "old session logs" in user_events[0]["text"]
    assert user_events[0]["line_no"] == 2


def test_iter_codex_events_normalizes_command_failures():
    events = list(iter_codex_events(FIXTURE))

    failures = [event for event in events if event["event_type"] == "tool_error"]
    assert len(failures) == 1
    assert failures[0]["exit_code"] == 1
    assert "timeout" in failures[0]["text"]


def test_iter_codex_events_truncates_preview_text():
    events = list(iter_codex_events(FIXTURE, max_text_chars=20))

    long_user = next(event for event in events if event["role"] == "user")
    assert len(long_user["text"]) <= 20
