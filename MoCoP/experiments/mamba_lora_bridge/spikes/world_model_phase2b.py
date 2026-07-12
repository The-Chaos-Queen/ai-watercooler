#!/usr/bin/env python3
"""Prepare, collect, and verify the frozen World Model Phase 2b replication."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BRIDGE_DIR = Path(__file__).resolve().parents[1]
SPIKES_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
for import_path in (BRIDGE_DIR, SPIKES_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import collect_world_model_phase2 as phase2  # noqa: E402
import score_world_model_trace as scorer  # noqa: E402
from world_model_baselines import (  # noqa: E402
    DeterministicActionShuffleNull,
    DirichletTabularEstimator,
    EmpiricalMarginalEstimator,
)
from world_model_capture import (  # noqa: E402
    CapturedTracePair,
    canonical_action,
    load_journal,
    paired_trace_bytes,
)
from world_model_trace import canonical_sha256  # noqa: E402


PREREGISTRATION_SCHEMA_VERSION = "world-model-phase2b-preregistration-v1"
EVAL_FREEZE_SCHEMA_VERSION = "world-model-phase2b-eval-freeze-v1"
REPORT_SCHEMA_VERSION = "world-model-phase2b-report-v1"
REVIEW_DOCUMENT = SPIKES_DIR / "WORLD_MODEL_PHASE2B_LS20_REPLICATION_PREREG_2026-07-12.md"
V1_BUNDLE = BRIDGE_DIR / "results" / "world_model_phase2" / "phase2_real_v1"
V1_BUNDLE_RELATIVE = "MoCoP/experiments/mamba_lora_bridge/results/world_model_phase2/phase2_real_v1"
FREEZE_BUNDLE_RELATIVE = (
    "MoCoP/experiments/mamba_lora_bridge/results/world_model_phase2/"
    "phase2b_ls20_prereg_v1"
)
RESULT_BUNDLE_RELATIVE = (
    "MoCoP/experiments/mamba_lora_bridge/results/world_model_phase2/"
    "phase2b_ls20_real_v1"
)
SEED_NAMESPACE = (
    "mocop/openclaw/152/world-model-phase2b/"
    "497acb5cbbea6f26afecfaf9c8f28d4bbd7cebba081e35d2f34d07ddef4facd2"
)
RUN_COUNT = 16
PLANNED_STEPS = 48

V1_FILE_SHA256 = {
    "pre_run_manifest.json": "6d1fb290b2a2c06c35cd709be71291b623a7ac241a6f009f7c50e5e2592a0304",
    "train.jsonl": "29b3f349d43f6ae29b3a8509d0513177198a38f5232346fae3e27b88e9f657ef",
    "frozen_baselines.json": "4e0d2d39dfab75fcf68abe53ab97738eeaaa1653c6523aa95769e3f8e9cf780c",
    "eval_freeze.json": "5e14cce94743c74163170af42988cc7d5fb79abd93a2984e9bbb4d9673d130d0",
    "report.json": "0be026c1d5c834c9b4313c3d391ffb62936b98c2a23eb25d694657b15ebd9fdd",
}
V1_MANIFEST_SHA256 = "497acb5cbbea6f26afecfaf9c8f28d4bbd7cebba081e35d2f34d07ddef4facd2"
V1_BASELINE_BUNDLE_SHA256 = "6e96fae900fa85a12ac638df6e33d652ae6398cc8648dd143d6934679097bc7a"
V1_EVAL_FREEZE_SHA256 = "7a7d2b856724ed29bff5e24de4b7f5db917ee746415d30cf3762980214d856d2"
TABULAR_ESTIMATOR_ID = "dirichlet-tabular-v1:ls20:29b3f349d43f6ae2"
MARGINAL_ESTIMATOR_ID = "empirical-marginal-null-v1:ls20:29b3f349d43f6ae2"
SHUFFLE_ESTIMATOR_ID = "action-shuffle-null-v1:001b866749367806"
SHUFFLE_SEED_BASE = "world-model-phase2-real-v1"
SHUFFLE_SEED = f"{SHUFFLE_SEED_BASE}:ls20"

LS20_ACTION_SPACE = tuple(canonical_action(f"ACTION{index}") for index in range(1, 5))
LS20_OBSERVATION_SPACE = (
    "avatar_blocked",
    "avatar_moved",
    "level_advanced",
    "terminal_game_over",
    "terminal_win",
)
EXPECTED_LS20_SOURCE = {
    "arc_agi_distribution_sha256": "5332c0e7a71076577bfca080bfb72afca21cc23591cd95f29b9490f50faff153",
    "arc_agi_version": "0.9.8",
    "arcengine_distribution_sha256": "2feecf2979c5a7b1398f53696f17abb5fdaea21cba164228ac8278b3fb326b42",
    "arcengine_version": "0.9.3",
    "game_file_sha256": "67cc85888eeef68f125cbb5f5fb158e9ca455d6bca46b171790f556fcabf934e",
    "game_id": "ls20-9607627b",
    "metadata_sha256": "b0c1518d6bb8542a59888dcdcd1469a3530da608d0a53dc746c73f13f1d0bf15",
    "official_toolkit_url": "https://github.com/arcprize/ARC-AGI",
    "operation_mode": "OFFLINE",
}
DECISION_RULE = {
    "domain": "ls20",
    "min_brier_improvement": 0.01,
    "min_eval_runs": 16,
    "min_eval_transitions": 512,
    "min_nll_improvement_nats": 0.02,
    "min_positive_run_fraction": 0.75,
    "min_positive_runs": 12,
    "min_train_action_count": 8,
    "min_train_state_action_cells": 4,
    "min_train_transitions": 192,
    "short_run_transition_threshold": 16,
    "max_short_runs": 4,
}
ANALYSIS_CONTRACT = {
    "aggregate_weighting": "transition_micro",
    "run_macro_weighting": "unweighted_complete_run",
    "positive_run": (
        "all_nll_and_class_summed_brier_deltas_strictly_positive_against_"
        "both_frozen_nulls"
    ),
    "effect_gate_applies_to": ["transition_micro", "unweighted_run_macro"],
    "v1_eval_use": "historical_context_only_never_pooled_or_gated",
    "terminal_run_policy": "retain_without_replacement",
    "failed_run_policy": "resume_same_hash_bound_journal_or_fail_support_no_new_seed",
    "decision_precedence": [
        "INVALID_PROTOCOL",
        "NO_GO_LS20_INSUFFICIENT_EVIDENCE",
        "NO_GO_LS20_PREDICTIVE_FAILURE",
        "NO_GO_LS20_RUN_INCONSISTENT",
        "NO_GO_LS20_EFFECT_GATE_FAILED",
        "GO_LS20_CONSISTENCY_REPLICATED",
    ],
}
PROHIBITED_INTEGRATIONS = [
    "bridge_loss",
    "gemma_dose",
    "online_action_selection",
    "qdrant_access",
    "memory_routing",
    "dynamic_alpha",
    "learned_observer",
]
PUBLICATION_CONTRACT = {
    "freeze_bundle_path": FREEZE_BUNDLE_RELATIVE,
    "result_bundle_path": RESULT_BUNDLE_RELATIVE,
    "single_result_per_eval_freeze": True,
    "retained_staging_blocks_replacement": True,
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path, *, field: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be a JSON object")
    return payload


def _validate_utc_timestamp(value: Any, *, field: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0.0:
        raise ValueError(f"{field} must include a zero UTC offset")


def _validate_self_hash(
    payload: dict[str, Any], *, hash_field: str, expected: str | None = None
) -> str:
    if hash_field not in payload:
        raise ValueError(f"missing self-hash field: {hash_field}")
    claimed = payload[hash_field]
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError(f"invalid self-hash field: {hash_field}")
    unhashed = dict(payload)
    unhashed.pop(hash_field)
    if canonical_sha256(unhashed) != claimed:
        raise ValueError(f"self-hash mismatch: {hash_field}")
    if expected is not None and claimed != expected:
        raise ValueError(f"unexpected identity: {hash_field}")
    return claimed


def validate_v1_bundle(bundle: Path = V1_BUNDLE) -> dict[str, Any]:
    bundle = Path(bundle).resolve()
    for name, expected in V1_FILE_SHA256.items():
        if file_sha256(bundle / name) != expected:
            raise ValueError(f"Phase 2 v1 artifact hash mismatch: {name}")

    manifest = _load_json_object(bundle / "pre_run_manifest.json", field="v1 manifest")
    _validate_self_hash(
        manifest,
        hash_field="manifest_sha256",
        expected=V1_MANIFEST_SHA256,
    )
    if manifest.get("ls20_source") != EXPECTED_LS20_SOURCE:
        raise ValueError("Phase 2 v1 LS20 provenance mismatch")

    eval_freeze = _load_json_object(bundle / "eval_freeze.json", field="v1 eval freeze")
    _validate_self_hash(
        eval_freeze,
        hash_field="eval_freeze_sha256",
        expected=V1_EVAL_FREEZE_SHA256,
    )
    if eval_freeze.get("pre_run_manifest_sha256") != V1_MANIFEST_SHA256:
        raise ValueError("Phase 2 v1 eval-freeze manifest mismatch")
    if eval_freeze.get("train_trace_sha256") != V1_FILE_SHA256["train.jsonl"]:
        raise ValueError("Phase 2 v1 eval-freeze train identity mismatch")
    if eval_freeze.get("baseline_bundle_sha256") != V1_BASELINE_BUNDLE_SHA256:
        raise ValueError("Phase 2 v1 eval-freeze baseline identity mismatch")

    baselines = _load_json_object(
        bundle / "frozen_baselines.json", field="v1 frozen baselines"
    )
    _validate_self_hash(
        baselines,
        hash_field="baseline_bundle_sha256",
        expected=V1_BASELINE_BUNDLE_SHA256,
    )
    ls20 = baselines.get("domains", {}).get("ls20", {})
    expected_estimator_ids = {
        "tabular": TABULAR_ESTIMATOR_ID,
        "empirical_marginal_null": MARGINAL_ESTIMATOR_ID,
        "action_shuffle_null": SHUFFLE_ESTIMATOR_ID,
    }
    actual_estimator_ids = {
        "tabular": ls20.get("tabular", {}).get("estimator_id"),
        "empirical_marginal_null": ls20.get("empirical_marginal_null", {}).get(
            "estimator_id"
        ),
        "action_shuffle_null": ls20.get("action_shuffle_null", {}).get("estimator_id"),
    }
    if actual_estimator_ids != expected_estimator_ids:
        raise ValueError("Phase 2 v1 LS20 estimator identity mismatch")
    if ls20.get("action_shuffle_null", {}).get("seed") != SHUFFLE_SEED:
        raise ValueError("Phase 2 v1 LS20 shuffle seed mismatch")
    if ls20.get("action_space") != list(LS20_ACTION_SPACE):
        raise ValueError("Phase 2 v1 LS20 action space mismatch")
    if ls20.get("observation_space") != list(LS20_OBSERVATION_SPACE):
        raise ValueError("Phase 2 v1 LS20 observation space mismatch")

    report = _load_json_object(bundle / "report.json", field="v1 report")
    if report.get("decision") != "NO_GO_RUN_INCONSISTENT":
        raise ValueError("Phase 2 v1 decision identity mismatch")
    return {
        "manifest": manifest,
        "eval_freeze": eval_freeze,
        "baselines": baselines,
        "report": report,
    }


def derive_seed(label: str, index: int) -> int:
    if label not in {"environment", "policy"}:
        raise ValueError("seed label must be environment or policy")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < RUN_COUNT:
        raise ValueError(f"seed index must be in [0, {RUN_COUNT})")
    digest = hashlib.sha256(
        f"{SEED_NAMESPACE}|{label}|{index:03d}".encode("ascii")
    ).digest()
    return 100_000 + int.from_bytes(digest[:8], "big") % (2_147_483_647 - 100_000)


def build_run_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for index in range(RUN_COUNT):
        suffix = f"{index:03d}"
        run_id = f"phase2b-ls20-eval-{suffix}"
        policy_seed = derive_seed("policy", index)
        rng = random.Random(policy_seed)
        actions = [rng.choice(LS20_ACTION_SPACE) for _ in range(PLANNED_STEPS)]
        specs.append(
            {
                "run_id": run_id,
                "split": "eval",
                "domain": "ls20",
                "episode_id": f"episode:{run_id}",
                "source_group_id": f"source-group:{run_id}",
                "environment_seed": derive_seed("environment", index),
                "policy_seed": policy_seed,
                "planned_steps": PLANNED_STEPS,
                "action_sequence": actions,
                "action_sequence_sha256": canonical_sha256(actions),
            }
        )
    return specs


def _code_hashes() -> dict[str, str]:
    paths = (
        BRIDGE_DIR / "world_model_trace.py",
        BRIDGE_DIR / "world_model_baselines.py",
        BRIDGE_DIR / "world_model_capture.py",
        SPIKES_DIR / "score_world_model_trace.py",
        SPIKES_DIR / "collect_world_model_phase2.py",
        SPIKES_DIR / "world_model_phase2b.py",
    )
    return {
        path.relative_to(REPO_ROOT).as_posix(): file_sha256(path)
        for path in paths
    }


def _runtime_identity() -> dict[str, str]:
    return {
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": sys.version,
        "platform": sys.platform,
        "os_name": os.name,
    }


def _validate_review_attestation(
    attestation: dict[str, Any],
    *,
    reviewed_document: Path,
    verify_canonical_document: bool = True,
) -> None:
    expected_fields = {
        "reviewer",
        "disposition",
        "watercooler_message_id",
        "reviewed_at_utc",
        "reviewed_document_path",
        "reviewed_document_sha256",
        "note",
    }
    if not isinstance(attestation, dict) or set(attestation) != expected_fields:
        raise ValueError("review attestation fields mismatch")
    if attestation["reviewer"] != "isegrim":
        raise ValueError("Phase 2b primary review must be attributed to Isegrim")
    if attestation["disposition"] not in {"approved", "approved_with_changes_resolved"}:
        raise ValueError("review disposition does not authorize a freeze")
    message_id = attestation["watercooler_message_id"]
    if isinstance(message_id, bool) or not isinstance(message_id, int) or message_id <= 0:
        raise ValueError("review Watercooler message id must be a positive integer")
    _validate_utc_timestamp(attestation["reviewed_at_utc"], field="reviewed_at_utc")
    claimed_document_sha256 = attestation["reviewed_document_sha256"]
    if claimed_document_sha256 != file_sha256(reviewed_document):
        raise ValueError("review attestation document hash mismatch")
    expected_path = REVIEW_DOCUMENT.resolve().relative_to(REPO_ROOT).as_posix()
    if attestation["reviewed_document_path"] != expected_path:
        raise ValueError("review attestation document path mismatch")
    if (
        verify_canonical_document
        and claimed_document_sha256 != file_sha256(REPO_ROOT / expected_path)
    ):
        raise ValueError("canonical reviewed document hash mismatch")
    if not isinstance(attestation["note"], str):
        raise ValueError("review note must be text")


def build_preregistration(
    review_attestation: dict[str, Any],
    *,
    reviewed_document: Path = REVIEW_DOCUMENT,
    v1_bundle: Path = V1_BUNDLE,
    created_at_utc: str,
) -> dict[str, Any]:
    validate_v1_bundle(v1_bundle)
    reviewed_document = Path(reviewed_document).resolve()
    _validate_review_attestation(review_attestation, reviewed_document=reviewed_document)
    payload = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "created_at_utc": created_at_utc,
        "openclaw_task_id": 152,
        "phase": "world_model_phase2b_ls20_consistency_replication",
        "status": "frozen_before_phase2b_outcomes",
        "review_attestation": dict(review_attestation),
        "v1_inputs": {
            "bundle_path": V1_BUNDLE_RELATIVE,
            "file_sha256": dict(V1_FILE_SHA256),
            "manifest_sha256": V1_MANIFEST_SHA256,
            "baseline_bundle_sha256": V1_BASELINE_BUNDLE_SHA256,
            "eval_freeze_sha256": V1_EVAL_FREEZE_SHA256,
            "v1_decision": "NO_GO_RUN_INCONSISTENT",
            "eval_use": "historical_context_only_never_pooled_or_gated",
        },
        "estimator_policy": {
            "policy": "reuse_exact_v1_frozen",
            "refit": False,
            "new_training_split": False,
            "alpha": 1.0,
            "tabular_estimator_id": TABULAR_ESTIMATOR_ID,
            "empirical_marginal_estimator_id": MARGINAL_ESTIMATOR_ID,
            "action_shuffle_estimator_id": SHUFFLE_ESTIMATOR_ID,
            "action_shuffle_seed": SHUFFLE_SEED,
        },
        "environment": dict(EXPECTED_LS20_SOURCE),
        "spaces": {
            "state_ref_extractor": "ls20-avatar-mask-v1",
            "actions": list(LS20_ACTION_SPACE),
            "observations": list(LS20_OBSERVATION_SPACE),
        },
        "seed_derivation": {
            "namespace": SEED_NAMESPACE,
            "digest": "sha256",
            "input": "namespace|label|zero_padded_three_digit_index",
            "conversion": (
                "100000 + int.from_bytes(digest[0:8], big) % "
                "(2147483647 - 100000)"
            ),
        },
        "run_specs": build_run_specs(),
        "decision_rule": dict(DECISION_RULE),
        "analysis_contract": dict(ANALYSIS_CONTRACT),
        "split_contract": {
            "claim": "rollout_held_out_not_state_held_out",
            "held_out_unit": "whole_run_episode_source_group",
            "state_content_overlap": "allowed_for_transition_estimation",
            "v1_eval_overlap": "prohibited",
        },
        "runtime": _runtime_identity(),
        "code_sha256": _code_hashes(),
        "publication_contract": dict(PUBLICATION_CONTRACT),
        "prohibited_integrations": list(PROHIBITED_INTEGRATIONS),
        "claim_boundary": (
            "scoped_go_confirms_ls20_consistency_only_and_does_not_authorize_"
            "downstream_integration"
        ),
    }
    return {**payload, "preregistration_sha256": canonical_sha256(payload)}


def validate_preregistration(
    payload: dict[str, Any],
    *,
    reviewed_document: Path,
    v1_bundle: Path = V1_BUNDLE,
    verify_code_hashes: bool = True,
    verify_canonical_review_document: bool = True,
) -> None:
    expected_fields = {
        "schema_version",
        "created_at_utc",
        "openclaw_task_id",
        "phase",
        "status",
        "review_attestation",
        "v1_inputs",
        "estimator_policy",
        "environment",
        "spaces",
        "seed_derivation",
        "run_specs",
        "decision_rule",
        "analysis_contract",
        "split_contract",
        "runtime",
        "code_sha256",
        "publication_contract",
        "prohibited_integrations",
        "claim_boundary",
        "preregistration_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise ValueError("preregistration fields mismatch")
    if payload["schema_version"] != PREREGISTRATION_SCHEMA_VERSION:
        raise ValueError("preregistration schema version mismatch")
    _validate_utc_timestamp(payload["created_at_utc"], field="created_at_utc")
    _validate_self_hash(payload, hash_field="preregistration_sha256")
    validate_v1_bundle(v1_bundle)
    _validate_review_attestation(
        payload["review_attestation"],
        reviewed_document=Path(reviewed_document),
        verify_canonical_document=verify_canonical_review_document,
    )
    if payload["openclaw_task_id"] != 152 or payload["status"] != "frozen_before_phase2b_outcomes":
        raise ValueError("preregistration task or outcome-free status mismatch")
    if payload["v1_inputs"] != {
        "bundle_path": V1_BUNDLE_RELATIVE,
        "file_sha256": V1_FILE_SHA256,
        "manifest_sha256": V1_MANIFEST_SHA256,
        "baseline_bundle_sha256": V1_BASELINE_BUNDLE_SHA256,
        "eval_freeze_sha256": V1_EVAL_FREEZE_SHA256,
        "v1_decision": "NO_GO_RUN_INCONSISTENT",
        "eval_use": "historical_context_only_never_pooled_or_gated",
    }:
        raise ValueError("preregistration v1 inputs mismatch")
    if payload["environment"] != EXPECTED_LS20_SOURCE:
        raise ValueError("preregistration environment mismatch")
    if payload["run_specs"] != build_run_specs():
        raise ValueError("preregistration run specs differ from the bound derivation")
    if payload["decision_rule"] != DECISION_RULE:
        raise ValueError("preregistration decision rule mismatch")
    if payload["analysis_contract"] != ANALYSIS_CONTRACT:
        raise ValueError("preregistration analysis contract mismatch")
    if payload["publication_contract"] != PUBLICATION_CONTRACT:
        raise ValueError("preregistration publication contract mismatch")
    if payload["prohibited_integrations"] != PROHIBITED_INTEGRATIONS:
        raise ValueError("preregistration prohibited integrations mismatch")
    environment_seeds = {spec["environment_seed"] for spec in payload["run_specs"]}
    policy_seeds = {spec["policy_seed"] for spec in payload["run_specs"]}
    if len(environment_seeds) != RUN_COUNT or len(policy_seeds) != RUN_COUNT:
        raise ValueError("Phase 2b seed collision")
    if environment_seeds & policy_seeds:
        raise ValueError("Phase 2b environment/policy seed collision")
    if environment_seeds & set(range(1100, 1106)) | environment_seeds & set(range(2100, 2103)):
        raise ValueError("Phase 2b environment seed overlaps Phase 2 v1")
    if verify_code_hashes and payload["code_sha256"] != _code_hashes():
        raise ValueError("preregistration execution-code hash mismatch")
    if verify_code_hashes and payload["runtime"] != _runtime_identity():
        raise ValueError("preregistration Python runtime mismatch")


def build_eval_freeze(preregistration: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": EVAL_FREEZE_SCHEMA_VERSION,
        "created_at_utc": preregistration["created_at_utc"],
        "status": "frozen_before_phase2b_outcomes",
        "preregistration_sha256": preregistration["preregistration_sha256"],
        "review_attestation": preregistration["review_attestation"],
        "v1_manifest_sha256": V1_MANIFEST_SHA256,
        "v1_train_trace_sha256": V1_FILE_SHA256["train.jsonl"],
        "v1_baseline_bundle_sha256": V1_BASELINE_BUNDLE_SHA256,
        "v1_baseline_file_sha256": V1_FILE_SHA256["frozen_baselines.json"],
        "estimator_ids": {
            "tabular": TABULAR_ESTIMATOR_ID,
            "empirical_marginal_null": MARGINAL_ESTIMATOR_ID,
            "action_shuffle_null": SHUFFLE_ESTIMATOR_ID,
        },
        "eval_run_specs_sha256": canonical_sha256(preregistration["run_specs"]),
        "decision_rule": preregistration["decision_rule"],
        "analysis_contract": preregistration["analysis_contract"],
        "runtime": preregistration["runtime"],
        "code_sha256": preregistration["code_sha256"],
        "publication_contract": preregistration["publication_contract"],
    }
    return {**payload, "eval_freeze_sha256": canonical_sha256(payload)}


def validate_eval_freeze(
    payload: dict[str, Any], *, preregistration: dict[str, Any]
) -> None:
    expected = build_eval_freeze(preregistration)
    if payload != expected:
        raise ValueError("eval freeze differs from the preregistration-derived freeze")
    _validate_self_hash(payload, hash_field="eval_freeze_sha256")


def load_frozen_ls20_estimators(
    v1_bundle: Path = V1_BUNDLE,
) -> tuple[
    DirichletTabularEstimator,
    EmpiricalMarginalEstimator,
    DeterministicActionShuffleNull,
]:
    validated = validate_v1_bundle(v1_bundle)
    ls20 = validated["baselines"]["domains"]["ls20"]
    tabular = DirichletTabularEstimator.from_payload(ls20["tabular"])
    marginal = EmpiricalMarginalEstimator.from_payload(ls20["empirical_marginal_null"])
    shuffle = DeterministicActionShuffleNull(tabular, LS20_ACTION_SPACE, seed=SHUFFLE_SEED)
    if shuffle.estimator_id != SHUFFLE_ESTIMATOR_ID:
        raise ValueError("reconstructed action-shuffle estimator identity mismatch")
    if shuffle.action_mapping != ls20["action_shuffle_null"]["mapping"]:
        raise ValueError("reconstructed action-shuffle mapping mismatch")
    return tabular, marginal, shuffle


def decide(score: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Apply the preregistered LS20-only decision rule."""
    bucket = score["domains"]["ls20"]
    run_items = [
        (run_id, run_bucket)
        for run_id, run_bucket in score["runs"].items()
        if run_bucket["domain"] == "ls20"
    ]
    run_buckets = [run_bucket for _, run_bucket in run_items]
    short_run_threshold = DECISION_RULE["short_run_transition_threshold"]
    short_run_ids = [
        run_id
        for run_id, run_bucket in run_items
        if run_bucket["n_eval"] < short_run_threshold
    ]
    deltas = {
        "marginal": bucket["delta_marginal_minus_tabular"],
        "shuffle": bucket["delta_null_minus_tabular"],
    }
    macro_deltas = {
        "marginal": {
            metric: math.fsum(
                run_bucket["delta_marginal_minus_tabular"][metric]
                for run_bucket in run_buckets
            )
            / len(run_buckets)
            if run_buckets
            else float("-inf")
            for metric in ("categorical_nll", "multiclass_brier")
        },
        "shuffle": {
            metric: math.fsum(
                run_bucket["delta_null_minus_tabular"][metric]
                for run_bucket in run_buckets
            )
            / len(run_buckets)
            if run_buckets
            else float("-inf")
            for metric in ("categorical_nll", "multiclass_brier")
        },
    }
    training = score["training_support"]["ls20"]
    support_passed = (
        training["n_train"] >= DECISION_RULE["min_train_transitions"]
        and bucket["n_eval"] >= DECISION_RULE["min_eval_transitions"]
        and len(run_buckets) == DECISION_RULE["min_eval_runs"]
        and len(short_run_ids) <= DECISION_RULE["max_short_runs"]
        and min(training["action_counts"].values())
        >= DECISION_RULE["min_train_action_count"]
        and training["n_state_action_cells"]
        >= DECISION_RULE["min_train_state_action_cells"]
    )
    aggregate_effect_passed = all(
        delta["categorical_nll"] >= DECISION_RULE["min_nll_improvement_nats"]
        and delta["multiclass_brier"] >= DECISION_RULE["min_brier_improvement"]
        for delta in deltas.values()
    )
    macro_effect_passed = all(
        delta["categorical_nll"] >= DECISION_RULE["min_nll_improvement_nats"]
        and delta["multiclass_brier"] >= DECISION_RULE["min_brier_improvement"]
        for delta in macro_deltas.values()
    )
    positive_runs = sum(
        run_bucket["n_eval"] >= short_run_threshold
        and all(
            run_bucket[delta_key][metric] > 0.0
            for delta_key in (
                "delta_marginal_minus_tabular",
                "delta_null_minus_tabular",
            )
            for metric in ("categorical_nll", "multiclass_brier")
        )
        for run_bucket in run_buckets
    )
    positive_fraction = positive_runs / len(run_buckets) if run_buckets else 0.0
    run_consistency_passed = (
        positive_runs >= DECISION_RULE["min_positive_runs"]
        and positive_fraction >= DECISION_RULE["min_positive_run_fraction"]
    )
    predictive_failure = support_passed and all(
        value <= 0.0
        for source in (deltas, macro_deltas)
        for delta in source.values()
        for value in delta.values()
    )
    passed = (
        support_passed
        and aggregate_effect_passed
        and macro_effect_passed
        and run_consistency_passed
    )
    if not support_passed:
        decision = "NO_GO_LS20_INSUFFICIENT_EVIDENCE"
        failure_class = "insufficient_evidence"
    elif predictive_failure:
        decision = "NO_GO_LS20_PREDICTIVE_FAILURE"
        failure_class = "predictive_failure"
    elif aggregate_effect_passed and macro_effect_passed and not run_consistency_passed:
        decision = "NO_GO_LS20_RUN_INCONSISTENT"
        failure_class = "run_inconsistent"
    elif not passed:
        decision = "NO_GO_LS20_EFFECT_GATE_FAILED"
        failure_class = "effect_gate_failed"
    else:
        decision = "GO_LS20_CONSISTENCY_REPLICATED"
        failure_class = None
    check = {
        "passed": passed,
        "failure_class": failure_class,
        "support_passed": support_passed,
        "aggregate_effect_passed": aggregate_effect_passed,
        "macro_effect_passed": macro_effect_passed,
        "run_consistency_passed": run_consistency_passed,
        "n_train": training["n_train"],
        "minimum_n_train": DECISION_RULE["min_train_transitions"],
        "n_eval": bucket["n_eval"],
        "minimum_n_eval": DECISION_RULE["min_eval_transitions"],
        "n_eval_runs": len(run_buckets),
        "required_eval_runs": DECISION_RULE["min_eval_runs"],
        "eval_run_lengths": [run_bucket["n_eval"] for run_bucket in run_buckets],
        "short_run_transition_threshold": short_run_threshold,
        "short_run_ids": short_run_ids,
        "short_runs": len(short_run_ids),
        "maximum_short_runs": DECISION_RULE["max_short_runs"],
        "train_action_counts": training["action_counts"],
        "minimum_train_action_count": DECISION_RULE["min_train_action_count"],
        "train_state_action_cells": training["n_state_action_cells"],
        "minimum_train_state_action_cells": DECISION_RULE[
            "min_train_state_action_cells"
        ],
        "positive_runs": positive_runs,
        "minimum_positive_runs": DECISION_RULE["min_positive_runs"],
        "positive_run_fraction": positive_fraction,
        "minimum_positive_run_fraction": DECISION_RULE["min_positive_run_fraction"],
        "micro_deltas": deltas,
        "macro_run_deltas": macro_deltas,
    }
    return decision, check


def _validate_ls20_journal(
    path: Path,
    *,
    spec: dict[str, Any],
    eval_freeze_sha256: str,
    estimator: DirichletTabularEstimator,
) -> list[CapturedTracePair]:
    pairs = load_journal(path, expected_manifest_sha256=eval_freeze_sha256)
    if len(pairs) > spec["planned_steps"]:
        raise ValueError("journal exceeds its frozen planned length")
    if (
        len(pairs) < spec["planned_steps"]
        and pairs[-1].outcome.observation not in {"terminal_game_over", "terminal_win"}
    ):
        raise ValueError("journal ended early without a terminal LS20 outcome")
    previous_post: dict[str, Any] | None = None
    guid: str | None = None
    for step_index, pair in enumerate(pairs):
        commit = pair.commit
        if (
            commit.run_id != spec["run_id"]
            or commit.domain != "ls20"
            or commit.episode_id != spec["episode_id"]
            or commit.step_index != step_index
            or commit.action != spec["action_sequence"][step_index]
        ):
            raise ValueError("journal commit differs from its frozen run spec")
        if commit.estimator_id != estimator.estimator_id:
            raise ValueError("journal estimator identity mismatch")
        if commit.probabilities != estimator.predict(commit.state_ref, commit.action):
            raise ValueError("journal probabilities differ from the frozen estimator")
        if pair.state_source.kind != "environment":
            raise ValueError("LS20 state source must be an environment")
        if pair.outcome_source is None or pair.outcome_source.kind != "environment":
            raise ValueError("LS20 outcome source must be an environment")
        if pair.state_source.source_id != f"{spec['source_group_id']}:pre:{step_index}":
            raise ValueError("journal pre-state source identity mismatch")
        if pair.outcome_source.source_id != f"{spec['source_group_id']}:post:{step_index}":
            raise ValueError("journal post-state source identity mismatch")
        pre_payload = pair.state_source.payload
        post_payload = pair.outcome_source.payload
        expected_payload_fields = {
            "collector",
            "source_group_id",
            "environment_seed",
            "observation",
        }
        if set(pre_payload) != expected_payload_fields or set(post_payload) != expected_payload_fields:
            raise ValueError("LS20 source payload fields mismatch")
        for payload in (pre_payload, post_payload):
            if (
                payload["collector"] != phase2.COLLECTOR_VERSION
                or payload["source_group_id"] != spec["source_group_id"]
                or payload["environment_seed"] != spec["environment_seed"]
            ):
                raise ValueError("LS20 source provenance differs from its run spec")
            phase2.validate_ls20_observation_payload(
                payload["observation"], expected_game_id=EXPECTED_LS20_SOURCE["game_id"]
            )
        pre = pre_payload["observation"]
        post = post_payload["observation"]
        if guid is None:
            guid = pre["guid"]
        if pre["guid"] != guid or post["guid"] != guid:
            raise ValueError("LS20 GUID changed within a frozen run")
        if previous_post is not None and pre != previous_post:
            raise ValueError("LS20 post/pre observations are not continuous")
        if commit.state_ref != phase2.ls20_state_ref(pre):
            raise ValueError("LS20 state_ref does not reproduce from the pre-state")
        action_payload = json.loads(commit.action)
        action_name = action_payload["name"]
        if commit.action != canonical_action(action_name):
            raise ValueError("LS20 action is not canonical")
        if int(action_name.removeprefix("ACTION")) not in pre["available_actions"]:
            raise ValueError("LS20 action was illegal in the captured pre-state")
        if post["previous_action"] != {
            "id": action_name,
            "data": {},
            "reasoning": None,
        }:
            raise ValueError("LS20 post-state does not bind the committed action")
        expected_observation = phase2.classify_ls20_outcome(pre, post)
        if pair.outcome.observation != expected_observation:
            raise ValueError("LS20 outcome label does not reproduce from captured sources")
        if expected_observation in {"terminal_game_over", "terminal_win"} and step_index != len(pairs) - 1:
            raise ValueError("LS20 journal continued after a terminal outcome")
        previous_post = post
    return pairs


def _reconstruct_and_score(eval_path: Path, *, v1_bundle: Path = V1_BUNDLE) -> dict[str, Any]:
    frozen_tabular, frozen_marginal, frozen_shuffle = load_frozen_ls20_estimators(v1_bundle)
    train_pairs = [
        pair
        for pair in scorer.load_trace_pairs(Path(v1_bundle) / "train.jsonl")
        if pair.commit.domain == "ls20"
    ]
    reconstructed_tabular = DirichletTabularEstimator(
        LS20_OBSERVATION_SPACE,
        alpha=1.0,
        estimator_id=TABULAR_ESTIMATOR_ID,
    )
    reconstructed_marginal = EmpiricalMarginalEstimator(
        LS20_OBSERVATION_SPACE,
        alpha=1.0,
        estimator_id=MARGINAL_ESTIMATOR_ID,
    )
    for pair in train_pairs:
        reconstructed_tabular.update(
            pair.commit.state_ref,
            pair.commit.action,
            pair.outcome.observation,
        )
        reconstructed_marginal.update(pair.outcome.observation)
    reconstructed_shuffle = DeterministicActionShuffleNull(
        reconstructed_tabular,
        LS20_ACTION_SPACE,
        seed=SHUFFLE_SEED,
    )
    if reconstructed_tabular.canonical_payload() != frozen_tabular.canonical_payload():
        raise ValueError("v1 train trace does not reconstruct the frozen tabular estimator")
    if reconstructed_marginal.canonical_payload() != frozen_marginal.canonical_payload():
        raise ValueError("v1 train trace does not reconstruct the frozen marginal estimator")
    if reconstructed_shuffle.action_mapping != frozen_shuffle.action_mapping:
        raise ValueError("v1 train trace does not reconstruct the frozen shuffle mapping")
    eval_pairs = scorer.load_trace_pairs(eval_path)
    return scorer.score_trace_pairs(
        train_pairs,
        eval_pairs,
        alpha=1.0,
        shuffle_seed=SHUFFLE_SEED_BASE,
        observation_spaces={"ls20": LS20_OBSERVATION_SPACE},
        action_spaces={"ls20": LS20_ACTION_SPACE},
        require_eval_commits=True,
        estimator_ids={"ls20": TABULAR_ESTIMATOR_ID},
    )


def _markdown_report(report: dict[str, Any]) -> str:
    score = report["scores"]
    bucket = score["domains"]["ls20"]
    metrics = bucket["metrics"]
    check = report["decision_check"]
    lines = [
        "# World Model Phase 2b LS20 Consistency Replication",
        "",
        f"**Decision:** `{report['decision']}`",
        "",
        "## Aggregate Evidence",
        "",
        "| Eval n | Tabular NLL | Marginal NLL | Shuffle NLL | Tabular Brier | Marginal Brier | Shuffle Brier |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {bucket['n_eval']} | {metrics['tabular']['categorical_nll']:.6f} | "
            f"{metrics['empirical_marginal_null']['categorical_nll']:.6f} | "
            f"{metrics['action_shuffle_null']['categorical_nll']:.6f} | "
            f"{metrics['tabular']['multiclass_brier']:.6f} | "
            f"{metrics['empirical_marginal_null']['multiclass_brier']:.6f} | "
            f"{metrics['action_shuffle_null']['multiclass_brier']:.6f} |"
        ),
        "",
        "## Run Evidence",
        "",
        "| Run | n | Marginal delta NLL/Brier | Shuffle delta NLL/Brier | Positive |",
        "|---|---:|---:|---:|---|",
    ]
    for run_id in sorted(score["runs"]):
        run = score["runs"][run_id]
        marginal = run["delta_marginal_minus_tabular"]
        shuffle = run["delta_null_minus_tabular"]
        positive = (
            run["n_eval"] >= DECISION_RULE["short_run_transition_threshold"]
            and all(
            run[key][metric] > 0.0
            for key in ("delta_marginal_minus_tabular", "delta_null_minus_tabular")
            for metric in ("categorical_nll", "multiclass_brier")
            )
        )
        lines.append(
            f"| {run_id} | {run['n_eval']} | "
            f"{marginal['categorical_nll']:.6f}/{marginal['multiclass_brier']:.6f} | "
            f"{shuffle['categorical_nll']:.6f}/{shuffle['multiclass_brier']:.6f} | "
            f"{'yes' if positive else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Decision Checks",
            "",
            f"Support: `{'PASS' if check['support_passed'] else 'FAIL'}`. "
            f"Micro effects: `{'PASS' if check['aggregate_effect_passed'] else 'FAIL'}`. "
            f"Run-macro effects: `{'PASS' if check['macro_effect_passed'] else 'FAIL'}`. "
            f"Consistency: `{check['positive_runs']}/{check['n_eval_runs']}` "
            f"(`{'PASS' if check['run_consistency_passed'] else 'FAIL'}`). "
            f"Short runs: `{check['short_runs']}/{check['maximum_short_runs']}` "
            f"(threshold `<{check['short_run_transition_threshold']}`).",
            "",
            "NLL is in nats. Brier is the class-summed multiclass score in `[0, 2]`. "
            "Positive deltas mean the exact v1 tabular estimator beats the named exact v1 null. "
            "A run with fewer than 16 transitions is automatically non-positive.",
            "",
            "## Boundary",
            "",
            "This scoped result addresses LS20 rollout consistency only. It does not alter the "
            "v1 result by pooling rows and does not authorize a learned observer or any runtime, "
            "bridge, Gemma, Qdrant, memory-routing, or dynamic-alpha integration.",
            "",
        ]
    )
    return "\n".join(lines)


def _json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def publish_packet(
    output: Path,
    *,
    preregistration: dict[str, Any],
    eval_freeze: dict[str, Any],
    reviewed_document: Path,
    v1_bundle: Path = V1_BUNDLE,
) -> Path:
    output = Path(output).resolve()
    reviewed_document = Path(reviewed_document).resolve()
    validate_preregistration(
        preregistration,
        reviewed_document=reviewed_document,
        v1_bundle=v1_bundle,
    )
    validate_eval_freeze(eval_freeze, preregistration=preregistration)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing freeze packet: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        artifacts = {
            "preregistration.json": _json_bytes(preregistration),
            "eval_freeze.json": _json_bytes(eval_freeze),
            "REVIEWED_SPEC.md": reviewed_document.read_bytes(),
        }
        sums: dict[str, str] = {}
        for name, data in artifacts.items():
            _write_exclusive(staging / name, data)
            digest = hashlib.sha256(data).hexdigest()
            sums[name] = digest
            _write_exclusive(staging / f"{name}.sha256", f"{digest}  {name}\n".encode("ascii"))
        _write_exclusive(staging / "SHA256SUMS.json", _json_bytes(sums))
        phase2._publish_directory_no_overwrite(staging, output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def verify_packet(
    bundle: Path,
    *,
    v1_bundle: Path = V1_BUNDLE,
    verify_code_hashes: bool = True,
) -> dict[str, str]:
    bundle = Path(bundle).resolve()
    expected_names = {
        "preregistration.json",
        "preregistration.json.sha256",
        "eval_freeze.json",
        "eval_freeze.json.sha256",
        "REVIEWED_SPEC.md",
        "REVIEWED_SPEC.md.sha256",
        "SHA256SUMS.json",
    }
    actual_names = {path.name for path in bundle.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise ValueError("freeze packet artifact inventory mismatch")
    sums = _load_json_object(bundle / "SHA256SUMS.json", field="SHA256SUMS")
    if set(sums) != {"preregistration.json", "eval_freeze.json", "REVIEWED_SPEC.md"}:
        raise ValueError("freeze packet hash inventory mismatch")
    for name, expected in sums.items():
        if file_sha256(bundle / name) != expected:
            raise ValueError(f"freeze packet artifact hash mismatch: {name}")
        sidecar = (bundle / f"{name}.sha256").read_text(encoding="ascii")
        if sidecar != f"{expected}  {name}\n":
            raise ValueError(f"freeze packet sidecar mismatch: {name}")
    preregistration = _load_json_object(
        bundle / "preregistration.json", field="preregistration"
    )
    validate_preregistration(
        preregistration,
        reviewed_document=bundle / "REVIEWED_SPEC.md",
        v1_bundle=v1_bundle,
        verify_code_hashes=verify_code_hashes,
        verify_canonical_review_document=False,
    )
    eval_freeze = _load_json_object(bundle / "eval_freeze.json", field="eval freeze")
    validate_eval_freeze(eval_freeze, preregistration=preregistration)
    return {
        "preregistration_sha256": preregistration["preregistration_sha256"],
        "eval_freeze_sha256": eval_freeze["eval_freeze_sha256"],
    }


RESULT_ARTIFACTS = {
    "preregistration.json",
    "eval_freeze.json",
    "REVIEWED_SPEC.md",
    "eval.jsonl",
    "RAW_SHA256SUMS.json",
    "report.json",
    "REPORT.md",
}


def _load_freeze_context(
    bundle: Path,
    *,
    v1_bundle: Path = V1_BUNDLE,
    verify_code_hashes: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = Path(bundle).resolve()
    preregistration = _load_json_object(
        bundle / "preregistration.json", field="preregistration"
    )
    validate_preregistration(
        preregistration,
        reviewed_document=bundle / "REVIEWED_SPEC.md",
        v1_bundle=v1_bundle,
        verify_code_hashes=verify_code_hashes,
        verify_canonical_review_document=False,
    )
    eval_freeze = _load_json_object(bundle / "eval_freeze.json", field="eval freeze")
    validate_eval_freeze(eval_freeze, preregistration=preregistration)
    return preregistration, eval_freeze


def _write_artifact_hashes(staging: Path, artifacts: set[str]) -> dict[str, str]:
    sums = {name: file_sha256(staging / name) for name in sorted(artifacts)}
    _write_exclusive(staging / "SHA256SUMS.json", _json_bytes(sums))
    for name, digest in sums.items():
        _write_exclusive(
            staging / f"{name}.sha256",
            f"{digest}  {name}\n".encode("ascii"),
        )
    return sums


def _finalize_result_staging(
    staging: Path,
    *,
    preregistration: dict[str, Any],
    eval_freeze: dict[str, Any],
    collection_environment: dict[str, Any],
    v1_bundle: Path = V1_BUNDLE,
) -> dict[str, Any]:
    estimator, _, _ = load_frozen_ls20_estimators(v1_bundle)
    pairs: list[CapturedTracePair] = []
    raw_sums: dict[str, str] = {}
    for run_spec in preregistration["run_specs"]:
        journal = phase2._journal_path(staging, run_spec)
        pairs.extend(
            _validate_ls20_journal(
                journal,
                spec=run_spec,
                eval_freeze_sha256=eval_freeze["eval_freeze_sha256"],
                estimator=estimator,
            )
        )
        raw_sums[journal.relative_to(staging).as_posix()] = file_sha256(journal)
    _write_exclusive(staging / "eval.jsonl", paired_trace_bytes(pairs))
    _write_exclusive(staging / "RAW_SHA256SUMS.json", _json_bytes(raw_sums))
    score = _reconstruct_and_score(staging / "eval.jsonl", v1_bundle=v1_bundle)
    decision, decision_check = decide(score)
    initial_artifacts = {
        name: file_sha256(staging / name)
        for name in (
            "preregistration.json",
            "eval_freeze.json",
            "REVIEWED_SPEC.md",
            "eval.jsonl",
            "RAW_SHA256SUMS.json",
        )
    }
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration_sha256": preregistration["preregistration_sha256"],
        "eval_freeze_sha256": eval_freeze["eval_freeze_sha256"],
        "review_attestation": preregistration["review_attestation"],
        "collection_environment": collection_environment,
        "artifacts": initial_artifacts,
        "raw_journal_sha256": raw_sums,
        "scores": score,
        "decision_rule": preregistration["decision_rule"],
        "analysis_contract": preregistration["analysis_contract"],
        "decision_check": decision_check,
        "decision": decision,
        "boundary": preregistration["claim_boundary"],
    }
    _write_exclusive(staging / "report.json", _json_bytes(report))
    _write_exclusive(staging / "REPORT.md", _markdown_report(report).encode("utf-8"))
    _write_artifact_hashes(staging, RESULT_ARTIFACTS)
    return report


def collect_result(
    *,
    freeze_bundle: Path,
    output: Path,
    environments_dir: Path,
    recordings_dir: Path,
    v1_bundle: Path = V1_BUNDLE,
    enforce_canonical_paths: bool = True,
) -> Path:
    """Collect the reviewed independent evaluation and atomically publish it."""
    freeze_bundle = Path(freeze_bundle).resolve()
    verify_packet(freeze_bundle, v1_bundle=v1_bundle)
    preregistration, eval_freeze = _load_freeze_context(
        freeze_bundle, v1_bundle=v1_bundle
    )
    if enforce_canonical_paths:
        expected_freeze = (REPO_ROOT / FREEZE_BUNDLE_RELATIVE).resolve()
        if freeze_bundle != expected_freeze:
            raise ValueError(f"freeze bundle must use its preregistered path: {expected_freeze}")
    actual_source = phase2._resolve_ls20_provenance(environments_dir, recordings_dir)
    if actual_source != preregistration["environment"]:
        raise RuntimeError("current LS20 package/game provenance differs from the freeze")
    output = Path(output).resolve()
    if enforce_canonical_paths:
        expected_output = (REPO_ROOT / RESULT_BUNDLE_RELATIVE).resolve()
        if output != expected_output:
            raise ValueError(f"result bundle must use its preregistered path: {expected_output}")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing result bundle: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / (
        f".{output.name}.staging-{eval_freeze['eval_freeze_sha256'][:16]}"
    )
    try:
        staging.mkdir()
    except FileExistsError as exc:
        raise FileExistsError(
            "refusing to replace retained outcome-bearing Phase 2b staging: "
            f"{staging}"
        ) from exc
    try:
        for name in ("preregistration.json", "eval_freeze.json", "REVIEWED_SPEC.md"):
            _write_exclusive(staging / name, (freeze_bundle / name).read_bytes())
        estimator, _, _ = load_frozen_ls20_estimators(v1_bundle)
        for run_spec in preregistration["run_specs"]:
            phase2.collect_ls20_run(
                staging=staging,
                spec=run_spec,
                manifest_sha256=eval_freeze["eval_freeze_sha256"],
                observer=estimator,
                environments_dir=Path(environments_dir),
                recordings_dir=Path(recordings_dir),
            )
        _finalize_result_staging(
            staging,
            preregistration=preregistration,
            eval_freeze=eval_freeze,
            collection_environment=actual_source,
            v1_bundle=v1_bundle,
        )
        verify_result(staging, v1_bundle=v1_bundle)
        phase2._publish_directory_no_overwrite(staging, output)
    except BaseException as exc:
        raise RuntimeError(
            f"Phase 2b collection failed; retained outcome-bearing staging at {staging}"
        ) from exc
    verify_result(output, v1_bundle=v1_bundle)
    return output


def verify_result(
    bundle: Path,
    *,
    v1_bundle: Path = V1_BUNDLE,
    verify_code_hashes: bool = True,
) -> dict[str, Any]:
    bundle = Path(bundle).resolve()
    expected_files = (
        RESULT_ARTIFACTS
        | {f"{name}.sha256" for name in RESULT_ARTIFACTS}
        | {"SHA256SUMS.json"}
    )
    actual_files = {path.name for path in bundle.iterdir() if path.is_file()}
    if actual_files != expected_files:
        raise ValueError("result artifact inventory mismatch")
    sums = _load_json_object(bundle / "SHA256SUMS.json", field="SHA256SUMS")
    if set(sums) != RESULT_ARTIFACTS:
        raise ValueError("result hash inventory mismatch")
    for name, expected in sums.items():
        if file_sha256(bundle / name) != expected:
            raise ValueError(f"result artifact hash mismatch: {name}")
        if (bundle / f"{name}.sha256").read_text(encoding="ascii") != (
            f"{expected}  {name}\n"
        ):
            raise ValueError(f"result artifact sidecar mismatch: {name}")
    preregistration, eval_freeze = _load_freeze_context(
        bundle,
        v1_bundle=v1_bundle,
        verify_code_hashes=verify_code_hashes,
    )
    estimator, _, _ = load_frozen_ls20_estimators(v1_bundle)
    expected_journals = {
        phase2._journal_path(bundle, run_spec).resolve()
        for run_spec in preregistration["run_specs"]
    }
    actual_journals = {
        path.resolve() for path in (bundle / "raw").rglob("*.journal.jsonl")
    }
    if actual_journals != expected_journals:
        raise ValueError("raw journal inventory differs from the frozen run specs")
    raw_sums = _load_json_object(bundle / "RAW_SHA256SUMS.json", field="raw sums")
    expected_raw_names = {
        path.relative_to(bundle).as_posix() for path in expected_journals
    }
    if set(raw_sums) != expected_raw_names:
        raise ValueError("raw journal hash inventory mismatch")
    pairs: list[CapturedTracePair] = []
    for run_spec in preregistration["run_specs"]:
        journal = phase2._journal_path(bundle, run_spec)
        relative = journal.relative_to(bundle).as_posix()
        if file_sha256(journal) != raw_sums[relative]:
            raise ValueError(f"raw journal hash mismatch: {relative}")
        pairs.extend(
            _validate_ls20_journal(
                journal,
                spec=run_spec,
                eval_freeze_sha256=eval_freeze["eval_freeze_sha256"],
                estimator=estimator,
            )
        )
    if (bundle / "eval.jsonl").read_bytes() != paired_trace_bytes(pairs):
        raise ValueError("eval trace is not the canonical raw-journal materialization")
    score = _reconstruct_and_score(bundle / "eval.jsonl", v1_bundle=v1_bundle)
    decision, decision_check = decide(score)
    report = _load_json_object(bundle / "report.json", field="report")
    expected_report_fields = {
        "schema_version",
        "collected_at_utc",
        "preregistration_sha256",
        "eval_freeze_sha256",
        "review_attestation",
        "collection_environment",
        "artifacts",
        "raw_journal_sha256",
        "scores",
        "decision_rule",
        "analysis_contract",
        "decision_check",
        "decision",
        "boundary",
    }
    if set(report) != expected_report_fields or report["schema_version"] != REPORT_SCHEMA_VERSION:
        raise ValueError("result report fields or schema mismatch")
    _validate_utc_timestamp(report["collected_at_utc"], field="collected_at_utc")
    if report["preregistration_sha256"] != preregistration["preregistration_sha256"]:
        raise ValueError("result report preregistration identity mismatch")
    if report["eval_freeze_sha256"] != eval_freeze["eval_freeze_sha256"]:
        raise ValueError("result report eval-freeze identity mismatch")
    if report["review_attestation"] != preregistration["review_attestation"]:
        raise ValueError("result report review attestation mismatch")
    if report["collection_environment"] != preregistration["environment"]:
        raise ValueError("result report environment mismatch")
    expected_initial_artifacts = {
        name: sums[name]
        for name in (
            "preregistration.json",
            "eval_freeze.json",
            "REVIEWED_SPEC.md",
            "eval.jsonl",
            "RAW_SHA256SUMS.json",
        )
    }
    if report["artifacts"] != expected_initial_artifacts:
        raise ValueError("result report artifact identities mismatch")
    if report["raw_journal_sha256"] != raw_sums:
        raise ValueError("result report raw-journal identities mismatch")
    if (
        report["scores"] != score
        or report["decision_rule"] != preregistration["decision_rule"]
        or report["analysis_contract"] != preregistration["analysis_contract"]
        or report["decision_check"] != decision_check
        or report["decision"] != decision
        or report["boundary"] != preregistration["claim_boundary"]
    ):
        raise ValueError("result report scoring or decision mismatch")
    if (bundle / "REPORT.md").read_text(encoding="utf-8") != _markdown_report(report):
        raise ValueError("Markdown report does not reproduce from report.json")
    return {
        "ok": True,
        "preregistration_sha256": preregistration["preregistration_sha256"],
        "eval_freeze_sha256": eval_freeze["eval_freeze_sha256"],
        "n_eval": score["n_eval"],
        "positive_runs": decision_check["positive_runs"],
        "decision": decision,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="publish an approved no-outcome freeze")
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--review-message-id", type=int, required=True)
    prepare.add_argument("--reviewed-at-utc", required=True)
    prepare.add_argument(
        "--review-disposition",
        choices=("approved", "approved_with_changes_resolved"),
        required=True,
    )
    prepare.add_argument("--review-note", default="")
    prepare.add_argument("--review-document", type=Path, default=REVIEW_DOCUMENT)
    verify = subparsers.add_parser("verify", help="verify a published freeze packet")
    verify.add_argument("--bundle", type=Path, required=True)
    collect = subparsers.add_parser(
        "collect", help="collect the reviewed independent LS20 evaluation"
    )
    collect.add_argument("--freeze", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--arc-environments-dir", type=Path, required=True)
    collect.add_argument("--arc-recordings-dir", type=Path, required=True)
    verify_result_parser = subparsers.add_parser(
        "verify-result", help="verify a published Phase 2b result bundle"
    )
    verify_result_parser.add_argument("--bundle", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.command == "prepare":
        expected_output = (REPO_ROOT / FREEZE_BUNDLE_RELATIVE).resolve()
        if args.output.resolve() != expected_output:
            parser.error(f"freeze packet must use its preregistered path: {expected_output}")
        document = args.review_document.resolve()
        attestation = {
            "reviewer": "isegrim",
            "disposition": args.review_disposition,
            "watercooler_message_id": args.review_message_id,
            "reviewed_at_utc": args.reviewed_at_utc,
            "reviewed_document_path": document.relative_to(REPO_ROOT).as_posix(),
            "reviewed_document_sha256": file_sha256(document),
            "note": args.review_note,
        }
        created_at = datetime.now(timezone.utc).isoformat()
        preregistration = build_preregistration(
            attestation,
            reviewed_document=document,
            created_at_utc=created_at,
        )
        eval_freeze = build_eval_freeze(preregistration)
        output = publish_packet(
            args.output,
            preregistration=preregistration,
            eval_freeze=eval_freeze,
            reviewed_document=document,
        )
        result = verify_packet(output)
        print(json.dumps({"bundle": str(output), **result}, indent=2, sort_keys=True))
        return 0
    if args.command == "verify":
        result = verify_packet(args.bundle)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "collect":
        output = collect_result(
            freeze_bundle=args.freeze,
            output=args.output,
            environments_dir=args.arc_environments_dir,
            recordings_dir=args.arc_recordings_dir,
        )
        result = verify_result(output)
        print(json.dumps({"bundle": str(output), **result}, indent=2, sort_keys=True))
        return 0
    result = verify_result(args.bundle)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
