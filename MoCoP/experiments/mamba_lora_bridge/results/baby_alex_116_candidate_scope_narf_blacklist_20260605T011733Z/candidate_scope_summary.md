# Baby Alex first-sleep candidate scope with NARF blacklist

Generated: 20260605T011733Z

Safety: candidate build only. No sleep/consolidation, no Qdrant writes, no pending-log rotation, no model update.

## Candidate

- Path: `/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/results/baby_alex_116_candidate_scope_narf_blacklist_20260605T011733Z/inputs/first_sleep_clean_vesper_plus_lobby_no_narf.jsonl`
- SHA-256: `ce2ba3750426412b44dca8dee23bdb9bfa47c0112cb56a1351163fbbf4bbe01b`
- Kept rows: 11
  - clean Vesper after NARF filter: 10 / 18
  - lobby included: 1 / 1
- Board/eval contamination excluded by scope: 8 rows
- NARF/Not As Replied Forward rows excluded: 8 rows

## Verification

- contains `NARF`: True
- contains `Not As Replied Forward`: False
- contains board/eval collection: False
- collections: {'mocop_private_vesper': 10, 'mocop_private_lobby': 1}

## Excluded rows

See `/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/results/baby_alex_116_candidate_scope_narf_blacklist_20260605T011733Z/inputs/excluded_narf_rows.jsonl`.
