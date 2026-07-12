from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "spikes" / "world_model_phase2b.py"
spec = importlib.util.spec_from_file_location("world_model_phase2b", MODULE_PATH)
phase2b = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = phase2b
spec.loader.exec_module(phase2b)


EXPECTED_ACTION_HASHES = (
    "7a34ddb5c8e25d951a240434c6115458289e5ceb07af9a165984d83ccf6c130d",
    "febac5748a23abe764e2c1ba3dd9c33f255aa5b3d95334ee4434a919c06ea553",
    "91616910c509c1e42f149262064b7cac9b36971a4abf1b8de1eeb970932126dc",
    "2b3c8eaa402fff61dbc5400f5b14718add19a4f7a232895d146d6be9ee96c76c",
    "796b2be53327ebc4153de70a934d8956946101979c38318fc8af8e32ba96b6b4",
    "380b87f7d637e4c0c10bb92260a7497eb1011aeae11404c2b7260cfd9f5b9ba5",
    "9cc39de5931bb333e1de533e261abc4bb4ccbbd08b2b7f275dfdf4e55f6aa920",
    "5ca4e7d50ed0a50989153e62c05e941357fb7ca1535acc1d688ed9c6d066da62",
    "b4ce440019e88fbcfb04bfa2d5a7738752e12a333c2f99d0774e62165aa54a1a",
    "3cb5c095bf6f9c0703892334926f88dc85c45278c8d9351bd4c24fe6cb41bd85",
    "a451f0f7c83f7cdd69eca67cbad607e5dbe2e14f7b1413dd82ba1963dac4f51b",
    "aa3fb1246744564c68dc15e1e7847a56800d09c90eeaaff3bd8f90c53e0ac2e4",
    "dbb42e4fa2222764ebab1909cd93a00e2751ef3cb3d0be5adf075346c8fb84ec",
    "22fff563b777c6f64d442e775c578ca001b1e487b7e41d7dddb258524c3beca1",
    "9db3f5ced3088a2f3fd1809b1601778cc4e7cf5de29f7c6c0035521dc4218a1a",
    "90678a0d1adbb25bb0b2ed5b0dc8293610dbad4fee3f035966b2a35c9d6af5c7",
)


def _review_attestation() -> dict:
    document = phase2b.REVIEW_DOCUMENT.resolve()
    return {
        "reviewer": "isegrim",
        "disposition": "approved",
        "watercooler_message_id": 999,
        "reviewed_at_utc": "2026-07-12T14:00:00+00:00",
        "reviewed_document_path": document.relative_to(phase2b.REPO_ROOT).as_posix(),
        "reviewed_document_sha256": phase2b.file_sha256(document),
        "note": "test attestation only",
    }


def _preregistration() -> dict:
    return phase2b.build_preregistration(
        _review_attestation(),
        created_at_utc="2026-07-12T14:01:00+00:00",
    )


def _rehash(payload: dict, field: str) -> None:
    payload.pop(field)
    payload[field] = phase2b.canonical_sha256(payload)


def _decision_score(
    *, positive_runs: int = 16, n_eval: int = 512, short_runs: int = 0
) -> dict:
    runs = {}
    for index in range(16):
        value = 0.1 if index < positive_runs else -0.1
        runs[f"phase2b-ls20-eval-{index:03d}"] = {
            "domain": "ls20",
            "n_eval": 15 if index >= 16 - short_runs else 32,
            "delta_marginal_minus_tabular": {
                "categorical_nll": value,
                "multiclass_brier": value,
            },
            "delta_null_minus_tabular": {
                "categorical_nll": value,
                "multiclass_brier": value,
            },
        }
    return {
        "domains": {
            "ls20": {
                "n_eval": n_eval,
                "delta_marginal_minus_tabular": {
                    "categorical_nll": 0.05,
                    "multiclass_brier": 0.05,
                },
                "delta_null_minus_tabular": {
                    "categorical_nll": 0.05,
                    "multiclass_brier": 0.05,
                },
            }
        },
        "runs": runs,
        "training_support": {
            "ls20": {
                "n_train": 288,
                "n_state_action_cells": 38,
                "action_counts": {action: 60 for action in phase2b.LS20_ACTION_SPACE},
            }
        },
    }


def test_v1_bundle_identities_are_unchanged():
    validated = phase2b.validate_v1_bundle()
    assert validated["report"]["decision"] == "NO_GO_RUN_INCONSISTENT"
    assert (
        validated["baselines"]["domains"]["ls20"]["tabular"]["estimator_id"]
        == phase2b.TABULAR_ESTIMATOR_ID
    )


def test_run_specs_bind_all_seeds_actions_and_groups():
    specs = phase2b.build_run_specs()
    assert len(specs) == 16
    assert len({row["run_id"] for row in specs}) == 16
    assert len({row["episode_id"] for row in specs}) == 16
    assert len({row["source_group_id"] for row in specs}) == 16
    assert len({row["environment_seed"] for row in specs}) == 16
    assert len({row["policy_seed"] for row in specs}) == 16
    assert {len(row["action_sequence"]) for row in specs} == {48}
    assert tuple(row["action_sequence_sha256"] for row in specs) == EXPECTED_ACTION_HASHES
    assert {row["environment_seed"] for row in specs}.isdisjoint(
        set(range(1100, 1106)) | set(range(2100, 2103))
    )


def test_preregistration_and_eval_freeze_validate_without_outcomes():
    preregistration = _preregistration()
    phase2b.validate_preregistration(
        preregistration,
        reviewed_document=phase2b.REVIEW_DOCUMENT,
    )
    eval_freeze = phase2b.build_eval_freeze(preregistration)
    phase2b.validate_eval_freeze(eval_freeze, preregistration=preregistration)
    serialized = str(preregistration).lower() + str(eval_freeze).lower()
    for forbidden in ("'scores':", "'outcomes':", "'report':", "'decision':"):
        assert forbidden not in serialized


def test_scoped_decision_requires_twelve_of_sixteen_positive_runs():
    decision, check = phase2b.decide(_decision_score(positive_runs=12))
    assert decision == "GO_LS20_CONSISTENCY_REPLICATED"
    assert check["positive_runs"] == 12
    decision, check = phase2b.decide(_decision_score(positive_runs=11))
    assert decision == "NO_GO_LS20_RUN_INCONSISTENT"
    assert check["macro_effect_passed"] is True


def test_scoped_decision_precedes_effects_with_support_failure():
    decision, check = phase2b.decide(_decision_score(n_eval=511))
    assert decision == "NO_GO_LS20_INSUFFICIENT_EVIDENCE"
    assert check["support_passed"] is False


def test_short_runs_are_non_positive_without_single_run_study_failure():
    decision, check = phase2b.decide(_decision_score(short_runs=4))
    assert decision == "GO_LS20_CONSISTENCY_REPLICATED"
    assert check["support_passed"] is True
    assert check["short_runs"] == 4
    assert check["positive_runs"] == 12


def test_more_than_four_short_runs_fail_support():
    decision, check = phase2b.decide(_decision_score(short_runs=5))
    assert decision == "NO_GO_LS20_INSUFFICIENT_EVIDENCE"
    assert check["support_passed"] is False
    assert check["short_runs"] == 5


def test_v1_ls20_rows_reconstruct_the_exact_frozen_scoring_path(tmp_path):
    source = phase2b.V1_BUNDLE / "eval.jsonl"
    rows = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["commit"]["domain"] == "ls20"
    ]
    eval_path = tmp_path / "ls20-eval.jsonl"
    eval_path.write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    score = phase2b._reconstruct_and_score(eval_path)
    assert score["n_train"] == 288
    assert score["n_eval"] == 144
    assert score["domains"]["ls20"]["metrics"]["tabular"][
        "categorical_nll"
    ] == pytest.approx(0.3806431267008909)


def test_validator_rejects_rehashed_seed_tampering():
    preregistration = copy.deepcopy(_preregistration())
    preregistration["run_specs"][0]["environment_seed"] += 1
    _rehash(preregistration, "preregistration_sha256")
    with pytest.raises(ValueError, match="run specs differ"):
        phase2b.validate_preregistration(
            preregistration,
            reviewed_document=phase2b.REVIEW_DOCUMENT,
        )


def test_validator_rejects_rehashed_decision_tuning():
    preregistration = copy.deepcopy(_preregistration())
    preregistration["decision_rule"]["min_positive_runs"] = 11
    _rehash(preregistration, "preregistration_sha256")
    with pytest.raises(ValueError, match="decision rule mismatch"):
        phase2b.validate_preregistration(
            preregistration,
            reviewed_document=phase2b.REVIEW_DOCUMENT,
        )


def test_v1_artifact_transcription_or_content_change_fails_closed(tmp_path):
    copied = tmp_path / "v1"
    shutil.copytree(phase2b.V1_BUNDLE, copied)
    with (copied / "report.json").open("ab") as handle:
        handle.write(b"\n")
    with pytest.raises(ValueError, match="report.json"):
        phase2b.validate_v1_bundle(copied)


def test_packet_is_no_overwrite_and_tamper_evident(tmp_path):
    preregistration = _preregistration()
    eval_freeze = phase2b.build_eval_freeze(preregistration)
    output = tmp_path / "freeze"
    phase2b.publish_packet(
        output,
        preregistration=preregistration,
        eval_freeze=eval_freeze,
        reviewed_document=phase2b.REVIEW_DOCUMENT,
    )
    identities = phase2b.verify_packet(output)
    assert identities["preregistration_sha256"] == preregistration[
        "preregistration_sha256"
    ]
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        phase2b.publish_packet(
            output,
            preregistration=preregistration,
            eval_freeze=eval_freeze,
            reviewed_document=phase2b.REVIEW_DOCUMENT,
        )
    with (output / "eval_freeze.json").open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ValueError, match="eval_freeze.json"):
        phase2b.verify_packet(output)


def test_synthetic_result_bundle_reconstructs_end_to_end(tmp_path, monkeypatch):
    decision_rule = {
        **phase2b.DECISION_RULE,
        "min_eval_transitions": 16,
        "short_run_transition_threshold": 1,
    }
    monkeypatch.setattr(phase2b, "DECISION_RULE", decision_rule)
    preregistration = _preregistration()
    eval_freeze = phase2b.build_eval_freeze(preregistration)
    freeze = tmp_path / "freeze"
    phase2b.publish_packet(
        freeze,
        preregistration=preregistration,
        eval_freeze=eval_freeze,
        reviewed_document=phase2b.REVIEW_DOCUMENT,
    )

    result = tmp_path / "synthetic-result"
    result.mkdir()
    for name in ("preregistration.json", "eval_freeze.json", "REVIEWED_SPEC.md"):
        shutil.copy2(freeze / name, result / name)
    estimator, _, _ = phase2b.load_frozen_ls20_estimators()
    frame = np.full((64, 64), 4, dtype=np.int8)
    frame[20:22, 20:25] = 12
    frame_payload = phase2b.phase2._frame_payload(frame)
    for run_spec in preregistration["run_specs"]:
        action = run_spec["action_sequence"][0]
        action_name = json.loads(action)["name"]
        pre = {
            "game_id": phase2b.EXPECTED_LS20_SOURCE["game_id"],
            "guid": f"guid:{run_spec['run_id']}",
            "state": "NOT_FINISHED",
            "levels_completed": 0,
            "win_levels": 0,
            "full_reset": False,
            "available_actions": [1, 2, 3, 4],
            "previous_action": {"id": "RESET", "data": {}, "reasoning": None},
            "frames": [frame_payload],
        }
        post = copy.deepcopy(pre)
        post["state"] = "GAME_OVER"
        post["previous_action"] = {
            "id": action_name,
            "data": {},
            "reasoning": None,
        }
        journal = phase2b.phase2.DurableTraceJournal(
            phase2b.phase2._journal_path(result, run_spec),
            manifest_sha256=eval_freeze["eval_freeze_sha256"],
        )
        pending = journal.begin(
            observer=estimator,
            run_id=run_spec["run_id"],
            domain="ls20",
            episode_id=run_spec["episode_id"],
            step_index=0,
            state_ref=phase2b.phase2.ls20_state_ref(pre),
            action=action,
            state_source_kind="environment",
            state_source_id=f"{run_spec['source_group_id']}:pre:0",
            state_source_payload={
                "collector": phase2b.phase2.COLLECTOR_VERSION,
                "source_group_id": run_spec["source_group_id"],
                "environment_seed": run_spec["environment_seed"],
                "observation": pre,
            },
        )
        journal.finish(
            pending,
            observation="terminal_game_over",
            outcome_source_kind="environment",
            outcome_source_id=f"{run_spec['source_group_id']}:post:0",
            outcome_source_payload={
                "collector": phase2b.phase2.COLLECTOR_VERSION,
                "source_group_id": run_spec["source_group_id"],
                "environment_seed": run_spec["environment_seed"],
                "observation": post,
            },
        )
    phase2b._finalize_result_staging(
        result,
        preregistration=preregistration,
        eval_freeze=eval_freeze,
        collection_environment=phase2b.EXPECTED_LS20_SOURCE,
    )
    verified = phase2b.verify_result(result)
    assert verified["ok"] is True
    assert verified["n_eval"] == 16


def test_outcome_bearing_collection_failure_blocks_replacement(tmp_path, monkeypatch):
    preregistration = _preregistration()
    eval_freeze = phase2b.build_eval_freeze(preregistration)
    freeze = tmp_path / "freeze"
    phase2b.publish_packet(
        freeze,
        preregistration=preregistration,
        eval_freeze=eval_freeze,
        reviewed_document=phase2b.REVIEW_DOCUMENT,
    )
    monkeypatch.setattr(
        phase2b.phase2,
        "_resolve_ls20_provenance",
        lambda *_: phase2b.EXPECTED_LS20_SOURCE,
    )

    def fail_collection(**_):
        raise RuntimeError("synthetic collection interruption")

    monkeypatch.setattr(phase2b.phase2, "collect_ls20_run", fail_collection)
    output = tmp_path / "result"
    with pytest.raises(RuntimeError, match="retained outcome-bearing staging"):
        phase2b.collect_result(
            freeze_bundle=freeze,
            output=output,
            environments_dir=tmp_path,
            recordings_dir=tmp_path,
            enforce_canonical_paths=False,
        )
    staging = tmp_path / f".result.staging-{eval_freeze['eval_freeze_sha256'][:16]}"
    assert staging.is_dir()
    with pytest.raises(FileExistsError, match="refusing to replace retained"):
        phase2b.collect_result(
            freeze_bundle=freeze,
            output=output,
            environments_dir=tmp_path,
            recordings_dir=tmp_path,
            enforce_canonical_paths=False,
        )


def test_collection_rejects_noncanonical_freeze_before_opening_arc(tmp_path):
    preregistration = _preregistration()
    eval_freeze = phase2b.build_eval_freeze(preregistration)
    freeze = tmp_path / "freeze"
    phase2b.publish_packet(
        freeze,
        preregistration=preregistration,
        eval_freeze=eval_freeze,
        reviewed_document=phase2b.REVIEW_DOCUMENT,
    )
    with pytest.raises(ValueError, match="freeze bundle must use its preregistered path"):
        phase2b.collect_result(
            freeze_bundle=freeze,
            output=tmp_path / "result",
            environments_dir=tmp_path,
            recordings_dir=tmp_path,
        )
