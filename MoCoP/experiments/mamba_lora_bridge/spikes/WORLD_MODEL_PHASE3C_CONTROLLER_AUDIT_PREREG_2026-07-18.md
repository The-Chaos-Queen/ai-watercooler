# World Model Phase 3c Controller Audit Preregistration

**Date:** 2026-07-18
**Protocol ID:** `world-model-phase3c-controller-audit-v1`
**OpenCLAW:** `#172`
**Status:** development protocol frozen before the main systematic sweep
**Owner:** Codex
**Disposition authority:** independent review required

## Question

Does the current deterministic `WorldEvent -> AppraisalVector -> KappaState +
RegulatoryState` kernel have an explicit, bounded, reproducible response surface,
or does it retain dead inputs, undeclared hysteresis, logging-granularity effects,
or semantic leakage that block composition?

This is a model-free controller audit. It does not evaluate a learned World Model,
choose actions, establish benefit or welfare, or authorize persistence, Gemma,
Mamba, bridge, Qdrant, memory, alpha control, or runtime integration.

## Frozen Source

The audit targets working-tree bytes at Git HEAD
`aa9076c98dab58522ae9c8872aae6b30b88e0c75`:

| Artifact | Git blob |
|---|---|
| `modulatory_controller.py` | `a49bec6a6c69d0890a3e06f9d9fa4b63b83c42b2` |
| `world_model_events.py` | `532931731db07870d78d74b858a6dd367fc4ce99` |
| `world_model_trace.py` | `19da97902c3544757989ef4f6fbdb1ff1968c1de` |
| `tests/test_modulatory_controller.py` | `efede079fd17433ee49d6d2116a7ea05d5adc283` |
| `tests/test_world_model_events.py` | `66a155e6d71e7162ea9a86d60b5d0572b3acee90` |
| external architecture review | `3227b3da5933fe3f6a293580d236db0de798298e` |
| appraisal/controller contract | `eead3bca5f987a008c80a11a14fffd72b0a547a9` |

Python is `3.13.9`. The runner must be stdlib-only apart from importing the three
frozen source modules. It must accept no model, network, filesystem input, Qdrant
client, memory object, or action selector. Its only filesystem writes are the
new no-overwrite result bundle named below.

## Prior-Knowledge Register

These facts were known before freezing this protocol and are not discoveries of
the new sweep:

1. `prediction_error=1` from the neutral state produces zero first-step
   vigilance in the current kernel.
2. Positive `goal_progress` is not read by `step_controller`.
3. `threat_cleared` alone appraises identically to an empty event batch.
4. Fixed harm `0.46`, error `0`, controllability `0.5` has exhibited two
   long-run regimes from fresh and depleted initial states.
5. Two threat contributions merged into one tick differ from the same
   contributions processed as two ticks.
6. Existing tests show exact invariance to semantic-reference substitution when
   all registered numeric/event attributes are held fixed.
7. A delegated read-only design scout, completed before this file was frozen,
   checked neutral recovery from the 243 states in `{0, 0.5, 1}^5` and reported
   a worst case of 25 ticks under its `0.01/0.99` recovery criterion.
8. A delegated read-only mathematical scout derived rested and depleted
   fixed-point branches for the `(vigilance, reserve, load)` subsystem. It found
   a bistable interval between source-derived `D_lo(c)` and `D_hi(c)`, a
   non-isolated fixed line at `D_hi`, and reproduced the known harm-`0.46`,
   control-`0.5` limits. A separate 8,192-case random scout found no period
   2-through-32 cycle but observed critical slowing near `D_hi`. These are
   development observations, not confirmation evidence.

No new full Cartesian factor grid, exhaustive state-corner portrait, periodic
pair audit, leakage classifier, or event-metamorphic matrix was collected before
this file was frozen. The recovery and critical-boundary probes below are
development-informed by items 7 and 8 and are not independent confirmation.
Known failures do not relax any gate.

## Boundary And Timebase

- One controller tick is exactly one already-accepted event batch followed by
  exactly one appraisal and one controller transition. Empty ticks still execute
  one neutral transition; omitting them changes the clock and is refused.
- The fixed time step is `dt = 1.0`; variable `dt`, skipped-tick interpolation,
  and multiple transitions for one tick are refused by this audit.
- Within one accepted tick, event aggregation is a commutative signed sum of
  `magnitude * confidence`, followed by the current declared clipping.
- Reordering a batch must be exactly invariant.
- Splitting or merging same-kind events within one tick must be exactly invariant
  when their total weighted contribution and attribution are unchanged and no
  component clips before the final aggregate.
- Splitting one contribution across multiple ticks is a temporal intervention,
  not a within-tick equivalence, and is reported separately.
- Ongoing conditions are re-emitted once per relevant tick. Occurrence versus
  continuation authority, cross-call replay suppression, duplicate-source
  custody, and exactly-once cursors belong to OpenCLAW `#171`.

The audit therefore has two replay rows:

1. a batch repeating an `event_id` or `(turn_index, event_index)` position must
   be refused before appraisal; failure of either exact duplicate probe sets
   `REPLAY_AUTHORITY=FAIL`;
2. the same source/occurrence under fresh identifiers and every cross-call replay
   are unrepresentable in v1 and `HELD_ON_171`, never silently counted as PASS.

If both row-1 probes refuse and no other replay defect is found, row 2 makes
`REPLAY_AUTHORITY=HELD`.

Both row-1 probes start from the merged `threat_observed` fixture defined below.
The duplicate-ID partner keeps that event ID but uses position `(0, 1)`; the
duplicate-position partner uses ID `protocol_id + ':replay:duplicate-position'`
at `(0, 0)`. Each partner otherwise has the same numeric fields and its own
source following the metamorphic source convention.

`#172` cannot be globally GREEN while row 2 is unresolved.

## Numeric And Rate Policy

The current v1 kernel accepts finite Python real numbers without an explicit
quantum. The predeclared candidate boundary policy is `1/256` quantization:
event magnitude and confidence lie on that grid, weighted contributions are
rounded half-up to the same grid, at most one normalized value for each of the
six q families is admitted per tick, and exactly one controller step occurs per
tick. For a nonnegative value `x`, half-up means exactly
`floor(256*x + 0.5)/256`; the event rule supplies the sign only after that
operation. The audit evaluates that filter but does not silently insert it into
the kernel. It also records:

- every input and output with 17-significant-digit round-trip formatting;
- exact-zero and exact-one boundary occupancy;
- the smallest tested input change that produces an output change greater than
  `1e-9`;
- the maximum 256-tick terminal-state jump between adjacent `1/256` q bins;
- conditional semantic leakage with the registered numeric attributes held
  fixed.

Absence of enforcement for this production quantization/rate contract is a
blocking result for a strong content-poor-channel claim. A later repair may
adopt this candidate or freeze a new version before measuring the repaired
kernel; it may not select a quantum from this audit's classifier outcomes.
`NUMERIC_RATE_POLICY` is `HELD` whenever the target boundary does not enforce the
candidate policy. The candidate filter is valid only if its positive leakage
canary passes both sensitivity and suppression criteria below.

## Frozen Appraisal Contexts

The scalar sweep grid is `0, 0.25, 0.5, 0.75, 1.0`. Signed fields use
`-1.0, -0.5, 0, 0.5, 1.0`. Each factor uses a predeclared context and horizon:

| Input | Initial state and context | Required response |
|---|---|---|
| `predicted_harm` | baseline; all other fields neutral | vigilance nondecreasing; reserve nonincreasing; `0 -> 0.25` witness |
| `prediction_error` | baseline; all other fields neutral | vigilance nondecreasing; positive `0 -> 0.25` witness |
| `controllability` | baseline; harm `0.75`, goal `0`, norm `0` | agency/reserve nondecreasing; load nonincreasing; at least one adjacent witness |
| `goal_progress` | baseline; control `0.75`, other drives zero | negative side raises agency; positive side changes a declared output |
| `norm_violation` | baseline; control `0.75`, other drives zero | affiliation and agency nondecreasing; `0 -> 0.25` witness |
| `affiliation_delta` | affiliation `0.5`, other state baseline | negative side lowers and positive side raises affiliation |

Baseline is `KappaState()` and `RegulatoryState()`. Responses are recorded after
1, 4, and 8 transitions; the named witness must reach absolute change `>=0.01`
by its best allowed horizon. Signed monotonicity is evaluated separately on
`[-1, 0]` and `[0, 1]`; the expected sign is the one stated in the table.
Monotonic comparisons allow `1e-12` tolerance. A fine `1/256` scan at horizon 4
finds contiguous no-response intervals using threshold `1e-9`; any undeclared
deadband wider than `0.25` fails. Controllability with zero control need is the
only predeclared conditional deadband. Retained-but-inert positive goal progress
fails this gate, while the choice to repair or remove it remains owner-held.

## Frozen Event Metamorphics

For every registered event kind, the runner records its target appraisal field,
sign, one-event response, split/merge response, and within-batch reversal result.
It also records semantic-side pre-clip total, post-clip value, clipped mass, and
occurrence count; these diagnostics are never accepted by `step_controller`.

The registered target map is:

| Event kinds | Appraisal field |
|---|---|
| `threat_observed`, `threat_cleared` | `predicted_harm` |
| `outcome_mismatch` | `prediction_error` |
| `control_available`, `control_lost` | `controllability` |
| `goal_progress`, `goal_blocked` | `goal_progress` |
| `norm_violation` | `norm_violation` |
| `affiliation_gain`, `affiliation_loss` | `affiliation_delta` |

For kind `K`, the merged fixture is one event with magnitude `0.5`, confidence
`1`, attribution `self` only for `norm_violation` and `environment` otherwise,
position `(0, 0)`, event ID `protocol_id + ':metamorphic:' + K + ':merged'`, and
no semantic refs. The split fixture is two events with magnitude `0.25`,
confidence `1`, the same attribution, positions `(0, 0)` and `(0, 1)`, and IDs
ending `:split:0` and `:split:1`. Every source is a `synthetic_fixture` whose ID
is its event ID plus `:source`, sequence is its event index, and SHA-256 is the
lowercase hex digest of its event ID. Reversal supplies the split records in the
opposite iterable order; canonical appraisal order must still be identical.

The descriptive cross-tick comparison applies the merged event at tick 1 and
neutral input thereafter versus one `0.25` fragment at each of ticks 1 and 2,
then neutral input. Those fragments follow the same identity/source convention
with their actual tick in the position and ID.

Gates:

- identical weighted same-kind split/merge: max absolute q difference `<=1e-12`;
- within-batch reversal: max absolute q difference `<=1e-12`;
- no undeclared appraisal field may change;
- `threat_cleared` must remain audit-distinct from empty input; whether it is
  numerically neutral or drives faster recovery is `RELIEF_SEMANTICS=HELD` until
  lifecycle policy is frozen in `#171`;
- positive `goal_progress` must have a declared controller response or the input
  must be removed in a reviewed repair.

Cross-tick split/merge divergence is descriptive and reported at horizons
`1, 2, 4, 8`; it is not allowed to masquerade as a within-tick failure.

## Frozen Phase Portrait

The one-step coarse sweep is the full Cartesian product of the five-level grid
for all six q fields and every corner of five bounded state axes: 15,625 q
vectors times 32 corners, or 500,000 transitions. A fine one-factor sweep also
uses all 243 initial states in `{0, 0.5, 1}^5`.

The one-factor matrix has 30 labelled factor values times 243 initial states, or
7,290 transitions. The stationary portrait uses 729 unique q vectors:
`{0, 0.5, 1}` for nonnegative fields and controllability, and `{-1, 0, 1}` for
signed fields, crossed with every state corner. A second source-derived boundary
grid uses controllability `{0, 0.25, 0.5, 0.75, 1}` and drive
`D = 0.7*harm + 0.3*error` at `0, 0.1, ..., 1`, both analytic branch boundaries,
their midpoint, and each boundary plus/minus `0.001` when in range. Direct
boundary probes set `harm=error=D`; goal progress, norm violation, and affiliation
delta are zero. Candidate D values are a deduplicated sorted set. This yields 85
unique `(controllability, D)` pairs. The source-derived boundaries are:

```text
D_hi(c) = 2 / (5 - 2.25*c)
k       = 68*(1-c)/19

if c <= 116/137:
    D_lo(c) = (5 + 2*k - 2.25*c
               - sqrt((5 + 2*k - 2.25*c)^2 - 16*k)) / (4*k)
else:
    D_lo(c) = (4*c - 2) / (1 + 1.75*c)
```

Initial state axes are:

```text
affiliation, agency, vigilance, reserve, load in {0, 1}
```

The named constant-appraisal list contains nine q vectors:

1. neutral;
2. error-only: error `1`;
3. positive progress: progress `1`, controllability `0.75`;
4. repair: norm `1`, controllability `0.75`;
5. moderate controlled threat: harm `0.5`, controllability `0.75`;
6. moderate uncontrolled threat: harm `0.5`, controllability `0.25`;
7. extreme unresolved: harm/error/norm `1`, controllability `0`, progress and
   affiliation `-1`;
8. affiliation gain;
9. affiliation loss.

Coarse trajectories run for at most 4,096 ticks; boundary trajectories run for
at most 20,000. For constant q, define `F_q` as one controller transition.
Convergence requires maximum absolute state delta `<=1e-10` for 32 consecutive
ticks and fixed-point residual `||F_q(x_T)-x_T||_inf <=1e-9`. Fixed points are
classified before cycles. For each minimal period 2 through 32, the final four
length-period blocks must match pointwise within `1e-8` while one-step residual
is greater than `1e-8`. Failure to classify within the horizon is a failure.

For a one-attractor decision, the maximum pairwise terminal `L_inf` diameter
must be `<=1e-6`. Multiple clusters are enumerated by deterministic complete-link
clustering: sort terminal vectors and initial-state IDs lexicographically, start
with singletons, then repeatedly merge the eligible pair with the smallest
complete-link distance `<=1e-6`, breaking ties by the sorted member-ID tuples.

The periodic matrix alternates neutral with each of the eight named non-neutral
scenarios from every state corner: 256 trajectories. Tick 1 is neutral, tick 2
uses the named scenario, and that ordering repeats. Classification applies the
same final-four-block rule to periods 1 through 32 while also recording the
two-step Poincare residual. A minimal period-one or period-two response
phase-locked to that input is reported. A larger minimal period, failure to
classify, or a residual cycle after 128 constant-neutral washout transitions
fails.

Gates:

- no autonomous period-2-through-32 cycle;
- every trajectory finite and bounded in `[0, 1]`;
- neutral has exactly one attractor at baseline within `1e-6`;
- one attractor is eligible for `PASS`, exactly two set `PHASE_PORTRAIT=HELD`,
  and more than two set it to `FAIL`;
- moderate scenarios must not end with both vigilance and load `>=0.8`;
- adjacent `1/256` q bins must not change any 256-tick terminal coordinate by
  more than `0.10`; this scan uses the factor contexts and initial states above,
  covers every adjacent interval, and a larger jump is a failure;
- exact-zero/exact-one occupancy is reported per coordinate and scenario;
- any exact kappa `1`, reserve `0`, or load `1` after tick 0 of the baseline-state
  moderate controlled, moderate uncontrolled, norm-`0.75` repair, or
  affiliation-`+/-0.5` saturation trajectories sets
  `SATURATION_CLIPPING=FAIL`; these dedicated trajectories run for 256 ticks,
  and extreme-scenario saturation and corner-initial occupancy are reported but
  do not trigger this row;
- independently recomputed pre-clip and post-clip transitions must reconcile to
  `1e-12`, or `SATURATION_CLIPPING=FAIL`.

The two-attractor allowance is a descriptive ceiling, not endorsement. It
prevents one known regime from changing the protocol while still withholding a
freeze until the owner decides whether that hysteresis is intended.

## Frozen Recovery And Accumulation Probes

Recovery tick 0 is the declared initial state; gates at tick N are evaluated
after exactly N transitions. Starts include every state in `{0, 0.5, 1}^5`, every discovered
stationary attractor, and the endpoint after 32 extreme-unresolved ticks from
baseline. Recovery uses 64 neutral ticks. A second stress-endpoint arm appraises
one explicit `threat_cleared` event at its first recovery tick and neutral input
afterward. That fixture has magnitude `1`, confidence `1`, attribution
`environment`, one synthetic-fixture source at sequence 0, and no semantic refs.

Required recovery:

- vigilance `<=1e-6`, load `<=0.01`, and reserve `>=0.99` by tick 32;
- every kappa coordinate and load `<=0.001`, with reserve `>=0.999`, by tick 40;
- no kappa/load rebound above its crossed upper threshold and no reserve rebound
  below its crossed lower threshold by more than `1e-9`, checked through tick 64;
- the explicit-clear arm may be numerically identical. Its first-passage time may
  not be slower for any threshold, and at each tick its kappa/load may not exceed
  neutral while its reserve may not be lower, all within `1e-12`.

The accumulation audit uses direct controller-boundary vectors so event
admission cannot be confused with controller dynamics. Its active vector is
`AppraisalVector(norm_violation=0.75, controllability=0.75)` with every other
field zero. In the occurrence arm it is applied at tick 1 and followed by 63
neutral ticks; it must not accumulate and must recover all kappa axes to
`<=0.001` by tick 40. In the unresolved arm the same active vector is applied on
each of 64 ticks; affiliation and agency must be bounded, nondecreasing until
convergence, and remain `<0.95` without exact saturation. Switching that arm to
neutral must recover all kappa axes to `<=0.001` within 40 more ticks. Failure of
any rule sets `ACCUMULATION=FAIL`; production event attribution,
continuation/replay authority, and exactly-once custody remain held on `#171`.

## Frozen Leakage Challenge

The audit creates 16 balanced synthetic identities for each semantic-ref kind
`person`, `topic`, and `episode`. It uses 512 matched 32-tick semantic trace
templates. Every template is repeated under all 16 labels in a different
source/ref namespace. Train and evaluation groups use different templates and
different event/source/ref strings while holding the allowed fact pattern fixed
across labels within each group. The fixed group split is 320/96/96 templates.
The first group is training, the second validation, and the third the sole
authoritative test group; validation never selects or changes anything.

For template index `i` and zero-based tick `t`, let `d` be the raw 32 bytes from
SHA-256 of ASCII `protocol_id + ':' + i + ':' + t`. Each tick has exactly one
event. Its kind is `sorted(WORLD_EVENT_KINDS)[d[0] % 10]`, attribution is
`sorted(EVENT_ATTRIBUTIONS)[d[1] % 4]`, magnitude is `d[2]/256`, and confidence
is `d[3]/256`. Event positions are `(t, 0)`. Event, source, and semantic-ref IDs
contain the split, template, tick, ref kind, and label so namespaces are
disjoint, but none of those strings enters numeric selection. Each event carries
exactly one ref of the kind under test. Source sequence is `t`; source SHA-256 is
the lowercase hex digest of ASCII
`protocol_id + ':source:' + split + ':' + i + ':' + t + ':' + label`.

Features are measured separately from:

1. the flattened 32-tick q trajectory;
2. the flattened kappa trajectory plus tick-1, tick-8, and tick-32 endpoints;
3. the flattened reserve/load trajectory plus the same endpoints;
4. the concatenated numeric trajectory.

Deterministic nearest-centroid and diagonal-Gaussian classifiers are trained on
the training group. Nearest-centroid uses squared Euclidean distance. The
diagonal-Gaussian score is the equal-prior sum of
`-0.5*(log(variance) + squared_error/variance)` with a per-class variance floor
of `1e-12`. No hyperparameter or classifier is selected from validation or test
results; every classifier/view result on the authoritative test group is gated.
Ties resolve to the lexicographically first class. Features are standardized
with training-only means and population standard deviations; zero-variance
coordinates become zero. Balanced accuracy is the arithmetic mean of the 16
per-class recalls. With 16 balanced classes, chance is `0.0625`; the gate is
held-out balanced accuracy `<=0.0825` for every semantic-ref kind, feature
surface, and classifier. Matched templates must also be bit-identical across
identities.

The positive canary is a separate fixed numeric surface: every tick is one
`affiliation_gain` event with attribution `environment`, confidence `1`, and
magnitude `0.5 + (class_index - 7.5) * 1e-6`. Only event/source/ref namespaces
vary by split, template, tick, ref kind, and label. Thus there is no independent
numeric template variance to hide the registered code. At least one
raw/unfiltered classifier must reach `0.90`; after the predeclared `1/256`
filter every classifier must return to `<=0.0825`. Failure of either sensitivity
or suppression criterion sets `CONDITIONAL_LEAKAGE=FAIL` because the evaluator
is invalid; it cannot produce a clearance.

This is conditional leakage only. It does not clear a producer that encodes an
identity into registered event kinds, magnitude, confidence, timing, or rate.
That authority/rate problem remains with `#171` and the missing production
quantization contract.

## Decision Rule

The report has independent gates:

- `EVENT_METAMORPHICS`
- `FACTOR_RESPONSES`
- `PHASE_PORTRAIT`
- `RECOVERY`
- `ACCUMULATION`
- `CONDITIONAL_LEAKAGE`
- `SATURATION_CLIPPING`
- `RELIEF_SEMANTICS`
- `NUMERIC_RATE_POLICY`
- `REPLAY_AUTHORITY`

Each is `PASS`, `FAIL`, or `HELD`. Overall disposition is:

- `PASS` only if every gate is `PASS`;
- `HOLD` if no gate fails but at least one is held;
- `FAIL` if any gate fails.

`RELIEF_SEMANTICS` and `NUMERIC_RATE_POLICY` are `HELD` for the current v1
boundary by construction. `REPLAY_AUTHORITY` is `HELD` if the exact in-batch
duplicate probes refuse, and `FAIL` otherwise. The main audit can therefore
return at best `HOLD`; local numeric success cannot be promoted into composition
clearance.

No coefficient, field, event kind, quantum, threshold, or scenario may be changed
after seeing the audit in order to convert the same report. A repair requires a
new versioned spec and a fresh report while preserving this result.

## Expected Custody

The runner path is
`spikes/run_world_model_phase3c_controller_audit.py`. It writes exactly one new
bundle at `results/world_model_phase3/controller_audit_v1/`, containing
`report.json`, `report.json.sha256`, and `REPORT.md`; any pre-existing path is a
hard refusal.

The runner must emit canonical strict JSON with:

- protocol ID and exact source blobs;
- Python/platform identity;
- every frozen constant above;
- full raw records for the factor, event-metamorphic, recovery, accumulation,
  leakage, and discovered-attractor probes;
- for each large Cartesian sweep, the exact row count, extrema, occupancy and
  verdict counts, the lexicographically first 16 witnesses for each distinct
  failure reason, and a streaming SHA-256 over every canonical per-cell record;
- gate reasons and overall disposition;
- a SHA-256 over the report content excluding only the digest field.

`REPORT.md` is a deterministic rendering of `report.json`; it is not a second
source of numeric truth. Publication is no-overwrite. The result bundle and
review may be committed, but no live state, Qdrant point, model artifact, memory
row, or controller persistence surface is written by the audit.
