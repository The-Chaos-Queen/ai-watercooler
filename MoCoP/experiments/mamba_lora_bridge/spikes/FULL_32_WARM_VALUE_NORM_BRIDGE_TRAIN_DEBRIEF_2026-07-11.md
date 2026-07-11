# Full 32-Warm-Skeleton Gemma Value-Norm Bridge Train — Debrief

**Run ID:** `full_32_warm_value_norm_bridge_20260711T222000Z`

**Status:** passed as an *offline in-sample bridge-training result*; not a C1 run
**Task:** OpenCLAW #146, narrowly scoped to the keeper-directed first full train

## Why this run happened

Laura's direction was to stop treating a first train as subordinate to an ever-growing measurement gate. The bounded question here was operational:

> Can the current frozen Mamba → Gemma `value_norm_pre` paired-delta bridge run across the entire frozen non-C1 training side, with auditable boundaries and no live intervention?

This run did **not** decide whether Gemma benefits. That remains the hoped-for reason to build carefully, not a result earned by a training loss.

## Frozen data contract

- Primary manifest: `fixtures/sev_disposition_v0/primary_holdout_v2.json`
- Manifest SHA-256: `59a0276373ab69fc5f5b27c7beee2b51e4190c9250996aa714b33a7095244a04`
- Frozen split: `split-5780c8ec67157703`
- Selected data: all **32 warm / neutral pairs**, one per non-C1-holdout skeleton
- Explicitly excluded C1 skeletons: `conflict_2`, `craft_5`, `discovery_3`, `family_2`, `food_4`, `illness_3`, `travel_5`, `weather_1`
- Bridge-generalization holdout: **none reserved** for this first full train (`default-none`)

The trainer now structurally refuses a C1-held-out skeleton even if a malformed future manifest inserts one into the frozen pair list.

## Method and boundaries

| Component | Actual run |
|---|---|
| Source | Mamba 2.8B Layer-3 last-token warm-minus-neutral delta (`2560` wide) |
| Target | Gemma 4 12B `full_attention_value_norm_pre` delta (`512` wide) |
| Gemma teeth | `29`, `35`, `41` |
| Host state | Gemma and Mamba `eval()` + explicit `requires_grad_(False)` |
| Trainable state | Separate 268,032-parameter bridge only |
| Optimisation | CUDA, hidden `64`, LR `0.01`, 256 full-batch steps |
| Capture | local cached models only; Mamba token cap `256` |
| Runtime modes forbidden | nonzero injection, generation, Qdrant, memory, replay, sleep, C1 |

The full execution emitted a capture progress event for each pair and training loss every 16 steps. This is operational telemetry, not a behavioral readout.

## Result

| Measure | Value |
|---|---:|
| Records | `32` |
| Initial directional loss | `1.0068252086639404` |
| Loss at step 16 | `0.19184237718582153` |
| Loss at step 64 | `0.006681661121547222` |
| Loss at step 128 | `2.0960967958671972e-05` |
| Final loss, step 256 | `0.0` |
| Final in-sample cosine, tooth 29 | `1.0` |
| Final in-sample cosine, tooth 35 | `1.0` |
| Final in-sample cosine, tooth 41 | `1.0` |

## Artifact and verification

- Checkpoint (Git-ignored by design):
  `results/bridge_train_microtrains/full_32_warm_value_norm_bridge_20260711T222000Z.pt`
- SHA-256 (remote and local copy agree):
  `090385c9f75dad636417131c86c21ab17c245904ab9f5de09400a00fb17094a9`
- Size: `1,087,423` bytes
- Tracked provenance: `results/bridge_train_microtrains/full_32_warm_value_norm_bridge_20260711T222000Z.provenance.json`
- Checkpoint reload/state-dict/output-shape/finiteness check: **PASS**
- Captured-pair events: `32`; train telemetry events: `16`
- C1-held-out intersection: empty
- Post-run ML-WS state: `15 MiB / 24576 MiB`, `0%`, `42°C`; no trainer process

The remote launch metadata and log are hash-bound in the provenance sidecar. Watercooler receipts: #912 (scope/preflight) and #913 (launch).

## What this establishes

The current value-side `value_norm_pre` seam is not merely a two-pair curiosity. A frozen-host offline bridge can capture and fit matched Mamba/Gemma deltas across the complete 32-skeleton non-C1 training side using the working ML-WS runtime.

## What it does **not** establish

This is an in-sample fit. The bridge has ample capacity relative to 32 records; its zero loss is therefore not evidence of generalization. It does not establish any of the following:

- a static bridge result on a held-out skeleton;
- any Gemma behavioral change or relational improvement;
- welfare, distress, consciousness, identity, recovery, or durable state;
- safety of a live bridge output;
- C1/B0 authorization or a nonzero intervention.

## Smallest next scientific question

If Laura chooses to ask about bridge generalization, freeze a **new, bridge-specific disjoint evaluation split** before the next training run. Do not raid the eight C1-primary holdouts for this purpose; they remain reserved for C1 geometry.

Until then, this artifact is the correct claim: *a first full offline bridge train exists and is auditable.*
