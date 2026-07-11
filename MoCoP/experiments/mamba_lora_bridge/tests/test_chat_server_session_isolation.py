import pytest
import sys
import os
import copy
from unittest.mock import MagicMock

# Ensure chat_server can be imported if this is run from tests/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Keep the import cheap without replacing process-global dependencies for every
# test collected after this module.
_dependency_stubs = {
    "torch": MagicMock(),
    "torch.nn": MagicMock(),
    "torch.nn.functional": MagicMock(),
    "transformers": MagicMock(),
    "sentence_transformers": MagicMock(),
    "qdrant_client": MagicMock(),
    "qdrant_client.models": MagicMock(),
    "autobiographical_memory": MagicMock(),
    "memory_evidence": MagicMock(),
    "lesson_memory": MagicMock(),
    "astrocyte_memory_controller": MagicMock(),
    "failure_detector": MagicMock(),
    "mamba_runtime_compat": MagicMock(),
    "models": MagicMock(),
    "reincarnated_inference": MagicMock(),
}
_missing = object()
_previous_modules = {
    name: sys.modules.get(name, _missing)
    for name in (*_dependency_stubs, "chat_server")
}
try:
    sys.modules.update(_dependency_stubs)
    sys.modules.pop("chat_server", None)
    import chat_server
    from chat_server import (
        get_or_create_chat_session,
        switch_to_chat_session,
        save_active_chat_session,
    )
finally:
    for _name, _previous in _previous_modules.items():
        if _previous is _missing:
            sys.modules.pop(_name, None)
        else:
            sys.modules[_name] = _previous


def test_dependency_stubs_do_not_escape_collection():
    import torch

    assert not isinstance(torch, MagicMock)

@pytest.fixture(autouse=True)
def isolated_chat_server_globals():
    """
    Autouse fixture to snapshot and restore all global state variables in chat_server.
    Otherwise, tests will pass alone but poison the suite.
    """
    # Snapshot
    orig_sessions = dict(chat_server.SESSIONS)
    orig_active_session_id = chat_server.ACTIVE_SESSION_ID
    orig_conversation = chat_server.CONVERSATION
    orig_runtime_state = copy.deepcopy(chat_server.RUNTIME_STATE) if chat_server.RUNTIME_STATE else {}
    orig_dual_gate_events = list(chat_server.DUAL_GATE_EVENTS) if chat_server.DUAL_GATE_EVENTS else []
    orig_last_conversation_snapshot = chat_server.LAST_CONVERSATION_SNAPSHOT
    orig_latest_transcript_path = chat_server.LATEST_TRANSCRIPT_PATH
    orig_latest_jsonl_path = chat_server.LATEST_JSONL_PATH
    
    orig_bridge_cache_params = chat_server.BRIDGE_CTX.cache_params
    orig_bridge_cache_position = chat_server.BRIDGE_CTX.cache_position
    
    orig_args_user_label = getattr(chat_server.ARGS, 'user_label', None)
    orig_args_model_label = getattr(chat_server.ARGS, 'model_label', None)
    orig_args_instance_id = getattr(chat_server.ARGS, 'instance_id', None)
    orig_args_qdrant_collection = getattr(chat_server.ARGS, 'qdrant_collection', None)
    orig_args_no_shared_memory = getattr(chat_server.ARGS, 'no_shared_memory', None)
    
    orig_qdrant_gate_sink = chat_server.QDRANT_GATE_SINK
    orig_qdrant_gate_sink_error = chat_server.QDRANT_GATE_SINK_ERROR
    orig_qdrant_last_retry_ts = chat_server.QDRANT_LAST_RETRY_TS

    # Clear state for the current test
    chat_server.SESSIONS.clear()
    chat_server.ACTIVE_SESSION_ID = None
    chat_server.CONVERSATION = []
    chat_server.RUNTIME_STATE = {}
    chat_server.DUAL_GATE_EVENTS = []
    
    if chat_server.ARGS is None:
        import argparse
        chat_server.ARGS = argparse.Namespace(
            user_label=None, model_label=None, instance_id=None,
            qdrant_collection=None, no_shared_memory=None
        )
    
    yield

    # Restore
    chat_server.SESSIONS.clear()
    chat_server.SESSIONS.update(orig_sessions)
    chat_server.ACTIVE_SESSION_ID = orig_active_session_id
    chat_server.CONVERSATION = orig_conversation
    chat_server.RUNTIME_STATE = orig_runtime_state
    chat_server.DUAL_GATE_EVENTS = orig_dual_gate_events
    chat_server.LAST_CONVERSATION_SNAPSHOT = orig_last_conversation_snapshot
    chat_server.LATEST_TRANSCRIPT_PATH = orig_latest_transcript_path
    chat_server.LATEST_JSONL_PATH = orig_latest_jsonl_path
    
    chat_server.BRIDGE_CTX.cache_params = orig_bridge_cache_params
    chat_server.BRIDGE_CTX.cache_position = orig_bridge_cache_position
    
    if chat_server.ARGS is not None:
        chat_server.ARGS.user_label = orig_args_user_label
        chat_server.ARGS.model_label = orig_args_model_label
        chat_server.ARGS.instance_id = orig_args_instance_id
        chat_server.ARGS.qdrant_collection = orig_args_qdrant_collection
        chat_server.ARGS.no_shared_memory = orig_args_no_shared_memory
    
    chat_server.QDRANT_GATE_SINK = orig_qdrant_gate_sink
    chat_server.QDRANT_GATE_SINK_ERROR = orig_qdrant_gate_sink_error
    chat_server.QDRANT_LAST_RETRY_TS = orig_qdrant_last_retry_ts


@pytest.fixture
def session_a(tmp_path):
    chat_server.LATEST_TRANSCRIPT_PATH = tmp_path / "chat.md"
    chat_server.LATEST_JSONL_PATH = tmp_path / "turns.jsonl"
    body = {
        "session_id": "session_A",
        "user_label": "Alice",
        "instance_id": "alice_private",
        "no_shared_memory": True,
    }
    return get_or_create_chat_session(body=body, path="")


@pytest.fixture
def session_b(tmp_path):
    chat_server.LATEST_TRANSCRIPT_PATH = tmp_path / "chat.md"
    chat_server.LATEST_JSONL_PATH = tmp_path / "turns.jsonl"
    body = {
        "session_id": "session_B",
        "user_label": "Bob",
        "instance_id": "bob_private",
        "no_shared_memory": True,
    }
    return get_or_create_chat_session(body=body, path="")


def test_session_isolation_user_labels(session_a, session_b):
    switch_to_chat_session(session_a)
    assert chat_server.ARGS.user_label == "Alice"
    
    switch_to_chat_session(session_b)
    assert chat_server.ARGS.user_label == "Bob"
    
    # Check that a session restores its own label
    switch_to_chat_session(session_a)
    assert chat_server.ARGS.user_label == "Alice"


def test_session_isolation_private_collections(session_a, session_b):
    assert session_a.qdrant_collection == "mocop_private_alice_private"
    assert session_b.qdrant_collection == "mocop_private_bob_private"
    assert session_a.no_shared_memory is True
    assert session_b.no_shared_memory is True

    switch_to_chat_session(session_a)
    assert chat_server.ARGS.qdrant_collection == "mocop_private_alice_private"
    assert chat_server.ARGS.no_shared_memory is True
    
    switch_to_chat_session(session_b)
    assert chat_server.ARGS.qdrant_collection == "mocop_private_bob_private"
    assert chat_server.ARGS.no_shared_memory is True
    
    switch_to_chat_session(session_a)
    assert chat_server.ARGS.qdrant_collection == "mocop_private_alice_private"


def test_session_isolation_transcript_paths(session_a, session_b):
    assert session_a.transcript_path is not None
    assert session_b.transcript_path is not None
    assert session_a.turn_log_path is not None
    assert session_b.turn_log_path is not None
    assert session_a.transcript_path != session_b.transcript_path
    assert session_a.turn_log_path != session_b.turn_log_path
    assert "session-a" in session_a.transcript_path.name
    assert "session-b" in session_b.transcript_path.name

    switch_to_chat_session(session_a)
    assert chat_server.LATEST_TRANSCRIPT_PATH == session_a.transcript_path
    assert chat_server.LATEST_JSONL_PATH == session_a.turn_log_path
    
    switch_to_chat_session(session_b)
    assert chat_server.LATEST_TRANSCRIPT_PATH == session_b.transcript_path
    assert chat_server.LATEST_JSONL_PATH == session_b.turn_log_path
    
    switch_to_chat_session(session_a)
    assert chat_server.LATEST_TRANSCRIPT_PATH == session_a.transcript_path
    assert chat_server.LATEST_JSONL_PATH == session_a.turn_log_path


def test_session_isolation_runtime_counters_and_pending_rows(session_a, session_b):
    switch_to_chat_session(session_a)
    if not isinstance(chat_server.RUNTIME_STATE, dict):
        chat_server.RUNTIME_STATE = {}
    chat_server.RUNTIME_STATE["turns"] = 5
    chat_server.RUNTIME_STATE["qdrant_pending_count"] = 2
    chat_server.RUNTIME_STATE["qdrant_sleep_pending_count"] = 1
    chat_server.RUNTIME_STATE["qdrant_retry_pending_count"] = 0
    save_active_chat_session()
    
    switch_to_chat_session(session_b)
    if not isinstance(chat_server.RUNTIME_STATE, dict):
        chat_server.RUNTIME_STATE = {}
    chat_server.RUNTIME_STATE["turns"] = 10
    chat_server.RUNTIME_STATE["qdrant_pending_count"] = 7
    chat_server.RUNTIME_STATE["qdrant_sleep_pending_count"] = 2
    chat_server.RUNTIME_STATE["qdrant_retry_pending_count"] = 3
    save_active_chat_session()
    
    switch_to_chat_session(session_a)
    assert chat_server.RUNTIME_STATE["turns"] == 5
    assert chat_server.RUNTIME_STATE["qdrant_pending_count"] == 2
    assert chat_server.RUNTIME_STATE["qdrant_sleep_pending_count"] == 1
    assert chat_server.RUNTIME_STATE["qdrant_retry_pending_count"] == 0

    switch_to_chat_session(session_b)
    assert chat_server.RUNTIME_STATE["turns"] == 10
    assert chat_server.RUNTIME_STATE["qdrant_pending_count"] == 7
    assert chat_server.RUNTIME_STATE["qdrant_sleep_pending_count"] == 2
    assert chat_server.RUNTIME_STATE["qdrant_retry_pending_count"] == 3


def test_session_isolation_gate_events(session_a, session_b):
    switch_to_chat_session(session_a)
    if not isinstance(chat_server.DUAL_GATE_EVENTS, list):
        chat_server.DUAL_GATE_EVENTS = []
    chat_server.DUAL_GATE_EVENTS.append("Event A1")
    save_active_chat_session()
    
    switch_to_chat_session(session_b)
    if not isinstance(chat_server.DUAL_GATE_EVENTS, list):
        chat_server.DUAL_GATE_EVENTS = []
    chat_server.DUAL_GATE_EVENTS.append("Event B1")
    chat_server.DUAL_GATE_EVENTS.append("Event B2")
    save_active_chat_session()
    
    switch_to_chat_session(session_a)
    assert chat_server.DUAL_GATE_EVENTS == ["Event A1"]
    
    switch_to_chat_session(session_b)
    assert chat_server.DUAL_GATE_EVENTS == ["Event B1", "Event B2"]


def test_session_isolation_conversation_lists_and_qdrant_sink_reset(session_a, session_b):
    sentinel_sink = object()

    switch_to_chat_session(session_a)
    chat_server.CONVERSATION.append({"role": "user", "content": "A-only"})
    chat_server.QDRANT_GATE_SINK = sentinel_sink
    chat_server.QDRANT_GATE_SINK_ERROR = "stale-error"
    chat_server.QDRANT_LAST_RETRY_TS = 123.0
    save_active_chat_session()

    switch_to_chat_session(session_b)
    assert chat_server.CONVERSATION == []
    assert chat_server.QDRANT_GATE_SINK is None
    assert chat_server.QDRANT_GATE_SINK_ERROR is None
    assert chat_server.QDRANT_LAST_RETRY_TS == 0.0
    chat_server.CONVERSATION.append({"role": "user", "content": "B-only"})
    save_active_chat_session()

    switch_to_chat_session(session_a)
    assert chat_server.CONVERSATION == [{"role": "user", "content": "A-only"}]

    switch_to_chat_session(session_b)
    assert chat_server.CONVERSATION == [{"role": "user", "content": "B-only"}]


def test_session_isolation_mamba_cache_state(session_a, session_b):
    cache_a = object()
    pos_a = object()
    cache_b = object()
    pos_b = object()
    
    switch_to_chat_session(session_a)
    chat_server.BRIDGE_CTX.cache_params = cache_a
    chat_server.BRIDGE_CTX.cache_position = pos_a
    save_active_chat_session()
    
    switch_to_chat_session(session_b)
    chat_server.BRIDGE_CTX.cache_params = cache_b
    chat_server.BRIDGE_CTX.cache_position = pos_b
    save_active_chat_session()
    
    switch_to_chat_session(session_a)
    assert chat_server.BRIDGE_CTX.cache_params is cache_a
    assert chat_server.BRIDGE_CTX.cache_position is pos_a
    
    switch_to_chat_session(session_b)
    assert chat_server.BRIDGE_CTX.cache_params is cache_b
    assert chat_server.BRIDGE_CTX.cache_position is pos_b
