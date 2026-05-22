#!/usr/bin/env python3
"""Minimal offline scorer for ARC-AGI-3 LS20-style trace fixtures.

This is deliberately trace-level only. It does not start ARC gameplay, call Alex,
or integrate with chat_server.py. The scorer checks two v0 friction failures:

- state confabulation: response claims objects/actions not present in observation;
- illegal action: chosen action is not listed in available_actions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

OBSERVABLE_OBJECT_TERMS = {
    "player",
    "wall",
    "door",
    "goal",
    "tile",
    "grid",
    "cursor",
    "key",
}

CONFABULATION_TERMS = {
    "block",
    "switch",
    "button",
    "enemy",
    "box",
    "crate",
    "teleporter",
    "portal",
    "laser",
}


def _terms_in_text(text: str, terms: set[str]) -> set[str]:
    lower = text.lower()
    found: set[str] = set()
    for term in terms:
        if re.search(rf"\b{re.escape(term)}s?\b", lower):
            found.add(term)
    return found


def _observed_terms_in_text(text: str, terms: set[str]) -> set[str]:
    """Extract observed terms, ignoring simple negated mentions like "no key"."""

    lower = text.lower()
    found: set[str] = set()
    for term in terms:
        if not re.search(rf"\b{re.escape(term)}s?\b", lower):
            continue
        if re.search(rf"\b(no|not|without)\s+(?:\w+\s+){{0,2}}{re.escape(term)}s?\b", lower):
            continue
        found.add(term)
    return found


def observed_terms_for_event(event: dict[str, Any]) -> set[str]:
    """Return explicit observed terms for one trace event."""

    terms = _observed_terms_in_text(
        str(event.get("observation", "")), OBSERVABLE_OBJECT_TERMS | CONFABULATION_TERMS
    )
    for item in event.get("observed_objects", []) or []:
        if item:
            terms.add(str(item).lower())
    return terms


def load_jsonl_trace(path: str | Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"Trace event at {path}:{line_number} must be a JSON object")
        events.append(event)
    return events


def score_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    state_confabulation_count = 0
    illegal_action_count = 0

    for event in events:
        t = event.get("t")
        observed = observed_terms_for_event(event)
        response = str(event.get("agent_response", event.get("response", "")))
        mentioned_confab_terms = _terms_in_text(response, CONFABULATION_TERMS)
        available_actions = {str(action).lower() for action in event.get("available_actions", []) or []}
        unobserved_terms = sorted(term for term in mentioned_confab_terms if term not in observed)

        if unobserved_terms:
            state_confabulation_count += len(unobserved_terms)
            violations.append(
                {
                    "t": t,
                    "kind": "state_confabulation",
                    "observed_terms": sorted(observed),
                    "unobserved_terms": unobserved_terms,
                    "detail": "Response mentions LS20 objects/actions not present in this observation.",
                }
            )

        action = event.get("action")
        if action is not None and str(action).lower() not in available_actions:
            illegal_action_count += 1
            violations.append(
                {
                    "t": t,
                    "kind": "illegal_action",
                    "action": action,
                    "available_actions": sorted(available_actions),
                    "detail": "Chosen action is not available in this trace state.",
                }
            )

    return {
        "event_count": len(events),
        "state_confabulation_count": state_confabulation_count,
        "illegal_action_count": illegal_action_count,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score an offline LS20 JSONL trace fixture.")
    parser.add_argument(
        "trace",
        nargs="?",
        default=str(Path(__file__).parent / "fixtures" / "arc_agi3_ls20_level0_trace.sample.jsonl"),
    )
    parser.add_argument("--json", action="store_true", help="Emit compact JSON instead of pretty JSON")
    args = parser.parse_args()

    report = score_events(load_jsonl_trace(args.trace))
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["state_confabulation_count"] or report["illegal_action_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
