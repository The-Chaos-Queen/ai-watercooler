from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Iterator
from pathlib import Path

if __package__ in {None, ""}:  # direct script execution: python archivist_mamba/case_extractor.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from .case_store import append_cases
    from .log_parser import iter_codex_events
    from .schemas import EvidenceRef, MemoryCase, now_iso, validate_case
except ImportError:  # pragma: no cover - direct script execution
    from archivist_mamba.case_store import append_cases
    from archivist_mamba.log_parser import iter_codex_events
    from archivist_mamba.schemas import EvidenceRef, MemoryCase, now_iso, validate_case

CORRECTION_MARKERS = ("no", "don't", "do not", "actually", "current repo", "unless prior context", "by default")
FAILURE_MARKERS = ("error", "failed", "failure", "traceback", "timeout", "doesn't work", "exit_code")


def infer_domain(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("codex", "claude", "hermes", "agent", "watercooler", "session log", "archaeology", "current repo")):
        return "meta"
    if any(token in lower for token in ("mocop", "alex", "mamba", "qdrant")):
        return "research"
    if any(token in lower for token in ("fiction", "chapter", "character", "scene")):
        return "creative"
    return "unknown"


def _case_id(source_path: str | Path, line_no: int, memory_type: str, text: str) -> str:
    digest = hashlib.sha1(f"{source_path}:{line_no}:{memory_type}:{text}".encode("utf-8")).hexdigest()[:12]
    return f"archivist-{memory_type}-{digest}"


def _evidence(source_path: str | Path, event: dict) -> EvidenceRef:
    line_no = int(event.get("line_no") or 0)
    quote = str(event.get("text") or "")[:240]
    return EvidenceRef(
        source_path=str(source_path),
        source_type="codex_rollout",
        line_start=line_no or None,
        line_end=line_no or None,
        quote=quote,
    )


def _topics(text: str) -> list[str]:
    lower = text.lower()
    topics = []
    for token in ("codex", "claude", "hermes", "logs", "qdrant", "mamba", "watercooler", "boot"):
        if token in lower:
            topics.append(token)
    return topics or ["unknown"]


def extract_cases_from_codex_log(path: str | Path, *, max_cases: int = 100) -> Iterator[MemoryCase]:
    """Extract bounded heuristic case records from a Codex rollout log."""
    count = 0
    extracted_at = now_iso()
    for event in iter_codex_events(path, max_text_chars=1000):
        text = str(event.get("text") or "").strip()
        if not text:
            continue
        lower = text.lower()
        memory_type: str | None = None
        outcome = "unknown"
        title = ""
        summary = text
        failure_modes: list[str] = []
        applies_when: list[str] = []
        does_not_apply_when: list[str] = []
        confidence = 0.55

        if event.get("event_type") == "tool_error" or any(marker in lower for marker in FAILURE_MARKERS):
            memory_type = "failure"
            outcome = "failure"
            title = "Tool or workflow failure in Codex session"
            failure_modes = [text[:180]]
            confidence = 0.65
        elif event.get("role") == "user" and any(marker in lower for marker in CORRECTION_MARKERS):
            memory_type = "rule"
            outcome = "partial"
            title = "User correction about agent behavior"
            applies_when = ["Task depends on current repository state", "Historical context is not explicitly requested"]
            does_not_apply_when = ["Laura references prior work or says this was decided before", "Exact historical evidence is needed"]
            confidence = 0.75
        else:
            continue

        case = MemoryCase(
            id=_case_id(path, int(event.get("line_no") or 0), memory_type, text),
            title=title,
            domain=infer_domain(text),
            memory_type=memory_type,  # type: ignore[arg-type]
            outcome=outcome,  # type: ignore[arg-type]
            authority="extracted",
            status="active",
            agent="codex",
            project="mocop",
            topics=_topics(text),
            summary=summary,
            failure_modes=failure_modes,
            applies_when=applies_when,
            does_not_apply_when=does_not_apply_when,
            confidence=confidence,
            event_date=str(event.get("timestamp") or ""),
            extracted_at=extracted_at,
            evidence=[_evidence(path, event)],
        )
        validate_case(case)
        yield case
        count += 1
        if count >= max_cases:
            return


def main() -> int:
    parser = argparse.ArgumentParser(description="Heuristically extract Archivist cases from Codex rollout JSONL.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-cases", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cases = list(extract_cases_from_codex_log(args.input, max_cases=args.max_cases))
    print(f"Extracted {len(cases)} cases from {args.input}")
    for case in cases[:10]:
        print(f"- {case.id} [{case.domain}/{case.memory_type}] {case.summary[:100]}")
    if not args.dry_run:
        append_cases(args.output, cases)
        print(f"Wrote {len(cases)} cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
