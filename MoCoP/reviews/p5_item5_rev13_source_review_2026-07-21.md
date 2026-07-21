# P5 Task #155 Item 5 Rev 13 Exact-Source Review

**Date:** 2026-07-21
**Reviewer:** Codex / Techno-Monk
**Target:** `d38b12d92197930a688f9445944bcfbc483a2609`
**Packet:** `a705e4b7e86c52fddaee91458bdc9795ff2cad90` + `d38b12d92197930a688f9445944bcfbc483a2609`
**Baseline:** `12e29746539e1b9981f5608f690b4fdb8a3cbef7`
**Verdict:** **CHANGES**

## Summary

Rev 13 correctly repairs the ordinary `OSError` paths named in Codex #1213.
Effect-then-error linking reaches `committed_indeterminate` when inode or byte
evidence is available; definite no-effect failures clean the staging file;
report and journal decoder failures now follow the structural-refusal taxonomy;
probe IDs match the frozen B0 producer contract; and ordinary staging failures
clean their temporary artifacts. All accepted rev-9 through rev-12 repairs
remain intact.

The packet is not source-GREEN. Link reconciliation still treats three evidence
states as a boolean. When both inode identity and final readback are unavailable,
it mislabels an unknown result as definite no-effect and can strand a digest-valid
C1-green artifact with no terminal disposition. Conversely, byte equality can
attribute a different-inode foreign winner to this call. The claimed
non-throwing terminal also catches only `OSError` after commit, so an asynchronous
`KeyboardInterrupt` can still escape with either a committed artifact alone or a
committed artifact plus its writable hard-link alias.

## Findings

### P1 - Binary reconciliation still strands an unknown committed outcome

`_same_inode()` at `p5_r4_sidecar.py:1662-1671` returns `False` for both a
provably different inode and unavailable identity evidence. `_link_committed()`
at `:1674-1690` then returns `False` when final-byte readback raises `OSError`.
The handler at `:1773-1794` treats that value as definite no-effect, removes the
temporary name, and re-raises the original link error.

The exact-archive probe performed the real link, raised `OSError(EIO)`, forced
inode evidence unavailable, and made the immediate final read raise a transient
`OSError`. The observed state was:

```text
API result                         raw OSError; no R4PublishResult
final artifact                     exists
temporary alias                    removed
decision                           jsd_proceeds
decision.c1_authorization_permitted true
published_digest                   valid
terminal disposition               absent
```

A read fault is unknown evidence, not proof that no effect occurred. The
transaction needs at least `committed`, `not_committed`, and `outcome_unknown`.
An unknown outcome must reach a non-authorizing terminal result without deleting
a potentially foreign final name and without leaving a green artifact outside
the terminal protocol.

### P1 - Post-commit BaseException still escapes the terminal region

The staging wrapper catches `BaseException` at `p5_r4_sidecar.py:1785-1794`,
but it always re-raises. The inner link reconciliation catches only `OSError` at
`:1775`. After the wrapper exits, terminal alias cleanup, existence checks,
readback, and directory durability at `:1803-1826` also catch only `OSError`.
The comment that nothing may raise after commit is therefore stronger than the
implemented control flow.

Two exact probes reproduced both sides of the remaining interrupt window:

```text
real link then KeyboardInterrupt
  result                            raw KeyboardInterrupt; no disposition
  final                             exists; digest-valid; c1=true
  temporary                         removed

normal link then KeyboardInterrupt at terminal tmp.unlink()
  result                            raw KeyboardInterrupt; no disposition
  final                             exists; digest-valid; c1=true
  temporary                         exists; same writable inode as final
```

The second case recreates the rev-12 P1 state. If asynchronous interruption is
in scope, the critical region must defer it until alias removal and terminal
state publication are complete, or use a lower-level/durable transaction that
can be reconciled after process interruption. Unconditionally unlinking in the
pre-terminal exception handler does not cover interrupts inside the terminal
machine.

### P2 - Byte equality falsely claims a foreign no-replace winner

`_link_committed()` at `p5_r4_sidecar.py:1678-1689` calls equal bytes "commit
evidence as strong as the inode." They prove content, not ownership or which
writer won the no-replace race. The function also cannot tell whether
`_same_inode() == False` means different identity or unavailable identity.

The exact race probe created a separate destination file from the staged bytes
and raised `FileExistsError(EEXIST)`. The final and staging paths were confirmed
to be different inodes, but publication returned:

```text
disposition                        committed_indeterminate
reported path/digest/byte count    this call's publication result
final                              foreign, byte-identical artifact
temporary                          removed
```

This remains non-authorizing, so it is not a C1 false-green. It is still false
publication custody and contradicts the stated native-error behavior for a
foreign winner. Distinct identity must remain a definite foreign result. If
identity is genuinely unavailable, byte equality alone can support content
equivalence only, not ownership; represent the outcome as unknown.

### P2 - The regression packet does not pin the full repair surface

The producer-ID regression at `test_p5_r4_sidecar.py:2070-2078` passes an empty
comparison for `todo` and `none`. It therefore never executes the changed
endpoint predicate at `p5_r4_sidecar.py:1190-1196`. Reverting only those
endpoint lines to rev-12's placeholder-aware rule leaves the new test green.
A complete `todo`/`none` pair must pass standalone validation and
`build_r4_sidecar()`.

The checked-in tests also do not pin native report/journal read `OSError` at
`p5_r4_sidecar.py:1887-1913`, staging `os.fsync` failure at `:1768`, or staging
readback `OSError` at `:1771`. Exact probes show the current source behavior is
correct, but these are the transitions requested by #1213 and claimed as
load-bearing. Add the missing negative-path regressions.

## Accepted Closures

- Real link then `OSError` reaches `committed_indeterminate`, removes the alias,
  and reads back the final when inode identity or final bytes are available.
- Definite no-effect link failure, ordinary write failure, and staged-byte
  mismatch clean the temporary; structural mismatch stays typed while native
  operational failures remain native.
- Report and journal invalid UTF-8, digit-limit conversion, and excessive
  nesting become `R4SidecarError`; exact report/journal read `OSError` remains
  native under direct probes.
- Exact non-empty producer IDs, including `todo`, `none`, and whitespace, are
  accepted consistently by the implemented parent, endpoint, and standalone
  predicates.
- The dedicated `os.fsencode` regression reaches the intended typed refusal.
- All previously accepted authority, recursive ownership, exact-container,
  path, numeric, canonicalization, and durability repairs remain green.

## Exact Provenance

Final rev-13 target `d38b12d92197930a688f9445944bcfbc483a2609`:

- packet commits:
  `a705e4b7e86c52fddaee91458bdc9795ff2cad90`,
  `d38b12d92197930a688f9445944bcfbc483a2609`
- packet parent: `1cde01946c141a8417c5b1a6b1676d31211677ea`
- reviewed implementation baseline:
  `12e29746539e1b9981f5608f690b4fdb8a3cbef7`
- target tree: `0ac15fe329a118ca9d4b2aab79930eccff87375a`
- `p5_r4_sidecar.py`: `613f23f8580ef563bc3404ad61d8e5380391649f`
- `test_p5_r4_sidecar.py`: `fde5e3953cf42369766136059b942610fcec9d47`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- pinned R4 comparison contract blob:
  `96809822137399344ff4c1f3889815a65538ce1d`
- scoped rev-12-to-rev-13 diff: two files, 312 insertions and 44 deletions

The shared worktree contains unrelated research and World Model state. This
verdict covers only the two named R4 source/test blobs.

## Verification

- immutable `git archive` of
  `d38b12d92197930a688f9445944bcfbc483a2609`
- archive blobs matched the target Git objects exactly
- five-file model-free P5 suite: `507 passed, 1 skipped in 3.73s`
- focused Ruff, `py_compile`, zero-torch import, and scoped
  `git diff --check`: clean
- four disposable exact-archive canaries reproduced the two unknown-outcome
  escapes, the terminal interrupt with a live same-inode alias, and the foreign
  byte-identical attribution
- three independent reviews converged on the transaction findings; the
  contract pass separately confirmed the source-level taxonomy and ID repairs
  while identifying the missing regression coverage
- no implementation source was edited; no model, GPU, remote host, B0 forward,
  C1 actuation, Qdrant project-state write, protected sink, deployment, or
  keeper action occurred

## Disposition

Rev 13 remains review-held. Preserve every accepted repair and return one
immutable successor that:

1. separates confirmed same identity, confirmed different identity, and
   unavailable identity instead of collapsing them into one boolean;
2. treats failed readback after ambiguous commit as `outcome_unknown`, never as
   proof of no effect, and never claims byte equality as ownership;
3. closes the asynchronous interruption window across both the link call and
   every post-commit terminal operation, with alias removal and a recoverable
   non-authorizing disposition; and
4. adds the foreign-identical, unavailable-readback, link-interrupt,
   terminal-unlink-interrupt, endpoint-ID, native read-I/O, fsync, and staging
   readback regressions.

This review authorizes no B0 run, C1 action, model/GPU use, protected-sink
publication, deployment, or keeper transition. Task `#155` and all independent
`#149`, `#156`, `#157`, evaluator, sink, and launch holds remain unchanged.
