from __future__ import annotations

import io
import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import watercooler_loop as loop  # noqa: E402


EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def make_spec(tmp_path: Path, **overrides) -> loop.LoopSpec:
    payload = {
        "version": 1,
        "name": "review-tick",
        "argv": [sys.executable, "-c", "pass"],
        "cwd": str(tmp_path.resolve()),
        "interval_seconds": 5,
        "count": 2,
        "until": None,
        "timeout_seconds": 10,
    }
    payload.update(overrides)
    return loop.LoopSpec.from_payload(payload)


def success_outcome(duration: float = 0.0) -> loop.IterationOutcome:
    stream = loop.StreamDigest(0, EMPTY_SHA256, False)
    return loop.IterationOutcome("succeeded", 0, duration, stream, stream)


class FakeClock:
    def __init__(self, start: datetime):
        self.current = start
        self.sleeps: list[float] = []

    def now(self) -> datetime:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.current += timedelta(seconds=seconds)

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"name": "../escape"}, "loop name"),
        ({"argv": "python"}, "argv"),
        ({"argv": ["python", ""]}, "argv"),
        ({"argv": ["python", "\ud800"]}, "argv"),
        ({"argv": ["review.cmd"]}, "command-shell"),
        ({"cwd": "relative"}, "absolute"),
        ({"cwd": "C:\\\ud800"}, "absolute"),
        ({"interval_seconds": True}, "interval_seconds"),
        ({"count": 0}, "count"),
        ({"count": None, "until": None}, "at least one"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"extra": "field"}, "exactly"),
    ],
)
def test_spec_schema_is_exact_and_bounded(tmp_path, overrides, match):
    payload = make_spec(tmp_path).to_payload()
    payload.update(overrides)

    with pytest.raises(loop.LoopError, match=match):
        loop.LoopSpec.from_payload(payload)


def test_until_must_be_canonical_utc(tmp_path):
    with pytest.raises(loop.LoopError, match="canonical UTC"):
        make_spec(tmp_path, until="2026-07-18T12:00:00+00:00")

    spec = make_spec(tmp_path, count=None, until="2026-07-18T12:00:00Z")
    assert spec.until_datetime == datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


def test_named_spec_round_trip_is_atomic_and_requires_replace(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")
    spec = make_spec(tmp_path)

    path = loop.save_spec(paths, spec)

    assert loop.load_spec(paths, spec.name) == spec
    assert json.loads(path.read_text(encoding="utf-8")) == spec.to_payload()
    assert not list(path.parent.glob("*.tmp"))
    with pytest.raises(loop.LoopError, match="already exists"):
        loop.save_spec(paths, spec)
    loop.save_spec(paths, make_spec(tmp_path, count=3), replace=True)
    assert loop.load_spec(paths, spec.name).count == 3


def test_non_replacing_spec_creation_is_serialized(tmp_path, monkeypatch):
    paths = loop.LoopPaths(tmp_path / "loops")
    spec = make_spec(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    failures = []
    original_write = loop._atomic_write_json

    def slow_write(path, payload):
        entered.set()
        if not release.wait(timeout=5):
            raise AssertionError("test did not release the spec writer")
        original_write(path, payload)

    def writer():
        try:
            loop.save_spec(paths, spec)
        except BaseException as exc:  # captured for the parent test thread
            failures.append(exc)

    monkeypatch.setattr(loop, "_atomic_write_json", slow_write)
    thread = threading.Thread(target=writer)
    thread.start()
    assert entered.wait(timeout=5)
    try:
        with pytest.raises(loop.AlreadyRunning):
            loop.save_spec(paths, spec)
    finally:
        release.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert failures == []
    assert loop.load_spec(paths, spec.name) == spec


def test_list_specs_is_name_sorted(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")
    loop.save_spec(paths, make_spec(tmp_path, name="z-last"))
    loop.save_spec(paths, make_spec(tmp_path, name="A-first"))

    assert [spec.name for spec in loop.list_specs(paths)] == ["A-first", "z-last"]


def test_run_is_dry_by_default_and_creates_no_runtime_state(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")
    called = False

    def hook(spec, iteration, cancellation):
        del spec, iteration, cancellation
        nonlocal called
        called = True
        return success_outcome()

    result = loop.run_loop(paths, make_spec(tmp_path), hook=hook)

    assert result.dry_run is True
    assert result.terminal_reason == "dry_run"
    assert called is False
    assert not paths.root.exists()


def test_count_uses_immediate_first_run_and_fixed_delay_after_finish(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")
    clock = FakeClock(datetime(2026, 7, 18, 10, tzinfo=timezone.utc))
    starts: list[datetime] = []

    def hook(spec, iteration, cancellation):
        del spec, iteration, cancellation
        starts.append(clock.now())
        clock.advance(2)
        return success_outcome(2)

    result = loop.run_loop(
        paths,
        make_spec(tmp_path, count=3),
        execute=True,
        hook=hook,
        now=clock.now,
        sleeper=clock.sleep,
    )

    assert result.terminal_reason == "count_reached"
    assert result.iterations_started == 3
    assert starts == [
        datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 18, 10, 0, 7, tzinfo=timezone.utc),
        datetime(2026, 7, 18, 10, 0, 14, tzinfo=timezone.utc),
    ]
    assert sum(clock.sleeps) == pytest.approx(10)


def test_until_is_exclusive_and_first_limit_wins(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")
    start = datetime(2026, 7, 18, 10, tzinfo=timezone.utc)
    clock = FakeClock(start)
    calls = 0

    def hook(spec, iteration, cancellation):
        del spec, iteration, cancellation
        nonlocal calls
        calls += 1
        clock.advance(1)
        return success_outcome(1)

    result = loop.run_loop(
        paths,
        make_spec(
            tmp_path,
            count=99,
            until=loop.iso_utc(start + timedelta(seconds=5)),
        ),
        execute=True,
        hook=hook,
        now=clock.now,
        sleeper=clock.sleep,
    )

    assert calls == 1
    assert result.terminal_reason == "until_reached"


def test_non_success_stops_loop_and_journals_each_boundary(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")
    clock = FakeClock(datetime(2026, 7, 18, 10, tzinfo=timezone.utc))
    stream = loop.StreamDigest(7, "a" * 64, False)

    def hook(spec, iteration, cancellation):
        del spec, cancellation
        if iteration == 1:
            return success_outcome()
        return loop.IterationOutcome("failed", 7, 0.25, stream, stream)

    result = loop.run_loop(
        paths,
        make_spec(tmp_path, count=5),
        execute=True,
        hook=hook,
        now=clock.now,
        sleeper=clock.sleep,
    )
    rows = loop.read_journal(paths, "review-tick", tail=20)

    assert result.terminal_reason == "failed"
    assert result.iterations_started == 2
    assert [row["event"] for row in rows] == [
        "run_started",
        "iteration_started",
        "iteration_finished",
        "iteration_started",
        "iteration_finished",
        "run_finished",
    ]
    assert rows[-2]["returncode"] == 7
    assert rows[-2]["stdout"]["sha256"] == "a" * 64
    assert "argv" not in json.dumps(rows)


def test_hook_fault_becomes_a_terminal_journal_row_and_cleans_active_state(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")

    def hook(spec, iteration, cancellation):
        del spec, iteration, cancellation
        raise RuntimeError("untrusted hook detail must not be journaled")

    result = loop.run_loop(
        paths,
        make_spec(tmp_path, count=5),
        execute=True,
        hook=hook,
    )
    rows = loop.read_journal(paths, "review-tick")

    assert result.terminal_reason == "launch_failed"
    assert rows[-2]["event"] == "iteration_finished"
    assert rows[-2]["error_type"] == "RuntimeError"
    assert "untrusted hook detail" not in json.dumps(rows)
    assert not paths.active("review-tick").exists()


def test_named_lock_rejects_overlap(tmp_path):
    lock_path = tmp_path / "same.lock"

    with loop.NamedLoopLock(lock_path):
        with pytest.raises(loop.AlreadyRunning):
            with loop.NamedLoopLock(lock_path):
                pass


def test_operator_cancellation_stops_before_next_iteration_and_cleans_state(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")
    clock = FakeClock(datetime(2026, 7, 18, 10, tzinfo=timezone.utc))
    calls = 0

    def hook(spec, iteration, cancellation):
        del spec, iteration, cancellation
        nonlocal calls
        calls += 1
        assert loop.request_cancellation(paths, "review-tick", now=clock.now)
        return success_outcome()

    result = loop.run_loop(
        paths,
        make_spec(tmp_path, count=5),
        execute=True,
        hook=hook,
        now=clock.now,
        sleeper=clock.sleep,
    )

    assert calls == 1
    assert result.terminal_reason == "cancelled"
    assert not paths.active("review-tick").exists()
    assert not paths.cancellation("review-tick").exists()


def test_cancel_returns_false_without_active_run(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")

    assert loop.request_cancellation(paths, "review-tick") is False


def test_cancellation_reason_rejects_lone_surrogate(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")

    with pytest.raises(loop.LoopError, match="cancellation reason"):
        loop.request_cancellation(paths, "review-tick", reason="bad\ud800")


def test_journal_repairs_a_crash_truncated_final_row(tmp_path):
    paths = loop.LoopPaths(tmp_path / "loops")
    journal = paths.journal("review-tick")
    loop.append_journal(journal, {"event": "first", "sequence": 1})
    with journal.open("ab") as handle:
        handle.write(b'{"event":"truncated"')

    assert [row["sequence"] for row in loop.read_journal(paths, "review-tick")] == [1]

    loop.append_journal(journal, {"event": "second", "sequence": 2})
    rows = loop.read_journal(paths, "review-tick")

    assert [row["sequence"] for row in rows] == [1, 2]
    assert b"truncated" not in journal.read_bytes()


def test_journal_rotation_retains_a_bounded_tail(tmp_path, monkeypatch):
    paths = loop.LoopPaths(tmp_path / "loops")
    journal = paths.journal("review-tick")
    monkeypatch.setattr(loop, "MAX_JOURNAL_BYTES", 240)

    for sequence in range(12):
        loop.append_journal(journal, {"event": "tick", "sequence": sequence})

    assert journal.with_name(f"{journal.name}.1").exists()
    rows = loop.read_journal(paths, "review-tick", tail=6)
    assert [row["sequence"] for row in rows] == list(range(6, 12))


def test_journal_read_and_rotation_share_one_snapshot_lock(tmp_path, monkeypatch):
    paths = loop.LoopPaths(tmp_path / "loops")
    journal = paths.journal("review-tick")
    for sequence in range(6):
        loop.append_journal(journal, {"event": "tick", "sequence": sequence})

    reader_entered = threading.Event()
    release_reader = threading.Event()
    writer_finished = threading.Event()
    read_rows = []
    original_tail_reader = loop._read_complete_tail_lines

    def paused_tail_reader(path, limit):
        rows = original_tail_reader(path, limit)
        if path == journal and not reader_entered.is_set():
            reader_entered.set()
            if not release_reader.wait(timeout=5):
                raise AssertionError("test did not release the journal reader")
        return rows

    def read_snapshot():
        read_rows.extend(loop.read_journal(paths, "review-tick", tail=6))

    def rotate_and_append():
        loop.append_journal(journal, {"event": "tick", "sequence": 6})
        writer_finished.set()

    monkeypatch.setattr(loop, "_read_complete_tail_lines", paused_tail_reader)
    monkeypatch.setattr(loop, "MAX_JOURNAL_BYTES", 1)
    reader = threading.Thread(target=read_snapshot)
    writer = threading.Thread(target=rotate_and_append)
    reader.start()
    assert reader_entered.wait(timeout=5)
    writer.start()
    assert not writer_finished.wait(timeout=0.1)
    release_reader.set()
    reader.join(timeout=5)
    writer.join(timeout=5)

    assert not reader.is_alive()
    assert not writer.is_alive()
    assert [row["sequence"] for row in read_rows] == list(range(6))
    assert [
        row["sequence"] for row in loop.read_journal(paths, "review-tick", tail=6)
    ] == list(range(1, 7))


class ImmediateProcess:
    pid = 123
    returncode = 0

    def __init__(self):
        self.stdout = io.BytesIO(b"output")
        self.stderr = io.BytesIO(b"")

    def poll(self):
        return self.returncode


class RunningProcess(ImmediateProcess):
    returncode = None

    def poll(self):
        return self.returncode


class TerminableProcess(RunningProcess):
    def kill(self):
        self.returncode = -9

    def wait(self, timeout):
        del timeout
        return self.returncode


class DeadlineRaceProcess(ImmediateProcess):
    def __init__(self):
        super().__init__()
        self.polls = 0

    def poll(self):
        self.polls += 1
        return None if self.polls == 1 else 0


def test_subprocess_hook_passes_argv_directly_and_never_uses_shell(tmp_path):
    calls = []

    def popen_factory(argv, **kwargs):
        calls.append((argv, kwargs))
        return ImmediateProcess()

    hook = loop.SubprocessHook(popen_factory=popen_factory)
    outcome = hook(
        make_spec(tmp_path),
        1,
        loop.CancellationToken(tmp_path / "none", "run"),
    )

    assert outcome.status == "succeeded"
    assert calls[0][0] == [sys.executable, "-c", "pass"]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["stdin"] is subprocess.DEVNULL
    assert calls[0][1]["text"] is False
    if sys.platform == "win32":
        flags = calls[0][1]["creationflags"]
        assert flags & subprocess.CREATE_NEW_PROCESS_GROUP
        assert flags & subprocess.CREATE_NO_WINDOW


def test_subprocess_hook_terminates_child_when_monitor_is_interrupted(tmp_path):
    process = RunningProcess()
    terminated = []

    def sleeper(seconds):
        del seconds
        raise KeyboardInterrupt

    def terminate(candidate):
        terminated.append(candidate)
        candidate.returncode = -9

    hook = loop.SubprocessHook(
        popen_factory=lambda *args, **kwargs: process,
        terminator=terminate,
        sleeper=sleeper,
    )

    with pytest.raises(KeyboardInterrupt):
        hook(
            make_spec(tmp_path),
            1,
            loop.CancellationToken(tmp_path / "none", "run"),
        )

    assert terminated == [process]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows creation flag contract")
def test_windows_tree_termination_is_also_silent(monkeypatch):
    calls = []
    process = TerminableProcess()

    def run(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(loop.subprocess, "run", run)

    loop.terminate_process_tree(process)

    assert calls[0][1]["shell"] is False
    assert calls[0][1]["creationflags"] & subprocess.CREATE_NO_WINDOW
    assert process.returncode == -9


def test_subprocess_hook_enforces_timeout(tmp_path):
    hook = loop.SubprocessHook(poll_seconds=0.02)
    spec = make_spec(
        tmp_path,
        argv=[sys.executable, "-c", "import time; time.sleep(10)"],
        timeout_seconds=1,
    )

    outcome = hook(spec, 1, loop.CancellationToken(tmp_path / "none", "run"))

    assert outcome.status == "timed_out"
    assert outcome.duration_seconds < 5


def test_subprocess_hook_deadline_wins_a_completion_poll_race(tmp_path):
    readings = iter([0.0, 0.0, 1.1, 1.1])
    hook = loop.SubprocessHook(
        popen_factory=lambda *args, **kwargs: DeadlineRaceProcess(),
        monotonic=lambda: next(readings),
        sleeper=lambda seconds: None,
    )

    outcome = hook(
        make_spec(tmp_path, timeout_seconds=1),
        1,
        loop.CancellationToken(tmp_path / "none", "run"),
    )

    assert outcome.status == "timed_out"


def test_subprocess_hook_honors_live_cancellation(tmp_path):
    marker = tmp_path / "cancel.json"
    token = loop.CancellationToken(marker, "run-1")
    hook = loop.SubprocessHook(poll_seconds=0.02)
    spec = make_spec(
        tmp_path,
        argv=[sys.executable, "-c", "import time; time.sleep(10)"],
        timeout_seconds=5,
    )

    def cancel_soon():
        time.sleep(0.2)
        marker.write_text(json.dumps({"run_id": "run-1"}), encoding="utf-8")

    thread = threading.Thread(target=cancel_soon)
    thread.start()
    outcome = hook(spec, 1, token)
    thread.join()

    assert outcome.status == "cancelled"
    assert outcome.duration_seconds < 5


def test_subprocess_hook_enforces_output_limit_even_if_process_exits_fast(tmp_path):
    hook = loop.SubprocessHook(max_stream_bytes=1_024, poll_seconds=0.01)
    spec = make_spec(
        tmp_path,
        argv=[sys.executable, "-c", "import sys; sys.stdout.write('x' * 20000)"],
    )

    outcome = hook(spec, 1, loop.CancellationToken(tmp_path / "none", "run"))

    assert outcome.status == "output_limit"
    assert outcome.stdout.byte_count > 1_024
    assert outcome.stdout.limit_exceeded is True


def test_cli_run_is_dry_by_default(tmp_path, capsys):
    root = tmp_path / "loops"
    assert (
        loop.main(
            [
                "--root",
                str(root),
                "put",
                "demo",
                "--interval-seconds",
                "10",
                "--count",
                "1",
                "--timeout-seconds",
                "10",
                "--cwd",
                str(tmp_path),
                "--",
                sys.executable,
                "-c",
                "raise SystemExit(99)",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert loop.main(["--root", str(root), "run", "demo"]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["dry_run"] is True
    assert output["iterations_started"] == 0
    assert output["spec"]["argv"][-1] == "raise SystemExit(99)"
    assert output["semantics"]["until"] == "exclusive_start_deadline"
    assert output["semantics"]["descendants"] == "foreground_only"
    assert not loop.LoopPaths(root).journal("demo").exists()
