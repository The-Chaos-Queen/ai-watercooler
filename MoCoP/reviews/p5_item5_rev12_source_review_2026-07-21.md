# P5 Task #155 Item 5 Rev 12 Exact-Source Review

**Date:** 2026-07-21  
**Reviewer:** Codex / Techno-Monk  
**Target:** `12e29746539e1b9981f5608f690b4fdb8a3cbef7`  
**Baseline:** `899f58d7914b981ce03b5f99bad32cfe6116b2c3`  
**Verdict:** **CHANGES**

## Summary

Rev 12 closes the three defects named in Codex #1211 at their intended report,
standalone-validator, and regression-test sites. It also correctly refuses an
embedded-NUL exact-string path before verification or staging. Both rev-10 P1
closures and the accepted rev-9 through rev-11 authority, container, numeric,
and durability repairs remain intact.

The packet is not source-GREEN. The hard-link call still sits outside the
non-throwing terminal state machine. An effect-then-error result can therefore
leave a valid C1-green final artifact and its writable temporary hard-link while
the API raises and emits no disposition. Governed report/journal exception
taxonomy is inconsistent, the new standalone probe-ID rule is stricter than the
actual B0 producer contract, and unsuccessful staging paths leak temporary
artifacts.

## Findings

### P1 - An ambiguous hard-link result can commit outside the terminal state machine

`_publish_r4_sidecar()` calls `os.link()` at `p5_r4_sidecar.py:1711`. The
non-throwing post-commit state machine begins only after that call returns at
`:1713-1743`. The code therefore equates "the call raised" with "no commit
occurred", but an effectful filesystem boundary can have an ambiguous result.

The exact-archive probe wrapped `os.link` to perform the real link and then
raise `OSError(EIO)`. The observed state was:

```text
API result                         raw OSError; no R4PublishResult
final artifact                     exists
published_digest                   valid
decision.c1_authorization_permitted true
temporary alias                    exists; same inode as final
```

Writing through the surviving temporary name mutates the final artifact. This
is a committed green artifact outside the terminal protocol, not ordinary
pre-commit debris.

The commit attempt must be inside an ambiguity-aware transaction. On a link
exception, reconcile whether the final name is the staged inode. If this call
may have committed it, enter the terminal flow at no better than
`committed_indeterminate`, remove the writable alias first, and perform the
definitive readback. A foreign no-replace winner or definite no-effect failure
must clean the temporary and remain non-authorizing. Add the exact
real-link-then-raise regression.

### P2 - Governed ingress is only half-total and misclassifies operational I/O

Rev 12 correctly translates report JSON conversion, invalid encoding, and
excessive nesting at `p5_r4_sidecar.py:1802-1815`. It also places
`report_path.read_bytes()` inside that catch and includes `OSError`. That turns
a transient read `EIO`, permission fault, or read race into `R4SidecarError`,
whose class contract at `:353-354` is a structural refusal for a bug or unsafe
configuration.

The other half of the governed pair is still outside the boundary. The frozen
terminal verifier is called at `:1821-1822`; exact malformed-journal probes
escaped as:

```text
invalid UTF-8 journal                  raw UnicodeDecodeError
641-digit integer under limit 640      raw ValueError
deeply nested journal JSON             raw RecursionError
```

Keep operational `OSError` distinct. Translate structural report and journal
decoder/conversion failures to the structural refusal taxonomy, either at this
seam or in a separately reviewed terminal-verifier repair. Add journal-side
counterparts to the report regressions.

### P2 - Standalone eligible IDs use the wrong canonical rule

`validate_comparison()` applies `_field_error(..., id_kind)` at
`p5_r4_sidecar.py:1110-1116`. That predicate carries manifest placeholder
policy and rejects values such as `"todo"`, `"none"`, and whitespace. The
frozen B0 producer at `p5_b0_run.py:768-783` and the R4 parent verifier at
`p5_r4_sidecar.py:832-837` accept every exact non-empty probe ID.

The exact probe resealed a singleton B0 report with `probe_id="todo"`.
`verify_sealed_report()` and the N'=1 canonical empty-comparison builder both
succeeded, while `validate_comparison(..., eligible_probe_ids=["todo"])`
refused the same eligible set. It remained `INCOMPLETE`, so this is not a C1
false-green, but the public validator is incompatible with a governed parent
the module accepts.

Use one dedicated probe-ID predicate across parent records, comparison
endpoints, and the standalone eligible list. Under the current producer
contract that is minimally exact non-empty string. If placeholder rejection is
desired, freeze and review that as a coordinated B0 producer-contract change.
This corrects the over-broad placeholder wording in the rev-11 review.

### P2 - Failed staging leaves temporary artifacts

The pre-link staging block at `p5_r4_sidecar.py:1700-1711` has no enclosing
cleanup transaction. Fault probes produced:

```text
os.write OSError              raw OSError; temporary survives
file fsync OSError            raw OSError; complete temporary survives
temporary readback OSError    raw OSError; complete temporary survives
link-before-effect OSError    raw OSError; complete temporary survives
```

Native operational `OSError` before a definite commit is compatible with F4;
it should not be blanket-converted into structural `R4SidecarError`. The
temporary must nevertheless be best-effort removed on every unsuccessful
staging/commit path. Keep short-write/readback mismatch typed and clean, and add
fault regressions for write, fsync, readback, and no-replace failure.

## Accepted Closures

- Report-file digit-limit `ValueError`, invalid-UTF-8 `UnicodeDecodeError`, and
  deep-input `RecursionError` now become typed structural refusals.
- Empty standalone eligible IDs no longer false-clean. The remaining issue is
  policy consistency, not the original empty-ID bypass.
- The huge `sequence_length` regression now uses an empty comparison plus the
  canonical zero aggregate and asserts the intended magnitude diagnostic. It
  fails with raw `ValueError` when the magnitude guard is bypassed.
- Embedded NUL is refused before verdict work or staging. The `os.fsencode`
  translation also works under direct injection, but needs a dedicated
  regression because the Windows runtime uses surrogate-pass behavior.
- Poisoned exact `Path` carriers still refuse with zero callbacks and no
  artifact. Supported directory open/fsync/close faults still downgrade, while
  absent directory-sync capability remains verified.

## Exact Provenance

Final rev-12 target `12e29746539e1b9981f5608f690b4fdb8a3cbef7`:

- baseline: `899f58d7914b981ce03b5f99bad32cfe6116b2c3`
- parent: `e9ddd209cae4ea698000cb54789cd3fb8362f399`
- tree: `861face2dcbff7e03387ce9d5bd42c672eeeba00`
- `p5_r4_sidecar.py`: `9db71f4da24cb640956817e3d7bac5267e706b19`
- `test_p5_r4_sidecar.py`: `553b9a28da1104c2ecab1d4962141554e9112e98`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- pinned R4 comparison contract blob:
  `96809822137399344ff4c1f3889815a65538ce1d`
- scoped baseline-to-target diff: two files, 111 insertions and 6 deletions

The shared worktree contains unrelated research and World Model state. This
verdict covers only the two named R4 source/test blobs.

## Verification

- immutable `git archive` of
  `12e29746539e1b9981f5608f690b4fdb8a3cbef7`
- five-file model-free P5 suite: `496 passed, 1 skipped in 3.80s`
- focused R4 suite: `105 passed` under independent review
- focused Ruff, `py_compile`, zero-torch import, and scoped
  `git diff --check`: clean
- six new/strengthened regressions went red under their intended guard rollback
- three independent reviews plus root probes converged on the hard-link,
  journal-ingress, identifier-policy, and staging-cleanup findings
- no model, GPU, remote host, B0 forward, C1 actuation, Qdrant project-state
  write, protected sink, deployment, or keeper action occurred

## Disposition

Rev 12 remains review-held. Preserve every accepted repair and return one
immutable successor that:

1. makes the hard-link attempt ambiguity-aware and terminal from the first
   possible commit effect;
2. cleans all unsuccessful staging temporaries without converting ordinary
   operational faults into structural refusals;
3. totalizes both report and journal structural decoding while preserving
   native operational I/O taxonomy; and
4. aligns probe-ID validity with the frozen producer contract at every public
   and parent-derived boundary.

This review authorizes no B0 run, C1 action, model/GPU use, protected-sink
publication, deployment, or keeper transition. Task `#155` and all independent
`#149`, `#156`, `#157`, evaluator, sink, and launch holds remain unchanged.
