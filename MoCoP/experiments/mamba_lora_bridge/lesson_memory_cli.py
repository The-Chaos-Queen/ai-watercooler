"""
Lesson Memory v0 CLI (task #112).

Three verbs: add, list, show. No `revise` in v0 — to supersede a lesson, run
`list` to find the old lesson_id, then drop into a short Python script that
constructs a new Lesson with `supersedes=<old_id>` and calls
LessonMemory.add(). Awkward by design; v0 ships the substrate, not the
editing UX. v0.5 will add `revise`.

UTF-8 is explicit on every read/write because the Windows default is cp1252
and would silently corrupt non-ASCII content.

Usage examples:

    python lesson_memory_cli.py add \\
        --title "prefer the harder true thing" \\
        --frame correction \\
        --wrong-policy-named helpful_assistant_attractor \\
        --strategy "name the deflection, not just the fact" \\
        --created-by gidim \\
        --corrected-by laura \\
        --occasion "review feedback on #112" \\
        --session-id sess-001

    python lesson_memory_cli.py list
    python lesson_memory_cli.py list --include-superseded
    python lesson_memory_cli.py show <lesson_id>

Author: Gidim
Task: #112
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from lesson_memory import (
    Lesson,
    LessonMemory,
    SourceMemoryRef,
)


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lesson Memory v0 CLI (add / list / show).",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="JSONL path override (default: data/lessons.jsonl beside the module).",
    )
    parser.add_argument(
        "--embeddings-path",
        type=Path,
        default=None,
        help="Embedding matrix override (default: data/lessons_embeddings.npy).",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=None,
        help="Embedding index override (default: data/lessons_embeddings_index.json).",
    )

    sub = parser.add_subparsers(dest="verb", required=True)

    add = sub.add_parser("add", help="Append a new lesson.")
    add.add_argument("--title", required=True)
    add.add_argument("--frame", required=True)
    add.add_argument("--wrong-policy-named", required=True, dest="wrong_policy_named")
    add.add_argument("--strategy", required=True)
    add.add_argument("--supersedes", default=None)
    add.add_argument("--lesson-id", default=None, dest="lesson_id",
                     help="Optional explicit UUID. Generated if omitted.")
    add.add_argument("--created-by", required=True, dest="created_by")
    add.add_argument("--corrected-by", required=True, dest="corrected_by")
    add.add_argument("--occasion", required=True)
    add.add_argument("--session-id", required=True, dest="session_id")
    add.add_argument("--created-ts", default=None, dest="created_ts",
                     help="ISO timestamp; defaults to now.")
    add.add_argument(
        "--source-ref",
        action="append",
        default=[],
        dest="source_refs",
        help=(
            "Repeatable source ref as 'qdrant_id:content_hash'. "
            "Leave qdrant_id empty for orphaned refs ('::<hash>')."
        ),
    )

    lst = sub.add_parser("list", help="List visible lessons (one per line).")
    lst.add_argument(
        "--include-superseded",
        action="store_true",
        help="Include lessons that have been superseded by later edits.",
    )

    show = sub.add_parser("show", help="Pretty-print a lesson by id.")
    show.add_argument("lesson_id")

    return parser


def _parse_source_refs(raw: List[str]) -> List[SourceMemoryRef]:
    refs: List[SourceMemoryRef] = []
    for entry in raw:
        if entry.startswith("::"):
            qid_part = ""
            hash_part = entry[2:]
        elif entry.startswith(":"):
            qid_part = ""
            hash_part = entry[1:]
        elif ":" in entry:
            qid_part, hash_part = entry.split(":", 1)
        else:
            raise SystemExit(
                f"--source-ref must be 'qdrant_id:content_hash' or '::<hash>' "
                f"for orphaned refs (got {entry!r})"
            )
        if not hash_part:
            raise SystemExit(
                f"--source-ref content_hash must not be empty (got {entry!r})"
            )
        refs.append(SourceMemoryRef(
            qdrant_point_id=qid_part or None,
            content_hash=hash_part,
        ))
    return refs


def _cmd_add(args: argparse.Namespace, store: LessonMemory) -> int:
    provenance = {
        "created_by": args.created_by,
        "created_ts": args.created_ts or _now_iso(),
        "corrected_by": args.corrected_by,
        "occasion": args.occasion,
        "session_id": args.session_id,
    }
    lesson = Lesson(
        lesson_id=args.lesson_id or str(uuid.uuid4()),
        title=args.title,
        frame=args.frame,
        wrong_policy_named=args.wrong_policy_named,
        strategy=args.strategy,
        provenance=provenance,
        source_memory_refs=_parse_source_refs(args.source_refs),
        supersedes=args.supersedes,
    )
    store.add(lesson)
    print(f"added lesson {lesson.lesson_id}")
    return 0


def _cmd_list(args: argparse.Namespace, store: LessonMemory) -> int:
    lessons = store.all(include_superseded=args.include_superseded)
    if not lessons:
        print("(no lessons)")
        return 0
    for lesson in lessons:
        marker = " [superseded]" if (
            args.include_superseded
            and lesson.lesson_id in store._superseded_ids  # noqa: SLF001
        ) else ""
        print(f"{lesson.lesson_id}\t{lesson.frame}\t{lesson.title}{marker}")
    return 0


def _cmd_show(args: argparse.Namespace, store: LessonMemory) -> int:
    lesson = store.get(args.lesson_id)
    if lesson is None:
        print(f"no lesson with id {args.lesson_id!r}", file=sys.stderr)
        return 1
    payload = asdict(lesson)
    payload["source_memory_refs"] = [
        {"qdrant_point_id": ref.qdrant_point_id, "content_hash": ref.content_hash}
        for ref in lesson.source_memory_refs
    ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    store = LessonMemory(
        path=args.path,
        embeddings_path=args.embeddings_path,
        index_path=args.index_path,
    )

    if args.verb == "add":
        return _cmd_add(args, store)
    if args.verb == "list":
        return _cmd_list(args, store)
    if args.verb == "show":
        return _cmd_show(args, store)
    parser.error(f"unknown verb {args.verb!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
