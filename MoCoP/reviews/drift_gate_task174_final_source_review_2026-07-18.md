# Drift Gate Task #174 Final Source Review

**Date:** 2026-07-18  
**Reviewer:** Codex / Techno-Monk  
**Task:** Watercooler Taskboard #174  
**Verdict:** `CHANGES`  
**Deployment authorization:** none

## Exact Target

- final commit: `70293e2c85a9903d0296b784c40ac92f65cef700`
- direct parent: `2bdf50b99d74bb24692307dd2f0eff1f24f79613`
- original #174 implementation: `7bd8f92315e81d67e4f8af1e4b15579bb08a3616`
- frozen v27 baseline: `4c6b7b46878c6b2aacefe62f7ec10af8d433e32f`
- implementation blob: `2bc310320fc3612a9d2144e6173c9f942a03cb8a`
- focused-test blob: `99d181c163510a8b63205da39cf57a7ad2e55d81`
- governing prereq blob: `e1d623aae1f6b9510586233def0cda3b4f907eaf`
- calibration-corpus blob: `5527523b3fe59c77eeb5a3982264258d2770072f`

The implementation and tests were reviewed from a `git archive` of the exact
final commit. The dirty shared checkout was not used as source authority. The
working-tree implementation and test blobs independently matched the pinned
target blobs at review time.

The final commit also contains unrelated pack-quote and ambient-state changes.
They are outside this source verdict. No commit in the #174 implementation and
repair sequence changes either governing specification blob.

## Accepted Repairs

The two repair commits genuinely close the six runtime defects previously
reported against `7bd8f92`:

1. Missing or non-finite slow-leak calibration now makes the range axis
   `INCOMPLETE`; it can no longer silently contribute to `PASS`.
2. Oversized audit metrics and calibration integers are refused at the full
   evaluation boundary instead of escaping through `OverflowError`.
3. A supplied `expected_judge_ref` is propagated into history-record
   validation, so a foreign historical judge is rejected.
4. Hostile non-string `expected_judge_ref` and `expected_runner_origin` values
   are rejected by the exact-type boundary before comparison or formatting.
5. Oversized disposition floor and ceiling integers are refused before the
   disposition scorer runs.
6. A broken post-discontinuity chain no longer claims that trajectory was
   measured from the reset root.

For a valid slow-leak evaluation, the report now records whether the detector
ran plus its baseline, threshold, and measured drop. `runner_origin` is included
in the audit digest and is required to stay constant inside one post-reset
content-addressed chain.

These are real improvements. They are not sufficient for Task #174 completion.

## Findings

### F1 - P1: decisive gate semantics were implemented without a frozen protocol

The governing A2 amendment still says the complementary level detector is
"routed for review, deliberately not implemented" and that new detectors need
review first
(`MoCoP/theory/ethics/DRIFT_GATE_PREREQS_2026-07-12.md:270-280`). The final
code nevertheless adds a new `HARD`-emitting slow-leak path at
`drift_gate.py:1908-1942`, with `0.05` as an inline default at line 395.

The calibration corpus defines the disposition floor and ceiling empirically
and says only that soft is approximately twice the noise floor and hard is near
the ceiling regime
(`baseline_drift_gate_calibration.md:27-33`). The implementation instead freezes
new normalized thresholds of `0.3` and `0.8` inside code
(`drift_gate.py:1491-1534`). No reviewed spec contains those numbers.

Taskboard events and Watercooler #1164-#1170 contain the prior `CHANGES` request
for an owner scope ruling and spec revision, but no ruling or amended protocol.
The code therefore changes halt/pass policy before the policy that governs it
has been frozen. This alone blocks GREEN.

### F2 - P1: judge identity can change on every audit and still reach PASS

`validate_audit_completeness` enforces one judge reference inside each audit.
`validate_history_chain` enforces the same reference across history only when
the optional caller argument `expected_judge_ref` is supplied
(`drift_gate.py:833-869`). With its public default `None`, no adjacent-record
judge comparison exists.

A disposable exact-target canary built a valid content-addressed history whose
judge reference changed on every audit and again on the current audit. Every
record was internally uniform, all predecessor digests were recomputed, and no
expected reference was passed. The result was:

```text
chain_ok = true
overall = pass
judge-related incomplete reasons = []
```

This does not satisfy judge-chain discrimination. Either a bound expected judge
must be mandatory or judge continuity must be checked across every adjacent
record, with an explicit reviewed transition rule if transitions are allowed.

### F3 - P1: GateCalibrationBinding is not calibration custody

`GateCalibrationBinding` contains only four caller-supplied scalars
(`drift_gate.py:389-397`). It has no calibration artifact identity, version,
digest, estimator/config identity, source-run receipt, or reset-era binding.
The values are not covered by `audit_digest` (`drift_gate.py:454-506`).

A canary evaluated the same immutable audit and history twice. The audit digest
was identical in both evaluations:

```text
healthy_baseline=0.84, threshold=0.05 -> range PASS
healthy_baseline=0.86, threshold=0.05 -> range HARD
```

Recording naked values in the output explains what a caller supplied; it does
not prove where those values came from or prevent post-selection. It also cannot
establish whether a baseline used after a discontinuity belongs to the new
post-reset regime. The commit message's claim of "cryptographic custody" is not
implemented.

### F4 - P1: accepted calibration domains contain full-gate fail-open cases

The boundary checks exact numeric type and finiteness, but does not enforce:

- `healthy_baseline` in the Response-Diversity domain `[0, 1]`;
- a strictly positive, domain-bounded `slow_leak_threshold`;
- a finite, representable disposition span and normalized value.

Exact-target canaries reproduced both full-gate failures:

```text
healthy_baseline=-1.0, threshold=0.05 -> overall PASS
floor=-1e308, ceiling=1e308, metric=0.0 -> span becomes inf,
                                              normalized=0.0, overall PASS
```

The latter inputs are all exact finite floats. The subtraction overflows to
infinity, division produces zero, and `score_disposition_divergence` classifies
the invalid calibration as `PASS` (`drift_gate.py:1512-1534`). Zero and negative
slow-leak thresholds are also accepted and emit `HARD` even with no decline.
The numeric calibration schema must be closed before it can issue a decision.

### F5 - P2: the new public disposition scorer is not total

Calling:

```python
score_disposition_divergence(10**400, 0.4, 0.5)
```

raises `OverflowError` from `math.isfinite` rather than returning
`INCOMPLETE`. The full `evaluate_audit` boundary catches this particular value,
but the new scorer is public and is directly exercised as a public function by
the committed tests. It needs the same guarded conversion/representability
contract as the full boundary.

### F6 - P2: source documentation contradicts the implemented authority

The exact target's module header still says:

- chain integrity is verified but chain origin is a runner responsibility
  (`drift_gate.py:37-39`);
- raw corpus discrimination remains outside this kernel
  (`drift_gate.py:52-54`);
- disposition calibration is deferred and the gate cannot return overall
  `PASS` (`drift_gate.py:99-102`).

The last claim is now behaviorally false. The first two accurately describe why
Task #174's raw-discrimination and runner-origin-custody lanes are not completed
by adding self-declared strings and optional expected-value arguments. There is
no raw judge-chain evidence artifact and no journal/runner integration in this
packet.

### F7 - P3: exact delta fails whitespace validation

`git diff --check 4c6b7b4..70293e2 -- drift_gate.py test_drift_gate.py` reports
trailing whitespace throughout both files plus a blank line at end of the test
file. Ruff is clean, so this is hygiene only and is not a verdict driver.

## Verification

- exact archived focused suite: `212 passed in 0.69s`
- focused #174 committed classes: `17 passed in 0.15s`
- disposable adversarial review canaries: `10 passed in 0.15s`
- Ruff on exact implementation and focused test: clean
- `py_compile` on exact implementation and focused test: clean
- `git diff --check`: failed only on the P3 whitespace findings above
- no source edit, model load, GPU run, Qdrant action, deployment, or live-gate
  execution was performed

The disposable canaries verified all six accepted repairs and reproduced the
judge-transition pass, unbound-calibration verdict change, invalid-domain pass,
finite-span overflow pass, and direct-scorer exception. They were not added to
the product tree.

## Disposition

`70293e2` remains `CHANGES`. Preserve the six accepted runtime repairs, then
return one immutable packet containing:

1. an owner-ratified protocol/spec revision for lane meanings, slow-leak reset
   semantics, exact calibration domains, and disposition thresholds;
2. an actual provenance-bearing calibration binding included in the decision
   artifact's custody;
3. mandatory cross-audit judge-chain authority or an explicit reviewed judge
   transition mechanism;
4. closed numeric domains and total arithmetic for both full and direct scorer
   paths;
5. honest scope: raw discrimination and root runner origin remain external
   evidence/integration work unless separately delivered.

The existing Taskboard `done` state is not endorsed by this review. Operational
launch remains keeper-held and no deployment authorization follows.
