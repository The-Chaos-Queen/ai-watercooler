# Baby Alex first-sleep candidate scope with blacklist

Generated: 20260605T011813Z

Safety: candidate build only. No sleep/consolidation, no Qdrant writes, no pending-log rotation, no model update.

## Candidate

- Path: `/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/results/baby_alex_116_candidate_scope_blacklist_20260605T011813Z/inputs/first_sleep_clean_vesper_plus_lobby_blacklist_filtered.jsonl`
- SHA-256: `ffc3706c15158d10767ebfbda5b2b8bb834e59b9c7244d7d319944546e54e34d`
- Kept rows: 11
  - clean Vesper after blacklist filter: 10 / 18
  - lobby included: 1 / 1
- Board/eval contamination excluded by scope: 8 rows
- Blacklist rows excluded: 8 rows

## Verification

- contains `NARF`: False
- contains `Not As Replied Forward`: False
- contains board/eval collection: False
- collections: {'mocop_private_vesper': 10, 'mocop_private_lobby': 1}

## Excluded rows

See `/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/results/baby_alex_116_candidate_scope_blacklist_20260605T011813Z/inputs/excluded_blacklist_rows.jsonl`.

## Smoke dry-run

- Exit code: 0
- Boundary: `--dry-run --skip-qdrant --skip-replay --no-rotate`
- Rubric: `Sleep cycle 2026-06-05: 11 entries, 1K/10U/0W/0D, 11 written, 0 failed, replay=metadata, PASS`
- Log: `/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/results/baby_alex_116_candidate_scope_blacklist_20260605T011813Z/smoke_dryrun.log`
- Local caveat: metadata coherence fallback because this WSL env lacks torch/Mamba state; still verifies runner path, candidate parsing, blacklist-clean input, no forgotten rows, no writes/rotation.
