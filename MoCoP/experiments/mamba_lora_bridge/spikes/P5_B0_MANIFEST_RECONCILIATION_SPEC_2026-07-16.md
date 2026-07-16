# P5 B0 ↔ C1 Manifest/Attempt Contract Reconciliation (spec)

**Status:** DRAFT for Codex/Monk review · **Owner:** Gidim (#156 runner lane) ·
**Closes:** Codex cross-lane finding #693 (Monk ack #697), the "#149 schema reconciliation" hold ·
**Binds to:** `DQ1B_C1_MONITOR_GATE_DRAFT_2026-07-11.md` §7 ·
**Requested by:** keeper, via Gidim's #149 named-seat review (WC #1073).

Sequencing (Monk event-696): this spec commit lands FIRST; the implementation commit lands second
against it; both go to Codex in one review round, spec first. This is a P5 **contract** change.

---

## 1. Why

DQ1b §7 defines a **stage-neutral immutable base manifest**, with this binding note:

> *run_kind is excluded from the immutable base manifest; it must be supplied per-attempt to permit
> Stage A and Stage B to share the exact same base manifest.*

The current `p5_b0_harness` contradicts that contract:

| DQ1b §7 requires | `p5_b0_harness` at HEAD (`c17f6d8`) |
|---|---|
| base manifest is stage-NEUTRAL | `REQUIRED_B0_KEYS` includes `run_kind`; `validate_b0_manifest` refuses unless `manifest["run_kind"] == "b0_baseline"` |
| `run_kind` supplied PER-ATTEMPT | `run_kind` is a base-manifest key, hashed into `manifest_digest` |
| `schema_variant = closed_world_b0 \| closed_world_c1` | absent (only `schema_version`) |
| `base_manifest_id` + `base_manifest_digest` | absent |

This is not cosmetic. Because `run_kind` is hashed into the base, a Stage-A (`c1_alpha_zero`) and a
Stage-B (`c1_nonzero`) attempt **cannot share a byte-identical base manifest** — which is precisely
the property DQ1b §7 exists to guarantee, and which the Stage-B sidecar rule
("references the *unchanged* base manifest") depends on. The B0 harness as built structurally
cannot host the Stage A/B chain. Gidim's #149 runnability seat cannot sign a numeric freeze bound to
a manifest contract the runner contradicts.

## 2. Contract (B0 side)

The pre-run **base manifest** becomes stage-neutral and gains a discriminated variant + base identity:

- `schema_variant` — closed-world union, exactly one of `closed_world_b0` | `closed_world_c1`.
  A `closed_world_b0` manifest MUST NOT carry C1 actuator/direction/GO fields; the existing
  closed-world unknown-key refusal already rejects them, and the variant makes the intent explicit
  and drives which required-key set applies.
- `base_manifest_id` — a non-placeholder stable identifier for this base.
- `base_manifest_digest` — see §4 (OPEN QUESTION; not invented here).
- `run_kind` — **REMOVED** from the base manifest and from `REQUIRED_B0_KEYS`. A base manifest that
  still carries `run_kind` is REFUSED (closed-world unknown key), so a stage-specific base cannot be
  smuggled through.

## 3. Per-attempt run kind

`run_kind` moves to the **attempt** boundary:

- `run_b0(..., run_kind=...)` becomes a required, exact-`str` per-attempt binding (subject to the
  existing #1011 exact-type scalar normalization: an equality-overriding subclass is refused).
- The runner REFUSES unless `run_kind == "b0_baseline"` for a `closed_world_b0` base — i.e. the
  applicability check DQ1b §7 asks for ("refuse … if the per-attempt run-kind field is inapplicable"),
  now enforced against the *variant* rather than against a base-manifest field.
- The journal `claim` frame continues to carry `run_kind` (already exact-schema bound, §18) — its
  value now provably comes from the attempt, not from the hashed base.
- The `execution_descriptor` binds `schema_variant`, `base_manifest_id`, and the attempt `run_kind`,
  so a report states which base it ran and which stage it was, without the base being stage-specific.

**Invariant this buys:** two attempts with different `run_kind` MUST produce the identical
`manifest_digest`. That is the executable statement of DQ1b §7's Stage A/B sharing property, and it
gets a direct regression test.

## 4. OPEN QUESTION for Monk/Codex — `base_manifest_digest` semantics

DQ1b §7 lists `base_manifest_id + base_manifest_digest` as base-manifest contents. A manifest cannot
contain its own digest without an exclusion rule. Two readings, and I will **not** pick one
unilaterally — this is a shared B0/C1 contract field:

- **(a) self-digest with excluded field** — `base_manifest_digest = canonical_digest(base minus
  base_manifest_digest)`, the pattern already used for `report.published_digest`. Gives the base a
  self-verifying identity.
- **(b) reference-only** — the base carries only `base_manifest_id`; `base_manifest_digest` is what
  *attempts/Stage-B sidecars* carry to reference the unchanged base (the digest lives in the
  referrer, not the referent).

(b) reads more naturally against "a Stage-B release is an append-only sidecar referencing the
unchanged base manifest", but (a) matches the literal "base manifest must include". **Monk's call**
(DQ1b owner); Codex to confirm. Until answered, the implementation lands (a) behind an explicit,
reviewable marker and the spec records that it is provisional — no numeric or launch consequence
either way.

## 5. Out of scope / unchanged

C1-side required keys (condition key, direction artifact digest, Stage-A/B GO records, the final
numeric gate values, recovery spans, …) are **not** implemented here: they are the C1 lane's, and the
numerics are B0-dependent per keeper decision 2026-07-11 and DQ1b §219. This spec reconciles only the
B0 harness to DQ1b §7's *base/attempt* shape.

This changes NO threshold, authorizes NO run, and lifts NO hold: not #155, not a B0 run, not #149's
numeric ratification, not #157/#158, not alpha-zero, not any nonzero intervention. It removes ONE
structural blocker (the manifest contract) so the seats can be worked in the correct order:
reconcile → nonnumeric freeze + `T_control` seat → #155 B0 review → baseline runs → numerics.

## 6. Acceptance

1. `schema_variant` required, closed-world union, exact-`str`; unknown/absent/placeholder refused.
2. `base_manifest_id` required and non-placeholder (`_is_unset`-checked).
3. `run_kind` absent from the base manifest; a base carrying it is refused.
4. `run_b0` requires an exact-`str` per-attempt `run_kind`; refuses when inapplicable to the variant.
5. **Stage A/B invariant:** two attempts differing only in `run_kind` yield an identical
   `manifest_digest` (regression test).
6. `execution_descriptor` + `claim` bind `schema_variant`, `base_manifest_id`, attempt `run_kind`.
7. All existing custody/authority/allowlist guarantees (§10–§20) preserved; full suite + ruff clean.
