"""Durable, bounded named loops for local Watercooler automation.

Loop definitions contain scheduling policy and an argv vector, not project
logic. Running is a dry-run unless ``--execute`` is supplied explicitly.
Commands must remain in the foreground; detached descendants are outside the
portable lifetime boundary of this runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

SPEC_VERSION = 1
STATE_VERSION = 1
JOURNAL_VERSION = 1
MAX_ARGV_ITEMS = 64
MAX_ARG_LENGTH = 4_096
MAX_ARGV_BYTES = 32_768
MAX_COUNT = 100_000
MAX_INTERVAL_SECONDS = 7 * 24 * 60 * 60
MAX_TIMEOUT_SECONDS = 24 * 60 * 60
MAX_STREAM_BYTES = 1_000_000
MAX_JOURNAL_BYTES = 8 * 1024 * 1024
MAX_JOURNAL_BACKUPS = 3
MAX_JOURNAL_ROW_BYTES = 16 * 1024
JOURNAL_TAIL_CHUNK_BYTES = 64 * 1024
POLL_SECONDS = 0.1
LOOP_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SPEC_KEYS = frozenset(
    {
        "version",
        "name",
        "argv",
        "cwd",
        "interval_seconds",
        "count",
        "until",
        "timeout_seconds",
    }
)
TERMINAL_ITERATION_STATUSES = frozenset(
    {
        "succeeded",
        "failed",
        "timed_out",
        "cancelled",
        "output_limit",
        "launch_failed",
    }
)


class LoopError(RuntimeError):
    """Raised when a loop boundary cannot be satisfied safely."""


class AlreadyRunning(LoopError):
    """Raised when the named loop already has a live owner."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    current = value or utc_now()
    if current.tzinfo is None or current.utcoffset() is None:
        raise LoopError("timestamps must be timezone-aware")
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_until(value: str) -> datetime:
    if type(value) is not str or not value:
        raise LoopError("until must be a canonical UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LoopError("until must be a canonical UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LoopError("until must include a timezone")
    if iso_utc(parsed) != value:
        raise LoopError("until must use canonical UTC form ending in Z")
    return parsed.astimezone(timezone.utc)


def validate_name(name: Any) -> str:
    if type(name) is not str or LOOP_NAME_RE.fullmatch(name) is None:
        raise LoopError("loop name must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return name


def _contains_surrogate(value: str) -> bool:
    return any(0xD800 <= ord(character) <= 0xDFFF for character in value)


@dataclass(frozen=True)
class LoopSpec:
    name: str
    argv: tuple[str, ...]
    cwd: str
    interval_seconds: int
    count: int | None
    until: str | None
    timeout_seconds: int

    @classmethod
    def from_payload(cls, payload: Any) -> "LoopSpec":
        if type(payload) is not dict or set(payload) != SPEC_KEYS:
            raise LoopError("loop spec must contain exactly the v1 fields")
        if type(payload["version"]) is not int or payload["version"] != SPEC_VERSION:
            raise LoopError("loop spec version is unsupported")
        name = validate_name(payload["name"])
        argv = payload["argv"]
        if type(argv) is not list or not 1 <= len(argv) <= MAX_ARGV_ITEMS:
            raise LoopError(f"argv must contain 1 to {MAX_ARGV_ITEMS} strings")
        if any(
            type(arg) is not str
            or not arg
            or "\0" in arg
            or _contains_surrogate(arg)
            or len(arg) > MAX_ARG_LENGTH
            for arg in argv
        ):
            raise LoopError("argv contains an invalid value")
        if Path(argv[0]).suffix.casefold() in {".bat", ".cmd"}:
            raise LoopError("argv[0] must not rely on implicit Windows command-shell dispatch")
        if len(json.dumps(argv, ensure_ascii=False).encode("utf-8")) > MAX_ARGV_BYTES:
            raise LoopError("argv exceeds its byte limit")
        cwd = payload["cwd"]
        if (
            type(cwd) is not str
            or not cwd
            or "\0" in cwd
            or _contains_surrogate(cwd)
            or not Path(cwd).is_absolute()
        ):
            raise LoopError("cwd must be a non-empty absolute path")
        interval = payload["interval_seconds"]
        if type(interval) is not int or not 1 <= interval <= MAX_INTERVAL_SECONDS:
            raise LoopError(
                f"interval_seconds must be an integer from 1 to {MAX_INTERVAL_SECONDS}"
            )
        count = payload["count"]
        if count is not None and (
            type(count) is not int or not 1 <= count <= MAX_COUNT
        ):
            raise LoopError(f"count must be null or an integer from 1 to {MAX_COUNT}")
        until = payload["until"]
        if until is not None:
            parse_until(until)
        if count is None and until is None:
            raise LoopError("at least one of count or until is required")
        timeout = payload["timeout_seconds"]
        if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT_SECONDS:
            raise LoopError(
                f"timeout_seconds must be an integer from 1 to {MAX_TIMEOUT_SECONDS}"
            )
        return cls(
            name=name,
            argv=tuple(argv),
            cwd=cwd,
            interval_seconds=interval,
            count=count,
            until=until,
            timeout_seconds=timeout,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "version": SPEC_VERSION,
            "name": self.name,
            "argv": list(self.argv),
            "cwd": self.cwd,
            "interval_seconds": self.interval_seconds,
            "count": self.count,
            "until": self.until,
            "timeout_seconds": self.timeout_seconds,
        }

    @property
    def until_datetime(self) -> datetime | None:
        return parse_until(self.until) if self.until is not None else None


@dataclass(frozen=True)
class LoopPaths:
    root: Path

    @classmethod
    def default(cls) -> "LoopPaths":
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
        return cls(base / "Watercooler" / "loops")

    def spec(self, name: str) -> Path:
        return self.root / "specs" / f"{validate_name(name)}.json"

    def journal(self, name: str) -> Path:
        return self.root / "journals" / f"{validate_name(name)}.jsonl"

    def lock(self, name: str) -> Path:
        return self.root / "locks" / f"{validate_name(name)}.lock"

    def active(self, name: str) -> Path:
        return self.root / "active" / f"{validate_name(name)}.json"

    def cancellation(self, name: str) -> Path:
        return self.root / "cancellations" / f"{validate_name(name)}.json"


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        encoded = (
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise LoopError("state payload is not UTF-8 JSON serializable") from exc
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def save_spec(paths: LoopPaths, spec: LoopSpec, *, replace: bool = False) -> Path:
    validated = LoopSpec.from_payload(spec.to_payload())
    path = paths.spec(validated.name)
    spec_lock = paths.root / "spec-locks" / f"{validated.name}.lock"
    with NamedLoopLock(spec_lock):
        if path.exists() and not replace:
            raise LoopError(f"loop spec already exists: {validated.name}")
        _atomic_write_json(path, validated.to_payload())
    return path


def load_spec(paths: LoopPaths, name: str) -> LoopSpec:
    path = paths.spec(name)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LoopError(f"loop spec does not exist: {name}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LoopError(f"loop spec is unreadable: {name}") from exc
    spec = LoopSpec.from_payload(payload)
    if spec.name != name:
        raise LoopError("loop spec name does not match its filename")
    return spec


def list_specs(paths: LoopPaths) -> list[LoopSpec]:
    directory = paths.root / "specs"
    if not directory.exists():
        return []
    specs = [load_spec(paths, path.stem) for path in directory.glob("*.json")]
    return sorted(specs, key=lambda spec: spec.name.casefold())


def spec_sha256(spec: LoopSpec) -> str:
    encoded = json.dumps(
        spec.to_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class NamedLoopLock(AbstractContextManager["NamedLoopLock"]):
    """An OS-held lock that prevents concurrent runs of one named loop."""

    def __init__(self, path: Path, *, blocking: bool = False):
        self.path = path
        self.blocking = blocking
        self._handle: Any = None

    def __enter__(self) -> "NamedLoopLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                mode = msvcrt.LK_LOCK if self.blocking else msvcrt.LK_NBLCK
                msvcrt.locking(handle.fileno(), mode, 1)
            else:  # pragma: no cover - Windows is the primary local surface
                import fcntl

                flags = fcntl.LOCK_EX
                if not self.blocking:
                    flags |= fcntl.LOCK_NB
                fcntl.flock(handle.fileno(), flags)
        except OSError as exc:
            handle.close()
            raise AlreadyRunning(f"loop is already running: {self.path.stem}") from exc
        self._handle = handle
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        handle = self._handle
        if handle is None:
            return
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            self._handle = None


def _journal_backup_path(path: Path, index: int) -> Path:
    return path.with_name(f"{path.name}.{index}")


def _journal_lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


def _repair_trailing_journal_fragment(path: Path) -> None:
    if not path.exists():
        return
    with path.open("r+b") as handle:
        size = handle.seek(0, os.SEEK_END)
        if size == 0:
            return
        handle.seek(-1, os.SEEK_END)
        if handle.read(1) == b"\n":
            return
        position = size
        last_newline = -1
        while position > 0 and last_newline < 0:
            chunk_size = min(JOURNAL_TAIL_CHUNK_BYTES, position)
            position -= chunk_size
            handle.seek(position)
            chunk = handle.read(chunk_size)
            offset = chunk.rfind(b"\n")
            if offset >= 0:
                last_newline = position + offset
        handle.truncate(last_newline + 1 if last_newline >= 0 else 0)
        handle.flush()
        os.fsync(handle.fileno())


def _rotate_journal(path: Path) -> None:
    for index in range(MAX_JOURNAL_BACKUPS, 0, -1):
        source = path if index == 1 else _journal_backup_path(path, index - 1)
        if source.exists():
            os.replace(source, _journal_backup_path(path, index))


def append_journal(path: Path, event: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"journal_version": JOURNAL_VERSION, **event}
    try:
        encoded = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise LoopError("journal row is not UTF-8 JSON serializable") from exc
    if len(encoded) > MAX_JOURNAL_ROW_BYTES:
        raise LoopError("journal row exceeds its byte limit")
    with NamedLoopLock(_journal_lock_path(path), blocking=True):
        _repair_trailing_journal_fragment(path)
        if path.exists() and path.stat().st_size + len(encoded) > MAX_JOURNAL_BYTES:
            _rotate_journal(path)
        with path.open("ab") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())


def _read_complete_tail_lines(path: Path, limit: int) -> list[bytes]:
    if not path.exists() or limit <= 0:
        return []
    with path.open("rb") as handle:
        size = handle.seek(0, os.SEEK_END)
        if size == 0:
            return []
        position = size
        chunks: list[bytes] = []
        newline_count = 0
        while position > 0 and newline_count < limit + 1:
            chunk_size = min(JOURNAL_TAIL_CHUNK_BYTES, position)
            position -= chunk_size
            handle.seek(position)
            chunk = handle.read(chunk_size)
            chunks.append(chunk)
            newline_count += chunk.count(b"\n")
    data = b"".join(reversed(chunks))
    if position > 0:
        first_newline = data.find(b"\n")
        data = data[first_newline + 1 :] if first_newline >= 0 else b""
    if data and not data.endswith(b"\n"):
        last_newline = data.rfind(b"\n")
        data = data[: last_newline + 1] if last_newline >= 0 else b""
    return data.splitlines()[-limit:]


def read_journal(paths: LoopPaths, name: str, *, tail: int = 20) -> list[dict[str, Any]]:
    if type(tail) is not int or not 1 <= tail <= 1_000:
        raise LoopError("journal tail must be an integer from 1 to 1000")
    path = paths.journal(name)
    lines: list[bytes] = []
    try:
        candidates = [path] + [
            _journal_backup_path(path, index)
            for index in range(1, MAX_JOURNAL_BACKUPS + 1)
        ]
        if not any(candidate.exists() for candidate in candidates):
            return []
        with NamedLoopLock(_journal_lock_path(path), blocking=True):
            for candidate in candidates:
                remaining = tail - len(lines)
                if remaining <= 0:
                    break
                lines = _read_complete_tail_lines(candidate, remaining) + lines
        rows = [json.loads(line.decode("utf-8")) for line in lines]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LoopError(f"loop journal is unreadable: {name}") from exc
    if any(type(row) is not dict for row in rows):
        raise LoopError(f"loop journal contains a malformed row: {name}")
    return rows


@dataclass(frozen=True)
class CancellationToken:
    path: Path
    run_id: str

    def requested(self) -> bool:
        if not self.path.exists():
            return False
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return True
        if type(payload) is not dict:
            return True
        marker_run_id = payload.get("run_id")
        if type(marker_run_id) is not str:
            return True
        return marker_run_id == self.run_id


def request_cancellation(
    paths: LoopPaths,
    name: str,
    *,
    reason: str = "operator_request",
    now: Callable[[], datetime] = utc_now,
) -> bool:
    validate_name(name)
    if (
        type(reason) is not str
        or not reason
        or len(reason) > 200
        or "\0" in reason
        or _contains_surrogate(reason)
    ):
        raise LoopError("cancellation reason must contain 1 to 200 characters")
    active_path = paths.active(name)
    try:
        active = json.loads(active_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LoopError(f"active loop state is unreadable: {name}") from exc
    expected = {"version", "name", "run_id", "pid", "started_ts", "spec_sha256"}
    if type(active) is not dict or set(active) != expected:
        raise LoopError(f"active loop state is malformed: {name}")
    if active["name"] != name or type(active["run_id"]) is not str:
        raise LoopError(f"active loop state does not match: {name}")
    _atomic_write_json(
        paths.cancellation(name),
        {
            "version": STATE_VERSION,
            "name": name,
            "run_id": active["run_id"],
            "requested_ts": iso_utc(now()),
            "reason": reason,
        },
    )
    return True


@dataclass(frozen=True)
class StreamDigest:
    byte_count: int
    sha256: str
    limit_exceeded: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "bytes": self.byte_count,
            "sha256": self.sha256,
            "limit_exceeded": self.limit_exceeded,
        }


@dataclass(frozen=True)
class IterationOutcome:
    status: str
    returncode: int | None
    duration_seconds: float
    stdout: StreamDigest
    stderr: StreamDigest
    error_type: str | None = None

    def __post_init__(self) -> None:
        if self.status not in TERMINAL_ITERATION_STATUSES:
            raise LoopError(f"unsupported iteration status: {self.status}")


class IterationHook(Protocol):
    def __call__(
        self,
        spec: LoopSpec,
        iteration: int,
        cancellation: CancellationToken,
    ) -> IterationOutcome: ...


class _StreamReader:
    def __init__(self, stream: Any, limit: int, exceeded: threading.Event):
        self.stream = stream
        self.limit = limit
        self.exceeded = exceeded
        self.byte_count = 0
        self.hasher = hashlib.sha256()

    def run(self) -> None:
        try:
            while True:
                chunk = self.stream.read(8_192)
                if not chunk:
                    break
                self.byte_count += len(chunk)
                self.hasher.update(chunk)
                if self.byte_count > self.limit:
                    self.exceeded.set()
                    break
        finally:
            self.stream.close()

    def digest(self) -> StreamDigest:
        return StreamDigest(
            byte_count=self.byte_count,
            sha256=self.hasher.hexdigest(),
            limit_exceeded=self.byte_count > self.limit,
        )


def terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                shell=False,
                capture_output=True,
                timeout=30,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
    else:  # pragma: no cover - exercised on non-Windows CI
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            try:
                process.kill()
            except OSError:
                pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            process.kill()
        else:  # pragma: no cover
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=5)


class SubprocessHook:
    """Run a foreground spec argv directly, with bounded time and output."""

    def __init__(
        self,
        *,
        max_stream_bytes: int = MAX_STREAM_BYTES,
        poll_seconds: float = POLL_SECONDS,
        popen_factory: Callable[..., subprocess.Popen[Any]] = subprocess.Popen,
        terminator: Callable[[subprocess.Popen[Any]], None] = terminate_process_tree,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        if type(max_stream_bytes) is not int or max_stream_bytes < 1:
            raise LoopError("max_stream_bytes must be a positive integer")
        self.max_stream_bytes = max_stream_bytes
        self.poll_seconds = poll_seconds
        self.popen_factory = popen_factory
        self.terminator = terminator
        self.monotonic = monotonic
        self.sleeper = sleeper

    def __call__(
        self,
        spec: LoopSpec,
        iteration: int,
        cancellation: CancellationToken,
    ) -> IterationOutcome:
        del iteration
        started = self.monotonic()
        empty = StreamDigest(0, hashlib.sha256(b"").hexdigest(), False)
        creation_kwargs: dict[str, Any] = {}
        if os.name == "nt":
            creation_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            )
        else:  # pragma: no cover - exercised on non-Windows CI
            creation_kwargs["start_new_session"] = True
        try:
            process = self.popen_factory(
                list(spec.argv),
                cwd=spec.cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                text=False,
                **creation_kwargs,
            )
        except Exception as exc:
            return IterationOutcome(
                status="launch_failed",
                returncode=None,
                duration_seconds=max(0.0, self.monotonic() - started),
                stdout=empty,
                stderr=empty,
                error_type=type(exc).__name__,
            )
        if process.stdout is None or process.stderr is None:
            self.terminator(process)
            return IterationOutcome(
                status="launch_failed",
                returncode=process.returncode,
                duration_seconds=max(0.0, self.monotonic() - started),
                stdout=empty,
                stderr=empty,
                error_type="MissingProcessPipe",
            )
        exceeded = threading.Event()
        stdout_reader = _StreamReader(process.stdout, self.max_stream_bytes, exceeded)
        stderr_reader = _StreamReader(process.stderr, self.max_stream_bytes, exceeded)
        readers = [
            threading.Thread(target=stdout_reader.run, daemon=True),
            threading.Thread(target=stderr_reader.run, daemon=True),
        ]
        for reader in readers:
            reader.start()
        deadline = started + spec.timeout_seconds
        status: str | None = None
        try:
            while True:
                observed = self.monotonic()
                returncode = process.poll()
                if observed >= deadline:
                    status = "timed_out"
                    if returncode is None:
                        self.terminator(process)
                    break
                if returncode is not None:
                    break
                if cancellation.requested():
                    status = "cancelled"
                    self.terminator(process)
                    break
                if exceeded.is_set():
                    status = "output_limit"
                    self.terminator(process)
                    break
                self.sleeper(self.poll_seconds)
        except BaseException:
            self.terminator(process)
            for reader in readers:
                reader.join(timeout=5)
            raise
        returncode = process.poll()
        if returncode is None:
            self.terminator(process)
            returncode = process.poll()
        for reader in readers:
            reader.join(timeout=5)
        if any(reader.is_alive() for reader in readers):
            raise LoopError("subprocess output reader did not terminate")
        if exceeded.is_set() and status is None:
            status = "output_limit"
        if status is None:
            status = "succeeded" if returncode == 0 else "failed"
        return IterationOutcome(
            status=status,
            returncode=returncode,
            duration_seconds=max(0.0, self.monotonic() - started),
            stdout=stdout_reader.digest(),
            stderr=stderr_reader.digest(),
        )


@dataclass(frozen=True)
class LoopRunResult:
    name: str
    run_id: str | None
    dry_run: bool
    iterations_started: int
    terminal_reason: str
    journal_path: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "run_id": self.run_id,
            "dry_run": self.dry_run,
            "iterations_started": self.iterations_started,
            "terminal_reason": self.terminal_reason,
            "journal_path": self.journal_path,
        }


def _wait_until(
    target: datetime,
    *,
    cancellation: CancellationToken,
    now: Callable[[], datetime],
    sleeper: Callable[[float], None],
) -> bool:
    while True:
        if cancellation.requested():
            return False
        remaining = (target - now().astimezone(timezone.utc)).total_seconds()
        if remaining <= 0:
            return True
        sleeper(min(POLL_SECONDS, remaining))


def _remove_marker_for_run(path: Path, run_id: str) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return
    if type(payload) is dict and payload.get("run_id") == run_id:
        path.unlink(missing_ok=True)


def run_loop(
    paths: LoopPaths,
    spec: LoopSpec,
    *,
    execute: bool = False,
    hook: IterationHook | None = None,
    now: Callable[[], datetime] = utc_now,
    sleeper: Callable[[float], None] = time.sleep,
) -> LoopRunResult:
    spec = LoopSpec.from_payload(spec.to_payload())
    journal_path = paths.journal(spec.name)
    if not execute:
        return LoopRunResult(
            name=spec.name,
            run_id=None,
            dry_run=True,
            iterations_started=0,
            terminal_reason="dry_run",
            journal_path=str(journal_path),
        )
    iteration_hook = hook or SubprocessHook()
    with NamedLoopLock(paths.lock(spec.name)):
        run_id = uuid.uuid4().hex
        spec_digest = spec_sha256(spec)
        cancellation_path = paths.cancellation(spec.name)
        cancellation_path.unlink(missing_ok=True)
        cancellation = CancellationToken(cancellation_path, run_id)
        active_path = paths.active(spec.name)
        started_at = now()
        _atomic_write_json(
            active_path,
            {
                "version": STATE_VERSION,
                "name": spec.name,
                "run_id": run_id,
                "pid": os.getpid(),
                "started_ts": iso_utc(started_at),
                "spec_sha256": spec_digest,
            },
        )
        try:
            append_journal(
                journal_path,
                {
                    "event": "run_started",
                    "name": spec.name,
                    "run_id": run_id,
                    "spec_sha256": spec_digest,
                    "ts": iso_utc(started_at),
                    "schedule": {
                        "interval_seconds": spec.interval_seconds,
                        "count": spec.count,
                        "until": spec.until,
                        "timeout_seconds": spec.timeout_seconds,
                    },
                },
            )
        except BaseException:
            _remove_marker_for_run(active_path, run_id)
            _remove_marker_for_run(cancellation_path, run_id)
            raise
        iteration = 0
        terminal_reason = "internal_error"
        previous_finished: datetime | None = None
        until = spec.until_datetime
        try:
            while True:
                if cancellation.requested():
                    terminal_reason = "cancelled"
                    break
                if spec.count is not None and iteration >= spec.count:
                    terminal_reason = "count_reached"
                    break
                current = now().astimezone(timezone.utc)
                if until is not None and current >= until:
                    terminal_reason = "until_reached"
                    break
                if previous_finished is not None:
                    next_start = previous_finished.timestamp() + spec.interval_seconds
                    target = datetime.fromtimestamp(next_start, timezone.utc)
                    if until is not None and target >= until:
                        terminal_reason = "until_reached"
                        break
                    if not _wait_until(
                        target,
                        cancellation=cancellation,
                        now=now,
                        sleeper=sleeper,
                    ):
                        terminal_reason = "cancelled"
                        break
                    if until is not None and now().astimezone(timezone.utc) >= until:
                        terminal_reason = "until_reached"
                        break
                iteration += 1
                iteration_started = now()
                append_journal(
                    journal_path,
                    {
                        "event": "iteration_started",
                        "name": spec.name,
                        "run_id": run_id,
                        "spec_sha256": spec_digest,
                        "iteration": iteration,
                        "ts": iso_utc(iteration_started),
                    },
                )
                try:
                    outcome = iteration_hook(spec, iteration, cancellation)
                    if type(outcome) is not IterationOutcome:
                        raise LoopError("iteration hook returned an invalid outcome")
                except Exception as exc:
                    empty = StreamDigest(0, hashlib.sha256(b"").hexdigest(), False)
                    outcome = IterationOutcome(
                        status="launch_failed",
                        returncode=None,
                        duration_seconds=0.0,
                        stdout=empty,
                        stderr=empty,
                        error_type=type(exc).__name__,
                    )
                iteration_finished = now()
                append_journal(
                    journal_path,
                    {
                        "event": "iteration_finished",
                        "name": spec.name,
                        "run_id": run_id,
                        "spec_sha256": spec_digest,
                        "iteration": iteration,
                        "started_ts": iso_utc(iteration_started),
                        "finished_ts": iso_utc(iteration_finished),
                        "status": outcome.status,
                        "returncode": outcome.returncode,
                        "duration_seconds": round(outcome.duration_seconds, 6),
                        "stdout": outcome.stdout.to_payload(),
                        "stderr": outcome.stderr.to_payload(),
                        "error_type": outcome.error_type,
                    },
                )
                previous_finished = iteration_finished.astimezone(timezone.utc)
                if outcome.status != "succeeded":
                    terminal_reason = outcome.status
                    break
        finally:
            try:
                append_journal(
                    journal_path,
                    {
                        "event": "run_finished",
                        "name": spec.name,
                        "run_id": run_id,
                        "spec_sha256": spec_digest,
                        "ts": iso_utc(now()),
                        "iterations_started": iteration,
                        "terminal_reason": terminal_reason,
                    },
                )
            finally:
                _remove_marker_for_run(active_path, run_id)
                _remove_marker_for_run(cancellation_path, run_id)
        return LoopRunResult(
            name=spec.name,
            run_id=run_id,
            dry_run=False,
            iterations_started=iteration,
            terminal_reason=terminal_reason,
            journal_path=str(journal_path),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Durable, bounded Watercooler loops")
    parser.add_argument("--root", default="", help="Override the loop state directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    put = subparsers.add_parser("put", help="Create or replace a named loop spec")
    put.add_argument("name")
    put.add_argument("--interval-seconds", type=int, required=True)
    put.add_argument("--count", type=int)
    put.add_argument("--until", default="")
    put.add_argument("--timeout-seconds", type=int, required=True)
    put.add_argument("--cwd", default=str(Path.cwd()))
    put.add_argument("--replace", action="store_true")
    subparsers.add_parser("list", help="List named loop specs")
    show = subparsers.add_parser("show", help="Show one loop spec")
    show.add_argument("name")
    run = subparsers.add_parser("run", help="Plan a loop, or execute it explicitly")
    run.add_argument("name")
    run.add_argument("--execute", action="store_true")
    cancel = subparsers.add_parser("cancel", help="Request cancellation of an active loop")
    cancel.add_argument("name")
    cancel.add_argument("--reason", default="operator_request")
    journal = subparsers.add_parser("journal", help="Read structured journal rows")
    journal.add_argument("name")
    journal.add_argument("--tail", type=int, default=20)
    return parser


def _paths_from_arg(root: str) -> LoopPaths:
    if root:
        return LoopPaths(Path(root).expanduser().resolve())
    return LoopPaths.default()


def main(argv: Sequence[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    put_argv: list[str] = []
    if "put" in raw_args:
        put_index = raw_args.index("put")
        try:
            delimiter = raw_args.index("--", put_index + 1)
        except ValueError:
            delimiter = -1
        if delimiter >= 0:
            put_argv = raw_args[delimiter + 1 :]
            del raw_args[delimiter:]
    args = build_parser().parse_args(raw_args)
    paths = _paths_from_arg(args.root)
    try:
        if args.command == "put":
            until = iso_utc(parse_until(args.until)) if args.until else None
            payload = {
                "version": SPEC_VERSION,
                "name": args.name,
                "argv": put_argv,
                "cwd": str(Path(args.cwd).expanduser().resolve()),
                "interval_seconds": args.interval_seconds,
                "count": args.count,
                "until": until,
                "timeout_seconds": args.timeout_seconds,
            }
            spec = LoopSpec.from_payload(payload)
            path = save_spec(paths, spec, replace=args.replace)
            print(json.dumps({"saved": str(path), "spec": spec.to_payload()}, indent=2))
            return 0
        if args.command == "list":
            print(json.dumps({"loops": [spec.to_payload() for spec in list_specs(paths)]}, indent=2))
            return 0
        if args.command == "show":
            print(json.dumps(load_spec(paths, args.name).to_payload(), indent=2))
            return 0
        if args.command == "run":
            spec = load_spec(paths, args.name)
            result = run_loop(paths, spec, execute=args.execute)
            payload = result.to_payload()
            if result.dry_run:
                payload["spec"] = spec.to_payload()
                payload["semantics"] = {
                    "first_iteration": "immediate",
                    "interval": "fixed_delay_after_finish",
                    "until": "exclusive_start_deadline",
                    "combined_limits": "first_limit_wins",
                    "failure": "stop",
                    "descendants": "foreground_only",
                }
            print(json.dumps(payload, indent=2))
            return 0 if result.dry_run or result.terminal_reason in {"count_reached", "until_reached"} else 1
        if args.command == "cancel":
            requested = request_cancellation(paths, args.name, reason=args.reason)
            print(json.dumps({"name": args.name, "cancellation_requested": requested}, indent=2))
            return 0 if requested else 1
        if args.command == "journal":
            print(json.dumps({"events": read_journal(paths, args.name, tail=args.tail)}, indent=2))
            return 0
    except (AlreadyRunning, LoopError, OSError) as exc:
        print(f"watercooler loop failed: {exc}", file=sys.stderr)
        return 1
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
