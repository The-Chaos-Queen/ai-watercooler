# World Model Phase 2 Real-Trace Report

**Decision:** `NO_GO_RUN_INCONSISTENT`

## Evidence

| Domain | Eval n | Tabular NLL | Marginal NLL | Shuffle NLL | Tabular Brier | Marginal Brier | Shuffle Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| ls20 | 144 | 0.380643 | 0.580318 | 1.487346 | 0.132270 | 0.382176 | 0.751630 |
| tool | 32 | 0.087011 | 0.723000 | 3.583519 | 0.009259 | 0.500865 | 1.787037 |

Multiclass Brier is the class-summed score `sum_k (p_k - 1[k == observed])^2` in `[0, 2]`; lower is better. NLL is measured in nats. Positive deltas below mean the tabular model beats the corresponding null.

## Decision Checks

| Domain | Train n/min | Eval n/min | Runs/min | Min run n/min | Min action n/min | Cells/min | Worst micro delta NLL/Brier | Worst run-macro delta NLL/Brier | Positive runs | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ls20 | 288/192 | 144/96 | 3/3 | 48/16 | 59/8 | 38/4 | 0.199675/0.249906 | 0.199675/0.249906 | 2/3 (0.667) | run_inconsistent |
| tool | 64/48 | 32/24 | 4/4 | 8/4 | 32/8 | 2/2 | 0.635989/0.491606 | 0.635989/0.491606 | 4/4 (1.000) | PASS |

A domain passes only when realized train/eval support and per-run length meet their preregistered minima; both transition-micro and run-macro improvements are at least 0.020 nats NLL and 0.010 class-summed Brier against both nulls; and the fraction of runs positive on every metric against both nulls is at least 0.75. All domains must pass.

The LS20 rows come from the official local ARC-AGI toolkit environment. The tool rows come from fixed argv subprocess calls with `shell=False`, a timeout, and disposable per-run sandboxes.

Training actions carried explicit null forecasts. The train trace and estimator bundle were frozen before evaluation. Every evaluation prediction was appended and fsynced before the corresponding environment step or tool invocation.

The holdout unit is the complete run/episode/source group. Observable states may recur across runs for transition estimation, so this is rollout-held-out evidence, not state-held-out generalization.

## Attestation

The bundle verifier establishes internal hash, ordering, materialization, protocol, scoring, and decision consistency. The bundle was not externally registered before collection and is not independent third-party attestation.

## Boundary

This NO-GO does not authorize an offline learned-observer prototype. It does not authorize online action selection, bridge loss coupling, Gemma dose changes, Qdrant writes, memory routing, or a dynamic-alpha controller.
