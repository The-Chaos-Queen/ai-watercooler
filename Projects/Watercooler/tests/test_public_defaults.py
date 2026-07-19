from __future__ import annotations

import io
import os
import stat
import subprocess
import sys
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from watercooler import admin, common, post, read, taskboard
from watercooler.service import build_arg_parser, ensure_db, normalize_cors_origins


def test_service_defaults_to_loopback_with_cross_origin_access_disabled(monkeypatch):
    for name in (
        "WATERCOOLER_HOST",
        "WATERCOOLER_PORT",
        "WATERCOOLER_DB_PATH",
        "WATERCOOLER_ADMIN_TOKEN",
        "WATERCOOLER_TOKEN",
        "WATERCOOLER_CORS_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)

    args = build_arg_parser().parse_args([])

    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.db_path == "./watercooler.db"
    assert args.cors_origin == []


def test_cors_origins_are_exact_http_origins():
    assert normalize_cors_origins(
        ["http://127.0.0.1:8000/", "https://console.example.test", "http://127.0.0.1:8000"]
    ) == ("http://127.0.0.1:8000", "https://console.example.test")

    for invalid in (
        "*",
        "null",
        "file://",
        "http://user@example.test",
        "https://example.test/path",
        "http://example.test:bad",
        "http://example.test\n.invalid",
    ):
        with pytest.raises(ValueError):
            normalize_cors_origins([invalid])


def test_shared_transport_ignores_proxies_and_refuses_redirect_before_forwarding_token(
    monkeypatch,
):
    monkeypatch.setattr(
        common.urllib.request,
        "getproxies",
        lambda: {"http": "http://proxy.invalid:8080"},
    )
    proxy_handlers = [
        handler
        for handler in common.build_direct_http_opener().handlers
        if isinstance(handler, common.urllib.request.ProxyHandler)
    ]
    assert proxy_handlers == []

    received_tokens: list[str | None] = []

    class TargetHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            received_tokens.append(self.headers.get("X-Watercooler-Token"))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "11")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        def log_message(self, _format, *_args):
            return

    target = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self):
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
        with pytest.raises(common.WatercoolerError, match="HTTP 302"):
            common.request_json(
                {
                    "base_url": f"http://127.0.0.1:{source.server_port}",
                    "token": "sentinel-token",
                },
                method="GET",
                path="/v1/messages",
            )
    finally:
        for server in (source, target):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)

    assert received_tokens == []


def test_read_and_post_clients_delegate_to_hardened_transport(monkeypatch, capsys):
    config = {
        "base_url": "http://127.0.0.1:8765",
        "token": "sentinel-token",
        "principal": "reviewer-1",
        "_config_path": "session.json",
    }
    calls = []

    monkeypatch.setattr(read, "load_config", lambda _path: config)
    monkeypatch.setattr(post, "load_config", lambda _path: config)

    def fake_request_json(request_config, **kwargs):
        assert request_config is config
        calls.append(kwargs)
        if kwargs["path"] == "/v1/messages":
            return {"messages": []}
        return {"ok": True, "message": {"id": 1}}

    monkeypatch.setattr(read, "request_json", fake_request_json)
    monkeypatch.setattr(post, "request_json", fake_request_json)

    monkeypatch.setattr(sys, "argv", ["watercooler-read", "--thread", "demo", "--limit", "7"])
    assert read.main() == 0
    assert "No messages." in capsys.readouterr().out

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "watercooler-post",
            "--config",
            "session.json",
            "--thread",
            "demo",
            "--body",
            "ready",
        ],
    )
    assert post.main() == 0
    capsys.readouterr()

    assert calls == [
        {
            "method": "GET",
            "path": "/v1/messages",
            "query": {"limit": "7", "thread": "demo"},
        },
        {
            "method": "POST",
            "path": "/v1/post",
            "payload": {
                "from_agent": "reviewer-1",
                "to_agent": "",
                "thread": "demo",
                "topic": "",
                "lang": "en",
                "tags": [],
                "body": "ready",
            },
        },
    ]


def test_shared_transport_bounds_success_and_error_responses(monkeypatch):
    url = "http://watercooler.test/v1/messages"
    success_reads: list[int] = []

    class OversizedResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def geturl(self):
            return url

        def read(self, size=-1):
            success_reads.append(size)
            return b"x" * size

    class SuccessOpener:
        def open(self, _request, *, timeout):
            assert timeout == 15
            return OversizedResponse()

    monkeypatch.setattr(common, "build_direct_http_opener", lambda: SuccessOpener())
    config = {"base_url": "http://watercooler.test", "token": "sentinel"}
    with pytest.raises(common.WatercoolerError, match="response exceeds"):
        common.request_json(config, method="GET", path="/v1/messages")
    assert success_reads == [common.MAX_RESPONSE_BYTES + 1]

    error_reads: list[int] = []

    class ErrorBody(io.BytesIO):
        def read(self, size=-1):
            error_reads.append(size)
            return super().read(size)

    failure = urllib.error.HTTPError(
        url,
        500,
        "failure",
        {},
        ErrorBody(b"e" * (common.MAX_ERROR_RESPONSE_BYTES + 100)),
    )

    class ErrorOpener:
        def open(self, _request, *, timeout):
            raise failure

    monkeypatch.setattr(common, "build_direct_http_opener", lambda: ErrorOpener())
    with pytest.raises(common.WatercoolerError, match="error response exceeds"):
        common.request_json(config, method="GET", path="/v1/messages")
    assert error_reads == [common.MAX_ERROR_RESPONSE_BYTES + 1]


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode contract")
def test_generated_session_config_repairs_owner_only_directory_and_file(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir(mode=0o777)
    sessions.chmod(0o777)
    config_path = sessions / "reviewer.json"

    admin.write_session_config(config_path, {"token": "sentinel"})

    assert stat.S_IMODE(sessions.stat().st_mode) == 0o700
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode contract")
def test_database_preserves_existing_parent_and_makes_database_private(tmp_path):
    database_root = tmp_path / "database"
    database_root.mkdir(mode=0o777)
    database_root.chmod(0o777)
    db_path = database_root / "watercooler.db"

    ensure_db(db_path)
    db_path.chmod(0o666)
    ensure_db(db_path)

    assert stat.S_IMODE(database_root.stat().st_mode) == 0o777
    assert stat.S_IMODE(db_path.stat().st_mode) == 0o600

    new_database_root = tmp_path / "new-database"
    new_db_path = new_database_root / "watercooler.db"
    ensure_db(new_db_path)

    assert stat.S_IMODE(new_database_root.stat().st_mode) == 0o700
    assert stat.S_IMODE(new_db_path.stat().st_mode) == 0o600


def test_taskboard_requires_declared_token_principal():
    with pytest.raises(SystemExit, match="token-bound principal"):
        taskboard.config_principal({})


def test_taskboard_forces_utf8_stdout_on_legacy_windows_console_encoding():
    source_root = Path(__file__).resolve().parents[1] / "src"
    environment = {
        **os.environ,
        "PYTHONIOENCODING": "cp1252",
        "PYTHONPATH": str(source_root),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from watercooler import taskboard; print('context \\u2192 message')",
        ],
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stdout.decode("utf-8").strip() == "context \u2192 message"


def test_web_console_never_parses_server_values_as_html_or_url_tokens():
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")

    assert "innerHTML" not in html
    assert "outerHTML" not in html
    assert "insertAdjacentHTML" not in html
    assert "document.write" not in html
    assert "location.hash" not in html
    assert "hash.get(\"token\")" not in html
    assert "resolveWatercoolerBase" in html
    assert 'hostname === "127.0.0.1"' in html
    assert "Generated, unreviewed orientation" in html


def test_web_console_persists_only_the_theme_preference():
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")

    assert 'id="theme-toggle"' in html
    assert 'aria-label="Use dark theme"' in html
    assert "ai-watercooler-theme" in html
    assert "prefers-color-scheme: dark" in html
    assert ':root[data-theme="dark"]' in html
    assert "window.localStorage.setItem(THEME_STORAGE_KEY, next)" in html
    assert html.count("localStorage.setItem(") == 1
    assert "localStorage.setItem(\"token\"" not in html


def test_web_console_uses_the_current_onboarding_snapshot_contract():
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")

    assert "summary.content" in html
    assert "summary.structured_content" not in html
    assert "coverageWarning(payload.delta)" in html
    assert "delta?.coverage_known" in html
    assert "delta?.complete" in html
    assert "payload.authoritative_taskboard" in html
    assert "payload.coverage_warning" not in html
    assert "payload.complete" not in html
    assert "payload.taskboard" not in html
    assert "Summary coverage is unknown; recent messages are not a complete delta." in html
    assert "Summary delta is incomplete; the latest messages shown are not the full uncovered set." in html
