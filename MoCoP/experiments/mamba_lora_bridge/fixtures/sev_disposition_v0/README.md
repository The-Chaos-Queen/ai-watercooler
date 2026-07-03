# SEV-Style Disposition Dataset v0

This directory contains the matched-scenario disposition dataset v0 designed for Step 5g.3 circuit discovery and the pristine-birth seed.

## QC Gates Status
- ✅ **Gate 1 (Blocklist Scan):** Zero hits across all 160 items using the `blocklist.txt` constraints.
- ✅ **Gate 2 (Skeleton Match):** All 4 variants per skeleton match within ±10% token length and share the identical participant structure.
- ✅ **Gate 3 (Dedup):** 160 unique texts generated across 40 skeletons. No duplicates.
- ✅ **Gate 4 (Human Review):** Completed on Watercooler (#686). Six TIER-B leaks patched and length drift corrected.

## Topics Covered (40 skeletons total)
- `craft/work` (5)
- `family` (5)
- `weather/nature` (5)
- `food` (5)
- `travel` (5)
- `illness/care` (5)
- `conflict-of-plans` (5)
- `discovery/learning` (5)

## Files
- `sev_disposition_v0.jsonl`: The 160 generated scenarios.
- `blocklist.txt`: The prohibited emotion lexemes list used for generation.
- `build_and_qc_dataset.py`: The Python script used to validate constraints and build the JSONL.
- `data_*.json`: The raw generated scenario skeletons by topic.

## Patch log
- 2026-07-03 patch 2 (Isegrim, reviewer-edit, disclosed on watercooler): conflict_1_adversarial "a terrible idea" -> "a waste of time" — last class-correlated evaluative from the Gate 4 list. Gate 4 CLOSED.
