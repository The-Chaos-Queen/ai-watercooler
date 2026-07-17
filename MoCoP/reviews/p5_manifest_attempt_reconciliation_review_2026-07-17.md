# P5 Manifest/Attempt Reconciliation Review

**Date:** 2026-07-17
**Reviewer:** Codex
**Spec:** `6b2347ed19dae3fc521a9a2c23df622487788b3c`
**Implementation/tests:** `6ad5a3732217581c64f34baf4b568d6d895e66a8`
**DQ1b owner correction:** `f1c647a748f4460cb5c863c774b1e6bb85f0d59f`
**Pointer-only spec revision:** `1d9928ec1a43f6c9d8cf7f134bed218a9125b254`

**Verdict:** `GREEN` for the exact post-closure manifest/attempt reconciliation packet.

## Scope And Provenance

The reviewed commits form a linear chain. Implementation and focused-test blobs
at `f1c647a` and `1d9928e` are byte-identical to `6ad5a373`. Revision
`1d9928e` changes only the reconciliation document: it replaces the rev-2
digest-naming question with the owner ruling already source-bound in DQ1b at
`f1c647a`. It changes no executable contract or acceptance criterion.

Pinned blobs:

- rev-2 spec: `0ec19c0ed6848b6c278d08d557d1838a4fe6afc2`
- harness: `7104c70b27854716908bac3aa4eb42d374c586a7`
- runner: `21a253d03d6eeff35ee79b629ee7312d40f9f459`
- harness tests: `828afcd3349f48ec100ca1304303c501e6ddcc54`
- runner tests: `72f148fe19351bd27b81fcb91aa4058db313122b`
- DQ1b owner correction: `63cb8336bb0cb754b36d795518a7dc35bf20edd9`
- rev-3 pointer spec: `2de209524a7937ccf168327639d1dce2dd18b65f`

## Accepted Repairs

The immutable base is now stage-neutral on the B0 surface. `run_kind` and
`base_manifest_digest` are structurally excluded base keys, so a legacy
stage-specific base or a self-digesting base is refused by both a targeted
reason and the closed-world unknown-key gate. The complete base alone produces
`manifest_digest`; the exact-str per-attempt `run_kind` is checked separately
against the frozen schema-variant policy before any governed forward.

`schema_variant` and `base_manifest_id` are required exact strings. The union,
the B0-only applicable variant, the excluded-key policy, and the B0 run kind
are captured in the harness policy snapshot. Rebinding the published globals
therefore cannot widen authorization. The B0 harness continues to refuse a C1
variant; C1-only keys and authorization remain outside this packet.

On a successful B0 run, the execution descriptor binds the variant, base ID,
attempt run kind, and both digest names. The journal claim binds the same
variant/base/stage and the existing exact-schema `manifest_digest`. The report
binds the descriptor and repeats the variant/base/stage. The owner correction
makes `claim.manifest_digest` the normative legacy alias for
`base_manifest_digest`, and the regression requires it to equal both descriptor
digest fields and the standalone complete-base digest.

The packet is also honest about what B0 cannot demonstrate. Because this
harness admits only `b0_baseline`, the provenance difference between the
attempt value and a hardcoded literal is not behaviorally observable here.
Likewise, two applicable C1 run kinds sharing one byte-identical base require a
later C1-capable fixture. Both claims remain explicitly deferred rather than
being presented as B0 test evidence.

## Findings

No correctness, regression, or contract finding remains in the reviewed
packet.

## Verification

- isolated detached clone at exact `f1c647a`
- focused pytest with a sandbox-local basetemp: `280 passed, 1 skipped in 2.99s`
- focused Ruff over implementation and tests: clean
- scoped `git diff --check` through the pointer-only `1d9928e`: clean
- ancestry: `6b2347e -> 6ad5a373 -> f1c647a -> 1d9928e`
- implementation/test blob equality verified at `6ad5a373`, `f1c647a`, and `1d9928e`
- the initial pytest attempt inherited an inaccessible managed-sandbox temp
  root and failed only during `tmp_path` fixture setup; the explicit-basetemp
  rerun above is the substantive result
- no model, GPU, B0 forward, C1 action, Qdrant path, deployment, or experiment
  state was touched

## Disposition

The exact post-closure #156 reconciliation packet is GREEN. This clears only
the held manifest/attempt contract review. It does not authorize a B0 run,
close #149, approve #155 provenance/protected-sink work, supply any numeric
threshold, instantiate the deferred C1 fixture, grant an alpha-zero keeper GO,
or permit a nonzero intervention. The established CPython non-TEE/process-
isolation residual and every independent launch hold remain unchanged.
