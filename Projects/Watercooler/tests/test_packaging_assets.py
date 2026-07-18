from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError
from pathlib import Path

from watercooler import assets

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_asset_locator_exposes_every_public_source_asset(capsys):
    assert assets.asset_root() == PROJECT_ROOT
    for name in assets.ASSETS:
        assert assets.asset_path(name).exists()

    assert assets.main(["web"]) == 0
    assert Path(capsys.readouterr().out.strip()) == PROJECT_ROOT / "web" / "index.html"

    assert assets.main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == set(assets.ASSETS)
    assert Path(payload["reviewer"]) == PROJECT_ROOT / "integrations" / "codex-reviewer"


def test_asset_locator_supports_pip_target_layout(tmp_path, monkeypatch):
    package_dir = tmp_path / "target" / "watercooler"
    marker = tmp_path / "target" / "share" / "watercooler" / "web" / "index.html"
    package_dir.mkdir(parents=True)
    marker.parent.mkdir(parents=True)
    marker.write_text("<!doctype html>", encoding="utf-8")

    monkeypatch.setattr(assets, "__file__", str(package_dir / "assets.py"))
    monkeypatch.setattr(assets, "distribution", lambda _name: (_ for _ in ()).throw(PackageNotFoundError()))

    assert assets.asset_root() == marker.parents[1]


def test_package_configuration_includes_advertised_assets_and_cli():
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for expected in (
        'watercooler-assets = "watercooler.assets:main"',
        '"share/watercooler/web" = ["web/index.html"]',
        '"share/watercooler/docs" = ["docs/architecture.md"]',
        '"share/watercooler/integrations/codex-reviewer"',
        '"share/watercooler/integrations/codex-reviewer/windows"',
        '"integrations/codex-reviewer/review-schema.json"',
        '"integrations/codex-reviewer/windows/install-scheduled-task.ps1"',
    ):
        assert expected in pyproject


def test_sdist_manifest_includes_nested_tests_and_public_assets():
    manifest = (PROJECT_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    for expected in (
        "include SECURITY.md",
        "include THIRD_PARTY_NOTICES.md",
        "recursive-include docs *.md",
        "recursive-include integrations/codex-reviewer",
        "recursive-include tests *.py",
        "recursive-include web *.html",
    ):
        assert expected in manifest
