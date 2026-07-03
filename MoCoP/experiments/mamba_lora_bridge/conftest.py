"""Shared pytest configuration for mamba_lora_bridge.

Bare `pytest` collects only lightweight tests (no torch, no Qdrant, no live
server). Use `-m gpu` or `-m numpy` to include heavier suites. Run everything
with `pytest -m ""`.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_collection_modifyitems(config, items):
    """Auto-apply markers based on file location for root-level test files.

    Tests under tests/ and archivist_mamba/tests/ are collected by testpaths
    and must carry their own markers if needed. Root-level test_*.py files
    are NOT in testpaths (they often import torch transitively) — if you
    want to collect them, run `pytest test_bridge.py -m gpu` explicitly.
    """
