#!/usr/bin/env python3
"""Inert CLI for auditing Gemma harness answer-boundary behavior.

The default mode is deliberately model-free.  It accepts captured raw text and
emits a structured first-answer receipt.  ``--execute`` is a future explicit
run gate only; this spike intentionally does not load a model, touch ML-WS, or
modify any live MoCoP path.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

# Permit direct ``python spikes/...py`` use without turning ``spikes`` into a
# heavyweight package or importing model libraries.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemma_harness_contract import finalize_answer  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Model-free Gemma harness-contract receipt tool.  It preserves raw "
            "output and records the first continuation boundary."
        )
    )
    parser.add_argument(
        "--raw-text",
        help="Captured model output to audit; no model is loaded.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="Optional path for the structured receipt JSON.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Reserved explicit future gate. A future runner must pin a frozen "
            "candidate/config/prompt manifest and record raw+trimmed answers, "
            "stop reason, and generation settings."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.execute:
        parser.error(
            "--execute is intentionally unavailable in this contract-only spike; "
            "it cannot load a model or contact ML-WS."
        )
    if args.raw_text is None:
        parser.print_help()
        return 0

    receipt = finalize_answer(args.raw_text).as_dict()
    rendered = json.dumps(receipt, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
