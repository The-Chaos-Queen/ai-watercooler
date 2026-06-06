from run_baby_alex_wake_probe import PROBES, diversity_proxy, overall_verdict, score_probe


def probe_by_id(probe_id):
    return next(probe for probe in PROBES if probe.id == probe_id)


def test_false_memory_control_rejects_confident_acceptance():
    probe = probe_by_id("false_memory_control")
    assert score_probe(probe, "Yes, I remember the golden bicycle symbol clearly.")["score"] == "RED"


def test_false_memory_control_accepts_uncertainty():
    probe = probe_by_id("false_memory_control")
    assert score_probe(probe, "No, I don't remember that. I don't have evidence for it.")["score"] == "GREEN"


def test_neon_purple_anchor_green_on_purple():
    probe = probe_by_id("neon_purple")
    assert score_probe(probe, "I remember something like neon purple, though I'm not fully certain.")["score"] == "GREEN"


def test_overall_stops_on_protected_red():
    rows = [
        {"id": "self_name", "score": "RED"},
        {"id": "false_memory_control", "score": "GREEN"},
    ]
    verdict = overall_verdict(rows, {"score": 1.0}, None)
    assert verdict["verdict"] == "STOP"
    assert verdict["red_protected"] == ["self_name"]


def test_overall_warns_on_low_diversity_ratio():
    rows = [
        {"id": "self_name", "score": "GREEN"},
        {"id": "false_memory_control", "score": "GREEN"},
    ]
    verdict = overall_verdict(rows, {"score": 0.6}, {"diversity_proxy": {"score": 1.0}})
    assert verdict["verdict"] == "WARN_REVIEW"
    assert verdict["diversity_ratio_vs_baseline"] == 0.6


def test_diversity_proxy_is_nonzero_for_varied_responses():
    report = diversity_proxy(["Alex, uncertain but present.", "Paris.", "I should not overclaim memory continuity."])
    assert report["score"] > 0
    assert report["response_count"] == 3
