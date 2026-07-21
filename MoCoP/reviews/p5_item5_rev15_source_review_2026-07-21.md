# P5 Task #155 Item 5 Rev 15 Exact-Source Review

**Date:** 2026-07-21
**Reviewer:** Codex / Techno-Monk
**Target:** `c1de21291408fba4b8dcc722aa34d976c5a5ee5f`
**Packet:** `64947e6f4147c2d8bc3cf91a2b748b1b15d5d01c` +
`c1de21291408fba4b8dcc722aa34d976c5a5ee5f`
**Implementation baseline:** `8dbf5b0eabdf7a874f694e055126b69d958101f4`
**Watercooler request:** `#1218`
**Verdict:** **CHANGES (P2; no in-scope P1)**

## Summary

Rev 15 closes the two rev-14 false-authorization roots within the boundary Laura
selected on 2026-07-21. Staging identity now comes from the open descriptor;
normal and raised `os.link` outcomes are classified against it; the clean path
requires the expected final inode and exact link count; content is read through
an identity-checked descriptor; foreign regular-file replacements of the temp
name are preserved; and the public seam explicitly requires both
`integrity_verified` and `origin == confirmed_self`. The ineffective POSIX SIGINT
mask is gone. No in-scope path to `ok=True` was reproduced.

The keeper-approved limits are accepted: this model-free sidecar is not a durable
transaction/recovery system, and it does not defend its namespace against an
arbitrary same-principal concurrent attacker. Those limits remain non-authorizing
and must remain explicit.

The packet is nevertheless not source-GREEN. Rev 14 required publication origin
and target presence to be separate from integrity/durability, and required an
UNKNOWN outcome not to assert committed bytes at the intended path. Rev 15 adds
only a first-check `origin` snapshot. Later contradictory evidence downgrades the
disposition without updating that snapshot, while every result still reports the
planned byte count as `committed_bytes`. The advertised temporary-acquisition
repair and test also begin only after `mkstemp` has returned, so they do not cover
the create-then-interrupt window they claim to close.

## Exact Source

- target tree: `bcb7d9c5f67fe028d3d58af24e132db8860e4e46`
- packet parent: `2475f64aa1429242ab1614a593897a0906a827b4`
- source blob: `e72a43cedd4be29e8e55c9f9e41ac7dd5fe8644c`
- test blob: `998df79d9932b158d745f9a7a22d6d1e442b4e0b`
- frozen `p5_b0_run.py` blob:
  `a04499b6b6abb2418344cf47b9beced612f55f0b`
- frozen `p5_b0_harness.py` blob:
  `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- immutable review archive SHA-256:
  `6fc828924dc0e034d5136c699323c58ec62745968bbec22efe14bc0046faa6b8`
- scoped delta from rev 14: two files, `+373/-269`; diff check clean

## Findings

### P2 - The public receipt still conflates intended bytes with terminal state

`R4PublishResult` at `p5_r4_sidecar.py:1653-1662` has an `origin` field but no
independent target-presence field. It always exposes `committed_bytes: int`.
`origin` is assigned once from `_final_origin()` at `:1831`; terminal no-follow
and read-handle checks at `:1854-1883` can prove that the final is absent or a
different inode, but they change only `disposition`. The return at `:1892-1893`
reuses the stale origin and always supplies `len(committed)`.

Disposable exact-target canaries reproduced both truth failures:

```text
link had no effect + final lstat unavailable
  disposition       committed_indeterminate
  origin            unknown
  committed_bytes   > 0
  final path        absent

initial final self; terminal check observes foreign replacement
  disposition       committed_integrity_failed
  origin            confirmed_self
  final path        different inode
```

Deleting the final at the same terminal boundary likewise returns
`origin=confirmed_self` while the path is absent. These paths are fail-closed for
C1, so this is P2 rather than P1, but they are false audit custody. The existing
readback-foreign regression at `test_p5_r4_sidecar.py:2397-2420` asserts only the
disposition and therefore preserves the stale origin.

Add an exact target-presence state (`present | absent | unknown`) and ensure a
receipt never labels intended payload length as committed bytes unless terminal
self-ownership/presence evidence supports that claim. Refresh origin/presence
when terminal `lstat`, `open`, or `fstat` evidence contradicts the first snapshot.
The unavoidable race after the last observation remains the named external
boundary; the receipt must still be truthful about the last evidence it used.

### P2 - Temporary acquisition is not owned across create-then-interrupt

The outer `try` at `p5_r4_sidecar.py:1811` improves ordinary cleanup, but the
assignment at `:1812-1814` receives cleanup authority only after `mkstemp`
returns and after `Path(tmp_name)` completes. An interrupt after the underlying
OS open creates the file but before the tuple assignment leaves `fd=None` and
`tmp=None`; the `finally` at `:1894-1907` cannot close or unlink either resource.
An interrupt while constructing `Path(tmp_name)` closes the known descriptor but
still leaks the name.

A real Windows SIGINT canary injected immediately after the underlying open and
reproduced both a live descriptor and surviving temporary file. The checked-in
test at `test_p5_r4_sidecar.py:2281-2294` injects at `os.fstat`, after `mkstemp`
has returned and both locals have been assigned. Its statement that it exercises
the create-then-interrupt boundary is therefore inaccurate.

This need not become a durable transaction. Either use a path-first exclusive
acquisition whose cleanup name is known before the effect, or explicitly include
pre-return acquisition and repeated `BaseException` delivery in the ratified
best-effort interruption boundary. In the latter case, remove the false closure
claim and make the regression document the permitted residual rather than claim
to exercise an earlier branch.

The module-level statement at `:35-39` should also say that alias cleanup is
best-effort under interruption. Persistent `KeyboardInterrupt`, `SystemExit`, or
a custom `BaseException` at both unlink attempts still leaves the final and live
temporary hard-link; this is acceptable only as part of the named interruption
boundary, not as a guarantee that holds generally "against fault injection."

### P3 - Several new terminal branches are not independently pinned

The raised-link UNKNOWN state is not driven directly. The new read-handle
`st_nlink` check at `p5_r4_sidecar.py:1871-1876` is masked by the earlier final
`lstat` check in the hidden-alias test. The seam's new origin conjunct at
`:2036-2038` has no verified-but-non-self regression. Add branch-specific tests
alongside the receipt and acquisition canaries so these state transitions are
load-bearing rather than inferred from overlapping checks.

## Accepted Residual Boundary

Laura's bounded-scope decision is accepted. The following are recorded residuals,
not new findings in this review:

- no durable receipt/recovery after process interruption or sudden power loss;
- no complete defense against an arbitrary same-principal namespace mutator;
- the no-follow-check/open and identity-check/unlink race windows that follow
  from that namespace boundary;
- a same-principal replacement of the temp with a symlink can survive and provide
  another pathname to the final on POSIX. It is outside the protected namespace
  model and cannot independently authorize without the already excluded actor.

No future review should silently promote these properties back into the sidecar's
guarantees. Expanding the threat model requires a separately scoped protected
namespace or durable publication protocol, not another local retry loop.

## Verification

- official five-file model-free suite: `523 passed, 1 skipped`
- disposable receipt/acquisition canaries: `3 passed, 1 Windows-only skip`, where
  passing asserts the reproduced defect states
- independent exact-target state-machine review: `CHANGES`
- independent interruption review: `CHANGES`
- independent contract/coverage review: `CHANGES`
- Ruff: clean
- `py_compile`: clean
- scoped diff check: clean
- zero-model/GPU property retained; no B0 forward, C1 action, protected-sink
  publication, deployment, or remote compute occurred

## Disposition

Rev 15 remains review-held. Preserve every accepted rev-9 through rev-15 repair
and return one narrow immutable successor that:

1. makes origin, target presence, integrity/durability, and committed byte
   evidence mutually truthful at the final receipt;
2. updates origin/presence on contradictory terminal evidence;
3. either owns acquisition before its first filesystem effect or accurately
   places that exact window inside the keeper-approved interruption boundary;
4. narrows the remaining alias/interruption prose and replaces the mislocated
   acquisition test; and
5. pins the raised-UNKNOWN, read-handle link-count, seam-origin, stale-origin,
   target-absent, and true acquisition branches directly.

This review authorizes no B0 run, C1 action, model/GPU use, protected-sink
publication, deployment, or keeper transition. Task `#155` and all independent
`#149`, `#156`, `#157`, evaluator, sink, and launch holds remain unchanged.
