from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:  # direct script execution: python archivist_mamba/retrieve_cases.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from .case_store import filter_cases, iter_cases
    from .schemas import MemoryCase
except ImportError:  # pragma: no cover - direct script execution
    from archivist_mamba.case_store import filter_cases, iter_cases
    from archivist_mamba.schemas import MemoryCase

TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RankedCase:
    case: MemoryCase
    score: float
    reasons: list[str]


def tokenize(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def case_text(case: MemoryCase) -> str:
    return " ".join([case.title, case.summary, " ".join(case.topics), case.agent, case.project])


def score_case(query: str, case: MemoryCase) -> RankedCase:
    query_tokens = tokenize(query)
    candidate_tokens = tokenize(case_text(case))
    overlap = query_tokens & candidate_tokens
    score = float(len(overlap))
    reasons = [f"token_overlap={len(overlap)}"]

    if case.status == "active":
        score += 0.75
        reasons.append("active_status_boost")
    elif case.status in {"superseded", "stale"}:
        score -= 0.75
        reasons.append(f"{case.status}_penalty")

    if case.authority in {"curated", "canonical"}:
        score += 0.5
        reasons.append("high_authority_boost")
    elif case.authority == "raw":
        score -= 0.25
        reasons.append("raw_authority_penalty")

    score += max(0.0, min(1.0, case.confidence)) * 0.1
    return RankedCase(case=case, score=score, reasons=reasons)


def rank_cases(
    query: str,
    cases: Iterable[MemoryCase],
    *,
    domain: list[str] | None = None,
    memory_type: list[str] | None = None,
    agent: list[str] | None = None,
    project: list[str] | None = None,
    status: list[str] | None = None,
    authority: list[str] | None = None,
    limit: int = 10,
) -> list[RankedCase]:
    filtered = filter_cases(
        cases,
        domain=domain,
        memory_type=memory_type,
        agent=agent,
        project=project,
        status=status,
        authority=authority,
    )
    ranked = [score_case(query, case) for case in filtered]
    ranked.sort(key=lambda item: (item.score, item.case.confidence, item.case.id), reverse=True)
    return ranked[:limit]


def _csv(values: list[str] | None) -> str:
    return ",".join(values or [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve Archivist memory cases with metadata filters.")
    parser.add_argument("query")
    parser.add_argument("--cases", required=True, help="Path to cases.jsonl")
    parser.add_argument("--domain", action="append", default=[])
    parser.add_argument("--memory-type", action="append", default=[])
    parser.add_argument("--agent", action="append", default=[])
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--status", action="append", default=[])
    parser.add_argument("--authority", action="append", default=[])
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    ranked = rank_cases(
        args.query,
        iter_cases(args.cases),
        domain=args.domain or None,
        memory_type=args.memory_type or None,
        agent=args.agent or None,
        project=args.project or None,
        status=args.status or None,
        authority=args.authority or None,
        limit=args.limit,
    )
    print(f"Archivist results for: {args.query}")
    print(f"Filters: domain={_csv(args.domain)} memory_type={_csv(args.memory_type)} agent={_csv(args.agent)} status={_csv(args.status)}")
    for idx, item in enumerate(ranked, 1):
        case = item.case
        print(f"\n{idx}. {case.id} [{case.domain}/{case.memory_type}/{case.status}] score={item.score:.2f}")
        print(f"   {case.title}")
        print(f"   {case.summary}")
        if case.evidence:
            ref = case.evidence[0]
            print(f"   Evidence: {ref.source_path}:{ref.line_start or ''}-{ref.line_end or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
