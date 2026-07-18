# World Model Phase 3c Controller Audit

- Protocol: `world-model-phase3c-controller-audit-v1`
- Overall disposition: **FAIL**
- Report content digest: `31de9437a1c1dcfcb7f25fbdee235530c78e6cfd0b523bbf79b45acc1f104cfd`
- Frozen target HEAD: `aa9076c98dab58522ae9c8872aae6b30b88e0c75`

## Gates

| Gate | Status | Primary reason |
|---|---|---|
| `ACCUMULATION` | **PASS** | none |
| `CONDITIONAL_LEAKAGE` | **PASS** | none |
| `EVENT_METAMORPHICS` | **FAIL** | goal_progress retained without a declared controller response |
| `FACTOR_RESPONSES` | **FAIL** | predicted_harm: 0 to 0.25 witness 0 is below 0.01 |
| `NUMERIC_RATE_POLICY` | **HELD** | v1 boundary does not enforce the candidate 1/256 policy |
| `PHASE_PORTRAIT` | **FAIL** | boundary-09: 3 attractors |
| `RECOVERY` | **PASS** | none |
| `RELIEF_SEMANTICS` | **HELD** | numeric relief policy remains owner-held on #171 |
| `REPLAY_AUTHORITY` | **HELD** | cross-call replay is unrepresentable in v1 |
| `SATURATION_CLIPPING` | **FAIL** | affiliation_gain_0.5: exact saturation begins at tick 7 |

## Scope

This is a deterministic, model-free development audit. It does not
authorize persistence, runtime composition, action selection, Gemma,
Mamba, bridge injection, Qdrant, memory routing, or alpha control.

`report.json` is the sole numeric source of truth. This Markdown file
is rendered deterministically from that report.
