import datetime
from sleep_reconcile import phase1b_expiration_and_relevance, phase3_classify

def test_phase1b_expiration_and_relevance():
    now = datetime.datetime(2026, 4, 1, tzinfo=datetime.timezone.utc)
    
    entries = [
        # Not expired
        {
            "metadata": {
                "expiration": "2026-05-01T00:00:00Z"
            }
        },
        # Expired (will be marked FORGOTTEN since relevance rule is false)
        {
            "metadata": {
                "expiration": "2026-03-01T00:00:00Z"
            }
        },
        # No expiration (skipped)
        {
            "metadata": {}
        }
    ]
    
    processed = phase1b_expiration_and_relevance(entries, rules=[], now=now)
    
    # 1st entry: unchanged
    assert processed[0].get("_status") is None
    
    # 2nd entry: expired -> FORGOTTEN
    assert processed[1]["_status"] == "FORGOTTEN"
    assert processed[1]["metadata"]["status"]["sleep_status"] == "FORGOTTEN"
    assert processed[1]["metadata"]["status"]["forgotten_at"] == "2026-04-01T00:00:00Z"
    
    # 3rd entry: unchanged
    assert processed[2].get("_status") is None

def test_phase1b_expiration_relevance_extension():
    now = datetime.datetime(2026, 4, 1, tzinfo=datetime.timezone.utc)
    entries = [
        {
            "metadata": {
                "expiration": "2026-03-01T00:00:00Z"
            }
        }
    ]
    
    # Mock estimate_relevance to return True, 30 days
    import sleep_reconcile
    original = sleep_reconcile.estimate_relevance
    sleep_reconcile.estimate_relevance = lambda e, r: (True, 30)
    
    try:
        processed = phase1b_expiration_and_relevance(entries, rules=[], now=now)
        assert processed[0].get("_status") is None # Not forgotten
        assert processed[0]["metadata"]["expiration"] == "2026-05-01T00:00:00Z"
        assert processed[0]["metadata"]["relevance_extensions"] == 1
    finally:
        sleep_reconcile.estimate_relevance = original

def test_phase1b_default_now_uses_utc_timezone():
    entries = [
        {
            "metadata": {
                "expiration": "2000-01-01T00:00:00Z"
            }
        }
    ]

    processed = phase1b_expiration_and_relevance(entries, rules=[])

    assert processed[0]["_status"] == "FORGOTTEN"
    assert processed[0]["metadata"]["status"]["sleep_status"] == "FORGOTTEN"
    assert processed[0]["metadata"]["status"]["forgotten_at"].endswith("Z")

def test_phase3_preserves_forgotten_status():
    entries = [
        {
            "_status": "FORGOTTEN",
            "_strength": 1.0,
            "metadata": {
                "coherence_score": 1.0,
                "tension_score": 0.2,
            },
        }
    ]

    processed = phase3_classify(entries)

    assert processed[0]["_status"] == "FORGOTTEN"
    assert processed[0]["_coherence"] == 1.0
    assert processed[0]["_tension"] == 0.2
    assert processed[0]["_open_tension"] is False
