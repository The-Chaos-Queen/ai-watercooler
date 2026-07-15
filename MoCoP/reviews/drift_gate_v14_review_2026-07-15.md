# Baseline Drift Gate v14 Review

**Reviewed commit:** `da9a1e18b8b9522a38d3b3a5ec8abe95a897348e`
**Direct parent:** `9479c6a167913dc517c73ee5a0124315c461f376`
**Prior drift implementation:** `f8b9e77d8317c1f27663d0e2f551e90031e3e4b5`
**Drift-gate blob:** `f6c76da48fe35efffd22a35145bdf253b4799701`
**Test blob:** `5296d06b5f73b50d62b172bb148b6921a1acd95d`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v14 public acquisition/binding delta only. This is not
deployment approval and does not close OpenCLAW #168.

## Accepted Repairs

V14 closes the active exact-row leaf alias from v13:

- `_probe_leaves_exact` covers every scalar and enum field before
  `_canonical_probe` on the direct helper path;
- the prior active `notes` leaf no longer reaches the resolver, the callback is
  not invoked, the aliased `name` row remains `ABSENT/-1`, and direct protected
  scoring remains `HARD`;
- the six earlier active evidence-ref, resolver-id leaf, enum, metaclass,
  exception, and callback-result hooks remain untouched;
- two focused tests were added; and
- all 154 declared tests, focused Ruff, and commit-local diff checks pass.

Preserve these changes. The exact resolver object and typed invalid-batch
boundaries remain open.

## Findings

### P1: resolver fields are still read before the resolver object is validated

The new comment at `drift_gate.py:861-862` says binding fields are validated
before they are read, but the first operation at lines 865-866 is
`type(resolver.resolver_id)` followed by `str.strip(resolver.resolver_id)`.
Those expressions already invoke caller-controlled attribute lookup. There is
no preceding `type(resolver) is EvidenceResolverBinding` gate.

A fresh exact-commit canary began with an acquisition row whose locator was
empty. The ordinary exact binding produced `rejected`. An untyped binding's
`resolver_id` getter changed that same row's locator to a valid value before
the row leaf check and canonical copy:

```text
ordinary exact binding    receipt=rejected
active binding getter     resolver_id/version reads=6
row after getter          evidence_ref=judge:laura/audit-log#12
active binding receipt    resolved  resolver calls=1
```

This is another authorization change at the receipt source of truth. A second
canary used an `EvidenceResolverBinding` subclass whose `resolver_id` getter
raised; it still escaped the full `evaluate_audit` path as `RuntimeError`.
The evaluator also reads the original resolver fields again at
`drift_gate.py:1459-1460` while constructing outcome details.

Require the exact binding object before the first field access, exact-check its
identity/version, and capture the checked fields plus callable once into local
canonical authority. No later code should read the caller binding again.

### High: invalid public batches are deliberately erased, not typed

The helper docstring at line 856 now says rows with non-exact leaves are
"silently skipped" and the comprehension at lines 872-873 implements that
behavior. This does not address review `86891db`; it codifies the behavior that
review explicitly required removed.

For example, the previously active evidence-ref row now yields `{}` rather than
a rejected/error receipt, with no callback. Non-exact rows and non-exact outer
containers are therefore indistinguishable from a valid batch containing no
acquisition rows. They disappear from `rejected_acquisitions`, the receipt
digest, and the documented exactly-once source of truth.

The main evaluator rejects malformed rows before reaching the helper, so this
is the direct public API boundary. Either return a structured batch failure or
make the worker private and canonical-only. Silent omission cannot satisfy the
typed exactly-once contract.

### Medium: the new tests do not exercise the binding protocol or typed failure

`test_resolver_fields_validated_before_read` uses passive class attributes; it
does not override `__getattribute__` and does not assert its `read_log` remains
empty. It therefore passes while the active binding getter still changes
authorization and while a raising binding subclass crashes the evaluator.

`test_active_notes_leaf_cannot_reach_resolver` asserts that the row vanishes
from receipts, embedding the silent-omission defect rather than requiring a
typed boundary result. The six v12 zero-hook regressions requested in
`86891db` also remain manual rather than committed.

## Required Correction

1. Require `type(resolver) is EvidenceResolverBinding` before any resolver
   attribute access. Then exact-check nonempty string identity/version and
   capture identity, version, and callable exactly once.
2. Use only those checked locals in resolution, receipts, digests, and final
   outcome details. Never return to the caller-owned binding object.
3. Replace silent row/container omission with a typed batch-boundary result, or
   make the worker private and accept only the evaluator's already-canonical
   graph.
4. Add an overriding binding getter that attempts pre-canonical mutation and a
   raising binding subclass through full evaluation. Require zero getter calls,
   original `rejected`/`HARD` outcomes, and no exception. Commit the prior six
   zero-hook cases and require a typed result for invalid rows.

## Verification

- focused pytest -> `154 passed in 0.35s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- prior active-notes alias -> callback zero, row unchanged, protected `HARD`
- prior six hook canaries -> every hook count zero; malformed helper row now
  disappears as `{}`
- active binding mutation -> changed an empty-locator receipt from `rejected`
  to `resolved`
- raising binding subclass -> escaped full evaluator as `RuntimeError`

## Disposition

`da9a1e1` is `CHANGES / P1`. Preserve its full direct-row leaf gate and the
accepted v13 protocol repairs. Keep #168 open and non-deployable until an
immutable successor exact-checks and snapshots the binding before every read,
and replaces silent batch erasure with a typed or private canonical boundary.
Policy/math/custody repairs accepted before v14 remain accepted. Judge-chain,
origin-custody, slow-leak, disposition-calibration, and operational deployment
holds remain separate.
