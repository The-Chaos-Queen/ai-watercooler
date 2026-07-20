# World Model Phase 3a: Causal Trace Custody and Open-Set Outcomes

**Status:** implementation contract for Taskboard #170
**Date:** 2026-07-20
**Implementation:** `world_model_phase3a.py`
**Gate:** `tests/test_world_model_phase3a.py`

## 1. Scope

Phase 3a supplies a model-free evidence boundary for action-conditioned World Model
experiments. It binds the information available before an action, records the point at
which execution authority crossed to an external system, retains the authoritative
execution result and raw outcome, and closes against a frozen planned-step denominator.

It does not add or authorize a learned observer, Gemma/Mamba integration, `WorldEvent`
adapter, Qdrant access, appraisal, controller use, or autonomous runtime action.

The Phase 2 sources remain frozen:

| Source | SHA-256 |
|---|---|
| `world_model_trace.py` | `c87d94bac4df8b211d9a067e8c68ba34aabcb60f8d190a873e832d36dbdeed5d` |
| `world_model_capture.py` | `e5af1edcbb15307a79e450cb08a29e4fff2e662e9e5268d0844f3866ca3b5c65` |

Phase 3a is additive because existing Phase 2/2b evidence and Phase 3c custody records
pin those exact bytes. Phase 3a evidence must not be silently parsed as a legacy v1/v2
trace, and legacy evidence must not be promoted to Phase 3a custody.

## 2. Bounded Claim

Within the controlled writer and protected journal directory:

1. the executor callback is not invoked until a pre-action commit and execution handoff
   have both completed their publication protocol;
2. the commit binds the canonical state, complete candidate-action set, selected-action
   membership, estimator artifact and configuration, executor artifact, outcome ontology,
   and predictive distribution;
3. every authoritative executed result retains its receipt, raw observation artifact,
   source artifact, and raw outcome label before open-set classification;
4. every record has a journal-owned sequence and predecessor hash, and a terminal ledger
   accounts for every frozen planned step and every retained outcome; and
5. recovery never converts the post-handoff/pre-receipt interval into a fabricated result.

This is a procedural custody and tamper-evidence claim, not trusted time attestation,
non-repudiation, or protection against an actor who controls both the complete journal
history and every external anchor. The caller must preserve the expected manifest hash;
a published evidence packet must additionally anchor the terminal chain head.

## 3. Canonical Artifacts

Every state, action, estimator, estimator configuration, executor, receipt, observation,
outcome source, and run manifest is an inline `CanonicalArtifact` with exact fields:

```text
artifact_kind, artifact_id, schema_version, content, byte_length, sha256
```

`content` is exact JSON data, recursively restricted to standard JSON scalar, list, and
object types with finite numbers. The implementation isolates it through canonical JSON
rather than retaining a caller-owned mutable object. `byte_length` binds the canonical
content bytes; `sha256` binds kind, identity, schema, content, and length. All references
resolve inside the journal and are recomputed during verification.

Candidate actions are sorted by unique artifact ID. The commit stores the complete inline
set, its aggregate hash, selected ID, and selected artifact hash. Selection outside the
committed set refuses before any journal record or action.

## 4. Outcome Ontology

The complete versioned ontology must contain the literal, distinct `OTHER` and `UNKNOWN`
labels; aliases are not accepted in v1. A
collected prediction covers every ontology label exactly once, sums to one, and assigns
strictly positive probability to both reserved labels.

Raw outcomes are retained before classification:

| Raw result | `support_status` | Scoring label |
|---|---|---|
| Enumerated ordinary label | `in_support` | same label |
| Exact `OTHER` | `declared_other` | `OTHER` |
| Exact `UNKNOWN` | `unknown` | `UNKNOWN` |
| Any novel label | `out_of_support` | `OTHER` |

The frozen policy is `map-out-of-support-to-other-v1`. It keeps scoring finite without
discarding novelty: both the novel raw label and its observation/source artifacts remain
in the receipt, while the mapped row remains in the denominator. A future scoring policy
requires a new ontology/policy version and preregistration; it cannot reinterpret a
closed journal in place.

## 5. Record and Publication Grammar

The schema is `world-model-causal-journal-v1`. A journal is a dedicated directory. Each
record is one canonical JSON line in an immutable segment named:

```text
<eight-digit-sequence>-<record-sha256>.json
```

Every envelope has exactly:

```text
schema_version, journal_id, run_id, domain, sequence,
previous_record_sha256, record_type, body, record_sha256
```

The first predecessor is 64 zeroes. The legal grammar is:

```text
run_header
(
  pre_action_commit
  (
    execution_resolution(not_executed)
    |
    execution_handoff
    (
      execution_resolution(not_executed | execution_unknown)
      |
      action_receipt outcome
    )
  )
)*
run_ledger
```

Steps occur exactly once and in the order frozen by `expected_step_ids`. Unknown record
types, versions, fields, filenames, gaps, duplicates, replay, non-canonical encodings,
torn segments, cross-journal identity changes, broken links, and post-ledger records
refuse.

Publication uses a same-directory exclusive temporary file, complete-write loop, file
`fsync`, atomic no-replace hard-link to the final record name, and temporary-name cleanup.
The directory is also fsynced where Python exposes `O_DIRECTORY`. The header records one
of these closed durability profiles:

```text
fsync-file+atomic-link+fsync-directory
fsync-file+atomic-link
```

The second profile, used on Windows, supports the process-crash gate but does not claim a
portable proof that directory metadata survives sudden power loss. A power-loss evidence
tier on that platform requires a separately validated protected sink/OS protocol.

Only one writer may hold the persistent writer lock. The writer also checks the retained
directory and lock-file identities and re-verifies the complete current chain before each
new record and immediately before invoking the executor. Preflight uses an exact inert
`ActionAdapterBinding` containing the executor artifact hash and an opaque adapter
reference; the adapter object is not touched until after the durable handoff. Step and
selected-action IDs are exact strings before any equality/hash operation. A publication fault poisons that
writer handle; it cannot retry against an uncertain partial write.

## 6. Causal and Crash Semantics

The boundary meanings are:

| Durable prefix | Honest state after crash |
|---|---|
| Commit, no handoff | `committed_not_executed` (`handoff_not_published`) |
| Handoff, no authoritative receipt | `execution_unknown` until reconciliation |
| Authoritative receipt, no outcome record | `executed_outcome_missing`; recover locally from receipt evidence |
| Receipt plus outcome | `complete` |

An external side effect cannot be made exactly-once by a local journal alone. The stable
`execution_id` binds the journal/run/domain/step, state, candidate set, selected action,
estimator and configuration, executor, ontology, prediction status/reason, and complete
probability vector. After the commit and handoff are published, the opaque executor
adapter receives an exact `ExecutionRequest` that also carries the commit record hash and
supplies:

```text
execute(request) -> ActionResolution
reconcile(request) -> ActionResolution
```

An `executed` resolution requires an authoritative receipt plus the retained observation
and source. Reconciliation may establish executed or not-executed only when the external
system can answer authoritatively for that stable ID. Failure, absence, or indeterminate
reconciliation closes as `execution_unknown`; the run is held and cannot be scored.
Blind replay is outside this contract.

Injected crash checkpoints cover commit, handoff, post-execute/pre-receipt, receipt,
outcome, and both sides of ledger publication. Injection is a closed exact set of inert
checkpoint names; it is not a caller callback. Publication-fault tests additionally prove
that failed record link/fsync boundaries do not invoke the executor.

## 7. Closed Status and Reason Sets

Prediction statuses:

```text
collected, not_applicable, not_collected, estimator_failed
```

Execution dispositions:

```text
executed, not_executed, execution_unknown
```

Step statuses:

```text
not_committed, committed_not_executed, execution_unknown,
executed_outcome_missing, complete
```

Run statuses are `open`, `complete`, and `held`. A terminal reason is derived from the
verified step state: `all_steps_observed`, `planned_steps_uncommitted`,
`action_not_executed`, `execution_unknown`, `executed_outcome_missing`, or
`multiple_incomplete_conditions`. Execution and prediction reason codes are likewise
closed in the implementation. Free-form text is not authoritative contract data.

## 8. Completeness Ledger and Scoring Gate

The terminal ledger binds the preceding chain head, every expected step and terminal
record, and exact counts for:

```text
planned, uncommitted, committed, executed, not_executed, execution_unknown,
outcomes, in_support, declared_other, unknown, out_of_support
```

The four outcome classes must sum exactly to `outcomes`. Ledger values are derived, then
recomputed independently by the loader. Closing early remains valid evidence but produces
a held ledger with visible omissions; it is never a successful experiment.

`scoring_rows(path, expected_manifest_sha256=...)` reloads and verifies the journal rather
than trusting a caller-constructed snapshot. It accepts only a terminal `complete` journal
in which every prediction was collected. It returns every planned outcome, including
`declared_other`, `unknown`, and `out_of_support`. It refuses the whole run rather than
filtering incomplete, uncertain, or unpredicted rows and thereby shrinking the denominator.

## 9. Phase 3a Gate

The task gate requires:

- zero executor calls before the durable commit and handoff prefix is observable;
- zero acceptance of mutated, replayed, torn, non-canonical, or semantically false-ledger
  records in the tested threat model;
- complete inline resolution of all committed artifacts;
- 100 percent retention of authoritative outcomes, including novel raw labels;
- exact planned-step and outcome-class accounting;
- conservative recovery at every causal boundary, including no re-execution after an
  authoritative reconciliation result; and
- unchanged Phase 2 trace/capture source hashes and passing legacy model-free tests.

A green Phase 3a gate authorizes only this evidence format and local controlled-executor
contract. Integration remains held by the independent downstream tasks.
