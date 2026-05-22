"""SQLite engine + session setup.

DB path is taken from EISSTOCK_DB env var (default: ./data/eisstock.db).
Use `init_db()` at app startup to create tables.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine


def _db_url() -> str:
    raw = os.environ.get("EISSTOCK_DB", "./data/eisstock.db")
    path = Path(raw).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


engine = create_engine(
    _db_url(),
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    # Import models so SQLModel.metadata sees every table.
    from eisstock import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
