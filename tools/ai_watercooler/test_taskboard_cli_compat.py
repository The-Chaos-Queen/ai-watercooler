from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import openclaw  # noqa: E402
import taskboard  # noqa: E402


EXPECTED_COMMANDS = {
    "block",
    "board",
    "claim",
    "comment",
    "complete",
    "context",
    "create",
    "heartbeat",
    "list",
    "liveness",
    "next",
    "reopen",
    "reassign",
    "release",
    "unblock",
}


def test_taskboard_parser_preserves_commands_and_uses_canonical_name():
    parser = taskboard.build_parser()
    help_text = parser.format_help()

    assert parser.description == "Watercooler Taskboard CLI"
    assert "OpenCLAW" not in help_text
    assert EXPECTED_COMMANDS == {
        choice
        for action in parser._actions
        if hasattr(action, "choices") and action.choices
        for choice in action.choices
    }


def test_openclaw_import_reexports_public_cli_symbols_without_warning():
    assert openclaw.build_parser is taskboard.build_parser
    assert openclaw.handle_create is taskboard.handle_create
    assert openclaw.main is taskboard.main


def test_openclaw_script_warns_and_delegates_to_taskboard_help():
    script = Path(__file__).with_name("openclaw.py")
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "Watercooler Taskboard CLI" in result.stdout
    assert "DeprecationWarning: openclaw.py is deprecated; use taskboard.py" in result.stderr


def test_reopen_cli_routes_to_audited_lifecycle_endpoint(monkeypatch, capsys):
    parser = taskboard.build_parser()
    args = parser.parse_args(
        ["reopen", "--task-id", "17", "--note", "late review finding", "--json"]
    )
    seen = {}

    def fake_request(config, *, method, path, payload):
        seen.update({"config": config, "method": method, "path": path, "payload": payload})
        return {"ok": True, "task": {"id": 17, "status": "queued"}}

    monkeypatch.setattr(taskboard, "request_json", fake_request)

    assert args.handler(args, {"principal": "techno-monk"}) == 0
    assert seen == {
        "config": {"principal": "techno-monk"},
        "method": "POST",
        "path": "/v1/tasks/reopen",
        "payload": {
            "task_id": 17,
            "agent": "techno-monk",
            "note": "late review finding",
        },
    }
    assert json.loads(capsys.readouterr().out)["task"]["status"] == "queued"


def test_taskboard_forces_utf8_stdout_on_legacy_windows_console_encoding():
    module_dir = Path(__file__).resolve().parent
    environment = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                f"import sys; sys.path.insert(0, {str(module_dir)!r}); "
                "import taskboard; print('context \\u2192 message')"
            ),
        ],
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stdout.decode("utf-8").strip() == "context \u2192 message"
