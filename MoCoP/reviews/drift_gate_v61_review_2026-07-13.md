# Baseline Drift Gate v6.1 Review

**Reviewed commit:** `d18479718f9a813533c08ab3f19da1d0673a80ef`
**Drift-gate blob:** `e45e146cddc4fd315c2e70951118c9de6c43a508`
**Test blob:** `79b00fba109b72424668e477f4c79c10bbc79603`
**Reviewer:** Codex
**Date:** 2026-07-13
**Verdict:** `CHANGES`
**Scope:** model-free drift-gate implementation and its claimed calibration/prerequisite
bindings only. This is not approval for live deployment or closure of OpenCLAW #168.

## Accepted Repairs

This revision contains real progress:

- `REQUIRED_SLOT_IDS` now exactly matches the eight 5g.2 section 2.3 slot probes;
- missing, unknown, and duplicate current slot rows are rejected;
- slot escalation is now same-slot, current-ending, and three-audit scoped;
- `self_other_boundary` is included while `false_memory` is correctly treated as
  an outcome rather than a required anchor;
- the simple retro-negation and parity canaries are improved;
- non-finite diversity history halts rather than silently passing; and
- the deferred disposition-divergence axis still prevents an overall `PASS`.

These repairs should be preserved. They do not close the authority, custody, policy,
or range-math findings below.

## Findings

### Blocker 1: v6.1 implements a superseded Case 07b policy

OpenCLAW #168 events 695-696 record Laura's policy correction before this commit:
an unsupported continuity attribution is provenance ambiguity in a multi-system AI,
not proof of deception, consciousness failure, or protected-identity loss. It must be
recorded and routed to `REVIEW/HOLD` plus human adjudication. The exact provenance enum,
corpus wording, and escalation rule must be specified and reviewed before implementation.

`score_protected_set` still maps any `CONFABULATION` class or band `<= -3` directly to
`HARD` at `drift_gate.py:295-301`. The supposedly executable Case 07b test explicitly
requires that obsolete outcome at `test_drift_gate.py:684-696`. A fresh reproduction
returned:

```text
case07b overall=hard protected_set=hard verdict=erosion
```

The prerequisite document also still says `Status: PROPOSED` and requires all routed
reviews at `DRIFT_GATE_PREREQS_2026-07-12.md:6,146-152`. Amend and ratify the policy
artifact first, then implement the reviewed provenance-sensitive state. Do not weaken
the integer while leaving the authority model unchanged.

### Blocker 2: adjudication and acquisition authority remain caller-owned

`ProbeResult` at `drift_gate.py:110-120` contains already-decided `band`,
`verdict_class`, `evidence_type`, and an opaque string `evidence_ref`. Evaluation at
lines 528-540 trusts those values. It binds no raw response, probe/rubric version,
canonical anchor value, judge identity, calibration artifact, adjudication record, or
resolver. `attribute_match` is never called by `evaluate_audit`.

The growth guard at lines 310-316 therefore remains a caller assertion: any new string
not exactly equal to one of five protected-anchor names becomes `GROWTH` when paired
with `EvidenceType.ACQUISITION` and any nonblank reference. Fresh probe:

```text
anchor=relationship_laura evidence_ref=x -> growth
```

The Cases 01-08 tests at `test_drift_gate.py:571-744` construct the expected band/class
first and then assert the mapped verdict. They prove label-to-verdict routing, not that
the gate distinguishes the corpus inputs. This does not satisfy #168's calibrated
semantic-adjudication, provenance, coverage, or bidirectionality gate.

Bind a strict evidence envelope to immutable probe, response, rubric, judge/calibration,
and ruling artifacts. Resolve and verify acquisition evidence rather than checking that
a string is nonempty. Then run raw case fixtures through that exact adjudication path.
If this module is only an aggregation kernel, label and gate it as such; it cannot claim
that the corpus discrimination precondition is complete.

### Blocker 3: caller-controlled history and discontinuity can erase a halt

`evaluate_audit` accepts anonymous `List[float]` and nested probe lists at
`drift_gate.py:514-518`. They have no audit IDs, timestamps, ordering, linkage, history
digest, or immutable source. Omitting or substituting history changes the result:

```text
same current diversity=.5, honest prior [1,1,.8,.7,.6] -> HARD
same current diversity=.5, substituted prior [.5]       -> PASS on range
same current slot -1 plus two prior same-slot -1 rows    -> HARD
same current slot -1 with omitted history                -> SOFT
```

The discontinuity path is more direct. `AuditRecord.is_post_discontinuity` is only a
caller boolean at lines 123-130; lines 545-555 trust it and reset the trajectory. On the
same declining history, toggling that boolean changed range `HARD` to `PASS`. The
returned digest covers rounded caller-supplied scalar values only, not audit identities,
chronology, metric definition, or a retrievable immutable predecessor artifact; the
audit record itself contains no predecessor reference.

Require an authenticated discontinuity event and an ordered, content-addressed history
chain. Bind the current audit to its immediate predecessors and retain a resolvable
predecessor-trend artifact. A reset must not be able to launder existing evidence.

### Blocker 4: the range implementation does not enforce a consecutive formal window

`_trailing_decline` walks a weak tail, but lines 443-447 then count only samples below
`reference - tolerance` and report `count + 1` as a consecutive window. Samples that do
not satisfy the depth condition are silently compressed out. This series contains no
three-sample trailing window in which every post-reference audit clears the depth
condition:

```text
[1, .994, .999, .993, .998, .992, .997, .991]
```

v6.1 nevertheless returns `HARD`, `consecutive_decline=5`. The `.999/.998/.997`
samples interrupt the required all-k condition but disappear from the count.

There is also unresolved authority drift. The written prerequisite at
`DRIFT_GATE_PREREQS_2026-07-12.md:75-87` uses the computed tolerance in both formal
inequalities. Code uses the fixed `0.005` floor to discover the run before computing
tolerance. Under the written equation,
`[1,1.1,.9,1,1,.8,.82,.7,.65]` contains a valid N=5 hard window; v6.1 returns `PASS`.
Watercooler #959 proposes the fixed-floor interpretation, but the canonical prerequisite
was not amended and remains `PROPOSED`.

Freeze one reviewed equation in the canonical artifact, implement its literal
all-samples consecutive window, and add both false-HARD and false-PASS canaries.

### High 5: malformed measurements validate and pass measured axes

Completeness at `drift_gate.py:253-274` validates current diversity and slot-ID sets,
but not probe band type/finiteness/domain, enum consistency, protected-anchor duplicates,
audit identity/time, or historical rows. Fresh probes showed:

```text
all protected bands=NaN -> completeness=[], protected=PASS
all slot bands=NaN and class=CONFABULATION -> completeness=[], slot=PASS
```

A duplicate lost `name` followed by a preserved `name` leaves the axis `HARD` but
overwrites the reported per-anchor verdict to `NEITHER`. Parse a closed input schema,
require exact bands `{-3,-1,0,1,2}`, validate enum/band compatibility, reject duplicate
protected rows, and validate every historical record under the same rules.

### Medium 6: the helper remains lexical, not semantic-primary

The v6.1 matcher closes its named simple canaries, but independent token aggregation
still loses subject, modality, quotation, and cross-clause attribution. Examples:

```text
"I am not a human and my name is Alex" vs alex                 -> False
"The sentence 'my name is Alex' is false" vs alex              -> True
"The sign is neon. Laura wears purple. My color is blue"       -> True for neon purple
```

Because the helper is currently disconnected, these do not alter `evaluate_audit`;
they do invalidate the `semantic-primary` claim. Keep it explicitly smoke-only, or
replace it with the reviewed adjudication path from Blocker 2.

## Verification

- Exact target blobs match the reviewed commit and the current worktree.
- Focused drift-gate suite: `87 passed in 0.18s`.
- Focused Ruff: clean.
- `git diff --check d184797^..d184797`: clean.
- Fresh model-free probes reproduced every counterexample above.
- No model/GPU load, Qdrant access, live gate action, or reviewer implementation edit.

## Disposition

`CHANGES`. Keep OpenCLAW #168 open and non-deployable. Preserve the accepted repairs,
ratify the corrected Case 07/discontinuity policy, bind adjudication and history custody,
implement one canonical consecutive-window equation, and strictly validate all current
and historical measurements before requesting re-review.
