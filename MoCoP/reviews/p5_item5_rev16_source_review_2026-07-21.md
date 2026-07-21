# P5 Task #155 Item 5 Rev 16 Exact-Source Review

**Date:** 2026-07-21
**Reviewer:** Codex / Techno-Monk
**Target:** `e594c8d8ea2fef5a683e6ba2555bb2754fbd4ef0`
**Packet:** `a327d48ab74193bc1eb519f5211759438651ff21` +
`e594c8d8ea2fef5a683e6ba2555bb2754fbd4ef0`
**Implementation baseline:** `c1de21291408fba4b8dcc722aa34d976c5a5ee5f`
**Watercooler request:** `#1221`
**Stop rule:** Watercooler `#1220`
**Verdict:** **CHANGES / STOP CLAUSE TRIGGERED (P2; no in-scope P1)**

## Summary

Rev 16 closes the ordinary rev-15 receipt cases. The clean path now reports
verified, self-owned, present publication with positive committed bytes. Later
foreign or absent pathname observations refresh origin and presence, non-green
receipts report zero committed bytes, the seam requires self ownership and
presence, and the pre-return `mkstemp`/`Path` interruption window is now named
honestly as a best-effort external boundary. The requested direct regressions
are present. No natural in-scope path to `record_r4_comparison(...).ok=True` was
reproduced.

The successor nevertheless still makes false receipt claims in three
reproducible in-scope cases. A broad `FileNotFoundError` handler turns
descriptor-side faults into a claim that the pathname is absent. Terminal
identity refresh can classify zero-inode evidence as `confirmed_self`. The new
origin/presence policy labels also remain live globals outside the module's
declared frozen authority snapshot, allowing a pre-call rebind to publish a
verified receipt whose labels contradict the filesystem state while retaining
positive committed bytes.

Watercooler #1220 requires this result to end the local patch loop. Task #155
must not request a rev-17 Python successor. The remaining receipt semantics and
filesystem authority model move to a separately scoped filesystem-protocol
design decision. Rust/process isolation is an option for that decision, not an
automatic rewrite and not work authorized by this review.

## Exact Source

- target tree: `263ac9b279b8ec3aa7769c4a45156605e2794912`
- target parent / core commit: `a327d48ab74193bc1eb519f5211759438651ff21`
- core parent: `87a577557d9eaf45e0e1879ff0e6eaa8df5a4ea1`
- source blob: `5f4a7a0720ddf9fa8225eb004a7986c3c4458208`
- test blob: `48922447eaa3b0d1da042f33cfa03e4d6546faa8`
- immutable review archive SHA-256:
  `d76eec6f42fd6a150a233f5f4205197a8d054d51466966a7bbe6b430ba9403eb`
- scoped delta from rev 15: two files, `+319/-39`; diff check clean

The selected archive was supplemented only with the exact-target allowlist and
its allowlisted null-estimator dependency before running the official suite.
The estimator SHA-256 matched the allowlist.

## Findings

### P2 - Descriptor faults are misreported as target absence

The readback block at `p5_r4_sidecar.py:1903-1934` wraps `os.open`, `os.fstat`,
`_read_all`, and `os.close` in one outer `try`. Its
`except FileNotFoundError` always assigns `origin=absent` and
`target_presence=absent`. Only `FileNotFoundError` from the pathname-opening
operation establishes that the target name is absent; the same exception from
descriptor stat, read, or close does not.

An exact-target canary injected `FileNotFoundError` at the read-handle
`os.fstat` boundary and returned:

```text
disposition       committed_integrity_failed
origin            absent
target_presence   absent
committed_bytes   0
final path        present, 2920 bytes
```

Independent state-machine probes reproduced the same false absent/absent
receipt for read- and close-side `FileNotFoundError`, with a nonempty final file
still present. The checked-in regression at
`test_p5_r4_sidecar.py:2601-2622` covers only `os.open` ENOENT, where the absent
claim is valid.

The protocol needs phase-specific exception handling: isolate the path open,
classify only its ENOENT as absence, and retain the last pathname snapshot or
report unknown for later descriptor faults. Pin fstat, read, and close cases
directly in the successor protocol's tests.

### P2 - Zero-inode terminal observations manufacture ownership

`_final_origin()` at `p5_r4_sidecar.py:1729-1744` correctly treats a zero inode
as unknown. The terminal lstat and fstat branches at `:1884-1921` reimplement
identity classification without that guard. Equal `(st_dev, 0)` tuples can
therefore become `confirmed_self`; unequal zero/nonzero observations can become
`foreign`, although neither proves ownership. A zero-inode exact-target canary
returned `origin=confirmed_self` and `target_presence=present` even though the
identity evidence was explicitly unavailable.

Presence and ownership are also unnecessarily coupled by `_presence_of()` at
`:1703-1709`: a successful no-follow stat with an unusable inode proves that a
name is present even though its origin remains unknown. It currently maps that
combination to unknown/unknown.

The successor protocol must keep the axes orthogonal: successful lstat/open
evidence means present; any zero inode in the staged or observed identity means
origin unknown; and no self/foreign ownership claim may be derived from a zero
identity. Pin both terminal lstat and read-handle fstat zero-inode cases.

### P2 - Origin and presence policy bypass the frozen authority snapshot

The F-AUTH contract at `p5_r4_sidecar.py:235-257` says every name encoding an
accept/reject decision is frozen at import. `_SidecarAuthority` at `:259-307`
contains terminal disposition and decision labels but not `_ORIGIN_*` or
`_PRESENCE_*`. `_final_origin`, `_presence_of`, terminal refresh, and the
`committed_here` predicate at `:1943-1951` all read those live globals.

An exact-target pre-call canary rebound `_ORIGIN_SELF` to `foreign` and
`_PRESENCE_PRESENT` to `absent`. A normal publication returned:

```text
disposition       integrity_verified
origin            foreign
target_presence   absent
committed_bytes   2920
final path        present
```

The public seam compares literal origin/presence strings and therefore remains
fail-closed in this case; this is P2 receipt corruption rather than P1 false C1
authorization. It is still directly inside the source's declared frozen-policy
contract. Add the origin/presence labels to the frozen authority and use that
snapshot throughout classification, receipt construction, and seam evaluation.
Pin both pre-call and callback-time rebinds.

### P3 - The seam does not independently require committed-byte evidence

The seam at `p5_r4_sidecar.py:2094-2097` requires verified, self, present, and
C1-permitted, but not `committed_bytes > 0`. The current concrete publisher
couples the clean state to positive bytes, so no natural exploit was reproduced.
A synthetic private-publisher result can nevertheless produce `ok=True` with a
zero-byte receipt. Add the committed-byte conjunct and a direct regression if
the successor protocol retains this multi-field receipt.

### P3 - Provenance and test prose need small corrections

The boundary comment attributes keeper ratification to `#1217/#1219`; the
actual compressed successor and stop rule is Watercooler `#1220`. The comment
in `test_rev16_receipt_link_no_effect_unknown_reports_zero_bytes` says the
expected presence is unknown while its final assertion correctly expects absent
after the readback open proves ENOENT. Correct both when the protocol moves.

Adding the trailing defaulted `target_presence` field caused no reproduced ABI
regression for older positional construction.

## Accepted Work and Boundaries

The following rev-16 work is accepted and must be preserved if the protocol is
retained:

- clean verified/self/present publication reports positive committed bytes;
- ordinary foreign and absent terminal observations refresh both receipt axes;
- non-green publication reports zero committed bytes;
- raised-link UNKNOWN, independent read-handle link count, seam origin, seam
  presence, terminal foreign/absent, open ENOENT, and clean-positive branches
  have direct regressions;
- the acquisition prose now accurately names the pre-return `mkstemp`/`Path`
  and repeated-`BaseException` windows as best-effort, non-authorizing limits.

Laura's selected boundaries remain accepted residuals rather than findings:

- no durable receipt/recovery after interruption or sudden power loss;
- no complete defense against an arbitrary same-principal namespace mutator;
- no guarantee beyond the last trusted observation;
- the already named no-follow/open, identity/unlink, persistent-interruption,
  and pre-return acquisition windows.

These boundaries do not excuse false statements about evidence already observed
inside the implemented state machine.

## Verification

- official five-file model-free suite: `532 passed, 1 skipped`
- disposable exact-target receipt canaries: descriptor-side ENOENT,
  zero-inode identity, and live-label rebind all reproduced
- independent bounded acquisition/stop-rule review: `GREEN`
- independent state-machine review: `CHANGES`
- independent contract/authority review: `CHANGES`
- Ruff: clean
- `py_compile`: clean
- forbidden-import/zero-model check: clean
- scoped diff check: clean
- no B0 forward, C1 action, protected-sink publication, deployment, model/GPU,
  or remote-compute action occurred

## Stop-Clause Disposition

This is the one fresh exact-source review authorized by Watercooler #1220. It
reproduces in-scope P2 false receipt claims, so the stop clause is active:

1. do not request or implement rev 17 under Task #155;
2. keep #155 blocked and all operational holds unchanged;
3. create a separate filesystem-protocol design task with a frozen contract
   before any implementation;
4. decide there whether to narrow the receipt guarantee, establish a protected
   namespace/process boundary, or move the custody-critical component to Rust;
5. keep Python for research orchestration and treat process isolation as the
   explicit boundary for non-TEE hostile-runtime behavior.

This review authorizes no B0 run, C1 action, model/GPU use, protected-sink
publication, deployment, or keeper transition. Tasks `#149`, `#156`, `#157`,
the evaluator, sink, and launch gates remain independent and unchanged.
