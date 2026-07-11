from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

from world_model_capture import DurableTraceJournal


ROOT = Path(__file__).resolve().parents[1]
COLLECTOR_PATH = ROOT / "spikes" / "collect_world_model_phase2.py"
spec = importlib.util.spec_from_file_location("collect_world_model_phase2", COLLECTOR_PATH)
phase2 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = phase2
spec.loader.exec_module(phase2)


def _ls20_payload(
    *, row: int = 20, column: int = 20, level: int = 0, state: str = "NOT_FINISHED"
) -> dict:
    frame = np.full((64, 64), 4, dtype=np.int8)
    for delta_row, delta_column in ((-5, 0), (0, -5), (0, 5)):
        frame[row + delta_row : row + delta_row + 2, column + delta_column : column + delta_column + 5] = 3
    frame[row : row + 2, column : column + 5] = 12
    return {
        "game_id": "ls20-test",
        "guid": "guid",
        "state": state,
        "levels_completed": level,
        "win_levels": 0,
        "full_reset": False,
        "available_actions": [1, 2, 3, 4],
        "previous_action": {"id": "RESET", "data": {}, "reasoning": None},
        "frames": [phase2._frame_payload(frame)],
    }


def test_ls20_state_key_uses_only_pre_action_movement_mask():
    payload = _ls20_payload()
    assert phase2.ls20_state_ref(payload).endswith("mask=1011")


def test_ls20_animation_frames_are_retained_but_state_uses_final_frame():
    payload = _ls20_payload()
    final_frame = payload["frames"][0]
    animation_frame = phase2._frame_payload(np.full((64, 64), 4, dtype=np.int8))
    payload["frames"] = [animation_frame, final_frame]
    phase2.validate_ls20_observation_payload(payload)
    assert phase2.ls20_state_ref(payload).endswith("mask=1011")


def test_ls20_outcome_projection_distinguishes_move_block_and_level():
    pre = _ls20_payload()
    blocked = _ls20_payload()
    moved = _ls20_payload(row=15)
    advanced = _ls20_payload(level=1)
    winning = _ls20_payload(level=1, state="WIN")
    assert phase2.classify_ls20_outcome(pre, blocked) == "avatar_blocked"
    assert phase2.classify_ls20_outcome(pre, moved) == "avatar_moved"
    assert phase2.classify_ls20_outcome(pre, advanced) == "level_advanced"
    assert phase2.classify_ls20_outcome(pre, winning) == "terminal_win"


def test_one_pixel_changes_canonical_ls20_source_hash():
    first = _ls20_payload()
    second = _ls20_payload()
    second["frames"][0]["values"][0][0] = 3
    assert phase2.canonical_sha256(first) != phase2.canonical_sha256(second)


def test_real_tool_probe_reports_success_and_not_found(tmp_path):
    (tmp_path / "present.txt").write_text("present\n", encoding="utf-8")
    success, success_payload = phase2.run_tool_action(
        python_executable=Path(sys.executable),
        sandbox=tmp_path,
        action=phase2.canonical_action("read_text", {"path": "present.txt"}),
        timeout_seconds=5.0,
    )
    missing, missing_payload = phase2.run_tool_action(
        python_executable=Path(sys.executable),
        sandbox=tmp_path,
        action=phase2.canonical_action("read_text", {"path": "missing.txt"}),
        timeout_seconds=5.0,
    )
    assert success == "success"
    assert success_payload["returncode"] == 0
    assert missing == "not_found"
    assert missing_payload["returncode"] == 2


def test_run_manifest_freezes_disjoint_run_and_source_groups():
    specs = phase2.build_run_specs(
        train_ls20_runs=2,
        eval_ls20_runs=1,
        train_tool_runs=2,
        eval_tool_runs=1,
        ls20_steps=4,
        tool_steps=4,
    )
    assert len({spec["run_id"] for spec in specs}) == len(specs)
    assert len({spec["source_group_id"] for spec in specs}) == len(specs)
    assert {spec["split"] for spec in specs} == {"train", "eval"}
    assert all(len(spec["action_sequence"]) == spec["planned_steps"] for spec in specs)
    train_seeds = {
        spec["environment_seed"]
        for spec in specs
        if spec["domain"] == "ls20" and spec["split"] == "train"
    }
    eval_seeds = {
        spec["environment_seed"]
        for spec in specs
        if spec["domain"] == "ls20" and spec["split"] == "eval"
    }
    assert train_seeds.isdisjoint(eval_seeds)


def _fake_collect_ls20_run(
    *, staging, spec, manifest_sha256, observer, environments_dir, recordings_dir
):
    del environments_dir, recordings_dir
    observation = _ls20_payload()
    observation["game_id"] = "ls20-fake"
    observation["previous_action"] = {"id": "RESET", "data": {}, "reasoning": None}
    journal = DurableTraceJournal(
        phase2._journal_path(staging, spec), manifest_sha256=manifest_sha256
    )
    for step_index, action in enumerate(spec["action_sequence"]):
        pre = json.loads(json.dumps(observation))
        pre_payload = {
            "collector": phase2.COLLECTOR_VERSION,
            "source_group_id": spec["source_group_id"],
            "environment_seed": spec["environment_seed"],
            "observation": pre,
        }
        pending = journal.begin(
            observer=observer,
            run_id=spec["run_id"],
            domain="ls20",
            episode_id=spec["episode_id"],
            step_index=step_index,
            state_ref=phase2.ls20_state_ref(pre),
            action=action,
            state_source_kind="environment",
            state_source_id=f"{spec['source_group_id']}:pre:{step_index}",
            state_source_payload=pre_payload,
        )
        post = json.loads(json.dumps(pre))
        post["previous_action"] = {
            "id": json.loads(action)["name"],
            "data": {},
            "reasoning": None,
        }
        post_payload = {
            "collector": phase2.COLLECTOR_VERSION,
            "source_group_id": spec["source_group_id"],
            "environment_seed": spec["environment_seed"],
            "observation": post,
        }
        journal.finish(
            pending,
            observation="avatar_blocked",
            outcome_source_kind="environment",
            outcome_source_id=f"{spec['source_group_id']}:post:{step_index}",
            outcome_source_payload=post_payload,
        )
        observation = post
    return journal.path


def _phase2_test_args(output: Path):
    return phase2.build_arg_parser().parse_args(
        [
            "--output",
            str(output),
            "--arc-environments-dir",
            str(output.parent / "fake-environments"),
            "--arc-recordings-dir",
            str(output.parent / "fake-recordings"),
            "--train-ls20-runs",
            "4",
            "--eval-ls20-runs",
            "3",
            "--train-tool-runs",
            "4",
            "--eval-tool-runs",
            "3",
            "--ls20-steps",
            "16",
            "--tool-steps",
            "4",
        ]
    )


def test_complete_bundle_verifies_refuses_overwrite_and_rejects_semantic_tamper(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        phase2,
        "MIN_ACTUAL_TRANSITIONS",
        {
            "train": {"ls20": 64, "tool": 16},
            "eval": {"ls20": 48, "tool": 12},
        },
    )
    monkeypatch.setattr(
        phase2,
        "MIN_TRANSITIONS_PER_EVAL_RUN",
        {"ls20": 16, "tool": 4},
    )
    monkeypatch.setattr(
        phase2,
        "MIN_TRAIN_ACTION_COUNT",
        {"ls20": 1, "tool": 1},
    )
    monkeypatch.setattr(
        phase2,
        "MIN_TRAIN_STATE_ACTION_CELLS",
        {"ls20": 4, "tool": 2},
    )
    monkeypatch.setattr(
        phase2,
        "_resolve_ls20_provenance",
        lambda *_: {
            "arc_agi_version": phase2.EXPECTED_ARC_AGI_VERSION,
            "arc_agi_distribution_sha256": "c" * 64,
            "arcengine_version": phase2.EXPECTED_ARCENGINE_VERSION,
            "arcengine_distribution_sha256": "d" * 64,
            "game_id": "ls20-fake",
            "game_file_sha256": "a" * 64,
            "metadata_sha256": "b" * 64,
            "operation_mode": "OFFLINE",
            "official_toolkit_url": "https://github.com/arcprize/ARC-AGI",
        },
    )
    monkeypatch.setattr(phase2, "collect_ls20_run", _fake_collect_ls20_run)
    output = tmp_path / "bundle"
    args = _phase2_test_args(output)
    assert phase2.collect_bundle(args) == output.resolve()
    verified = phase2.verify_bundle(output)
    assert verified["ok"] is True
    with pytest.raises(FileExistsError):
        phase2.collect_bundle(args)

    tampered = tmp_path / "tampered"
    shutil.copytree(output, tampered)
    report_path = tampered / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["boundary"]["authorized"] = "online_action_selection"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_hash = phase2.file_sha256(report_path)
    sums_path = tampered / "SHA256SUMS.json"
    sums = json.loads(sums_path.read_text(encoding="utf-8"))
    sums["report.json"] = report_hash
    sums_path.write_text(
        json.dumps(sums, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (tampered / "report.json.sha256").write_text(
        f"{report_hash}  report.json\n", encoding="ascii"
    )
    with pytest.raises(ValueError, match="integration boundary"):
        phase2.verify_bundle(tampered)


def test_collection_argument_validation_rejects_false_go_inputs(tmp_path):
    args = _phase2_test_args(tmp_path / "bundle")
    args.alpha = -1.0
    with pytest.raises(ValueError, match="strictly positive"):
        phase2.validate_collection_args(args)
    args = _phase2_test_args(tmp_path / "bundle-2")
    args.eval_ls20_runs = 1
    with pytest.raises(ValueError, match="integer >= 3"):
        phase2.validate_collection_args(args)


def _decision_fixture(delta: float = 0.1) -> tuple[dict, dict]:
    domains = ("ls20", "tool")
    score = {
        "domains": {
            domain: {
                "n_eval": 16,
                "delta_marginal_minus_tabular": {
                    "categorical_nll": delta,
                    "multiclass_brier": delta,
                },
                "delta_null_minus_tabular": {
                    "categorical_nll": delta,
                    "multiclass_brier": delta,
                },
            }
            for domain in domains
        },
        "runs": {},
        "training_support": {
            domain: {
                "n_train": 40,
                "action_counts": {"a": 20, "b": 20},
                "n_state_action_cells": 4,
            }
            for domain in domains
        },
    }
    for domain in domains:
        for run_index in range(4):
            score["runs"][f"{domain}-{run_index}"] = {
                "domain": domain,
                "n_eval": 4,
                "delta_marginal_minus_tabular": {
                    "categorical_nll": delta,
                    "multiclass_brier": delta,
                },
                "delta_null_minus_tabular": {
                    "categorical_nll": delta,
                    "multiclass_brier": delta,
                },
            }
    rule = {
        "min_train_transitions": {domain: 32 for domain in domains},
        "min_eval_transitions": {domain: 16 for domain in domains},
        "min_eval_runs": {domain: 4 for domain in domains},
        "min_transitions_per_eval_run": {domain: 4 for domain in domains},
        "min_train_action_count": {domain: 8 for domain in domains},
        "min_train_state_action_cells": {domain: 2 for domain in domains},
        "min_nll_improvement_nats": 0.02,
        "min_brier_improvement": 0.01,
        "min_positive_run_fraction": 0.75,
        "all_domains_must_pass": True,
    }
    return score, rule


def test_decision_requires_support_micro_macro_and_run_consistency():
    score, rule = _decision_fixture()
    decision, checks = phase2._decision(score, rule)
    assert decision == "GO_OFFLINE_LEARNED_OBSERVER_PROTOTYPE"
    assert all(check["passed"] for check in checks.values())

    score["runs"]["ls20-0"]["n_eval"] = 3
    decision, checks = phase2._decision(score, rule)
    assert decision == "NO_GO_INSUFFICIENT_EVIDENCE"
    assert checks["ls20"]["failure_class"] == "insufficient_evidence"


def test_decision_distinguishes_predictive_consistency_and_effect_failures():
    score, rule = _decision_fixture(delta=-0.1)
    decision, checks = phase2._decision(score, rule)
    assert decision == "NO_GO_PREDICTIVE_FAILURE"
    assert checks["ls20"]["failure_class"] == "predictive_failure"

    score, rule = _decision_fixture(delta=0.1)
    for run_index in (2, 3):
        run = score["runs"][f"ls20-{run_index}"]
        for key in ("delta_marginal_minus_tabular", "delta_null_minus_tabular"):
            run[key] = {"categorical_nll": -0.01, "multiclass_brier": -0.01}
    decision, checks = phase2._decision(score, rule)
    assert decision == "NO_GO_RUN_INCONSISTENT"
    assert checks["ls20"]["positive_run_fraction"] == 0.5

    score, rule = _decision_fixture(delta=0.005)
    decision, checks = phase2._decision(score, rule)
    assert decision == "NO_GO_EFFECT_GATE_FAILED"
    assert checks["ls20"]["failure_class"] == "effect_gate_failed"
