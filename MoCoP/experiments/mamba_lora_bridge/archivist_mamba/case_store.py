from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

try:
    from .schemas import MemoryCase, validate_case
except ImportError:  # pragma: no cover - direct script execution
    from archivist_mamba.schemas import MemoryCase, validate_case


def append_cases(path: str | Path, cases: Iterable[MemoryCase]) -> int:
    """Append validated cases to a JSONL store.

    Validation happens before opening the output path so invalid batches do not
    create partial files.
    """
    case_list = list(cases)
    for case in case_list:
        validate_case(case)

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        for case in case_list:
            handle.write(json.dumps(case.to_json(), ensure_ascii=False, sort_keys=True) + "\n")
    return len(case_list)


def iter_cases(path: str | Path) -> Iterator[MemoryCase]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            yield MemoryCase.from_json(json.loads(line))


def _matches(value: str, allowed: list[str] | tuple[str, ...] | set[str] | None) -> bool:
    return not allowed or value in allowed


def filter_cases(
    cases: Iterable[MemoryCase],
    *,
    domain: list[str] | None = None,
    memory_type: list[str] | None = None,
    agent: list[str] | None = None,
    project: list[str] | None = None,
    status: list[str] | None = None,
    authority: list[str] | None = None,
) -> Iterator[MemoryCase]:
    for case in cases:
        if not _matches(case.domain, domain):
            continue
        if not _matches(case.memory_type, memory_type):
            continue
        if not _matches(case.agent, agent):
            continue
        if not _matches(case.project, project):
            continue
        if not _matches(case.status, status):
            continue
        if not _matches(case.authority, authority):
            continue
        yield case
