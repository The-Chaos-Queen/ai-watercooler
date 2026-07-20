from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

import world_model_phase3a as phase3a


class FakeAdapter:
    def __init__(
        self,
        executor: phase3a.CanonicalArtifact,
        *,
        execute_result: phase3a.ActionResolution | None = None,
        reconcile_result: phase3a.ActionResolution | None = None,
        raise_execute: bool = False,
        raise_reconcile: bool = False,
    ):
        self.executor_artifact_sha256 = executor.sha256
        self.execute_result = execute_result
        self.reconcile_result = reconcile_result
        self.raise_execute = raise_execute
        self.raise_reconcile = raise_reconcile
        self.execute_calls = 0
        self.reconcile_calls = 0
        self.requests: list[phase3a.ExecutionRequest] = []

    def execute(self, request: phase3a.ExecutionRequest) -> phase3a.ActionResolution:
        assert len(request.execution_id) == 64
        assert request.selected_action.artifact_kind == "action"
        assert len(request.commit_record_sha256) == 64
        self.requests.append(request)
        self.execute_calls += 1
        if self.raise_execute:
            raise RuntimeError("executor failed after an unknown boundary")
        if self.execute_result is None:
            raise AssertionError("test adapter has no execute result")
        return self.execute_result

    def reconcile(self, request: phase3a.ExecutionRequest) -> phase3a.ActionResolution:
        assert len(request.execution_id) == 64
        assert request.selected_action.artifact_kind == "action"
        assert len(request.commit_record_sha256) == 64
        self.reconcile_calls += 1
        if self.raise_reconcile:
            raise RuntimeError("executor cannot reconcile")
        if self.reconcile_result is None:
            raise AssertionError("test adapter has no reconcile result")
        return self.reconcile_result


def _artifact(kind: str, artifact_id: str, content=None) -> phase3a.CanonicalArtifact:
    return phase3a.CanonicalArtifact(
        kind,
        artifact_id,
        f"test-{kind}-v1",
        content if content is not None else {"id": artifact_id},
    )


def _ontology() -> phase3a.OutcomeOntology:
    return phase3a.OutcomeOntology(
        "test-outcomes-v1", ("ALERT", "CALM", "OTHER", "UNKNOWN")
    )


def _prediction() -> phase3a.Prediction:
    return phase3a.Prediction(
        "collected",
        (
            phase3a.OutcomeProbability("ALERT", 0.35),
            phase3a.OutcomeProbability("CALM", 0.55),
            phase3a.OutcomeProbability("OTHER", 0.05),
            phase3a.OutcomeProbability("UNKNOWN", 0.05),
        ),
    )


def _evidence(raw_label: str = "CALM") -> phase3a.ExecutionEvidence:
    return phase3a.ExecutionEvidence(
        receipt=_artifact("execution_receipt", f"receipt-{raw_label}"),
        observation=_artifact(
            "observation", f"observation-{raw_label}", {"raw_label": raw_label}
        ),
        outcome_source=_artifact(
            "outcome_source", f"source-{raw_label}", {"sensor": "fixture"}
        ),
        raw_outcome_label=raw_label,
    )


def _executed(raw_label: str = "CALM") -> phase3a.ActionResolution:
    return phase3a.ActionResolution(
        "executed", "authoritative_receipt", _evidence(raw_label)
    )


def _inputs(
    executor: phase3a.CanonicalArtifact,
    adapter: FakeAdapter,
    *,
    step_id: str = "step-0",
) -> dict:
    return {
        "step_id": step_id,
        "state": _artifact("state", f"state-{step_id}", {"tick": step_id}),
        "candidate_actions": (
            _artifact("action", "ACTION-A", {"move": "left"}),
            _artifact("action", "ACTION-B", {"move": "right"}),
        ),
        "selected_action_id": "ACTION-B",
        "estimator": _artifact("estimator", "estimator-v1", {"family": "fixture"}),
        "estimator_config": _artifact(
            "estimator_config", "estimator-config-v1", {"alpha": 0.5}
        ),
        "executor": executor,
        "ontology": _ontology(),
        "prediction": _prediction(),
        "adapter_binding": phase3a.ActionAdapterBinding(executor.sha256, adapter),
    }


def _new_journal(
    tmp_path: Path,
    *,
    steps: tuple[str, ...] = ("step-0",),
    fault_points: frozenset[str] | None = None,
) -> tuple[phase3a.CausalTraceJournal, phase3a.CanonicalArtifact, Path]:
    path = tmp_path / "causal-journal"
    manifest = _artifact(
        "run_manifest", "manifest-v1", {"test": "phase3a", "steps": list(steps)}
    )
    journal = phase3a.CausalTraceJournal.create(
        path,
        journal_id="journal-fixture-v1",
        run_id="run-fixture-v1",
        domain="fixture",
        manifest=manifest,
        expected_step_ids=steps,
        fault_points=fault_points,
    )
    return journal, manifest, path


def _record_paths(path: Path) -> list[Path]:
    return sorted(item for item in path.glob("*.json") if item.is_file())


def test_complete_journal_binds_artifacts_and_scores_in_support(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed("CALM"))

    step = journal.run_step(**_inputs(executor, adapter))
    assert step.status == "complete"
    assert adapter.execute_calls == 1
    snapshot = journal.close_run()

    assert snapshot.run_status == "complete"
    assert [record.record_type for record in snapshot.records] == [
        "run_header",
        "pre_action_commit",
        "execution_handoff",
        "action_receipt",
        "outcome",
        "run_ledger",
    ]
    rows = phase3a.scoring_rows(path, expected_manifest_sha256=manifest.sha256)
    assert len(rows) == 1
    assert rows[0].raw_outcome_label == "CALM"
    assert rows[0].scoring_label == "CALM"
    assert rows[0].support_status == "in_support"


@pytest.mark.parametrize(
    ("raw_label", "support_status", "scoring_label"),
    [
        ("OTHER", "declared_other", "OTHER"),
        ("UNKNOWN", "unknown", "UNKNOWN"),
        ("NEVER_ENUMERATED", "out_of_support", "OTHER"),
    ],
)
def test_open_set_outcomes_are_retained_and_counted(
    tmp_path, raw_label, support_status, scoring_label
):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed(raw_label))
    journal.run_step(**_inputs(executor, adapter))
    snapshot = journal.close_run()

    outcome = snapshot.steps[0].outcome
    assert outcome is not None
    assert outcome.body["raw_outcome_label"] == raw_label
    assert outcome.body["support_status"] == support_status
    assert outcome.body["scoring_label"] == scoring_label
    ledger = snapshot.records[-1].body
    assert ledger["counts"]["outcomes"] == 1
    assert ledger["counts"][support_status] == 1
    assert len(phase3a.scoring_rows(path, expected_manifest_sha256=manifest.sha256)) == 1


def test_other_and_unknown_require_positive_committed_mass():
    ontology = _ontology()
    prediction = phase3a.Prediction(
        "collected",
        (
            phase3a.OutcomeProbability("ALERT", 0.5),
            phase3a.OutcomeProbability("CALM", 0.5),
            phase3a.OutcomeProbability("OTHER", 0.0),
            phase3a.OutcomeProbability("UNKNOWN", 0.0),
        ),
    )
    with pytest.raises(ValueError, match="positive committed mass"):
        prediction.validate_for(ontology)


def test_reserved_ontology_labels_are_literal():
    with pytest.raises(ValueError, match="literal OTHER and UNKNOWN"):
        phase3a.OutcomeOntology(
            "renamed-reserved-v1",
            ("ALERT", "MISC", "UNRESOLVED"),
            other_label="MISC",
            unknown_label="UNRESOLVED",
        )


def test_executor_observes_durable_commit_and_handoff_before_action(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")

    class InspectingAdapter(FakeAdapter):
        def execute(self, request):
            snapshot = phase3a.load_causal_journal(
                path, expected_manifest_sha256=manifest.sha256
            )
            assert [record.record_type for record in snapshot.records] == [
                "run_header",
                "pre_action_commit",
                "execution_handoff",
            ]
            assert snapshot.steps[0].status == "execution_unknown"
            commit = snapshot.steps[0].commit
            assert commit is not None
            assert request.commit_record_sha256 == commit.record_sha256
            assert request.state_sha256 == commit.body["state"]["sha256"]
            return super().execute(request)

    adapter = InspectingAdapter(executor, execute_result=_executed())
    journal.run_step(**_inputs(executor, adapter))
    journal.close_run()
    assert adapter.execute_calls == 1


def test_adapter_object_is_not_touched_before_durable_handoff(tmp_path):
    journal, _manifest, _path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    touches = 0

    class HostileAdapter:
        @property
        def executor_artifact_sha256(self):
            nonlocal touches
            touches += 1
            return executor.sha256

        def execute(self, _request):
            raise AssertionError("mismatched inert binding must refuse before execute")

        def reconcile(self, _request):
            raise AssertionError("mismatched inert binding must refuse before reconcile")

    inputs = _inputs(executor, FakeAdapter(executor, execute_result=_executed()))
    inputs["adapter_binding"] = phase3a.ActionAdapterBinding("f" * 64, HostileAdapter())
    with pytest.raises(ValueError, match="not bound"):
        journal.run_step(**inputs)
    assert touches == 0
    assert [record.record_type for record in journal.snapshot.records] == ["run_header"]
    journal.close_run()


@pytest.mark.parametrize("field", ["step_id", "selected_action_id"])
def test_hostile_identity_objects_refuse_without_callbacks(tmp_path, field):
    journal, _manifest, _path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    calls = 0

    class HostileIdentity:
        def __eq__(self, _other):
            nonlocal calls
            calls += 1
            return True

        def __ne__(self, _other):
            nonlocal calls
            calls += 1
            return False

        def __hash__(self):
            nonlocal calls
            calls += 1
            return 0

    inputs = _inputs(executor, adapter)
    inputs[field] = HostileIdentity()
    with pytest.raises(ValueError, match="non-empty string"):
        journal.run_step(**inputs)
    assert calls == 0
    assert [record.record_type for record in journal.snapshot.records] == ["run_header"]
    journal.close_run()


def test_execution_id_binds_state_actions_estimator_and_prediction(tmp_path):
    executor = _artifact("executor", "executor-v1")
    ids: list[str] = []
    for index, tick in enumerate(("before", "changed")):
        journal, _manifest, _path = _new_journal(tmp_path / str(index))
        adapter = FakeAdapter(executor, execute_result=_executed())
        inputs = _inputs(executor, adapter)
        inputs["state"] = _artifact("state", "state-step-0", {"tick": tick})
        journal.run_step(**inputs)
        journal.close_run()
        ids.append(adapter.requests[0].execution_id)
    assert ids[0] != ids[1]


def test_scorer_reloads_verified_journal_and_cannot_accept_forged_snapshot(tmp_path):
    journal, manifest, path = _new_journal(tmp_path, steps=("step-0", "step-1"))
    executor = _artifact("executor", "executor-v1")
    first = FakeAdapter(executor, execute_result=_executed("CALM"))
    second = FakeAdapter(executor, execute_result=_executed("NOVEL"))
    journal.run_step(**_inputs(executor, first, step_id="step-0"))
    journal.run_step(**_inputs(executor, second, step_id="step-1"))
    snapshot = journal.close_run()
    forged = replace(snapshot, steps=(snapshot.steps[0], snapshot.steps[0]))

    with pytest.raises(TypeError):
        phase3a.scoring_rows(
            forged,  # type: ignore[arg-type]
            expected_manifest_sha256=manifest.sha256,
        )
    rows = phase3a.scoring_rows(path, expected_manifest_sha256=manifest.sha256)
    assert [row.raw_outcome_label for row in rows] == ["CALM", "NOVEL"]
    assert [row.support_status for row in rows] == ["in_support", "out_of_support"]


def test_crash_after_commit_is_provably_not_executed(tmp_path):
    journal, manifest, path = _new_journal(
        tmp_path, fault_points=frozenset({"after_pre_action_commit"})
    )
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    with pytest.raises(phase3a.InjectedJournalCrash):
        journal.run_step(**_inputs(executor, adapter))
    assert adapter.execute_calls == 0
    journal.close_handle()

    recovered = phase3a.CausalTraceJournal.reopen(
        path, expected_manifest_sha256=manifest.sha256
    )
    step = recovered.recover_pending()
    assert step is not None
    assert step.status == "committed_not_executed"
    assert step.resolution is not None
    assert step.resolution.body["reason"] == "handoff_not_published"
    snapshot = recovered.close_run()
    assert snapshot.run_status == "held"
    with pytest.raises(ValueError, match="complete causal journal"):
        phase3a.scoring_rows(path, expected_manifest_sha256=manifest.sha256)


def test_post_handoff_crash_without_reconciliation_is_unknown(tmp_path):
    journal, manifest, path = _new_journal(
        tmp_path, fault_points=frozenset({"after_execution_handoff"})
    )
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    with pytest.raises(phase3a.InjectedJournalCrash):
        journal.run_step(**_inputs(executor, adapter))
    assert adapter.execute_calls == 0
    journal.close_handle()

    recovered = phase3a.CausalTraceJournal.reopen(
        path, expected_manifest_sha256=manifest.sha256
    )
    step = recovered.recover_pending()
    assert step is not None
    assert step.status == "execution_unknown"
    assert step.resolution is not None
    assert step.resolution.body["reason"] == "adapter_unavailable"
    snapshot = recovered.close_run()
    assert snapshot.reason == "execution_unknown"


def test_crash_after_side_effect_reconciles_without_reexecution(tmp_path):
    journal, manifest, path = _new_journal(
        tmp_path, fault_points=frozenset({"after_execute_before_receipt"})
    )
    executor = _artifact("executor", "executor-v1")
    result = _executed("ALERT")
    adapter = FakeAdapter(executor, execute_result=result, reconcile_result=result)
    with pytest.raises(phase3a.InjectedJournalCrash):
        journal.run_step(**_inputs(executor, adapter))
    assert adapter.execute_calls == 1
    journal.close_handle()

    recovered = phase3a.CausalTraceJournal.reopen(
        path, expected_manifest_sha256=manifest.sha256
    )
    step = recovered.recover_pending(
        phase3a.ActionAdapterBinding(executor.sha256, adapter)
    )
    assert step is not None and step.status == "complete"
    assert adapter.execute_calls == 1
    assert adapter.reconcile_calls == 1
    snapshot = recovered.close_run()
    assert snapshot.run_status == "complete"


def test_receipt_contains_enough_evidence_for_local_outcome_recovery(tmp_path):
    journal, manifest, path = _new_journal(
        tmp_path, fault_points=frozenset({"after_action_receipt"})
    )
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed("ALERT"))
    with pytest.raises(phase3a.InjectedJournalCrash):
        journal.run_step(**_inputs(executor, adapter))
    journal.close_handle()

    recovered = phase3a.CausalTraceJournal.reopen(
        path, expected_manifest_sha256=manifest.sha256
    )
    step = recovered.recover_pending()
    assert step is not None and step.status == "complete"
    assert step.outcome is not None
    assert step.outcome.body["raw_outcome_label"] == "ALERT"
    recovered.close_run()


def test_crash_after_outcome_needs_no_executor_reconciliation(tmp_path):
    journal, manifest, path = _new_journal(
        tmp_path, fault_points=frozenset({"after_outcome"})
    )
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed("CALM"))
    with pytest.raises(phase3a.InjectedJournalCrash):
        journal.run_step(**_inputs(executor, adapter))
    journal.close_handle()

    recovered = phase3a.CausalTraceJournal.reopen(
        path, expected_manifest_sha256=manifest.sha256
    )
    assert recovered.recover_pending() is None
    snapshot = recovered.close_run()
    assert snapshot.run_status == "complete"


@pytest.mark.parametrize("boundary", ["before_run_ledger", "after_run_ledger"])
def test_terminal_ledger_crash_boundaries_are_recoverable(tmp_path, boundary):
    journal, manifest, path = _new_journal(
        tmp_path, fault_points=frozenset({boundary})
    )
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    journal.run_step(**_inputs(executor, adapter))
    with pytest.raises(phase3a.InjectedJournalCrash):
        journal.close_run()
    journal.close_handle()

    snapshot = phase3a.load_causal_journal(
        path, expected_manifest_sha256=manifest.sha256
    )
    if boundary == "before_run_ledger":
        assert snapshot.run_status == "open"
        recovered = phase3a.CausalTraceJournal.reopen(
            path, expected_manifest_sha256=manifest.sha256
        )
        assert recovered.close_run().run_status == "complete"
    else:
        assert snapshot.run_status == "complete"


def test_execute_and_reconcile_failure_records_unknown_instead_of_guessing(tmp_path):
    journal, _manifest, _path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, raise_execute=True, raise_reconcile=True)
    step = journal.run_step(**_inputs(executor, adapter))
    assert step.status == "execution_unknown"
    assert step.resolution is not None
    assert step.resolution.body["reason"] == "adapter_failure"
    snapshot = journal.close_run()
    assert snapshot.run_status == "held"


def test_executor_refusal_is_closed_and_denominator_is_not_shrunk(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(
        executor,
        execute_result=phase3a.ActionResolution("not_executed", "executor_refused"),
    )
    step = journal.run_step(**_inputs(executor, adapter))
    assert step.status == "committed_not_executed"
    snapshot = journal.close_run()
    ledger = snapshot.records[-1].body
    assert ledger["counts"]["planned"] == 1
    assert ledger["counts"]["committed"] == 1
    assert ledger["counts"]["not_executed"] == 1
    assert ledger["counts"]["outcomes"] == 0
    with pytest.raises(ValueError, match="complete causal journal"):
        phase3a.scoring_rows(path, expected_manifest_sha256=manifest.sha256)


def test_plan_order_and_selected_action_membership_are_enforced_before_commit(tmp_path):
    journal, _manifest, _path = _new_journal(tmp_path, steps=("step-0", "step-1"))
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    bad = _inputs(executor, adapter, step_id="step-1")
    with pytest.raises(ValueError, match="next member"):
        journal.run_step(**bad)
    bad = _inputs(executor, adapter)
    bad["selected_action_id"] = "ACTION-C"
    with pytest.raises(ValueError, match="not in candidate_actions"):
        journal.run_step(**bad)
    assert len(journal.snapshot.records) == 1
    journal.close_run()


def test_terminal_resolutions_do_not_block_later_planned_steps(tmp_path):
    journal, _manifest, _path = _new_journal(tmp_path, steps=("step-0", "step-1"))
    executor = _artifact("executor", "executor-v1")
    refused = FakeAdapter(
        executor,
        execute_result=phase3a.ActionResolution("not_executed", "executor_refused"),
    )
    journal.run_step(**_inputs(executor, refused, step_id="step-0"))
    executed = FakeAdapter(executor, execute_result=_executed())
    journal.run_step(**_inputs(executor, executed, step_id="step-1"))
    snapshot = journal.close_run()
    assert [step.status for step in snapshot.steps] == [
        "committed_not_executed",
        "complete",
    ]
    assert snapshot.run_status == "held"


def test_second_writer_is_refused(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    with pytest.raises(phase3a.CausalJournalError, match="active writer"):
        phase3a.CausalTraceJournal.reopen(
            path, expected_manifest_sha256=manifest.sha256
        )
    journal.close_run()


def test_publication_fault_before_handoff_never_calls_executor(tmp_path, monkeypatch):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    real_link = phase3a.os.link
    calls = 0

    def fail_second_link(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected handoff publication fault")
        return real_link(source, destination)

    monkeypatch.setattr(phase3a.os, "link", fail_second_link)
    with pytest.raises(OSError, match="injected handoff"):
        journal.run_step(**_inputs(executor, adapter))
    assert adapter.execute_calls == 0
    journal.close_handle()
    snapshot = phase3a.load_causal_journal(
        path, expected_manifest_sha256=manifest.sha256
    )
    assert snapshot.steps[0].status == "committed_not_executed"
    assert [record.record_type for record in snapshot.records] == [
        "run_header",
        "pre_action_commit",
    ]


def test_record_fsync_fault_before_commit_never_calls_executor(tmp_path, monkeypatch):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())

    def fail_fsync(_fd):
        raise OSError("injected fsync fault")

    monkeypatch.setattr(phase3a.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="injected fsync"):
        journal.run_step(**_inputs(executor, adapter))
    assert adapter.execute_calls == 0
    journal.close_handle()
    snapshot = phase3a.load_causal_journal(
        path, expected_manifest_sha256=manifest.sha256
    )
    assert [record.record_type for record in snapshot.records] == ["run_header"]


def test_record_mutation_and_replay_are_rejected(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    journal.run_step(**_inputs(executor, adapter))
    journal.close_run()

    records = _record_paths(path)
    commit_path = records[1]
    data = bytearray(commit_path.read_bytes())
    data[data.index(b"state-step-0")] = ord("S")
    commit_path.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="not canonical|record_sha256"):
        phase3a.load_causal_journal(
            path, expected_manifest_sha256=manifest.sha256, require_closed=True
        )


def test_recomputed_outer_hash_cannot_hide_artifact_mutation(tmp_path):
    journal, manifest, path = _new_journal(
        tmp_path, fault_points=frozenset({"after_pre_action_commit"})
    )
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    with pytest.raises(phase3a.InjectedJournalCrash):
        journal.run_step(**_inputs(executor, adapter))
    journal.close_handle()
    commit_path = _record_paths(path)[1]
    payload = json.loads(commit_path.read_text(encoding="utf-8"))
    payload["body"]["state"]["content"]["tick"] = "forged-after-outcome"
    base = {key: value for key, value in payload.items() if key != "record_sha256"}
    payload["record_sha256"] = phase3a.canonical_sha256(base)
    replacement = commit_path.with_name(
        f"{payload['sequence']:08d}-{payload['record_sha256']}.json"
    )
    commit_path.unlink()
    replacement.write_bytes(phase3a.canonical_json_bytes(payload) + b"\n")
    with pytest.raises(ValueError, match="byte_length|sha256"):
        phase3a.load_causal_journal(
            path, expected_manifest_sha256=manifest.sha256, require_closed=True
        )


def test_semantically_false_ledger_is_rejected_even_when_rehashed(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    journal.run_step(**_inputs(executor, adapter))
    journal.close_run()
    ledger_path = _record_paths(path)[-1]
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    payload["body"]["counts"]["outcomes"] = 0
    base = {key: value for key, value in payload.items() if key != "record_sha256"}
    payload["record_sha256"] = phase3a.canonical_sha256(base)
    replacement = ledger_path.with_name(
        f"{payload['sequence']:08d}-{payload['record_sha256']}.json"
    )
    ledger_path.unlink()
    replacement.write_bytes(phase3a.canonical_json_bytes(payload) + b"\n")
    with pytest.raises(ValueError, match="counts do not match"):
        phase3a.load_causal_journal(
            path, expected_manifest_sha256=manifest.sha256, require_closed=True
        )


def test_tail_deletion_cannot_pass_closed_verification(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    journal.run_step(**_inputs(executor, adapter))
    journal.close_run()
    _record_paths(path)[-1].unlink()
    with pytest.raises(ValueError, match="no terminal run_ledger"):
        phase3a.load_causal_journal(
            path, expected_manifest_sha256=manifest.sha256, require_closed=True
        )


def test_torn_record_and_unknown_directory_entry_are_rejected(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    journal.close_handle()
    header = _record_paths(path)[0]
    original = header.read_bytes()
    header.write_bytes(original[:-1])
    with pytest.raises(ValueError, match="torn"):
        phase3a.load_causal_journal(path, expected_manifest_sha256=manifest.sha256)
    header.write_bytes(original)
    (path / "unexpected.txt").write_text("not evidence", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected causal journal entry"):
        phase3a.load_causal_journal(path, expected_manifest_sha256=manifest.sha256)


def test_replayed_record_is_rejected_by_sequence_and_chain(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed())
    journal.run_step(**_inputs(executor, adapter))
    journal.close_run()
    commit = _record_paths(path)[1]
    replay = path / f"{99:08d}-{'f' * 64}.json"
    shutil.copyfile(commit, replay)
    with pytest.raises(ValueError, match="sequence gap"):
        phase3a.load_causal_journal(
            path, expected_manifest_sha256=manifest.sha256, require_closed=True
        )


def test_manifest_hash_is_external_anchor(tmp_path):
    journal, _manifest, path = _new_journal(tmp_path)
    journal.close_handle()
    with pytest.raises(ValueError, match="manifest hash mismatch"):
        phase3a.load_causal_journal(path, expected_manifest_sha256="f" * 64)


def test_uncollected_prediction_retains_outcome_but_refuses_scoring(tmp_path):
    journal, manifest, path = _new_journal(tmp_path)
    executor = _artifact("executor", "executor-v1")
    adapter = FakeAdapter(executor, execute_result=_executed("CALM"))
    inputs = _inputs(executor, adapter)
    inputs["prediction"] = phase3a.Prediction("not_collected", reason="observer_disabled")
    journal.run_step(**inputs)
    snapshot = journal.close_run()
    assert snapshot.run_status == "complete"
    assert snapshot.steps[0].outcome is not None
    with pytest.raises(ValueError, match="uncollected prediction"):
        phase3a.scoring_rows(path, expected_manifest_sha256=manifest.sha256)


def test_frozen_phase2_sources_remain_byte_identical():
    root = Path(__file__).resolve().parents[1]
    expected = {
        "world_model_trace.py": "c87d94bac4df8b211d9a067e8c68ba34aabcb60f8d190a873e832d36dbdeed5d",
        "world_model_capture.py": "e5af1edcbb15307a79e450cb08a29e4fff2e662e9e5268d0844f3866ca3b5c65",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
