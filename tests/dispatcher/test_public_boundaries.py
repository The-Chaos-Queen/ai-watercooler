from __future__ import annotations

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from watercooler.common import WatercoolerError
from watercooler.dispatcher import commit_review as dispatch
from watercooler.dispatcher import transport

INTEGRATION_ROOT = Path(__file__).resolve().parents[2] / "integrations" / "codex-reviewer"


@pytest.mark.parametrize(
    ("endpoint", "mode", "expected"),
    [
        ("http://127.0.0.1:8765/", "loopback_http", "http://127.0.0.1:8765"),
        ("http://[::1]:8765", "loopback_http", "http://[::1]:8765"),
        ("https://watercooler.example:8443/", "https", "https://watercooler.example:8443"),
    ],
)
def test_transport_modes_accept_only_their_exact_origin(endpoint, mode, expected):
    assert dispatch.validate_policy_endpoint(endpoint, mode) == expected


@pytest.mark.parametrize(
    ("endpoint", "mode"),
    [
        ("http://localhost:8765", "loopback_http"),
        ("http://192.0.2.1:8765", "loopback_http"),
        ("https://127.0.0.1:8765", "loopback_http"),
        ("http://watercooler.example", "https"),
        ("https://user:password@watercooler.example", "https"),
        ("https://watercooler.example/api", "https"),
        ("https://watercooler.example?mode=review", "https"),
        ("https://watercooler.example#fragment", "https"),
        ("https://watercooler.example", "custom"),
    ],
)
def test_transport_modes_fail_closed(endpoint, mode):
    with pytest.raises(dispatch.DispatchError):
        dispatch.validate_policy_endpoint(endpoint, mode)


def test_example_policy_is_non_operational_and_uses_generic_direct_docker():
    path = INTEGRATION_ROOT / "dispatcher-policy.example.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    loaded = dispatch.load_policy(path)

    assert loaded.worker_backend == "docker"
    assert loaded.wsl_distribution == ""
    assert loaded.docker_image.startswith("org.watercooler/")
    assert raw["docker_image_id"] == "sha256:" + "0" * 64
    assert raw["model"] == "REPLACE_WITH_MODEL_ID"
    assert "token" not in raw


def test_review_schema_matches_the_runtime_result_contract():
    schema = json.loads((INTEGRATION_ROOT / "review-schema.json").read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == dispatch.RESULT_KEYS
    assert set(schema["properties"]["status"]["enum"]) == {
        "FINDINGS",
        "NO_FINDINGS",
        "BLOCKED",
    }
    assert schema["properties"]["findings"]["maxItems"] == dispatch.MAX_FINDINGS


def test_integration_assets_have_generic_labels_and_no_credential_discovery():
    dockerfile = (INTEGRATION_ROOT / "Dockerfile").read_text(encoding="utf-8")
    windows = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((INTEGRATION_ROOT / "windows").iterdir())
    )

    assert "org.watercooler.codex-reviewer.cli-version" in dockerfile
    assert "Get-ChildItem" not in windows
    assert "-ConfigPath" in windows
    assert "-RepoRoot" in windows
    assert "-CodexAuthFile" in windows
    assert "Watercooler\\commit_review_dispatch" in windows


def test_policy_requires_empty_distribution_for_direct_docker(tmp_path):
    raw = json.loads(
        (INTEGRATION_ROOT / "dispatcher-policy.example.json").read_text(encoding="utf-8")
    )
    raw["wsl_distribution"] = "SomeDistribution"
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(dispatch.DispatchError, match="empty wsl_distribution"):
        dispatch.load_policy(path)


def test_policy_requires_distribution_for_wsl_docker(tmp_path):
    raw = json.loads(
        (INTEGRATION_ROOT / "dispatcher-policy.example.json").read_text(encoding="utf-8")
    )
    raw["worker_backend"] = "wsl_docker"
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(dispatch.DispatchError, match="requires a valid"):
        dispatch.load_policy(path)


def test_repo_root_must_be_the_exact_git_top_level(tmp_path):
    repo = tmp_path / "repo"
    child = repo / "child"
    child.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

    dispatch.validate_repo_root(repo)
    with pytest.raises(dispatch.DispatchError, match="exact Git root"):
        dispatch.validate_repo_root(child)
    with pytest.raises(dispatch.DispatchError, match="not a Git working copy"):
        dispatch.validate_repo_root(tmp_path)


def test_transport_opener_disables_environment_proxies(monkeypatch):
    monkeypatch.setattr(
        transport.urllib.request,
        "getproxies",
        lambda: {"http": "http://proxy.invalid:8080"},
    )
    proxy_handlers = [
        handler
        for handler in transport._build_opener().handlers
        if isinstance(handler, transport.urllib.request.ProxyHandler)
    ]

    assert proxy_handlers == []


def test_transport_refuses_redirect_before_forwarding_token():
    target_hits = 0

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal target_hits
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/target")
                self.end_headers()
                return
            target_hits += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        def log_message(self, _format, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(WatercoolerError, match="HTTP 302"):
            transport.request_json(
                {"base_url": f"http://127.0.0.1:{server.server_port}", "token": "test-token"},
                method="GET",
                path="/redirect",
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert target_hits == 0


@pytest.mark.parametrize("path", ["https://other.example/v1/messages", "//other/v1", "/v1?x=1"])
def test_transport_refuses_non_api_paths_before_network(path):
    with pytest.raises(WatercoolerError, match="path is malformed"):
        transport.request_json(
            {"base_url": "http://127.0.0.1:1", "token": "test-token"},
            method="GET",
            path=path,
        )
