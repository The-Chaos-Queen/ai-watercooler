#!/usr/bin/env python3
"""
test_fixture.py - End-to-end test for wakeup_daemon against a fresh PowerShell
console with a unique window title.

Does NOT touch Cairn's live Claude Code terminal: spawns its own console with
a unique title token so the daemon's window-substring match cannot collide
with any real terminal.

Why PowerShell and not Notepad: modern Notepad (a) runs the window in a
different pid than the launcher, (b) overwrites SetWindowText changes after
launch, and (c) is multi-tab so a shared process can host Laura's other docs
too. A PowerShell console is a clean isolated target — it's the same shape as
a Claude Code terminal (text input via stdin + Enter), and PowerShell can set
its own window title reliably via $Host.UI.RawUI.WindowTitle.

What the fixture does:
1. Create a tempfile log path.
2. Launch a new PowerShell console with a unique title. The console runs a
   Read-Host loop that writes every line entered to the log file.
3. Write a presence marker pointing at the console title + window pid.
4. Write one fake inbox line for ``test-wolf``.
5. Run wakeup_daemon with --once. The daemon should focus the console and
   paste the notification + Enter.
6. Read the log file; assert the pasted text appears.
7. Clean up: kill the PowerShell process, delete marker and log.

Exits 0 on success, 1 on any failure.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import win32api
import win32con
import win32gui
import win32process

HERE = Path(__file__).resolve().parent
DAEMON = HERE / "wakeup_daemon.py"

BASE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AIWatercooler"
INBOX_DIR = BASE / "inbox"
ACTIVE_DIR = BASE / "active"

WOLF = "test-wolf"
UNIQUE_TOKEN = f"WakeupDaemonTest_{int(time.time())}"

CREATE_NEW_CONSOLE = 0x00000010


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_window_by_title(needle: str, timeout: float = 8.0) -> Optional[int]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        hits: list[int] = []

        def _cb(hwnd: int, _arg) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd) or ""
            if needle in title:
                hits.append(hwnd)
            return True

        win32gui.EnumWindows(_cb, None)
        if hits:
            return hits[0]
        time.sleep(0.25)
    return None


def get_window_pid(hwnd: int) -> int:
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return int(pid)
    except Exception:  # noqa: BLE001
        return 0


def write_marker(window_title: str, pid: int) -> Path:
    ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
    p = ACTIVE_DIR / f"{WOLF}.lock"
    p.write_text(
        json.dumps(
            {"window_title": window_title, "pid": pid, "ts": now_iso()},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


def write_inbox_line() -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    p = INBOX_DIR / f"{WOLF}.jsonl"
    line = {
        "post_id": 9999,
        "from": "laura",
        "topic": "wakeup-fixture",
        "ts": now_iso(),
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return p


def cleanup(launcher_pid: int, marker: Optional[Path], log_path: Optional[Path]) -> None:
    if marker and marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass
    if launcher_pid:
        try:
            os.kill(launcher_pid, signal.SIGTERM)
        except OSError:
            pass
    # Give it a moment, then force.
    time.sleep(0.5)
    if launcher_pid:
        try:
            os.kill(launcher_pid, signal.SIGKILL if hasattr(signal, "SIGKILL") else 9)
        except OSError:
            pass
    if log_path and log_path.exists():
        try:
            log_path.unlink()
        except OSError:
            pass


def build_ps_command(unique: str, log_path: str) -> list[str]:
    """Build the PowerShell command for the spawned console.

    The console:
      - Sets its own window title (so we can find it).
      - Opens an append stream to log_path.
      - Loops reading lines and writes every line received to log_path.
    """
    # We do the work in a single-line script using Out-File for line-by-line
    # writes to keep the inner shell simple.
    inner = (
        f"$Host.UI.RawUI.WindowTitle = '{unique}'; "
        f"$log = '{log_path}'; "
        "Write-Host 'READY' ; "
        "while ($true) { "
        "  $line = Read-Host ; "
        "  if ($null -ne $line) { "
        f"    Add-Content -Path $log -Value $line -Encoding utf8 "
        "  } "
        "}"
    )
    return ["powershell", "-NoExit", "-NoProfile", "-Command", inner]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Don't close console / delete marker at end (for manual inspection).",
    )
    args = parser.parse_args()

    print(f"[fixture] base dir: {BASE}")
    print(f"[fixture] unique window token: {UNIQUE_TOKEN}")

    # Create the log file the PS console will write to.
    log_fd, log_path_str = tempfile.mkstemp(prefix="wakeup_fixture_", suffix=".log")
    os.close(log_fd)
    log_path = Path(log_path_str)
    # Ensure the file starts empty.
    log_path.write_text("", encoding="utf-8")
    print(f"[fixture] log path: {log_path}")

    # Launch a new console.
    cmd = build_ps_command(UNIQUE_TOKEN, log_path_str.replace("\\", "\\\\"))
    proc = subprocess.Popen(cmd, creationflags=CREATE_NEW_CONSOLE)
    print(f"[fixture] launched powershell pid={proc.pid}")

    # Wait for the window with our unique title.
    hwnd = find_window_by_title(UNIQUE_TOKEN, timeout=8.0)
    if not hwnd:
        print("[fixture] FAILED: could not find PowerShell console with unique title")
        cleanup(proc.pid, None, log_path)
        return 1
    owner_pid = get_window_pid(hwnd)
    actual_title = win32gui.GetWindowText(hwnd)
    print(
        f"[fixture] found console hwnd={hwnd} owner_pid={owner_pid} title={actual_title!r}"
    )

    # Wait a moment for the Read-Host loop to be ready.
    time.sleep(0.8)

    # Write marker + inbox line.
    # The marker uses the owner_pid (which is conhost.exe in modern Windows).
    marker = write_marker(UNIQUE_TOKEN, owner_pid)
    inbox = write_inbox_line()
    print(f"[fixture] wrote marker {marker}")
    print(f"[fixture] wrote inbox {inbox}")

    # Run daemon once.
    print("[fixture] running daemon --once ...")
    result = subprocess.run(
        [sys.executable, str(DAEMON), "--once", "--verbose"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"[fixture] daemon exit={result.returncode}")
    if result.stderr:
        print("[fixture] daemon stderr:")
        print(result.stderr)

    # Give the console a tick to process the paste + Enter.
    time.sleep(1.0)

    # Read back the log. PowerShell's Add-Content may have written UTF-16LE
    # despite our -Encoding utf8 hint on Windows PowerShell 5.1 (the flag is
    # honored but the file may include a UTF-8 BOM), so be liberal.
    log_text = ""
    for enc in ("utf-8-sig", "utf-8", "utf-16-le", "utf-16", "cp1252"):
        try:
            log_text = log_path.read_text(encoding=enc)
            print(f"[fixture] read log as {enc}")
            break
        except (UnicodeDecodeError, OSError):
            continue
    if not log_text:
        try:
            log_text = log_path.read_bytes().decode("utf-8", errors="replace")
            print(f"[fixture] read log as utf-8 with replacement")
        except OSError as exc:
            print(f"[fixture] could not read log: {exc}")
    print(f"[fixture] log content ({len(log_text)} chars): {log_text!r}")

    expected_fragment = "Watercooler #9999 from @laura"
    success = expected_fragment in log_text
    if success:
        print(f"[fixture] PASS: found {expected_fragment!r} in console log")
    else:
        print(f"[fixture] FAIL: did not find {expected_fragment!r} in console log")

    # Inbox truncation check.
    processed = INBOX_DIR / f"{WOLF}.processed.jsonl"
    if processed.exists():
        proc_content = processed.read_text(encoding="utf-8")
        if "9999" in proc_content:
            print(f"[fixture] PASS: processed log contains post 9999")
        else:
            print(f"[fixture] FAIL: processed log missing post 9999: {proc_content!r}")
            success = False
    else:
        print(f"[fixture] FAIL: no processed log at {processed}")
        success = False

    if inbox.exists():
        leftover = inbox.read_text(encoding="utf-8").strip()
        if leftover:
            print(f"[fixture] WARN: inbox not empty after processing: {leftover!r}")
        else:
            print(f"[fixture] PASS: inbox truncated to empty")
    else:
        print(f"[fixture] PASS: inbox file removed (also acceptable)")

    if not args.keep:
        print("[fixture] cleaning up")
        cleanup(proc.pid, marker, log_path)
    else:
        print(
            f"[fixture] --keep set; ps pid={proc.pid}, marker={marker}, log={log_path}"
        )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
