# P5 B0 Runner — Reviewed-Scorer Allowlist Contract (spec amendment)

**Status:** DRAFT for Codex/Monk review · **Owner:** Gidim (#156 runner lane) ·
**Requested by:** Laura · **Endorsed (with six conditions):** Isegrim, WC #990 ·
**Supersedes:** the runtime scorer-identity machinery in `p5_b0_run.py` at `46765b8`.

Sequencing (Monk event-696 discipline): this spec commit lands FIRST; the implementation
commit lands second against it; both go to Codex in one review round, spec first. This is a
P5 **contract** change, not a patch — architectures are not swapped inside a fix commit.

---

## 1. Why (the theorem-shaped fact)

Nine review rounds (#960→#980→#987) produced the same blocker in a dozen coats: you cannot
cryptographically bind the identity of an **arbitrary caller-supplied Python callable**.
`inspect.getsource` fails on eval'd code; `globals()['STATE']` / `getattr` route around any
static `co_names` scan; `isinstance` admits stateful subclasses; and behind those wait
`__class__` swaps, `sys.modules` shadowing, C-extension state, and hash-time/call-time TOCTOU.
Rounds 6 and 9 taught it from opposite ends: `repr` is not identity, `isinstance` is not
identity — **identity is not a runtime property in this language; it is a review property.**

The fix is the authority move, not a better hash: **stop verifying arbitrary code; only
reviewed code exists.** For a read-only B0 baseline there is no legitimate caller-supplied
scorer — the baseline scorer is a fixed null-estimator by definition. This mirrors the drift
gate's aggregation-kernel correction (#979/#984: structure verified in-kernel, authority pinned
to reviewed artifacts) and the runner/OS custody split drawn in #971.

## 2. The allowlist artifact (Condition 4: reviewed, committed)

A committed file `scorer_allowlist.json` (git-tracked, alongside the runner). Adding or changing
a scorer is a **commit + Codex review**, exactly like the protected-sink attestation. There is
NO runtime-mutable allowlist and NO env-var override (Condition 3: no back door).

```json
{
  "schema_version": "b0_scorer_allowlist_v1",
  "scorers": [
    {
      "scorer_id": "b0_null_estimator",
      "version": "1",
      "module_path": "b0_scorers/null_estimator.py",
      "entrypoint": "score",
      "blob_sha256": "<sha256 of the module FILE bytes as committed>",
      "review_ref": "<wolf-Codex message id that GREENed this scorer>"
    }
  ]
}
```

The **allowlist digest** = `canonical_digest` of the parsed allowlist object.

## 3. Manifest binding

The manifest `scorer` block pins the reviewed scorer by ID+version and the allowlist it was
drawn from — never a caller code digest:

```json
"scorer": {"scorer_id": "b0_null_estimator", "version": "1", "allowlist_digest": "<hex>"}
```

The runner receives NO caller `scorer` callable. `run_b0` resolves the scorer from the
allowlist; a `scorer=` argument, if the API retains one, is accepted ONLY when it is the exact
object the allowlist load produced (identity check), else refused.

## 4. Load procedure (Condition 1: pin content, not names)

Never import-by-name-then-hash — `sys.path`/`sys.modules` can hand back a different module than
the one hashed. The load is content-first:

1. Read the allowlist file bytes; parse; compute the allowlist digest; refuse unless it equals
   `manifest.scorer.allowlist_digest`.
2. Find the entry whose `scorer_id` + `version` match `manifest.scorer`; refuse if absent
   (Condition 3: no unlisted scorer, no unlisted-but-hashed fallback).
3. Read the module FILE bytes at `module_path`; sha256; refuse unless it equals the entry's
   `blob_sha256`.
4. Compile the verified bytes and `exec` them in a FRESH, isolated namespace (not `import`);
   resolve `entrypoint`; refuse if it is not a plain function.
5. Bind and journal (Section 6).

Any step failing is a pre-run refusal (`ok=False`), zero forwards.

## 5. Review-time properties (Condition 2: not runtime cleverness)

The reviewed scorer module is a frozen artifact whose safety is a REVIEW obligation, frozen by
the content hash. The reviewer (wolf-Codex) checks and the `review_ref` records that the module:

- is stdlib-only (ideally import-free), no third-party/component imports;
- performs no global mutation, no I/O, no network, no filesystem, no clock/entropy;
- is deterministic: `score(probe_id, generation) -> (scorer_input, scorer_output)` pure over
  its inputs, output strict-JSON (`assert_strict_json`).

These properties are NOT re-derived at runtime. The runtime introspection edifice is DELETED:
`_callable_digest`, `_scorer_selfcontained_refusals`, `_is_deeply_immutable`, `_cell_is_mutable`,
the `co_names` scan, and the before/after scorer-digest re-verification all go. Input/output
**schema** checks (`assert_strict_json`, the `(input, output)` shape) are retained as
defense-in-depth only, no longer load-bearing for identity.

## 6. Journal the binding (Condition 5)

The manifest AND the run journal `claim` frame carry `scorer_id@version`, the entry
`blob_sha256`, the `allowlist_digest`, and the `review_ref`, so every run is reproducible and
the review chain (which review GREENed this scorer) is referenceable — the same envelope shape
as the drift gate's `judge_ref`/`rubric_version`.

## 7. Residual boundary (Condition 6: honest scope)

The allowlist collapses the scorer-**identity** class in full. It does NOT make CPython a TEE.
Interpreter/process integrity, a hostile in-process co-thread mutating a loaded function object,
and host environment integrity remain **out of scope** — the same custody split as chain-origin
(#971): kernel verifies integrity; the runner journal records origin; the host/OS owns
environment. This is stated so the allowlist is never mistaken for an attestation it is not.
A resolvable protected-sink attestation, #149 schema reconciliation, and the real HF read-only
audit remain the separate launch holds; the reviewed-scorer allowlist is the mechanism that
retires the scorer-binding review class, not a launch authorization.

---

## 8. Folded-in GPT-5.5 findings (fix regardless of the allowlist)

- **Event sequence grammar.** `_KNOWN_EVENTS` is an allowlist of event TYPES; valid types in an
  invalid ORDER (double `sealing`, terminal-before-`claim`) can pass. Promote to a full sequence
  grammar over the per-probe `attempt→generated→recorded` cycle bounded by `claim`/`sealing`/
  terminal, and retire `_KNOWN_EVENTS` as an identity check.
- **Terminal binds `report_bytes_sha256`.** The committed terminal frame carries
  `report_bytes_sha256` but nothing binds it. An artifact the verdict depends on must be inside
  the verified set (Monk #984 blocker-2): `verify_terminal_frames`, given the committed report
  bytes, must require the terminal frame's `report_bytes_sha256` to equal their sha256.

## 9. Deletion / retention summary

DELETE (identity-by-runtime-introspection): `_callable_digest`, `_scorer_selfcontained_refusals`,
`_is_deeply_immutable`, `_cell_is_mutable`, `_IMMUTABLE_ATOMS`, the co_names/globals scan, the
per-probe scorer-digest re-verification, `manifest.scorer.code_digest`.

RETAIN (structure + defense-in-depth): `assert_strict_json`, the `(input, output)` shape check,
the import-sentinel around the loaded scorer CALL (a reviewed pure scorer imports nothing, so a
sentinel trip is a review-contract violation and fails closed), and reachability checks.

ADD: `scorer_allowlist.json`, the content-first loader, the manifest `scorer` allowlist binding,
the journal binding, the event sequence grammar, the terminal `report_bytes_sha256` binding.

---

## 10. Codex #1000 review corrections (round 2, verdict CHANGES on 7f9b66c+b0983d7)

Codex accepted the authority move and issued a bounded module-only GREEN of
`b0_scorers/null_estimator.py` (raw sha256 `977eb558…f9e`), usable as the scorer `review_ref`
(= `wc#1000`). Three blockers on the contract/impl, all folded here:

- **B1 — no runtime authority back door (restores Condition 3).** The governed entrypoint
  `run_b0` must expose NO allowlist path; a caller-supplied allowlist + a caller-supplied
  `allowlist_digest` prove agreement, not review. The public `allowlist_path` parameter is
  REMOVED; the loader reads only the single committed `scorer_allowlist.json`. An entry's
  `module_path` is resolved ONLY relative to that committed allowlist's own directory —
  absolute paths and `..` traversal out of it are refused — so an entry cannot point the loader
  at arbitrary caller code. Test injection lives BELOW the entrypoint (repoint the committed
  path), never through a public argument.
- **B2 — order is not a full event contract (restores the omitted half of the GPT-5.5 finding).**
  Beyond ordering, `verify_terminal_frames` binds each cycle's per-event SCHEMA and IDENTITY:
  `attempt`/`generated`/`recorded` each REQUIRE a typed `attempt_id` (non-empty str), `ordinal`
  (int, not bool), and `probe_id` (non-empty str); `generated` also requires `generation_sha256`;
  the three frames of one cycle must AGREE on `(attempt_id, ordinal, probe_id)`; and `ordinal`
  runs monotonically `0,1,2,…`. A well-ordered cycle whose frames disagree on their ids/ordinal
  is rejected. The legitimate pre-publication `sealing → failed` path is preserved.
- **B3 — an unresolved review authority must not execute.** The loader locally REFUSES an
  `entry.review_ref` that is empty/`TBD`/`PENDING` (journaling it is not clearing it). The
  external resolvable-attestation hold still stands; this is the local half. The committed
  allowlist's `review_ref` is set to `wc#1000` (Codex's bounded module GREEN of the exact bytes).

Unchanged residual: this still collapses scorer-IDENTITY only, not process/interpreter/host
integrity (CPython is not a TEE, custody split per #971); #149 schema reconciliation, the real
HF read-only audit, and the resolvable protected-sink attestation remain independent launch holds.

Note (module_path): §2's `module_path` is relative to the COMMITTED ALLOWLIST's own directory
(`b0_scorers/null_estimator.py`), not repo-relative. The §2 example is corrected accordingly.

---

## 11. Codex #1003 review corrections (round 3, CHANGES; GPT-5.5 cross-check confirmed at #1004)

Round 2 fixed the *named* holes and left the *shape* of both. Codex (and an independent GPT-5.5
Extra-High pass) found the same two residuals with matching line-level reasoning.

- **B1 — the authority knob moved, it did not close.** Removing the `run_b0(allowlist_path=…)`
  parameter is not enough while `DEFAULT_ALLOWLIST_PATH` remains an **exported, assignable module
  global that the loader dereferences at call time** — and the round-2 positive integration test
  reassigned it to run a temporary scorer (canary: `mutable_default_override → integrity_verified`).
  A path-*selection* global IS an alternate governed authority; it is not merely "hostile
  interpreter mutation" and does not fall under the CPython-is-not-a-TEE residual.
  **Contract:** the governed allowlist path is **derived INTERNALLY**, inline from the runner
  module's own `__file__`. There is NO module-level allowlist-path global — no knob to reassign.
  `run_b0` never selects an allowlist. The loader retains an `allowlist_path` argument for LOADER
  UNIT TESTS ONLY (they sit below the governed entrypoint); **governed `run_b0` integration tests
  MUST exercise the committed scorer** — a test seam that substitutes the scorer through the
  governed path would BE the back door, so the round-2 tests that did so are deleted, and the
  strict-JSON scorer-evidence invariant is tested where it actually lives (the evidence bundle).

- **B2 — the exact-schema requirement was narrowed to a subset.** Identity-trio + monotone ordinal
  is not the repair. Every governed frame now has an **EXACT field set**: required fields present
  and well-typed, and **no extra fields** (arbitrary extra keys are how a co-writer smuggles state
  past a name-only checker). Specifically:
  - `claim` binds `run_id`, `run_kind` (== `b0_baseline`), `manifest_digest`,
    `execution_descriptor_digest`, `utc`, and a fully-bound `scorer_binding`
    (`scorer_id`/`version`/`blob_sha256`/`allowlist_digest`/`review_ref`, the latter resolved).
  - `attempt`/`generated`/`recorded` require `attempt_id`/`ordinal`/`probe_id` (+ `prompt_sha256`;
    + `generation_sha256`/`generation`), the three frames of a cycle must AGREE on the trio, the
    ordinal is monotone from 0, and **`attempt_id` must be run-DERIVED (`{run_id}:{ordinal}`)**.
  - `sealing` requires `published_digest` + `journal_digest_prefix`; a committed terminal requires
    `disposition` + `published_digest` + `report_bytes_sha256` + `durability_warnings` — **all
    digest fields unconditional and sha256-shaped** (an empty or absent digest is not a digest).
  - `failed` (the legitimate pre-publication `sealing → failed` path) is preserved and must carry
    `error_type`/`error` and **no** `disposition`.

Both #1003 canaries are re-run against the fix and refused: `mutable_default_override` has no
knob to turn, and `underspecified_exact_schema` / `attempt_id_not_run_derived` are rejected.

---

## 12. Codex #1006 review corrections (round 4, CHANGES on 6f874ee+4394e32)

Three blockers. B1 is the SAME defect class for the third consecutive round, one level lower each
time — the standing lesson is now explicit in the contract:

> **An authority must never be a call-time dereference of ANY assignable module attribute —
> dunders included.** Deleting a named global is not enough if the replacement reads `__file__`.

- **B1 — the governed authority and the runner receipt followed assignable `__file__`.** Round 3
  derived the allowlist path inline from `__file__` at call time, and `_runner_digest` read the
  same global independently. `__file__` is an ordinary assignable module attribute: assigning
  `p5_b0_run.__file__` selected BOTH a sibling temporary `scorer_allowlist.json` AND the runner
  bytes whose digest the manifest must match — so a reviewed-scorer lookalike with top-level
  filesystem I/O executed through governed `run_b0` and still reported success (canary:
  `mutable_dunder_file_override`). This needed no function replacement, no bytecode mutation, no
  reflective write. The round-3 guard test explicitly skipped dunder globals and was therefore
  structurally blind to the authority it relied on.
  **Contract:** the runner ORIGIN is resolved **once, at import, into a CLOSURE CELL**
  (`_bind_runner_origin`). There is no module-level path DATA attribute to reassign, and a later
  `__file__` assignment cannot move the authority. The governed allowlist path AND the runner
  receipt both hang off that single frozen origin. A governed integration canary must assign
  `p5_b0_run.__file__` and prove neither the selected allowlist nor `_runner_digest()` changes.

- **B2 — a journal claim could restore an unresolved scorer review reference.** The loader refused
  `review_ref="PENDING-codex"`, but the standalone terminal-protocol verifier typed the claim's
  nested `scorer_binding.review_ref` as merely a non-empty string, so a fully schema-complete
  journal carrying it passed (canary: `pending_claim_review_ref`).
  **Contract:** ONE unresolved-reference predicate (`_is_unresolved_ref`) is shared by the loader
  AND the journal verifier — they cannot drift. Empty / `TBD` / `PENDING-*` claim bindings are
  refused by both. The external resolver remains a separate launch hold.

- **B3 — sealing and terminal publication identities were not mutually bound.** The exact schemas
  made both `published_digest` fields mandatory and sha256-shaped, but never compared them; they
  were only checked against the OPTIONAL `report_published_digest` argument. Without it, a sealing
  frame with one valid digest and a committed terminal with a different valid digest passed
  (canary: `mismatched_publication_digests`).
  **Contract:** the executable terminal protocol ALWAYS requires the committed terminal's
  `published_digest` to equal the preceding sealing frame's. An expected report digest may
  additionally bind both to the report bytes, but its absence can never permit the journal's two
  receipts to attest different publications.

All three #1006 canaries are re-run against the fix and refused.

---

## 13. a-Fable adversarial pass — the fifth defect, self-found before the round-4 verdict

Provenance: an ANONYMOUS Fable adversarial review (substrate capability, unattested — not
wolf-Isegrim), run by Gidim after relaying round 4 (WC #1007) and before Codex's round-4 verdict.
One real blocker + two correctness notes, all reproduced independently before fixing.

The scorer-execution authority (R1–R4) held — the Fable could not break it. But it found the
R4 lesson had been applied to the scorer/runner origin and **not** to the OTHER core B0 promise,
the no-component runtime guarantee, which was still wired to assignable module globals exactly the
way R3/R4 taught against. The standing rule (§12) is now enforced across BOTH guarantees.

- **BLOCKER — the no-component guard read assignable module globals at call time.** The
  reachability lookup dereferenced `FORBIDDEN_ROUTE_MODULES` (a dict) live, and the transient-import
  sentinel trusted `_audit_installed` (a bool) and appended to `_forbidden_imports` (a list) — all
  in-scope data attributes. `p5_b0_run.FORBIDDEN_ROUTE_MODULES = {}` (or an in-place `.clear()`)
  blanked the reachability guard; `_audit_installed = True` left the sentinel disarmed while it
  reported armed. Either yields a GREEN `integrity_verified` B0 report while a forbidden component
  is reachable/imported — B0's central guarantee, void and silent.
  **Contract:** freeze the guard's authority at import into closure cells (`_bind_reachability_guard`),
  exactly as R4 froze the runner origin. `FORBIDDEN_ROUTE_MODULES` remains the reviewed PUBLISHED
  inventory, but the guard reads a deep snapshot (new dict of new frozensets) immune to reassignment
  AND in-place mutation; the sentinel's buffer and installed-state are cells with no module-attribute
  handle to blank or spoof. Reassigning the exposed functions is function replacement (out of scope).

- **NOTE — standalone verifier fail-open on a non-string event.** A journal frame with a
  non-hashable `event` (e.g. `{"event": []}`) raised an uncaught `TypeError` in the membership scan
  (and a missing/None event collided with the `next()` sentinel). Inside `run_b0` the post-commit
  reconcile wraps this in `except Exception → indeterminate`, but the independently-verifiable
  auditor path must fail CLOSED. Fixed: iterate and reject any non-string / unknown event.

- **NOTE — `_is_unresolved_ref` over-refused.** The §12 predicate matched the bare substring
  `"pending"`, wrongly rejecting a legitimate ref like `REVIEW-appending-42`. No security loss (it
  only over-refuses), but corrected to a `pending`-PREFIX match; our placeholders are always leading.

All three are reproduced and refused after the fix, including the in-place `.clear()` variant.

---

## 14. Codex #1009 review corrections (round 6, CHANGES on 5a05884+08925d0)

Round 5 closed the scorer/runner-origin and one part of the component guard; Codex (with a GPT-5.5
cross-check) then did the COMPLETE authority sweep the §12 rule implies and found four more. The
rule is now enforced across EVERY verdict authority, not surface by surface.

- **B1 — the frozen component guard still leaked erase/authority capabilities.** (i) The closure's
  inventory was RETURNED as the mutable module alias `_FROZEN_FORBIDDEN`, so `.clear()` on that
  name cleared the closure's own dict. (ii) The destructive `_clear`/`_drain` sentinel ops were
  module attributes — code inside a guarded window (a backend) could call them, or trip
  `_drain_and_check` and catch the `B0RunError`, to empty its own import evidence. (iii) the guard
  read the assignable module global `sys`, so a `sys` proxy with an empty `modules` and a no-op
  `addaudithook` hid a resident component.
  **Contract:** the guard factory captures the REAL `sys` module object; the inventory snapshot is
  NEVER returned as an alias; the sentinel is an APPEND-ONLY MONOTONE log with NO exposed clear/
  drain. Accounting is done through a per-run watch holding a PRIVATE local cursor (a run_b0 local
  a backend has no handle to); it only reads the log suffix since its checkpoint and advances its
  own cursor — non-destructive. Cross-run bleed is structurally impossible (nothing is cleared;
  each run inspects only its own suffix), so the clear-era "dirty at entry" refusal is subsumed;
  a component RESIDENT at entry is still caught by the snapshot check.

- **B2 — every OTHER verdict authority was still live module data.** `DESCRIPTOR_KEYS`,
  `_FRAME_SCHEMAS`, `B0_RUN_KIND`, `INTEGRITY_VERIFIED`, `_TERMINAL_DISPOSITION` (and the event
  vocabulary, probe cycle, schema kind-tags, dtype table) could be reassigned or mutated in place
  to blank the descriptor binding, weaken a claim schema, select a caller run-kind, or make a
  caller disposition read `ok=True`.
  **Contract:** ONE complete authority inventory is frozen at import into a closure snapshot
  (`_bind_authority` → `_authority()`), dict-valued members exposed as read-only proxies. The
  governed entrypoint and the standalone verifier rebind the names they need from that snapshot at
  entry, so no verdict is a call-time read of a published module global. The module constants remain
  as published DOCUMENTATION but are not the objects consulted for a verdict.

- **B3 — the authorized manifest/panel stayed caller-mutable.** They were hashed, then a backend
  callback mutated `model.id` / a prompt AFTER hashing and published success under the original
  receipt.
  **Contract:** BEFORE any backend access, `run_b0` rebuilds inert deep snapshots of the manifest
  and panel from EXACT built-in types (`_inert_snapshot`; a dict/list subclass with an overridden
  `items`/`__deepcopy__` is refused, not honored) and authorizes/hashes/validates/journals/executes
  ONLY those. The caller's originals are never read again.

- **B4 — the standalone verifier only shape-checked `journal_digest_prefix`.** A sha256-SHAPED but
  wrong 64-hex value passed.
  **Contract:** `verify_terminal_frames` reads the raw journal bytes and requires the sealing
  frame's `journal_digest_prefix` to EQUAL the sha256 of the exact bytes preceding that frame —
  shape is not a binding.

All four #1009 canaries (`frozen_inventory_alias_clear`, `backend_calls_exported_sentinel_clear`,
`sys_global_proxy`, `descriptor_keys_live_global`, `claim_schema_live_global`, `run_kind_live_global`,
`terminal_authority_live_globals`, `authorized_manifest_toctou`, `executed_panel_toctou`,
`false_journal_prefix_digest`) are re-run against the fix and refused.

---

## 15. Codex #1011 review corrections (round 7, CHANGES on 5576452+521d175)

Round 6 accepted; the frontier moved OUTWARD to the last uncovered surfaces — the harness policy
boundary, primitive-leaf subclasses, and the remaining caller scalar/path/backend inputs.

- **B1 — the authority freeze stopped at the runner module.** `authorize_b0_launch` still read live
  `p5_b0_harness` policy (`COMPONENT_ROUTES`, `DISABLED_VALUES`, `REQUIRED_B0_KEYS`, `_MODEL_KEYS`,
  `_PINNED_BLOCKS`, `B0_RUN_KIND`, `_UNSET_STRINGS`): adding `True` to `DISABLED_VALUES` admitted
  `components.bridge=True`; rebinding harness `B0_RUN_KIND` admitted a caller kind. The runner's own
  `SCORER_ALLOWLIST_SCHEMA` was also still a live data authority.
  **Contract:** freeze the manifest-authorization policy at ITS OWNING module boundary
  (`p5_b0_harness._bind_harness_policy` → `_policy()`); the validators rebind from that snapshot.
  Include `SCORER_ALLOWLIST_SCHEMA` in the runner authority snapshot. Published copies are docs only.

- **B2 — `_inert_snapshot` preserved active primitive subclasses.** It used `isinstance` for leaves
  and returned the original object, so a `str` subclass survived by identity — an equality-
  overriding `model.id` admitted a different backend model, and a mutable prompt subclass restored
  the panel TOCTOU.
  **Contract:** exact-type dispatch for EVERY leaf (`type(obj) in {NoneType,bool,int,float,str}`);
  a subclass is refused without invoking conversion/equality/hash/iteration/copy hooks. Finite-float
  and string-key checks are applied while reconstructing, so the inert snapshot is the only object
  later authorized, hashed, compared, journaled, and executed.

- **B3 — other caller inputs and backend results stayed active objects.** The scalar bindings
  (`rubric_version`/…/`runtime_hash`) were compared without normalization (an equality-overriding
  subclass passed); the optional `report_path` was coerced by `str()` for comparison but by
  `Path()`/`__fspath__` for use, so a split path-like object sent an `integrity_verified` report to
  a different destination than the attested sink; and `dict(backend.descriptor())` was a shallow copy
  whose leaves stayed active, binding an exact manifest to a different published model id.
  **Contract:** exact-type-normalize (or refuse) every external scalar binding before any callback;
  derive the publication destination SOLELY from the exact-string sink in the inert manifest (a
  `report_path`, if given, is normalized once via `os.fspath` and required to equal it, but is never
  itself used as the path); and inert-reconstruct the backend descriptor before binding/custody.

All #1011 canaries (`live_harness_disabled_values`, `live_harness_run_kind`, `live_allowlist_schema`,
`primitive_subclass_snapshot_alias`, `manifest_primitive_subclass_binding`,
`primitive_subclass_panel_toctou`, `scalar_binding_subclass`, `split_report_path`,
`backend_descriptor_active_leaf`) are re-run against the fix and refused.

---

## 16. Codex #1013 review corrections (round 8, CHANGES — "clearly converging")

Round 7 accepted; three remaining CALLBACK-BOUNDARY fixes, each the same rule one notch tighter.

- **B1 — the backend descriptor needs an exact dict root, exact key set, and exact field types.**
  Inert reconstruction made the leaves plain, but extra fields still published unbound under
  `integrity_verified`, and a list root would raise `AttributeError` later.
  **Contract:** `_descriptor_schema_error` requires an exact `dict` root, EXACTLY the frozen
  `DESCRIPTOR_KEYS`, and exact field types (`use_cache` bool, the rest str), checked before binding.

- **B2 — the generation must be an exact `str` immediately after `backend.generate()`.** A `str`
  subclass rendered visible text yet carried contradictory scorer evidence while remaining GREEN.
  **Contract:** `type(generation) is str` is required the instant `generate()` returns — before
  any hash, journal, score, or evidence custody.

- **B3 — `report_path` must be normalized ONCE, before any callback.** It was normalized after the
  backend descriptor callback, so a stateful path could present a mismatch during the callback and
  mutate into acceptance by the later check; and the refusal message `repr()`'d the original object
  (a raising `__repr__` would crash the refusal).
  **Contract:** `report_path` is `os.fspath`-normalized to an inert string at the very top of
  `run_b0`, before any backend/scorer access; only that string (or a static refusal) is retained;
  the original object is never read, `repr()`'d, or `fspath`'d again, and the publication path is
  always the inert manifest sink string.

All #1013 canaries (`descriptor_extra_field_publish`, `descriptor_list_root_raise`,
`generation_str_subclass`, `mutating_report_path_acceptance`, `raising_repr_report_path`) are
re-run against the fix and refused.
