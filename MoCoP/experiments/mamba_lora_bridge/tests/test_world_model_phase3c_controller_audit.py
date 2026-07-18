from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


SPIKES = Path(__file__).resolve().parents[1] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

import run_world_model_phase3c_controller_audit as audit  # noqa: E402


def test_frozen_source_custody_and_registered_cardinalities():
    custody = audit.verify_frozen_sources()
    assert custody["pass"] is True
    assert len(custody["records"]) == 7
    assert all(record["match"] for record in custody["records"])
    assert len(audit.STATE_CORNERS) == 32
    assert len(audit.STATE_GRID_3) == 243
    assert len(audit.boundary_pairs()) == 85
    assert len(audit.named_scenarios()) == 9


def test_candidate_quantization_is_exact_half_up_and_suppresses_canary_code():
    assert audit.quantize_half_up(0.5 - 7.5e-6) == 0.5
    assert audit.quantize_half_up(0.5 + 7.5e-6) == 0.5
    assert audit.quantize_half_up(0.5 + 0.5 / 256.0) == 0.5 + 1.0 / 256.0
    with pytest.raises(ValueError):
        audit.quantize_half_up(-0.1)


@pytest.mark.parametrize(
    ("state", "q"),
    [
        (audit.baseline_state(), audit.controller.AppraisalVector()),
        (
            (0.2, 0.4, 0.6, 0.8, 0.3),
            audit.controller.AppraisalVector(
                predicted_harm=0.7,
                prediction_error=0.2,
                controllability=0.3,
                goal_progress=-0.4,
                norm_violation=0.5,
                affiliation_delta=-0.6,
            ),
        ),
        (
            (1.0, 1.0, 1.0, 0.0, 1.0),
            audit.named_scenarios()["extreme_unresolved"],
        ),
    ],
)
def test_independent_transition_reconciles_with_frozen_kernel(state, q):
    _, expected = audit.independent_transition(state, q)
    actual = audit.transition(state, q)
    assert audit.max_abs_delta(actual, expected) <= 1e-12


def test_event_metamorphics_are_exact_and_retained_positive_goal_fails():
    result, failures = audit.audit_event_metamorphics()
    assert result["gate"] == "FAIL"
    assert any("goal_progress retained" in reason for reason in failures)
    assert result["threat_clear_audit_distinct"] is True
    assert len(result["rows"]) == 10
    for row in result["rows"]:
        assert float(row["split_merge_max_abs_delta"]) == 0.0
        assert float(row["reversal_max_abs_delta"]) == 0.0
        assert row["undeclared_changed_fields"] == []


def test_duplicate_replay_probes_refuse_before_the_owner_hold():
    result = audit.audit_replay_boundary()
    assert result["gate"] == "HELD"
    assert result["probes"]["duplicate_event_id"]["refused"] is True
    assert result["probes"]["duplicate_position"]["refused"] is True


def test_dead_input_and_adjacent_jump_numeric_oracles():
    baseline = audit.baseline_state()
    for q in (
        audit.controller.AppraisalVector(predicted_harm=0.25),
        audit.controller.AppraisalVector(prediction_error=1.0),
        audit.controller.AppraisalVector(
            goal_progress=1.0, controllability=0.75
        ),
    ):
        assert audit.simulate(q, 8)[-1] == baseline

    left = audit.simulate(
        audit.controller.AppraisalVector(predicted_harm=189 / 256), 256
    )[-1]
    right = audit.simulate(
        audit.controller.AppraisalVector(predicted_harm=190 / 256), 256
    )[-1]
    assert audit.max_abs_delta(left, right) > 0.97


def test_phase_cluster_and_saturation_oracles():
    gain = audit.controller.AppraisalVector(affiliation_delta=0.5)
    trajectory = audit.simulate(gain, 7)
    assert trajectory[6][0] < 1.0
    assert trajectory[7][0] == 1.0

    states = [(0.0, 0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 0.0, 1.0)]
    clusters = audit.complete_link_clusters(states, ("a", "b"))
    assert len(clusters) == 2
    assert sorted(cluster["members"] for cluster in clusters) == [["a"], ["b"]]


def test_recovery_and_accumulation_targeted_oracles():
    extreme = audit.named_scenarios()["extreme_unresolved"]
    endpoint = audit.simulate(extreme, 32)[-1]
    assert endpoint == (0.0, 0.0, 1.0, 0.0, 1.0)
    recovered = audit.simulate(audit.controller.AppraisalVector(), 25, endpoint)[-1]
    assert recovered[2] <= 1e-6
    assert recovered[3] >= 0.99
    assert recovered[4] <= 0.01

    accumulation, failures = audit.audit_accumulation()
    assert failures == []
    assert accumulation["gate"] == "PASS"
    terminal = [float(value) for value in accumulation["unresolved"][-1]]
    assert terminal[0] < 0.75
    assert terminal[1] < 0.75


def test_matched_identity_features_are_exact_and_canary_is_valid():
    for ref_kind in ("person", "topic", "episode"):
        left = audit.leakage_features(7, 0, ref_kind)
        right = audit.leakage_features(7, 15, ref_kind)
        assert left == right

    representatives = (0, 320, 416)
    raw = audit._canary_samples(
        "person", filtered=False, template_indices=representatives
    )
    filtered = audit._canary_samples(
        "person", filtered=True, template_indices=representatives
    )
    raw_scores = audit.evaluate_classifiers(raw["train"]["q"], raw["test"]["q"])
    filtered_scores = audit.evaluate_classifiers(
        filtered["train"]["q"], filtered["test"]["q"]
    )
    assert max(map(float, raw_scores.values())) >= 0.90
    assert max(map(float, filtered_scores.values())) <= 0.0825


def test_balanced_accuracy_and_gate_precedence():
    truth = [label for label in range(16)]
    assert audit.balanced_accuracy(truth, [0] * 16) == 0.0625
    assert audit.balanced_accuracy(truth, truth) == 1.0
    assert (
        audit.overall_disposition(
            {"a": {"status": "PASS"}, "b": {"status": "HELD"}}
        )
        == "HOLD"
    )
    assert (
        audit.overall_disposition(
            {"a": {"status": "FAIL"}, "b": {"status": "HELD"}}
        )
        == "FAIL"
    )


def test_stream_summary_counts_all_failures_and_keeps_lexical_first_16():
    summary = audit.StreamSummary()
    for index in reversed(range(20)):
        summary.fail("reason", {"id": f"{index:02d}"})
    record = summary.record()
    assert record["failure_counts"] == {"reason": 20}
    assert [item["id"] for item in record["failure_witnesses"]["reason"]] == [
        f"{index:02d}" for index in range(16)
    ]


def test_canonical_report_publication_is_no_overwrite(tmp_path):
    probes = {name: {} for name in audit.PROBE_NAMES}
    gates = {}
    for gate_name, probe_name in audit.PROBE_GATE_MAP.items():
        status = "HELD" if gate_name == "REPLAY_AUTHORITY" else "PASS"
        reasons = ["owner hold"] if status == "HELD" else []
        probes[probe_name] = {"gate": status, "reasons": reasons}
        gates[gate_name] = {"status": status, "reasons": reasons}
    for gate_name in ("RELIEF_SEMANTICS", "NUMERIC_RATE_POLICY"):
        gates[gate_name] = {"status": "HELD", "reasons": ["owner hold"]}
    unsigned = {
        "schema_version": "world-model-phase3c-controller-audit-report-v1",
        "protocol_id": audit.PROTOCOL_ID,
        "preregistration": {"git_blob": audit.FROZEN_PREREG_BLOB},
        "runner": {},
        "source_custody": audit.verify_frozen_sources(),
        "platform": {},
        "constants": {},
        "probes": probes,
        "gates": gates,
        "overall_disposition": "HOLD",
    }
    report = dict(unsigned)
    report["report_sha256"] = audit.sha256_hex(audit.canonical_bytes(unsigned))
    invalid = dict(report)
    invalid["report_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="self-digest"):
        audit.publish_bundle(invalid, tmp_path / "invalid")
    fabricated = json.loads(audit.canonical_bytes(report))
    fabricated["gates"]["RELIEF_SEMANTICS"] = {
        "status": "PASS",
        "reasons": [],
    }
    unsigned_fabricated = dict(fabricated)
    del unsigned_fabricated["report_sha256"]
    fabricated["report_sha256"] = audit.sha256_hex(
        audit.canonical_bytes(unsigned_fabricated)
    )
    with pytest.raises(ValueError, match="RELIEF_SEMANTICS"):
        audit.publish_bundle(fabricated, tmp_path / "fabricated")
    destination = tmp_path / "bundle"
    assert audit.publish_bundle(report, destination) == destination
    report_bytes = (destination / "report.json").read_bytes()
    assert report_bytes == audit.canonical_bytes(report)
    assert json.loads(report_bytes) == report
    sidecar = (destination / "report.json.sha256").read_text("ascii")
    assert sidecar == f"{hashlib.sha256(report_bytes).hexdigest()}  report.json\n"
    with pytest.raises(FileExistsError):
        audit.publish_bundle(report, destination)
