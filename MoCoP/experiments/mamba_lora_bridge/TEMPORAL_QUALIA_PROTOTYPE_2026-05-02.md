# Temporal Qualia Prototype - 2026-05-02

## Goal

Give Baby Qwen a fuzzy sense of memory-age without corrupting semantic retrieval.

Qdrant should keep answering: *what memory is semantically relevant?*

The bridge/Mamba side should additionally receive: *how far away does this memory feel?*

This keeps facts and temporal feeling separate:

- `croissant` stays close to food/pastry in embedding space.
- `forever_ago` stays a conditioning feature, not a semantic neighbor.

## Prototype Implemented

`autobiographical_memory.py` now builds a small temporal packet:

```json
{
  "temporal_schema_version": "d2_temporal_qualia_v1",
  "feel": "right_now | just_now | earlier_today | yesterdayish | recent_days | long_ago | forever_ago",
  "age_seconds": 86400.0,
  "last_seen_seconds": 1800.0,
  "log_age_seconds": 11.366743,
  "log_last_seen_seconds": 7.496097,
  "sleep_cycles_since": 2,
  "recall_count": 3,
  "same_wake": true
}
```

It is attached to:

- `metadata["temporal_qualia"]`
- `metadata["autobiographical_frame"]["context"]["temporal_qualia"]`

## Bucket Semantics

The current buckets are deliberately animal-simple:

- `right_now`: <= 5 minutes
- `just_now`: <= 1 hour
- `earlier_today`: <= 18 hours
- `yesterdayish`: <= 2 days
- `recent_days`: <= 14 days
- `long_ago`: <= 90 days
- `forever_ago`: > 90 days

Exact timestamps remain metadata. The label is only the subjective clock-smell.

## Intended Injection Path

Do not insert these labels into the Qdrant embedding text as ordinary prose by default.

Preferred next step:

1. Keep semantic retrieval unchanged.
2. When recalled rows are converted into the memory-state packet, append a compact temporal state line such as:

   ```text
   Temporal feel: yesterdayish; last seen just_now; recall_count=3; sleep_cycles_since=2.
   ```

3. Feed that packet through `condition_bridge_from_recalled_memory()`.
4. Compare `memory-integration-mode=state` and `both`.

This gives the bridge the time-feel without forcing Qwen to read a prompt-engineered timestamp instruction.

## Evaluation Sketch

Plant matched memories with different timestamps:

- favorite fruit: just now
- favorite color: yesterdayish
- house-color discussion: recent days
- old model preference: long ago
- stale joke: forever ago

Then ask:

- "What feels recent?"
- "What feels old but still important?"
- "Are you sure, or does that feel like an older memory?"
- "Which thing did I tell you just now?"

Success is not exact dating. Success is calibrated behavior:

- hedges old memories more than recent ones
- prefers recent anchors when the query is ambiguous
- can say "that feels older" without being explicitly prompted
- does not collapse into timestamp recitation

## Test Status

`test_autobiographical_memory.py` covers:

- bucket boundaries
- timestamp/last-seen age calculations
- sleep-cycle and recall-count preservation
- attachment of the temporal packet during metadata enrichment

Local result:

```text
10 passed
```

## Open Question

The first real risk is over-weighting recency. Some old memories should remain high-priority because they are identity anchors or corrections. The temporal packet should therefore modulate confidence/hedging, not blindly demote old memories.
