"""Locate documentation and integration assets in source or installed layouts."""

from __future__ import annotations

import argparse
import json
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Sequence

DIST_NAME = "watercooler-agents"
MARKER = Path("web") / "index.html"
ASSETS = {
    "root": Path("."),
    "web": MARKER,
    "web-dir": Path("web"),
    "license": Path("LICENSE"),
    "notice": Path("NOTICE"),
    "architecture": Path("docs") / "architecture.md",
    "security": Path("SECURITY.md"),
    "notices": Path("THIRD_PARTY_NOTICES.md"),
    "reviewer": Path("integrations") / "codex-reviewer",
    "review-schema": Path("integrations") / "codex-reviewer" / "review-schema.json",
    "policy-example": (
        Path("integrations") / "codex-reviewer" / "dispatcher-policy.example.json"
    ),
}


def _source_asset_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    return candidate if (candidate / MARKER).is_file() else None


def _target_install_asset_root() -> Path | None:
    """Locate data files beside a ``pip install --target`` package tree."""

    candidate = Path(__file__).resolve().parents[1] / "share" / "watercooler"
    return candidate if (candidate / MARKER).is_file() else None


def _installed_asset_root() -> Path | None:
    try:
        installed = distribution(DIST_NAME)
    except PackageNotFoundError:
        return None

    suffix = "/share/watercooler/web/index.html"
    for entry in installed.files or ():
        if not ("/" + entry.as_posix()).endswith(suffix):
            continue
        marker = Path(installed.locate_file(entry)).resolve()
        candidate = marker.parent.parent
        if marker.is_file():
            return candidate
    return None


def asset_root() -> Path:
    """Return the source-tree or installed ``share/watercooler`` directory."""

    root = _source_asset_root() or _target_install_asset_root() or _installed_asset_root()
    if root is None:
        raise FileNotFoundError(
            "Watercooler assets are unavailable; reinstall from a complete wheel or source tree"
        )
    return root


def asset_path(name: str) -> Path:
    """Return one named public asset path, requiring it to exist."""

    try:
        relative = ASSETS[name]
    except KeyError as exc:
        raise KeyError(f"unknown Watercooler asset: {name}") from exc
    path = (asset_root() / relative).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Watercooler asset is missing: {name}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print paths to installed Watercooler documentation and integration assets."
    )
    parser.add_argument("name", nargs="?", choices=tuple(ASSETS), default="root")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print every named asset path as one JSON object.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.json:
            payload = {name: str(asset_path(name)) for name in ASSETS}
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(asset_path(args.name))
    except (FileNotFoundError, KeyError) as exc:
        build_parser().error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
