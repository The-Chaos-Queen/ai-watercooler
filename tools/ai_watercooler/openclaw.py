"""Compatibility entry point for the renamed Watercooler Taskboard CLI."""

from __future__ import annotations

import warnings

from taskboard import *  # noqa: F403


if __name__ == "__main__":
    warnings.warn(
        "openclaw.py is deprecated; use taskboard.py",
        DeprecationWarning,
        stacklevel=1,
    )
    raise SystemExit(main())  # noqa: F405
