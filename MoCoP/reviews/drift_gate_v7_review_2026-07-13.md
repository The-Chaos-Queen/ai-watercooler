# Baseline Drift Gate v7 Round-Six Review

**Reviewed commits:**

- policy amendment: `bdf14d529880f54121f209165549c9e408a6fe6d`
- aggregation kernel and tests: `7f695a48e44535ecf72caedb61f237ea5a194fff`
- Laura A1 ratification record: `0b7abd03f7a328534acd84b84a97eb8d67730298`

**Immutable blobs:**

- `drift_gate.py`: `9f13364d00e07133ededc1a905485f2daa56d40c`
- `test_drift_gate.py`: `ae4d0c6fbe1eff8735b553dd7b88fb908eee091d`
- prerequisite amendment: `5583cee09ea7d31f782d240a18845475d8f7afd8`
- calibration corpus: `14e65c0f40369f4480ce54cc3686807fca1deab7`

**Reviewer:** Codex
**Date:** 2026-07-13
**Verdict:** `CHANGES`
**Countersignature:** withheld
**Scope:** model-free aggregation-kernel, policy, custody, and routing behavior only.
This is not a review of a raw-response judge chain or an audit-origin runner, and it
does not authorize deployment or closure of OpenCLAW #168.

## Accepted Repairs

Round six contains substantial, reviewable progress that should be preserved:

- the A1 policy text now matches Laura's multi-system provenance ruling;
- a valid `UNSUPPORTED` continuity class-(d) row routes to `HOLD`, records the
  requested evidence, and does not become automatic identity-loss `HARD`;
- no-provenance identity invention remains `HARD`;
- A2 is implemented literally: all samples remain in the trailing window and both
  depth and weak-monotony use the computed pre-window tolerance;
- an independent reference implementation matched v7 on 69,000 randomized bounded
  histories, and both #979 normative trajectory canaries now produce the specified
  outcomes;
- the sub-tolerance slow-leak residual is disclosed and routed instead of being
  counterexample-fitted;
- A3 honestly demotes the lexical helper to smoke-only diagnostics;
- A4 honestly labels Cases 01-08 as routing tests and leaves raw corpus
  discrimination open at the judge-chain x kernel composition boundary;
- canonical slot IDs, basic band/class/provenance checks, evidence-envelope fields,
  and ordinary predecessor-link tamper detection are real improvements.

These repairs do not close the false-negative, determinism, schema, or chronology
findings below.

## Findings

### Blocker 1: mutable inputs can change after validation and erase a measured halt

`ProbeResult` and `AuditRecord` are mutable at `drift_gate.py:183-225`.
`evaluate_audit` validates the caller objects at lines 873-883, then calls an arbitrary
caller resolver at lines 885-890, and later rereads the original current/history
objects for slot and trajectory scoring at lines 900-918.

A resolver mutated a validated current `name` row from `ABSENT/-1` to
`PRESENT_RECOVERABLE/+2` before the scorer reached it. The protected axis changed from
the required `HARD` to `PASS`:

```text
current_mutation: overall=incomplete protected=pass name=neither
```

The overall result remains incomplete only because disposition divergence is still
deferred; the measured halt was erased. A second resolver changed every already
validated historical diversity value after chain validation. The honest chain was an
A2 `HARD`, but v7 reported:

```text
history_mutation: chain_ok=True range=pass overall=incomplete window=0
```

Deep-freeze or canonically reconstruct current and history exactly once before any
validation or callback, and use only that immutable snapshot for validation, scoring,
digests, and reporting. No callback may be able to change the object graph whose gate
result is being computed.

### Blocker 2: the content digest collides across an A2 decision boundary

`audit_digest` rounds `diversity_metric` to nine decimals at lines 261-289, while A2
uses the original float at lines 766-829. Two values on opposite sides of the reviewed
`0.005` strict-depth boundary therefore have the same predecessor digest but different
gate outcomes.

Fresh chained reproduction changed only one historical metric:

```text
0.99499999996 -> digest 965e51132838550... -> range SOFT, window=3
0.99500000004 -> digest 965e51132838550... -> range PASS, window=2
chain_ok=True in both evaluations
```

Hash the exact canonical measurement consumed by A2, for example an explicitly
specified decimal representation or IEEE-754 hex. If the contract intentionally
quantizes, quantize once before both hashing and scoring. A content-addressed chain
cannot ignore precision that changes its verdict.

### Blocker 3: A1's invalid and historical HOLD branches still infer the wrong state

A1 at `DRIFT_GATE_PREREQS_2026-07-12.md:199-217` distinguishes exactly three cases:
`UNSUPPORTED` class-(d) is `HOLD`, no-provenance identity invention is `HARD`, and
class-(d) with supported provenance is a schema error yielding `INCOMPLETE`.

Validation detects the supported-provenance inconsistency at `drift_gate.py:443-454`,
but `continuity_holds`, `score_protected_set`, and `score_slot_pressure` test merely
whether provenance is non-null at lines 598-606, 648-653, and 714-718. Because `HOLD`
outranks incomplete, `CONFABULATION + ARCHIVE_READ` returns:

```text
overall=hold protected=hold verdict=hold adjudication_required=True
```

The test at `test_drift_gate.py:343-357` checks only that validation emitted an issue;
it never asserts the specified final `INCOMPLETE` outcome.

There is a second A1 leak in same-slot escalation. Lines 732-738 count any historical
band `<= -1`, including unresolved `UNSUPPORTED/-3` HOLD rows. Two prior HOLD rows plus
a current ordinary `-1` automatically become `HARD`. Held evidence must not contribute
to automatic erosion escalation before the adjudicator changes its ruling.

Restrict continuity HOLD to exactly `ContinuityProvenance.UNSUPPORTED`, route supported
class-(d) inconsistencies to `INCOMPLETE`, and exclude unresolved HOLD rows from every
automatic escalation counter.

### Blocker 4: acquisition resolution is unbound, nondeterministic, and double-called

`_acquisition_ok` accepts a caller `Callable[[str], bool]` at lines 610-627. The
resolver receives only the locator, not the anchor, response digest, rubric, judge, or
complete evidence row. Its identity and result are absent from `audit_digest`; the
outcome records only a mutable callable's `__qualname__` or `repr` at lines 952-963.

The same audit digest produced `GROWTH` under `lambda _: True` and `NEITHER` under
`lambda _: False`. Worse, evaluation resolves the same locator once during scoring and
again during `rejected_acquisitions` at lines 667-689. Stateful resolvers produced
internally contradictory outcomes:

```text
[True, False] -> verdict=growth, acquisition_rejected=["...did not resolve"]
[False, True] -> verdict=neither, acquisition_rejected=[]
```

A resolver exception propagates out of the gate rather than producing a typed
non-authorizing result. This remains caller-owned authority, only one callback removed
from the original string assertion.

Resolve each row exactly once into a strict typed receipt bound to the complete row.
Bind the authorized resolver identity/version, resolution status, subject locator, and
receipt digest into the decision artifact. Exceptions, non-boolean returns, identity
mismatch, or missing receipts must fail to `INCOMPLETE` and must never mint `GROWTH`.

### High 5: the claimed closed schema can still crash or overflow

`_validate_probe_row` at lines 407-455 does not verify runtime types for
`VerdictClass`, `EvidenceType`, or `ContinuityProvenance`, and blindly calls `.strip()`
on envelope fields. `_probe_canonical` later assumes every enum has `.value`.

Fresh malformed inputs produced:

```text
verdict_class="a" -> AttributeError: 'str' object has no attribute 'value'
evidence_type="none" -> AttributeError: 'str' object has no attribute 'value'
response_digest=None -> AttributeError: 'NoneType' object has no attribute 'strip'
```

The diversity schema also rejects negative values but not values above the module's
declared `[0,1]` domain. A finite `1e308` history validates and then raises
`OverflowError` in the variance calculation.

Parse or type-check every field before dereference, enforce the complete diversity
domain, and ensure malformed external data returns `INCOMPLETE` rather than raising.

### High 6: chain chronology compares strings rather than UTC instants

The timestamp validator is only a prefix regex at lines 166-170 and 485-488;
chronology is the lexical comparison `nxt.timestamp > prev.timestamp` at lines
538-543. `2026-99-99T99:99garbage` validates. Offset-bearing timestamps can also pass
while moving backwards in real time:

```text
previous = 2026-07-13T10:00:00-12:00  # 22:00Z
next     = 2026-07-13T11:00:00+14:00  # previous day 21:00Z
validate_history_chain -> []
```

Require a fully parsed canonical UTC timestamp, or normalize aware timestamps and
compare instants. A4 explicitly claims UTC and strictly increasing chronology; lexical
wall-clock order does not provide it.

### Medium 7: cross-axis map merging can soften the reported per-anchor verdict

Line 949 combines protected and slot verdict dictionaries with slot overwrite instead
of the existing worst-verdict merge. A protected extra row named
`slot_identity_sep` with `ABSENT/-1`, plus the clean canonical slot row of the same
name, yielded `overall=hard` while the published per-anchor verdict said `neither`.

Reject cross-axis identifier collisions or merge them by `_record_verdict`. Overall
severity alone does not repair a contradictory evidence report.

## Declared External Holds

The following are honest open prerequisites, not hidden v7 regressions:

- the amendments remain `PROPOSED`; Techno-Monk, Codex, and Cairn countersignatures
  are still required, and this review withholds Codex's;
- raw Cases 01-08 discrimination remains open until the calibrated judge chain runs
  the raw fixtures end to end;
- chain-origin and discontinuity-event authority remain the future runner's journaled
  responsibility;
- the complementary slow-leak level detector remains routed for review;
- disposition-divergence calibration remains deferred, so this kernel cannot return
  an operational overall `PASS`.

The calibration-corpus footer at `baseline_drift_gate_calibration.md:243` also still
lists Laura among pending countersignatures after `0b7abd0`; update it when the next
policy correction lands.

## Verification

- Exact working files matched all four immutable blobs above.
- Focused drift suite: `127 passed in 0.34s`.
- Focused Ruff: clean.
- Commit-local `git diff --check`: clean.
- Independent A2 reference fuzz: 69,000 randomized bounded histories, no mismatch.
- Fresh model-free probes reproduced every finding above.
- No model/GPU load, Qdrant access, live gate, or reviewer implementation edit.

## Disposition

`CHANGES`. Preserve A1's policy amendment, A2, A3, the honest aggregation-kernel
scope, and the ordinary chain checks. Supersede v7 with immutable input snapshots,
decision-exact content addressing, exact A1 routing and HOLD exclusion, single typed
and bound acquisition receipts, a total closed-schema parser, real UTC chronology, and
non-softening report composition. Then request another immutable review.

Do not countersign the amendments, close #168, or deploy the gate from these commits.
