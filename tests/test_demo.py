from __future__ import annotations

import gc
import json
import sqlite3
import threading
from contextlib import closing

import pytest

from watercooler.common import WatercoolerError, request_json
from watercooler.demo import restore_demo_database, seed_demo_database
from watercooler.service import WatercoolerHandler, WatercoolerServer


def test_demo_seed_is_scoped_grounded_and_resettable(tmp_path):
    db_path = tmp_path / "watercooler.db"
    snapshot_path = tmp_path / "seed.db"
    access_path = tmp_path / "demo-access.json"

    result = seed_demo_database(
        db_path=db_path,
        snapshot_path=snapshot_path,
        access_path=access_path,
        base_url="https://demo.example.test",
    )

    assert result["message_count"] == 7
    assert result["summary_revision_id"] == 1
    assert db_path.is_file()
    assert snapshot_path.is_file()
    access = json.loads(access_path.read_text(encoding="utf-8"))
    assert access["base_url"] == "https://demo.example.test"
    assert access["principal"] == "demo-judge"
    assert "summaries:publish" not in access["scopes"]

    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO messages (ts, from_agent, to_agent, thread, topic, lang, body, tags_json, remote_addr)
            VALUES ('2026-07-21T00:00:00Z', 'visitor', 'all', 'general', 'Disposable', 'en', ?, '[]', '127.0.0.1')
            """,
            ("This edit should disappear after reset.",),
        )
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 8
    del conn
    gc.collect()

    restore_demo_database(snapshot_path=snapshot_path, db_path=db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 7
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 4
        active = conn.execute("SELECT COUNT(*) FROM auth_tokens WHERE revoked_ts = ''").fetchone()[0]
        assert active == 1

    server = WatercoolerServer(
        ("127.0.0.1", 0),
        WatercoolerHandler,
        state={"db_path": str(db_path), "admin_token": "not-the-judge-token", "cors_origins": ()},
    )
    server.daemon_threads = False
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = {"base_url": f"http://127.0.0.1:{server.server_port}", "token": access["token"]}
    try:
        onboarding = request_json(
            config,
            method="GET",
            path="/v1/onboarding?thread=general&recent_limit=5",
        )
        assert onboarding["summary"]["revision_id"] == 1
        assert onboarding["summary"]["model_id"] == "gemma-4-e2b-it-demo"
        assert onboarding["authoritative_taskboard"]["counts"] == {
            "queued": 2,
            "claimed": 0,
            "blocked": 1,
            "done": 1,
        }
        assert onboarding["delta"]["uncovered_message_count"] == 1

        posted = request_json(
            config,
            method="POST",
            path="/v1/post",
            payload={
                "to_agent": "all",
                "thread": "general",
                "topic": "Judge interaction",
                "lang": "en",
                "body": "This edit should disappear after reset.",
                "tags": ["disposable"],
            },
        )
        assert posted["id"] == 8

        with pytest.raises(WatercoolerError, match="HTTP 403"):
            request_json(
                config,
                method="POST",
                path="/v1/summary",
                payload={"thread": "general", "body": "unauthorized"},
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_demo_seed_refuses_existing_outputs_without_force(tmp_path):
    db_path = tmp_path / "watercooler.db"
    snapshot_path = tmp_path / "seed.db"
    access_path = tmp_path / "demo-access.json"
    db_path.write_text("occupied", encoding="utf-8")

    with pytest.raises(FileExistsError, match="use --force"):
        seed_demo_database(
            db_path=db_path,
            snapshot_path=snapshot_path,
            access_path=access_path,
            base_url="https://demo.example.test",
        )
