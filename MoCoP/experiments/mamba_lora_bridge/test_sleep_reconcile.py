import pytest
import datetime
from sleep_reconcile import phase1b_expiration_and_relevance

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
