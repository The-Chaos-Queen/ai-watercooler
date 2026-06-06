# Memory Quality Controller — A/B/C Probe Runbook

## Purpose

Compare answer-time memory integration modes without changing sleep/Qdrant writes.

## Modes

| Flag | Behavior |
|------|----------|
| `--memory-controller off` | Legacy raw recall (default, no behavior change) |
| `--memory-controller modulation` | Modulation packet only — clean memories scored, telemetry demoted, fake-claim guard active |
| `--memory-controller modulation_plus_evidence` | Modulation packet + legacy raw recall block |

## Blind / Natural Vesper Probe Labels

```
--instance-id vesper
--user-label You
--model-label I
--no-shared-memory
--transient
```

Do not use `--model-label Alex` for blind name/identity probes.
Do not set `--user-label Laura` unless Laura is actually the speaker.

## Offline Fixture Probe (no model, no GPU)

```bash
cd MoCoP/experiments/mamba_lora_bridge
python3 run_memory_controller_fixture_probe.py --output /tmp/probe.json
python3 -c "import json; d=json.load(open('/tmp/probe.json')); [print(r['mode'], len(r['prompt']), 'chars') for r in d['runs']]"
```

Outputs three runs (raw / modulation / modulation_plus_evidence) with prompt text and audit metadata. No model call.

## Live A/B/C on ML-WS

Run three chat_server instances (or sequential sessions) with different `--memory-controller` values. Keep all other flags identical.

```bash
# Baseline (A)
python3 chat_server.py --memory-controller off \
  --instance-id vesper --user-label You --model-label I \
  --transient --no-shared-memory

# Modulation only (B)
python3 chat_server.py --memory-controller modulation \
  --instance-id vesper --user-label You --model-label I \
  --transient --no-shared-memory

# Modulation + evidence (C)
python3 chat_server.py --memory-controller modulation_plus_evidence \
  --instance-id vesper --user-label You --model-label I \
  --transient --no-shared-memory
```

For pure autobiographical tests, ensure recall rows prefer `source_type=organic_vesper_memory` and do not force `steve_gate_event`.

## Audit Metadata

When controller is enabled, response JSON includes:

```json
"memory_controller": {
  "mode": "modulation",
  "process_count": 4,
  "memory_process_count": 3,
  "cluster_process_count": 1,
  "clean_process_count": 3,
  "clean_memory_process_count": 3,
  "clean_cluster_process_count": 0,
  "warnings": ["..."],
  "available_memory_count": 3,
  "applied_to_prompt": true,
  "applied_to_state": false
}
```

## Test Suite

```bash
python3 -m pytest test_chat_server_recall.py tests/test_astrocyte_memory_controller.py tests/test_memory_controller_fixture_probe.py -q
```

Expected: 37 passed.
