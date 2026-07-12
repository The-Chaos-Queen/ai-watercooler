# World Model Phase 2b LS20 Consistency Replication

**Decision:** `GO_LS20_CONSISTENCY_REPLICATED`

## Aggregate Evidence

| Eval n | Tabular NLL | Marginal NLL | Shuffle NLL | Tabular Brier | Marginal Brier | Shuffle Brier |
|---:|---:|---:|---:|---:|---:|---:|
| 768 | 0.495680 | 0.605049 | 1.476581 | 0.196637 | 0.404740 | 0.739156 |

## Run Evidence

| Run | n | Marginal delta NLL/Brier | Shuffle delta NLL/Brier | Positive |
|---|---:|---:|---:|---|
| phase2b-ls20-eval-000 | 48 | 0.149625/0.188562 | 1.099456/0.605410 | yes |
| phase2b-ls20-eval-001 | 48 | 0.083633/0.196840 | 1.403685/0.776280 | yes |
| phase2b-ls20-eval-002 | 48 | 0.335999/0.362317 | 1.248504/0.690744 | yes |
| phase2b-ls20-eval-003 | 48 | 0.104697/0.166425 | 0.483126/0.269780 | yes |
| phase2b-ls20-eval-004 | 48 | 0.034103/0.163895 | 0.930814/0.511137 | yes |
| phase2b-ls20-eval-005 | 48 | 0.218902/0.257911 | 0.743020/0.409780 | yes |
| phase2b-ls20-eval-006 | 48 | 0.140114/0.215049 | 1.063361/0.595345 | yes |
| phase2b-ls20-eval-007 | 48 | -0.050857/0.067016 | 0.354957/0.205035 | no |
| phase2b-ls20-eval-008 | 48 | 0.074974/0.201771 | 1.240235/0.679113 | yes |
| phase2b-ls20-eval-009 | 48 | -0.123807/0.149411 | 0.419744/0.223773 | no |
| phase2b-ls20-eval-010 | 48 | -0.259625/-0.002526 | 0.628367/0.338775 | no |
| phase2b-ls20-eval-011 | 48 | 0.097258/0.146104 | 0.754801/0.422225 | yes |
| phase2b-ls20-eval-012 | 48 | 0.359329/0.406872 | 1.561855/0.864026 | yes |
| phase2b-ls20-eval-013 | 48 | 0.049896/0.182151 | 0.719044/0.395424 | yes |
| phase2b-ls20-eval-014 | 48 | 0.325678/0.356807 | 2.031359/1.122128 | yes |
| phase2b-ls20-eval-015 | 48 | 0.209980/0.271046 | 1.012094/0.571337 | yes |

## Decision Checks

Support: `PASS`. Micro effects: `PASS`. Run-macro effects: `PASS`. Consistency: `13/16` (`PASS`). Short runs: `0/4` (threshold `<16`).

NLL is in nats. Brier is the class-summed multiclass score in `[0, 2]`. Positive deltas mean the exact v1 tabular estimator beats the named exact v1 null. A run with fewer than 16 transitions is automatically non-positive.

## Boundary

This scoped result addresses LS20 rollout consistency only. It does not alter the v1 result by pooling rows and does not authorize a learned observer or any runtime, bridge, Gemma, Qdrant, memory-routing, or dynamic-alpha integration.
