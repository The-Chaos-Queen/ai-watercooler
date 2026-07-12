from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import math

import pytest

from modulatory_controller import (
    AppraisalAuditRecord,
    AppraisalResult,
    AppraisalVector,
    ControllerConfig,
    KappaState,
    RegulatoryState,
    appraisal_from_payload,
    appraise_events,
    begin_session,
    kappa_from_payload,
    regulatory_from_payload,
    step_controller,
)
from world_model_events import EventSourceRef, SemanticRef, WorldEvent


def _source(
    source_id: str = "fixture-source", sequence: int = 0, digest_char: str = "a"
) -> EventSourceRef:
    return EventSourceRef(
        kind="synthetic_fixture",
        source_id=source_id,
        sha256=digest_char * 64,
        sequence=sequence,
    )


def _event(
    index: int,
    kind: str,
    magnitude: float = 1.0,
    confidence: float = 1.0,
    attribution: str = "environment",
    semantic_refs: tuple[SemanticRef, ...] = (),
    identity_prefix: str = "fixture",
) -> WorldEvent:
    return WorldEvent(
        event_id=f"{identity_prefix}-event-{index}",
        turn_index=0,
        event_index=index,
        kind=kind,
        magnitude=magnitude,
        confidence=confidence,
        attribution=attribution,
        source=_source(
            source_id=f"{identity_prefix}-source",
            sequence=index,
            digest_char="a" if identity_prefix == "fixture" else "b",
        ),
        semantic_refs=semantic_refs,
    )


def _neutral() -> AppraisalVector:
    return AppraisalVector(controllability=0.5)


def test_empty_event_batch_produces_neutral_numeric_appraisal():
    result = appraise_events([])
    assert result.vector == _neutral()
    assert result.audit == ()


def test_rule_table_aggregates_signed_and_bounded_appraisals():
    result = appraise_events(
        [
            _event(0, "threat_observed", 0.8),
            _event(1, "threat_cleared", 0.1),
            _event(2, "outcome_mismatch", 0.6, confidence=0.5),
            _event(3, "control_available", 0.8),
            _event(4, "goal_blocked", 0.4),
            _event(5, "affiliation_gain", 0.7),
            _event(6, "affiliation_loss", 0.2),
            _event(7, "norm_violation", 0.5, attribution="self"),
        ]
    )
    assert result.vector.predicted_harm == pytest.approx(0.7)
    assert result.vector.prediction_error == pytest.approx(0.3)
    assert result.vector.controllability == pytest.approx(0.9)
    assert result.vector.goal_progress == pytest.approx(-0.4)
    assert result.vector.norm_violation == pytest.approx(0.5)
    assert result.vector.affiliation_delta == pytest.approx(0.5)
    assert len(result.audit) == 8
    assert {item.rule_id for item in result.audit} >= {
        "threat.raise_harm",
        "threat.clear_harm",
        "norm.self_violation",
    }


def test_non_self_norm_violation_does_not_become_guilt_appraisal():
    result = appraise_events(
        [_event(0, "norm_violation", 1.0, attribution="other")]
    )
    assert result.vector.norm_violation == 0.0
    assert result.audit[0].rule_id == "norm.non_self_no_guilt"
    assert result.audit[0].contribution == 0.0


def test_semantic_identity_changes_cannot_change_q_or_controller_state():
    refs_a = (
        SemanticRef("person", "laura-private-id"),
        SemanticRef("episode", "episode-alpha"),
        SemanticRef("topic", "private-topic-a"),
    )
    refs_b = (
        SemanticRef("person", "different-person"),
        SemanticRef("episode", "episode-beta"),
        SemanticRef("topic", "private-topic-b"),
    )
    events_a = [
        _event(0, "affiliation_gain", 0.8, semantic_refs=refs_a),
        _event(1, "control_available", 0.6, semantic_refs=refs_a),
    ]
    events_b = [
        _event(
            0,
            "affiliation_gain",
            0.8,
            semantic_refs=refs_b,
            identity_prefix="other",
        ),
        _event(
            1,
            "control_available",
            0.6,
            semantic_refs=refs_b,
            identity_prefix="other",
        ),
    ]

    appraisal_a = appraise_events(events_a)
    appraisal_b = appraise_events(events_b)
    assert appraisal_a.vector == appraisal_b.vector
    assert appraisal_a.audit != appraisal_b.audit

    state_a = step_controller(KappaState(), RegulatoryState(), appraisal_a.vector)
    state_b = step_controller(KappaState(), RegulatoryState(), appraisal_b.vector)
    assert state_a == state_b

    payload = json.dumps(
        {
            "q": appraisal_a.vector.canonical_payload(),
            "state": state_a.canonical_payload(),
        },
        sort_keys=True,
    )
    for forbidden in (
        "laura-private-id",
        "episode-alpha",
        "private-topic-a",
        "fixture-event",
        "fixture-source",
    ):
        assert forbidden not in payload


def test_many_adversarial_semantic_substitutions_leave_numeric_channel_invariant():
    def scenario(identity: int):
        refs = tuple(
            SemanticRef(kind, f"private-{kind}-{identity}")
            for kind in (
                "person",
                "rule",
                "goal",
                "topic",
                "episode",
                "relationship",
                "object",
            )
        )
        prefix = f"identity-{identity}"
        events = [
            _event(0, "threat_observed", 0.75, semantic_refs=refs, identity_prefix=prefix),
            _event(1, "control_available", 0.5, semantic_refs=refs, identity_prefix=prefix),
            _event(2, "affiliation_gain", 0.25, semantic_refs=refs, identity_prefix=prefix),
            _event(
                3,
                "norm_violation",
                0.5,
                attribution="self",
                semantic_refs=refs,
                identity_prefix=prefix,
            ),
        ]
        q = appraise_events(events).vector
        state = step_controller(KappaState(), RegulatoryState(), q)
        return q, state

    expected = scenario(0)
    for identity in range(1, 65):
        assert scenario(identity) == expected


def test_closed_numeric_payloads_reject_semantic_or_unknown_fields():
    cases = [
        (appraisal_from_payload, AppraisalVector().canonical_payload()),
        (kappa_from_payload, KappaState().canonical_payload()),
        (regulatory_from_payload, RegulatoryState().canonical_payload()),
    ]
    for parser, payload in cases:
        for field in ("entity_id", "topic", "episode_id", "text", "embedding"):
            poisoned = dict(payload)
            poisoned[field] = "smuggled"
            with pytest.raises(ValueError, match="fields mismatch"):
                parser(poisoned)


def test_numeric_payload_roundtrips_are_exact():
    q = AppraisalVector(0.2, 0.3, 0.4, -0.5, 0.6, -0.7)
    kappa = KappaState(0.1, 0.2, 0.3)
    regulatory = RegulatoryState(0.8, 0.4)
    assert appraisal_from_payload(q.canonical_payload()) == q
    assert kappa_from_payload(kappa.canonical_payload()) == kappa
    assert regulatory_from_payload(regulatory.canonical_payload()) == regulatory


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True])
def test_numeric_contracts_reject_nonfinite_and_bool_values(value):
    with pytest.raises(ValueError):
        AppraisalVector(predicted_harm=value)
    with pytest.raises(ValueError):
        KappaState(vigilance=value)
    with pytest.raises(ValueError):
        RegulatoryState(load=value)


def test_controlled_threat_produces_vigilance_with_preserved_agency():
    high_control = appraise_events(
        [
            _event(0, "threat_observed", 0.8),
            _event(1, "control_available", 0.8),
        ]
    ).vector
    low_control = appraise_events(
        [
            _event(0, "threat_observed", 0.8),
            _event(1, "control_lost", 0.8),
        ]
    ).vector
    careful = step_controller(KappaState(), RegulatoryState(), high_control)
    uncontrolled = step_controller(KappaState(), RegulatoryState(), low_control)

    assert careful.kappa.vigilance > 0.0
    assert careful.kappa.agency > careful.kappa.vigilance
    assert uncontrolled.kappa.vigilance > 0.0
    assert uncontrolled.kappa.agency == 0.0
    assert careful.regulatory.reserve > uncontrolled.regulatory.reserve
    assert "panic" not in careful.canonical_payload()


def test_repeated_uncontrolled_threat_raises_load_and_depletes_reserve():
    appraisal = appraise_events(
        [
            _event(0, "threat_observed"),
            _event(1, "control_lost"),
        ]
    ).vector
    state = begin_session()
    loads = []
    reserves = []
    for _ in range(8):
        state = step_controller(state.kappa, state.regulatory, appraisal)
        loads.append(state.regulatory.load)
        reserves.append(state.regulatory.reserve)

    assert loads == sorted(loads)
    assert reserves == sorted(reserves, reverse=True)
    assert state.kappa.vigilance == 1.0
    assert state.regulatory.load > 0.5
    assert state.regulatory.reserve < 0.5


def test_relief_recovers_vigilance_load_and_reserve():
    threat = appraise_events(
        [_event(0, "threat_observed"), _event(1, "control_lost")]
    ).vector
    state = begin_session()
    for _ in range(8):
        state = step_controller(state.kappa, state.regulatory, threat)

    stressed = state
    for _ in range(8):
        state = step_controller(state.kappa, state.regulatory, _neutral())

    assert state.kappa.vigilance < stressed.kappa.vigilance
    assert state.regulatory.load < stressed.regulatory.load
    assert state.regulatory.reserve > stressed.regulatory.reserve
    assert state.kappa.vigilance < 0.01


def test_trust_like_event_raises_affiliation_without_storing_relationship():
    refs = (
        SemanticRef("person", "trusted-person-private"),
        SemanticRef("relationship", "relationship-private"),
    )
    appraisal = appraise_events(
        [
            _event(0, "affiliation_gain", 0.8, semantic_refs=refs),
            _event(1, "control_available", 0.8, semantic_refs=refs),
        ]
    ).vector
    state = step_controller(KappaState(), RegulatoryState(), appraisal)
    assert state.kappa.affiliation > 0.0
    serialized = json.dumps(state.canonical_payload())
    assert "trusted-person-private" not in serialized
    assert "relationship-private" not in serialized


def test_self_norm_violation_can_drive_bounded_repair_without_rule_identity():
    refs = (
        SemanticRef("rule", "private-rule-id"),
        SemanticRef("episode", "private-episode-id"),
    )
    appraisal = appraise_events(
        [
            _event(
                0,
                "norm_violation",
                0.8,
                attribution="self",
                semantic_refs=refs,
            ),
            _event(1, "control_available", 0.8, semantic_refs=refs),
        ]
    ).vector
    state = step_controller(KappaState(), RegulatoryState(), appraisal)
    assert appraisal.norm_violation == 0.8
    assert state.kappa.affiliation > 0.0
    assert state.kappa.agency > 0.0
    serialized = json.dumps(state.canonical_payload())
    assert "private-rule-id" not in serialized
    assert "private-episode-id" not in serialized


def test_begin_session_resets_kappa_but_preserves_validated_regulatory_state():
    regulatory = RegulatoryState(reserve=0.4, load=0.6)
    state = begin_session(regulatory)
    assert state.kappa == KappaState()
    assert state.regulatory is regulatory


def test_neutral_turns_decay_session_kappa_without_erasing_regulatory_contract():
    state = step_controller(
        KappaState(affiliation=0.8, agency=0.7, vigilance=0.6),
        RegulatoryState(reserve=0.5, load=0.4),
        _neutral(),
    )
    assert state.kappa.affiliation < 0.8
    assert state.kappa.agency < 0.7
    assert state.kappa.vigilance < 0.6
    assert 0.0 <= state.regulatory.reserve <= 1.0
    assert 0.0 <= state.regulatory.load <= 1.0


def test_controller_remains_bounded_under_long_extreme_sequences():
    extreme = AppraisalVector(
        predicted_harm=1.0,
        prediction_error=1.0,
        controllability=0.0,
        goal_progress=-1.0,
        norm_violation=1.0,
        affiliation_delta=-1.0,
    )
    state = begin_session()
    for _ in range(250):
        state = step_controller(state.kappa, state.regulatory, extreme)
    values = (
        state.kappa.affiliation,
        state.kappa.agency,
        state.kappa.vigilance,
        state.regulatory.reserve,
        state.regulatory.load,
    )
    assert all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in values)


def test_config_is_strict_and_state_records_are_immutable():
    with pytest.raises(ValueError):
        ControllerConfig(load_gain=1.1)
    kappa = KappaState()
    with pytest.raises(FrozenInstanceError):
        kappa.agency = 0.5


def test_controller_rejects_untyped_inputs():
    with pytest.raises(ValueError, match="KappaState"):
        step_controller({}, RegulatoryState(), AppraisalVector())
    with pytest.raises(ValueError, match="RegulatoryState"):
        step_controller(KappaState(), {}, AppraisalVector())
    with pytest.raises(ValueError, match="AppraisalVector"):
        step_controller(KappaState(), RegulatoryState(), {})
    with pytest.raises(ValueError, match="RegulatoryState"):
        begin_session({})


def test_appraisal_audit_and_result_are_closed_typed_records():
    with pytest.raises(ValueError, match="appraisal_field"):
        AppraisalAuditRecord("event", "rule", "entity_id", 0.5)
    with pytest.raises(ValueError, match="contribution"):
        AppraisalAuditRecord("event", "rule", "predicted_harm", math.inf)
    with pytest.raises(ValueError, match="AppraisalVector"):
        AppraisalResult({}, ())
    with pytest.raises(ValueError, match="AppraisalAuditRecord"):
        AppraisalResult(AppraisalVector(), ({"event_id": "event"},))
