#!/usr/bin/env python3
r"""
wakeup_daemon.py - Wakes a Claude Code terminal when a watercooler @<wolf>
mention arrives.

Watches %LOCALAPPDATA%\AIWatercooler\inbox\<wolf>.jsonl, looks up the wolf's
session-presence marker, and pastes a notification + Enter into the right
terminal window. Falls back to a Windows toast notification if the wolf is
not home or DND is active.

This daemon is a delivery mechanism only. It does NOT post to the watercooler,
read it, or speak for any wolf. Something else (the Telegram bridge, an MCP
hook, manual scripting) writes JSONL lines into inbox/<wolf>.jsonl. We then
deliver them.

Tool choice: Python + pywin32. pywin32 is already installed on this machine,
so no new dependencies are required. See README for the full rationale.

Run:
    python tools/wakeup_daemon/wakeup_daemon.py

Optional flags:
    --interval N        Poll period in seconds (default 5)
    --once              Process current backlog and exit (for testing)
    --inbox-dir PATH    Override inbox directory
    --active-dir PATH   Override active-markers directory
    --dnd PATH          Override DND lock path
    --dry-run           Don't actually paste; print what would happen
    --verbose           Debug logging
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

# pywin32
import win32api
import win32clipboard
import win32con
import win32gui
import win32process

LOG = logging.getLogger("wakeup_daemon")

DEFAULT_BASE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AIWatercooler"
DEFAULT_INBOX_DIR = DEFAULT_BASE / "inbox"
DEFAULT_ACTIVE_DIR = DEFAULT_BASE / "active"
DEFAULT_DND_LOCK = DEFAULT_BASE / "dnd.lock"
DEFAULT_LOG_DIR = DEFAULT_BASE / "logs"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class InboxLine:
    raw: str
    post_id: int
    sender: str
    topic: str
    ts: str

    @classmethod
    def parse(cls, raw: str) -> Optional["InboxLine"]:
        raw = raw.rstrip("\r\n")
        if not raw.strip():
            return None
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            LOG.warning("malformed inbox line skipped: %s (line=%r)", exc, raw[:120])
            return None
        try:
            return cls(
                raw=raw,
                post_id=int(obj["post_id"]),
                sender=str(obj.get("from", "?")),
                topic=str(obj.get("topic", "")),
                ts=str(obj.get("ts", "")),
            )
        except (KeyError, ValueError, TypeError) as exc:
            LOG.warning("inbox line missing required fields: %s (line=%r)", exc, raw[:120])
            return None


@dataclass
class PresenceMarker:
    window_title: str
    pid: int
    ts: str

    @classmethod
    def load(cls, path: Path) -> Optional["PresenceMarker"]:
        try:
            with path.open("r", encoding="utf-8") as f:
                obj = json.load(f)
            return cls(
                window_title=str(obj.get("window_title", "")),
                pid=int(obj.get("pid", 0)),
                ts=str(obj.get("ts", "")),
            )
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
            LOG.warning("active marker %s unreadable: %s", path, exc)
            return None


# ---------------------------------------------------------------------------
# Window discovery + focus
# ---------------------------------------------------------------------------


def find_window(title_substring: str, pid_hint: int = 0) -> Optional[int]:
    """Return an HWND matching ``title_substring`` (case-insensitive substring).

    If ``pid_hint`` is given and matches a window, prefer that window. We do not
    require the pid match because terminals often spawn child processes whose
    window belongs to the parent shell host.
    """
    needle = title_substring.strip().lower()
    if not needle:
        return None

    candidates: list[tuple[int, str, int]] = []  # hwnd, title, pid

    def _cb(hwnd: int, _arg) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd) or ""
        if not title:
            return True
        if needle in title.lower():
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:  # noqa: BLE001
                pid = 0
            candidates.append((hwnd, title, pid))
        return True

    win32gui.EnumWindows(_cb, None)

    if not candidates:
        return None

    if pid_hint:
        for hwnd, _, pid in candidates:
            if pid == pid_hint:
                return hwnd

    # Prefer the candidate with the shortest title (closest substring match)
    # — terminal renames often append `- ClaudeCode` etc; the canonical name
    # is usually the shortest.
    candidates.sort(key=lambda c: len(c[1]))
    return candidates[0][0]


def pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = None
    try:
        handle = win32api.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        exit_code = win32process.GetExitCodeProcess(handle)
        # STILL_ACTIVE == 259
        return exit_code == 259
    except Exception:  # noqa: BLE001
        return False
    finally:
        if handle:
            try:
                win32api.CloseHandle(handle)
            except Exception:  # noqa: BLE001
                pass


def bring_to_foreground(hwnd: int) -> bool:
    """Bring ``hwnd`` to the foreground, working around SetForegroundWindow's
    rules by attaching to the current foreground thread.
    """
    try:
        # Restore if minimised
        placement = win32gui.GetWindowPlacement(hwnd)
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        fg = win32gui.GetForegroundWindow()
        if fg == hwnd:
            return True

        cur_thread = win32api.GetCurrentThreadId()
        fg_thread, _ = win32process.GetWindowThreadProcessId(fg) if fg else (0, 0)
        tgt_thread, _ = win32process.GetWindowThreadProcessId(hwnd)

        attached_fg = False
        attached_tgt = False
        try:
            if fg_thread and fg_thread != cur_thread:
                win32process.AttachThreadInput(cur_thread, fg_thread, True)
                attached_fg = True
            if tgt_thread and tgt_thread != cur_thread and tgt_thread != fg_thread:
                win32process.AttachThreadInput(cur_thread, tgt_thread, True)
                attached_tgt = True
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            if attached_fg:
                try:
                    win32process.AttachThreadInput(cur_thread, fg_thread, False)
                except Exception:  # noqa: BLE001
                    pass
            if attached_tgt:
                try:
                    win32process.AttachThreadInput(cur_thread, tgt_thread, False)
                except Exception:  # noqa: BLE001
                    pass

        # Give the window manager a moment
        time.sleep(0.15)
        return win32gui.GetForegroundWindow() == hwnd
    except Exception as exc:  # noqa: BLE001
        LOG.warning("bring_to_foreground failed for hwnd=%s: %s", hwnd, exc)
        return False


# ---------------------------------------------------------------------------
# Clipboard + keystroke paste
# ---------------------------------------------------------------------------


def _set_clipboard_text(text: str) -> bool:
    for attempt in range(5):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception as exc:  # noqa: BLE001
            LOG.debug("clipboard busy (try %d): %s", attempt + 1, exc)
            time.sleep(0.1)
    LOG.error("could not set clipboard after retries")
    return False


def _get_clipboard_text() -> Optional[str]:
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            return None
        finally:
            win32clipboard.CloseClipboard()
    except Exception:  # noqa: BLE001
        return None


# Virtual-key codes
VK_CONTROL = 0x11
VK_V = 0x56
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002


def _send_key(vk: int, key_up: bool = False) -> None:
    win32api.keybd_event(vk, 0, KEYEVENTF_KEYUP if key_up else 0, 0)


def paste_and_enter(text: str) -> bool:
    """Set ``text`` on the clipboard, send Ctrl+V, send Enter. Restore the
    previous clipboard contents on a best-effort basis.
    """
    prev = _get_clipboard_text()

    if not _set_clipboard_text(text):
        return False

    try:
        # Ctrl+V
        _send_key(VK_CONTROL)
        time.sleep(0.02)
        _send_key(VK_V)
        time.sleep(0.05)
        _send_key(VK_V, key_up=True)
        time.sleep(0.02)
        _send_key(VK_CONTROL, key_up=True)
        time.sleep(0.2)
        # Enter
        _send_key(VK_RETURN)
        time.sleep(0.05)
        _send_key(VK_RETURN, key_up=True)
        time.sleep(0.1)
    finally:
        # Restore clipboard on a delay so the paste actually grabs our text.
        if prev is not None:
            time.sleep(0.2)
            _set_clipboard_text(prev)
    return True


# ---------------------------------------------------------------------------
# Toast notification (no extra deps; uses built-in PowerShell + NotifyIcon)
# ---------------------------------------------------------------------------


_TOAST_PS_TEMPLATE = r"""
[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null
[System.Reflection.Assembly]::LoadWithPartialName('System.Drawing') | Out-Null
$ni = New-Object System.Windows.Forms.NotifyIcon
$ni.Icon = [System.Drawing.SystemIcons]::Information
$ni.Visible = $true
$ni.BalloonTipTitle = $env:WAKEUP_TITLE
$ni.BalloonTipText = $env:WAKEUP_BODY
$ni.ShowBalloonTip(5000)
Start-Sleep -Milliseconds 5500
$ni.Dispose()
"""


def show_toast(title: str, body: str) -> None:
    """Fire-and-forget Windows balloon notification. Best-effort; never raises."""
    try:
        env = os.environ.copy()
        env["WAKEUP_TITLE"] = title
        env["WAKEUP_BODY"] = body
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                _TOAST_PS_TEMPLATE,
            ],
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:  # noqa: BLE001
        LOG.warning("toast notification failed: %s", exc)


# ---------------------------------------------------------------------------
# Inbox processing
# ---------------------------------------------------------------------------


def iter_wolves(inbox_dir: Path) -> Iterable[str]:
    if not inbox_dir.exists():
        return
    for entry in sorted(inbox_dir.glob("*.jsonl")):
        if entry.name.endswith(".processed.jsonl"):
            continue
        yield entry.stem


def read_inbox_lines(path: Path) -> List[InboxLine]:
    if not path.exists():
        return []
    out: list[InboxLine] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            parsed = InboxLine.parse(raw)
            if parsed is not None:
                out.append(parsed)
    return out


def append_processed(processed_path: Path, line: InboxLine) -> None:
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    with processed_path.open("a", encoding="utf-8") as f:
        f.write(line.raw)
        if not line.raw.endswith("\n"):
            f.write("\n")


def truncate_inbox_keeping(path: Path, remaining: List[InboxLine]) -> None:
    """Atomic-ish truncate: write to .tmp then replace."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for line in remaining:
            f.write(line.raw)
            if not line.raw.endswith("\n"):
                f.write("\n")
    os.replace(tmp, path)


def format_paste(line: InboxLine) -> str:
    return (
        f"Watercooler #{line.post_id} from @{line.sender} "
        f"— topic: {line.topic}. Pulling."
    )


def format_toast(wolf: str, line: InboxLine) -> tuple[str, str]:
    title = f"{wolf} tagged in #{line.post_id}"
    body = f"@{line.sender} in '{line.topic}'"
    return title, body


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


@dataclass
class DaemonConfig:
    inbox_dir: Path
    active_dir: Path
    dnd_lock: Path
    log_dir: Path
    interval: float
    dry_run: bool


def process_wolf(wolf: str, cfg: DaemonConfig) -> int:
    """Process all pending lines for ``wolf``. Returns the number delivered."""
    inbox_path = cfg.inbox_dir / f"{wolf}.jsonl"
    processed_path = cfg.inbox_dir / f"{wolf}.processed.jsonl"
    marker_path = cfg.active_dir / f"{wolf}.lock"

    lines = read_inbox_lines(inbox_path)
    if not lines:
        return 0

    dnd_active = cfg.dnd_lock.exists()
    marker = PresenceMarker.load(marker_path)

    # Sanity check the marker: if the pid is gone, clean up and treat as away.
    if marker and marker.pid and not pid_is_alive(marker.pid):
        LOG.info("stale marker for %s (pid=%d dead) — removing", wolf, marker.pid)
        try:
            marker_path.unlink()
        except OSError as exc:
            LOG.warning("could not remove stale marker %s: %s", marker_path, exc)
        marker = None

    delivered_count = 0
    leftover: list[InboxLine] = []

    for line in lines:
        LOG.info(
            "inbox %s: post=%d from=%s topic=%s",
            wolf,
            line.post_id,
            line.sender,
            line.topic,
        )

        if marker is None:
            # Not home — toast only, keep line for next time.
            LOG.info("%s not home; toasting and leaving line in inbox", wolf)
            t_title, t_body = format_toast(wolf, line)
            if not cfg.dry_run:
                show_toast(t_title, t_body)
            leftover.append(line)
            continue

        if dnd_active:
            LOG.info("DND active; toasting only for %s", wolf)
            t_title, t_body = format_toast(wolf, line)
            if not cfg.dry_run:
                show_toast(t_title, t_body)
            # Still mark as processed — DND is "I saw it, don't paste".
            append_processed(processed_path, line)
            delivered_count += 1
            continue

        # Wolf is home, DND off — paste into the terminal.
        hwnd = find_window(marker.window_title, pid_hint=marker.pid)
        if not hwnd:
            LOG.warning(
                "%s home but no window matching %r; falling back to toast",
                wolf,
                marker.window_title,
            )
            t_title, t_body = format_toast(wolf, line)
            if not cfg.dry_run:
                show_toast(t_title, t_body)
            leftover.append(line)
            continue

        text = format_paste(line)
        if cfg.dry_run:
            LOG.info("[dry-run] would paste into hwnd=%s: %s", hwnd, text)
            append_processed(processed_path, line)
            delivered_count += 1
            continue

        if not bring_to_foreground(hwnd):
            LOG.warning("could not foreground hwnd=%s; trying paste anyway", hwnd)
        # Tiny extra settle so the terminal's input field is ready.
        time.sleep(0.1)
        if paste_and_enter(text):
            LOG.info("delivered post=%d to %s (hwnd=%s)", line.post_id, wolf, hwnd)
            append_processed(processed_path, line)
            delivered_count += 1
        else:
            LOG.error("paste failed for post=%d %s; leaving in inbox", line.post_id, wolf)
            leftover.append(line)

    # Rewrite the inbox with only the unprocessed lines.
    if leftover != lines:
        truncate_inbox_keeping(inbox_path, leftover)

    return delivered_count


def run_once(cfg: DaemonConfig) -> int:
    total = 0
    for wolf in iter_wolves(cfg.inbox_dir):
        try:
            total += process_wolf(wolf, cfg)
        except Exception as exc:  # noqa: BLE001
            LOG.exception("error processing wolf=%s: %s", wolf, exc)
    return total


def run_forever(cfg: DaemonConfig) -> None:
    LOG.info(
        "wakeup_daemon running: inbox=%s active=%s interval=%ss dnd=%s dry_run=%s",
        cfg.inbox_dir,
        cfg.active_dir,
        cfg.interval,
        cfg.dnd_lock,
        cfg.dry_run,
    )
    while True:
        try:
            run_once(cfg)
        except KeyboardInterrupt:
            LOG.info("interrupted; exiting")
            return
        except Exception as exc:  # noqa: BLE001
            LOG.exception("loop error: %s", exc)
        time.sleep(cfg.interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _setup_logging(verbose: bool, log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "wakeup_daemon.log"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    try:
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def build_config(args: argparse.Namespace) -> DaemonConfig:
    return DaemonConfig(
        inbox_dir=Path(args.inbox_dir).expanduser(),
        active_dir=Path(args.active_dir).expanduser(),
        dnd_lock=Path(args.dnd).expanduser(),
        log_dir=Path(args.log_dir).expanduser(),
        interval=float(args.interval),
        dry_run=bool(args.dry_run),
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Watercooler wakeup daemon")
    parser.add_argument("--inbox-dir", default=str(DEFAULT_INBOX_DIR))
    parser.add_argument("--active-dir", default=str(DEFAULT_ACTIVE_DIR))
    parser.add_argument("--dnd", default=str(DEFAULT_DND_LOCK))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    cfg = build_config(args)
    cfg.inbox_dir.mkdir(parents=True, exist_ok=True)
    cfg.active_dir.mkdir(parents=True, exist_ok=True)
    _setup_logging(args.verbose, cfg.log_dir)

    if args.once:
        n = run_once(cfg)
        LOG.info("processed %d line(s) in one-shot mode", n)
        return 0

    try:
        run_forever(cfg)
    except KeyboardInterrupt:
        LOG.info("interrupted; exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
