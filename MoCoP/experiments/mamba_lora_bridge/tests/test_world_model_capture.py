from __future__ import annotations

import json

import pytest

import world_model_capture as capture
from world_model_baselines import DirichletTabularEstimator
from world_model_trace import NullWorldModelObserver


def _begin_kwargs(observer=None) -> dict:
    return {
        "observer": observer or NullWorldModelObserver(),
        "run_id": "run-train-1",
        "domain": "tool",
        "episode_id": "episode-1",
        "step_index": 0,
        "state_ref": "sandbox:ready",
        "action": capture.canonical_action("read", {"path": "present.txt"}),
        "state_source_kind": "tool_context",
        "state_source_id": "sandbox:run-train-1:step:0:pre",
        "state_source_payload": {"files": ["present.txt"]},
    }


def test_commit_is_fsynced_before_action_executes(tmp_path, monkeypatch):
    journal_path = tmp_path / "trace.journal.jsonl"
    fsync_calls: list[int] = []
    real_fsync = capture.os.fsync

    def tracked_fsync(fd: int) -> None:
        fsync_calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(capture.os, "fsync", tracked_fsync)
    journal = capture.DurableTraceJournal(journal_path, manifest_sha256="1" * 64)

    def execute():
        records = [json.loads(line) for line in journal_path.read_text().splitlines()]
        assert [record["record_type"] for record in records] == [
            "header",
            "pre_action_commit",
        ]
        assert len(fsync_calls) == 2
        return "success", "tool_result", "sandbox:run-train-1:step:0:post", {
            "returncode": 0
        }

    outcome = journal.capture(execute=execute, **_begin_kwargs())
    assert outcome.observation == "success"
    assert len(fsync_calls) == 3
    pairs = capture.load_journal(journal_path, expected_manifest_sha256="1" * 64)
    assert len(pairs) == 1


def test_executor_crash_leaves_an_unscoreable_orphan_commit(tmp_path):
    journal_path = tmp_path / "trace.journal.jsonl"
    journal = capture.DurableTraceJournal(journal_path, manifest_sha256="2" * 64)

    def crash():
        raise RuntimeError("tool crashed")

    with pytest.raises(RuntimeError, match="tool crashed"):
        journal.capture(execute=crash, **_begin_kwargs())
    with pytest.raises(ValueError, match="orphan pre-action commit"):
        capture.load_journal(journal_path, expected_manifest_sha256="2" * 64)


def test_frozen_eval_prediction_is_durable_before_action_executes(tmp_path):
    journal_path = tmp_path / "eval.journal.jsonl"
    estimator = DirichletTabularEstimator(("success", "not_found"), estimator_id="frozen")
    estimator.update("sandbox:ready", capture.canonical_action("read", {"path": "present.txt"}), "success")
    journal = capture.DurableTraceJournal(journal_path, manifest_sha256="5" * 64)

    def execute():
        record = json.loads(journal_path.read_text().splitlines()[-1])
        assert record["record_type"] == "pre_action_commit"
        assert record["commit"]["status"] == "committed"
        assert record["commit"]["estimator_id"] == "frozen"
        assert record["commit"]["probabilities"]
        return "success", "tool_result", "sandbox:eval:post", {"returncode": 0}

    journal.capture(execute=execute, **_begin_kwargs(observer=estimator))
    assert len(capture.load_journal(journal_path, expected_manifest_sha256="5" * 64)) == 1


def test_state_source_payload_is_hash_bound(tmp_path):
    journal_path = tmp_path / "trace.journal.jsonl"
    journal = capture.DurableTraceJournal(journal_path, manifest_sha256="3" * 64)
    journal.capture(
        execute=lambda: (
            "success",
            "tool_result",
            "sandbox:run-train-1:step:0:post",
            {"pixels": [[0, 1], [2, 3]]},
        ),
        **_begin_kwargs(),
    )
    records = [json.loads(line) for line in journal_path.read_text().splitlines()]
    records[1]["state_source"]["payload"]["files"].append("one-pixel-change")
    journal_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="state_source sha256"):
        capture.load_journal(journal_path, expected_manifest_sha256="3" * 64)


def test_canonical_action_binds_complete_arguments():
    first = capture.canonical_action("ACTION6", {"x": 1, "y": 2})
    second = capture.canonical_action("ACTION6", {"x": 1, "y": 3})
    assert first != second


def test_no_overwrite_journal_creation(tmp_path):
    path = tmp_path / "trace.journal.jsonl"
    capture.DurableTraceJournal(path, manifest_sha256="4" * 64)
    with pytest.raises(FileExistsError):
        capture.DurableTraceJournal(path, manifest_sha256="4" * 64)
