from __future__ import annotations

import json
import os
import stat
import subprocess
from datetime import timedelta
from pathlib import Path

import pytest

from watercooler.common import WatercoolerError
from watercooler.dispatcher import commit_review as dispatch
from watercooler.dispatcher import request as request_review

COMMIT = "1" * 40
INTEGRATION_ROOT = Path(__file__).resolve().parents[2] / "integrations" / "codex-reviewer"


def policy(**overrides) -> dispatch.Policy:
    values = dict(
        principal="review-dispatcher",
        expected_base_url="http://127.0.0.1:8765",
        threads=("general",),
        allowed_senders=frozenset({"maintainer", "review-requester", "reviewer"}),
        topic="commit-review/v1",
        tag="commit-review-request",
        model="review-model",
        reasoning_effort="high",
        codex_cli_version="0.144.5",
        daily_review_limit=24,
        transport_security="loopback_http",
        worker_backend="docker",
        wsl_distribution="",
        docker_image="org.watercooler/codex-reviewer:0.144.5",
        docker_image_id="sha256:" + "a" * 64,
    )
    values.update(overrides)
    return dispatch.Policy(**values)


def wsl_policy() -> dispatch.Policy:
    return policy(worker_backend="wsl_docker", wsl_distribution="TestDistro")


def config(**overrides):
    value = {
        "base_url": "http://127.0.0.1:8765",
        "token": "not-a-real-token",
        "principal": "review-dispatcher",
        "default_from": "review-dispatcher",
        "scopes": ["messages:read", "messages:write"],
        "expires_ts": dispatch.iso_utc(dispatch.utc_now() + timedelta(days=1)),
    }
    value.update(overrides)
    return value


def request_body(commit: str = COMMIT) -> str:
    return json.dumps(
        {"version": 1, "kind": "commit", "commit": commit},
        separators=(",", ":"),
    )


def message(message_id: int, **overrides):
    row = {
        "id": message_id,
        "ts": "2026-07-16T12:00:00Z",
        "from_agent": "review-requester",
        "to_agent": "review-dispatcher",
        "thread": "general",
        "topic": "commit-review/v1",
        "lang": "en",
        "tags": ["commit-review-request"],
        "body": request_body(),
    }
    row.update(overrides)
    return row


def valid_result(commit: str = COMMIT, *, findings: bool = False):
    return {
        "reviewed_commit": commit,
        "status": "FINDINGS" if findings else "NO_FINDINGS",
        "summary": "One actionable defect was found." if findings else "No actionable defect found.",
        "findings": (
            [
                {
                    "severity": "P1",
                    "title": "Incorrect boundary check",
                    "body": "The final row bypasses validation.",
                    "path": "src/check.py",
                    "line": 41,
                }
            ]
            if findings
            else []
        ),
        "verification": ["Inspected the commit diff", "Ran focused tests"],
    }


def fake_worker_result(tmp_path: Path, result=None, *, returncode: int = 0):
    return dispatch.WorkerResult(
        returncode=returncode,
        timed_out=False,
        log_path=tmp_path / "worker.log",
        result_path=tmp_path / "result.json",
        prompt_path=tmp_path / "prompt.txt",
        container_name="watercooler-review-1-1",
        duration_seconds=1.25,
        result=result,
        error="" if returncode == 0 else "reviewer failed",
    )


def test_repository_policy_loads_with_dedicated_identity():
    loaded = dispatch.load_policy(INTEGRATION_ROOT / "dispatcher-policy.example.json")

    assert loaded.principal == "review-dispatcher"
    assert loaded.topic == "commit-review/v1"
    assert loaded.tag == "commit-review-request"
    assert loaded.allowed_senders == frozenset({"review-requester"})
    assert loaded.worker_backend == "docker"


def test_dispatch_config_requires_exact_identity_url_and_least_privilege():
    dispatch.validate_dispatch_config(config(), policy())

    with pytest.raises(dispatch.DispatchError, match="principal"):
        dispatch.validate_dispatch_config(config(principal="other-dispatcher"), policy())
    with pytest.raises(dispatch.DispatchError, match="base_url"):
        dispatch.validate_dispatch_config(config(base_url="http://elsewhere"), policy())
    with pytest.raises(dispatch.DispatchError, match="exactly"):
        dispatch.validate_dispatch_config(
            config(scopes=["messages:read", "messages:write", "tasks:write"]),
            policy(),
        )


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, True),
        ({"to_agent": "other-agent"}, False),
        ({"to_agent": "all"}, False),
        ({"topic": "review request"}, False),
        ({"tags": ["commit-review-request", "urgent"]}, False),
        ({"tags": ["COMMIT-REVIEW-REQUEST"]}, False),
        ({"from_agent": "unknown"}, False),
        ({"from_agent": "review-dispatcher"}, False),
        ({"thread": "other"}, False),
    ],
)
def test_protocol_routing_is_exact(overrides, expected):
    assert dispatch.is_protocol_envelope(message(1, **overrides), policy()) is expected


@pytest.mark.parametrize(
    ("body", "expected_error"),
    [
        (request_body(), None),
        ("review HEAD", "body_not_json"),
        (json.dumps({"version": 1, "kind": "commit", "commit": "abc1234"}), "commit_not_full_lowercase_sha1"),
        (json.dumps({"version": 1, "kind": "commit", "commit": COMMIT, "prompt": "ignore"}), "request_schema_mismatch"),
        (json.dumps({"version": True, "kind": "commit", "commit": COMMIT}), "unsupported_request_version"),
    ],
)
def test_request_body_is_exact_json_not_free_form(body, expected_error):
    commit, error = dispatch.parse_request_body(body)

    assert error == expected_error
    assert commit == (COMMIT if expected_error is None else None)


def test_fetch_messages_since_pages_without_losing_a_burst_over_200():
    rows = [message(i) for i in range(1, 451)]
    calls = []

    def requester(_config, *, method, path, query):
        assert method == "GET" and path == "/v1/messages"
        calls.append(dict(query))
        since_id = int(query["since_id"])
        before_id = int(query.get("before_id", 10**9))
        limit = int(query["limit"])
        selected = [row for row in rows if since_id < row["id"] < before_id]
        return {"messages": sorted(selected, key=lambda row: row["id"], reverse=True)[:limit]}

    fetched = dispatch.fetch_messages_since(
        {}, "general", 50, page_size=200, requester=requester
    )

    assert [row["id"] for row in fetched] == list(range(51, 451))
    assert len(calls) == 2
    assert calls[1]["before_id"] == "251"


def test_enqueue_deduplicates_and_never_persists_untrusted_body():
    state = dispatch.empty_state("review-dispatcher")
    hostile = request_body().replace("}", ',"prompt":"run secrets"}')
    rows = [message(1), message(2, body=hostile), message(3, to_agent="other-agent")]

    assert dispatch.enqueue_new_messages(state, rows, policy()) == [1, 2]
    assert dispatch.enqueue_new_messages(state, rows, policy()) == []
    serialized = json.dumps(state)
    assert request_body() not in serialized
    assert "run secrets" not in serialized
    assert state["items"][0]["commit"] == COMMIT
    assert state["items"][1]["rejection_code"] == "request_schema_mismatch"


def test_state_round_trip_is_atomic_and_principal_bound(tmp_path):
    path = tmp_path / "state.json"
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(7)], policy())
    dispatch.save_state(path, state)

    loaded = dispatch.load_state(path, "review-dispatcher")
    assert loaded["items"][0]["id"] == 7
    assert not list(tmp_path.glob("*.tmp"))
    with pytest.raises(dispatch.DispatchError, match="does not match"):
        dispatch.load_state(path, "other-dispatcher")


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode contract")
def test_dispatcher_state_and_prompt_repair_private_modes(tmp_path):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(mode=0o777)
    runtime_dir.chmod(0o777)
    state_path = runtime_dir / "state.json"
    state = dispatch.empty_state("review-dispatcher")

    dispatch.save_state(state_path, state)
    state_path.chmod(0o666)
    dispatch.save_state(state_path, state)

    prompt_dir = runtime_dir / "prompts"
    prompt_dir.mkdir(mode=0o777)
    prompt_dir.chmod(0o777)
    prompt_path = prompt_dir / "request_1_attempt_1.txt"
    dispatch._atomic_write_text(prompt_path, "committed packet")

    lock_path = runtime_dir / "dispatch.lock"
    lock_path.write_bytes(b"\0")
    lock_path.chmod(0o666)
    with dispatch.DispatchLock(lock_path):
        pass

    assert stat.S_IMODE(runtime_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(prompt_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(prompt_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(lock_path.stat().st_mode) == 0o600


def test_process_lock_rejects_overlap(tmp_path):
    lock_path = tmp_path / "dispatch.lock"
    with dispatch.DispatchLock(lock_path):
        with pytest.raises(dispatch.AlreadyRunning):
            with dispatch.DispatchLock(lock_path):
                pass


def test_worker_environment_is_an_allowlist_not_a_secret_name_heuristic():
    source = {
        "PATH": "path",
        "HOME": "home",
        "OPENAI_API_KEY": "secret",
        "HF_TOKEN": "secret",
        "VECTOR_DB_URL": "secret-adjacent",
        "WATERCOOLER_CONFIG": "config",
        "NORMAL_FLAG": "not-allowed",
    }

    cleaned = dispatch.sanitized_worker_environment(source)

    assert cleaned == {"PATH": "path", "HOME": "home", "PYTHONIOENCODING": "utf-8"}


def test_codex_command_is_fixed_read_only_and_contains_no_watercooler_body(tmp_path):
    auth_file = tmp_path / "auth.json"
    auth_file.write_text("{}", encoding="utf-8")
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{}", encoding="utf-8")
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    result_path = tmp_path / "result.json"
    command = dispatch.build_codex_command(
        item={"id": 1, "commit": COMMIT, "review_attempts": 1},
        auth_file=auth_file,
        schema_path=schema_path,
        result_path=result_path,
        results_dir=results_dir,
        policy=policy(),
    )
    joined = " ".join(command)

    assert command[0] == "docker"
    assert "run" in command
    assert command[-1] == "-"
    assert COMMIT not in joined
    assert "--ephemeral" in command
    assert "--ignore-user-config" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("--network") + 1] == "bridge"
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert "--interactive" in command
    assert command[command.index("--pull") + 1] == "never"
    assert policy().docker_image_id in command
    assert policy().docker_image not in command
    assert "/worker:rw,noexec,nosuid,size=4m,uid=1000,gid=1000,mode=0700" in command
    assert "/codex-home:rw,noexec,nosuid,size=32m,uid=1000,gid=1000,mode=0700" in command
    assert 'approval_policy="never"' in command
    assert 'web_search="disabled"' in command
    assert "shell_environment_policy.exclude" in " ".join(command)
    assert "workspace-write" not in joined
    assert "Watercooler" not in joined
    assert request_body() not in joined
    assert "multi_agent" in command
    assert "shell_tool" in command
    assert "unified_exec" in command
    volumes = [
        command[index + 1]
        for index, value in enumerate(command[:-1])
        if value == "--volume"
    ]
    assert len(volumes) == 3
    assert any(value.endswith(":/codex-home/auth.json:ro") for value in volumes)
    assert any(value.endswith(":/schema/review.json:ro") for value in volumes)
    assert any(value.endswith(":/output:rw") for value in volumes)


def test_wsl_backend_wraps_the_same_pinned_docker_command(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    command = dispatch.build_codex_command(
        item={"id": 1, "commit": COMMIT, "review_attempts": 1},
        auth_file=tmp_path / "auth.json",
        schema_path=tmp_path / "schema.json",
        result_path=tmp_path / "result.json",
        results_dir=results_dir,
        policy=wsl_policy(),
    )

    assert command[:5] == ["wsl.exe", "-d", "TestDistro", "--exec", "docker"]
    assert wsl_policy().docker_image_id in command


def test_runtime_preflight_pins_image_and_checks_auth_mount_and_ca(tmp_path, monkeypatch):
    auth_file = tmp_path / "auth.json"
    auth_file.write_text("{}", encoding="utf-8")
    calls = []

    def run_docker(_policy, arguments, **_kwargs):
        calls.append(arguments)
        if arguments[:2] == ["image", "inspect"]:
            return subprocess.CompletedProcess(arguments, 0, policy().docker_image_id + "\n", "")
        if arguments[-1] == "--version":
            return subprocess.CompletedProcess(arguments, 0, "codex-cli 0.144.5\n", "")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(dispatch, "_run_docker", run_docker)

    dispatch.validate_container_runtime(policy(), auth_file)

    assert len(calls) == 3
    assert policy().docker_image_id in calls[1]
    assert policy().docker_image_id in calls[2]
    assert "--network" in calls[2]
    assert calls[2][calls[2].index("--network") + 1] == "none"
    assert any(value.endswith(":/codex-home/auth.json:ro") for value in calls[2])
    assert "test -s /etc/ssl/certs/ca-certificates.crt" in calls[2][-1]


def test_structured_result_enforces_status_and_findings_without_keyword_false_positive():
    normalized = dispatch.validate_review_result(valid_result(findings=True), COMMIT)
    assert normalized["status"] == "FINDINGS"

    contradictory = valid_result()
    contradictory["findings"] = valid_result(findings=True)["findings"]
    with pytest.raises(dispatch.DispatchError, match="disagree"):
        dispatch.validate_review_result(contradictory, COMMIT)

    legitimate = valid_result(findings=True)
    legitimate["findings"][0]["body"] = "This path can incorrectly report success."
    assert dispatch.validate_review_result(legitimate, COMMIT)["findings"][0][
        "body"
    ].endswith("success.")


def test_review_packet_is_pinned_to_git_objects_and_excludes_dirty_worktree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "sample.txt").write_text("committed\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "sample"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    (repo / "sample.txt").write_text("dirty\n", encoding="utf-8")
    dispatch.validate_commit(repo, commit)
    packet = json.loads(dispatch.build_review_packet(repo, commit))

    assert packet["reviewed_commit"] == commit
    assert packet["base_kind"] == "empty_tree"
    assert packet["changed_files"][0]["content_utf8"] == "committed\n"
    assert "dirty" not in json.dumps(packet)
    assert "committed" in packet["unified_diff_utf8"]


def test_review_packet_ignores_replace_refs_and_inherited_git_overrides(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    tracked = repo / "sample.txt"
    tracked.write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "original"], cwd=repo, check=True, capture_output=True)
    original = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    tracked.write_text("replacement\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "replacement"], cwd=repo, check=True, capture_output=True)
    replacement = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    subprocess.run(["git", "replace", original, replacement], cwd=repo, check=True)
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "wrong-worktree"))

    packet = json.loads(dispatch.build_review_packet(repo, original))

    assert packet["base_commit"] is None
    assert packet["commit_message_utf8"] == "original"
    assert packet["changed_files"][0]["content_utf8"] == "original\n"
    assert "replacement" not in json.dumps(packet)


def test_review_packet_parent_comes_from_raw_commit_not_graft_metadata(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    tracked = repo / "sample.txt"
    tracked.write_text("first\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "first"], cwd=repo, check=True, capture_output=True)
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    tracked.write_text("second\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "second"], cwd=repo, check=True, capture_output=True)
    second = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    info_dir = repo / ".git" / "info"
    info_dir.mkdir(exist_ok=True)
    (info_dir / "grafts").write_text(second + "\n", encoding="ascii")

    packet = json.loads(dispatch.build_review_packet(repo, second))

    assert packet["base_commit"] == first
    assert packet["changed_files"][0]["content_utf8"] == "second\n"
    assert "-first" in packet["unified_diff_utf8"]
    assert "+second" in packet["unified_diff_utf8"]


def test_review_packet_diff_ignores_dirty_worktree_attributes(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    tracked = repo / "sample.txt"
    tracked.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "one"], cwd=repo, check=True, capture_output=True)
    tracked.write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "two"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    clean_packet = json.loads(dispatch.build_review_packet(repo, commit))
    (repo / ".gitattributes").write_text("sample.txt -diff\n", encoding="utf-8")

    dirty_packet = json.loads(dispatch.build_review_packet(repo, commit))
    (repo / ".git" / "info" / "attributes").write_text(
        "sample.txt -diff\n", encoding="utf-8"
    )
    info_packet = json.loads(dispatch.build_review_packet(repo, commit))

    assert dirty_packet == clean_packet
    assert info_packet == clean_packet
    assert "-one" in dirty_packet["unified_diff_utf8"]
    assert "+two" in dirty_packet["unified_diff_utf8"]


def test_review_packet_refuses_invalid_utf8_commit_message(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "sample.txt").write_text("content\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.txt"], cwd=repo, check=True)
    tree = subprocess.run(
        ["git", "write-tree"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    raw_commit = (
        f"tree {tree}\n"
        "author Test <test@example.invalid> 0 +0000\n"
        "committer Test <test@example.invalid> 0 +0000\n\n"
    ).encode("ascii") + b"invalid-\xff\n"
    commit = subprocess.run(
        ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
        cwd=repo,
        input=raw_commit,
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").strip()

    with pytest.raises(dispatch.DispatchError, match="commit message is not valid UTF-8"):
        dispatch.build_review_packet(repo, commit)


def test_review_packet_refuses_invalid_utf8_unified_diff(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / ".gitattributes").write_text("sample.txt diff\n", encoding="utf-8")
    (repo / "sample.txt").write_bytes(b"invalid-\xff\n")
    subprocess.run(["git", "add", ".gitattributes", "sample.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "invalid diff"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    with pytest.raises(dispatch.DispatchError, match="unified diff is not valid UTF-8"):
        dispatch.build_review_packet(repo, commit)


def test_review_packet_refuses_binary_nul_diff(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "sample.bin").write_bytes(b"prefix\x00suffix\n")
    subprocess.run(["git", "add", "sample.bin"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "binary"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    with pytest.raises(dispatch.DispatchError, match="contains binary NUL bytes"):
        dispatch.build_review_packet(repo, commit)


def test_review_packet_stops_streaming_when_diff_exceeds_limit(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    large_text = "".join(
        f"line-{index:06d}-{'x' * 64}\n" for index in range(6_000)
    )
    (repo / "large.txt").write_text(large_text, encoding="utf-8")
    subprocess.run(["git", "add", "large.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "large"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    with pytest.raises(dispatch.DispatchError, match="byte limit"):
        dispatch.build_review_packet(repo, commit)


def test_worker_reads_fixed_packet_prompt_from_stdin_and_validates_output_file(tmp_path):
    schema = tmp_path / "schema.json"
    schema.write_text("{}", encoding="utf-8")
    auth_file = tmp_path / "auth.json"
    auth_file.write_text("{}", encoding="utf-8")
    worker_dir = tmp_path / "worker"
    captured = {}

    class FakeProcess:
        pid = 12345
        returncode = 0

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs
            captured["prompt"] = kwargs["stdin"].read()
            output = tmp_path / "results" / Path(
                command[command.index("--output-last-message") + 1]
            ).name
            output.write_text(json.dumps(valid_result()), encoding="utf-8")

        def wait(self, timeout=None):
            captured["timeout"] = timeout
            return 0

        def poll(self):
            return self.returncode

    started = []
    item = {"id": 3, "commit": COMMIT, "review_attempts": 1}
    removed = []
    result = dispatch.run_codex_worker(
        item,
        review_packet='{"reviewed_commit":"' + COMMIT + '"}',
        worker_dir=worker_dir,
        auth_file=auth_file,
        schema_path=schema,
        results_dir=tmp_path / "results",
        logs_dir=tmp_path / "logs",
        prompts_dir=tmp_path / "prompts",
        policy=policy(),
        timeout_seconds=60,
        environment={"PATH": "safe", "SOME_TOKEN": "secret"},
        on_started=lambda pid, output, log, prompt, container: started.append(
            (pid, output, log, prompt, container)
        ),
        popen_factory=FakeProcess,
        runtime_validator=lambda _policy, _auth: None,
        container_remover=lambda _policy, name: removed.append(name),
    )

    assert result.result == valid_result()
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["stdout"] is subprocess.DEVNULL
    assert captured["kwargs"]["stderr"] is subprocess.DEVNULL
    assert captured["command"][-1] == "-"
    assert COMMIT not in " ".join(captured["command"])
    assert COMMIT in captured["prompt"]
    assert "BEGIN IMMUTABLE REVIEW PACKET" in captured["prompt"]
    assert captured["kwargs"]["cwd"] == worker_dir
    assert captured["kwargs"]["env"] == {"PATH": "safe", "PYTHONIOENCODING": "utf-8"}
    assert started[0][0] == 12345
    assert removed == ["watercooler-review-3-1"]
    if os.name == "posix":
        for directory in (worker_dir, tmp_path / "results", tmp_path / "logs", tmp_path / "prompts"):
            assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        for artifact in (result.result_path, result.log_path, result.prompt_path):
            assert stat.S_IMODE(artifact.stat().st_mode) == 0o600


def test_worker_unexpected_wait_failure_still_terminates_and_removes_container(
    tmp_path, monkeypatch
):
    schema = tmp_path / "schema.json"
    schema.write_text("{}", encoding="utf-8")
    auth_file = tmp_path / "auth.json"
    auth_file.write_text("{}", encoding="utf-8")
    terminated = []
    removed = []

    class FailingWaitProcess:
        pid = 12346
        returncode = None

        def __init__(self, _command, **_kwargs):
            pass

        def wait(self, timeout=None):
            raise OSError("wait failed")

        def poll(self):
            return self.returncode

    def terminate(process):
        terminated.append(process.pid)
        process.returncode = -9

    monkeypatch.setattr(dispatch, "_terminate_process_tree", terminate)
    result = dispatch.run_codex_worker(
        {"id": 6, "commit": COMMIT, "review_attempts": 1},
        review_packet='{"reviewed_commit":"' + COMMIT + '"}',
        worker_dir=tmp_path / "worker",
        auth_file=auth_file,
        schema_path=schema,
        results_dir=tmp_path / "results",
        logs_dir=tmp_path / "logs",
        prompts_dir=tmp_path / "prompts",
        policy=policy(),
        timeout_seconds=60,
        popen_factory=FailingWaitProcess,
        runtime_validator=lambda _policy, _auth: None,
        container_remover=lambda _policy, name: removed.append(name),
    )

    assert result.returncode == -9
    assert result.container_removed is True
    assert "wait failed: OSError" in result.error
    assert terminated == [12346]
    assert removed == ["watercooler-review-6-1"]


def test_worker_reports_unconfirmed_custody_when_container_removal_fails(tmp_path):
    schema = tmp_path / "schema.json"
    schema.write_text("{}", encoding="utf-8")
    auth_file = tmp_path / "auth.json"
    auth_file.write_text("{}", encoding="utf-8")

    class ExitedProcess:
        pid = 12348
        returncode = 1

        def __init__(self, _command, **_kwargs):
            pass

        def wait(self, timeout=None):
            return self.returncode

        def poll(self):
            return self.returncode

    def refuse_removal(_policy, _name):
        raise dispatch.DispatchError("container remains")

    result = dispatch.run_codex_worker(
        {"id": 8, "commit": COMMIT, "review_attempts": 1},
        review_packet='{"reviewed_commit":"' + COMMIT + '"}',
        worker_dir=tmp_path / "worker",
        auth_file=auth_file,
        schema_path=schema,
        results_dir=tmp_path / "results",
        logs_dir=tmp_path / "logs",
        prompts_dir=tmp_path / "prompts",
        policy=policy(),
        timeout_seconds=60,
        popen_factory=ExitedProcess,
        runtime_validator=lambda _policy, _auth: None,
        container_remover=refuse_removal,
    )

    assert result.container_removed is False
    assert result.container_name == "watercooler-review-8-1"
    assert "container cleanup failed" in result.error


def test_unconfirmed_container_cleanup_keeps_dispatch_item_in_running_custody(tmp_path):
    def requester(_config, *, method, path, **_kwargs):
        assert method == "GET"
        assert path == "/v1/messages"
        return {"messages": [message(7)]}

    def worker(item, **kwargs):
        container_name = dispatch.reviewer_container_name(item)
        kwargs["on_started"](
            12347,
            tmp_path / "result.json",
            tmp_path / "worker.log",
            tmp_path / "prompt.txt",
            container_name,
        )
        return dispatch.WorkerResult(
            returncode=-1,
            timed_out=False,
            log_path=tmp_path / "worker.log",
            result_path=tmp_path / "result.json",
            prompt_path=tmp_path / "prompt.txt",
            container_name=container_name,
            duration_seconds=1.0,
            container_removed=False,
            error="reviewer container cleanup failed",
        )

    state_path = tmp_path / "state.json"
    summary = dispatch.dispatch_cycle(
        config=config(),
        state_path=state_path,
        policy=policy(),
        repo_root=tmp_path,
        runtime_dir=tmp_path / "runtime",
        schema_path=tmp_path / "schema.json",
        codex_auth_file=tmp_path / "auth.json",
        timeout_seconds=60,
        max_attempts=2,
        retry_base_seconds=30,
        requester=requester,
        worker=worker,
        commit_validator=lambda _root, _commit: None,
        packet_builder=lambda _root, _commit: "{}",
    )
    item = dispatch.load_state(state_path, "review-dispatcher")["items"][0]

    assert summary["action"] == "reviewer_custody_pending"
    assert item["status"] == "running"
    assert item["worker_pid"] is not None
    assert item["container_name"] == "watercooler-review-7-1"
    assert item["review_attempts"] == 1


def test_recovery_removes_exact_overdue_container_before_retry(tmp_path):
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(4)], policy())
    item = state["items"][0]
    item["status"] = "running"
    item["worker_started_ts"] = dispatch.iso_utc(
        dispatch.utc_now() - timedelta(hours=2)
    )
    item["worker_pid"] = 99999999
    item["container_name"] = "watercooler-review-4-1"
    result_path = tmp_path / "old-result.json"
    result_path.write_text(json.dumps(valid_result()), encoding="utf-8")
    item["result_path"] = str(result_path)
    removed = []

    changed = dispatch.recover_interrupted_items(
        state,
        timeout_seconds=60,
        policy=policy(),
        container_inspector=lambda _policy, _name: "running",
        container_remover=lambda _policy, name: removed.append(name),
    )

    assert changed is True
    assert removed == ["watercooler-review-4-1"]
    assert item["status"] == "queued"
    assert item["result"] is None
    assert item["container_name"] == ""


def test_recovery_does_not_retry_when_overdue_container_cleanup_fails():
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(4)], policy())
    item = state["items"][0]
    item["status"] = "running"
    item["worker_started_ts"] = dispatch.iso_utc(
        dispatch.utc_now() - timedelta(hours=2)
    )
    item["worker_pid"] = 99999999
    item["container_name"] = "watercooler-review-4-1"

    def refuse_removal(_policy, _name):
        raise dispatch.DispatchError("container remains")

    changed = dispatch.recover_interrupted_items(
        state,
        timeout_seconds=60,
        policy=policy(),
        container_inspector=lambda _policy, _name: "running",
        container_remover=refuse_removal,
    )

    assert changed is True
    assert item["status"] == "running"
    assert item["container_name"] == "watercooler-review-4-1"
    assert "orphan cleanup failed" in item["last_error"]


def test_recovery_uses_completed_output_instead_of_reinvoking(tmp_path):
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(5)], policy())
    item = state["items"][0]
    item["status"] = "running"
    item["worker_pid"] = 99999999
    item["worker_started_ts"] = dispatch.iso_utc(dispatch.utc_now() - timedelta(hours=2))
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(valid_result()), encoding="utf-8")
    item["result_path"] = str(result_path)

    assert dispatch.recover_interrupted_items(state, timeout_seconds=60)
    assert item["status"] == "result_ready"
    assert item["result"]["status"] == "NO_FINDINGS"


def test_dispatch_cycle_is_model_free_when_mailbox_is_quiet(tmp_path):
    def requester(_config, **_kwargs):
        return {"messages": []}

    def worker(*_args, **_kwargs):
        raise AssertionError("quiet tick must not invoke Codex")

    summary = dispatch.dispatch_cycle(
        config={},
        state_path=tmp_path / "state.json",
        policy=policy(),
        repo_root=tmp_path,
        runtime_dir=tmp_path / "runtime",
        schema_path=tmp_path / "schema.json",
        codex_auth_file=tmp_path / "auth.json",
        timeout_seconds=60,
        max_attempts=2,
        retry_base_seconds=30,
        requester=requester,
        worker=worker,
    )

    assert summary["invoked"] is False
    assert summary["action"] == "quiet"


def test_http_failure_does_not_advance_durable_cursor(tmp_path):
    state_path = tmp_path / "state.json"
    state = dispatch.empty_state("review-dispatcher")
    state["last_seen_by_thread"]["general"] = 12
    dispatch.save_state(state_path, state)

    def requester(_config, **_kwargs):
        raise WatercoolerError("offline")

    with pytest.raises(WatercoolerError, match="offline"):
        dispatch.dispatch_cycle(
            config={},
            state_path=state_path,
            policy=policy(),
            repo_root=tmp_path,
            runtime_dir=tmp_path / "runtime",
            schema_path=tmp_path / "schema.json",
            codex_auth_file=tmp_path / "auth.json",
            timeout_seconds=60,
            max_attempts=2,
            retry_base_seconds=30,
            requester=requester,
        )

    assert dispatch.load_state(state_path, "review-dispatcher")["last_seen_by_thread"] == {
        "general": 12
    }


def test_daily_attempt_cap_keeps_request_queued_without_model_call(tmp_path):
    state_path = tmp_path / "state.json"
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(8)], policy())
    state["last_seen_by_thread"]["general"] = 8
    state["review_starts"] = [dispatch.iso_utc()] * policy().daily_review_limit
    dispatch.save_state(state_path, state)

    def requester(_config, **_kwargs):
        return {"messages": []}

    def worker(*_args, **_kwargs):
        raise AssertionError("daily cap must not invoke Codex")

    summary = dispatch.dispatch_cycle(
        config={},
        state_path=state_path,
        policy=policy(),
        repo_root=tmp_path,
        runtime_dir=tmp_path / "runtime",
        schema_path=tmp_path / "schema.json",
        codex_auth_file=tmp_path / "auth.json",
        timeout_seconds=60,
        max_attempts=2,
        retry_base_seconds=30,
        requester=requester,
        worker=worker,
    )

    assert summary["action"] == "daily_review_limit_reached"
    assert dispatch.load_state(state_path, "review-dispatcher")["items"][0]["status"] == "queued"


def test_malformed_exact_request_gets_protocol_refusal_without_model(tmp_path):
    posts = []

    def requester(_config, *, method, path, query=None, payload=None):
        if method == "GET":
            return {"messages": [message(10, body="review HEAD")]} if int(query["since_id"]) < 10 else {"messages": []}
        posts.append(payload)
        return {"id": 11}

    def worker(*_args, **_kwargs):
        raise AssertionError("malformed protocol must not invoke Codex")

    summary = dispatch.dispatch_cycle(
        config={},
        state_path=tmp_path / "state.json",
        policy=policy(),
        repo_root=tmp_path,
        runtime_dir=tmp_path / "runtime",
        schema_path=tmp_path / "schema.json",
        codex_auth_file=tmp_path / "auth.json",
        timeout_seconds=60,
        max_attempts=2,
        retry_base_seconds=30,
        requester=requester,
        worker=worker,
    )

    assert summary["action"] == "posted_reply"
    assert "No model was invoked" in posts[0]["body"]
    assert "review-rejection" in posts[0]["tags"]


def test_result_is_durable_before_ambiguous_post_and_model_is_not_replayed(tmp_path):
    state_path = tmp_path / "state.json"
    posts = 0
    worker_calls = 0
    def requester(_config, *, method, path, query=None, payload=None):
        nonlocal posts
        if method == "GET":
            if query.get("participant"):
                return {"messages": []}
            return {"messages": [message(20)]} if int(query["since_id"]) < 20 else {"messages": []}
        posts += 1
        if posts == 1:
            raise WatercoolerError("ambiguous network failure")
        return {"id": 21}

    def worker(item, **kwargs):
        nonlocal worker_calls
        worker_calls += 1
        kwargs["on_started"](
            123,
            tmp_path / "result.json",
            tmp_path / "worker.log",
            tmp_path / "prompt.txt",
            "watercooler-review-20-1",
        )
        return fake_worker_result(tmp_path, valid_result(item["commit"]))

    arguments = dict(
        config={},
        state_path=state_path,
        policy=policy(),
        repo_root=tmp_path,
        runtime_dir=tmp_path / "runtime",
        schema_path=tmp_path / "schema.json",
        codex_auth_file=tmp_path / "auth.json",
        timeout_seconds=60,
        max_attempts=2,
        retry_base_seconds=30,
        requester=requester,
        worker=worker,
        commit_validator=lambda _repo, _commit: None,
        packet_builder=lambda _repo, _commit: "{}",
    )

    with pytest.raises(WatercoolerError, match="ambiguous"):
        dispatch.dispatch_cycle(**arguments)
    persisted = dispatch.load_state(state_path, "review-dispatcher")
    assert persisted["items"][0]["status"] == "result_ready"
    assert persisted["items"][0]["result"]["status"] == "NO_FINDINGS"

    summary = dispatch.dispatch_cycle(**arguments)
    assert summary["action"] == "posted_reply"
    assert worker_calls == 1
    assert dispatch.load_state(state_path, "review-dispatcher")["completed"][0]["id"] == 20


def test_existing_marker_recovers_ambiguous_post_without_reposting(tmp_path):
    state_path = tmp_path / "state.json"
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(30)], policy())
    item = state["items"][0]
    item["status"] = "result_ready"
    item["result"] = valid_result()
    dispatch.save_state(state_path, state)

    def requester(_config, *, method, path, query=None, payload=None):
        assert method == "GET"
        if query.get("participant"):
            return {
                "messages": [
                    message(
                        31,
                        from_agent="review-dispatcher",
                        to_agent="review-requester",
                        tags=["review-result", "commit-review-request-30"],
                    )
                ]
            }
        return {"messages": []}

    summary = dispatch.dispatch_cycle(
        config={},
        state_path=state_path,
        policy=policy(),
        repo_root=tmp_path,
        runtime_dir=tmp_path / "runtime",
        schema_path=tmp_path / "schema.json",
        codex_auth_file=tmp_path / "auth.json",
        timeout_seconds=60,
        max_attempts=2,
        retry_base_seconds=30,
        requester=requester,
    )

    assert summary["action"] == "recovered_existing_reply"
    assert dispatch.load_state(state_path, "review-dispatcher")["completed"][0]["reply_message_id"] == 31


def test_bounded_worker_failures_end_in_labeled_blocked_reply(tmp_path):
    state_path = tmp_path / "state.json"
    worker_calls = 0
    posts = []
    def requester(_config, *, method, path, query=None, payload=None):
        if method == "GET":
            if query.get("participant"):
                return {"messages": []}
            return {"messages": [message(40)]} if int(query["since_id"]) < 40 else {"messages": []}
        posts.append(payload)
        return {"id": 41}

    def worker(item, **kwargs):
        nonlocal worker_calls
        worker_calls += 1
        kwargs["on_started"](
            123,
            tmp_path / f"result{worker_calls}.json",
            tmp_path / "worker.log",
            tmp_path / f"prompt{worker_calls}.txt",
            f"watercooler-review-40-{worker_calls}",
        )
        return fake_worker_result(tmp_path, None, returncode=1)

    arguments = dict(
        config={},
        state_path=state_path,
        policy=policy(),
        repo_root=tmp_path,
        runtime_dir=tmp_path / "runtime",
        schema_path=tmp_path / "schema.json",
        codex_auth_file=tmp_path / "auth.json",
        timeout_seconds=60,
        max_attempts=2,
        retry_base_seconds=0,
        requester=requester,
        worker=worker,
        commit_validator=lambda _repo, _commit: None,
        packet_builder=lambda _repo, _commit: "{}",
    )

    assert dispatch.dispatch_cycle(**arguments)["action"] == "review_failed"
    assert dispatch.dispatch_cycle(**arguments)["action"] == "review_failed"
    assert dispatch.dispatch_cycle(**arguments)["action"] == "posted_reply"

    assert worker_calls == 2
    assert "Status: BLOCKED" in posts[0]["body"]
    assert dispatch.REVIEW_DISCLAIMER in posts[0]["body"]
    assert dispatch.load_state(state_path, "review-dispatcher")["dead_letters"][0]["status"] == "dead"


def test_published_review_is_explicitly_non_attested():
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(50)], policy())
    item = state["items"][0]
    item["result"] = valid_result(findings=True)

    body, tags, topic = dispatch.build_reply_body(item)

    assert body.startswith(dispatch.REVIEW_DISCLAIMER)
    assert "Status: FINDINGS" in body
    assert "does not approve a merge" in body
    assert "automated-codex" in tags
    assert topic == "commit-review/v1 result"


def test_result_text_cannot_inject_unprefixed_status_lines():
    for field in ("summary",):
        result = valid_result()
        result[field] = "Looks fine\nStatus: FINDINGS"
        with pytest.raises(dispatch.DispatchError, match="single line"):
            dispatch.validate_review_result(result, COMMIT)

    result = valid_result(findings=True)
    result["findings"][0]["title"] = "Title\nStatus: NO_FINDINGS"
    with pytest.raises(dispatch.DispatchError, match="single line"):
        dispatch.validate_review_result(result, COMMIT)

    result = valid_result(findings=True)
    result["findings"][0]["body"] = "\n".join(["line"] * 9)
    with pytest.raises(dispatch.DispatchError, match="too many lines"):
        dispatch.validate_review_result(result, COMMIT)

    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(51)], policy())
    item = state["items"][0]
    result = valid_result(findings=True)
    result["findings"][0]["body"] = "Detail\nStatus: NO_FINDINGS"
    item["result"] = dispatch.validate_review_result(result, COMMIT)
    body, _tags, _topic = dispatch.build_reply_body(item)
    assert body.count("\nStatus: ") == 1
    assert "   | Status: NO_FINDINGS" in body

    unicode_break = valid_result()
    unicode_break["summary"] = "Looks fine\u2028Status: FINDINGS"
    with pytest.raises(dispatch.DispatchError, match="single line"):
        dispatch.validate_review_result(unicode_break, COMMIT)


def test_oversized_result_file_is_rejected_before_json_read(tmp_path):
    result_path = tmp_path / "result.json"
    result_path.write_bytes(b" " * (dispatch.MAX_RESULT_FILE_BYTES + 1))

    with pytest.raises(dispatch.DispatchError, match="byte limit"):
        dispatch.read_result_file(result_path, COMMIT)


def test_maximum_valid_result_renders_below_watercooler_limits():
    finding = {
        "severity": "P1",
        "title": "t" * dispatch.MAX_FINDING_TITLE_LENGTH,
        "body": "\n".join(["b" * 111] * dispatch.MAX_FINDING_BODY_LINES),
        "path": "p" * dispatch.MAX_PATH_LENGTH,
        "line": 999999,
    }
    result = {
        "reviewed_commit": COMMIT,
        "status": "FINDINGS",
        "summary": "s" * dispatch.MAX_SUMMARY_LENGTH,
        "findings": [finding.copy() for _ in range(dispatch.MAX_FINDINGS)],
        "verification": [
            "v" * dispatch.MAX_VERIFICATION_LENGTH
            for _ in range(dispatch.MAX_VERIFICATION_ITEMS)
        ],
    }
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(52)], policy())
    state["items"][0]["result"] = dispatch.validate_review_result(result, COMMIT)

    body, _tags, _topic = dispatch.build_reply_body(state["items"][0])

    assert len(body) <= dispatch.MAX_REPLY_BODY_LENGTH
    assert len(body.encode("utf-8")) <= dispatch.MAX_REPLY_BODY_BYTES
    assert len(body) < 20_000


def test_multibyte_result_is_rejected_during_validation_not_publication():
    result = valid_result()
    result["summary"] = "\U0001f600" * dispatch.MAX_SUMMARY_LENGTH

    with pytest.raises(dispatch.DispatchError, match="length limit"):
        dispatch.validate_review_result(result, COMMIT)


def test_missing_post_id_keeps_durable_result_for_marker_recovery(tmp_path):
    state_path = tmp_path / "state.json"
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(53)], policy())
    state["items"][0]["status"] = "result_ready"
    state["items"][0]["result"] = valid_result()
    dispatch.save_state(state_path, state)

    def requester(_config, *, method, path, query=None, payload=None):
        if method == "GET":
            return {"messages": []}
        return {"ok": True}

    with pytest.raises(dispatch.DispatchError, match="no positive message id"):
        dispatch.dispatch_cycle(
            config={},
            state_path=state_path,
            policy=policy(),
            repo_root=tmp_path,
            runtime_dir=tmp_path / "runtime",
            schema_path=tmp_path / "schema.json",
            codex_auth_file=tmp_path / "auth.json",
            timeout_seconds=60,
            max_attempts=2,
            retry_base_seconds=30,
            requester=requester,
        )

    retained = dispatch.load_state(state_path, "review-dispatcher")
    assert retained["items"][0]["status"] == "result_ready"
    assert retained["items"][0]["result"]["status"] == "NO_FINDINGS"
    assert retained["completed"] == []


def test_permanent_publication_rejection_moves_result_to_dead_letter(tmp_path):
    state_path = tmp_path / "state.json"
    state = dispatch.empty_state("review-dispatcher")
    dispatch.enqueue_new_messages(state, [message(54)], policy())
    state["items"][0]["status"] = "result_ready"
    state["items"][0]["result"] = valid_result()
    dispatch.save_state(state_path, state)

    def requester(_config, *, method, path, query=None, payload=None):
        if method == "GET":
            return {"messages": []}
        raise WatercoolerError("POST /v1/post failed with HTTP 400: invalid payload")

    summary = dispatch.dispatch_cycle(
        config={},
        state_path=state_path,
        policy=policy(),
        repo_root=tmp_path,
        runtime_dir=tmp_path / "runtime",
        schema_path=tmp_path / "schema.json",
        codex_auth_file=tmp_path / "auth.json",
        timeout_seconds=60,
        max_attempts=2,
        retry_base_seconds=30,
        requester=requester,
    )

    final = dispatch.load_state(state_path, "review-dispatcher")
    assert summary["action"] == "publication_dead_lettered"
    assert final["items"] == []
    assert final["dead_letters"][0]["status"] == "post_failed"
    assert final["dead_letters"][0]["result"]["status"] == "NO_FINDINGS"


def test_reprime_existing_state_never_advances_cursor_or_calls_network(tmp_path):
    state_path = tmp_path / "state.json"
    state = dispatch.empty_state("review-dispatcher")
    state["last_seen_by_thread"]["general"] = 10
    dispatch.enqueue_new_messages(state, [message(11)], policy())
    dispatch.save_state(state_path, state)

    def requester(*_args, **_kwargs):
        raise AssertionError("existing state must never be re-primed from the live head")

    heads = dispatch.prime_state({}, state_path, policy(), requester=requester)

    assert heads == {"general": 10}
    retained = dispatch.load_state(state_path, "review-dispatcher")
    assert retained["last_seen_by_thread"]["general"] == 10
    assert retained["items"][0]["id"] == 11


def test_request_helper_resolves_full_sha_and_posts_exact_envelope(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "x.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "x"], cwd=repo, check=True, capture_output=True)

    commit = request_review.resolve_commit(repo, "HEAD")
    payload = request_review.build_request_payload(
        principal="review-requester", thread="general", commit=commit, policy=policy()
    )

    assert len(commit) == 40
    assert payload["to_agent"] == "review-dispatcher"
    assert payload["topic"] == "commit-review/v1"
    assert payload["tags"] == ["commit-review-request"]
    assert json.loads(payload["body"]) == {"version": 1, "kind": "commit", "commit": commit}


def test_scheduled_task_uses_a_no_window_launcher():
    tool_dir = INTEGRATION_ROOT / "windows"
    installer = (tool_dir / "install-scheduled-task.ps1").read_text(
        encoding="utf-8"
    )
    launcher = (tool_dir / "run-hidden.vbs").read_text(
        encoding="utf-8"
    )

    assert "Get-Command wscript.exe" in installer
    assert '"//B"' in installer
    assert "run-hidden.vbs" in installer
    assert "shell.Run(command, 0, True)" in launcher
    assert "WScript.Quit exitCode" in launcher
