#!/usr/bin/env python3
"""Tiny fixed-argv filesystem tool used by the Phase-2 capture boundary."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-text", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        text = args.read_text.read_text(encoding="utf-8")
    except FileNotFoundError:
        print("not_found", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"tool_error:{type(exc).__name__}", file=sys.stderr)
        return 1
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
