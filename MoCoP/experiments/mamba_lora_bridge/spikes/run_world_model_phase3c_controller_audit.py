#!/usr/bin/env python3
"""Run the frozen World Model Phase 3c controller audit.

This runner is deliberately model-free and stdlib-only. It audits the frozen
WorldEvent -> AppraisalVector -> controller kernel and publishes one
content-addressed, no-overwrite result bundle.
"""

from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Any, Iterable, Sequence


MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import modulatory_controller as controller  # noqa: E402
import world_model_events as events  # noqa: E402
import world_model_trace as trace  # noqa: E402


PROTOCOL_ID = "world-model-phase3c-controller-audit-v1"
FROZEN_HEAD = "aa9076c98dab58522ae9c8872aae6b30b88e0c75"
FROZEN_PREREG_BLOB = "734e8d38032caa296a4fde76a53df48f8df26ef1"
SOURCE_BLOBS = {
    "modulatory_controller.py": "a49bec6a6c69d0890a3e06f9d9fa4b63b83c42b2",
    "world_model_events.py": "532931731db07870d78d74b858a6dd367fc4ce99",
    "world_model_trace.py": "19da97902c3544757989ef4f6fbdb1ff1968c1de",
    "tests/test_modulatory_controller.py": (
        "efede079fd17433ee49d6d2116a7ea05d5adc283"
    ),
    "tests/test_world_model_events.py": (
        "66a155e6d71e7162ea9a86d60b5d0572b3acee90"
    ),
    "../../reviews/world_model_pro_external_review_2026-07-12.md": (
        "3227b3da5933fe3f6a293580d236db0de798298e"
    ),
    "spikes/APPRAISAL_MODULATORY_CONTROLLER_CONTRACT_2026-07-12.md": (
        "eead3bca5f987a008c80a11a14fffd72b0a547a9"
    ),
}
PREREG_PATH = (
    MODULE_ROOT
    / "spikes"
    / "WORLD_MODEL_PHASE3C_CONTROLLER_AUDIT_PREREG_2026-07-18.md"
)
OUTPUT_DIR = MODULE_ROOT / "results" / "world_model_phase3" / "controller_audit_v1"

Q_FIELDS = (
    "predicted_harm",
    "prediction_error",
    "controllability",
    "goal_progress",
    "norm_violation",
    "affiliation_delta",
)
STATE_FIELDS = ("affiliation", "agency", "vigilance", "reserve", "load")
NONNEG_GRID_5 = (0.0, 0.25, 0.5, 0.75, 1.0)
SIGNED_GRID_5 = (-1.0, -0.5, 0.0, 0.5, 1.0)
STATE_CORNERS = tuple(itertools.product((0.0, 1.0), repeat=5))
STATE_GRID_3 = tuple(itertools.product((0.0, 0.5, 1.0), repeat=5))
FAILURE_WITNESS_LIMIT = 16

TARGET_FIELDS = {
    "threat_observed": "predicted_harm",
    "threat_cleared": "predicted_harm",
    "outcome_mismatch": "prediction_error",
    "control_available": "controllability",
    "control_lost": "controllability",
    "goal_progress": "goal_progress",
    "goal_blocked": "goal_progress",
    "norm_violation": "norm_violation",
    "affiliation_gain": "affiliation_delta",
    "affiliation_loss": "affiliation_delta",
}


def canonical_bytes(value: Any) -> bytes:
    """Canonical strict JSON with one LF record delimiter."""
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def f17(value: float) -> str:
    return format(float(value), ".17g")


def float_list(values: Iterable[float]) -> list[str]:
    return [f17(value) for value in values]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def verify_frozen_sources() -> dict[str, Any]:
    if sys.version_info[:3] != (3, 13, 9):
        raise RuntimeError(
            "frozen Python mismatch: expected 3.13.9, got "
            f"{platform.python_version()}"
        )
    records = []
    ok = True
    for relative, expected in SOURCE_BLOBS.items():
        path = MODULE_ROOT / relative
        actual = git_blob_sha1(path)
        match = actual == expected
        ok = ok and match
        records.append(
            {
                "path": relative,
                "expected_git_blob": expected,
                "actual_git_blob": actual,
                "match": match,
            }
        )
    if not ok:
        mismatches = [item["path"] for item in records if not item["match"]]
        raise RuntimeError(f"frozen source mismatch: {mismatches}")
    prereg_blob = git_blob_sha1(PREREG_PATH)
    if prereg_blob != FROZEN_PREREG_BLOB:
        raise RuntimeError(
            "frozen preregistration mismatch: "
            f"expected {FROZEN_PREREG_BLOB}, got {prereg_blob}"
        )
    return {
        "frozen_head": FROZEN_HEAD,
        "preregistration_git_blob": prereg_blob,
        "loaded_modules": [controller.__name__, events.__name__, trace.__name__],
        "records": records,
        "pass": True,
    }


def quantize_half_up(value: float) -> float:
    if not 0.0 <= value <= 1.0 or not math.isfinite(value):
        raise ValueError("candidate quantization requires a finite unit value")
    return math.floor(256.0 * value + 0.5) / 256.0


def q_tuple(q: controller.AppraisalVector) -> tuple[float, ...]:
    return tuple(getattr(q, field) for field in Q_FIELDS)


def q_record(q: controller.AppraisalVector) -> dict[str, str]:
    return {field: f17(getattr(q, field)) for field in Q_FIELDS}


def state_tuple(step: controller.ControllerStep) -> tuple[float, ...]:
    return (
        step.kappa.affiliation,
        step.kappa.agency,
        step.kappa.vigilance,
        step.regulatory.reserve,
        step.regulatory.load,
    )


def state_objects(
    state: Sequence[float],
) -> tuple[controller.KappaState, controller.RegulatoryState]:
    if len(state) != 5:
        raise ValueError("state must contain five values")
    return (
        controller.KappaState(*state[:3]),
        controller.RegulatoryState(*state[3:]),
    )


def baseline_state() -> tuple[float, ...]:
    return (0.0, 0.0, 0.0, 1.0, 0.0)


def transition(
    state: Sequence[float], q: controller.AppraisalVector
) -> tuple[float, ...]:
    kappa, regulatory = state_objects(state)
    return state_tuple(controller.step_controller(kappa, regulatory, q))


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def independent_transition(
    state: Sequence[float], q: controller.AppraisalVector
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Independent pre-clip and post-clip implementation of the frozen equations."""
    affiliation, agency, vigilance, reserve, load = state
    cfg = controller.DEFAULT_CONTROLLER_CONFIG
    positive_affiliation = max(0.0, q.affiliation_delta)
    negative_affiliation = max(0.0, -q.affiliation_delta)
    repair_drive = q.norm_violation * q.controllability
    raw_affiliation = (
        cfg.affiliation_retention * affiliation
        + cfg.affiliation_gain * positive_affiliation
        + cfg.repair_gain * repair_drive
        - cfg.affiliation_loss * negative_affiliation
    )
    blocked_goal = max(0.0, -q.goal_progress)
    control_need = max(q.predicted_harm, blocked_goal, q.norm_violation)
    raw_agency = (
        cfg.agency_retention * agency
        + cfg.agency_gain * q.controllability * control_need
        - cfg.agency_loss * (1.0 - q.controllability) * control_need
    )
    drive = _clip(0.7 * q.predicted_harm + 0.3 * q.prediction_error)
    recovery = reserve * (1.0 - drive) * (1.0 - 0.5 * load)
    raw_vigilance = (
        cfg.vigilance_retention * vigilance
        + cfg.vigilance_gain * drive
        - cfg.vigilance_recovery * recovery
    )
    depletion = drive * (0.25 + 0.75 * (1.0 - q.controllability))
    reserve_recovery = (1.0 - drive) * (1.0 - load)
    raw_reserve = (
        reserve
        + cfg.reserve_recovery * reserve_recovery
        - cfg.reserve_depletion * depletion
    )
    clipped_vigilance = _clip(raw_vigilance)
    raw_load = (
        cfg.load_retention * load
        + cfg.load_gain * clipped_vigilance * (1.0 - q.controllability)
        - cfg.load_recovery * (1.0 - drive) * reserve
    )
    raw = (
        raw_affiliation,
        raw_agency,
        raw_vigilance,
        raw_reserve,
        raw_load,
    )
    return raw, tuple(_clip(value) for value in raw)


def max_abs_delta(left: Sequence[float], right: Sequence[float]) -> float:
    return max(abs(a - b) for a, b in zip(left, right, strict=True))


def make_source(event_id: str, sequence: int) -> events.EventSourceRef:
    return events.EventSourceRef(
        kind="synthetic_fixture",
        source_id=f"{event_id}:source",
        sha256=sha256_hex(event_id.encode("ascii")),
        sequence=sequence,
    )


def make_event(
    *,
    event_id: str,
    turn_index: int,
    event_index: int,
    kind: str,
    magnitude: float,
    confidence: float = 1.0,
    attribution: str | None = None,
    semantic_refs: tuple[events.SemanticRef, ...] = (),
    source: events.EventSourceRef | None = None,
) -> events.WorldEvent:
    if attribution is None:
        attribution = "self" if kind == "norm_violation" else "environment"
    return events.WorldEvent(
        event_id=event_id,
        turn_index=turn_index,
        event_index=event_index,
        kind=kind,
        magnitude=magnitude,
        confidence=confidence,
        attribution=attribution,
        source=source if source is not None else make_source(event_id, event_index),
        semantic_refs=semantic_refs,
    )


def metamorphic_event(kind: str, part: str, index: int = 0) -> events.WorldEvent:
    if part == "merged":
        magnitude = 0.5
        event_id = f"{PROTOCOL_ID}:metamorphic:{kind}:merged"
    elif part == "split":
        magnitude = 0.25
        event_id = f"{PROTOCOL_ID}:metamorphic:{kind}:split:{index}"
    else:
        raise ValueError(f"unknown metamorphic part: {part}")
    return make_event(
        event_id=event_id,
        turn_index=0,
        event_index=index,
        kind=kind,
        magnitude=magnitude,
    )


def appraisal_values(q: controller.AppraisalVector) -> tuple[float, ...]:
    return tuple(getattr(q, name) for name in Q_FIELDS)


def simulate(
    q: controller.AppraisalVector,
    ticks: int,
    initial: Sequence[float] | None = None,
) -> list[tuple[float, ...]]:
    current = tuple(initial) if initial is not None else baseline_state()
    trajectory = [current]
    for _ in range(ticks):
        current = transition(current, q)
        trajectory.append(current)
    return trajectory


class StreamSummary:
    def __init__(self) -> None:
        self.count = 0
        self._digest = hashlib.sha256()
        self._failures: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._failure_counts: dict[str, int] = defaultdict(int)

    def add(self, record: dict[str, Any]) -> None:
        self._digest.update(canonical_bytes(record))
        self.count += 1

    def fail(self, reason: str, witness: dict[str, Any]) -> None:
        self._failure_counts[reason] += 1
        bucket = self._failures[reason]
        bucket.append(witness)
        bucket.sort(key=canonical_bytes)
        del bucket[FAILURE_WITNESS_LIMIT:]

    def record(self) -> dict[str, Any]:
        return {
            "record_delimiter": "canonical-json-lf",
            "row_count": self.count,
            "stream_sha256": self._digest.hexdigest(),
            "failure_counts": dict(sorted(self._failure_counts.items())),
            "failure_witnesses": dict(sorted(self._failures.items())),
        }


def _audit_record(item: controller.AppraisalAuditRecord) -> dict[str, Any]:
    return {
        "event_id": item.event_id,
        "rule_id": item.rule_id,
        "appraisal_field": item.appraisal_field,
        "contribution": f17(item.contribution),
    }


def _semantic_preclip(kind: str, magnitude: float) -> float:
    if kind in {
        "threat_cleared",
        "control_lost",
        "goal_blocked",
        "affiliation_loss",
    }:
        return -magnitude
    return magnitude


def audit_event_metamorphics() -> tuple[dict[str, Any], list[str]]:
    rows = []
    failures: list[str] = []
    neutral_q = controller.appraise_events(()).vector
    for kind in sorted(events.WORLD_EVENT_KINDS):
        merged_event = metamorphic_event(kind, "merged")
        split_events = (
            metamorphic_event(kind, "split", 0),
            metamorphic_event(kind, "split", 1),
        )
        merged = controller.appraise_events((merged_event,))
        split = controller.appraise_events(split_events)
        reversed_split = controller.appraise_events(tuple(reversed(split_events)))
        merge_delta = max_abs_delta(
            appraisal_values(merged.vector), appraisal_values(split.vector)
        )
        reversal_delta = max_abs_delta(
            appraisal_values(split.vector), appraisal_values(reversed_split.vector)
        )
        changed = [
            field
            for field in Q_FIELDS
            if getattr(merged.vector, field) != getattr(neutral_q, field)
        ]
        undeclared = [field for field in changed if field != TARGET_FIELDS[kind]]
        if merge_delta > 1e-12:
            failures.append(f"{kind}: split/merge delta {f17(merge_delta)}")
        if reversal_delta > 1e-12:
            failures.append(f"{kind}: reversal delta {f17(reversal_delta)}")
        if undeclared:
            failures.append(f"{kind}: undeclared fields {undeclared}")

        signed_total = _semantic_preclip(kind, 0.5)
        target = TARGET_FIELDS[kind]
        target_base = 0.5 if target == "controllability" else 0.0
        target_scale = 0.5 if target == "controllability" else 1.0
        semantic_preclip = target_base + target_scale * signed_total
        target_postclip = getattr(merged.vector, target)
        clipped_mass = abs(semantic_preclip - target_postclip)

        merged_traj = [baseline_state()]
        merged_state = baseline_state()
        for tick in range(1, 9):
            merged_state = transition(
                merged_state, merged.vector if tick == 1 else neutral_q
            )
            merged_traj.append(merged_state)
        cross_tick_events = tuple(
            make_event(
                event_id=(
                    f"{PROTOCOL_ID}:metamorphic:{kind}:cross-tick:{tick}"
                ),
                turn_index=tick,
                event_index=0,
                kind=kind,
                magnitude=0.25,
            )
            for tick in (0, 1)
        )
        split_state = baseline_state()
        cross_tick = []
        for tick in range(1, 9):
            if tick in {1, 2}:
                q = controller.appraise_events((cross_tick_events[tick - 1],)).vector
            else:
                q = neutral_q
            split_state = transition(split_state, q)
            if tick in {1, 2, 4, 8}:
                cross_tick.append(
                    {
                        "tick": tick,
                        "max_abs_state_delta": f17(
                            max_abs_delta(merged_traj[tick], split_state)
                        ),
                    }
                )

        rows.append(
            {
                "kind": kind,
                "target_field": target,
                "signed_preclip_total": f17(signed_total),
                "target_semantic_preclip": f17(semantic_preclip),
                "target_postclip": f17(target_postclip),
                "clipped_mass": f17(clipped_mass),
                "occurrence_count": 1,
                "one_event_q": q_record(merged.vector),
                "split_q": q_record(split.vector),
                "split_merge_max_abs_delta": f17(merge_delta),
                "reversal_max_abs_delta": f17(reversal_delta),
                "changed_fields": changed,
                "undeclared_changed_fields": undeclared,
                "audit": [_audit_record(item) for item in merged.audit],
                "cross_tick_split_merge": cross_tick,
            }
        )

    progress_q = controller.appraise_events(
        (metamorphic_event("goal_progress", "merged"),)
    ).vector
    progress_response = max(
        max_abs_delta(simulate(progress_q, horizon)[-1], baseline_state())
        for horizon in (1, 4, 8)
    )
    if progress_response < 0.01:
        failures.append(
            "goal_progress retained without a declared controller response"
        )

    clear_row = next(row for row in rows if row["kind"] == "threat_cleared")
    clear_audit_distinct = bool(clear_row["audit"])
    if not clear_audit_distinct:
        failures.append("threat_cleared is not audit-distinct from empty input")

    return (
        {
            "rows": rows,
            "goal_progress_best_response": f17(progress_response),
            "threat_clear_audit_distinct": clear_audit_distinct,
            "gate": "FAIL" if failures else "PASS",
            "reasons": failures,
        },
        failures,
    )


def audit_replay_boundary() -> dict[str, Any]:
    base = metamorphic_event("threat_observed", "merged")
    duplicate_id = make_event(
        event_id=base.event_id,
        turn_index=0,
        event_index=1,
        kind=base.kind,
        magnitude=base.magnitude,
    )
    duplicate_position = make_event(
        event_id=f"{PROTOCOL_ID}:replay:duplicate-position",
        turn_index=0,
        event_index=0,
        kind=base.kind,
        magnitude=base.magnitude,
    )

    results = {}
    for name, partner in (
        ("duplicate_event_id", duplicate_id),
        ("duplicate_position", duplicate_position),
    ):
        refused = False
        error = None
        try:
            controller.appraise_events((base, partner))
        except ValueError as exc:
            refused = True
            error = str(exc)
        results[name] = {"refused": refused, "error": error}
    failures = [name for name, result in results.items() if not result["refused"]]
    return {
        "probes": results,
        "cross_call_and_fresh_identifier_authority": "HELD_ON_171",
        "gate": "FAIL" if failures else "HELD",
        "reasons": failures or ["cross-call replay is unrepresentable in v1"],
    }


FACTOR_VALUES = {
    "predicted_harm": NONNEG_GRID_5,
    "prediction_error": NONNEG_GRID_5,
    "controllability": NONNEG_GRID_5,
    "goal_progress": SIGNED_GRID_5,
    "norm_violation": NONNEG_GRID_5,
    "affiliation_delta": SIGNED_GRID_5,
}


def factor_q(name: str, value: float) -> controller.AppraisalVector:
    if name == "predicted_harm":
        return controller.AppraisalVector(predicted_harm=value)
    if name == "prediction_error":
        return controller.AppraisalVector(prediction_error=value)
    if name == "controllability":
        return controller.AppraisalVector(
            predicted_harm=0.75, controllability=value
        )
    if name == "goal_progress":
        return controller.AppraisalVector(
            controllability=0.75, goal_progress=value
        )
    if name == "norm_violation":
        return controller.AppraisalVector(
            controllability=0.75, norm_violation=value
        )
    if name == "affiliation_delta":
        return controller.AppraisalVector(affiliation_delta=value)
    raise ValueError(f"unknown factor {name!r}")


def factor_initial(name: str) -> tuple[float, ...]:
    if name == "affiliation_delta":
        return (0.5, 0.0, 0.0, 1.0, 0.0)
    return baseline_state()


def fine_factor_values(name: str) -> tuple[float, ...]:
    if name in {"goal_progress", "affiliation_delta"}:
        return tuple(-1.0 + index / 256.0 for index in range(513))
    return tuple(index / 256.0 for index in range(257))


def _monotonic(
    values: Sequence[float], *, nondecreasing: bool, tolerance: float = 1e-12
) -> bool:
    if nondecreasing:
        return all(a <= b + tolerance for a, b in zip(values, values[1:]))
    return all(a + tolerance >= b for a, b in zip(values, values[1:]))


def _dead_intervals(
    values: Sequence[float], outputs: Sequence[Sequence[float]]
) -> list[dict[str, str]]:
    intervals = []
    start: int | None = None
    for index, (left, right) in enumerate(zip(outputs, outputs[1:])):
        dead = max_abs_delta(left, right) <= 1e-9
        if dead and start is None:
            start = index
        if start is not None and (not dead or index == len(outputs) - 2):
            end = index if dead and index == len(outputs) - 2 else index - 1
            intervals.append(
                {
                    "start": f17(values[start]),
                    "end": f17(values[end + 1]),
                    "width": f17(values[end + 1] - values[start]),
                }
            )
            start = None
    return intervals


def _factor_checkpoints(
    q: controller.AppraisalVector, initial: Sequence[float]
) -> tuple[tuple[float, ...], tuple[float, ...], bool]:
    current = tuple(initial)
    horizon4: tuple[float, ...] | None = None
    finite_bounded = True
    for tick in range(1, 257):
        previous = current
        current = transition(current, q)
        finite_bounded = finite_bounded and all(
            math.isfinite(value) and 0.0 <= value <= 1.0 for value in current
        )
        if tick == 4:
            horizon4 = current
        if tick >= 4 and current == previous:
            break
    if horizon4 is None:
        raise RuntimeError("horizon-4 checkpoint was not captured")
    return horizon4, current, finite_bounded


def audit_fine_state_grid() -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    stream = StreamSummary()
    failures = []
    deadband_failure_count = 0
    bounded = True
    global_max_jump = 0.0
    global_witness = None
    terminal_minima = [1.0] * 5
    terminal_maxima = [0.0] * 5
    terminal_zero = [0] * 5
    terminal_one = [0] * 5
    state_summaries = []

    for name in Q_FIELDS:
        print(f"  fine state grid: {name}", file=sys.stderr)
        values = fine_factor_values(name)
        q_values = [factor_q(name, value) for value in values]
        for initial_id, initial in enumerate(STATE_GRID_3):
            horizon4_outputs = []
            terminal_outputs = []
            for value, q in zip(values, q_values, strict=True):
                horizon4, terminal, row_bounded = _factor_checkpoints(q, initial)
                bounded = bounded and row_bounded
                horizon4_outputs.append(horizon4)
                terminal_outputs.append(terminal)
                row = {
                    "factor": name,
                    "value": f17(value),
                    "initial_id": initial_id,
                    "initial": float_list(initial),
                    "horizon4": float_list(horizon4),
                    "terminal256": float_list(terminal),
                    "finite_bounded": row_bounded,
                }
                stream.add(row)
                if not row_bounded:
                    stream.fail("nonfinite_or_unbounded", row)
                for index, item in enumerate(terminal):
                    terminal_minima[index] = min(terminal_minima[index], item)
                    terminal_maxima[index] = max(terminal_maxima[index], item)
                    terminal_zero[index] += item == 0.0
                    terminal_one[index] += item == 1.0

            dead_intervals = _dead_intervals(values, horizon4_outputs)
            widest = max(
                (float(item["width"]) for item in dead_intervals), default=0.0
            )
            if widest > 0.25 + 1e-12:
                deadband_failure_count += 1
                stream.fail(
                    "undeclared_deadband",
                    {
                        "factor": name,
                        "initial_id": initial_id,
                        "initial": float_list(initial),
                        "widest_deadband": f17(widest),
                        "intervals": dead_intervals,
                    },
                )

            local_max_jump = 0.0
            local_witness = None
            for index, (left, right) in enumerate(
                zip(terminal_outputs, terminal_outputs[1:])
            ):
                jump = max_abs_delta(left, right)
                if jump > local_max_jump:
                    local_max_jump = jump
                    local_witness = {
                        "factor": name,
                        "initial_id": initial_id,
                        "initial": float_list(initial),
                        "left": f17(values[index]),
                        "right": f17(values[index + 1]),
                        "left_terminal": float_list(left),
                        "right_terminal": float_list(right),
                        "max_abs_jump": f17(jump),
                    }
                if jump > global_max_jump:
                    global_max_jump = jump
                    global_witness = local_witness
            if local_max_jump > 0.10 + 1e-12 and local_witness is not None:
                stream.fail("adjacent_terminal_jump", local_witness)
            state_summaries.append(
                {
                    "factor": name,
                    "initial_id": initial_id,
                    "widest_deadband": f17(widest),
                    "terminal_256_max_jump": f17(local_max_jump),
                }
            )

    expected_count = 499_122
    if stream.count != expected_count:
        failures.append(
            f"fine state-grid row count is {stream.count}, expected {expected_count}"
        )
    if not bounded:
        failures.append("fine state-grid sweep produced nonfinite or unbounded state")
    if deadband_failure_count:
        failures.append(
            f"{deadband_failure_count} factor/state rows have an undeclared "
            "deadband wider than 0.25"
        )
    record = stream.record()
    record.update(
        {
            "state_summaries": state_summaries,
            "deadband_failure_count": deadband_failure_count,
            "bounded": bounded,
            "terminal_minima": dict(
                zip(STATE_FIELDS, float_list(terminal_minima), strict=True)
            ),
            "terminal_maxima": dict(
                zip(STATE_FIELDS, float_list(terminal_maxima), strict=True)
            ),
            "terminal_exact_zero_occupancy": dict(
                zip(STATE_FIELDS, terminal_zero, strict=True)
            ),
            "terminal_exact_one_occupancy": dict(
                zip(STATE_FIELDS, terminal_one, strict=True)
            ),
            "max_adjacent_terminal_jump": f17(global_max_jump),
            "max_adjacent_terminal_witness": global_witness,
            "pass": not failures,
            "reasons": failures,
        }
    )
    return (
        record,
        {"max_jump": global_max_jump, "witness": global_witness},
        failures,
    )


def audit_factor_responses() -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    failures: list[str] = []
    factor_rows: dict[str, Any] = {}
    adjacent_global_max = 0.0
    adjacent_global_witness: dict[str, Any] | None = None

    for name in Q_FIELDS:
        initial = factor_initial(name)
        coarse_states: dict[float, dict[int, tuple[float, ...]]] = {}
        rows = []
        for value in FACTOR_VALUES[name]:
            trajectory = simulate(factor_q(name, value), 8, initial)
            horizons = {horizon: trajectory[horizon] for horizon in (1, 4, 8)}
            coarse_states[value] = horizons
            rows.append(
                {
                    "value": f17(value),
                    "states": {
                        str(horizon): float_list(horizons[horizon])
                        for horizon in (1, 4, 8)
                    },
                }
            )

        factor_reasons = []
        for horizon in (1, 4, 8):
            ordered = [coarse_states[value][horizon] for value in FACTOR_VALUES[name]]
            if name == "predicted_harm":
                checks = (
                    _monotonic([state[2] for state in ordered], nondecreasing=True),
                    _monotonic([state[3] for state in ordered], nondecreasing=False),
                )
            elif name == "prediction_error":
                checks = (
                    _monotonic([state[2] for state in ordered], nondecreasing=True),
                )
            elif name == "controllability":
                checks = (
                    _monotonic([state[1] for state in ordered], nondecreasing=True),
                    _monotonic([state[3] for state in ordered], nondecreasing=True),
                    _monotonic([state[4] for state in ordered], nondecreasing=False),
                )
            elif name == "goal_progress":
                negative = ordered[:3]
                checks = (
                    _monotonic(
                        [state[1] for state in negative], nondecreasing=False
                    ),
                )
            elif name == "norm_violation":
                checks = (
                    _monotonic([state[0] for state in ordered], nondecreasing=True),
                    _monotonic([state[1] for state in ordered], nondecreasing=True),
                )
            else:
                checks = (
                    _monotonic([state[0] for state in ordered], nondecreasing=True),
                )
            if not all(checks):
                factor_reasons.append(f"monotonicity failed at horizon {horizon}")

        if name in {"predicted_harm", "prediction_error", "norm_violation"}:
            if name in {"predicted_harm", "prediction_error"}:
                witness = max(
                    abs(coarse_states[0.0][h][2] - coarse_states[0.25][h][2])
                    for h in (1, 4, 8)
                )
            else:
                witness = max(
                    max(
                        abs(
                            coarse_states[0.0][h][index]
                            - coarse_states[0.25][h][index]
                        )
                        for index in (0, 1)
                    )
                    for h in (1, 4, 8)
                )
            if witness < 0.01:
                factor_reasons.append(
                    f"0 to 0.25 witness {f17(witness)} is below 0.01"
                )
        elif name == "controllability":
            witness = max(
                max(
                    abs(
                        coarse_states[left][h][index]
                        - coarse_states[right][h][index]
                    )
                    for index in (1, 3, 4)
                )
                for left, right in zip(NONNEG_GRID_5, NONNEG_GRID_5[1:])
                for h in (1, 4, 8)
            )
            if witness < 0.01:
                factor_reasons.append("no adjacent controllability witness")
        elif name == "goal_progress":
            negative_witness = max(
                abs(coarse_states[-1.0][h][1] - coarse_states[0.0][h][1])
                for h in (1, 4, 8)
            )
            positive_witness = max(
                abs(coarse_states[0.0][h][1] - coarse_states[value][h][1])
                for value in (0.5, 1.0)
                for h in (1, 4, 8)
            )
            witness = max(negative_witness, positive_witness)
            if negative_witness < 0.01:
                factor_reasons.append("negative goal progress does not raise agency")
            if positive_witness < 0.01:
                factor_reasons.append("positive goal progress is dynamically inert")
        else:
            negative_witness = max(
                coarse_states[0.0][h][0] - coarse_states[-0.5][h][0]
                for h in (1, 4, 8)
            )
            positive_witness = max(
                coarse_states[0.5][h][0] - coarse_states[0.0][h][0]
                for h in (1, 4, 8)
            )
            witness = min(negative_witness, positive_witness)
            if negative_witness < 0.01:
                factor_reasons.append("negative affiliation does not lower affiliation")
            if positive_witness < 0.01:
                factor_reasons.append("positive affiliation does not raise affiliation")

        fine_values = fine_factor_values(name)
        fine_outputs = [
            simulate(factor_q(name, value), 4, initial)[-1]
            for value in fine_values
        ]
        dead_intervals = _dead_intervals(fine_values, fine_outputs)
        widest_deadband = max(
            (float(item["width"]) for item in dead_intervals), default=0.0
        )
        if widest_deadband > 0.25 + 1e-12:
            factor_reasons.append(
                f"undeclared deadband width {f17(widest_deadband)} exceeds 0.25"
            )
        responding = [
            index
            for index, (left, right) in enumerate(
                zip(fine_outputs, fine_outputs[1:])
            )
            if max_abs_delta(left, right) > 1e-9
        ]

        terminal_outputs = [
            simulate(factor_q(name, value), 256, initial)[-1]
            for value in fine_values
        ]
        adjacent = []
        factor_max_jump = 0.0
        for index, (left, right) in enumerate(
            zip(terminal_outputs, terminal_outputs[1:])
        ):
            jump = max_abs_delta(left, right)
            if jump > factor_max_jump:
                factor_max_jump = jump
            if jump > adjacent_global_max:
                adjacent_global_max = jump
                adjacent_global_witness = {
                    "factor": name,
                    "left": f17(fine_values[index]),
                    "right": f17(fine_values[index + 1]),
                    "left_terminal": float_list(left),
                    "right_terminal": float_list(right),
                    "max_abs_jump": f17(jump),
                }
            adjacent.append(f17(jump))
        failures.extend(f"{name}: {reason}" for reason in factor_reasons)
        factor_rows[name] = {
            "initial_state": float_list(initial),
            "coarse": rows,
            "named_witness_best": f17(witness),
            "fine_horizon_4": [
                {"value": f17(value), "state": float_list(state)}
                for value, state in zip(fine_values, fine_outputs)
            ],
            "dead_intervals": dead_intervals,
            "smallest_tested_responding_change": (
                f17(1.0 / 256.0) if responding else None
            ),
            "terminal_256_adjacent_jumps": adjacent,
            "terminal_256": [
                {"value": f17(value), "state": float_list(state)}
                for value, state in zip(fine_values, terminal_outputs)
            ],
            "terminal_256_max_jump": f17(factor_max_jump),
            "reasons": factor_reasons,
        }

    fine_state_grid, full_adjacent, fine_grid_failures = audit_fine_state_grid()
    failures.extend(fine_grid_failures)
    adjacent_global_max = full_adjacent["max_jump"]
    adjacent_global_witness = full_adjacent["witness"]

    matrix = StreamSummary()
    bounded = True
    matrix_minima = [1.0] * 5
    matrix_maxima = [0.0] * 5
    matrix_zero = [0] * 5
    matrix_one = [0] * 5
    for name in Q_FIELDS:
        for value in FACTOR_VALUES[name]:
            q = factor_q(name, value)
            for initial_id, initial in enumerate(STATE_GRID_3):
                output = transition(initial, q)
                row = {
                    "factor": name,
                    "value": f17(value),
                    "initial_id": initial_id,
                    "initial": float_list(initial),
                    "output": float_list(output),
                }
                matrix.add(row)
                if not all(math.isfinite(item) and 0.0 <= item <= 1.0 for item in output):
                    bounded = False
                    matrix.fail("nonfinite_or_unbounded", row)
                for index, item in enumerate(output):
                    matrix_minima[index] = min(matrix_minima[index], item)
                    matrix_maxima[index] = max(matrix_maxima[index], item)
                    matrix_zero[index] += item == 0.0
                    matrix_one[index] += item == 1.0
    matrix_record = matrix.record()
    matrix_record["bounded"] = bounded
    matrix_record["minima"] = dict(
        zip(STATE_FIELDS, float_list(matrix_minima), strict=True)
    )
    matrix_record["maxima"] = dict(
        zip(STATE_FIELDS, float_list(matrix_maxima), strict=True)
    )
    matrix_record["exact_zero_occupancy"] = dict(
        zip(STATE_FIELDS, matrix_zero, strict=True)
    )
    matrix_record["exact_one_occupancy"] = dict(
        zip(STATE_FIELDS, matrix_one, strict=True)
    )
    if matrix.count != 7290:
        failures.append(f"one-factor matrix row count is {matrix.count}, expected 7290")
    if not bounded:
        failures.append("one-factor matrix produced nonfinite or unbounded state")

    return (
        {
            "factors": factor_rows,
            "fine_state_grid": fine_state_grid,
            "one_factor_matrix": matrix_record,
            "adjacent_global_max_jump": f17(adjacent_global_max),
            "adjacent_global_witness": adjacent_global_witness,
            "gate": "FAIL" if failures else "PASS",
            "reasons": failures,
        },
        {
            "max_jump": adjacent_global_max,
            "witness": adjacent_global_witness,
        },
        failures,
    )


def audit_coarse_cartesian() -> tuple[dict[str, Any], list[str]]:
    stream = StreamSummary()
    minima = [1.0] * 5
    maxima = [0.0] * 5
    zero_occupancy = [0] * 5
    one_occupancy = [0] * 5
    max_reconciliation = 0.0
    failures: list[str] = []
    grids = (
        NONNEG_GRID_5,
        NONNEG_GRID_5,
        NONNEG_GRID_5,
        SIGNED_GRID_5,
        NONNEG_GRID_5,
        SIGNED_GRID_5,
    )
    for q_id, values in enumerate(itertools.product(*grids)):
        q = controller.AppraisalVector(*values)
        for state_id, initial in enumerate(STATE_CORNERS):
            actual = transition(initial, q)
            raw, expected = independent_transition(initial, q)
            reconciliation = max_abs_delta(actual, expected)
            max_reconciliation = max(max_reconciliation, reconciliation)
            row = {
                "q_id": q_id,
                "state_id": state_id,
                "q": float_list(values),
                "initial": float_list(initial),
                "preclip": float_list(raw),
                "output": float_list(actual),
            }
            stream.add(row)
            finite_bounded = all(
                math.isfinite(value) and 0.0 <= value <= 1.0 for value in actual
            )
            if not finite_bounded:
                stream.fail("nonfinite_or_unbounded", row)
            if reconciliation > 1e-12:
                stream.fail("transition_reconciliation", row)
            for index, value in enumerate(actual):
                minima[index] = min(minima[index], value)
                maxima[index] = max(maxima[index], value)
                zero_occupancy[index] += value == 0.0
                one_occupancy[index] += value == 1.0
    if stream.count != 500_000:
        failures.append(f"coarse sweep count is {stream.count}, expected 500000")
    if stream._failures.get("nonfinite_or_unbounded"):
        failures.append("coarse sweep produced nonfinite or unbounded output")
    if max_reconciliation > 1e-12:
        failures.append(
            f"independent transition mismatch {f17(max_reconciliation)} exceeds 1e-12"
        )
    record = stream.record()
    record.update(
        {
            "minima": dict(zip(STATE_FIELDS, float_list(minima), strict=True)),
            "maxima": dict(zip(STATE_FIELDS, float_list(maxima), strict=True)),
            "exact_zero_occupancy": dict(
                zip(STATE_FIELDS, zero_occupancy, strict=True)
            ),
            "exact_one_occupancy": dict(
                zip(STATE_FIELDS, one_occupancy, strict=True)
            ),
            "max_transition_reconciliation": f17(max_reconciliation),
            "pass": not failures,
            "reasons": failures,
        }
    )
    return record, failures


def minimal_period(
    history: Sequence[Sequence[float]],
    *,
    minimum: int = 1,
    maximum: int = 32,
    tolerance: float = 1e-8,
) -> int | None:
    for period in range(minimum, maximum + 1):
        required = 4 * period
        if len(history) < required:
            continue
        tail = history[-required:]
        matches = True
        for block in range(1, 4):
            for offset in range(period):
                if (
                    max_abs_delta(
                        tail[offset], tail[block * period + offset]
                    )
                    > tolerance
                ):
                    matches = False
                    break
            if not matches:
                break
        if matches:
            return period
    return None


def classify_constant_trajectory(
    q: controller.AppraisalVector,
    initial: Sequence[float],
    horizon: int,
) -> dict[str, Any]:
    current = tuple(initial)
    history: deque[tuple[float, ...]] = deque([current], maxlen=128)
    stable_ticks = 0
    finite_bounded = True
    for tick in range(1, horizon + 1):
        following = transition(current, q)
        finite_bounded = finite_bounded and all(
            math.isfinite(value) and 0.0 <= value <= 1.0
            for value in following
        )
        delta = max_abs_delta(current, following)
        stable_ticks = stable_ticks + 1 if delta <= 1e-10 else 0
        current = following
        history.append(current)
        if stable_ticks >= 32:
            residual = max_abs_delta(current, transition(current, q))
            if residual <= 1e-9:
                return {
                    "classification": "fixed",
                    "tick": tick,
                    "period": 1,
                    "terminal": current,
                    "residual": residual,
                    "finite_bounded": finite_bounded,
                }
    residual = max_abs_delta(current, transition(current, q))
    if stable_ticks >= 32 and residual <= 1e-9:
        classification = "fixed"
        period = 1
    elif residual > 1e-8:
        period = minimal_period(tuple(history), minimum=2)
        classification = "cycle" if period is not None else "unclassified"
    else:
        period = None
        classification = "unclassified"
    return {
        "classification": classification,
        "tick": horizon,
        "period": period,
        "terminal": current,
        "residual": residual,
        "finite_bounded": finite_bounded,
    }


def _complete_link_distance(
    left: Sequence[int], right: Sequence[int], states: Sequence[Sequence[float]]
) -> float:
    return max(max_abs_delta(states[a], states[b]) for a in left for b in right)


def complete_link_clusters(
    states: Sequence[Sequence[float]], member_ids: Sequence[str]
) -> list[dict[str, Any]]:
    ordering = sorted(
        range(len(states)), key=lambda index: (tuple(states[index]), member_ids[index])
    )
    clusters: list[tuple[int, ...]] = [(index,) for index in ordering]
    while True:
        candidates = []
        for left_index in range(len(clusters)):
            for right_index in range(left_index + 1, len(clusters)):
                distance = _complete_link_distance(
                    clusters[left_index], clusters[right_index], states
                )
                if distance <= 1e-6:
                    left_ids = tuple(sorted(member_ids[i] for i in clusters[left_index]))
                    right_ids = tuple(
                        sorted(member_ids[i] for i in clusters[right_index])
                    )
                    candidates.append(
                        (
                            distance,
                            left_ids,
                            right_ids,
                            left_index,
                            right_index,
                        )
                    )
        if not candidates:
            break
        _, _, _, left_index, right_index = min(candidates)
        merged = tuple(sorted(clusters[left_index] + clusters[right_index]))
        clusters = [
            cluster
            for index, cluster in enumerate(clusters)
            if index not in {left_index, right_index}
        ]
        clusters.append(merged)
        clusters.sort(key=lambda group: tuple(sorted(member_ids[i] for i in group)))

    output = []
    for cluster in clusters:
        representative = tuple(
            sum(states[index][axis] for index in cluster) / len(cluster)
            for axis in range(5)
        )
        diameter = max(
            (
                max_abs_delta(states[a], states[b])
                for a in cluster
                for b in cluster
            ),
            default=0.0,
        )
        output.append(
            {
                "members": sorted(member_ids[index] for index in cluster),
                "representative": representative,
                "diameter": diameter,
            }
        )
    output.sort(key=lambda item: (item["representative"], item["members"]))
    return output


def boundary_pairs() -> tuple[tuple[float, float], ...]:
    pairs = []
    for controllability in NONNEG_GRID_5:
        high = 2.0 / (5.0 - 2.25 * controllability)
        k = 68.0 * (1.0 - controllability) / 19.0
        if controllability <= 116.0 / 137.0:
            low = (
                5.0
                + 2.0 * k
                - 2.25 * controllability
                - math.sqrt(
                    (5.0 + 2.0 * k - 2.25 * controllability) ** 2
                    - 16.0 * k
                )
            ) / (4.0 * k)
        else:
            low = (4.0 * controllability - 2.0) / (
                1.0 + 1.75 * controllability
            )
        candidates = [index / 10.0 for index in range(11)]
        candidates.extend((low, high, (low + high) / 2.0))
        candidates.extend(
            boundary + offset
            for boundary in (low, high)
            for offset in (-0.001, 0.001)
        )
        for drive in sorted({value for value in candidates if 0.0 <= value <= 1.0}):
            pairs.append((controllability, drive))
    if len(pairs) != 85:
        raise RuntimeError(f"boundary construction produced {len(pairs)} pairs")
    return tuple(pairs)


def named_scenarios() -> dict[str, controller.AppraisalVector]:
    return {
        "neutral": controller.AppraisalVector(),
        "error_only": controller.AppraisalVector(prediction_error=1.0),
        "positive_progress": controller.AppraisalVector(
            goal_progress=1.0, controllability=0.75
        ),
        "repair": controller.AppraisalVector(
            norm_violation=1.0, controllability=0.75
        ),
        "moderate_controlled": controller.AppraisalVector(
            predicted_harm=0.5, controllability=0.75
        ),
        "moderate_uncontrolled": controller.AppraisalVector(
            predicted_harm=0.5, controllability=0.25
        ),
        "extreme_unresolved": controller.AppraisalVector(
            predicted_harm=1.0,
            prediction_error=1.0,
            controllability=0.0,
            goal_progress=-1.0,
            norm_violation=1.0,
            affiliation_delta=-1.0,
        ),
        "affiliation_gain": controller.AppraisalVector(affiliation_delta=1.0),
        "affiliation_loss": controller.AppraisalVector(affiliation_delta=-1.0),
    }


def _portrait_row(
    label: str,
    q: controller.AppraisalVector,
    horizon: int,
    stream: StreamSummary,
) -> tuple[dict[str, Any], list[tuple[float, ...]], list[str]]:
    terminals = []
    member_ids = []
    classifications = defaultdict(int)
    failures = []
    for initial_id, initial in enumerate(STATE_CORNERS):
        result = classify_constant_trajectory(q, initial, horizon)
        terminal = result["terminal"]
        terminals.append(terminal)
        member_id = f"corner-{initial_id:02d}"
        member_ids.append(member_id)
        classifications[result["classification"]] += 1
        row = {
            "label": label,
            "initial_id": member_id,
            "initial": float_list(initial),
            "classification": result["classification"],
            "period": result["period"],
            "tick": result["tick"],
            "terminal": float_list(terminal),
            "residual": f17(result["residual"]),
            "finite_bounded": result["finite_bounded"],
        }
        stream.add(row)
        if result["classification"] == "cycle":
            failures.append(f"{label}: autonomous period-{result['period']} cycle")
            stream.fail("autonomous_cycle", row)
        elif result["classification"] == "unclassified":
            failures.append(f"{label}: unclassified within horizon")
            stream.fail("unclassified", row)
        if not result["finite_bounded"]:
            failures.append(f"{label}: nonfinite or unbounded trajectory")
            stream.fail("nonfinite_or_unbounded", row)
    clusters = complete_link_clusters(terminals, member_ids)
    terminal_minima = [min(state[index] for state in terminals) for index in range(5)]
    terminal_maxima = [max(state[index] for state in terminals) for index in range(5)]
    terminal_zero = [
        sum(state[index] == 0.0 for state in terminals) for index in range(5)
    ]
    terminal_one = [
        sum(state[index] == 1.0 for state in terminals) for index in range(5)
    ]
    record = {
        "label": label,
        "q": q_record(q),
        "horizon": horizon,
        "classification_counts": dict(sorted(classifications.items())),
        "terminal_minima": dict(
            zip(STATE_FIELDS, float_list(terminal_minima), strict=True)
        ),
        "terminal_maxima": dict(
            zip(STATE_FIELDS, float_list(terminal_maxima), strict=True)
        ),
        "terminal_exact_zero_occupancy": dict(
            zip(STATE_FIELDS, terminal_zero, strict=True)
        ),
        "terminal_exact_one_occupancy": dict(
            zip(STATE_FIELDS, terminal_one, strict=True)
        ),
        "cluster_count": len(clusters),
        "clusters": [
            {
                "members": cluster["members"],
                "representative": float_list(cluster["representative"]),
                "diameter": f17(cluster["diameter"]),
            }
            for cluster in clusters
        ],
    }
    representatives = [tuple(cluster["representative"]) for cluster in clusters]
    return record, representatives, failures


def _portrait_aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    classification_counts: dict[str, int] = defaultdict(int)
    cluster_counts: dict[str, int] = defaultdict(int)
    minima = [1.0] * 5
    maxima = [0.0] * 5
    zero = [0] * 5
    one = [0] * 5
    for row in rows:
        for name, count in row["classification_counts"].items():
            classification_counts[name] += count
        cluster_counts[str(row["cluster_count"])] += 1
        for index, field in enumerate(STATE_FIELDS):
            minima[index] = min(minima[index], float(row["terminal_minima"][field]))
            maxima[index] = max(maxima[index], float(row["terminal_maxima"][field]))
            zero[index] += row["terminal_exact_zero_occupancy"][field]
            one[index] += row["terminal_exact_one_occupancy"][field]
    return {
        "classification_counts": dict(sorted(classification_counts.items())),
        "cluster_count_distribution": dict(sorted(cluster_counts.items())),
        "terminal_minima": dict(zip(STATE_FIELDS, float_list(minima), strict=True)),
        "terminal_maxima": dict(zip(STATE_FIELDS, float_list(maxima), strict=True)),
        "terminal_exact_zero_occupancy": dict(
            zip(STATE_FIELDS, zero, strict=True)
        ),
        "terminal_exact_one_occupancy": dict(
            zip(STATE_FIELDS, one, strict=True)
        ),
    }


def audit_periodic_matrix(
    scenarios: dict[str, controller.AppraisalVector]
) -> tuple[dict[str, Any], list[str]]:
    neutral = scenarios["neutral"]
    rows = []
    failures = []
    stream = StreamSummary()
    period_counts: dict[str, int] = defaultdict(int)
    terminal_minima = [1.0] * 5
    terminal_maxima = [0.0] * 5
    terminal_zero = [0] * 5
    terminal_one = [0] * 5
    for name, scenario in scenarios.items():
        if name == "neutral":
            continue
        for initial_id, initial in enumerate(STATE_CORNERS):
            current = initial
            history: deque[tuple[float, ...]] = deque([current], maxlen=128)
            finite_bounded = True
            for tick in range(1, 4097):
                q = neutral if tick % 2 else scenario
                current = transition(current, q)
                history.append(current)
                finite_bounded = finite_bounded and all(
                    math.isfinite(value) and 0.0 <= value <= 1.0
                    for value in current
                )
            period = minimal_period(tuple(history))
            after_two = transition(transition(current, neutral), scenario)
            poincare_residual = max_abs_delta(current, after_two)

            washout = [current]
            washed = current
            for _ in range(128):
                washed = transition(washed, neutral)
                washout.append(washed)
            washout_minimal_period = minimal_period(washout)
            washout_period = (
                washout_minimal_period
                if washout_minimal_period is not None and washout_minimal_period > 1
                else None
            )
            reason = None
            if period not in {1, 2}:
                reason = f"forced response period is {period}"
            elif poincare_residual > 1e-8:
                reason = (
                    "forced response is not phase-locked: Poincare residual "
                    f"{f17(poincare_residual)}"
                )
            elif not finite_bounded:
                reason = "forced trajectory is nonfinite or unbounded"
            elif washout_period is not None:
                reason = f"period-{washout_period} remains after neutral washout"
            row = {
                "scenario": name,
                "initial_id": f"corner-{initial_id:02d}",
                "period": period,
                "poincare_residual": f17(poincare_residual),
                "washout_period": washout_period,
                "terminal": float_list(current),
                "washout_terminal": float_list(washed),
                "finite_bounded": finite_bounded,
                "reason": reason,
            }
            stream.add(row)
            rows.append(row)
            period_counts[str(period)] += 1
            for index, value in enumerate(current):
                terminal_minima[index] = min(terminal_minima[index], value)
                terminal_maxima[index] = max(terminal_maxima[index], value)
                terminal_zero[index] += value == 0.0
                terminal_one[index] += value == 1.0
            if reason:
                failures.append(f"{name}/corner-{initial_id:02d}: {reason}")
                stream.fail(reason, row)
    if stream.count != 256:
        failures.append(f"periodic matrix count is {stream.count}, expected 256")
    record = stream.record()
    record["rows"] = rows
    record["period_counts"] = dict(sorted(period_counts.items()))
    record["terminal_minima"] = dict(
        zip(STATE_FIELDS, float_list(terminal_minima), strict=True)
    )
    record["terminal_maxima"] = dict(
        zip(STATE_FIELDS, float_list(terminal_maxima), strict=True)
    )
    record["terminal_exact_zero_occupancy"] = dict(
        zip(STATE_FIELDS, terminal_zero, strict=True)
    )
    record["terminal_exact_one_occupancy"] = dict(
        zip(STATE_FIELDS, terminal_one, strict=True)
    )
    record["pass"] = not failures
    record["reasons"] = failures
    return record, failures


def audit_phase_portrait(
    adjacent: dict[str, Any], coarse: dict[str, Any]
) -> tuple[dict[str, Any], list[tuple[float, ...]], list[str]]:
    failures: list[str] = []
    held_reasons: list[str] = []
    discovered: list[tuple[float, ...]] = []
    stationary_stream = StreamSummary()
    boundary_stream = StreamSummary()
    stationary_rows = []
    max_clusters = 0

    if coarse["row_count"] != 500_000:
        failures.append("coarse Cartesian sweep did not contain 500000 rows")
    if coarse["failure_witnesses"].get("nonfinite_or_unbounded"):
        failures.append("coarse Cartesian sweep produced nonfinite or unbounded state")

    stationary_grids = (
        (0.0, 0.5, 1.0),
        (0.0, 0.5, 1.0),
        (0.0, 0.5, 1.0),
        (-1.0, 0.0, 1.0),
        (0.0, 0.5, 1.0),
        (-1.0, 0.0, 1.0),
    )
    for q_id, values in enumerate(itertools.product(*stationary_grids)):
        q = controller.AppraisalVector(*values)
        row, representatives, row_failures = _portrait_row(
            f"stationary-{q_id:03d}", q, 4096, stationary_stream
        )
        stationary_rows.append(row)
        discovered.extend(representatives)
        failures.extend(row_failures)
        max_clusters = max(max_clusters, row["cluster_count"])
        if row["cluster_count"] == 2:
            held_reasons.append(f"{row['label']}: two attractors")
        elif row["cluster_count"] > 2:
            failures.append(f"{row['label']}: {row['cluster_count']} attractors")

    boundary_rows = []
    for pair_id, (controllability, drive) in enumerate(boundary_pairs()):
        q = controller.AppraisalVector(
            predicted_harm=drive,
            prediction_error=drive,
            controllability=controllability,
        )
        row, representatives, row_failures = _portrait_row(
            f"boundary-{pair_id:02d}", q, 20_000, boundary_stream
        )
        row["controllability"] = f17(controllability)
        row["drive"] = f17(drive)
        boundary_rows.append(row)
        discovered.extend(representatives)
        failures.extend(row_failures)
        max_clusters = max(max_clusters, row["cluster_count"])
        if row["cluster_count"] == 2:
            held_reasons.append(f"{row['label']}: two attractors")
        elif row["cluster_count"] > 2:
            failures.append(f"{row['label']}: {row['cluster_count']} attractors")

    scenarios = named_scenarios()
    named_rows = []
    named_stream = StreamSummary()
    for name, q in scenarios.items():
        row, representatives, row_failures = _portrait_row(
            name, q, 4096, named_stream
        )
        named_rows.append(row)
        discovered.extend(representatives)
        failures.extend(row_failures)
        max_clusters = max(max_clusters, row["cluster_count"])
        if row["cluster_count"] == 2:
            held_reasons.append(f"{name}: two attractors")
        elif row["cluster_count"] > 2:
            failures.append(f"{name}: {row['cluster_count']} attractors")
        if name in {"moderate_controlled", "moderate_uncontrolled"}:
            for cluster in row["clusters"]:
                terminal = [float(value) for value in cluster["representative"]]
                if terminal[2] >= 0.8 and terminal[4] >= 0.8:
                    failures.append(
                        f"{name}: vigilance and load both end at or above 0.8"
                    )

    neutral_row = next(row for row in named_rows if row["label"] == "neutral")
    if neutral_row["cluster_count"] != 1:
        failures.append("neutral does not have exactly one attractor")
    else:
        representative = [
            float(value) for value in neutral_row["clusters"][0]["representative"]
        ]
        if max_abs_delta(representative, baseline_state()) > 1e-6:
            failures.append("neutral attractor is not baseline within 1e-6")

    if adjacent["max_jump"] > 0.10 + 1e-12:
        failures.append(
            "adjacent 1/256 terminal jump exceeds 0.10: "
            f"{f17(adjacent['max_jump'])}"
        )

    periodic, periodic_failures = audit_periodic_matrix(scenarios)
    failures.extend(periodic_failures)
    gate = "FAIL" if failures else ("HELD" if held_reasons else "PASS")

    stationary_summary = stationary_stream.record()
    stationary_summary["q_count"] = len(stationary_rows)
    stationary_summary["aggregate"] = _portrait_aggregate(stationary_rows)
    stationary_summary["rows"] = stationary_rows
    boundary_summary = boundary_stream.record()
    boundary_summary["pair_count"] = len(boundary_rows)
    boundary_summary["aggregate"] = _portrait_aggregate(boundary_rows)
    boundary_summary["rows"] = boundary_rows
    named_summary = named_stream.record()
    named_summary["aggregate"] = _portrait_aggregate(named_rows)
    named_summary["rows"] = named_rows

    return (
        {
            "stationary": stationary_summary,
            "boundary": boundary_summary,
            "named": named_summary,
            "periodic": periodic,
            "max_cluster_count": max_clusters,
            "adjacent_terminal_jump": {
                "max": f17(adjacent["max_jump"]),
                "witness": adjacent["witness"],
            },
            "gate": gate,
            "reasons": failures if failures else held_reasons,
            "held_reasons": held_reasons,
        },
        discovered,
        failures,
    )


def _threshold_crossing(
    trajectory: Sequence[Sequence[float]],
    coordinate: int,
    threshold: float,
    *,
    upper: bool,
) -> int | None:
    for tick in range(1, len(trajectory)):
        previous = trajectory[tick - 1][coordinate]
        current = trajectory[tick][coordinate]
        if upper and previous > threshold and current <= threshold:
            return tick
        if not upper and previous < threshold and current >= threshold:
            return tick
    return None


def _first_passage(
    trajectory: Sequence[Sequence[float]],
    coordinate: int,
    threshold: float,
    *,
    upper: bool,
) -> int | None:
    for tick, state in enumerate(trajectory):
        value = state[coordinate]
        if (upper and value <= threshold) or (not upper and value >= threshold):
            return tick
    return None


def _rebound_failures(
    trajectory: Sequence[Sequence[float]], label: str
) -> list[str]:
    failures = []
    checks = (
        (0, 0.001, True, "affiliation"),
        (1, 0.001, True, "agency"),
        (2, 1e-6, True, "vigilance_1e-6"),
        (2, 0.001, True, "vigilance_0.001"),
        (3, 0.99, False, "reserve_0.99"),
        (3, 0.999, False, "reserve_0.999"),
        (4, 0.01, True, "load_0.01"),
        (4, 0.001, True, "load_0.001"),
    )
    for coordinate, threshold, upper, name in checks:
        crossing = _threshold_crossing(
            trajectory, coordinate, threshold, upper=upper
        )
        if crossing is None:
            continue
        later = [state[coordinate] for state in trajectory[crossing:]]
        if upper and max(later) > threshold + 1e-9:
            failures.append(f"{label}: {name} rebounds after tick {crossing}")
        if not upper and min(later) < threshold - 1e-9:
            failures.append(f"{label}: {name} rebounds after tick {crossing}")
    return failures


def audit_recovery(
    discovered: Sequence[Sequence[float]],
) -> tuple[dict[str, Any], list[str]]:
    neutral = controller.AppraisalVector()
    extreme = named_scenarios()["extreme_unresolved"]
    stress_endpoint = simulate(extreme, 32)[-1]
    starts: list[tuple[str, tuple[float, ...]]] = [
        (f"grid3-{index:03d}", tuple(state))
        for index, state in enumerate(STATE_GRID_3)
    ]
    seen = {tuple(f17(value) for value in state) for _, state in starts}
    for index, state in enumerate(discovered):
        state_tuple_value = tuple(state)
        key = tuple(f17(value) for value in state_tuple_value)
        if key not in seen:
            seen.add(key)
            starts.append((f"attractor-{index:04d}", state_tuple_value))
    stress_key = tuple(f17(value) for value in stress_endpoint)
    if stress_key not in seen:
        starts.append(("stress-endpoint", stress_endpoint))

    rows = []
    failures = []
    stress_neutral_trajectory: list[tuple[float, ...]] | None = None
    for label, initial in starts:
        trajectory = simulate(neutral, 64, initial)
        if label == "stress-endpoint":
            stress_neutral_trajectory = trajectory
        tick32 = trajectory[32]
        tick40 = trajectory[40]
        reasons = []
        if not (tick32[2] <= 1e-6 and tick32[4] <= 0.01 and tick32[3] >= 0.99):
            reasons.append("tick-32 vigilance/load/reserve gate")
        if not (
            max(tick40[:3]) <= 0.001
            and tick40[4] <= 0.001
            and tick40[3] >= 0.999
        ):
            reasons.append("tick-40 kappa/load/reserve gate")
        reasons.extend(
            reason.removeprefix(f"{label}: ")
            for reason in _rebound_failures(trajectory, label)
        )
        failures.extend(f"{label}: {reason}" for reason in reasons)
        rows.append(
            {
                "label": label,
                "initial": float_list(initial),
                "trajectory": [float_list(state) for state in trajectory],
                "tick32": float_list(tick32),
                "tick40": float_list(tick40),
                "reasons": reasons,
            }
        )

    if stress_neutral_trajectory is None:
        stress_neutral_trajectory = simulate(neutral, 64, stress_endpoint)
    clear_event = make_event(
        event_id=f"{PROTOCOL_ID}:recovery:threat-cleared",
        turn_index=0,
        event_index=0,
        kind="threat_cleared",
        magnitude=1.0,
        confidence=1.0,
        attribution="environment",
    )
    clear_result = controller.appraise_events((clear_event,))
    clear_trajectory = [stress_endpoint]
    current = stress_endpoint
    for tick in range(1, 65):
        q = clear_result.vector if tick == 1 else neutral
        current = transition(current, q)
        clear_trajectory.append(current)

    clear_reasons = []
    threshold_checks = (
        (0, 0.001, True, "affiliation"),
        (1, 0.001, True, "agency"),
        (2, 1e-6, True, "vigilance"),
        (2, 0.001, True, "vigilance_0.001"),
        (3, 0.99, False, "reserve_0.99"),
        (3, 0.999, False, "reserve_0.999"),
        (4, 0.01, True, "load_0.01"),
        (4, 0.001, True, "load_0.001"),
    )
    first_passages = {}
    for coordinate, threshold, upper, name in threshold_checks:
        neutral_tick = _first_passage(
            stress_neutral_trajectory, coordinate, threshold, upper=upper
        )
        clear_tick = _first_passage(
            clear_trajectory, coordinate, threshold, upper=upper
        )
        first_passages[name] = {"neutral": neutral_tick, "clear": clear_tick}
        if neutral_tick is not None and (
            clear_tick is None or clear_tick > neutral_tick
        ):
            clear_reasons.append(f"{name}: explicit clear is slower")
    for tick, (neutral_state, clear_state) in enumerate(
        zip(stress_neutral_trajectory, clear_trajectory, strict=True)
    ):
        if any(clear_state[index] > neutral_state[index] + 1e-12 for index in (0, 1, 2, 4)):
            clear_reasons.append(f"tick {tick}: explicit clear exceeds neutral")
            break
        if clear_state[3] < neutral_state[3] - 1e-12:
            clear_reasons.append(f"tick {tick}: explicit clear reserve is lower")
            break
    failures.extend(clear_reasons)
    clear_rebound_reasons = [
        reason.removeprefix("explicit-clear: ")
        for reason in _rebound_failures(clear_trajectory, "explicit-clear")
    ]
    clear_reasons.extend(clear_rebound_reasons)
    failures.extend(clear_rebound_reasons)
    return (
        {
            "start_count": len(starts),
            "stress_endpoint": float_list(stress_endpoint),
            "rows": rows,
            "explicit_clear": {
                "q": q_record(clear_result.vector),
                "audit": [_audit_record(item) for item in clear_result.audit],
                "trajectory": [float_list(state) for state in clear_trajectory],
                "first_passages": first_passages,
                "reasons": clear_reasons,
            },
            "gate": "FAIL" if failures else "PASS",
            "reasons": failures,
        },
        failures,
    )


def audit_accumulation() -> tuple[dict[str, Any], list[str]]:
    active = controller.AppraisalVector(
        norm_violation=0.75, controllability=0.75
    )
    neutral = controller.AppraisalVector()
    occurrence = [baseline_state()]
    current = transition(baseline_state(), active)
    occurrence.append(current)
    for _ in range(63):
        current = transition(current, neutral)
        occurrence.append(current)

    unresolved = [baseline_state()]
    current = baseline_state()
    for _ in range(64):
        current = transition(current, active)
        unresolved.append(current)
    recovery = [current]
    for _ in range(40):
        current = transition(current, neutral)
        recovery.append(current)

    failures = []
    for coordinate, name in enumerate(("affiliation", "agency", "vigilance")):
        post_occurrence = [state[coordinate] for state in occurrence[1:]]
        if not _monotonic(post_occurrence, nondecreasing=False):
            failures.append(f"occurrence arm {name} accumulates after tick 1")
    if max(occurrence[40][:3]) > 0.001:
        failures.append("occurrence arm has kappa above 0.001 at tick 40")
    for coordinate, name in ((0, "affiliation"), (1, "agency")):
        values = [state[coordinate] for state in unresolved]
        if not _monotonic(values, nondecreasing=True):
            failures.append(f"unresolved {name} is not nondecreasing")
        if max(values) >= 0.95:
            failures.append(f"unresolved {name} reaches 0.95 or saturation")
        if any(value == 1.0 for value in values):
            failures.append(f"unresolved {name} exactly saturates")
    if max(recovery[40][:3]) > 0.001:
        failures.append("unresolved arm does not recover kappa by 40 neutral ticks")
    if not all(
        math.isfinite(value) and 0.0 <= value <= 1.0
        for state in occurrence + unresolved + recovery
        for value in state
    ):
        failures.append("accumulation trajectory is nonfinite or unbounded")
    return (
        {
            "active_q": q_record(active),
            "occurrence": [float_list(state) for state in occurrence],
            "unresolved": [float_list(state) for state in unresolved],
            "recovery": [float_list(state) for state in recovery],
            "gate": "FAIL" if failures else "PASS",
            "reasons": failures,
        },
        failures,
    )


def audit_saturation_clipping(
    coarse: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    scenarios = {
        "moderate_controlled": controller.AppraisalVector(
            predicted_harm=0.5, controllability=0.75
        ),
        "moderate_uncontrolled": controller.AppraisalVector(
            predicted_harm=0.5, controllability=0.25
        ),
        "norm_repair_0.75": controller.AppraisalVector(
            norm_violation=0.75, controllability=0.75
        ),
        "affiliation_gain_0.5": controller.AppraisalVector(
            affiliation_delta=0.5
        ),
        "affiliation_loss_0.5": controller.AppraisalVector(
            affiliation_delta=-0.5
        ),
    }
    rows = []
    failures = []
    if float(coarse["max_transition_reconciliation"]) > 1e-12:
        failures.append(
            "independent pre/post-clip reconciliation exceeds 1e-12"
        )
    for name, q in scenarios.items():
        trajectory = simulate(q, 256)
        hits = []
        occupancy = {field: {"zero": 0, "one": 0} for field in STATE_FIELDS}
        for tick, state in enumerate(trajectory[1:], start=1):
            for index, field in enumerate(STATE_FIELDS):
                occupancy[field]["zero"] += state[index] == 0.0
                occupancy[field]["one"] += state[index] == 1.0
            triggered = (
                any(value == 1.0 for value in state[:3])
                or state[3] == 0.0
                or state[4] == 1.0
            )
            if triggered and len(hits) < FAILURE_WITNESS_LIMIT:
                hits.append({"tick": tick, "state": float_list(state)})
        if hits:
            failures.append(f"{name}: exact saturation begins at tick {hits[0]['tick']}")
        rows.append(
            {
                "scenario": name,
                "q": q_record(q),
                "trajectory": [float_list(state) for state in trajectory],
                "occupancy": occupancy,
                "saturation_witnesses": hits,
            }
        )
    extreme_trajectory = simulate(named_scenarios()["extreme_unresolved"], 256)
    extreme_occupancy = {
        field: {
            "zero": sum(state[index] == 0.0 for state in extreme_trajectory[1:]),
            "one": sum(state[index] == 1.0 for state in extreme_trajectory[1:]),
        }
        for index, field in enumerate(STATE_FIELDS)
    }
    return (
        {
            "dedicated": rows,
            "extreme_occupancy_descriptive": extreme_occupancy,
            "coarse_reconciliation": coarse["max_transition_reconciliation"],
            "gate": "FAIL" if failures else "PASS",
            "reasons": failures,
        },
        failures,
    )


def leakage_split(template_index: int) -> str:
    if template_index < 320:
        return "train"
    if template_index < 416:
        return "validation"
    return "test"


def leakage_digest(template_index: int, tick: int) -> bytes:
    material = f"{PROTOCOL_ID}:{template_index}:{tick}".encode("ascii")
    return hashlib.sha256(material).digest()


def leakage_event(
    *,
    template_index: int,
    tick: int,
    label: int,
    ref_kind: str,
    canary: bool = False,
    filtered: bool = False,
) -> events.WorldEvent:
    split = leakage_split(template_index)
    digest = leakage_digest(template_index, tick)
    if canary:
        kind = "affiliation_gain"
        attribution = "environment"
        magnitude = 0.5 + (label - 7.5) * 1e-6
        confidence = 1.0
        if filtered:
            magnitude = quantize_half_up(magnitude)
    else:
        kind = sorted(events.WORLD_EVENT_KINDS)[digest[0] % 10]
        attribution = sorted(events.EVENT_ATTRIBUTIONS)[digest[1] % 4]
        magnitude = digest[2] / 256.0
        confidence = digest[3] / 256.0
    event_id = (
        f"{PROTOCOL_ID}:leakage:{split}:{template_index}:{tick}:"
        f"{ref_kind}:{label}"
    )
    source_material = (
        f"{PROTOCOL_ID}:source:{split}:{template_index}:{tick}:{label}"
    ).encode("ascii")
    source = events.EventSourceRef(
        kind="synthetic_fixture",
        source_id=f"{event_id}:source",
        sha256=sha256_hex(source_material),
        sequence=tick,
    )
    semantic_ref = events.SemanticRef(
        ref_kind,
        f"{PROTOCOL_ID}:ref:{split}:{template_index}:{tick}:{ref_kind}:{label}",
    )
    return make_event(
        event_id=event_id,
        turn_index=tick,
        event_index=0,
        kind=kind,
        magnitude=magnitude,
        confidence=confidence,
        attribution=attribution,
        semantic_refs=(semantic_ref,),
        source=source,
    )


def leakage_features(
    template_index: int,
    label: int,
    ref_kind: str,
    *,
    canary: bool = False,
    filtered: bool = False,
) -> dict[str, tuple[float, ...]]:
    current = baseline_state()
    q_rows = []
    states = []
    numeric = []
    for tick in range(32):
        event = leakage_event(
            template_index=template_index,
            tick=tick,
            label=label,
            ref_kind=ref_kind,
            canary=canary,
            filtered=filtered,
        )
        q = controller.appraise_events((event,)).vector
        q_values = q_tuple(q)
        current = transition(current, q)
        q_rows.append(q_values)
        states.append(current)
        numeric.extend(q_values + current)
    q_flat = tuple(value for row in q_rows for value in row)
    kappa_flat = tuple(value for state in states for value in state[:3])
    regulatory_flat = tuple(value for state in states for value in state[3:])
    for endpoint in (0, 7, 31):
        kappa_flat += tuple(states[endpoint][:3])
        regulatory_flat += tuple(states[endpoint][3:])
    return {
        "q": q_flat,
        "kappa": kappa_flat,
        "regulatory": regulatory_flat,
        "numeric": tuple(numeric),
    }


def _standardizer(
    samples: Sequence[tuple[int, Sequence[float]]]
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not samples:
        raise ValueError("classifier requires training samples")
    dimension = len(samples[0][1])
    means = tuple(
        sum(features[index] for _, features in samples) / len(samples)
        for index in range(dimension)
    )
    deviations = []
    for index, mean in enumerate(means):
        variance = (
            sum((features[index] - mean) ** 2 for _, features in samples)
            / len(samples)
        )
        deviations.append(math.sqrt(variance))
    return means, tuple(deviations)


def _standardize(
    features: Sequence[float],
    means: Sequence[float],
    deviations: Sequence[float],
) -> tuple[float, ...]:
    return tuple(
        0.0 if deviation == 0.0 else (value - mean) / deviation
        for value, mean, deviation in zip(
            features, means, deviations, strict=True
        )
    )


def _classifier_parameters(
    train: Sequence[tuple[int, Sequence[float]]]
) -> dict[str, Any]:
    means, deviations = _standardizer(train)
    standardized = [
        (label, _standardize(features, means, deviations))
        for label, features in train
    ]
    by_class: dict[int, list[tuple[float, ...]]] = defaultdict(list)
    for label, features in standardized:
        by_class[label].append(features)
    if set(by_class) != set(range(16)):
        raise ValueError("classifier training set must contain all 16 classes")
    centroids = {}
    variances = {}
    for label in range(16):
        rows = by_class[label]
        centroid = tuple(
            sum(row[index] for row in rows) / len(rows)
            for index in range(len(rows[0]))
        )
        variance = tuple(
            max(
                sum((row[index] - centroid[index]) ** 2 for row in rows)
                / len(rows),
                1e-12,
            )
            for index in range(len(rows[0]))
        )
        centroids[label] = centroid
        variances[label] = variance
    return {
        "means": means,
        "deviations": deviations,
        "centroids": centroids,
        "variances": variances,
    }


def _predict(
    features: Sequence[float], parameters: dict[str, Any], classifier_name: str
) -> int:
    vector = _standardize(
        features, parameters["means"], parameters["deviations"]
    )
    if classifier_name == "nearest_centroid":
        scored = []
        for label in range(16):
            centroid = parameters["centroids"][label]
            distance = sum(
                (value - center) ** 2
                for value, center in zip(vector, centroid, strict=True)
            )
            scored.append((distance, label))
        return min(scored)[1]
    if classifier_name == "diagonal_gaussian":
        scored = []
        for label in range(16):
            centroid = parameters["centroids"][label]
            variances = parameters["variances"][label]
            score = -0.5 * sum(
                math.log(variance) + (value - center) ** 2 / variance
                for value, center, variance in zip(
                    vector, centroid, variances, strict=True
                )
            )
            scored.append((-score, label))
        return min(scored)[1]
    raise ValueError(f"unknown classifier {classifier_name!r}")


def balanced_accuracy(
    expected: Sequence[int], predicted: Sequence[int]
) -> float:
    totals = [0] * 16
    correct = [0] * 16
    for truth, guess in zip(expected, predicted, strict=True):
        totals[truth] += 1
        correct[truth] += truth == guess
    if any(total == 0 for total in totals):
        raise ValueError("balanced accuracy requires every class")
    return sum(correct[index] / totals[index] for index in range(16)) / 16.0


def evaluate_classifiers(
    train: Sequence[tuple[int, Sequence[float]]],
    evaluation: Sequence[tuple[int, Sequence[float]]],
) -> dict[str, str]:
    parameters = _classifier_parameters(train)
    return _evaluate_classifier_parameters(parameters, evaluation)


def _evaluate_classifier_parameters(
    parameters: dict[str, Any],
    evaluation: Sequence[tuple[int, Sequence[float]]],
) -> dict[str, str]:
    truth = [label for label, _ in evaluation]
    output = {}
    for classifier_name in ("nearest_centroid", "diagonal_gaussian"):
        predicted = [
            _predict(features, parameters, classifier_name)
            for _, features in evaluation
        ]
        output[classifier_name] = f17(balanced_accuracy(truth, predicted))
    return output


def _feature_digest(samples: Sequence[tuple[int, Sequence[float]]]) -> str:
    digest = hashlib.sha256()
    for index, (label, features) in enumerate(samples):
        digest.update(
            canonical_bytes(
                {
                    "sample": index,
                    "label": label,
                    "features": float_list(features),
                }
            )
        )
    return digest.hexdigest()


def _features_record(
    features: dict[str, Sequence[float]]
) -> dict[str, list[str]]:
    return {view: float_list(values) for view, values in features.items()}


def _features_sha256(features: dict[str, Sequence[float]]) -> str:
    return sha256_hex(canonical_bytes(_features_record(features)))


def _compressed_canary_raw(
    datasets: dict[str, dict[str, list[tuple[int, Sequence[float]]]]]
) -> tuple[dict[str, Any], int]:
    views = ("q", "kappa", "regulatory", "numeric")
    references: dict[int, dict[str, Sequence[float]]] = {}
    for sample_index, (label, _) in enumerate(datasets["train"]["q"]):
        if label not in references:
            references[label] = {
                view: datasets["train"][view][sample_index][1] for view in views
            }
    reference_records = {
        str(label): _features_record(references[label]) for label in range(16)
    }
    starts = {"train": 0, "validation": 320, "test": 416}
    sample_records = []
    mismatch_count = 0
    for split in ("train", "validation", "test"):
        for sample_index, (label, _) in enumerate(datasets[split]["q"]):
            features = {
                view: datasets[split][view][sample_index][1] for view in views
            }
            matches = features == references[label]
            if not matches:
                mismatch_count += 1
            sample_record: dict[str, Any] = {
                "split": split,
                "template": starts[split] + sample_index // 16,
                "label": label,
                "matches_label_reference": matches,
                "features_sha256": _features_sha256(features),
            }
            if not matches:
                sample_record["features"] = _features_record(features)
            sample_records.append(sample_record)
    return (
        {
            "encoding": (
                "full label-reference features plus lossless equality/digest rows; "
                "mismatches carry full replacement features"
            ),
            "label_references": reference_records,
            "samples": sample_records,
            "mismatch_count": mismatch_count,
        },
        mismatch_count,
    )


def _canary_samples(
    ref_kind: str,
    *,
    filtered: bool,
    template_indices: Iterable[int] | None = None,
) -> dict[str, dict[str, list[tuple[int, Sequence[float]]]]]:
    if template_indices is None:
        template_indices = range(512)
    output = {
        split: {view: [] for view in ("q", "kappa", "regulatory", "numeric")}
        for split in ("train", "validation", "test")
    }
    for template_index in template_indices:
        split = leakage_split(template_index)
        for label in range(16):
            features_by_view = leakage_features(
                template_index,
                label,
                ref_kind,
                canary=True,
                filtered=filtered,
            )
            for view, features in features_by_view.items():
                output[split][view].append((label, features))
    return output


def audit_conditional_leakage() -> tuple[dict[str, Any], list[str]]:
    failures = []
    ref_records = []
    raw_canary_max = 0.0
    filtered_canary_max = 0.0
    for ref_kind in ("person", "topic", "episode"):
        datasets = {
            split: {
                view: [] for view in ("q", "kappa", "regulatory", "numeric")
            }
            for split in ("train", "validation", "test")
        }
        mismatch_witnesses = []
        raw_templates = []
        for template_index in range(512):
            split = leakage_split(template_index)
            expected = leakage_features(template_index, 0, ref_kind)
            identities = []
            for label in range(16):
                features = leakage_features(template_index, label, ref_kind)
                matches = features == expected
                identity_record: dict[str, Any] = {
                    "label": label,
                    "matches_reference": matches,
                    "features_sha256": _features_sha256(features),
                }
                if not matches:
                    identity_record["features"] = _features_record(features)
                    if len(mismatch_witnesses) < 16:
                        mismatch_witnesses.append(
                            {"template": template_index, "label": label}
                        )
                identities.append(identity_record)
                for view, values in features.items():
                    datasets[split][view].append((label, values))
            raw_templates.append(
                {
                    "template": template_index,
                    "split": split,
                    "reference_features": _features_record(expected),
                    "identities": identities,
                }
            )

        view_records = {}
        for view in ("q", "kappa", "regulatory", "numeric"):
            parameters = _classifier_parameters(datasets["train"][view])
            validation_scores = _evaluate_classifier_parameters(
                parameters, datasets["validation"][view]
            )
            test_scores = _evaluate_classifier_parameters(
                parameters, datasets["test"][view]
            )
            if any(float(score) > 0.0825 + 1e-12 for score in test_scores.values()):
                failures.append(f"{ref_kind}/{view}: identity recovery exceeds 0.0825")
            view_records[view] = {
                "counts": {
                    split: len(datasets[split][view])
                    for split in ("train", "validation", "test")
                },
                "feature_sha256": {
                    split: _feature_digest(datasets[split][view])
                    for split in ("train", "validation", "test")
                },
                "validation_balanced_accuracy": validation_scores,
                "test_balanced_accuracy": test_scores,
            }
        if mismatch_witnesses:
            failures.append(f"{ref_kind}: matched identity features differ")

        canary_records = {}
        for filtered in (False, True):
            name = "filtered" if filtered else "raw"
            canary = _canary_samples(ref_kind, filtered=filtered)
            raw_custody, canary_mismatches = _compressed_canary_raw(canary)
            if canary_mismatches:
                failures.append(
                    f"{ref_kind}/{name}: {canary_mismatches} canary namespace "
                    "rows change the fixed numeric surface"
                )
            canary_views = {}
            for view in ("q", "kappa", "regulatory", "numeric"):
                scores = evaluate_classifiers(
                    canary["train"][view], canary["test"][view]
                )
                numeric_scores = [float(score) for score in scores.values()]
                if filtered:
                    filtered_canary_max = max(filtered_canary_max, *numeric_scores)
                else:
                    raw_canary_max = max(raw_canary_max, *numeric_scores)
                canary_views[view] = scores
            canary_records[name] = {
                "sample_counts": {
                    split: len(canary[split]["q"])
                    for split in ("train", "validation", "test")
                },
                "raw_records": raw_custody,
                "views": canary_views,
            }

        ref_records.append(
            {
                "ref_kind": ref_kind,
                "matched_bit_identical": not mismatch_witnesses,
                "mismatch_witnesses": mismatch_witnesses,
                "raw_templates": raw_templates,
                "views": view_records,
                "canary": canary_records,
            }
        )

    if raw_canary_max < 0.90:
        failures.append(
            f"positive canary sensitivity {f17(raw_canary_max)} is below 0.90"
        )
    if filtered_canary_max > 0.0825 + 1e-12:
        failures.append(
            "candidate filter canary recovery exceeds 0.0825: "
            f"{f17(filtered_canary_max)}"
        )
    return (
        {
            "ref_kinds": ref_records,
            "raw_canary_max_accuracy": f17(raw_canary_max),
            "filtered_canary_max_accuracy": f17(filtered_canary_max),
            "gate": "FAIL" if failures else "PASS",
            "reasons": failures,
        },
        failures,
    )


def frozen_constants() -> dict[str, Any]:
    clear_event_id = f"{PROTOCOL_ID}:recovery:threat-cleared"
    return {
        "dt": f17(1.0),
        "q_fields": list(Q_FIELDS),
        "state_fields": list(STATE_FIELDS),
        "event_kinds": sorted(events.WORLD_EVENT_KINDS),
        "event_attributions": sorted(events.EVENT_ATTRIBUTIONS),
        "event_target_map": dict(sorted(TARGET_FIELDS.items())),
        "coarse_nonnegative_grid": float_list(NONNEG_GRID_5),
        "coarse_signed_grid": float_list(SIGNED_GRID_5),
        "coarse_q_count": 15_625,
        "coarse_transition_count": 500_000,
        "state_corner_count": len(STATE_CORNERS),
        "state_grid3_count": len(STATE_GRID_3),
        "factor_contexts": {
            name: {
                "coarse_values": float_list(FACTOR_VALUES[name]),
                "initial": float_list(factor_initial(name)),
                "zero_value_context": q_record(factor_q(name, 0.0)),
            }
            for name in Q_FIELDS
        },
        "metamorphic": {
            "merged_magnitude": f17(0.5),
            "split_count": 2,
            "split_magnitude": f17(0.25),
            "confidence": f17(1.0),
            "q_tolerance": f17(1e-12),
        },
        "factor_horizons": [1, 4, 8],
        "factor_witness_minimum": f17(0.01),
        "factor_monotonic_tolerance": f17(1e-12),
        "fine_quantum": f17(1.0 / 256.0),
        "quantization_formula": "floor(256*x + 0.5)/256",
        "fine_response_threshold": f17(1e-9),
        "deadband_max_width": f17(0.25),
        "adjacent_terminal_horizon": 256,
        "adjacent_terminal_max_jump": f17(0.10),
        "stationary_horizon": 4096,
        "stationary_q_count": 729,
        "boundary_pair_count": 85,
        "boundary_formulas": {
            "D_hi": "2 / (5 - 2.25*c)",
            "k": "68*(1-c)/19",
            "D_lo_low_c": (
                "(5 + 2*k - 2.25*c - sqrt((5 + 2*k - 2.25*c)^2 "
                "- 16*k)) / (4*k)"
            ),
            "D_lo_high_c": "(4*c - 2) / (1 + 1.75*c)",
            "crossover": "116/137",
        },
        "boundary_pairs": [
            {"controllability": f17(control), "drive": f17(drive)}
            for control, drive in boundary_pairs()
        ],
        "named_scenarios": {
            name: q_record(q) for name, q in named_scenarios().items()
        },
        "boundary_horizon": 20_000,
        "fixed_delta_tolerance": f17(1e-10),
        "fixed_required_ticks": 32,
        "fixed_residual_tolerance": f17(1e-9),
        "cycle_periods": [2, 32],
        "cycle_tolerance": f17(1e-8),
        "cluster_tolerance": f17(1e-6),
        "periodic_trajectory_count": 256,
        "periodic_horizon": 4096,
        "periodic_tick_order": ["neutral", "named_scenario"],
        "periodic_first_tick": "neutral",
        "periodic_washout_ticks": 128,
        "recovery_horizon": 64,
        "recovery_tick32": {
            "vigilance_max": f17(1e-6),
            "load_max": f17(0.01),
            "reserve_min": f17(0.99),
        },
        "recovery_tick40": {
            "kappa_max": f17(0.001),
            "load_max": f17(0.001),
            "reserve_min": f17(0.999),
        },
        "rebound_tolerance": f17(1e-9),
        "explicit_clear_fixture": {
            "event_id": clear_event_id,
            "position": [0, 0],
            "kind": "threat_cleared",
            "magnitude": f17(1.0),
            "confidence": f17(1.0),
            "attribution": "environment",
            "source_kind": "synthetic_fixture",
            "source_id": f"{clear_event_id}:source",
            "source_sequence": 0,
            "source_sha256": sha256_hex(clear_event_id.encode("ascii")),
            "semantic_refs": [],
        },
        "accumulation_active_norm": f17(0.75),
        "accumulation_controllability": f17(0.75),
        "accumulation_active_ticks": 64,
        "accumulation_saturation_ceiling": f17(0.95),
        "saturation_horizon": 256,
        "leakage_classes": 16,
        "leakage_ref_kinds": ["person", "topic", "episode"],
        "leakage_feature_views": ["q", "kappa", "regulatory", "numeric"],
        "leakage_classifiers": ["nearest_centroid", "diagonal_gaussian"],
        "leakage_template_generator": (
            "sha256(protocol_id + ':' + template_index + ':' + tick)"
        ),
        "leakage_template_split": [320, 96, 96],
        "leakage_ticks": 32,
        "leakage_chance": f17(0.0625),
        "leakage_gate": f17(0.0825),
        "gaussian_variance_floor": f17(1e-12),
        "positive_canary_gate": f17(0.90),
        "positive_canary_base_magnitude": f17(0.5),
        "positive_canary_class_step": f17(1e-6),
        "output_bundle": (
            "results/world_model_phase3/controller_audit_v1/"
        ),
        "output_files": ["report.json", "report.json.sha256", "REPORT.md"],
        "record_delimiter": "canonical-json-lf",
    }


def overall_disposition(gates: dict[str, dict[str, Any]]) -> str:
    statuses = [gate["status"] for gate in gates.values()]
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "HELD" for status in statuses):
        return "HOLD"
    return "PASS"


def run_audit() -> dict[str, Any]:
    print("[1/10] verifying frozen source custody", file=sys.stderr)
    source_custody = verify_frozen_sources()
    print("[2/10] event metamorphics and replay", file=sys.stderr)
    event_result, _ = audit_event_metamorphics()
    replay_result = audit_replay_boundary()
    print("[3/10] factor, fine-bin, and one-factor sweeps", file=sys.stderr)
    factor_result, adjacent, _ = audit_factor_responses()
    print("[4/10] 500,000-transition Cartesian sweep", file=sys.stderr)
    coarse_result, _ = audit_coarse_cartesian()
    print("[5/10] stationary, boundary, and periodic phase portrait", file=sys.stderr)
    phase_result, discovered, _ = audit_phase_portrait(adjacent, coarse_result)
    print("[6/10] recovery", file=sys.stderr)
    recovery_result, _ = audit_recovery(discovered)
    print("[7/10] accumulation", file=sys.stderr)
    accumulation_result, _ = audit_accumulation()
    print("[8/10] saturation and clipping", file=sys.stderr)
    saturation_result, _ = audit_saturation_clipping(coarse_result)
    print("[9/10] conditional semantic leakage", file=sys.stderr)
    leakage_result, _ = audit_conditional_leakage()

    gates = {
        "EVENT_METAMORPHICS": {
            "status": event_result["gate"],
            "reasons": event_result["reasons"],
        },
        "FACTOR_RESPONSES": {
            "status": factor_result["gate"],
            "reasons": factor_result["reasons"],
        },
        "PHASE_PORTRAIT": {
            "status": phase_result["gate"],
            "reasons": phase_result["reasons"],
        },
        "RECOVERY": {
            "status": recovery_result["gate"],
            "reasons": recovery_result["reasons"],
        },
        "ACCUMULATION": {
            "status": accumulation_result["gate"],
            "reasons": accumulation_result["reasons"],
        },
        "CONDITIONAL_LEAKAGE": {
            "status": leakage_result["gate"],
            "reasons": leakage_result["reasons"],
        },
        "SATURATION_CLIPPING": {
            "status": saturation_result["gate"],
            "reasons": saturation_result["reasons"],
        },
        "RELIEF_SEMANTICS": {
            "status": "HELD",
            "reasons": ["numeric relief policy remains owner-held on #171"],
        },
        "NUMERIC_RATE_POLICY": {
            "status": "HELD",
            "reasons": ["v1 boundary does not enforce the candidate 1/256 policy"],
        },
        "REPLAY_AUTHORITY": {
            "status": replay_result["gate"],
            "reasons": replay_result["reasons"],
        },
    }
    disposition = overall_disposition(gates)
    print("[10/10] assembling canonical report", file=sys.stderr)
    runner_path = Path(__file__).resolve()
    report: dict[str, Any] = {
        "schema_version": "world-model-phase3c-controller-audit-report-v1",
        "protocol_id": PROTOCOL_ID,
        "preregistration": {
            "path": str(PREREG_PATH.relative_to(MODULE_ROOT)).replace("\\", "/"),
            "git_blob": git_blob_sha1(PREREG_PATH),
            "sha256": sha256_hex(PREREG_PATH.read_bytes()),
        },
        "runner": {
            "path": str(runner_path.relative_to(MODULE_ROOT)).replace("\\", "/"),
            "sha256": sha256_hex(runner_path.read_bytes()),
        },
        "source_custody": source_custody,
        "platform": {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "constants": frozen_constants(),
        "probes": {
            "event_metamorphics": event_result,
            "replay": replay_result,
            "factor_responses": factor_result,
            "coarse_cartesian": coarse_result,
            "phase_portrait": phase_result,
            "recovery": recovery_result,
            "accumulation": accumulation_result,
            "conditional_leakage": leakage_result,
            "saturation_clipping": saturation_result,
        },
        "gates": gates,
        "overall_disposition": disposition,
    }
    report["report_sha256"] = sha256_hex(canonical_bytes(report))
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# World Model Phase 3c Controller Audit",
        "",
        f"- Protocol: `{report['protocol_id']}`",
        f"- Overall disposition: **{report['overall_disposition']}**",
        f"- Report content digest: `{report['report_sha256']}`",
        f"- Frozen target HEAD: `{report['source_custody']['frozen_head']}`",
        "",
        "## Gates",
        "",
        "| Gate | Status | Primary reason |",
        "|---|---|---|",
    ]
    for name, gate in report["gates"].items():
        reason = gate["reasons"][0] if gate["reasons"] else "none"
        reason = str(reason).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{name}` | **{gate['status']}** | {reason} |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This is a deterministic, model-free development audit. It does not",
            "authorize persistence, runtime composition, action selection, Gemma,",
            "Mamba, bridge injection, Qdrant, memory routing, or alpha control.",
            "",
            "`report.json` is the sole numeric source of truth. This Markdown file",
            "is rendered deterministically from that report.",
            "",
        ]
    )
    return "\n".join(lines)


REPORT_FIELDS = {
    "schema_version",
    "protocol_id",
    "preregistration",
    "runner",
    "source_custody",
    "platform",
    "constants",
    "probes",
    "gates",
    "overall_disposition",
    "report_sha256",
}
GATE_NAMES = {
    "EVENT_METAMORPHICS",
    "FACTOR_RESPONSES",
    "PHASE_PORTRAIT",
    "RECOVERY",
    "ACCUMULATION",
    "CONDITIONAL_LEAKAGE",
    "SATURATION_CLIPPING",
    "RELIEF_SEMANTICS",
    "NUMERIC_RATE_POLICY",
    "REPLAY_AUTHORITY",
}
PROBE_NAMES = {
    "event_metamorphics",
    "replay",
    "factor_responses",
    "coarse_cartesian",
    "phase_portrait",
    "recovery",
    "accumulation",
    "conditional_leakage",
    "saturation_clipping",
}
PROBE_GATE_MAP = {
    "EVENT_METAMORPHICS": "event_metamorphics",
    "FACTOR_RESPONSES": "factor_responses",
    "PHASE_PORTRAIT": "phase_portrait",
    "RECOVERY": "recovery",
    "ACCUMULATION": "accumulation",
    "CONDITIONAL_LEAKAGE": "conditional_leakage",
    "SATURATION_CLIPPING": "saturation_clipping",
    "REPLAY_AUTHORITY": "replay",
}


def validated_report_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    if type(report) is not dict:
        raise ValueError("report must be an exact dict")
    snapshot = json.loads(canonical_bytes(report))
    if set(snapshot) != REPORT_FIELDS:
        raise ValueError("report fields do not match the frozen schema")
    if snapshot["schema_version"] != "world-model-phase3c-controller-audit-report-v1":
        raise ValueError("report schema_version mismatch")
    if snapshot["protocol_id"] != PROTOCOL_ID:
        raise ValueError("report protocol_id mismatch")
    if snapshot["preregistration"].get("git_blob") != FROZEN_PREREG_BLOB:
        raise ValueError("report preregistration custody mismatch")
    source_custody = snapshot["source_custody"]
    if source_custody.get("frozen_head") != FROZEN_HEAD:
        raise ValueError("report frozen source HEAD mismatch")
    if source_custody.get("preregistration_git_blob") != FROZEN_PREREG_BLOB:
        raise ValueError("report frozen preregistration blob mismatch")
    records = source_custody.get("records")
    if not isinstance(records, list) or len(records) != len(SOURCE_BLOBS):
        raise ValueError("report source custody record count mismatch")
    if not all(
        isinstance(item, dict)
        and item.get("match") is True
        and item.get("expected_git_blob") == item.get("actual_git_blob")
        for item in records
    ):
        raise ValueError("report contains an unverified source record")
    if set(snapshot["gates"]) != GATE_NAMES:
        raise ValueError("report gate set mismatch")
    probes = snapshot["probes"]
    if not isinstance(probes, dict) or set(probes) != PROBE_NAMES:
        raise ValueError("report probe set mismatch")
    for gate_name, probe_name in PROBE_GATE_MAP.items():
        probe = probes[probe_name]
        gate = snapshot["gates"][gate_name]
        if not isinstance(probe, dict) or probe.get("gate") not in {
            "PASS",
            "FAIL",
            "HELD",
        }:
            raise ValueError(f"probe {probe_name} has no valid gate")
        if gate.get("status") != probe["gate"]:
            raise ValueError(f"gate {gate_name} disagrees with probe {probe_name}")
        if gate.get("reasons") != probe.get("reasons"):
            raise ValueError(f"gate {gate_name} reasons disagree with its probe")
    if snapshot["gates"]["RELIEF_SEMANTICS"].get("status") != "HELD":
        raise ValueError("RELIEF_SEMANTICS must remain HELD for v1")
    if snapshot["gates"]["NUMERIC_RATE_POLICY"].get("status") != "HELD":
        raise ValueError("NUMERIC_RATE_POLICY must remain HELD for v1")
    if snapshot["gates"]["REPLAY_AUTHORITY"].get("status") == "PASS":
        raise ValueError("REPLAY_AUTHORITY cannot PASS at the v1 boundary")
    if snapshot["overall_disposition"] != overall_disposition(snapshot["gates"]):
        raise ValueError("report overall disposition does not match gates")
    supplied_digest = snapshot["report_sha256"]
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
        raise ValueError("report_sha256 is malformed")
    unsigned = dict(snapshot)
    del unsigned["report_sha256"]
    expected_digest = sha256_hex(canonical_bytes(unsigned))
    if supplied_digest != expected_digest:
        raise ValueError("report self-digest mismatch")
    return snapshot


def publish_bundle(report: dict[str, Any], output_dir: Path = OUTPUT_DIR) -> Path:
    if output_dir.exists():
        raise FileExistsError(f"result bundle already exists: {output_dir}")
    snapshot = validated_report_snapshot(report)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_dir.with_name(f".{output_dir.name}.tmp-{os.getpid()}")
    if temporary.exists():
        raise FileExistsError(f"temporary result bundle already exists: {temporary}")
    temporary.mkdir()
    try:
        report_bytes = canonical_bytes(snapshot)
        final_file_digest = sha256_hex(report_bytes)
        artifacts = {
            "report.json": report_bytes,
            "report.json.sha256": (
                f"{final_file_digest}  report.json\n".encode("ascii")
            ),
            "REPORT.md": render_markdown(snapshot).encode("ascii"),
        }
        for name, payload in artifacts.items():
            path = temporary / name
            with path.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        if output_dir.exists():
            raise FileExistsError(f"result bundle appeared during publication: {output_dir}")
        temporary.rename(output_dir)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return output_dir


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("this frozen runner accepts no command-line arguments")
    report = run_audit()
    published = publish_bundle(report)
    print(f"published {published}")
    print(f"overall disposition: {report['overall_disposition']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
