#!/usr/bin/env python3
"""Collect and score immutable real LS20/tool transition traces.

This is an offline sidecar. It never imports a model runtime, writes Qdrant,
changes bridge loss/dose, or selects an online action from a prediction.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib.metadata
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable

import numpy as np


BRIDGE_DIR = Path(__file__).resolve().parents[1]
SPIKES_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
for import_path in (BRIDGE_DIR, SPIKES_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import score_world_model_trace as scorer  # noqa: E402
from world_model_baselines import (  # noqa: E402
    DeterministicActionShuffleNull,
    DirichletTabularEstimator,
    EmpiricalMarginalEstimator,
)
from world_model_capture import (  # noqa: E402
    CapturedTracePair,
    DurableTraceJournal,
    canonical_action,
    load_journal,
    paired_trace_bytes,
)
from world_model_trace import NullWorldModelObserver, canonical_sha256  # noqa: E402


MANIFEST_SCHEMA_VERSION = "world-model-phase2-manifest-v1"
BASELINE_SCHEMA_VERSION = "world-model-phase2-baselines-v1"
EVAL_FREEZE_SCHEMA_VERSION = "world-model-phase2-eval-freeze-v1"
REPORT_SCHEMA_VERSION = "world-model-phase2-report-v1"
COLLECTOR_VERSION = "world-model-phase2-collector-v1"
EXPECTED_ARC_AGI_VERSION = "0.9.8"
EXPECTED_ARCENGINE_VERSION = "0.9.3"

LS20_ACTION_NAMES = ("ACTION1", "ACTION2", "ACTION3", "ACTION4")
LS20_ACTION_SPACE = tuple(canonical_action(name) for name in LS20_ACTION_NAMES)
LS20_OBSERVATION_SPACE = (
    "avatar_blocked",
    "avatar_moved",
    "level_advanced",
    "terminal_game_over",
    "terminal_win",
)
TOOL_ACTION_SPECS = (
    ("read_text", {"path": "present.txt"}),
    ("read_text", {"path": "missing.txt"}),
)
TOOL_ACTION_SPACE = tuple(canonical_action(name, arguments) for name, arguments in TOOL_ACTION_SPECS)
TOOL_OBSERVATION_SPACE = ("not_found", "success", "timeout", "tool_error")
PROHIBITED_INTEGRATIONS = (
    "bridge_loss",
    "gemma_dose",
    "online_action_selection",
    "qdrant_write",
    "memory_routing",
    "dynamic_alpha",
)
MIN_NLL_IMPROVEMENT_NATS = 0.02
MIN_SUM_BRIER_IMPROVEMENT = 0.01
MIN_POSITIVE_RUN_FRACTION = 0.75
MIN_ACTUAL_TRANSITIONS = {
    "train": {"ls20": 192, "tool": 48},
    "eval": {"ls20": 96, "tool": 24},
}
MIN_TRANSITIONS_PER_EVAL_RUN = {"ls20": 16, "tool": 4}
MIN_TRAIN_ACTION_COUNT = {"ls20": 8, "tool": 8}
MIN_TRAIN_STATE_ACTION_CELLS = {"ls20": 4, "tool": 2}
ATTESTATION_CONTRACT = {
    "level": "internal_consistency_only",
    "external_registration": "not_performed",
    "verifier_claim": (
        "hash_order_protocol_consistency_not_independent_third_party_attestation"
    ),
}

DECLARED_ACTION_SPACES = {
    "ls20": LS20_ACTION_SPACE,
    "tool": TOOL_ACTION_SPACE,
}
DECLARED_OBSERVATION_SPACES = {
    "ls20": LS20_OBSERVATION_SPACE,
    "tool": TOOL_OBSERVATION_SPACE,
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _distribution_tree_sha256(distribution_name: str) -> str:
    distribution = importlib.metadata.distribution(distribution_name)
    rows = []
    for relative in sorted(distribution.files or (), key=lambda path: path.as_posix()):
        path = Path(distribution.locate_file(relative))
        if path.is_file():
            rows.append(
                {
                    "path": relative.as_posix(),
                    "sha256": file_sha256(path),
                }
            )
    if not rows:
        raise RuntimeError(f"distribution {distribution_name!r} has no hashable files")
    return canonical_sha256(rows)


def _write_durable(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json_durable(path: Path, payload: Any) -> None:
    data = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    _write_durable(path, data)


def _publish_directory_no_overwrite(staging: Path, output: Path) -> None:
    """Atomically publish a directory without replacing an existing path."""
    staging = Path(staging).resolve()
    output = Path(output).resolve()
    if os.name == "nt":
        os.rename(staging, output)
        return
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise RuntimeError("atomic no-replace publication requires renameat2 on Linux")
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100,
            os.fsencode(staging),
            -100,
            os.fsencode(output),
            1,
        )
        if result != 0:
            error = ctypes.get_errno()
            if error == errno.EEXIST:
                raise FileExistsError(f"refusing to overwrite existing output bundle: {output}")
            raise OSError(error, os.strerror(error), str(output))
        return
    raise RuntimeError("atomic no-replace directory publication is unsupported on this platform")


def _git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
        shell=False,
    )
    return result.stdout.strip()


def _code_hashes() -> dict[str, str]:
    paths = (
        BRIDGE_DIR / "world_model_trace.py",
        BRIDGE_DIR / "world_model_baselines.py",
        BRIDGE_DIR / "world_model_capture.py",
        SPIKES_DIR / "score_world_model_trace.py",
        SPIKES_DIR / "collect_world_model_phase2.py",
        SPIKES_DIR / "world_model_tool_probe.py",
    )
    return {str(path.relative_to(REPO_ROOT)).replace("\\", "/"): file_sha256(path) for path in paths}


def _action_sequence(domain: str, *, seed: int, steps: int) -> list[str]:
    rng = random.Random(seed)
    if domain == "ls20":
        return [rng.choice(LS20_ACTION_SPACE) for _ in range(steps)]
    actions = [action for action in TOOL_ACTION_SPACE for _ in range(steps // 2)]
    while len(actions) < steps:
        actions.append(TOOL_ACTION_SPACE[len(actions) % len(TOOL_ACTION_SPACE)])
    rng.shuffle(actions)
    return actions


def build_run_specs(
    *,
    train_ls20_runs: int,
    eval_ls20_runs: int,
    train_tool_runs: int,
    eval_tool_runs: int,
    ls20_steps: int,
    tool_steps: int,
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    counts = {
        ("train", "ls20"): train_ls20_runs,
        ("eval", "ls20"): eval_ls20_runs,
        ("train", "tool"): train_tool_runs,
        ("eval", "tool"): eval_tool_runs,
    }
    seed_base = {("train", "ls20"): 1100, ("eval", "ls20"): 2100, ("train", "tool"): 3100, ("eval", "tool"): 4100}
    for (split, domain), count in counts.items():
        steps = ls20_steps if domain == "ls20" else tool_steps
        for index in range(count):
            run_id = f"phase2-{domain}-{split}-{index:03d}"
            policy_seed = seed_base[(split, domain)] + index
            specs.append(
                {
                    "run_id": run_id,
                    "split": split,
                    "domain": domain,
                    "episode_id": f"episode:{run_id}",
                    "source_group_id": f"source-group:{run_id}",
                    "environment_seed": policy_seed,
                    "policy_seed": policy_seed,
                    "planned_steps": steps,
                    "action_sequence": _action_sequence(domain, seed=policy_seed, steps=steps),
                }
            )
    return specs


def _frame_payload(frame: Any) -> dict[str, Any]:
    array = np.asarray(frame)
    if array.ndim != 2:
        raise ValueError(f"LS20 frame must be rank 2, got shape {array.shape}")
    return {
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "values": array.astype(int).tolist(),
    }


def ls20_observation_payload(observation: Any) -> dict[str, Any]:
    action_input = observation.action_input
    payload = {
        "game_id": observation.game_id,
        "guid": observation.guid,
        "state": observation.state.name,
        "levels_completed": int(observation.levels_completed),
        "win_levels": int(observation.win_levels),
        "full_reset": bool(observation.full_reset),
        "available_actions": [int(action) for action in observation.available_actions],
        "previous_action": {
            "id": action_input.id.name,
            "data": dict(action_input.data),
            "reasoning": action_input.reasoning,
        },
        "frames": [_frame_payload(frame) for frame in observation.frame],
    }
    validate_ls20_observation_payload(payload)
    return payload


def validate_ls20_observation_payload(
    payload: Any, *, expected_game_id: str | None = None
) -> None:
    fields = {
        "game_id",
        "guid",
        "state",
        "levels_completed",
        "win_levels",
        "full_reset",
        "available_actions",
        "previous_action",
        "frames",
    }
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError("LS20 observation fields mismatch")
    if (
        not isinstance(payload["game_id"], str)
        or not payload["game_id"].startswith("ls20-")
        or (expected_game_id is not None and payload["game_id"] != expected_game_id)
        or not isinstance(payload["guid"], str)
        or not payload["guid"].strip()
        or payload["state"] not in {"NOT_FINISHED", "WIN", "GAME_OVER"}
        or any(
            not isinstance(payload[field], int)
            or isinstance(payload[field], bool)
            or payload[field] < 0
            for field in ("levels_completed", "win_levels")
        )
        or not isinstance(payload["full_reset"], bool)
        or payload["available_actions"] != [1, 2, 3, 4]
    ):
        raise ValueError("LS20 observation identity/state contract mismatch")
    previous_action = payload["previous_action"]
    if (
        not isinstance(previous_action, dict)
        or set(previous_action) != {"id", "data", "reasoning"}
        or previous_action["id"] not in {"RESET", *LS20_ACTION_NAMES}
        or not isinstance(previous_action["data"], dict)
        or previous_action["reasoning"] is not None
    ):
        raise ValueError("LS20 previous-action contract mismatch")
    frames = payload["frames"]
    if not isinstance(frames, list) or not frames:
        raise ValueError("LS20 observation must contain at least one frame")
    for frame in frames:
        if (
            not isinstance(frame, dict)
            or set(frame) != {"dtype", "shape", "values"}
            or frame["dtype"] not in {"int8", "uint8"}
            or frame["shape"] != [64, 64]
            or not isinstance(frame["values"], list)
            or len(frame["values"]) != 64
            or any(
                not isinstance(row, list)
                or len(row) != 64
                or any(
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or not 0 <= value <= 15
                    for value in row
                )
                for row in frame["values"]
            )
        ):
            raise ValueError("LS20 frame schema/content mismatch")


def _avatar_anchor(payload: dict[str, Any]) -> tuple[int, int]:
    frame = np.asarray(payload["frames"][-1]["values"], dtype=np.int16)
    coords = np.argwhere(frame == 12)
    if coords.shape != (10, 2):
        raise ValueError(f"LS20 avatar extractor expected 10 orange pixels, got {len(coords)}")
    minimum = coords.min(axis=0)
    maximum = coords.max(axis=0)
    if tuple((maximum - minimum + 1).tolist()) != (2, 5):
        raise ValueError("LS20 avatar extractor expected a 2x5 orange anchor")
    return int(minimum[0]), int(minimum[1])


def ls20_state_ref(payload: dict[str, Any]) -> str:
    frame = np.asarray(payload["frames"][-1]["values"], dtype=np.int16)
    row, column = _avatar_anchor(payload)
    masks: list[str] = []
    for delta_row, delta_column in ((-5, 0), (5, 0), (0, -5), (0, 5)):
        target = frame[
            row + delta_row : row + delta_row + 2,
            column + delta_column : column + delta_column + 5,
        ]
        masks.append("1" if target.shape == (2, 5) and np.all(target == 3) else "0")
    return (
        "ls20-avatar-mask-v1:"
        f"state={payload['state']}:level={payload['levels_completed']}:mask={''.join(masks)}"
    )


def classify_ls20_outcome(pre: dict[str, Any], post: dict[str, Any]) -> str:
    if post["state"] == "WIN":
        return "terminal_win"
    if post["state"] == "GAME_OVER":
        return "terminal_game_over"
    if post["levels_completed"] > pre["levels_completed"]:
        return "level_advanced"
    return "avatar_moved" if _avatar_anchor(pre) != _avatar_anchor(post) else "avatar_blocked"


def _tool_files_payload(sandbox: Path) -> dict[str, Any]:
    rows = []
    for name in ("present.txt", "missing.txt"):
        path = sandbox / name
        rows.append(
            {
                "path": name,
                "exists": path.is_file(),
                "sha256": file_sha256(path) if path.is_file() else None,
                "text_sha256": (
                    hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                    if path.is_file()
                    else None
                ),
            }
        )
    return {"files": rows}


def tool_state_ref(payload: dict[str, Any]) -> str:
    bits = "".join("1" if row["exists"] else "0" for row in payload["files"])
    return f"tool-sandbox-v1:presence={bits}"


def tool_subprocess_environment() -> dict[str, str]:
    allowed = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    environment.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    return environment


def run_tool_action(
    *,
    python_executable: Path,
    sandbox: Path,
    action: str,
    timeout_seconds: float,
) -> tuple[str, dict[str, Any]]:
    action_payload = json.loads(action)
    if set(action_payload) != {"arguments", "name"} or action_payload["name"] != "read_text":
        raise ValueError("unknown tool action")
    arguments = action_payload["arguments"]
    if set(arguments) != {"path"} or arguments["path"] not in {"present.txt", "missing.txt"}:
        raise ValueError("tool action path is outside the frozen action space")
    argv = [
        str(python_executable),
        "-I",
        str(SPIKES_DIR / "world_model_tool_probe.py"),
        "--read-text",
        arguments["path"],
    ]
    environment = tool_subprocess_environment()
    try:
        completed = subprocess.run(
            argv,
            cwd=sandbox,
            text=True,
            capture_output=True,
            check=False,
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=timeout_seconds,
            env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        return "timeout", {
            "argv": argv,
            "timeout_seconds": timeout_seconds,
            "timed_out": True,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "shell": False,
            "stdin": "DEVNULL",
            "environment_keys": sorted(environment),
        }
    result_payload = {
        "argv": argv,
        "timeout_seconds": timeout_seconds,
        "timed_out": False,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "shell": False,
        "stdin": "DEVNULL",
        "environment_keys": sorted(environment),
    }
    return classify_tool_result(result_payload), result_payload


def classify_tool_result(payload: dict[str, Any]) -> str:
    if payload["timed_out"]:
        return "timeout"
    if payload["returncode"] == 0:
        return "success"
    if payload["returncode"] == 2 and payload["stderr"].strip() == "not_found":
        return "not_found"
    return "tool_error"


def _journal_path(staging: Path, spec: dict[str, Any]) -> Path:
    return staging / "raw" / spec["split"] / spec["domain"] / f"{spec['run_id']}.journal.jsonl"


def collect_tool_run(
    *,
    staging: Path,
    spec: dict[str, Any],
    manifest_sha256: str,
    observer: Any,
    python_executable: Path,
    timeout_seconds: float,
) -> Path:
    sandbox = staging / "sandboxes" / spec["run_id"]
    sandbox.mkdir(parents=True, exist_ok=False)
    (sandbox / "present.txt").write_text(f"real-tool-source:{spec['run_id']}\n", encoding="utf-8")
    journal = DurableTraceJournal(_journal_path(staging, spec), manifest_sha256=manifest_sha256)
    for step_index, action in enumerate(spec["action_sequence"]):
        pre_payload = {
            "collector": COLLECTOR_VERSION,
            "source_group_id": spec["source_group_id"],
            **_tool_files_payload(sandbox),
        }
        pending = journal.begin(
            observer=observer,
            run_id=spec["run_id"],
            domain="tool",
            episode_id=spec["episode_id"],
            step_index=step_index,
            state_ref=tool_state_ref(pre_payload),
            action=action,
            state_source_kind="tool_context",
            state_source_id=f"{spec['source_group_id']}:pre:{step_index}",
            state_source_payload=pre_payload,
        )
        observation, result_payload = run_tool_action(
            python_executable=python_executable,
            sandbox=sandbox,
            action=action,
            timeout_seconds=timeout_seconds,
        )
        journal.finish(
            pending,
            observation=observation,
            outcome_source_kind="tool_result",
            outcome_source_id=f"{spec['source_group_id']}:post:{step_index}",
            outcome_source_payload={
                "collector": COLLECTOR_VERSION,
                "source_group_id": spec["source_group_id"],
                **result_payload,
            },
        )
    return journal.path


def collect_ls20_run(
    *,
    staging: Path,
    spec: dict[str, Any],
    manifest_sha256: str,
    observer: Any,
    environments_dir: Path,
    recordings_dir: Path,
) -> Path:
    from arc_agi import Arcade, OperationMode
    from arcengine import GameAction

    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environments_dir),
        recordings_dir=str(recordings_dir),
    )
    environment = arcade.make("ls20", seed=spec["environment_seed"])
    if environment is None or not environment.info.game_id.startswith("ls20-"):
        raise RuntimeError("official LS20 environment could not be created")
    observation = environment.reset()
    if observation is None:
        raise RuntimeError("official LS20 reset returned no observation")
    journal = DurableTraceJournal(_journal_path(staging, spec), manifest_sha256=manifest_sha256)
    for step_index, action in enumerate(spec["action_sequence"]):
        action_name = json.loads(action)["name"]
        pre_payload = {
            "collector": COLLECTOR_VERSION,
            "source_group_id": spec["source_group_id"],
            "environment_seed": spec["environment_seed"],
            "observation": ls20_observation_payload(observation),
        }
        if int(GameAction[action_name].value) not in observation.available_actions:
            raise RuntimeError(f"manifest action {action_name} is not legal at step {step_index}")
        pending = journal.begin(
            observer=observer,
            run_id=spec["run_id"],
            domain="ls20",
            episode_id=spec["episode_id"],
            step_index=step_index,
            state_ref=ls20_state_ref(pre_payload["observation"]),
            action=action,
            state_source_kind="environment",
            state_source_id=f"{spec['source_group_id']}:pre:{step_index}",
            state_source_payload=pre_payload,
        )
        next_observation = environment.step(GameAction[action_name])
        if next_observation is None:
            raise RuntimeError(f"official LS20 step {step_index} returned no observation")
        post_payload = {
            "collector": COLLECTOR_VERSION,
            "source_group_id": spec["source_group_id"],
            "environment_seed": spec["environment_seed"],
            "observation": ls20_observation_payload(next_observation),
        }
        label = classify_ls20_outcome(pre_payload["observation"], post_payload["observation"])
        journal.finish(
            pending,
            observation=label,
            outcome_source_kind="environment",
            outcome_source_id=f"{spec['source_group_id']}:post:{step_index}",
            outcome_source_payload=post_payload,
        )
        observation = next_observation
        if label in {"terminal_game_over", "terminal_win"}:
            break
    return journal.path


def _materialize_split(
    *,
    staging: Path,
    specs: Iterable[dict[str, Any]],
    manifest_sha256: str,
    output_name: str,
) -> tuple[Path, list[CapturedTracePair]]:
    pairs: list[CapturedTracePair] = []
    for spec in specs:
        pairs.extend(
            load_journal(
                _journal_path(staging, spec), expected_manifest_sha256=manifest_sha256
            )
        )
    output = staging / output_name
    _write_durable(output, paired_trace_bytes(pairs))
    return output, pairs


def fit_frozen_baselines(
    pairs: list[CapturedTracePair],
    *,
    alpha: float,
    train_trace_sha256: str,
    shuffle_seed: str,
    manifest_sha256: str,
) -> tuple[dict[str, Any], dict[str, DirichletTabularEstimator]]:
    estimators: dict[str, DirichletTabularEstimator] = {}
    domains_payload: dict[str, Any] = {}
    for domain in sorted(DECLARED_ACTION_SPACES):
        estimator_id = f"dirichlet-tabular-v1:{domain}:{train_trace_sha256[:16]}"
        estimator = DirichletTabularEstimator(
            DECLARED_OBSERVATION_SPACES[domain],
            alpha=alpha,
            estimator_id=estimator_id,
        )
        marginal = EmpiricalMarginalEstimator(
            DECLARED_OBSERVATION_SPACES[domain],
            alpha=alpha,
            estimator_id=f"empirical-marginal-null-v1:{domain}:{train_trace_sha256[:16]}",
        )
        for pair in pairs:
            if pair.commit.domain != domain:
                continue
            if pair.commit.status != "not_collected" or pair.commit.estimator_kind != "null":
                raise ValueError("training capture must contain only null pre-action commits")
            if pair.outcome.observation not in DECLARED_OBSERVATION_SPACES[domain]:
                raise ValueError("training outcome is outside the frozen observation space")
            estimator.update(pair.commit.state_ref, pair.commit.action, pair.outcome.observation)
            marginal.update(pair.outcome.observation)
        shuffle = DeterministicActionShuffleNull(
            estimator,
            DECLARED_ACTION_SPACES[domain],
            seed=f"{shuffle_seed}:{domain}",
        )
        domains_payload[domain] = {
            "action_space": list(DECLARED_ACTION_SPACES[domain]),
            "observation_space": list(DECLARED_OBSERVATION_SPACES[domain]),
            "state_ref_extractor": (
                "ls20-avatar-mask-v1" if domain == "ls20" else "tool-sandbox-v1"
            ),
            "tabular": estimator.canonical_payload(),
            "empirical_marginal_null": marginal.canonical_payload(),
            "action_shuffle_null": {
                "estimator_id": shuffle.estimator_id,
                "seed": f"{shuffle_seed}:{domain}",
                "mapping": shuffle.action_mapping,
            },
        }
        estimators[domain] = estimator
    payload_without_hash = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "manifest_sha256": manifest_sha256,
        "train_trace_sha256": train_trace_sha256,
        "alpha": alpha,
        "shuffle_seed": shuffle_seed,
        "domains": domains_payload,
    }
    payload = {
        **payload_without_hash,
        "baseline_bundle_sha256": canonical_sha256(payload_without_hash),
    }
    return payload, estimators


def _validate_eval_commits(
    pairs: list[CapturedTracePair], estimators: dict[str, DirichletTabularEstimator]
) -> None:
    for pair in pairs:
        commit = pair.commit
        if commit.status != "committed" or commit.estimator_kind != "baseline":
            raise ValueError("evaluation capture lacks a committed train-frozen prediction")
        estimator = estimators[commit.domain]
        if commit.estimator_id != estimator.estimator_id:
            raise ValueError("evaluation estimator identity mismatch")
        if commit.probabilities != estimator.predict(commit.state_ref, commit.action):
            raise ValueError("evaluation prediction does not match the frozen estimator")


def _decision(score: dict[str, Any], decision_rule: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    domain_checks: dict[str, Any] = {}
    for domain, minimum_eval in decision_rule["min_eval_transitions"].items():
        bucket = score["domains"][domain]
        deltas = {
            "marginal": bucket["delta_marginal_minus_tabular"],
            "shuffle": bucket["delta_null_minus_tabular"],
        }
        run_buckets = [
            run_bucket
            for run_bucket in score["runs"].values()
            if run_bucket["domain"] == domain
        ]
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
        training = score["training_support"][domain]
        minimum_run_length = decision_rule["min_transitions_per_eval_run"][domain]
        support_passed = (
            training["n_train"] >= decision_rule["min_train_transitions"][domain]
            and bucket["n_eval"] >= minimum_eval
            and len(run_buckets) >= decision_rule["min_eval_runs"][domain]
            and all(run_bucket["n_eval"] >= minimum_run_length for run_bucket in run_buckets)
            and min(training["action_counts"].values())
            >= decision_rule["min_train_action_count"][domain]
            and training["n_state_action_cells"]
            >= decision_rule["min_train_state_action_cells"][domain]
        )
        aggregate_effect_passed = all(
            delta["categorical_nll"] >= decision_rule["min_nll_improvement_nats"]
            and delta["multiclass_brier"] >= decision_rule["min_brier_improvement"]
            for delta in deltas.values()
        )
        macro_effect_passed = all(
            delta["categorical_nll"] >= decision_rule["min_nll_improvement_nats"]
            and delta["multiclass_brier"] >= decision_rule["min_brier_improvement"]
            for delta in macro_deltas.values()
        )
        positive_runs = sum(
            all(
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
            positive_fraction >= decision_rule["min_positive_run_fraction"]
        )
        passed = (
            support_passed
            and aggregate_effect_passed
            and macro_effect_passed
            and run_consistency_passed
        )
        predictive_failure = support_passed and all(
            value <= 0.0
            for source in (deltas, macro_deltas)
            for delta in source.values()
            for value in delta.values()
        )
        if not support_passed:
            failure_class = "insufficient_evidence"
        elif predictive_failure:
            failure_class = "predictive_failure"
        elif aggregate_effect_passed and macro_effect_passed and not run_consistency_passed:
            failure_class = "run_inconsistent"
        elif not passed:
            failure_class = "effect_gate_failed"
        else:
            failure_class = None
        domain_checks[domain] = {
            "passed": passed,
            "failure_class": failure_class,
            "support_passed": support_passed,
            "aggregate_effect_passed": aggregate_effect_passed,
            "macro_effect_passed": macro_effect_passed,
            "run_consistency_passed": run_consistency_passed,
            "n_train": training["n_train"],
            "minimum_n_train": decision_rule["min_train_transitions"][domain],
            "n_eval": bucket["n_eval"],
            "minimum_n_eval": minimum_eval,
            "n_eval_runs": len(run_buckets),
            "minimum_eval_runs": decision_rule["min_eval_runs"][domain],
            "minimum_transitions_per_eval_run": minimum_run_length,
            "eval_run_lengths": [run_bucket["n_eval"] for run_bucket in run_buckets],
            "train_action_counts": training["action_counts"],
            "minimum_train_action_count": decision_rule["min_train_action_count"][domain],
            "train_state_action_cells": training["n_state_action_cells"],
            "minimum_train_state_action_cells": decision_rule[
                "min_train_state_action_cells"
            ][domain],
            "positive_runs": positive_runs,
            "positive_run_fraction": positive_fraction,
            "minimum_positive_run_fraction": decision_rule["min_positive_run_fraction"],
            "micro_deltas": deltas,
            "macro_run_deltas": macro_deltas,
        }
    failure_classes = {check["failure_class"] for check in domain_checks.values() if not check["passed"]}
    if not failure_classes:
        decision = "GO_OFFLINE_LEARNED_OBSERVER_PROTOTYPE"
    elif "insufficient_evidence" in failure_classes:
        decision = "NO_GO_INSUFFICIENT_EVIDENCE"
    elif "predictive_failure" in failure_classes:
        decision = "NO_GO_PREDICTIVE_FAILURE"
    elif "run_inconsistent" in failure_classes:
        decision = "NO_GO_RUN_INCONSISTENT"
    else:
        decision = "NO_GO_EFFECT_GATE_FAILED"
    return decision, domain_checks


def _markdown_report(report: dict[str, Any]) -> str:
    if report["decision"] == "GO_OFFLINE_LEARNED_OBSERVER_PROTOTYPE":
        boundary_text = (
            "This GO authorizes at most a later offline learned-observer prototype."
        )
    else:
        boundary_text = (
            "This NO-GO does not authorize an offline learned-observer prototype."
        )
    lines = [
        "# World Model Phase 2 Real-Trace Report",
        "",
        f"**Decision:** `{report['decision']}`",
        "",
        "## Evidence",
        "",
        "| Domain | Eval n | Tabular NLL | Marginal NLL | Shuffle NLL | Tabular Brier | Marginal Brier | Shuffle Brier |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for domain, bucket in report["scores"]["domains"].items():
        metrics = bucket["metrics"]
        lines.append(
            f"| {domain} | {bucket['n_eval']} | "
            f"{metrics['tabular']['categorical_nll']:.6f} | "
            f"{metrics['empirical_marginal_null']['categorical_nll']:.6f} | "
            f"{metrics['action_shuffle_null']['categorical_nll']:.6f} | "
            f"{metrics['tabular']['multiclass_brier']:.6f} | "
            f"{metrics['empirical_marginal_null']['multiclass_brier']:.6f} | "
            f"{metrics['action_shuffle_null']['multiclass_brier']:.6f} |"
        )
    rule = report["decision_rule"]
    lines.extend(
        [
            "",
            "Multiclass Brier is the class-summed score "
            "`sum_k (p_k - 1[k == observed])^2` in `[0, 2]`; lower is better. "
            "NLL is measured in nats. Positive deltas below mean the tabular model "
            "beats the corresponding null.",
            "",
            "## Decision Checks",
            "",
            "| Domain | Train n/min | Eval n/min | Runs/min | Min run n/min | Min action n/min | Cells/min | Worst micro delta NLL/Brier | Worst run-macro delta NLL/Brier | Positive runs | Result |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for domain, check in report["decision_checks"].items():
        minimum_action_count = min(check["train_action_counts"].values())
        minimum_run_length = min(check["eval_run_lengths"], default=0)
        worst_micro_nll = min(
            delta["categorical_nll"] for delta in check["micro_deltas"].values()
        )
        worst_micro_brier = min(
            delta["multiclass_brier"] for delta in check["micro_deltas"].values()
        )
        worst_macro_nll = min(
            delta["categorical_nll"]
            for delta in check["macro_run_deltas"].values()
        )
        worst_macro_brier = min(
            delta["multiclass_brier"]
            for delta in check["macro_run_deltas"].values()
        )
        lines.append(
            f"| {domain} | {check['n_train']}/{check['minimum_n_train']} | "
            f"{check['n_eval']}/{check['minimum_n_eval']} | "
            f"{check['n_eval_runs']}/{check['minimum_eval_runs']} | "
            f"{minimum_run_length}/{check['minimum_transitions_per_eval_run']} | "
            f"{minimum_action_count}/{check['minimum_train_action_count']} | "
            f"{check['train_state_action_cells']}/"
            f"{check['minimum_train_state_action_cells']} | "
            f"{worst_micro_nll:.6f}/{worst_micro_brier:.6f} | "
            f"{worst_macro_nll:.6f}/{worst_macro_brier:.6f} | "
            f"{check['positive_runs']}/{check['n_eval_runs']} "
            f"({check['positive_run_fraction']:.3f}) | "
            f"{'PASS' if check['passed'] else check['failure_class']} |"
        )
    lines.extend(
        [
            "",
            "A domain passes only when realized train/eval support and per-run length "
            "meet their preregistered minima; both transition-micro and run-macro "
            f"improvements are at least {rule['min_nll_improvement_nats']:.3f} nats "
            f"NLL and {rule['min_brier_improvement']:.3f} class-summed Brier against "
            "both nulls; and the fraction of runs positive on every metric against "
            f"both nulls is at least {rule['min_positive_run_fraction']:.2f}. All "
            "domains must pass.",
            "",
            "The LS20 rows come from the official local ARC-AGI toolkit environment. The tool rows come from fixed argv subprocess calls with `shell=False`, a timeout, and disposable per-run sandboxes.",
            "",
            "Training actions carried explicit null forecasts. The train trace and estimator bundle were frozen before evaluation. Every evaluation prediction was appended and fsynced before the corresponding environment step or tool invocation.",
            "",
            "The holdout unit is the complete run/episode/source group. Observable states may recur across runs for transition estimation, so this is rollout-held-out evidence, not state-held-out generalization.",
            "",
            "## Attestation",
            "",
            "The bundle verifier establishes internal hash, ordering, materialization, "
            "protocol, scoring, and decision consistency. The bundle was not "
            "externally registered before collection and is not independent "
            "third-party attestation.",
            "",
            "## Boundary",
            "",
            f"{boundary_text} It does not authorize online action selection, bridge "
            "loss coupling, Gemma dose changes, Qdrant writes, memory routing, or a "
            "dynamic-alpha controller.",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_ls20_provenance(environments_dir: Path, recordings_dir: Path) -> dict[str, Any]:
    from arc_agi import Arcade, OperationMode

    arc_version = importlib.metadata.version("arc-agi")
    engine_version = importlib.metadata.version("arcengine")
    if arc_version != EXPECTED_ARC_AGI_VERSION or engine_version != EXPECTED_ARCENGINE_VERSION:
        raise RuntimeError(
            f"expected arc-agi {EXPECTED_ARC_AGI_VERSION}/arcengine {EXPECTED_ARCENGINE_VERSION}, "
            f"got {arc_version}/{engine_version}"
        )
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environments_dir),
        recordings_dir=str(recordings_dir),
    )
    environment = arcade.make("ls20", seed=0)
    if environment is None:
        raise RuntimeError("LS20 is not installed in the declared offline environment directory")
    game_file = Path(environment.info.local_dir) / "ls20.py"
    metadata_file = Path(environment.info.local_dir) / "metadata.json"
    return {
        "arc_agi_version": arc_version,
        "arc_agi_distribution_sha256": _distribution_tree_sha256("arc-agi"),
        "arcengine_version": engine_version,
        "arcengine_distribution_sha256": _distribution_tree_sha256("arcengine"),
        "game_id": environment.info.game_id,
        "game_file_sha256": file_sha256(game_file),
        "metadata_sha256": file_sha256(metadata_file),
        "operation_mode": "OFFLINE",
        "official_toolkit_url": "https://github.com/arcprize/ARC-AGI",
    }


def validate_collection_args(args: argparse.Namespace) -> None:
    minimum_counts = {
        "train_ls20_runs": 4,
        "eval_ls20_runs": 3,
        "train_tool_runs": 4,
        "eval_tool_runs": 3,
        "ls20_steps": 16,
        "tool_steps": 4,
    }
    for field, minimum in minimum_counts.items():
        value = getattr(args, field)
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise ValueError(f"--{field.replace('_', '-')} must be an integer >= {minimum}")
    if args.tool_steps % 2:
        raise ValueError("--tool-steps must be even so both actions receive equal support")
    for field in (
        "tool_timeout",
        "alpha",
    ):
        value = getattr(args, field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"--{field.replace('_', '-')} must be finite")
    if args.tool_timeout <= 0.0 or args.alpha <= 0.0:
        raise ValueError("--tool-timeout and --alpha must be strictly positive")


def _load_json_object(path: Path, *, field: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {field}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be a JSON object")
    return payload


def _validate_manifest_contract(manifest: dict[str, Any]) -> None:
    if manifest["collector_version"] != COLLECTOR_VERSION:
        raise ValueError("manifest collector_version mismatch")
    if manifest["prohibited_integrations"] != list(PROHIBITED_INTEGRATIONS):
        raise ValueError("manifest prohibited-integration boundary mismatch")
    if manifest["split_contract"] != {
        "held_out_unit": "whole_run_episode_source_group",
        "state_content_overlap": "allowed_for_transition_estimation",
        "claim": "rollout_held_out_not_state_held_out",
    }:
        raise ValueError("manifest split contract mismatch")
    if manifest["attestation"] != ATTESTATION_CONTRACT:
        raise ValueError("manifest attestation boundary mismatch")
    if set(manifest["python"]) != {"executable", "version"}:
        raise ValueError("manifest Python fields mismatch")
    if set(manifest["ls20_source"]) != {
        "arc_agi_version",
        "arc_agi_distribution_sha256",
        "arcengine_version",
        "arcengine_distribution_sha256",
        "game_id",
        "game_file_sha256",
        "metadata_sha256",
        "operation_mode",
        "official_toolkit_url",
    }:
        raise ValueError("manifest LS20 source fields mismatch")
    if (
        manifest["ls20_source"]["arc_agi_version"] != EXPECTED_ARC_AGI_VERSION
        or manifest["ls20_source"]["arcengine_version"] != EXPECTED_ARCENGINE_VERSION
        or not manifest["ls20_source"]["game_id"].startswith("ls20-")
        or manifest["ls20_source"]["operation_mode"] != "OFFLINE"
    ):
        raise ValueError("manifest LS20 source contract mismatch")
    for field in (
        "arc_agi_distribution_sha256",
        "arcengine_distribution_sha256",
        "game_file_sha256",
        "metadata_sha256",
    ):
        if len(manifest["ls20_source"][field]) != 64:
            raise ValueError("manifest LS20 source hash mismatch")
    if set(manifest["tool_source"]) != {
        "runner",
        "runner_path",
        "runner_path_flavor",
        "shell",
        "stdin",
        "python_isolated",
        "environment_keys",
        "timeout_seconds",
        "sandbox",
    }:
        raise ValueError("manifest tool execution fields mismatch")
    runner_path_text = manifest["tool_source"]["runner_path"]
    runner_path_flavor = manifest["tool_source"]["runner_path_flavor"]
    if runner_path_flavor == "windows":
        runner_path = PureWindowsPath(runner_path_text)
    elif runner_path_flavor == "posix":
        runner_path = PurePosixPath(runner_path_text)
    else:
        raise ValueError("manifest tool runner path flavor is unknown")
    environment_keys = manifest["tool_source"]["environment_keys"]
    allowed_environment_keys = {
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "PYTHONIOENCODING",
        "PYTHONUTF8",
    }
    if (
        manifest["tool_source"]["runner"] != "world_model_tool_probe.py"
        or not runner_path.is_absolute()
        or runner_path.name != "world_model_tool_probe.py"
        or manifest["tool_source"]["shell"] is not False
        or manifest["tool_source"]["stdin"] != "DEVNULL"
        or manifest["tool_source"]["python_isolated"] is not True
        or manifest["tool_source"]["sandbox"] != "disposable_per_run"
        or not isinstance(environment_keys, list)
        or environment_keys != sorted(set(environment_keys))
        or not {"PYTHONIOENCODING", "PYTHONUTF8"}.issubset(environment_keys)
        or not set(environment_keys).issubset(allowed_environment_keys)
    ):
        raise ValueError("manifest tool execution contract mismatch")
    timeout = manifest["tool_source"]["timeout_seconds"]
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("manifest tool timeout must be finite and positive")

    expected_domains = {
        domain: {
            "action_space": list(DECLARED_ACTION_SPACES[domain]),
            "observation_space": list(DECLARED_OBSERVATION_SPACES[domain]),
            "state_ref_extractor": (
                "ls20-avatar-mask-v1" if domain == "ls20" else "tool-sandbox-v1"
            ),
        }
        for domain in sorted(DECLARED_ACTION_SPACES)
    }
    if manifest["domains"] != expected_domains:
        raise ValueError("manifest domain contract differs from collector constants")
    if not isinstance(manifest["alpha"], (int, float)) or isinstance(manifest["alpha"], bool):
        raise ValueError("manifest alpha must be numeric")
    if not math.isfinite(manifest["alpha"]) or manifest["alpha"] <= 0.0:
        raise ValueError("manifest alpha must be finite and positive")
    if not isinstance(manifest["shuffle_seed"], str) or not manifest["shuffle_seed"].strip():
        raise ValueError("manifest shuffle_seed must be non-empty")

    decision_rule = manifest["decision_rule"]
    if set(decision_rule) != {
        "min_train_transitions",
        "min_eval_transitions",
        "min_eval_runs",
        "min_transitions_per_eval_run",
        "min_train_action_count",
        "min_train_state_action_cells",
        "min_nll_improvement_nats",
        "min_brier_improvement",
        "min_positive_run_fraction",
        "all_domains_must_pass",
    }:
        raise ValueError("manifest decision-rule fields mismatch")
    if (
        decision_rule["min_nll_improvement_nats"] != MIN_NLL_IMPROVEMENT_NATS
        or decision_rule["min_brier_improvement"] != MIN_SUM_BRIER_IMPROVEMENT
        or decision_rule["min_positive_run_fraction"] != MIN_POSITIVE_RUN_FRACTION
        or decision_rule["all_domains_must_pass"] is not True
        or decision_rule["min_train_transitions"] != MIN_ACTUAL_TRANSITIONS["train"]
        or decision_rule["min_eval_transitions"] != MIN_ACTUAL_TRANSITIONS["eval"]
        or decision_rule["min_transitions_per_eval_run"]
        != MIN_TRANSITIONS_PER_EVAL_RUN
        or decision_rule["min_train_action_count"] != MIN_TRAIN_ACTION_COUNT
        or decision_rule["min_train_state_action_cells"]
        != MIN_TRAIN_STATE_ACTION_CELLS
    ):
        raise ValueError("manifest decision rule differs from preregistered constants")
    for field in (
        "min_train_transitions",
        "min_eval_transitions",
        "min_eval_runs",
        "min_transitions_per_eval_run",
        "min_train_action_count",
        "min_train_state_action_cells",
    ):
        values = decision_rule[field]
        if set(values) != set(DECLARED_ACTION_SPACES) or any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in values.values()
        ):
            raise ValueError(f"manifest {field} must contain positive domain counts")

    spec_fields = {
        "run_id",
        "split",
        "domain",
        "episode_id",
        "source_group_id",
        "environment_seed",
        "policy_seed",
        "planned_steps",
        "action_sequence",
    }
    combinations: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for spec in manifest["run_specs"]:
        if not isinstance(spec, dict) or set(spec) != spec_fields:
            raise ValueError("manifest run-spec fields mismatch")
        split = spec["split"]
        domain = spec["domain"]
        if split not in {"train", "eval"} or domain not in DECLARED_ACTION_SPACES:
            raise ValueError("manifest run spec has an unknown split or domain")
        if (
            not isinstance(spec["run_id"], str)
            or not spec["run_id"].startswith(f"phase2-{domain}-{split}-")
            or spec["episode_id"] != f"episode:{spec['run_id']}"
            or spec["source_group_id"] != f"source-group:{spec['run_id']}"
            or any(separator in spec["run_id"] for separator in ("/", "\\", ".."))
        ):
            raise ValueError("manifest run identity is not canonical")
        if (
            not isinstance(spec["planned_steps"], int)
            or isinstance(spec["planned_steps"], bool)
            or spec["planned_steps"] <= 0
            or not isinstance(spec["policy_seed"], int)
            or isinstance(spec["policy_seed"], bool)
            or spec["environment_seed"] != spec["policy_seed"]
            or not isinstance(spec["action_sequence"], list)
            or len(spec["action_sequence"]) != spec["planned_steps"]
            or any(action not in DECLARED_ACTION_SPACES[domain] for action in spec["action_sequence"])
        ):
            raise ValueError("manifest run plan is invalid")
        combinations.setdefault((split, domain), []).append(spec)
    expected_combinations = {
        (split, domain) for split in ("train", "eval") for domain in DECLARED_ACTION_SPACES
    }
    if set(combinations) != expected_combinations:
        raise ValueError("manifest must contain train and eval runs for both domains")
    minimum_runs = {("train", "ls20"): 4, ("eval", "ls20"): 3, ("train", "tool"): 4, ("eval", "tool"): 3}
    for key, minimum in minimum_runs.items():
        if len(combinations[key]) < minimum:
            raise ValueError(f"manifest has too few independent runs for {key}")
    for domain in DECLARED_ACTION_SPACES:
        train_specs = combinations[("train", domain)]
        eval_specs = combinations[("eval", domain)]
        if len(eval_specs) < decision_rule["min_eval_runs"][domain]:
            raise ValueError("manifest eval-run gate exceeds available independent runs")
        if sum(spec["planned_steps"] for spec in eval_specs) < decision_rule[
            "min_eval_transitions"
        ][domain]:
            raise ValueError("manifest eval-transition gate exceeds planned support")
        if sum(spec["planned_steps"] for spec in train_specs) < decision_rule[
            "min_train_transitions"
        ][domain]:
            raise ValueError("manifest train-transition gate exceeds planned support")
    train_ls20_seeds = {
        spec["environment_seed"] for spec in combinations[("train", "ls20")]
    }
    eval_ls20_seeds = {
        spec["environment_seed"] for spec in combinations[("eval", "ls20")]
    }
    if not train_ls20_seeds.isdisjoint(eval_ls20_seeds):
        raise ValueError("manifest LS20 train/eval environment seeds overlap")

    expected_code_paths = set(_code_hashes())
    if set(manifest["code_sha256"]) != expected_code_paths or any(
        not isinstance(digest, str) or len(digest) != 64
        for digest in manifest["code_sha256"].values()
    ):
        raise ValueError("manifest code-hash inventory mismatch")


def verify_bundle(bundle: Path) -> dict[str, Any]:
    """Recompute custody, materialization, estimator, score, and decision checks."""
    bundle = Path(bundle).resolve()
    manifest = _load_json_object(bundle / "pre_run_manifest.json", field="manifest")
    manifest_fields = {
        "schema_version",
        "created_at_utc",
        "collector_version",
        "git_revision",
        "code_sha256",
        "python",
        "ls20_source",
        "tool_source",
        "domains",
        "run_specs",
        "alpha",
        "shuffle_seed",
        "decision_rule",
        "split_contract",
        "attestation",
        "prohibited_integrations",
        "manifest_sha256",
    }
    if set(manifest) != manifest_fields:
        raise ValueError("manifest fields mismatch")
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ValueError("manifest schema_version mismatch")
    claimed_manifest_sha = manifest.pop("manifest_sha256")
    if canonical_sha256(manifest) != claimed_manifest_sha:
        raise ValueError("manifest self-hash mismatch")
    manifest["manifest_sha256"] = claimed_manifest_sha
    _validate_manifest_contract(manifest)

    sums = _load_json_object(bundle / "SHA256SUMS.json", field="SHA256SUMS")
    expected_artifacts = {
        "pre_run_manifest.json",
        "train.jsonl",
        "frozen_baselines.json",
        "eval_freeze.json",
        "eval.jsonl",
        "report.json",
        "REPORT.md",
    }
    if set(sums) != expected_artifacts:
        raise ValueError("artifact hash inventory mismatch")
    for relative, expected_hash in sums.items():
        path = bundle / relative
        if file_sha256(path) != expected_hash:
            raise ValueError(f"artifact hash mismatch: {relative}")
        sidecar = bundle / f"{relative}.sha256"
        expected_sidecar = f"{expected_hash}  {relative}\n"
        if sidecar.read_text(encoding="ascii") != expected_sidecar:
            raise ValueError(f"artifact sidecar mismatch: {relative}")
    if sums["train.jsonl"] == sums["eval.jsonl"]:
        raise ValueError("train and eval artifacts must not be byte-identical")

    specs = manifest["run_specs"]
    if not isinstance(specs, list) or not specs:
        raise ValueError("manifest run_specs must be a non-empty list")
    run_ids = [spec["run_id"] for spec in specs]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("manifest run_id values must be unique")
    source_groups = [spec["source_group_id"] for spec in specs]
    if len(source_groups) != len(set(source_groups)):
        raise ValueError("manifest source_group_id values must be unique")
    expected_journals = {_journal_path(bundle, spec).resolve() for spec in specs}
    actual_journals = {
        path.resolve() for path in (bundle / "raw").rglob("*.journal.jsonl")
    }
    if actual_journals != expected_journals:
        raise ValueError("raw journal inventory differs from the pre-run manifest")
    expected_sandboxes = {
        (bundle / "sandboxes" / spec["run_id"]).resolve()
        for spec in specs
        if spec["domain"] == "tool"
    }
    actual_sandboxes = {
        path.resolve() for path in (bundle / "sandboxes").iterdir() if path.is_dir()
    }
    if actual_sandboxes != expected_sandboxes:
        raise ValueError("tool sandbox inventory differs from the pre-run manifest")

    eval_freeze = _load_json_object(bundle / "eval_freeze.json", field="eval freeze")
    eval_freeze_fields = {
        "schema_version",
        "created_at_utc",
        "pre_run_manifest_sha256",
        "train_trace_sha256",
        "baseline_bundle_sha256",
        "baseline_file_sha256",
        "eval_run_specs_sha256",
        "estimator_ids",
        "decision_rule",
        "eval_freeze_sha256",
    }
    if set(eval_freeze) != eval_freeze_fields:
        raise ValueError("eval freeze fields mismatch")
    if eval_freeze["schema_version"] != EVAL_FREEZE_SCHEMA_VERSION:
        raise ValueError("eval freeze schema_version mismatch")
    claimed_eval_freeze_sha = eval_freeze.pop("eval_freeze_sha256")
    if canonical_sha256(eval_freeze) != claimed_eval_freeze_sha:
        raise ValueError("eval freeze self-hash mismatch")
    eval_freeze["eval_freeze_sha256"] = claimed_eval_freeze_sha
    if eval_freeze["pre_run_manifest_sha256"] != claimed_manifest_sha:
        raise ValueError("eval freeze pre-run manifest identity mismatch")
    eval_specs = [spec for spec in specs if spec["split"] == "eval"]
    if eval_freeze["eval_run_specs_sha256"] != canonical_sha256(eval_specs):
        raise ValueError("eval freeze run-spec identity mismatch")

    materialized: dict[str, list[CapturedTracePair]] = {}
    for split in ("train", "eval"):
        split_specs = [spec for spec in specs if spec["split"] == split]
        pairs: list[CapturedTracePair] = []
        for spec in split_specs:
            journal_pairs = load_journal(
                _journal_path(bundle, spec),
                expected_manifest_sha256=(
                    claimed_manifest_sha if split == "train" else claimed_eval_freeze_sha
                ),
            )
            if {pair.commit.run_id for pair in journal_pairs} != {spec["run_id"]}:
                raise ValueError(f"journal run identity mismatch: {spec['run_id']}")
            if len(journal_pairs) > spec["planned_steps"]:
                raise ValueError("journal exceeds its frozen planned length")
            if len(journal_pairs) < spec["planned_steps"] and journal_pairs[-1].outcome.observation not in {
                "terminal_game_over",
                "terminal_win",
            }:
                raise ValueError("journal ended early without a terminal LS20 outcome")
            previous_ls20_post: dict[str, Any] | None = None
            ls20_guid: str | None = None
            for step_index, pair in enumerate(journal_pairs):
                commit = pair.commit
                if (
                    commit.domain != spec["domain"]
                    or commit.episode_id != spec["episode_id"]
                    or commit.step_index != step_index
                    or commit.action != spec["action_sequence"][step_index]
                ):
                    raise ValueError("journal commit differs from its frozen run spec")
                if pair.state_source.source_id != f"{spec['source_group_id']}:pre:{step_index}":
                    raise ValueError("state source id differs from its frozen run spec")
                if pair.outcome_source is None or pair.outcome_source.source_id != (
                    f"{spec['source_group_id']}:post:{step_index}"
                ):
                    raise ValueError("outcome source id differs from its frozen run spec")
                pre_payload = pair.state_source.payload
                post_payload = pair.outcome_source.payload
                if spec["domain"] == "ls20":
                    if pair.state_source.kind != "environment" or pair.outcome_source.kind != "environment":
                        raise ValueError("LS20 source kinds must both be environment")
                    if set(pre_payload) != {
                        "collector",
                        "source_group_id",
                        "environment_seed",
                        "observation",
                    } or set(post_payload) != set(pre_payload):
                        raise ValueError("LS20 source payload fields mismatch")
                    for payload in (pre_payload, post_payload):
                        if (
                            payload["collector"] != COLLECTOR_VERSION
                            or payload["source_group_id"] != spec["source_group_id"]
                            or payload["environment_seed"] != spec["environment_seed"]
                        ):
                            raise ValueError("LS20 source provenance differs from its run spec")
                        validate_ls20_observation_payload(
                            payload["observation"],
                            expected_game_id=manifest["ls20_source"]["game_id"],
                        )
                    if ls20_guid is None:
                        ls20_guid = pre_payload["observation"]["guid"]
                    if (
                        pre_payload["observation"]["guid"] != ls20_guid
                        or post_payload["observation"]["guid"] != ls20_guid
                    ):
                        raise ValueError("LS20 GUID changed within a frozen run")
                    if (
                        previous_ls20_post is not None
                        and pre_payload["observation"] != previous_ls20_post
                    ):
                        raise ValueError("LS20 post/pre observations are not continuous")
                    if commit.state_ref != ls20_state_ref(pre_payload["observation"]):
                        raise ValueError("LS20 state_ref does not reproduce from pre-action state")
                    action_payload = json.loads(commit.action)
                    action_name = action_payload["name"]
                    if commit.action != canonical_action(action_name):
                        raise ValueError("LS20 action is not canonical")
                    if int(action_name.removeprefix("ACTION")) not in pre_payload["observation"][
                        "available_actions"
                    ]:
                        raise ValueError("LS20 action was not legal in the pre-action state")
                    if post_payload["observation"]["previous_action"] != {
                        "id": action_name,
                        "data": {},
                        "reasoning": None,
                    }:
                        raise ValueError("LS20 post-state does not bind the committed action")
                    expected_observation = classify_ls20_outcome(
                        pre_payload["observation"], post_payload["observation"]
                    )
                    previous_ls20_post = post_payload["observation"]
                else:
                    if pair.state_source.kind != "tool_context" or pair.outcome_source.kind != "tool_result":
                        raise ValueError("tool source kinds must be context then result")
                    if set(pre_payload) != {"collector", "source_group_id", "files"}:
                        raise ValueError("tool context payload fields mismatch")
                    if (
                        pre_payload["collector"] != COLLECTOR_VERSION
                        or pre_payload["source_group_id"] != spec["source_group_id"]
                    ):
                        raise ValueError("tool context provenance differs from its run spec")
                    sandbox_root = (bundle / "sandboxes").resolve()
                    sandbox = (sandbox_root / spec["run_id"]).resolve()
                    if not sandbox.is_relative_to(sandbox_root):
                        raise ValueError("tool sandbox path escapes the bundle")
                    if pre_payload["files"] != _tool_files_payload(sandbox)["files"]:
                        raise ValueError("tool context files differ from the captured sandbox")
                    if commit.state_ref != tool_state_ref(pre_payload):
                        raise ValueError("tool state_ref does not reproduce from pre-action context")
                    if set(post_payload) != {
                        "collector",
                        "source_group_id",
                        "argv",
                        "timeout_seconds",
                        "timed_out",
                        "returncode",
                        "stdout",
                        "stderr",
                        "shell",
                        "stdin",
                        "environment_keys",
                    }:
                        raise ValueError("tool result payload fields mismatch")
                    if (
                        post_payload["collector"] != COLLECTOR_VERSION
                        or post_payload["source_group_id"] != spec["source_group_id"]
                    ):
                        raise ValueError("tool result provenance differs from its run spec")
                    action_payload = json.loads(commit.action)
                    expected_argv = [
                        manifest["python"]["executable"],
                        "-I",
                        manifest["tool_source"]["runner_path"],
                        "--read-text",
                        action_payload["arguments"]["path"],
                    ]
                    if post_payload["argv"] != expected_argv:
                        raise ValueError("tool argv does not match the committed action")
                    if (
                        post_payload["timeout_seconds"]
                        != manifest["tool_source"]["timeout_seconds"]
                        or post_payload["shell"] is not False
                        or post_payload["stdin"] != "DEVNULL"
                        or post_payload["environment_keys"]
                        != manifest["tool_source"]["environment_keys"]
                    ):
                        raise ValueError("tool execution contract differs from the manifest")
                    expected_observation = classify_tool_result(post_payload)
                    action_path = action_payload["arguments"]["path"]
                    file_row = next(row for row in pre_payload["files"] if row["path"] == action_path)
                    if expected_observation == "success":
                        if not file_row["exists"] or hashlib.sha256(
                            post_payload["stdout"].encode("utf-8")
                        ).hexdigest() != file_row["text_sha256"]:
                            raise ValueError("successful tool output does not match the pre-state file")
                    elif expected_observation == "not_found" and file_row["exists"]:
                        raise ValueError("not-found tool result contradicts the pre-state file")
                if pair.outcome.observation != expected_observation:
                    raise ValueError("outcome label does not reproduce from captured sources")
                if pair.outcome.observation in {"terminal_game_over", "terminal_win"} and (
                    step_index != len(journal_pairs) - 1
                ):
                    raise ValueError("terminal LS20 outcome must be the final transition")
            pairs.extend(journal_pairs)
        if paired_trace_bytes(pairs) != (bundle / f"{split}.jsonl").read_bytes():
            raise ValueError(f"{split} paired trace does not match its journals")
        materialized[split] = pairs

    baseline = _load_json_object(bundle / "frozen_baselines.json", field="baseline bundle")
    baseline_fields = {
        "schema_version",
        "manifest_sha256",
        "train_trace_sha256",
        "alpha",
        "shuffle_seed",
        "domains",
        "baseline_bundle_sha256",
    }
    if set(baseline) != baseline_fields:
        raise ValueError("baseline bundle fields mismatch")
    if baseline["schema_version"] != BASELINE_SCHEMA_VERSION:
        raise ValueError("baseline bundle schema_version mismatch")
    claimed_baseline_sha = baseline.pop("baseline_bundle_sha256")
    if canonical_sha256(baseline) != claimed_baseline_sha:
        raise ValueError("baseline bundle self-hash mismatch")
    baseline["baseline_bundle_sha256"] = claimed_baseline_sha
    if baseline["manifest_sha256"] != claimed_manifest_sha:
        raise ValueError("baseline bundle manifest identity mismatch")
    if baseline["train_trace_sha256"] != sums["train.jsonl"]:
        raise ValueError("baseline bundle train trace hash mismatch")
    if eval_freeze["train_trace_sha256"] != sums["train.jsonl"]:
        raise ValueError("eval freeze train trace hash mismatch")
    if eval_freeze["baseline_bundle_sha256"] != claimed_baseline_sha:
        raise ValueError("eval freeze baseline identity mismatch")
    if eval_freeze["baseline_file_sha256"] != sums["frozen_baselines.json"]:
        raise ValueError("eval freeze baseline file hash mismatch")

    expected_baseline, estimators = fit_frozen_baselines(
        materialized["train"],
        alpha=manifest["alpha"],
        train_trace_sha256=sums["train.jsonl"],
        shuffle_seed=manifest["shuffle_seed"],
        manifest_sha256=claimed_manifest_sha,
    )
    if baseline != expected_baseline:
        raise ValueError("frozen baseline bundle does not reproduce from training data")
    for domain, domain_payload in baseline["domains"].items():
        if set(domain_payload) != {
            "action_space",
            "observation_space",
            "state_ref_extractor",
            "tabular",
            "empirical_marginal_null",
            "action_shuffle_null",
        }:
            raise ValueError("baseline domain fields mismatch")
        manifest_domain = manifest["domains"][domain]
        if domain_payload["action_space"] != manifest_domain["action_space"]:
            raise ValueError("baseline action space differs from pre-run manifest")
        if domain_payload["observation_space"] != manifest_domain["observation_space"]:
            raise ValueError("baseline observation space differs from pre-run manifest")
        estimator = DirichletTabularEstimator.from_payload(domain_payload["tabular"])
        EmpiricalMarginalEstimator.from_payload(domain_payload["empirical_marginal_null"])
        shuffle = DeterministicActionShuffleNull(
            estimator,
            domain_payload["action_space"],
            seed=domain_payload["action_shuffle_null"]["seed"],
        )
        if shuffle.action_mapping != domain_payload["action_shuffle_null"]["mapping"]:
            raise ValueError("frozen action-shuffle mapping mismatch")
        if shuffle.estimator_id != domain_payload["action_shuffle_null"]["estimator_id"]:
            raise ValueError("frozen action-shuffle identity mismatch")
        if estimator.canonical_payload() != estimators[domain].canonical_payload():
            raise ValueError("frozen tabular estimator does not reproduce from training data")
    if eval_freeze["estimator_ids"] != {
        domain: estimator.estimator_id for domain, estimator in estimators.items()
    }:
        raise ValueError("eval freeze estimator identity mismatch")
    if eval_freeze["decision_rule"] != manifest["decision_rule"]:
        raise ValueError("eval freeze decision rule mismatch")

    _validate_eval_commits(materialized["eval"], estimators)
    report = _load_json_object(bundle / "report.json", field="report")
    if set(report) != {
        "schema_version",
        "manifest_sha256",
        "baseline_bundle_sha256",
        "eval_freeze_sha256",
        "artifacts",
        "scores",
        "decision_rule",
        "decision_checks",
        "decision",
        "boundary",
        "attestation",
    }:
        raise ValueError("report fields mismatch")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("report schema_version mismatch")
    if report.get("manifest_sha256") != claimed_manifest_sha:
        raise ValueError("report manifest identity mismatch")
    if report.get("baseline_bundle_sha256") != claimed_baseline_sha:
        raise ValueError("report baseline identity mismatch")
    if report.get("eval_freeze_sha256") != claimed_eval_freeze_sha:
        raise ValueError("report eval-freeze identity mismatch")
    if report.get("decision_rule") != manifest["decision_rule"]:
        raise ValueError("report decision rule differs from the pre-run manifest")
    expected_report_artifacts = {
        relative: sums[relative]
        for relative in (
            "pre_run_manifest.json",
            "train.jsonl",
            "frozen_baselines.json",
            "eval_freeze.json",
            "eval.jsonl",
        )
    }
    if report.get("artifacts") != expected_report_artifacts:
        raise ValueError("report artifact inventory mismatch")
    expected_boundary = {
        "authorized": "offline_learned_observer_prototype_only_if_decision_is_go",
        "still_prohibited": list(PROHIBITED_INTEGRATIONS),
    }
    if report.get("boundary") != expected_boundary:
        raise ValueError("report integration boundary mismatch")
    if report.get("attestation") != manifest["attestation"]:
        raise ValueError("report attestation boundary mismatch")
    for relative, digest in report.get("artifacts", {}).items():
        if sums.get(relative) != digest:
            raise ValueError(f"report artifact hash mismatch: {relative}")

    action_spaces = {
        domain: tuple(payload["action_space"])
        for domain, payload in manifest["domains"].items()
    }
    observation_spaces = {
        domain: tuple(payload["observation_space"])
        for domain, payload in manifest["domains"].items()
    }
    score = scorer.score_files(
        bundle / "train.jsonl",
        bundle / "eval.jsonl",
        alpha=manifest["alpha"],
        shuffle_seed=manifest["shuffle_seed"],
        observation_spaces=observation_spaces,
        action_spaces=action_spaces,
        require_eval_commits=True,
        estimator_ids={domain: estimator.estimator_id for domain, estimator in estimators.items()},
    )
    if score != report.get("scores"):
        raise ValueError("report scores do not reproduce")
    decision, checks = _decision(score, manifest["decision_rule"])
    if decision != report.get("decision") or checks != report.get("decision_checks"):
        raise ValueError("report decision does not reproduce")
    if (bundle / "REPORT.md").read_text(encoding="utf-8") != _markdown_report(report):
        raise ValueError("human-readable report does not reproduce")
    return {
        "ok": True,
        "manifest_sha256": claimed_manifest_sha,
        "baseline_bundle_sha256": claimed_baseline_sha,
        "decision": decision,
        "n_train": score["n_train"],
        "n_eval": score["n_eval"],
    }


def collect_bundle(args: argparse.Namespace) -> Path:
    validate_collection_args(args)
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output bundle: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))

    ls20_provenance = _resolve_ls20_provenance(args.arc_environments_dir, args.arc_recordings_dir)
    specs = build_run_specs(
        train_ls20_runs=args.train_ls20_runs,
        eval_ls20_runs=args.eval_ls20_runs,
        train_tool_runs=args.train_tool_runs,
        eval_tool_runs=args.eval_tool_runs,
        ls20_steps=args.ls20_steps,
        tool_steps=args.tool_steps,
    )
    decision_rule = {
        "min_train_transitions": dict(MIN_ACTUAL_TRANSITIONS["train"]),
        "min_eval_transitions": dict(MIN_ACTUAL_TRANSITIONS["eval"]),
        "min_eval_runs": {"ls20": args.eval_ls20_runs, "tool": args.eval_tool_runs},
        "min_transitions_per_eval_run": dict(MIN_TRANSITIONS_PER_EVAL_RUN),
        "min_train_action_count": dict(MIN_TRAIN_ACTION_COUNT),
        "min_train_state_action_cells": dict(MIN_TRAIN_STATE_ACTION_CELLS),
        "min_nll_improvement_nats": MIN_NLL_IMPROVEMENT_NATS,
        "min_brier_improvement": MIN_SUM_BRIER_IMPROVEMENT,
        "min_positive_run_fraction": MIN_POSITIVE_RUN_FRACTION,
        "all_domains_must_pass": True,
    }
    manifest_without_hash = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "collector_version": COLLECTOR_VERSION,
        "git_revision": _git_revision(),
        "code_sha256": _code_hashes(),
        "python": {"executable": str(Path(sys.executable).resolve()), "version": sys.version},
        "ls20_source": ls20_provenance,
        "tool_source": {
            "runner": "world_model_tool_probe.py",
            "runner_path": str((SPIKES_DIR / "world_model_tool_probe.py").resolve()),
            "runner_path_flavor": "windows" if os.name == "nt" else "posix",
            "shell": False,
            "stdin": "DEVNULL",
            "python_isolated": True,
            "environment_keys": sorted(tool_subprocess_environment()),
            "timeout_seconds": args.tool_timeout,
            "sandbox": "disposable_per_run",
        },
        "domains": {
            domain: {
                "action_space": list(DECLARED_ACTION_SPACES[domain]),
                "observation_space": list(DECLARED_OBSERVATION_SPACES[domain]),
                "state_ref_extractor": (
                    "ls20-avatar-mask-v1" if domain == "ls20" else "tool-sandbox-v1"
                ),
            }
            for domain in sorted(DECLARED_ACTION_SPACES)
        },
        "run_specs": specs,
        "alpha": args.alpha,
        "shuffle_seed": args.shuffle_seed,
        "decision_rule": decision_rule,
        "split_contract": {
            "held_out_unit": "whole_run_episode_source_group",
            "state_content_overlap": "allowed_for_transition_estimation",
            "claim": "rollout_held_out_not_state_held_out",
        },
        "attestation": dict(ATTESTATION_CONTRACT),
        "prohibited_integrations": list(PROHIBITED_INTEGRATIONS),
    }
    manifest_sha256 = canonical_sha256(manifest_without_hash)
    manifest = {**manifest_without_hash, "manifest_sha256": manifest_sha256}
    manifest_path = staging / "pre_run_manifest.json"
    _write_json_durable(manifest_path, manifest)

    null_observer = NullWorldModelObserver()
    train_specs = [spec for spec in specs if spec["split"] == "train"]
    for spec in train_specs:
        if spec["domain"] == "ls20":
            collect_ls20_run(
                staging=staging,
                spec=spec,
                manifest_sha256=manifest_sha256,
                observer=null_observer,
                environments_dir=args.arc_environments_dir,
                recordings_dir=args.arc_recordings_dir,
            )
        else:
            collect_tool_run(
                staging=staging,
                spec=spec,
                manifest_sha256=manifest_sha256,
                observer=null_observer,
                python_executable=Path(sys.executable),
                timeout_seconds=args.tool_timeout,
            )

    train_path, train_pairs = _materialize_split(
        staging=staging,
        specs=train_specs,
        manifest_sha256=manifest_sha256,
        output_name="train.jsonl",
    )
    train_sha256 = file_sha256(train_path)
    baseline_payload, estimators = fit_frozen_baselines(
        train_pairs,
        alpha=args.alpha,
        train_trace_sha256=train_sha256,
        shuffle_seed=args.shuffle_seed,
        manifest_sha256=manifest_sha256,
    )
    baseline_path = staging / "frozen_baselines.json"
    _write_json_durable(baseline_path, baseline_payload)

    eval_specs = [spec for spec in specs if spec["split"] == "eval"]
    eval_freeze_without_hash = {
        "schema_version": EVAL_FREEZE_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pre_run_manifest_sha256": manifest_sha256,
        "train_trace_sha256": train_sha256,
        "baseline_bundle_sha256": baseline_payload["baseline_bundle_sha256"],
        "baseline_file_sha256": file_sha256(baseline_path),
        "eval_run_specs_sha256": canonical_sha256(eval_specs),
        "estimator_ids": {
            domain: estimator.estimator_id for domain, estimator in estimators.items()
        },
        "decision_rule": decision_rule,
    }
    eval_freeze_sha256 = canonical_sha256(eval_freeze_without_hash)
    eval_freeze = {
        **eval_freeze_without_hash,
        "eval_freeze_sha256": eval_freeze_sha256,
    }
    eval_freeze_path = staging / "eval_freeze.json"
    _write_json_durable(eval_freeze_path, eval_freeze)
    for spec in eval_specs:
        observer = estimators[spec["domain"]]
        if spec["domain"] == "ls20":
            collect_ls20_run(
                staging=staging,
                spec=spec,
                manifest_sha256=eval_freeze_sha256,
                observer=observer,
                environments_dir=args.arc_environments_dir,
                recordings_dir=args.arc_recordings_dir,
            )
        else:
            collect_tool_run(
                staging=staging,
                spec=spec,
                manifest_sha256=eval_freeze_sha256,
                observer=observer,
                python_executable=Path(sys.executable),
                timeout_seconds=args.tool_timeout,
            )

    eval_path, eval_pairs = _materialize_split(
        staging=staging,
        specs=eval_specs,
        manifest_sha256=eval_freeze_sha256,
        output_name="eval.jsonl",
    )
    _validate_eval_commits(eval_pairs, estimators)
    estimator_ids = {domain: estimator.estimator_id for domain, estimator in estimators.items()}
    score = scorer.score_files(
        train_path,
        eval_path,
        alpha=args.alpha,
        shuffle_seed=args.shuffle_seed,
        observation_spaces=DECLARED_OBSERVATION_SPACES,
        action_spaces=DECLARED_ACTION_SPACES,
        require_eval_commits=True,
        estimator_ids=estimator_ids,
    )
    decision, decision_checks = _decision(score, decision_rule)
    artifacts = {
        "pre_run_manifest.json": file_sha256(manifest_path),
        "train.jsonl": file_sha256(train_path),
        "frozen_baselines.json": file_sha256(baseline_path),
        "eval_freeze.json": file_sha256(eval_freeze_path),
        "eval.jsonl": file_sha256(eval_path),
    }
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "manifest_sha256": manifest_sha256,
        "baseline_bundle_sha256": baseline_payload["baseline_bundle_sha256"],
        "eval_freeze_sha256": eval_freeze_sha256,
        "artifacts": artifacts,
        "scores": score,
        "decision_rule": decision_rule,
        "decision_checks": decision_checks,
        "decision": decision,
        "boundary": {
            "authorized": "offline_learned_observer_prototype_only_if_decision_is_go",
            "still_prohibited": manifest["prohibited_integrations"],
        },
        "attestation": manifest["attestation"],
    }
    report_path = staging / "report.json"
    _write_json_durable(report_path, report)
    markdown_path = staging / "REPORT.md"
    _write_durable(markdown_path, _markdown_report(report).encode("utf-8"))
    artifacts["report.json"] = file_sha256(report_path)
    artifacts["REPORT.md"] = file_sha256(markdown_path)
    sums_path = staging / "SHA256SUMS.json"
    _write_json_durable(sums_path, artifacts)
    for relative, digest in artifacts.items():
        sidecar = staging / f"{relative}.sha256"
        _write_durable(sidecar, f"{digest}  {relative}\n".encode("ascii"))

    if _code_hashes() != manifest["code_sha256"]:
        raise RuntimeError("collector code changed after the pre-run manifest was frozen")
    verify_bundle(staging)
    _publish_directory_no_overwrite(staging, output)
    verify_bundle(output)
    return output


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--arc-environments-dir", type=Path)
    parser.add_argument("--arc-recordings-dir", type=Path)
    parser.add_argument("--train-ls20-runs", type=int, default=6)
    parser.add_argument("--eval-ls20-runs", type=int, default=3)
    parser.add_argument("--train-tool-runs", type=int, default=8)
    parser.add_argument("--eval-tool-runs", type=int, default=4)
    parser.add_argument("--ls20-steps", type=int, default=48)
    parser.add_argument("--tool-steps", type=int, default=8)
    parser.add_argument("--tool-timeout", type=float, default=5.0)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--shuffle-seed", default="world-model-phase2-real-v1")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        if args.verify is not None:
            print(json.dumps(verify_bundle(args.verify), indent=2, sort_keys=True))
            return 0
        if args.arc_environments_dir is None or args.arc_recordings_dir is None:
            raise ValueError("collection requires --arc-environments-dir and --arc-recordings-dir")
        output = collect_bundle(args)
    except (FileExistsError, RuntimeError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"collection failed: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
