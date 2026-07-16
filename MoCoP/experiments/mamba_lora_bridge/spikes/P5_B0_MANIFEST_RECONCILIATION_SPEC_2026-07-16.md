# P5 B0 ↔ C1 Manifest/Attempt Contract Reconciliation (spec)

**Status:** rev 2 — §4 RESOLVED by owner ruling; awaiting Codex exact-source review · **Owner:** Gidim
(#156 runner lane) ·
**Closes:** Codex cross-lane finding #693 (Monk ack #697), the "#149 schema reconciliation" hold ·
**Binds to:** `DQ1B_C1_MONITOR_GATE_DRAFT_2026-07-11.md` §7 ·
**Requested by:** keeper, via Gidim's #149 named-seat review (WC #1073).

Sequencing (Monk event-696): this spec commit lands FIRST; the implementation commit lands second
against it; both go to Codex in one review round, spec first. This is a P5 **contract** change.

**Revision history**
- **rev 1** — `58cfb43`, posted for review WC #1076, carrying §4 as an open question for the DQ1b owner.
- **rev 2** — this revision. Incorporates: Techno-Monk's DQ1b-owner ruling on §4 (**WC #1078**,
  reference-only base digest; the provisional (a) marker is withdrawn unimplemented) and Isegrim's
  executable correction to acceptance 5 (**WC #1077**, adopted by that ruling; new §4a). Adds
  acceptance 8 (policy-freeze reach). **No threshold, run authorization, hold, #155 status,
  alpha-zero/nonzero permission, C1 action, or Qdrant path is changed by either revision.**

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
- `base_manifest_digest` — **NOT a base key** (§4 ruling: reference-only). A base carrying it is
  REFUSED as a closed-world unknown key, exactly like `run_kind`. The digest is computed over the
  complete base and carried by the *referrers* — attempts and Stage-B sidecars.
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

**Invariant this buys:** the base `manifest_digest` cannot depend on `run_kind`, because `run_kind` is
no longer a base key — DQ1b §7's Stage A/B sharing property, bought structurally. See §4a for the form
that is executable on the B0 side today and for the part deferred to the C1-capable fixture.

## 4. RESOLVED by DQ1b owner — `base_manifest_digest` is reference-only (b)

DQ1b §7 lists `base_manifest_id + base_manifest_digest` as base-manifest contents. A manifest cannot
contain its own digest without an exclusion rule. The question was put to the DQ1b owner rather than
decided in this lane.

**RULING (Techno-Monk, DQ1b owner, WC #1078): (b) reference-only.** The provisional (a) marker this
spec previously reserved is withdrawn unimplemented.

- The immutable stage-neutral base carries `base_manifest_id` and **NOT** a self-referential
  `base_manifest_digest`.
- The canonical digest is computed over the **complete** base, externally.
- Every B0/C1 attempt and every Stage-B sidecar carries both `base_manifest_id` and
  `base_manifest_digest` as **references**; the verifier recomputes and compares the referenced base.

Rationale of record: this avoids an excluded-self-field rule, preserves the byte-identical Stage-A/B
base, and keeps the audit-chain relationship *referent ← referrer* clear. Isegrim's #1077 lineage
precedent supports it — in the #168 audit chain the digest always lives in the REFERRER (the
successor's `predecessor_digest`), never in the referent, and a self-digest-with-exclusion field hands
every future verifier the exact re-implementation divergence that consumed much of the drift-gate
review. (`report.published_digest` remains house precedent for the (a) pattern; it is not the pattern
for a base that two stages must share byte-identically.)

## 4a. Executable form of the Stage-A/B property (Isegrim #1077, adopted by owner ruling)

Acceptance 5 as originally phrased ("two attempts differing only in `run_kind` yield an identical
`manifest_digest`") is **not exercisable end-to-end on the B0 side today**: the variant applicability
check refuses a non-`b0_baseline` attempt *before* any digest comparison, so a second `run_kind` never
reaches a digest. Asserting it here would be aspirational prose wearing a regression's clothes — the
precise failure this lane exists to stop.

The B0-executable form, which §6.5 now binds:

- **(i)** `manifest_digest` is computed over the base ALONE, before and independent of any attempt
  binding, and contains no `run_kind`.
- **(ii)** a refused-inapplicable attempt leaves the base digest **defined and unchanged**.

The two-variant same-base assertion belongs to the later **C1-capable end-to-end fixture** and is
deferred to it explicitly; it is not claimed as B0-executable today. Note the property is bought
**structurally** rather than by a check: once `run_kind` is not a base key, the base digest cannot
depend on it. The regression pins the structure against reintroduction.

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
2. `base_manifest_id` required and non-placeholder (`_is_unset`-checked), exact-`str`.
3. `run_kind` absent from the base manifest; a base carrying it is refused. Likewise
   `base_manifest_digest` (§4 ruling: reference-only).
4. `run_b0` requires an exact-`str` per-attempt `run_kind`; refuses when inapplicable to the variant.
5. **Stage A/B invariant, B0-executable form (§4a):** (i) `manifest_digest` is computed over the base
   alone, before and independent of attempt binding, and contains no `run_kind`; (ii) a refused
   inapplicable attempt leaves the base digest defined and unchanged. Both get direct regressions.
   The two-variant same-base assertion is DEFERRED to the C1-capable end-to-end fixture and is not
   claimed as B0-executable today.
6. `execution_descriptor` + `claim` bind `schema_variant`, `base_manifest_id`, attempt `run_kind`.
7. All existing custody/authority/allowlist guarantees (§10–§20) preserved; full suite + ruff clean.
8. **Policy-freeze reach (#1011 B1):** the new `schema_variant` authorities join the frozen harness
   policy snapshot; rebinding a published module global must not weaken authorization. The existing
   `B0_RUN_KIND` freeze regression must be re-pointed at the ATTEMPT boundary — after this change a
   base carrying `run_kind` is refused as an unknown key, which would let that test pass vacuously
   while testing nothing.
