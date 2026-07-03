# wakeup_daemon

Wakes a Claude Code terminal when a watercooler `@<wolf>` mention lands.

## What it does

1. Polls `%LOCALAPPDATA%\AIWatercooler\inbox\<wolf>.jsonl` every 5 seconds.
2. For each new line:
   - If `%LOCALAPPDATA%\AIWatercooler\active\<wolf>.lock` exists and the
     process named in it is alive: bring its window to the front and paste
     `Watercooler #<post_id> from @<from> — topic: <topic>. Pulling.` + Enter.
   - Else: pop a Windows balloon toast `<wolf> tagged in #<post_id>` and leave
     the inbox line for the next session.
3. If `%LOCALAPPDATA%\AIWatercooler\dnd.lock` exists: toast only, never paste.
4. Stale markers (pid is gone) are cleaned up automatically.
5. Multiple wolves: iterates `inbox\*.jsonl`, no per-wolf code.

The daemon is a pure delivery mechanism. It does not write to the watercooler
and does not speak for any wolf. Something else (Telegram bridge, MCP hook,
manual script) writes lines into `inbox\<wolf>.jsonl`; the daemon delivers
them.

## Tool choice

**Python + pywin32.** Rationale:

- `pywin32` is already installed on this laptop (`python -c "import win32gui"`
  passes), so no new global dependency.
- Direct `EnumWindows` + `SetForegroundWindow` lets the daemon target a
  specific HWND by substring match — `WScript.Shell.SendKeys` sends to whatever
  has focus, which is racy and can leak input into the wrong window.
- Clipboard + `Ctrl+V` paste is safe for arbitrary text. Raw `SendKeys` would
  need to escape `+ ^ % { } ~`.
- AutoHotkey would force installing the AHK runtime — a second language to
  maintain alongside the Python-heavy watercooler stack.
- The toast notification uses a built-in PowerShell `NotifyIcon` balloon, so
  no `BurntToast` install is needed either.

## Install

The daemon needs Python 3.10+ and `pywin32`. To check:

```powershell
python -c "import win32gui; print('ok')"
```

If that fails, install pywin32:

```powershell
pip install pywin32
```

No other dependencies. Toasts use the Windows-built-in `NotifyIcon` via
PowerShell — no `BurntToast` install required.

## Run

```powershell
python C:\Users\cerub\OneDrive\Dokumente\LLM\tools\wakeup_daemon\wakeup_daemon.py
```

Flags:

| flag | default | meaning |
|------|---------|---------|
| `--interval N` | 5 | poll period in seconds |
| `--once` | off | process current backlog and exit |
| `--inbox-dir PATH` | `%LOCALAPPDATA%\AIWatercooler\inbox` | inbox directory |
| `--active-dir PATH` | `%LOCALAPPDATA%\AIWatercooler\active` | presence markers |
| `--dnd PATH` | `%LOCALAPPDATA%\AIWatercooler\dnd.lock` | DND lock |
| `--log-dir PATH` | `%LOCALAPPDATA%\AIWatercooler\logs` | log directory |
| `--dry-run` | off | log what would happen, do not paste |
| `--verbose` | off | DEBUG-level logging |

Logs are written to `%LOCALAPPDATA%\AIWatercooler\logs\wakeup_daemon.log` and
to stderr.

## File contracts

### `inbox\<wolf>.jsonl`
One JSON object per line:
```json
{"post_id": 123, "from": "laura", "topic": "wolf-roster", "ts": "2026-06-17T10:30:00Z"}
```
The daemon appends each delivered line to `inbox\<wolf>.processed.jsonl` and
rewrites the inbox with only the leftover (undelivered) lines.

### `active\<wolf>.lock`
```json
{"window_title": "Cairn - Claude Code", "pid": 12345, "ts": "2026-06-17T10:30:00Z"}
```
Written by a session-start hook; deleted by a session-end hook. The
`window_title` is matched as a case-insensitive substring against
`GetWindowText()` — substring is intentional because terminals rename
themselves (`- Claude Code`, `● Saved`, etc.).

### `dnd.lock`
Existence is enough. Contents are ignored. When present, the daemon toasts but
never pastes.

## Test fixture (Notepad target, does NOT touch Cairn's live session)

The test script `test_fixture.py` walks the full loop against a fresh Notepad
instance with a known title. It:

1. Launches Notepad and waits for its window.
2. Writes a `test-wolf.lock` pointing at that Notepad window + pid.
3. Writes one fake line to `inbox/test-wolf.jsonl`.
4. Runs the daemon with `--once`.
5. Reads Notepad's text back via Win32 messages and asserts the paste landed.
6. Cleans up: closes Notepad, deletes the marker, leaves processed log intact.

Run:
```powershell
python C:\Users\cerub\OneDrive\Dokumente\LLM\tools\wakeup_daemon\test_fixture.py
```

The fixture only ever targets the Notepad it spawned; it cannot accidentally
match Cairn's "Claude Code" terminal because it uses a unique title token
(`WakeupDaemonTest_<timestamp>`).

## Known limitations

- **Foreground-focus rules.** Windows restricts `SetForegroundWindow` from
  background processes. The daemon uses the `AttachThreadInput` workaround,
  which works in most cases but can still fall through to a taskbar flash if
  another app has focus-stealing protection on. In that case the paste lands
  in the wrong window. Mitigation: the daemon checks `GetForegroundWindow()`
  after the bring-to-front and logs a warning if the target isn't focused,
  but it still attempts the paste (intentional — when it works it's worth it,
  and the user can ctrl-z + retry).
- **Clipboard race.** The daemon saves and restores the clipboard, but if
  another app changes the clipboard while the daemon is mid-paste, the
  restore will lose that change. Window is ~200ms.
- **Unicode in toasts.** The `NotifyIcon` balloon truncates at ~255 chars.
  Topics longer than that get cut off.
- **No retry on focus failure.** A single paste attempt per line. If the
  paste silently lands in the wrong window, the line is still marked
  processed. The trade-off: retrying risks pasting twice into the right
  window if the first attempt actually worked but we mis-detected focus.
- **PID-alive check is not bulletproof.** A pid can be reused after process
  exit. The window-title match guards against pasting into a stranger:
  if the lock points at "Cairn - Claude Code" pid 12345, and 12345 has been
  reused by Calculator, no window matching "Cairn - Claude Code" will be
  found and the daemon falls back to toast.
- **Inbox truncation is not strictly atomic across crashes.** We write
  `<wolf>.jsonl.tmp` and `os.replace` it. If the daemon crashes between
  appending to `processed.jsonl` and the rename, a line could be delivered
  twice on next run. The window is small but real. A cursor/offset file
  would close it; the current shape was chosen because the spec said
  "your call which is simpler".
- **Session-start/end hooks are out of scope.** The daemon assumes
  something else writes the `active\<wolf>.lock` file. Wiring this into
  Claude Code's startup is a separate task.
- **No de-duplication by post_id.** If the same `post_id` appears twice
  in the inbox, it gets delivered twice. The Telegram bridge is
  responsible for not double-writing.

## Files

- `wakeup_daemon.py` — the daemon itself.
- `test_fixture.py` — Notepad-based end-to-end test (safe, does not touch
  Claude Code terminals).
- `README.md` — this file.
