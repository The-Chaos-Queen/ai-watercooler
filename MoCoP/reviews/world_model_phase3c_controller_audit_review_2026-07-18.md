# World Model Phase 3c Controller Audit Review

**Date:** 2026-07-18
**OpenCLAW:** `#172`
**Protocol:** `world-model-phase3c-controller-audit-v1`
**Preregistration commit:** `8873213`
**Runner/test commit:** `d275850`
**Frozen target HEAD:** `aa9076c98dab58522ae9c8872aae6b30b88e0c75`
**Disposition:** **FAIL**
**Scope:** deterministic model-free controller audit only

## Verdict

The current `WorldEvent -> AppraisalVector -> KappaState + RegulatoryState`
kernel is bounded and deterministic, but its response surface is not suitable
for composition. Retained inputs are dynamically inert, the long-horizon map
contains large adjacent-bin discontinuities and more than two corner-reachable
attractors on four critical boundary rows, and a moderate affiliation input
hits exact clipping. These are controller-geometry failures, not evidence of
model, memory, bridge, or runtime behavior.

The audit also establishes useful negative controls. Recovery and accumulation
pass their frozen gates. Conditional person/topic/episode recovery stays exactly
at 16-class chance on every registered numeric surface and classifier, while the
positive canary reaches `1.0` before filtering and returns to `0.0625` after the
candidate `1/256` filter.

## Custody

- Main run: Python `3.13.9`, 1,313 seconds, no model/GPU/network/Qdrant input.
- Result bundle:
  `experiments/mamba_lora_bridge/results/world_model_phase3/controller_audit_v1/`
- Report content digest, excluding only its digest field:
  `31de9437a1c1dcfcb7f25fbdee235530c78e6cfd0b523bbf79b45acc1f104cfd`
- Final `report.json` and sidecar SHA-256:
  `c17409c7731c8d11e12706a933c7efeabfc2f7c839cefb42b3349ee44295909e`
- `report.json` size: 21,512,467 bytes.
- Independent pre-run implementation review: GREEN after 14 focused tests,
  Ruff, `py_compile`, and scoped diff checks.
- Post-run validation rechecked the report self-digest, exact probe/gate
  agreement, construction holds, frozen prereg blob, and all source blobs.

## Gate Table

| Gate | Result | Primary evidence |
|---|---|---|
| `EVENT_METAMORPHICS` | **FAIL** | retained positive goal progress has no controller response |
| `FACTOR_RESPONSES` | **FAIL** | dead harm/error witnesses, inert positive goal, 540 wide factor/state deadbands |
| `PHASE_PORTRAIT` | **FAIL** | four three-attractor boundary rows; maximum adjacent-bin jump `1.0` |
| `RECOVERY` | PASS | all 414 registered starts meet tick-32/tick-40 and rebound gates |
| `ACCUMULATION` | PASS | occurrence decays; 64-tick unresolved norm remains bounded and recovers |
| `CONDITIONAL_LEAKAGE` | PASS | every held-out result `0.0625`; canary `1.0 -> 0.0625` |
| `SATURATION_CLIPPING` | **FAIL** | affiliation `+0.5` first reaches exact `1.0` at tick 7 |
| `RELIEF_SEMANTICS` | HELD | numeric relief policy remains owner-held on `#171` |
| `NUMERIC_RATE_POLICY` | HELD | v1 does not enforce the candidate `1/256` boundary policy |
| `REPLAY_AUTHORITY` | HELD | in-batch duplicates refuse; cross-call authority is absent in v1 |

## Main Findings

### 1. Retained inputs are not identified

- Harm `0 -> 0.25` has zero declared vigilance witness; the baseline fine scan
  has an undeclared deadband of `0.43359375`.
- Prediction error has zero witness and a full-width `1.0` deadband.
- Positive goal progress is inert and has a full-width `1.0` deadband.
- Across the exact 499,122-row fine state grid, 540 factor/state rows have a
  deadband wider than `0.25`.

The event schema must not retain numeric fields that the controller ignores.
Any repair must either connect the field to a declared response or remove it in
a new reviewed contract.

### 2. Small input changes can switch long-run regime

The fine grid found 486 factor/state adjacent intervals above the frozen `0.10`
terminal-jump ceiling. The largest jump is exactly `1.0`: from initial state
`(0,0,0,0,0)`, harm `0.546875 -> 0.55078125` switches reserve from `1` to `0`
at tick 256 while vigilance/load move from approximately
`(0.197780, 0)` to `(0.689926, 0.689907)`.

This is a controller phase transition under a one-bin input change. It is not a
calibration nuisance and should not be hidden by averaging.

### 3. The critical boundary has more than two attractors

All 23,328 stationary-grid and 2,720 analytic-boundary trajectories classified
as fixed points; no autonomous cycle was found. However, boundary rows 09, 27,
46, and 80 each expose three corner-reachable attractor clusters. A further 134
stationary/boundary/named rows expose two clusters and remain policy-relevant
even though the four three-cluster rows already force FAIL.

The periodic matrix is well behaved within its tested surface: 96 trajectories
settle to period 1 and 160 to the expected forced period 2, with no larger or
post-washout cycle.

### 4. Moderate affiliation drive clips

The baseline affiliation `+0.5` trajectory reaches exact affiliation `1.0` at
tick 7 and remains clipped. Independent pre/post-clip reconstruction otherwise
matches the kernel to `1.1102230246251565e-16`, well inside `1e-12`.

The failure is therefore actual coefficient/geometry behavior, not a runner
reconstruction error.

### 5. Recovery, accumulation, and conditional leakage are clean

- All 414 deduplicated recovery starts pass the fixed tick-32, tick-40, and
  actual-crossing rebound rules.
- The one-occurrence norm arm never re-accumulates; the 64-tick unresolved arm
  remains below `0.95` and recovers within 40 neutral ticks.
- Matched numeric trajectories are bit-identical across every person, topic,
  and episode identity. Nearest-centroid and diagonal-Gaussian balanced accuracy
  are `0.0625` for q, kappa, regulatory, and concatenated numeric views.
- The fixed positive canary is recovered at `1.0` before filtering and falls to
  `0.0625` after the candidate `1/256` filter, validating both sensitivity and
  suppression.

This is conditional leakage evidence only. It does not clear a producer that
encodes identity in registered event kinds, magnitude, confidence, timing, or
rate; those controls remain with `#171`.

## Required Successor Work

Do not patch coefficients against this report and relabel the same packet. A
successor requires a new frozen protocol and must preserve this FAIL result.

1. Decide whether `prediction_error` and positive `goal_progress` are retained;
   connect each retained field to a directional response or remove it.
2. Redesign the vigilance/reserve/load geometry so one-bin inputs cannot switch
   terminal reserve/load by the observed amount; re-audit the analytic branch
   boundaries and all 243-state adjacent bins.
3. Decide whether any hysteresis is intentional. If yes, freeze an explicit
   basin count and transition policy; the current three-attractor rows are not
   admissible under v1.
4. Remove moderate-input exact affiliation clipping or freeze a reviewed
   saturation contract that justifies it.
5. Complete `#171` event lifecycle, replay authority, relief semantics, and
   enforced numeric/rate boundary before any composition claim.

No Gemma, Mamba, bridge, alpha, Qdrant, persistence, memory-routing, action, or
runtime authorization follows from the passing rows in this audit.
