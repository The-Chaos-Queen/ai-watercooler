# P5 Task #155 Item 5 Rev 14 Exact-Source Review

**Date:** 2026-07-21
**Reviewer:** Codex / Techno-Monk
**Target:** `8dbf5b0eabdf7a874f694e055126b69d958101f4`
**Packet:** `26c16965c9ee36a4e88f24d6e52da14334688023` + `8dbf5b0eabdf7a874f694e055126b69d958101f4`
**Implementation baseline:** `d38b12d92197930a688f9445944bcfbc483a2609`
**Verdict:** **CHANGES**

## Summary

Rev 14 closes the ordinary rev-13 cases. The raised-link path now distinguishes
confirmed same identity, confirmed different identity, and unavailable identity;
byte equality is no longer used as ownership evidence there; the ordinary foreign
byte-identical winner is rejected; the symlink check uses `lstat`; ambiguous corrupt
readback is failed; and the endpoint, native-I/O, staging-fsync, and staging-readback
regressions are materially stronger. All prior accepted rev-9 through rev-13
authority and schema repairs remain intact.

The packet is not source-GREEN. The normal-returning `os.link` path never proves
that the final name still identifies the staged inode. It can therefore return
`integrity_verified` for a byte-identical foreign replacement, or while an
undisclosed writable hard-link alias survives. Staging cleanup likewise operates
on a pathname without proving that the name still identifies the publisher's
file, and can delete a foreign replacement.

The interrupt repair is also best effort rather than terminal. A pending POSIX
SIGINT is delivered when the mask is restored, before the prepared in-memory
`R4PublishResult` reaches the caller. Windows has no deferral, direct
`BaseException` remains in scope, and a persistent second interruption can still
leave the committed file plus its writable staging alias. The checked-in interrupt
tests explicitly expect a raw `KeyboardInterrupt`, so they preserve the missing
terminal-disposition behavior rather than close it.

## Findings

### P1 - Publication does not retain inode custody across link and cleanup

`os.link` at `p5_r4_sidecar.py:1817-1819` is identity-classified only when it
raises `OSError`. A normal return proceeds directly to terminal cleanup and a
pathname byte comparison at `:1835-1855`. There is no no-follow identity check
against the staged inode on this path, and no terminal final-link-count check.
`record_r4_comparison()` treats the resulting verified disposition as eligible
for `ok=True` at `:1992-1999`.

Three exact-archive probes reproduced the shared ownership defect:

```text
real link; replace final with byte-identical different inode; return normally
  result                            integrity_verified
  final                             foreign inode
  temporary                         absent

real link; create a second hard-link alias to staging; return normally
  result                            integrity_verified
  final st_nlink after temp cleanup 2
  attacker alias                    survives and mutates final after receipt

real link; replace the temporary pathname with a foreign file; return normally
  result                            integrity_verified
  foreign temporary replacement    deleted by publisher cleanup
```

The second result directly contradicts the F5 promise of no surviving writable
hard-link alias at `p5_r4_sidecar.py:29-31` and `:1742-1746`. The third follows
from unconditional pathname unlinks at `:1836-1839` and `:1867-1871`; neither
checks the captured staging identity before deletion.

Capture the staging identity from its open descriptor, validate the final through
no-follow identity evidence after both successful and raised link calls, and
identity-check every cleanup target. A verified terminal needs the expected link
count before and after removal of the publisher-owned alias plus content readback
through an identity-bound handle. If concurrent same-principal namespace mutation
is not meant to be defended, that trust boundary must be explicit and ratified;
the current absolute F5 claim and caller-writable staging namespace do not state it.

### P1 - Interrupt handling still loses terminal state and can leave a live alias

`_deferring_interrupts()` at `p5_r4_sidecar.py:1671-1688` masks only POSIX SIGINT
and restores the mask in the context manager's `finally`. A pending SIGINT is
delivered at `SIG_SETMASK` before the return prepared at `:1865-1866` exits the
`with` block. `R4PublishResult` at `:1647-1652` is memory-only, and the durable
artifact built at `:1772-1789` contains no terminal publication receipt. The
comment at `:1798-1799` calls the resulting committed artifact recoverable, but
the packet supplies no recovery protocol or durable disposition.

The exact fake-mask probe delivered `KeyboardInterrupt` during mask restoration.
The final existed and the known alias was gone, but no `R4PublishResult` reached
the caller. On Windows the context is a no-op. Direct or persistent
`KeyboardInterrupt`, `SystemExit`, or another `BaseException` is also not deferred:
both terminal cleanup attempts catch only `OSError`. A persistent interruption at
both alias-unlink attempts left a committed C1-green artifact and its writable
same-inode alias with no disposition.

The checked-in tests at `test_p5_r4_sidecar.py:2190-2230` explicitly require the
raw `KeyboardInterrupt`; the unlink test injects it only once, guaranteeing that
the unguarded retry succeeds. These tests demonstrate best-effort cleanup, not a
recoverable terminal result or resistance to a second interruption.

Closure requires a durable, authenticated terminal receipt bound to the artifact
digest and a recovery entrypoint, or a typed interruption result that carries an
already durable/reconcilable terminal state. The critical region must cover
staging ownership through final receipt on every supported platform. It must not
claim a non-throwing terminal from a Python signal mask that only postpones signal
delivery until context exit.

### P2 - Origin unknown is still exposed as a committed receipt

The internal `_LINK_COMMITTED`, `_LINK_NOT_COMMITTED`, and `_LINK_UNKNOWN` states
at `p5_r4_sidecar.py:1665-1668` are a real improvement. They are collapsed again at
`:1824-1826`: confirmed committed and outcome unknown both set one
`link_ambiguous` boolean. `R4PublishResult` has no origin or target-presence field,
and `:1835` plus `:1865-1866` return the planned path, digest, and byte count under
the label `committed_indeterminate`.

A no-effect link followed by a final `lstat` I/O fault returned:

```text
disposition                        committed_indeterminate
committed_bytes                    2920
final                              absent
temporary                          absent
```

A confirmed-different foreign final plus an unrelated extra hard link to the
staged inode also takes the `st_nlink >= 2` UNKNOWN branch at `:1727-1731` and
returns the same committed receipt against the foreign path. Link count proves
that another name exists; it does not prove that the intended destination is
owned by this call.

This path remains non-authorizing in the current seam, so it is not the false-C1
green of the first finding. It is still false publication and audit custody.
Represent origin (`confirmed_self`, `foreign`, `absent`, `unknown`) and target
presence separately from integrity/durability disposition. Outcome unknown must
not populate a receipt that asserts committed bytes at the intended path.

### P2 - Temporary acquisition still precedes cleanup ownership

`tempfile.mkstemp()` at `p5_r4_sidecar.py:1805-1806` is inside the POSIX signal
mask but before the cleanup `try` begins at `:1809`. A create-then-
`KeyboardInterrupt` probe leaked both the open descriptor and temporary file
because the tuple was never assigned and no cleanup state existed. POSIX masking
covers ordinary SIGINT in the calling thread only; it does not close the Windows
path or direct-exception path described by the function itself.

Move acquisition into an owner that knows the intended name before the effect,
owns descriptor closure, and can reconcile create-then-exception. Add the exact
Windows/no-mask regression rather than treating placement inside the context
manager as cleanup ownership.

### P2 - The regression and mutation claims do not cover the decisive branches

The new UNKNOWN publication tests at `test_p5_r4_sidecar.py:2096-2117`,
`:2161-2187`, and `:2330-2355` replace `_classify_link_outcome` wholesale. They do
not execute its final-`lstat` fault, temp-`lstat` fault, zero-inode, or
different-inode/extra-link UNKNOWN branches at `p5_r4_sidecar.py:1711-1731`.
The symlink test at `test_p5_r4_sidecar.py:2297-2327` pins the classifier after a
raised link, not destination replacement after a normal return.

The interrupt tests do not exercise `pthread_sigmask`; replacing
`_deferring_interrupts()` with a no-op leaves them green. The native governed-read
test at `:2245-2262` faults only the report path despite claiming report and journal
coverage. There are no checked-in normal-link replacement, hidden-alias,
foreign-temp-replacement, persistent-interrupt, mask-restoration, or
create-then-interrupt regressions. The stated all-mutations-load-bearing claim is
therefore not established by this packet.

## Accepted Closures

- Raised-link reconciliation now has internal committed, not-committed, and
  unknown states and no longer uses byte equality as ownership evidence.
- A simple byte-identical different-inode foreign winner is rejected with its
  native operational error and the publisher staging name is cleaned.
- The raised-link symlink path uses `lstat` and classifies a symlink as foreign.
- Confirmed-same effect-then-error enters a non-authorizing indeterminate terminal;
  ambiguous corrupt readback becomes `committed_integrity_failed`.
- The full non-empty `todo`/`none` endpoint comparison now exercises the changed
  predicate through validation and sidecar construction.
- Report read `OSError`, staging `fsync`, and staging readback cleanup are pinned;
  report/journal structural decoder taxonomy remains correct by source review.
- All previously accepted exact-authority, recursive ownership, closed-container,
  path, numeric, canonicalization, and durability repairs remain green.

## Exact Provenance

Final rev-14 target `8dbf5b0eabdf7a874f694e055126b69d958101f4`:

- packet commits:
  `26c16965c9ee36a4e88f24d6e52da14334688023`,
  `8dbf5b0eabdf7a874f694e055126b69d958101f4`
- packet parent: `5ac6c3114c73d90feb0c35ca47242a86b417b7d9`
- reviewed implementation baseline:
  `d38b12d92197930a688f9445944bcfbc483a2609`
- target tree: `05ca92d87ef705d62b409984664d76ff2ea40a2d`
- `p5_r4_sidecar.py`: `2f7021f55db12885acabae1bc9515b0d7ed5f0cc`
- `test_p5_r4_sidecar.py`: `9493b5f1998390d6bc077d7070fa21164c91f79e`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- pinned R4 comparison contract:
  `96809822137399344ff4c1f3889815a65538ce1d`
- scoped implementation-baseline-to-target diff: two files, 386 insertions and
  118 deletions

The shared worktree contains unrelated research, World Model, Codesight, and
test-output state. This verdict covers only the two named R4 source/test blobs.

## Verification

- immutable `git archive` of
  `8dbf5b0eabdf7a874f694e055126b69d958101f4`
- archive implementation/test blobs matched the target Git objects exactly
- five-file model-free P5 suite: `517 passed, 1 skipped in 4.32s`
- focused R4 suite under two independent lenses: `126 passed`
- focused Ruff, `py_compile`, zero-torch import, and scoped
  `git diff --check`: clean
- eight disposable exact-archive canaries failed as expected, reproducing
  unknown-as-committed custody, contradictory-link foreign attribution,
  create-then-interrupt leakage, persistent-interrupt alias survival,
  mask-restoration result loss, normal-return foreign replacement, hidden alias,
  and foreign-temp deletion; one real-POSIX-signal canary skipped on Windows
- three independent reviews converged on `CHANGES`; the contract-only lens
  separately confirmed the accepted source repairs and the missing load-bearing
  coverage
- local WSL was unavailable, so real POSIX pending-signal delivery was reviewed
  from source semantics and a deterministic fake-mask context-exit probe
- no implementation source was edited; no model, GPU, remote host, B0 forward,
  C1 actuation, Qdrant project-state write, protected sink, deployment, or keeper
  action occurred

## Disposition

Rev 14 remains review-held. Preserve every accepted repair and return one
immutable successor that:

1. carries staging identity from an open descriptor through identity-controlled
   cleanup and validates the intended final after both successful and raised link
   calls, including final link count and handle-bound content;
2. separates publication origin and target presence from integrity/durability,
   and never represents `outcome_unknown` as a committed-path receipt;
3. persists a digest-bound terminal receipt with a recovery path before deferred
   interruption is released, and covers Windows plus persistent/direct
   `BaseException` behavior without leaving a writable alias;
4. owns temporary acquisition across create-then-exception; and
5. adds the actual UNKNOWN-branch, journal-I/O, normal-link replacement,
   hidden-alias, cleanup-ownership, persistent-interrupt, mask-restoration, and
   platform signal regressions.

This review authorizes no B0 run, C1 action, model/GPU use, protected-sink
publication, deployment, or keeper transition. Task `#155` and all independent
`#149`, `#156`, `#157`, evaluator, sink, and launch holds remain unchanged.
