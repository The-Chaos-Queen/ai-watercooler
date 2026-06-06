# Baby-Alex #116 cluster/default-path preflight

Generated: `2026-06-03T20:47:41Z`

## Verdict

- verdict: **PASS**

## Conditions

- private_session: `True`
- server_launched_no_ambient_recall: `True`
- server_not_launched_cluster_recall: `True`
- status_recall_counters_zero_for_preflight_session: `True`
- memory_mode_recorded: `True`

## Runtime command

```text
bash -c cd ~/mocop/mamba_lora_bridge && LOG=logs/mlws_chat_15b_state_memory.log && nohup /home/isabell/miniforge3/bin/mamba run -n torch311 python chat_server.py --model Qwen/Qwen2.5-1.5B --bridge-path cheese_reincarnation_bridge_1.5b_codexfix.pt --episodes-file CHEESE_SHAPING_EPISODES.md --episode-index 2 --instance-id lobby --no-shared-memory --qdrant-host 192.168.2.191 --qdrant-port 6333 --no-ambient-recall --memory-integration-mode both --memory-state-max-tokens 768 --live-accumulation --qwen-device cuda:0 --mamba-device cuda:0 --user-label User --model-label Alex --alpha 0.2 --temperature 0.2 --max-new-tokens 120 --host 0.0.0.0 --port 7860 >> "$LOG" 2>&1 < /dev/null & echo $!
```

## Status subset

- running: `True`
- busy: `False`
- last_error: ``
- model_id: `Qwen/Qwen2.5-1.5B`
- session_id: `baby-alex-116-20260603`
- instance_id: `baby-alex-116-20260603`
- user_label: `Techno-Monk`
- model_label: `Alex`
- no_shared_memory: `True`
- qdrant_collection: `mocop_private_baby-alex-116-20260603`
- qdrant_write_mode: `critical-only`
- qdrant_pending_count: `27`
- qdrant_sleep_pending_count: `27`
- qdrant_retry_pending_count: `0`
- qdrant_replayed_count: `0`
- formation_log_count: `14`
- formation_queued_count: `8`
- formation_written_count: `1`
- live_accumulation_enabled: `True`
- live_accumulation_updates: `0`
- memory_integration_mode: `None`
- recall_request_count: `0`
- recall_hit_count: `0`
- last_recall: `{}`
- alpha: `0.2`
- temperature: `0.2`

## Code evidence

- `chat_server.py:5081-5105` — chat body defaults allow_auto_recall=True, but ambient recall only auto-starts if ARGS.ambient_recall and not transient; explicit identity/memory probes can also auto-recall unless clients pass allow_auto_recall=false.
- `chat_server.py:5135-5143 and 5167-5178` — cluster recall is only attempted after private recall returns memories and ARGS.cluster_recall is true; failed cluster recall falls back to flat anchors only.
- `chat_server.py:5515-5537` — ambient recall defaults true unless launched with --no-ambient-recall; cluster recall defaults false unless launched with --cluster-recall.

## Interpretation

This preflight does not prove that future explicit recall cannot use clusters. It proves the current live server was not launched with cluster recall as a default path, ambient recall is disabled by launch flag, and this private preflight session has no recall requests/hits before any chat turn. Explicit client recall remains a separate, auditable action.