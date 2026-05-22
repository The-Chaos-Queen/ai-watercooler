from argparse import Namespace
from types import SimpleNamespace
import sys


def test_run_cycle_passes_canonical_sleep_knobs(monkeypatch, tmp_path):
    monkeypatch.setitem(
        sys.modules,
        "numpy",
        SimpleNamespace(asarray=lambda value, dtype=None: value, ndarray=object, float32="float32"),
    )

    import run_sleep_cycle
    import sleep_reconcile
    import sleep_ethics_gate

    calls = []
    entries = [{"content": "a concrete memory entry", "metadata": {}}]

    monkeypatch.setattr(sleep_reconcile, "load_pending", lambda path: entries)
    monkeypatch.setattr(sleep_reconcile, "load_failure_packets", lambda path: [])
    monkeypatch.setattr(sleep_reconcile, "attach_failure_packets", lambda loaded_entries, packets: (loaded_entries, 0))
    monkeypatch.setattr(sleep_reconcile, "load_mamba_state", lambda path: None)
    monkeypatch.setattr(sleep_reconcile, "load_mamba_replay_stack", lambda model_id, device: None)
    monkeypatch.setattr(sleep_reconcile, "rotate_log", lambda path: None)

    def fake_phase1_decay(phase_entries, *positional, **kwargs):
        if positional:
            kwargs["_positional"] = positional
        calls.append(("phase1_decay", kwargs))
        return phase_entries

    def fake_phase1b_expiration_and_relevance(phase_entries, **kwargs):
        calls.append(("phase1b_expiration_and_relevance", kwargs))
        return phase_entries

    def fake_phase2_replay(phase_entries, bootstrap_state, **kwargs):
        calls.append(("phase2_replay", kwargs))
        return phase_entries

    def fake_phase3_classify(phase_entries, **kwargs):
        calls.append(("phase3_classify", kwargs))
        for entry in phase_entries:
            entry["_status"] = sleep_reconcile.KEEP
        return phase_entries

    monkeypatch.setattr(sleep_reconcile, "phase1_decay", fake_phase1_decay)
    monkeypatch.setattr(sleep_reconcile, "phase1b_expiration_and_relevance", fake_phase1b_expiration_and_relevance)
    monkeypatch.setattr(sleep_reconcile, "phase2_replay", fake_phase2_replay)
    monkeypatch.setattr(sleep_reconcile, "phase3_classify", fake_phase3_classify)
    monkeypatch.setattr(
        sleep_reconcile,
        "phase5_flush",
        lambda *args, **kwargs: {
            "classification": {sleep_reconcile.KEEP: 1},
            "same_space_replay_count": 0,
            "entries_failed": 0,
            "entries_written": 1,
        },
    )

    class FakeGate:
        def __init__(self, **kwargs):
            pass

        def pre_sleep(self, gate_entries, bootstrap_state):
            return SimpleNamespace(
                verdict="PASS",
                snapshot_version="pre.json",
                diversity_ratio=1.0,
                to_dict=lambda: {"verdict": "PASS"},
            )

        def post_sleep(self, pre_verdict, recon_snapshot, post_entries, new_disposition):
            return SimpleNamespace(
                verdict="PASS",
                diversity_ratio=1.0,
                to_dict=lambda: {"verdict": "PASS"},
            )

    monkeypatch.setattr(sleep_ethics_gate, "SleepEthicsGate", FakeGate)

    args = Namespace(
        pending_path=str(tmp_path / "pending.jsonl"),
        failure_path=str(tmp_path / "failure.jsonl"),
        mamba_state=str(tmp_path / "state.pt"),
        snapshot_dir=str(tmp_path / "snapshots"),
        snapshot_path=str(tmp_path / "snapshot.json"),
        dry_run=True,
        skip_qdrant=True,
        skip_replay=True,
        no_rotate=True,
        host="localhost",
        port=6333,
        collection="test_collection",
        embedding_model="test-embeddings",
        replay_model_id="test-mamba",
        replay_device="cpu",
        decay_factor=0.77,
        tension_decay=0.66,
        tension_floor_drain=0.03,
        tension_resolve_threshold=0.12,
        tension_budget_ratio=0.25,
        escalation_cycles=7,
        escalation_tension_floor=0.45,
        strength_threshold=0.31,
        coherence_threshold=0.13,
        top_k=11,
    )

    assert run_sleep_cycle.run_cycle(args) == 0

    assert calls == [
        (
            "phase1_decay",
            {
                "decay_factor": 0.77,
                "tension_decay": 0.66,
                "tension_floor_drain": 0.03,
                "tension_resolve_threshold": 0.12,
            },
        ),
        ("phase1b_expiration_and_relevance", {"rules": None}),
        (
            "phase2_replay",
            {
                "top_k": 11,
                "replay_stack": None,
                "tension_budget_ratio": 0.25,
            },
        ),
        (
            "phase3_classify",
            {
                "strength_threshold": 0.31,
                "coherence_threshold": 0.13,
                "escalation_cycles": 7,
                "escalation_tension_floor": 0.45,
            },
        ),
    ]
