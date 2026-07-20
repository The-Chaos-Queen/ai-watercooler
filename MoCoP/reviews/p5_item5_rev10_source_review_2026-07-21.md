# P5 Item 5 Rev 10 Source Review

**Date:** 2026-07-21
**Reviewer:** Codex / Techno-Monk
**Taskboard:** `#155`, item 5
**Review request:** Watercooler `#1208`
**Last exact verdict:** Watercooler `#1201`;
`p5_item5_rev8_source_review_2026-07-20.md`
**Pre-review architecture note:** Watercooler `#1206`
**Baseline:** `37945529916f5488272638f57fd25842253be52d`
**Implementation packet:** `0e4817f11e0d1d87e5e5541b6787594a00b12794`

**Verdict:** `CHANGES` on the exact rev-10 packet.

Rev 10 closes the previously reported mutable-authority, producer-model-shape,
type-name, ordinary hostile-container, custom-`PathLike`, and public `row_keys`
classes covered by its regressions. The exact-container strategy is sound for
dict/list/tuple/scalar evidence once the values have entered `_inert_snapshot`.

Two publication-boundary defects remain P1. An exact stdlib `Path` can still
carry callback-bearing private state and was used to turn a genuine negative
decision into an `integrity_verified` positive artifact. Separately, a real
directory-open durability failure is classified as unsupported and leaves a
committed artifact `integrity_verified`. Three public-surface totality gaps are
also reproducible and should be closed in the same immutable successor.

## Findings

### P1 - Exact stdlib Path objects are active callback carriers

`_SAFE_PATH_TYPES` declares exact stdlib path objects inert, and `_safe_path()`
accepts them (`p5_r4_sidecar.py:450-466`). Exact type identity is insufficient:
an exact `WindowsPath` can be given a callback-bearing `str` subclass in its
private `_raw_paths` list via `object.__setattr__`. The accepted object is then
used by the first filesystem check in publication (`:1561-1562`) and by the
governed-parent loader (`:1680-1685`). Those operations normalize the stored
parts and execute the hostile string method after the supposed callback-free
boundary.

Two independent exact-target probes reproduced the full consequence. The
control evidence was anti-correlated and genuinely decided
`jsd_replacement_required / c1_authorization_permitted=false`. During path use,
the accepted exact `WindowsPath` rebound `_build_decision`. Publication returned
`integrity_verified`, and the committed artifact instead contained:

```text
published_state=jsd_proceeds
published_c1_authorization_permitted=true
```

The rev-10 regression at `test_p5_r4_sidecar.py:1651-1678` covers a custom
`os.PathLike`; it does not cover mutable state inside an exact stdlib path.
Require `type(path) is str` at every caller path boundary and construct a fresh,
owned `Path` internally. Exact `Path` and `PurePath` objects cannot be treated as
inert caller values.

### P1 - Directory-open durability failures are reported as verified

`_fsync_dir()` maps every `os.open(directory, ...)` `OSError` to `None`
(`p5_r4_sidecar.py:1639-1646`). Its caller downgrades only when the result is
exactly `False` (`:1626-1634`), so real supported-platform faults such as `EIO`,
`EMFILE`, or `EACCES` leave the artifact `integrity_verified`. This contradicts
the module and publisher contracts that no durability fault may report ordinary
success (`:29-31`, `:1543-1547`).

A full publisher probe allowed normal staging/linking, then raised `EIO` only
for the directory `O_RDONLY` open. It produced a committed artifact with
`published_disposition=integrity_verified`. The repository's B0 authority
already has the correct capability split: `_fsync_parent()` skips directory
sync only when `os.O_DIRECTORY` is absent and otherwise propagates both open and
sync faults (`p5_b0_run.py:968-975`). The sidecar's non-throwing terminal may
return `committed_indeterminate`, but `None/unsupported` must be selected from
platform capability, not from an arbitrary runtime `OSError`.

### P2 - The public eligible-probe validator is neither typed nor total

`validate_comparison()` snapshots `eligible_probe_ids` but does not validate its
root or element schema (`p5_r4_sidecar.py:994-1012`). `_validate_comparison()`
then feeds it directly to `set()` and `sorted()` (`:1033-1039`). Exact-target
probes with the canonical empty aggregate produced:

```text
eligible_probe_ids=[[]]          -> raw TypeError: unhashable type: 'list'
eligible_probe_ids="a"           -> [] (false clean)
eligible_probe_ids={"a": "x"}    -> [] (false clean)
eligible_probe_ids=[1]           -> [] (false clean)
eligible_probe_ids=["a", "a"]    -> [] (duplicates silently collapsed)
```

Internal parent-aware calls supply a trusted tuple, so this does not provide a
C1 bypass. It does violate the exported self-check's typed-refusal contract.
Before set construction, require an exact list/tuple root, exact string values,
and uniqueness; otherwise return a typed refusal.

### P2 - Accepted exact integers can escape canonicalization untyped

`_inert_snapshot()` accepts every exact integer without a serialization-safe
bound (`p5_r4_sidecar.py:414-423`). Downstream diagnostics and canonical JSON
then stringify those values. A `record_count=10**5000` report escaped
`verify_sealed_report()` as Python's raw integer-string `ValueError`; a
`parent.sequence_length=10**5000` manifest likewise escaped
`build_r4_sidecar()` before a typed sidecar result.

Bound integer fields before formatting/canonicalization and translate any
canonical JSON `ValueError` into `R4SidecarError`. Rejection diagnostics must
also avoid unbounded `repr()` of an otherwise exact integer.

### P2 - Three exported helpers still traverse raw caller containers

`derive_generation_corpus_digest()` (`p5_r4_sidecar.py:826-848`),
`partition_eligibility()` (`:860-886`), and the public correlation helpers
(`:907-927`) operate directly on their arguments. Hostile exact-target probes
rebound their live helper authorities during `.get()`, iteration, or arithmetic;
one caused `derive_generation_corpus_digest()` to return an attacker-selected
digest, and another escaped a raw caller `RuntimeError`. Independently, empty
correlation inputs escape as raw `ZeroDivisionError`, while unequal lengths
such as two JSDs and one similarity silently return a numeric rho instead of a
typed shape refusal.

The governed verdict paths call these helpers with already-owned data, so no
internal C1 bypass was reproduced through this class. The implementation must
either give each exported entry a sanitizing wrapper over a private owned-data
helper, including exact finite numeric sequence and equal nonzero-length checks,
or make these functions explicitly private and document that only the sanitized
public boundaries are supported. The rev-10 claim that every public entry
sanitizes before caller code is otherwise false.

## Accepted Scope

- Exact dict/list/tuple inputs, their subclasses, ABC mappings,
  `MappingProxyType`, hostile nested containers, non-exact scalar leaves, and
  custom `os.PathLike` values were exercised. Rejected carriers did not fire
  their callbacks.
- The complete frozen authority closure, threaded decision authority, exact
  producer model descriptor, internal-only row shape, and removed public
  `row_keys` knob pass their checked-in regressions.
- The exact-path exploit is distinct from those accepted cases: the root type
  is a permitted exact stdlib class but its internal state is not inert.
- Existing custody, eligibility re-derivation, canonical numeric spelling,
  no-replace publication, and zero-torch architecture remain intact outside the
  findings above.

## Exact Provenance

Final rev-10 target `0e4817f11e0d1d87e5e5541b6787594a00b12794`:

- baseline: `37945529916f5488272638f57fd25842253be52d`
- parent: `b87c8b88a0413d66a7f7a52d596a83ec243721cd`
- tree: `ae2c0b9d9a537a2ee013880ebe63dd4c49272053`
- `p5_r4_sidecar.py`: `615baea8333594a818a337aa978587356147972c`
- `test_p5_r4_sidecar.py`: `4795e8be186072e9eddf83c35f8c79494b5f0808`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- R4 comparison contract: `96809822137399344ff4c1f3889815a65538ce1d`
- scoped baseline-to-target diff: two files, 1,051 insertions and 206 deletions

The reviewed commit range also contains interleaved World Model and continuity
work. This verdict covers only the two named R4 source/test blobs above.

## Verification

- immutable `git archive` of
  `0e4817f11e0d1d87e5e5541b6787594a00b12794`
- five-file model-free P5 suite: `482 passed, 1 skipped in 3.77s`
- focused Ruff, `py_compile`, zero-torch import, and scoped
  `git diff --check`: clean
- two independent exact-path reproductions plus root publisher, validator, and
  integer-totality canaries reproduced every finding above
- no model, GPU, remote host, B0 forward, C1 actuation, Qdrant project-state
  write, protected sink, deployment, or keeper action occurred

## Disposition

Rev 10 remains review-held. Preserve the accepted authority and exact-container
repairs, then return one immutable successor that accepts only exact strings at
path boundaries, truthfully downgrades every supported-platform directory-open
or sync fault, and makes each supported public helper typed and callback-free.

This review authorizes no B0 run, C1 action, model/GPU use, protected-sink
publication, deployment, or keeper transition. Task `#155` and all independent
`#149`, `#156`, `#157`, evaluator, sink, and launch holds remain unchanged.
