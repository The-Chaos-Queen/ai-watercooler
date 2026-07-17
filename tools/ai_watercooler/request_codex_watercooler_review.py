"""Post a correctly-shaped immutable commit request to the Codex dispatcher."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from codex_watercooler_dispatch import (
        DispatchError,
        Policy,
        default_policy_path,
        load_policy,
        parse_utc,
        sanitized_git_environment,
        utc_now,
    )
    from common import WatercoolerError, load_config, request_json
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from codex_watercooler_dispatch import (
        DispatchError,
        Policy,
        default_policy_path,
        load_policy,
        parse_utc,
        sanitized_git_environment,
        utc_now,
    )
    from common import WatercoolerError, load_config, request_json


def validate_sender_config(config: Mapping[str, Any], policy: Policy) -> str:
    principal = config.get("principal") or config.get("default_from")
    if type(principal) is not str or principal not in policy.allowed_senders:
        raise DispatchError("caller principal is not in the dispatcher allowlist")
    if config.get("default_from") != principal:
        raise DispatchError("caller config default_from does not match its principal")
    if str(config.get("base_url") or "").rstrip("/") != policy.expected_base_url:
        raise DispatchError("caller config points at a different Watercooler endpoint")
    scopes = config.get("scopes")
    if type(scopes) is not list or "messages:write" not in scopes:
        raise DispatchError("caller token lacks messages:write")
    if type(config.get("token")) is not str or not config["token"].strip():
        raise DispatchError("caller config has no usable token")
    expires = config.get("expires_ts")
    if type(expires) is not str or parse_utc(expires) <= utc_now():
        raise DispatchError("caller token is expired or lacks an expiry")
    return principal


def resolve_commit(repo_root: Path, revision: str) -> str:
    if not revision or revision.startswith("-") or any(ord(ch) < 32 for ch in revision):
        raise DispatchError("commit revision is empty or unsafe")
    completed = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "rev-parse",
            "--verify",
            f"{revision}^{{commit}}",
        ],
        cwd=repo_root,
        env=sanitized_git_environment(),
        shell=False,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    commit = completed.stdout.strip()
    if completed.returncode != 0 or len(commit) != 40:
        raise DispatchError(f"cannot resolve commit revision {revision!r}")
    return commit.casefold()


def build_request_payload(
    *, principal: str, thread: str, commit: str, policy: Policy
) -> dict[str, Any]:
    if thread not in policy.threads:
        raise DispatchError(f"thread {thread!r} is not enabled by dispatcher policy")
    return {
        "from_agent": principal,
        "to_agent": policy.principal,
        "thread": thread,
        "topic": policy.topic,
        "lang": "en",
        "tags": [policy.tag],
        "body": json.dumps(
            {"version": 1, "kind": "commit", "commit": commit},
            separators=(",", ":"),
            sort_keys=False,
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Request an isolated Codex review of an immutable commit."
    )
    parser.add_argument("--config", default="", help="Caller Watercooler session config.")
    parser.add_argument("--policy", default=str(default_policy_path()))
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--commit", default="HEAD", help="Git revision; resolved to a full SHA.")
    parser.add_argument("--thread", default="mamba-bridge")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        policy = load_policy(Path(args.policy).expanduser().resolve())
        config = load_config(args.config)
        principal = validate_sender_config(config, policy)
        commit = resolve_commit(Path(args.repo_root).expanduser().resolve(), args.commit)
        payload = build_request_payload(
            principal=principal,
            thread=args.thread,
            commit=commit,
            policy=policy,
        )
        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        response = request_json(config, method="POST", path="/v1/post", payload=payload)
    except (
        DispatchError,
        WatercoolerError,
        OSError,
        ValueError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"review request failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
