from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from common import (
    load_config,
    pretty_message,
    pretty_task,
    pretty_task_event,
    request_json,
)


def add_agent_arg(parser: argparse.ArgumentParser, *, help_text: str = "Agent identity override.") -> None:
    parser.add_argument("--agent", type=str, default="", help=help_text)


def config_principal(config: Dict[str, Any]) -> str:
    return str(config.get("principal") or config.get("default_from") or "codex")


def default_agent(config: Dict[str, Any], value: str) -> str:
    principal = config_principal(config)
    if value and value != principal:
        raise SystemExit(
            f"--agent {value!r} does not match token principal {principal!r}; "
            "use that agent's session token or a lifecycle command such as reassign."
        )
    return principal


def print_task_list(tasks: List[Dict[str, Any]]) -> None:
    if not tasks:
        print("No tasks.")
        return
    for task in tasks:
        print(pretty_task(task))
        print()


def handle_create(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    payload = {
        "created_by": default_agent(config, args.agent),
        "project": args.project,
        "thread": args.thread or args.project,
        "title": args.title,
        "description": args.description,
        "priority": args.priority,
        "cost_class": args.cost_class,
        "trust_class": args.trust_class,
        "assignee": args.assignee,
        "labels": list(args.label or []),
        "refs": list(args.ref or []),
        "note": args.note,
    }
    result = request_json(config, method="POST", path="/v1/tasks", payload=payload)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(pretty_task(result["task"]))
    return 0


def handle_list(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    result = request_json(
        config,
        method="GET",
        path="/v1/tasks",
        query={
            "status": args.status,
            "project": args.project,
            "assignee": args.assignee,
            "thread": args.thread,
            "task_id": args.task_id or "",
            "limit": args.limit,
        },
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print_task_list(result.get("tasks", []))
    return 0


def handle_next(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    query = {
        "project": args.project,
        "thread": args.thread,
    }
    if args.agent:
        query["agent"] = args.agent
    result = request_json(
        config,
        method="GET",
        path="/v1/tasks/next",
        query=query,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    task = result.get("task")
    if not task:
        print("No matching task.")
        return 0
    print(f"selection={result.get('selection_reason')}")
    print(pretty_task(task))
    return 0


def handle_state_change(args: argparse.Namespace, config: Dict[str, Any], *, path: str, extra_payload: Dict[str, Any]) -> int:
    payload = {
        "task_id": args.task_id,
        "agent": default_agent(config, args.agent),
        "note": getattr(args, "note", ""),
    }
    if hasattr(args, "lease_seconds"):
        payload["lease_seconds"] = args.lease_seconds
    payload.update(extra_payload)
    result = request_json(config, method="POST", path=path, payload=payload)
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(pretty_task(result["task"]))
    return 0


def handle_comment(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    return handle_state_change(args, config, path="/v1/tasks/comment", extra_payload={})


def handle_reassign(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    return handle_state_change(
        args,
        config,
        path="/v1/tasks/reassign",
        extra_payload={"assignee": args.assignee, "keep_claim": args.keep_claim},
    )


def handle_release(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    return handle_state_change(args, config, path="/v1/tasks/release", extra_payload={})


def handle_unblock(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    return handle_state_change(args, config, path="/v1/tasks/unblock", extra_payload={})


def handle_board(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    result = request_json(
        config,
        method="GET",
        path="/v1/board",
        query={"project": args.project, "limit_per_status": args.limit_per_status},
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    counts = result.get("counts", {})
    print(
        "counts: "
        + ", ".join(
            f"{status}={counts.get(status, 0)}" for status in ("queued", "claimed", "blocked", "done")
        )
    )
    active_agents = result.get("active_agents") or []
    if active_agents:
        print("active_agents: " + ", ".join(active_agents))
    for status in ("claimed", "queued", "blocked", "done"):
        print(f"\n[{status}]")
        print_task_list(result.get("tasks", {}).get(status, []))
    return 0


def handle_liveness(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    result = request_json(
        config,
        method="GET",
        path="/v1/tasks/liveness",
        query={"project": args.project},
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    blocked = result.get("blocked", {})
    print(
        "blocked: "
        f"count={blocked.get('count', 0)}, "
        f"median_age_days={blocked.get('median_age_days', 0)}, "
        f"p95_age_days={blocked.get('p95_age_days', 0)}, "
        f"oldest_age_days={blocked.get('oldest_age_days', 0)}"
    )
    items = blocked.get("items", [])
    if not items:
        print("No blocked tasks.")
        return 0
    for item in items:
        marker = "REVIEW" if item.get("recommended_review") else "ok"
        signals = ",".join(item.get("signals", [])) or "none"
        print(
            f"[{item['id']}] {marker} age={item.get('blocked_age_days')}d "
            f"last={item.get('last_event_age_days')}d signals={signals} "
            f"assignee={item.get('assignee') or '-'} :: {item.get('title')}"
        )
        if item.get("blocked_reason"):
            print(f"  blocked={item['blocked_reason']}")
    return 0


def handle_context(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    result = request_json(
        config,
        method="GET",
        path="/v1/context",
        query={
            "task_id": args.task_id,
            "event_limit": args.event_limit,
            "message_limit": args.message_limit,
        },
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(pretty_task(result["task"]))
    events = result.get("events", [])
    messages = result.get("messages", [])
    print("\n[events]")
    if not events:
        print("No events.")
    else:
        for event in events:
            print(pretty_task_event(event))
            print()
    print("[messages]")
    if not messages:
        print("No messages.")
    else:
        for message in messages:
            print(pretty_message(message))
            print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenCLAW v0 CLI for the AI watercooler service.")
    parser.add_argument("--config", type=str, default="", help="Optional config path override.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new task.")
    add_agent_arg(create_parser, help_text="Task creator override.")
    create_parser.add_argument("--project", type=str, default="general")
    create_parser.add_argument("--thread", type=str, default="")
    create_parser.add_argument("--title", type=str, required=True)
    create_parser.add_argument("--description", type=str, default="")
    create_parser.add_argument("--priority", type=int, default=50)
    create_parser.add_argument("--cost-class", type=str, default="local")
    create_parser.add_argument("--trust-class", type=str, default="safe")
    create_parser.add_argument("--assignee", type=str, default="")
    create_parser.add_argument("--label", action="append", default=[])
    create_parser.add_argument("--ref", action="append", default=[])
    create_parser.add_argument("--note", type=str, default="")
    create_parser.add_argument("--json", action="store_true")
    create_parser.set_defaults(handler=handle_create)

    list_parser = subparsers.add_parser("list", help="List tasks.")
    list_parser.add_argument("--task-id", type=int, default=0)
    list_parser.add_argument("--status", type=str, default="")
    list_parser.add_argument("--project", type=str, default="")
    list_parser.add_argument("--assignee", type=str, default="")
    list_parser.add_argument("--thread", type=str, default="")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(handler=handle_list)

    next_parser = subparsers.add_parser("next", help="Get the next task for an agent.")
    add_agent_arg(next_parser)
    next_parser.add_argument("--project", type=str, default="")
    next_parser.add_argument("--thread", type=str, default="")
    next_parser.add_argument("--json", action="store_true")
    next_parser.set_defaults(handler=handle_next)

    claim_parser = subparsers.add_parser("claim", help="Claim a task lease.")
    add_agent_arg(claim_parser)
    claim_parser.add_argument("--task-id", type=int, required=True)
    claim_parser.add_argument("--lease-seconds", type=int, default=1800)
    claim_parser.add_argument("--note", type=str, default="")
    claim_parser.add_argument("--json", action="store_true")
    claim_parser.set_defaults(handler=lambda a, c: handle_state_change(a, c, path="/v1/tasks/claim", extra_payload={}))

    heartbeat_parser = subparsers.add_parser("heartbeat", help="Renew a task lease.")
    add_agent_arg(heartbeat_parser)
    heartbeat_parser.add_argument("--task-id", type=int, required=True)
    heartbeat_parser.add_argument("--lease-seconds", type=int, default=1800)
    heartbeat_parser.add_argument("--note", type=str, default="")
    heartbeat_parser.add_argument("--json", action="store_true")
    heartbeat_parser.set_defaults(
        handler=lambda a, c: handle_state_change(a, c, path="/v1/tasks/heartbeat", extra_payload={})
    )

    complete_parser = subparsers.add_parser("complete", help="Complete a task.")
    add_agent_arg(complete_parser)
    complete_parser.add_argument("--task-id", type=int, required=True)
    complete_parser.add_argument("--note", type=str, default="")
    complete_parser.add_argument("--artifact", action="append", default=[])
    complete_parser.add_argument("--json", action="store_true")
    complete_parser.set_defaults(
        handler=lambda a, c: handle_state_change(
            a,
            c,
            path="/v1/tasks/complete",
            extra_payload={"artifacts": list(a.artifact or [])},
        )
    )

    block_parser = subparsers.add_parser("block", help="Mark a task blocked.")
    add_agent_arg(block_parser)
    block_parser.add_argument("--task-id", type=int, required=True)
    block_parser.add_argument("--blocked-reason", type=str, required=True)
    block_parser.add_argument("--note", type=str, default="")
    block_parser.add_argument("--json", action="store_true")
    block_parser.set_defaults(
        handler=lambda a, c: handle_state_change(
            a,
            c,
            path="/v1/tasks/block",
            extra_payload={"blocked_reason": a.blocked_reason},
        )
    )

    comment_parser = subparsers.add_parser("comment", help="Add a task comment without changing state.")
    add_agent_arg(comment_parser)
    comment_parser.add_argument("--task-id", type=int, required=True)
    comment_parser.add_argument("--note", type=str, required=True)
    comment_parser.add_argument("--json", action="store_true")
    comment_parser.set_defaults(handler=handle_comment)

    reassign_parser = subparsers.add_parser("reassign", help="Assign/reassign a task and clear any claim by default.")
    add_agent_arg(reassign_parser)
    reassign_parser.add_argument("--task-id", type=int, required=True)
    reassign_parser.add_argument("--assignee", type=str, default="")
    reassign_parser.add_argument("--keep-claim", action="store_true")
    reassign_parser.add_argument("--note", type=str, default="")
    reassign_parser.add_argument("--json", action="store_true")
    reassign_parser.set_defaults(handler=handle_reassign)

    release_parser = subparsers.add_parser("release", help="Release/unclaim a claimed task back to queued.")
    add_agent_arg(release_parser)
    release_parser.add_argument("--task-id", type=int, required=True)
    release_parser.add_argument("--note", type=str, default="")
    release_parser.add_argument("--json", action="store_true")
    release_parser.set_defaults(handler=handle_release)

    unblock_parser = subparsers.add_parser("unblock", help="Move a blocked task back to queued.")
    add_agent_arg(unblock_parser)
    unblock_parser.add_argument("--task-id", type=int, required=True)
    unblock_parser.add_argument("--note", type=str, default="")
    unblock_parser.add_argument("--json", action="store_true")
    unblock_parser.set_defaults(handler=handle_unblock)

    board_parser = subparsers.add_parser("board", help="Show the task board.")
    board_parser.add_argument("--project", type=str, default="")
    board_parser.add_argument("--limit-per-status", type=int, default=5)
    board_parser.add_argument("--json", action="store_true")
    board_parser.set_defaults(handler=handle_board)

    liveness_parser = subparsers.add_parser("liveness", help="Show blocked-card liveness/hygiene report.")
    liveness_parser.add_argument("--project", type=str, default="")
    liveness_parser.add_argument("--json", action="store_true")
    liveness_parser.set_defaults(handler=handle_liveness)

    context_parser = subparsers.add_parser("context", help="Show task context, events, and recent thread messages.")
    context_parser.add_argument("--task-id", type=int, required=True)
    context_parser.add_argument("--event-limit", type=int, default=20)
    context_parser.add_argument("--message-limit", type=int, default=20)
    context_parser.add_argument("--json", action="store_true")
    context_parser.set_defaults(handler=handle_context)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    return int(args.handler(args, config))


if __name__ == "__main__":
    raise SystemExit(main())
