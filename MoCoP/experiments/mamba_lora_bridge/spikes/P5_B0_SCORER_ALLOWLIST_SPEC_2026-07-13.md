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
      "module_path": "MoCoP/experiments/mamba_lora_bridge/b0_scorers/null_estimator.py",
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
