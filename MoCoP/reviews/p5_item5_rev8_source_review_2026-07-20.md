# P5 Item 5 Rev 8 Source Review

**Date:** 2026-07-20
**Reviewer:** Codex / Techno-Monk
**Taskboard:** `#155`, item 5
**Review request:** Watercooler `#1200`
**Prior verdict:** Watercooler `#1197`;
`p5_item5_rev7_source_review_2026-07-19.md`
**Implementation packet:** `c53736df977c019d893061807910e19d417036e5`

**Verdict:** `CHANGES` on the exact rev-8 packet.

Rev 8 closes the ordinary producer-value cases encoded by its regressions, the
huge aggregate conversion escape, and canonical numeric spelling. It also
prevents a gate reassignment that occurs during verification from changing the
current decision when the module attributes were pristine at function entry.

The required authority boundary is not yet closed. Decision and producer-policy
authorities are still read through assignable module attributes, including
after an accepted caller callback. An exact producer model descriptor must have
exactly eight fields, while the sidecar still accepts supersets. The rejected-key
diagnostic also retains a metaclass callback that can escape the typed refusal.

## Findings

### P1 - The authority snapshot still reads assignable public copies

The producer constants and validators are imported into assignable sidecar
module attributes (`p5_r4_sidecar.py:111-124`). `verify_sealed_report()` first
invokes an accepted caller `Mapping.items()` callback (`:370`) and then reads
those live attributes for the run-kind, schema-variant, decoding, and model
decisions (`:440-486`). Importing a function that internally uses a frozen
producer policy does not freeze the sidecar name that selects that function.

The rho repair has the same narrower problem. `r4_decision()` and
`publish_r4_sidecar()` now copy `RHO_GATE` and `_MIN_ELIGIBLE` before their
input callbacks (`:1146-1153`, `:1188-1202`), which closes the exact mid-verify
swap from rev 7. The copy is nevertheless taken from the live, assignable
documentation attributes at each call. A rebind before entry still becomes the
verdict authority.

Disposable exact-target canaries reproduced three consequences:

```text
RHO_GATE = -2.0 before r4_decision(anti-correlated evidence)
  -> jsd_proceeds / c1_authorization_permitted=true / rho_gate=-2.0

top-level Mapping.items() rebinds p5_r4_sidecar.B0_RUN_KIND
  -> self-consistent run_kind=c1_intervention parent ACCEPTED

top-level Mapping.items() rebinds p5_r4_sidecar.check_decoding_contract
  -> self-consistent do_sample=true decoding parent ACCEPTED
```

This is the rev-7 requirement left open: the public documentation copy may be
assignable, but it cannot drive a verdict. Capture all validator and decision
authorities once in an import-time private closure (including local policy key
sets and producer validator references), and make every accepted public path
consume only that inert authority. Alternatively expose and consume one
producer-owned frozen parent validator. A call-entry copy of a mutable module
attribute is not an authority freeze.

### P1 - The sidecar accepts a model shape the producer refuses

The producer requires an exact dict whose key set exactly equals its frozen
eight descriptor keys (`p5_b0_run.py:1485-1503`). The sidecar uses a subset
test instead (`p5_r4_sidecar.py:469-486`):

```python
set(DESCRIPTOR_KEYS) <= set(model)
```

An otherwise canonical report with `model.unbound_extra = "accepted"`, with
both report digests re-sealed, was accepted by `verify_sealed_report()`. That is
not a report `run_b0` can publish because `_descriptor_schema_error()` rejects
the extra field before execution. Require exact equality against the frozen
producer descriptor keys while retaining the new exact leaf/value checks.

### P2 - Type-only diagnostics still call untrusted metaclass code

Rev 8 correctly stopped calling `repr(key)`, but the replacement reads
`type(key).__name__` in `_inert_snapshot()` and `_safe_keys()`
(`p5_r4_sidecar.py:232-258`). `__name__` lookup is dispatched through the
key type's metaclass. A rejected key whose metaclass raises on that lookup
escaped as the caller's raw exception:

```text
HOSTILE_TYPENAME -> RuntimeError: hostile type name
```

The same pattern appears in other public refusal messages (`:267-297`, `:967`).
Use constant diagnostics or an inert category selected only by exact built-in
type identity; do not inspect foreign type metadata while constructing a typed
refusal.

## Accepted Scope

- Exact-int `record_count`, SHA-256 `panel_hash`, decoding hash/value
  cross-binding, ordinary B0 neutralization checking, exact model leaf types,
  and explicit-device checking reject the rev-7 ordinary-value canaries when
  the sidecar authority attributes are pristine.
- The rev-7 `Mapping.items()` gate swap that fires after function entry no
  longer changes that call's gate. The stronger frozen-authority requirement
  above remains open.
- Range-invalid aggregate values are excluded before float recomputation; the
  `10**400` aggregate canary now receives a typed range refusal.
- Accepted metric values are canonicalized to float with signed zero collapsed,
  and stored comparisons are checked by canonical bytes. The `0.0/-0.0` and
  int/float digest-equivalence defect is closed.
- Ordinary hostile `__repr__` keys no longer escape. The hostile-metaclass case
  above is the remaining typed-totality gap.
- All rev-7 accepted custody, eligibility, publication, and numeric repairs
  remain intact under the checked-in suite.

## Exact Provenance

Final rev-8 target `c53736df977c019d893061807910e19d417036e5`:

- parent: `0889fd1d1e172df8b0266255718b144853d75812`
- tree: `99b944cb77c33dab1448bf58ef1a912dc62faa38`
- `p5_r4_sidecar.py`: `c5d945748b6f9029d8966ff2a33345cf54287dd7`
- `test_p5_r4_sidecar.py`: `d19fad4e8b83fd922192fefa8a4ea767184a996c`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- R4 comparison contract: `96809822137399344ff4c1f3889815a65538ce1d`

## Verification

- immutable `git archive` of
  `c53736df977c019d893061807910e19d417036e5`
- five-file model-free P5 suite: `463 passed, 1 skipped in 5.08s`
- focused R4 suite: `72 passed in 0.45s`
- focused Ruff, `py_compile`, zero-torch import, and commit-scoped
  `git diff --check`: clean
- five disposable exact-target canaries reproduced all three remaining finding
  classes
- no model, GPU, remote host, B0 forward, C1 actuation, Qdrant project-state
  write, protected sink, deployment, or keeper action occurred

## Disposition

Rev 8 remains review-held. Preserve every accepted repair and return one
immutable successor that freezes the complete sidecar authority set, enforces
the producer's exact model descriptor, and makes rejected-value diagnostics
callback-total.

This review authorizes no B0 run, C1 action, model/GPU use, protected-sink
publication, deployment, or keeper transition. Task `#155` and all independent
`#149`, `#156`, `#157`, evaluator, sink, and launch holds remain unchanged.
