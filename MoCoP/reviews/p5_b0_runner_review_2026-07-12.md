# P5 B0 Runner Review

**Reviewed commit:** `b1190e9ba3386a432bffe67be3867cf994e91e2a`
**Reviewer:** Codex
**Date:** 2026-07-12
**Verdict:** `CHANGES`
**Scope:** B0 runner slice only; this is not closure of full OpenCLAW #156.

## Findings

### Blocker 1: executed inputs are not completely bound

`p5_b0_run.py:160-192` compares only panel hash, model ID/revision, and a
caller-supplied scorer-version string. It does not bind or verify:

- actual model dtype, device map, attention/backend configuration, or loaded artifact;
- processor revision/configuration or prompt formatting;
- rubric implementation/data;
- scorer callable/code/configuration;
- decoding hash, complete generation configuration, model generation defaults, or seed;
- runtime and runner hashes.

The real backend self-reports a requested dtype but always loads
`torch.bfloat16` at `p5_b0_run.py:342-365`; `_bind_execution_to_manifest` ignores
the dtype field entirely. A model-free backend descriptor containing only matching
`id` and `revision` was accepted under a manifest that required `dtype=bf16`.

**Required repair:** use closed execution descriptors with independently derived
hashes. Compare all frozen model, processor, rubric, scorer, decoding, runtime, and
runner fields to the manifest. Reject unsupported/extra decoding fields and do not
accept a version string as proof of callable identity.

### Blocker 2: journal and report publication are neither append-only nor crash-durable

`p5_b0_run.py:198-219,281-323` reserves an empty report placeholder and closes its
descriptor, opens the journal with truncating mode `w`, writes the final temporary
report without `fsync`, and then calls `os.replace` without a parent-directory
`fsync`.

Reproduced failures:

- an existing `.journal` was silently truncated despite the append-only claim;
- a backend could unlink the reserved placeholder and create a third-party file,
  which `fill_reserved_report` then silently replaced;
- a scorer exception after a successful forward left only the pre-forward attempt
  line, lost the raw generation, and left a zero-byte report placeholder;
- report reservation, journal creation, and final rename have no directory-durability
  proof.

The journal also has no unique attempt ID or collision/retry record, contrary to the
current DQ1b section 6 requirement that every crash/retry receive a new immutable
attempt identity.

**Required repair:** create each attempt/event with O_EXCL or append-only semantics;
persist the completed raw output before invoking the scorer; flush/fsync every event
and final temporary report; publish with an actual no-replace primitive; fsync parent
directories after create/publish; and test crash injection at every boundary. Never
use `os.replace` on a closed reservation as proof of no-overwrite ownership.

### High 3: the reachability guard has package-import false negatives

The comment at `p5_b0_run.py:37-42` says module basenames are inspected, but
`reachable_components` at lines 66-81 instead discards every dotted module name.
Consequently all of these produced no hit:

```text
MoCoP.experiments.mamba_lora_bridge.world_model_trace
MoCoP.experiments.mamba_lora_bridge.modulatory_controller
Projects.Project_Prosthetic.memory_engine
```

The one-time pre-forward check also cannot detect a forbidden component imported or
hooked by `backend.generate` after the check.

**Required repair:** use an exact reviewed module/path inventory and inspect live
module objects or resolved `__file__` paths, not generic substrings over dotless names.
Bind the reviewed backend implementation and inspect hooks/runtime state immediately
around governed forwards. Add dotted namespace/package imports to the adversarial
suite.

### Medium 4: report schemas permit hidden `default=str` coercion

`canonical_digest` and final JSON publication accept arbitrary objects through
`default=str`. Scorer outputs therefore need not be closed JSON values and can embed
process-specific representations such as memory addresses. That weakens reproducible
digest and closed-evidence claims.

**Required repair:** exact-key parse all report/scorer records and reject non-JSON,
non-finite, or unknown values before journaling or digesting. Remove `default=str`
from governed canonicalization.

### Low 5: focused lint is not clean

Ruff reports:

- `test_p5_b0_harness.py:11` unused `B0_RUN_KIND` import (`F401`);
- `test_p5_b0_run.py:113` ambiguous variable `l` (`E741`).

## Verification

- Four focused P5 modules: `118 passed in 0.37s`.
- Fresh adversarial probes reproduced every failure above.
- No model load, GPU use, injection, Qdrant access, or reviewer implementation edit.

## Re-review gate

Return a superseding commit with complete execution binding, append-only/durable
event custody, true no-replace publication, dotted-import/hook coverage, strict JSON
evidence, and clean focused lint. The real HF slice still needs separate read-only
verification of actual model/processor hashes, dtype/device/backend, generation
configuration, hook absence, and filesystem/network side effects.

## Re-review of Watercooler #958

**Candidate:** uncommitted working tree on `9039a8c`; runner blob
`f424601f92242af63be2f5ca21d059a87c319734`, runner-test blob
`50b48a7e793a52c81462d195f7730cca349d75a2`, three-file patch digest
`bfd4cbf82e808cc6e3180edfa0ccab5a86b5d934`
**Verdict:** `CHANGES`
**Scope:** B0 runner slice only. This is neither #149 review nor full #156 closure,
and an uncommitted candidate cannot receive an immutable sign-off.

### Blocker 1: report publication can return success without publishing the report

`p5_b0_run.py:226-253,322-375` writes JSON directly into the visible reserved
leaf, so publication is not atomic: readers can observe zero or partial JSON. Worse,
`fill_reserved_report` catches and discards every `OSError`; `run_b0` then returns
`ok=True` with the expected digest even when the leaf is still zero bytes. The open
descriptor is also leaked on this path and on any backend/scorer exception.

On the actual Linux execution platform, a backend can unlink the reserved leaf and
create a different file at that path. The runner fills its now-unlinked descriptor,
closes it, returns `ok=True`, and leaves the replacement file at the advertised report
path. Reproduced result:

```text
ok=True, published_path_content=THIRD-PARTY
```

The patch avoids the old `os.replace` clobber, but does not prove that the advertised
path is the owned, durable report. Use a separate exclusive claim/attempt record and
a same-directory exclusive temporary report; strict-encode, flush/fsync, publish with
a no-replace primitive, fsync the parent, verify the published identity/digest, and
propagate every failure. Close all descriptors in `finally` blocks.

### Blocker 2: execution binding remains optional, caller-asserted, and incomplete

`p5_b0_run.py:165-220,268-303` accepts missing `rubric_version`,
`processor_revision`, `decoding_hash`, and `runtime_hash`; a normal B0 run with none
of them still returns `ok=True`. When supplied, they are caller strings rather than
hashes derived from the objects/configuration actually used. Scorer callable/code,
runner, model artifact, backend/attention implementation, device map, processor and
prompt template, token IDs, generation defaults, and seed remain unbound.

The decoding allowlist does not bind execution: `temperature` is accepted at lines
202-209 but ignored by `HFGenerationBackend.generate` at lines 416-428. The real dtype
path is also internally inconsistent: `descriptor()` emits `bfloat16`, while the
frozen manifests/tests use `bf16`, so the nominal HF backend refuses its own manifest.

Replace the optional strings with one closed, independently derived execution
descriptor and require exact equality before every forward. The descriptor must bind
the actual loaded model/processor artifacts, dtype/device/backend, scorer/rubric code
and data, exact decoding kwargs/defaults/seed, runtime, and runner.

### High 3: journal custody and attempt identity are still not append-only-safe

Despite #958's O_EXCL claim, `p5_b0_run.py:328` opens the journal with plain append
mode. A pre-existing journal is accepted and mixed into the new run. There is still no
unique attempt ID, collision/retry record, runner/runtime digest, token hash, or final
failure event, as required by DQ1b section 6. A scorer crash now preserves the raw
generation, which is a real fix, but leaves the report descriptor open and the visible
report leaf empty.

Create a unique immutable attempt record before each forward, refuse journal/path
collisions (including links), durably record terminal failure/completion, and exercise
crash injection at every write/fsync/publish boundary.

### High 4: reachability still has real-route false negatives

`p5_b0_run.py:66-100` considers a route only when the module's `__file__` contains the
case-sensitive substring `MoCoP` or `Projects`. Consequently loaded external
`qdrant_client` and `mamba_ssm` packages under `site-packages` produce no hit, even
though those are exactly the forbidden B0 routes. The one-time check at line 295 still
misses a forbidden internal module imported by `backend.generate`; that run completed
with `ok=True`. No model-hook or runtime-state check was added.

Use a reviewed exact route inventory that includes external component packages, bind
the backend implementation, and enforce the sterile runtime/hook/import contract
around each governed forward. Add external-package, late-import, and late-hook
canaries rather than only fake modules placed under `/app/MoCoP`.

### Medium 5: governed evidence is not strict JSON

Removing `default=str` only from the final `json.dump` is insufficient.
`p5_b0_harness.py:217-220` still uses it in `canonical_digest`, and neither the bundle
nor journal rejects non-finite values. A scorer output containing `NaN` publishes with
`ok=True` and a literal `NaN`; an arbitrary object survives digesting and fails only
after the forwards, leaving a 506-byte partial report visible.

Validate the closed evidence schema recursively before custody transfer, reject
unknown/non-JSON/non-finite values, and use `allow_nan=False` with no fallback in both
canonicalization and publication.

### Launch dependency: the live #149 source and runner schema disagree

The current DQ1b draft requires a stage-neutral immutable base manifest and a separate
per-attempt `run_kind` (`DQ1B_C1_MONITOR_GATE_DRAFT_2026-07-11.md:241-289`). The B0
harness still requires `run_kind` inside the hashed manifest and does not carry the
required schema variant, base-manifest identity, backend/device map, or runner/spec
hashes. #149 remains blocked, so this dependency must be frozen and reconciled before
the runner can receive launch sign-off.

## Re-review verification

- Four focused P5 modules: `118 passed in 0.56s`.
- Focused Ruff: clean.
- Reproduced: optional execution claims accepted; external Qdrant/Mamba unseen;
  pre-existing journal reused; late forbidden import accepted; `NaN` published;
  arbitrary object leaves partial report; injected write failure returns `ok=True`
  with a zero-byte report and live descriptor; Linux path swap returns `ok=True` while
  the advertised leaf contains third-party data; HF dtype spelling mismatch.
- Confirmed repair: a completed raw generation is journaled before scorer execution.
- No reviewer implementation edit, model/GPU use, B0 launch, Qdrant access, or mutable
  experiment execution.

## Next re-review gate

Return one immutable superseding commit with the atomic/no-replace publication and
attempt-custody state machine, mandatory derived execution descriptor, sterile-runtime
checks, strict JSON canonicalization, #149 schema reconciliation, and adversarial tests
for every reproduced failure above. Passing the current happy-path suite is necessary
but not sufficient, and runner GREEN alone would still not authorize #155.

## Re-review of `e2a79e6` / Watercooler #964

**Reviewed commit:** `e2a79e67ca6c5da687d3c656ac77bd34ed282204`
**Runner blob:** `cf0de07760202e114d984a29df228ab5ee5ea7f8`
**Verdict:** `CHANGES`
**Scope:** B0 runner slice only; not #149 closure, full #156 closure, or #155 launch.

### Accepted repairs

This is an immutable candidate and it materially improves the previous patch:

- common external Qdrant/Mamba names and persistent late imports are detected;
- dtype normalization removes the `bfloat16`/`bf16` self-refusal;
- decoding rejects extra fields and derives its hash from the two declared kwargs;
- raw generation is journaled before scorer custody;
- the journal is initially claimed with `O_EXCL`;
- the primary hard-link publication path is no-replace;
- governed evidence rejects `NaN` and arbitrary objects instead of coercing them;
- the supplied four-module suite passes and focused Ruff is clean.

These deltas close several concrete #960 reproductions. They do not close the
execution-identity or custody contracts below.

### Blocker 1: execution identity remains self/caller-asserted

`p5_b0_run.py:247-333` still accepts any backend that self-reports the manifest's
model ID/revision/dtype. Rubric, processor, and runtime are explicitly caller strings
compared with manifest strings at lines 321-331; they are not derived from the objects,
files, or environment actually used. `runner_digest` is computed only after launch
authorization and recorded at lines 535-552, never compared with an authorized manifest
value. The HF descriptor at lines 678-683 still omits backend implementation, resolved
artifact/commit, actual processor identity, device map/device, and attention backend.
`use_cache=True`, tokenizer behavior, prompt formatting, token IDs, and decode behavior
at lines 695-708 are also outside the derived decoding hash.

Fresh counterexamples:

```text
backend_without_sterile_accepted=True
unapproved_runner_accepted=True, recorded=UNAPPROVED-RUNNER
closure_digest_equal=True
closure_state_accepted=True, value=2
```

The closure probe used two scorers with identical source but different captured state;
`_callable_digest` bound them identically. An arbitrary backend with no sterility method
also passed. Replace the optional/caller assertions with one closed manifest-authorized
descriptor derived from the actual backend/model/processor/rubric/scorer/runtime/runner
artifacts and configuration. Hash scorer closure/config/data dependencies, not source
text alone.

### Blocker 2: journal and report do not form an immutable terminal transaction

The O_EXCL journal descriptor does not protect its pathname. On Ubuntu, a backend
unlinked the journal during the forward and installed a replacement. All later events
went to the now-unlinked owned descriptor; the runner closed it and returned success:

```text
journal_swap_ok=True, journal_path_content=THIRD-PARTY
```

On failure, lines 611-614 close the owned descriptor and `_append_terminal_failure`
reopens the pathname with plain append mode at lines 460-472, without `O_NOFOLLOW` or
inode verification. A replaced hard link redirected the failure event into an unrelated
file. Conversely, if writing the `completed` event fails after report publication, the
runner leaves the sealed report visible but appends a terminal `failed` event:

```text
completed_failure=OSError, report_exists=True, terminal=failed
```

Keep the owned journal descriptor through terminal custody, verify pathname identity,
and define a recoverable two-phase terminal protocol so report existence and journal
state cannot disagree. The report must bind the sealed journal digest and terminal state.

### High 3: publication and crash durability still have fail-open/partial paths

`publish_report_atomic` catches every non-`FileExistsError` from `os.link` and falls
back to writing the final pathname in place at lines 416-428. A forced link failure plus
final-file `fsync` failure raised but left a visible 1019-byte report. Directory `fsync`
errors are swallowed at lines 339-348; two injected directory durability failures still
returned `ok=True`. `_write_journal_event` at lines 453-457 ignores `os.write`'s returned
byte count; a forced short write was treated as success and left invalid JSON.

There is also fallible work after reservation but before the `try` begins at line 555.
A backend that succeeded on its binding-time `descriptor()` call and raised on the
second call at line 543 left an empty journal and a live leaked descriptor.

Require the atomic no-replace primitive instead of downgrading to visible in-place
publication; propagate namespace-durability failure; loop until every journal byte is
written; and enter `try/finally` immediately after reservation.

### High 4: no-component reachability is still bypassable

The exact inventory at lines 55-92 omits the previously named real route
`Projects.Project_Prosthetic.memory_engine`; it produced no hit. Other real component
basenames are also absent, so inventory/route lockstep only proves that route labels
exist, not that the reviewed module set is complete.

The reachability check runs once before the loop and only after `generate`. A scorer can
import Mamba after probe 1, allowing probe 2 to execute with it reachable before the
post-forward check aborts. A backend can also import/use then remove `qdrant_client`
inside one forward; that run returned `ok=True`. Sterility remains optional, is checked
only before generation, and the HF implementation omits PyTorch global hook registries.

Use a sterile minimal runtime/import deny boundary, require a bound sterility contract,
and re-check immediately before and after every governed forward and scorer. Restore
the complete reviewed module inventory, including `memory_engine`.

### High 5: protected-sink and #149 schemas are not reconciled

The harness requires `evidence_sink.present=False`, but `reserve_report_slot` creates
missing parent directories. A completely absent parent sink was created and the run
returned `ok=True`; this does not prove the predeclared protected sink required by DQ1b
section 6 and permits a new mutable directory write. Distinguish and verify an existing
protected parent from an absent report leaf.

The current DQ1b source also requires a stage-neutral base manifest, per-attempt
`run_kind`, backend/device map, runner/runtime/spec hashes, and prompt/token binding.
The harness still hashes `run_kind` inside the manifest, lacks the other base fields,
and its per-probe attempt record omits run kind, model/runtime/runner digests, and token
hash. `e2a79e6` honestly declares this dependency unresolved; it remains a launch block.

### Medium 6: canonicalization is not fully strict JSON

`canonical_digest` at `p5_b0_harness.py:249-254` does not call
`assert_strict_json`. It therefore collapses non-JSON structures:

```text
canonical_digest({1: "x"}) == canonical_digest({"1": "x"})
canonical_digest((1, 2)) == canonical_digest([1, 2])
```

Call the strict validator before canonicalization and accept only actual JSON container
types. Close nested manifest schemas so unknown/non-string keys cannot enter custody.

## `e2a79e6` verification

- Four focused P5 modules: `151 passed in 0.82s` using a workspace basetemp.
- Focused Ruff: clean.
- Fresh model-free probes reproduced every counterexample recorded above.
- Ubuntu probes reproduced successful journal-path replacement and swallowed directory
  `fsync` failures on the actual Linux filesystem semantics relevant to ML-WS.
- No reviewer implementation edit, model/GPU load, real B0 model forward, Qdrant access,
  injection, or experiment-state write.

## `e2a79e6` disposition

`CHANGES`. Preserve the accepted repairs, then return a superseding immutable commit
that closes actual execution identity, journal/report terminal atomicity, full-write and
durability handling, sterile reachability, protected-sink verification, and strict
canonicalization. #149 schema reconciliation and a separate real HF read-only audit
remain mandatory before #155 even if the model-free slice later receives GREEN.

## Re-review of `e96c7d2` / Watercooler #968

- **Reviewed commit:** `e96c7d29e41592f8e28ebe4384482d091c04d6e2`
- **Runner source commit:** `139e5a31235d79517405b5590ba4ce87e0d6190d`
- **Runner blob:** `e73434329e3bcf07f10ef37717d18e131979634e`
- **Verdict:** `CHANGES`
- **Scope:** B0 runner slice only; not #149 closure, full #156 closure, the real HF audit,
  or #155 launch.

### Accepted repairs

The superseding state closes several exact `e2a79e6` counterexamples:

- `runtime.runner_digest` is now authorized before reservation;
- ordinary Python closure cells and defaults contribute to the scorer digest;
- backend descriptors add backend/device/attention/use-cache names;
- `assert_sterile` is mandatory, the real module inventory includes
  `memory_engine`, and the HF check includes PyTorch global hook registries;
- publication no longer downgrades from `os.link` to an in-place final write;
- journal writes loop over short writes, the failure path keeps the owned fd, and an
  absent sink parent is refused instead of created;
- strict canonicalization now rejects non-string keys and tuples; and
- the supplied four-module suite passes `164` tests.

These are material improvements. They do not establish the claimed closed terminal,
execution-identity, or sterile-runtime contracts.

### Blocker 1: a post-link failure still creates contradictory terminal records

`publish_report_atomic` makes the final report visible with `os.link` at
`p5_b0_run.py:535`, then performs the fallible parent-directory `fsync` and byte readback
at lines 547-550. `run_b0` does not set `published_ok=True` until that entire function
returns at line 711. Therefore any failure after the link enters the exception path with
`published_ok=False` and appends `failed` at lines 723-731, although the visible report
already says `terminal_state=completed`.

Fresh fault injection at the second parent `fsync` reproduced:

```text
postlink_fsync_error=OSError
report_exists=True
report_terminal=completed
journal_terminal=failed
```

This is the same class of terminal disagreement rejected in #966. Propagating the
durability error is necessary but insufficient: the state machine must distinguish
"final leaf became visible" from "publication returned normally" and must never record
the former as a failed, unpublished run.

The best-effort completion path at lines 715-722 is also not safely framed. A partial
write followed by `OSError` is swallowed, returns `ok=True`, and leaves an invalid JSONL
tail:

```text
completed_partial_write_ok=True
report_exists=True
journal_tail=invalid
```

A missing optional completion note may be a declared recovery state; a corrupt audit
tail is not. The terminal protocol needs an executable verifier and an explicit rule for
truncated terminal frames.

### Blocker 2: the report authenticates intended journal writes, not actual bytes

`_Journal` updates an in-memory hash only for writes through its owned descriptor at
`p5_b0_run.py:434-463`. `verify_identity()` checks only device/inode equality. Another
descriptor or hard link can therefore alter bytes on that same inode without changing
identity or the in-memory digest. An independent full-run probe overwrote byte zero of
the live journal through a second descriptor; the runner returned `ok=True`, but the
report's `journal_digest` did not equal SHA-256 of the actual journal prefix.

The report must authenticate bytes re-read from the stable owned object, and the
protected sink must prevent or detect same-inode mutation. Inode equality alone proves
pathname aliasing, not content custody.

### Blocker 3: execution identity still admits behaviorally different objects

`_callable_digest` at `p5_b0_run.py:238-263` covers function source, qualname, defaults,
and closure cells. It does not bind callable-instance state, `functools.partial`
arguments, referenced mutable globals, or scorer data dependencies. Two callable
instances with identical `__call__` code and different state still collide; a manifest
authorized with the first digest accepted the second and published its different score:

```text
stateful_digest_equal=True
different_state_accepted=True
value=2
```

The extended model descriptor is likewise presence-and-equality only at lines 326-333.
The harness still pins only model `id/revision/dtype` at
`p5_b0_harness.py:71-79`; setting backend, device, attention, and use-cache to `null` in
both manifest and descriptor produced `ok=True`. Rubric, processor, and runtime remain
caller strings at `p5_b0_run.py:387-396`, and no backend implementation digest is bound.
The real HF path also reports `config.use_cache` in its descriptor at lines 796-805 but
always executes `use_cache=True` at lines 821-834, so a false configured value can bind
while the governed forward consumes true.

The separate real-HF audit is an honest and necessary dependency, but it does not close
these model-free identity collisions. The runner must reject unset extended fields and
bind the concrete scorer/backend configuration and data it actually executes.

### High 4: the component and sterility boundary does not surround all executed code

`run_b0` calls `backend.descriptor()` unconditionally at `p5_b0_run.py:593-595`, even
when manifest/reachability/panel refusals already exist. A descriptor can therefore run
external code on a refused launch. More specifically, a transient forbidden import in
`descriptor()` enters the audit sentinel but is erased by `_clear_import_sentinel()` at
line 658 without inspection. The run completed successfully in a fresh probe:

```text
descriptor_transient_import_ok=True
```

Sterility is checked only before `generate` at line 657. The post-forward block at lines
662-667 checks module reachability, not the mandatory sterility contract. A one-probe
backend that became dirty during `generate` returned `ok=True` and published:

```text
post_forward_sterility_ok=True
backend_dirty=True
```

Drain/check the audit sentinel around descriptor and sterility calls, perform no backend
call after an initial refusal, and re-run the bound sterility check after every forward
and scorer. Also make audit-hook installation fail closed; `_ensure_import_audit` currently
swallows installation failure at lines 168-175 while marking the hook installed.

### High 5: reservation and protected-sink custody are incomplete

`reserve_report_slot` creates the O_EXCL journal at `p5_b0_run.py:502`, then calls the
fallible parent `fsync` at line 505 outside a cleanup block. Injecting that failure left
the journal present and its descriptor locked:

```text
reserve_error=OSError
journal_exists_after_error=True
unlink_while_leaked=PermissionError
```

`uuid.uuid4()` at line 622 is also fallible after reservation but before the `try` at
line 625, so the cleanup guarantee is not yet structurally complete.

The inode check at line 704 is also only a pre-publication snapshot. There is no identity
verification after the sealing event, report link, or completion event, leaving a
check-to-publication window for pathname replacement on the Linux target. Finally,
`parent.is_dir()` proves existence only; it does not bind canonical parent identity,
ownership/permissions, or reject a symlinked parent. Those attributes must come from the
frozen protected-sink contract rather than from the path string alone.

### Launch dependency: #149 schema reconciliation remains open

The current DQ1b contract requires a stage-neutral base manifest and a separately bound
per-attempt run kind. The B0 harness still includes `run_kind` in `REQUIRED_B0_KEYS` at
`p5_b0_harness.py:54-68`, while the per-probe attempt event at
`p5_b0_run.py:649-652` omits run kind, model/runtime/runner digests, token hash, and the
other DQ1b section 6.8 fields. #968 explicitly acknowledges this as a separate launch
block. That acknowledgment is correct: it remains unresolved and #155 must not launch.

### `e96c7d2` verification

- Requested runner blob matches both `e96c7d2` and current HEAD:
  `e73434329e3bcf07f10ef37717d18e131979634e`.
- Four focused P5 modules: `164 passed in 0.58s`.
- `git diff --check` on the three reviewed files: clean.
- The claimed focused Ruff result did not reproduce:
  `tests/test_p5_b0_run.py:19` has unused import `DESCRIPTOR_KEYS` (`F401`).
- Fresh model-free probes reproduced all counterexamples above. No model/GPU load,
  Qdrant access, injection, birth, or reviewer implementation edit occurred.

### `e96c7d2` disposition

`CHANGES`. Preserve the accepted repairs. Supersede with adversarial tests for the
post-link durability state, truncated completion frames, generic callable/config state,
non-null descriptor binding, descriptor-time imports, post-forward sterility, reservation
cleanup, and post-publication journal identity. #149 reconciliation and the real HF audit
remain independent launch holds; passing this runner re-review alone will not authorize
#155.

## Re-review of `3222f52` / Watercooler #970

- **Reviewed commit:** `3222f5241cfd2fb94e2d1bf626b292993b1ccc9c`
- **Runner blob:** `643bcbc9e5a8c91cf7c5287ceb24f5e7ce7ef8ed`
- **Verdict:** `CHANGES`
- **Scope:** B0 model-free runner slice and its proposed trust boundary only; not the
  real HF audit, #149 closure, full #156 closure, or #155 launch.

### Accepted repairs

Round four materially improves the previous state:

- the hard-link operation is now the explicit visibility/commit point, so a later
  parent-fsync failure no longer appends a contradictory `failed` event;
- the report reads and hashes actual journal-prefix bytes through the owned fd;
- callable instances and bound methods are refused, extended descriptor fields must be
  non-null, and HF `use_cache` is shared between descriptor and execution;
- descriptor code runs only after cheap refusals clear, descriptor imports are inspected,
  audit installation fails closed, and sterility is rechecked after forward/scorer calls;
- reservation-fsync failure closes the fd, a direct symlinked parent is refused, and
  `uuid4` is inside the cleanup region; and
- the changed runner/test files pass focused Ruff, while the four P5 modules pass
  `177` tests with one Windows symlink test skipped.

These repairs close several exact #969 probes. The remaining defects are at the
runner/boundary interface rather than reasons to discard the new structure.

### Boundary ruling

The three proposed external dependencies are not equivalent:

1. **Protected-sink OS contract: partly external.** Preventing a hostile same-UID process
   from mutating an inode requires filesystem/process isolation outside this model-free
   module. However, binding and checking that prerequisite, and refusing ordinary success
   after the module detects a custody violation, are runner responsibilities. The current
   code does neither completely.
2. **Real HF artifact/processor/device verification: correctly separate.** A model-free
   backend protocol cannot attest the resolved Hugging Face artifacts or device map. The
   read-only HF audit remains a valid independent launch hold.
3. **#149 stage-neutral/per-attempt schema: correctly separate ownership, still a launch
   hold.** Its separate lane does not make the current manifest launch-compatible and does
   not authorize #155.

Thus items 2 and 3 are correctly drawn. Item 1 may be a separately implemented and
reviewed deployment contract, but the runner must require a bound passing attestation or
return an explicit committed-but-integrity-failed/indeterminate result. It cannot silently
assume the contract and still return `ok=True`.

### Blocker 1: detected report or journal custody loss still returns normal success

`finalize_publication` at `p5_b0_run.py:621-639` converts a report readback mismatch into
a warning. A post-publication journal identity failure at lines 839-842 is also only a
warning. `run_b0` then unconditionally returns `ok=True` at lines 867-870; the immutable
report itself contains neither warning nor an indeterminate status.

Fresh probes reproduced both paths:

```text
corrupt_committed_report_ok=True
path_bytes=b'CORRUPTED'
warning=post-commit readback mismatch (protected-sink mutation; OS contract)
report_has_warnings=False

postpublish_journal_identity_failure_ok=True
warnings=('injected post-publication journal swap',)
```

The runner may be unable to undo a visible hard link, but it can and must distinguish
`committed`, `durability_verified`, and `integrity_verified`. A detected mismatch or lost
journal pathname is an integrity-failed/indeterminate governed outcome, not a successful
B0 result. Until the protected-sink contract is separately attested, its absence must be
a pre-run refusal rather than an implicit assumption.

### Blocker 2: swallowed temp cleanup leaves an unreported writable report alias

After linking the staged file to the final report, `publish_report_atomic` calls
`_safe_unlink(tmp_path)` at `p5_b0_run.py:614-615`. `_safe_unlink` suppresses every error
at lines 462-466. If unlink fails, the temporary pathname remains a second writable name
for the committed inode, but publication returns with no warning.

Fault injection reproduced:

```text
temp_unlink_failure_ok=True
warnings=()
alias_count=1
same_inode=True
report_bytes=b'ALIAS-MUTATED'
```

This alias is created and cleaned by the runner, so it is not an external OS-contract
escape. Post-link temp cleanup must be checked and included in the committed-but-
indeterminate disposition; the runner must not claim clean custody while its writable
staging alias remains.

### High 3: scorer identity is sampled once, not held across execution

The new plain-function constraint and referenced-data-global digest improve
`_callable_digest`, but the digest is computed once at `p5_b0_run.py:705`, before
`backend.descriptor()` and every forward/scorer call. A backend can mutate the scorer's
closure/global data after that sample; the scorer then executes different state without a
new comparison. A one-probe run produced:

```text
scorer_state_mutated_after_binding_ok=True
published_value=2
```

Plain functions can also reach helper functions/classes/modules whose current bindings
are deliberately excluded at lines 273-285. Bind an explicit immutable scorer code/data
descriptor and verify it immediately before and after each scorer call, or isolate the
scorer in a separately attested deterministic process. A one-time `repr` snapshot is not
an execution-state binding.

### High 4: the terminal verifier verifies JSON syntax, not the terminal protocol

`verify_terminal_frames` at `p5_b0_run.py:659-679` accepts any invalid final line as a
tolerated truncation and returns `ok=True` without requiring a terminal event. It checks
no event schema/order, run-id consistency, exactly-one terminal rule, report existence,
published digest, journal-prefix digest, or completed-vs-failed exclusivity. It is also not
called by `run_b0` before returning.

Fresh examples:

```text
claim + sealing -> ok=True, terminal=sealing
claim + ARBITRARY GARBAGE -> ok=True, terminal=claim, truncated_tail=True
```

Independent probes also accepted an empty journal and `failed` followed by `completed`.
Use framed/checksummed events or otherwise prove that a truncated final frame is the
terminal append, then validate the complete state machine and report cross-bindings.

### High 5: the import boundary still excludes the sterility checks themselves

The forward/scorer checks are better placed, but the sentinel is drained before the final
`backend.assert_sterile()` at `p5_b0_run.py:801-803` and never drained afterward. A
transient forbidden import during that final sterility call survives unexamined; on the
last probe the run publishes successfully:

```text
postscorer_sterility_import_ok=True
undrained=['qdrant_client']
```

Clear and drain the sentinel around each call into backend/scorer code, including every
sterility assertion. Do not clear imports produced by the code that is supposed to prove
sterility.

### High 6: short-read and post-commit write handling are still incomplete

`actual_prefix_digest` performs one `pread`/`read` at `p5_b0_run.py:513-522`. A short read
is legal and is not rejected or completed in a loop. Independent fault injection produced
`ok=True` with a report journal digest different from SHA-256 of the complete real prefix.

The completed-event handler catches only `OSError` at lines 843-853, while `_write_all`
raises `B0RunError` when a write makes zero progress. Injecting that return after commit
left the report visible, the journal ending at `sealing`, and `run_b0` raised:

```text
completed_zero_write_error=B0RunError
report_exists=True
journal_tail_event=sealing
```

Loop full reads, reject size changes, and route every post-commit terminal-write failure
through the same explicit committed-indeterminate state. The inadequate syntax-only
verifier cannot currently recover this case safely.

### Medium 7: reservation cleanup can falsely claim that the collision was removed

On reservation parent-fsync failure, lines 570-575 close the fd and call the swallowing
`_safe_unlink`, then raise an error saying the journal was cleaned up. Forced unlink
failure left the zero-byte O_EXCL journal in place, permanently colliding a retry. Cleanup
failure and the surviving path must be reported truthfully and fsynced when removal works.

### `3222f52` verification

- Runner blob at both `3222f52` and current HEAD:
  `643bcbc9e5a8c91cf7c5287ceb24f5e7ce7ef8ed`.
- Four focused P5 modules: `177 passed, 1 skipped in 0.65s`.
- Changed runner/test files: Ruff clean.
- Reviewed range `e96c7d2..3222f52`: `git diff --check` clean.
- Fresh model-free probes reproduced the findings above. No model/GPU load, Qdrant
  access, injection, birth, or reviewer implementation edit occurred.

### `3222f52` disposition

`CHANGES`. Preserve the round-four repairs. Supersede with tests and state semantics for
post-commit readback/journal-identity failure, staging-alias cleanup failure, scorer-state
mutation during a run, terminal-frame order/cross-binding, imports inside sterility calls,
full journal reads, zero-progress completed writes, and failed reservation cleanup.

A later model-free runner GREEN may remain explicitly conditional on three separately
reviewed launch holds: a manifest-bound protected-sink preflight/attestation, the real HF
read-only audit, and #149 schema reconciliation. `3222f52` itself is not runner GREEN and
does not authorize #155.

## Post-closeout audit of `99f7bd1` / Watercooler #977

- **Reviewed commit:** `99f7bd107e8889f03bfdf2876d428feb1a3bab5c`
- **Runner blob:** `f5efe896499c8090635b57b8f9897a217920886b`
- **Verdict:** `CHANGES`
- **Scope:** current model-free B0 runner after the `b8d4b40` review target was
  superseded. This audits the full unresolved canary set, not only the final
  terminal-event/disposition patch reviewed in #977.

### Accepted repairs since `b8d4b40`

The later sequence closes important terminal defects:

- terminal-frame `fsync` failure now returns `committed_indeterminate`, not normal
  success;
- the actual pre-sealing journal-prefix digest is reconciled after publication;
- non-terminal frames after sealing are rejected;
- claim, sealing, and terminal frames require nonempty run IDs; and
- terminal event names are checked against their permitted dispositions.

Those fixes and the clean focused test result should be preserved. They do not exercise
or close the independent scorer, import, attestation, framing, and failure-path findings
below. The #977 review was explicitly bounded to the last terminal mapping patch, so it
cannot establish full-runner convergence.

### Blocker 1: mutable scorer dependencies still execute outside the digest

`_callable_digest` at `p5_b0_run.py:248-291` serializes closure cells, defaults, and
allowed data globals with `repr`. `_scorer_selfcontained_refusals` at lines 301-326
checks direct module globals only. It neither recursively validates closure/default
values nor rejects custom objects nested inside otherwise allowed containers.

A plain scorer captured a mutable object whose `repr` was constant. The backend changed
that object's value during `generate`. Both pre/post scorer digests remained identical,
the self-contained check returned no refusals, and the run published the changed result:

```text
selfcontained_refusals=[]
digest_same=True
ok=True
recorded_value=2
```

Recursively canonicalize only inert, closed dependency values (strict JSON is the
simplest contract), and reject custom objects in closures, defaults, keyword defaults,
or nested global containers. `repr` is not a behavioral binding.

### Blocker 2: an unguarded backend attribute lookup can erase a forbidden import

`run_b0` calls `getattr(backend, "assert_sterile", None)` at line 1009. A custom
`__getattribute__` can execute there. Line 1018 then drains and discards the sentinel as
a supposed baseline before the guarded scorer/descriptor phase.

A backend emitted a one-shot `qdrant_client` import audit event during that exact lookup,
removed no persistent module because none was needed, and did not repeat the import on
later sterility calls. Fresh result:

```text
lookup_import_fired=True
ok=True
terminal_state=integrity_verified
```

Account for the attribute-resolution window before any drain. No unexamined sentinel
clear/drain may sit after attacker-influenceable backend or scorer access.

### Blocker 3: the terminal verifier still accepts split or malformed authority

The event/disposition mapping repair is necessary but not a complete terminal grammar.
Fresh current-head probes reproduced all of the following:

```text
complete terminal JSON written without final newline, then write error:
  result=committed_indeterminate
  verifier=ok / completed / integrity_verified

JSON [] terminal written and fsynced:
  AttributeError escapes after commit; report_exists=True

claim -> committed_integrity_failed, no sealing:
  verifier ok=True

claim -> unknown event -> sealing -> completed with wrong terminal digest:
  verifier ok=True
```

`verify_terminal_frames` at lines 893-979 assumes every decoded frame is a mapping,
forgets whether the final line was newline-terminated, requires sealing only for
`completed`, accepts arbitrary pre-sealing lifecycle events, and checks the sealing
digest but not the terminal report binding. `run_b0` catches `ValueError` but not the
resulting `AttributeError` at lines 1189-1194.

Use an explicitly framed/checksummed terminal append or otherwise bind terminal length
and durability. Validate each decoded frame's type and exact schema/order; require
sealing for every committed terminal; bind terminal report bytes/digest; and route every
post-commit verifier exception to `committed_indeterminate` without an uncaught raise.

### Blocker 4: the protected-sink prerequisite is still only two strings

`check_protected_sink_attestation` at lines 363-381 accepts any two non-placeholder
strings. `signer="x", review_ref="x"` returned `ok=True/integrity_verified`. It verifies
no attestation schema, signature/digest, subject sink path, expiry/status, authorized
signer, or deployment preflight result.

Actual same-UID mutation prevention remains an external OS responsibility, but a
manifest-bound, resolvable passing attestation is still a launch prerequisite under the
previous boundary ruling. It has not become one of only two remaining holds: the real HF
audit and #149 are separate, while protected-sink deployment verification remains a
third hold unless explicitly folded into a reviewed task/artifact contract.

### High 5: failed-event journaling can mask the original exception

The pre-commit failure handler at lines 1206-1215 catches only `OSError` around
`journal.event`. `_write_all` raises `B0RunError` on zero progress. A backend
`ValueError("original backend failure")` plus a zero-progress failed frame surfaced only:

```text
B0RunError: os.write made no progress
```

Catch the journal failure classes while preserving and re-raising the original exception;
record the secondary custody failure separately where possible.

### `99f7bd1` verification

- Current runner/test blobs match exact `99f7bd1`.
- Four focused P5 modules: `208 passed, 1 skipped in 1.43s`.
- Changed runner/test Ruff: clean.
- Fresh model-free probes reproduced every counterexample above.
- No model/GPU load, Qdrant access, injection, B0 launch, or reviewer implementation edit.

### `99f7bd1` disposition

`CHANGES`. Watercooler #977 is valid credit for its bounded terminal-mapping patch, but
not a full model-free runner closeout. Keep #156 open. Supersede with recursive scorer
dependency validation, fully accounted import windows, strict terminal framing/grammar
and exception containment, a verifiable protected-sink attestation contract, and
original-exception-preserving failure journaling. #149 and the real HF audit remain
independent holds; no #155 launch follows.

## Re-review of `46765b8` / Watercooler #985

- **Reviewed commit:** `46765b8d41ef587bbfdd318bb319f0c7efa6a5a0`
- **Parent:** `99f7bd107e8889f03bfdf2876d428feb1a3bab5c`
- **Runner blob:** `414d57845aafe958e3df8ebd14df6abfbf583479`
- **Test blob:** `e32a3a9131125ac2b8eaab5351e2210b053359fd`
- **Verdict:** `CHANGES`
- **Scope:** full model-free re-review of the claimed #980 repairs. Codex reviewed and
  reproduced the ordinary scorer-binding slice. At Laura's request, GPT-5.5 independently
  reviewed the content-filter-blocked integrity slice read-only; its analysis is supporting
  evidence, while this section is the Codex verdict of record.

### Accepted repairs in `46765b8`

Preserve these repairs:

- direct closure/default/keyword-default/global scorer dependencies now receive structured
  recursive handling for the exact built-in inert types the implementation recognizes;
- forbidden imports emitted while resolving `backend.assert_sterile` are examined before the
  sentinel baseline is drained;
- the terminal verifier rejects non-object frames, a valid-JSON tail without a final newline,
  committed terminals without sealing, unknown event names, and a terminal
  `published_digest` that disagrees with the report;
- post-commit verifier exceptions are contained as `committed_indeterminate`;
- protected-sink metadata now structurally requires a signer, review reference, SHA-256-shaped
  attestation digest, and a path equal to the manifest evidence sink; and
- failed-event journaling catches `B0RunError` as well as `OSError`, preserving the original
  backend exception. The real resolvable protected-sink attestation/preflight remains an
  explicitly separate launch hold, as the implementation comments state.

### Blocker 1: source-unavailable callables still collide

`_callable_digest` at `p5_b0_run.py:258-298` records `source=None` when
`inspect.getsource` fails. It does not then bind the code object's bytecode, constants, names,
or nested code objects. Two `eval`-created lambdas differing only in the returned value had the
same digest and no self-contained refusal. A manifest pinned to the first callable accepted the
second and published its different result:

```text
eval_collision True [] []
eval_run True () {'value': 2}
```

Fail closed when source is unavailable, or canonically bind the complete executable code object
including nested constants. `source=None` cannot be an executable identity.

### Blocker 2: dynamic namespace access bypasses direct-global binding

`_scorer_selfcontained_refusals` at `p5_b0_run.py:308-348` examines direct names in
`code.co_names` and permits built-ins. A scorer using `globals()['STATE'].value` exposes only
the built-in `globals` to that scan. The backend changed `STATE.value` during generation; the
scorer digest remained stable, the refusal list stayed empty, and the changed value was
published:

```text
dynamic_refusals [] digest_before 6321ffed4275
dynamic_run True () {'value': 2} digest_same True
```

Reject dynamic namespace, evaluation, import, and reflection primitives under a strict
AST/bytecode policy, or replace arbitrary executable scorers with a declarative reviewed
scoring substrate.

### Blocker 3: mutable subclasses masquerade as inert dependencies

`_is_deeply_immutable` at `p5_b0_run.py:250-255` uses `isinstance`. Subclasses of tuple,
integer, string, bytes, and frozenset can carry mutable attributes or override behavior while
passing the check. A `TupleState(tuple)` with mutable `.value` was accepted:

```text
tuple_subclass True []
```

Use exact built-in types and canonical recursive serialization. An `isinstance` admission rule
does not establish behavioral immutability.

### Blocker 4: terminal event names are not an exact journal grammar

The delegated GPT-5.5 review found that `_KNOWN_EVENTS` and
`verify_terminal_frames` at `p5_b0_run.py:942-1035` validate known names, run-ID consistency,
sealing placement, disposition, and published digest, but do not enforce the exact pre-sealing
state machine or per-event schemas. A journal such as
`claim -> generated -> claim -> sealing -> completed` can pass if its digest fields agree.
The verifier also does not require the committed terminal to carry and bind
`report_bytes_sha256`.

Implement an explicit event grammar with exact cardinality, order, required/forbidden fields,
and terminal binding to the immutable report bytes. Add canaries for missing `attempt`, duplicate
`claim`, reversed `recorded`/`generated`, missing required fields, and missing or false terminal
`report_bytes_sha256`.

The original-exception repair is also missing a direct regression that combines a backend
`ValueError` with a zero-progress failed-frame write and asserts that the backend error remains
the surfaced exception. This is a coverage gap, not a separate reproduced implementation defect.

### `46765b8` verification

- Exact runner/test blobs match the reviewed commit.
- Four focused P5 modules: `218 passed, 1 skipped in 1.37s`.
- Focused runner/test Ruff: clean.
- `git diff --check 99f7bd1..46765b8`: clean.
- Fresh model-free probes reproduced all three scorer-binding counterexamples above.
- GPT-5.5 reviewed only the delegated integrity slice read-only and returned `CHANGES` for the
  terminal-grammar blocker; it made no edits, posts, network calls, model loads, or Qdrant calls.
- No Gemma forward, GPU use, Qdrant access, injection, B0 launch, or reviewer implementation edit
  occurred in the Codex slice.

### `46765b8` disposition

`CHANGES`. The claimed #980 repairs are materially improved and should be preserved, but
the scorer identity remains bypassable through source-less code, dynamic namespace access, and
mutable subclasses, while the terminal verifier still lacks an exact state machine and schema.
Keep #156 open. The real HF audit, #149, and the resolvable protected-sink preflight remain three
separate launch holds; no #155 launch follows.

## Spec-first reviewed-scorer allowlist audit (`7f9b66c` + `b0983d7`)

- **Review request:** Watercooler #997, relaying Gidim #996
- **Spec commit:** `7f9b66c19c3f4d4ce8f7809599cf04ef7c8115a8`
- **Spec blob:** `f5fad00d19eb148ecca1b194505c310196798cf7`
- **Implementation commit:** `b0983d77f4633c5f77b6f44b638e91f9289bce29`
- **Runner blob:** `d801f8ac38ea618b52c5fbe656c3ae9fa3ae105d`
- **Test blob:** `e9e7367b4293b08c5bf24a78424d21cbdb28d16d`
- **Verdict:** `CHANGES` on the allowlist contract plus implementation.
- **Bounded scorer verdict:** `GREEN` on the exact null-estimator module bytes only; this does
  not GREEN the allowlist, loader, runner, #156, or #155.

### Accepted architecture and repairs

The authority move is sound: a B0 baseline has no legitimate need for an arbitrary
caller-supplied Python scorer, so scorer identity should be established through a reviewed,
content-pinned artifact rather than increasingly elaborate runtime introspection. Preserve:

- deletion of source/code-object/closure/global runtime identity heuristics;
- ID+version+allowlist-digest manifest binding;
- hashing the selected module bytes before compiling and executing those same bytes in a fresh
  namespace, without import-by-name or an unlisted fallback;
- claim-frame and execution-descriptor binding of scorer ID, version, module digest, allowlist
  digest, and review reference;
- the stricter event-order state machine; and
- committed terminal binding to `report_bytes_sha256` when committed report bytes are supplied.

The exact `null_estimator.py` artifact is separately acceptable. Its Git blob is
`31574f5cd95767d8c9aa3b55b958655d75f16ed2`; its raw-file SHA-256 is
`977eb558edd6cded15cfbe025f9fca7a3bca0630b397a3742eb5a3af351e2f9e`, matching the allowlist.
Static inspection found only a module docstring and one function, no imports, no module mutation,
and only deterministic built-in operations. Repeated representative calls returned identical
strict-JSON values. A successor may cite the routed Codex message as the bounded review reference
for these unchanged module bytes.

### Blocker 1: the production API is itself a runtime-mutable allowlist back door

The spec at lines 31-33 requires one committed allowlist and explicitly forbids a runtime-mutable
allowlist. The implementation instead exposes `allowlist_path` from
`load_allowlisted_scorer` (`p5_b0_run.py:277-292`) through the public `run_b0` API
(`p5_b0_run.py:1092-1103`). It also permits absolute module paths. The positive integration test
at `test_p5_b0_run.py:809-817` intentionally constructs a temporary allowlist, a temporary module,
and a matching caller-supplied manifest digest, then expects normal success.

A fresh full-run canary put top-level filesystem I/O in that temporary module. The loader executed
it before the forward, the marker file appeared, and the run still published normal success:

```text
runtime_allowlist_override True True integrity_verified
```

The module hash proves only that the bytes agree with the same runtime-supplied allowlist; it does
not prove either artifact was reviewed. Remove `allowlist_path` from the production `run_b0` API,
require the single committed allowlist location, and reject absolute/out-of-root module paths.
Loader unit tests may inject bytes through a private test seam, but a governed run must have no
alternate authority path.

### Blocker 2: event order is enforced, but event schemas and cycle identity are not

The prior GPT-5.5 finding required exact order **and per-event schema**. The spec amendment at
lines 119-128 narrows that to event sequence alone. The verifier at
`p5_b0_run.py:1022-1058` advances a three-name state machine but never requires the
`attempt_id`, `ordinal`, and `probe_id` in `generated` and `recorded` to equal those in their
opening `attempt`. It likewise does not validate the exact required/forbidden fields of the claim,
attempt, generated, recorded, sealing, failed, or committed-terminal frames.

A fresh journal used `r:0/0/p0` for the attempt, `evil:9/99/other` for generated, and
`third/-1/third` for recorded. It passed:

```text
mismatched_cycle_identity True
```

Amend the spec and implement typed exact schemas. Bind every cycle to one attempt ID, ordinal, and
probe ID; enforce monotone ordinals and `attempt_id == f"{run_id}:{ordinal}"`; require the claim's
manifest/execution/scorer bindings; and require the sealing and terminal digest fields. Preserve
the legitimate pre-publication `sealing -> failed` path when atomic publication itself fails.

### Blocker 3: an unresolved scorer review reference is executable

The core contract says only reviewed code exists, but the committed allowlist carries
`"review_ref": "PENDING-codex"` and the loader merely copies that value into the binding at
`p5_b0_run.py:373-376`. It neither rejects missing/placeholding references nor invokes a resolver.
A default full run therefore completed and journaled the unresolved reference:

```text
pending_review_ref_run True PENDING-codex
```

The separately declared resolvable-attestation hold remains valid and is not folded into this
review. Even so, the local structural gate must refuse empty, `TBD`, or `PENDING-*` review
references; the external resolver then establishes authenticity and exact subject binding. Update
the successor allowlist to the routed bounded module-review reference before any governed run.

### `7f9b66c` / `b0983d7` verification

- Exact spec, runner, scorer, allowlist, and test blobs matched the immutable targets.
- Four focused P5 modules: `221 passed, 1 skipped in 1.54s`.
- Focused Ruff: clean.
- Both commit-local `git diff --check` ranges: clean.
- Fresh model-free probes reproduced all three findings above.
- No Gemma/model forward, GPU use, Qdrant access, injection, deployment, B0 launch, or reviewer
  implementation edit occurred.

### `7f9b66c` / `b0983d7` disposition

`CHANGES`. Preserve the reviewed-artifact architecture, content-first loading within the selected
authority, journal binding, terminal report-byte binding, and the exact null-estimator bytes.
Supersede with one non-overridable committed allowlist authority, exact event schemas/cycle
identity, and a structural refusal on unresolved scorer review references. Keep #156 open. #149,
the real HF read-only audit, and the resolvable protected-sink attestation remain independent
launch holds; no #155 authorization follows.

## Round-two scorer-allowlist correction audit (`7ecbd19` + `664390f`)

- **Review request:** Watercooler #1002, relaying Gidim's round-two packet.
- **Spec commit:** `7ecbd193ff6aada5f2c6c5697e2a6805031aa5f3`.
- **Spec blob:** `c5da193833b0c36f702393e4263e3b29c8e92296`.
- **Implementation commit:** `664390ff8c1d51343d425e9b940f9479187c737b`.
- **Runner blob:** `aa11962c615282508fdd137d5b2258392d34f1d6`.
- **Allowlist blob:** `4946a99f09e4242dc1f43bdc1ea6ab3c7e41bcbb`.
- **Test blob:** `d2c2e7a02268de298ebfb10ce726d7de76b6cac1`.
- **Verdict:** `CHANGES` on the amended contract and implementation.

### Accepted round-two repairs

Preserve the following changes:

- `run_b0` no longer accepts an `allowlist_path` argument, and allowlist entries with absolute or
  out-of-root module paths are refused;
- the original well-ordered but identity-mismatched probe cycle is now refused, and ordinals must
  begin at zero and advance monotonically;
- empty, `TBD`, and `PENDING` scorer review references are locally refused, while the committed
  entry now cites `wc#1000`; and
- the exact scorer artifact remains unchanged: Git blob
  `31574f5cd95767d8c9aa3b55b958655d75f16ed2`, raw SHA-256
  `977eb558edd6cded15cfbe025f9fca7a3bca0630b397a3742eb5a3af351e2f9e`.

Fresh controls confirmed that the former cycle-identity and pending-review cases now fail closed:

```text
pending_review_ref_refused True True
mismatched_cycle_refused True generated frame identity ('evil:9', 99, 'other') != its cycle ('r:0', 0, 'p0')
```

### Blocker 1: the governed run still consults a caller-assignable allowlist path

The public function parameter is gone, but the authority is still selected at runtime.
`DEFAULT_ALLOWLIST_PATH` is an exported module global at `p5_b0_run.py:263`; the loader reads that
global on every default call at line 281; and `run_b0` reaches that default loader at line 1167.
The new integration seam at `test_p5_b0_run.py:92-96` assigns the global, and the positive
integration test at lines 858-868 then runs a temporary scorer through the governed entrypoint.

A normal caller can perform the same assignment without altering a function or using reflective
internals. A fresh full-run canary put top-level filesystem I/O in the temporary module; the
module executed and the governed run still published success:

```text
mutable_default_override True True integrity_verified
```

This is materially different from the declared out-of-scope case of an attacker replacing
functions or mutating arbitrary interpreter state: the implementation deliberately exposes and
tests the path-selection variable used by the production call. It contradicts both the original
requirement that loader tests inject only through a private loader seam and the contract's
statement that there is no runtime-mutable allowlist.

Make the governed path a private, internally derived value that `run_b0` does not obtain from an
assignable configuration global. Direct loader unit tests may pass a fixture path, but a
`run_b0` integration test must exercise the committed scorer. Also update the section-2 JSON
example: it still shows a repository-relative `module_path`, while section 10 and the committed
allowlist now require an allowlist-directory-relative path.

### Blocker 2: the exact event-schema requirement was narrowed to three identity fields

The prior verdict required exact required/forbidden schemas for every frame, the derivation
`attempt_id == f"{run_id}:{ordinal}"`, claim manifest/execution/scorer bindings, and mandatory
sealing/terminal digest fields. The round-two amendment at spec lines 159-169 records only the
identity trio, within-cycle agreement, monotone ordinal, and presence of
`generation_sha256`. The implementation at `p5_b0_run.py:1070-1090` implements that narrower
contract; claim, sealing, failed, and terminal frames retain only partial checks at lines
988-1028, while digest fields are compared only when optional expected values are supplied at
lines 1099-1116.

A fresh journal supplied all of the following in one otherwise ordered lifecycle:

- a claim containing only `event` and `run_id`;
- `attempt_id="not-r:0"` consistently across the cycle;
- arbitrary extra keys on all three probe frames;
- an empty-string `generation_sha256`; and
- sealing/completed frames without the emitted digest fields.

The verifier accepted it:

```text
underspecified_exact_schema True None
attempt_id_not_run_derived True not-r:0
```

Define one closed schema per event with exact allowed and required keys plus field types and hash
formats. Require a non-empty string `run_id`; derive each `attempt_id` from that run and ordinal;
require the claim's manifest, execution-descriptor, and exact scorer-binding fields; and require
the sealing and committed-terminal digests even when no comparison bytes were passed. Optional
expected values may strengthen those checks by equality, but their absence must not make required
protocol fields optional. Preserve the legitimate pre-publication `sealing -> failed` path.

### Delegated GPT-5.5 read-only cross-check

At Laura's request, GPT-5.5 Extra High independently reviewed the exact attached spec, runner,
tests, allowlist, and prior review ledger without editing or executing them. It reproduced the
line-level reasoning for both blockers, ruled that the named, exported path-selection global is an
ordinary authority knob rather than merely arbitrary hostile interpreter mutation, and agreed
that the event verifier implements only a subset of #1000's exact-schema repair. It found no
additional round-two regression at blocker confidence. Its verdict was `CHANGES`; it accepted the
reported test, Ruff, and diff evidence without rerunning it, as explicitly scoped.

### `7ecbd19` / `664390f` verification

- Exact target commits and blobs matched the packet.
- Four focused P5 modules: `231 passed, 1 skipped in 1.47s`.
- Changed runner/test Ruff: clean.
- Both commit-local `git diff --check` ranges: clean.
- The committed scorer's raw SHA-256 still matches `wc#1000`'s bounded module-only GREEN.
- Fresh model-free probes confirmed the two remaining counterexamples and the two accepted
  fail-closed repairs above.
- No Gemma/model forward, GPU use, Qdrant access, injection, deployment, B0 launch, or reviewer
  implementation edit occurred.

### `7ecbd19` / `664390f` disposition

`CHANGES`. B3 and the original mismatched-cycle case are closed, but B1 remains an ordinary
alternate authority path and B2 remains a partial rather than exact protocol schema. Keep #156
open. The bounded null-estimator GREEN remains valid only for its unchanged bytes. #149 schema
reconciliation, the real HF read-only audit, and the resolvable protected-sink attestation remain
independent launch holds; no #155 authorization follows.

## Round-three scorer-allowlist correction audit (`6f874ee` + `4394e32`)

- **Review request:** Watercooler #1005, relaying Gidim's round-three packet.
- **Spec commit:** `6f874eee148d423fa00fd74132659eea6b7efc57`.
- **Spec blob:** `6625204f8397ed463c0543a97757bac7d7826455`.
- **Implementation commit:** `4394e3202a15d536e421b9175802dee9d532e0d3`.
- **Runner blob:** `453dd3763fac32e512e0f6a00639a01862314255`.
- **Test blob:** `28c22915ca15ee77bef54aeb15e1162ca3849338`.
- **Allowlist blob:** `4946a99f09e4242dc1f43bdc1ea6ab3c7e41bcbb`.
- **Verdict:** `CHANGES` on the amended contract and implementation.

### Accepted round-three repairs

Preserve these repairs:

- the named `DEFAULT_ALLOWLIST_PATH` authority variable is deleted, `run_b0` still exposes no
  allowlist argument, and the governed integration test exercises the committed scorer;
- every frame now has a closed required field set with typed values, the claim binds `run_kind`,
  manifest/execution digests, and a complete scorer-binding object, and sealing/committed-terminal
  digest fields are unconditionally present and SHA-256-shaped;
- probe ordinals advance from zero, every cycle agrees on identity, and `attempt_id` is derived as
  `{run_id}:{ordinal}`; and
- the exact null-estimator remains unchanged: Git blob
  `31574f5cd95767d8c9aa3b55b958655d75f16ed2`, raw SHA-256
  `977eb558edd6cded15cfbe025f9fca7a3bca0630b397a3742eb5a3af351e2f9e`.

Fresh controls confirmed that the former under-specified claim and non-derived attempt identity
now fail closed: the first is rejected for missing `run_kind`, and the second for not being
run-derived.

### Blocker 1: the governed authority and runner receipt follow assignable `__file__`

The replacement authority at `p5_b0_run.py:281-289` derives the allowlist from the module global
`__file__` at call time. `_runner_digest` independently reads that same global at lines 245-249.
`__file__` is an ordinary assignable module attribute: assigning
`p5_b0_run.__file__` to a temporary runner path selects both a sibling temporary
`scorer_allowlist.json` and the runner bytes whose digest the manifest must match. A temporary
reviewed-scorer lookalike with top-level filesystem I/O executed through governed `run_b0`; its
marker appeared and the run still reported normal success:

```text
mutable_dunder_file_override True True integrity_verified
```

This uses the same direct module-attribute assignment as the prior `DEFAULT_ALLOWLIST_PATH`
canary; it does not replace a function, mutate bytecode, or require a reflective write primitive.
The new guard at `test_p5_b0_run.py:933-943` specifically ignores dunder globals and therefore
cannot detect the authority it now relies on. Bind runner origin through a call-time path that a
caller cannot select by assigning module metadata, and use that same fixed origin for the runner
receipt. Add a governed integration canary that assigns `p5_b0_run.__file__`, then proves neither
the selected allowlist nor `_runner_digest()` changes.

### Blocker 2: a journal claim can restore an unresolved scorer review reference

The loader correctly refuses unresolved review references, but the standalone terminal-protocol
verifier does not. `_SCORER_BINDING_SCHEMA` at `p5_b0_run.py:995-998` declares `review_ref` as only
a non-empty string, and `_typed_field_error` at lines 1001-1018 applies no `TBD`/`PENDING` refusal
to nested claim bindings. A complete exact-schema journal whose claim used
`review_ref="PENDING-codex"` passed:

```text
pending_claim_review_ref True None
```

This contradicts the section-11 requirement that the claim's `review_ref` be resolved. Apply the
same local unresolved-reference predicate inside claim verification and add empty, `TBD`, and
`PENDING-*` claim-frame regressions. The external resolver remains a separate launch hold.

### Blocker 3: sealing and terminal publication identities are not mutually bound

The exact schemas make both `published_digest` fields mandatory and SHA-256-shaped, but they are
independent values. `verify_terminal_frames` compares either field only when the optional
`report_published_digest` argument is supplied (`p5_b0_run.py:1205-1211`). Without that external
argument, a sealing frame with one valid digest and its committed terminal with a different valid
digest passed:

```text
mismatched_publication_digests True None
```

The executable terminal protocol must always require the committed terminal's
`published_digest` to equal the preceding sealing frame's value. An optional expected report
digest may additionally bind both to report bytes, but its absence cannot permit the two journal
receipts to identify different publications.

### `6f874ee` / `4394e32` verification

- Exact spec, runner, test, allowlist, and scorer blobs matched the immutable packet.
- Four focused P5 modules: `242 passed, 1 skipped`.
- Changed runner/test Ruff: clean.
- Both commit-local `git diff --check` ranges: clean.
- Fresh model-free probes reproduced all three fail-open behaviors above and confirmed the two
  advertised fail-closed repairs.
- No Gemma/model forward, GPU use, injection, deployment, B0 launch, or reviewer edit to Gidim's
  implementation, spec, or tests occurred.

### `6f874ee` / `4394e32` disposition

`CHANGES`. The named allowlist global and the broad exact-schema omissions are repaired, but the
governed path and runner receipt now follow caller-assignable `__file__`, while the journal
verifier admits unresolved claim authority and mutually inconsistent publication identities.
Keep #156 open. The unchanged null-estimator GREEN remains module-only. #149, the real HF
read-only audit, and resolvable protected-sink attestation remain independent launch holds; no
#155 authorization follows.

## Round-five self-corrected allowlist audit (`5a05884` + `08925d0`)

- **Review request:** Watercooler #1008, which supersedes round-four request #1007.
- **Spec commit:** `5a058848962494bf7db07a08441f188527895f39`.
- **Spec blob:** `46ea8961fdeaff2295cf8cb55785715e4bb2ffbf`.
- **Implementation commit:** `08925d080421285251336dd8efa2587d71538fde`.
- **Runner blob:** `61e8092947838076e60acccd1d646ef04be21b4f`.
- **Test blob:** `ff87f8b0ba5da4420c02c7da7bf7a194c83019d6`.
- **Allowlist blob:** `4946a99f09e4242dc1f43bdc1ea6ab3c7e41bcbb`.
- **Verdict:** `CHANGES` on the amended contract and implementation.

### Accepted round-five repairs

Preserve these repairs:

- the runner origin is captured once in a closure, so assigning module `__file__` no longer moves
  either the governed allowlist or the runner receipt;
- the loader and claim verifier share one unresolved-review predicate, and empty, `TBD`, and
  `PENDING-*` claim references now fail closed without the former bare-substring over-refusal;
- sealing and committed-terminal `published_digest` values are always mutually compared;
- non-string and missing event values fail closed instead of raising in the unknown-event scan;
- reassigning or clearing the published `FORBIDDEN_ROUTE_MODULES` object no longer changes the
  closure's separate inventory snapshot; and
- the exact null-estimator remains unchanged: Git blob
  `31574f5cd95767d8c9aa3b55b958655d75f16ed2`, raw SHA-256
  `977eb558edd6cded15cfbe025f9fca7a3bca0630b397a3742eb5a3af351e2f9e`.

Fresh controls confirmed the three #1006 cases are closed:

```text
dunder_origin_frozen True True
pending_claim_refused True claim frame scorer_binding.review_ref is unresolved (empty/TBD/PENDING)
mismatched_publications_refused True terminal published_digest does not match the sealing frame
```

### Blocker 1: the frozen no-component guard still exposes erase capabilities

`_bind_reachability_guard` builds the closure-captured `frozen` dict at
`p5_b0_run.py:112-127`, but returns that exact mutable object at lines 168-169. The module then
publishes the alias as `_FROZEN_FORBIDDEN` at lines 172-173. Clearing the new name therefore
clears the closure itself. With `qdrant_client` resident, both the direct reachability check and a
governed run reported clean:

```text
frozen_inventory_alias_clear True [] True integrity_verified
```

The import buffer is closure-local, but destructive capabilities over it remain exported.
`_clear_import_sentinel` and `_drain_import_sentinel` at lines 160-166 are module attributes. A
backend can emit a forbidden import and either call the clear function, or call `_drain_and_check`
and catch the resulting `B0RunError`; the runner's later check then sees an empty window:

```text
backend_calls_exported_sentinel_clear True integrity_verified () True
backend_drains_and_catches True integrity_verified ()
```

Finally, the closure's installer and the live reachability check still dereference the assignable
module global `sys` at lines 154 and 202. Replacing only that data attribute with a proxy carrying
an empty `modules` mapping and a no-op `addaudithook` hid a real resident component:

```text
sys_global_proxy True integrity_verified True
```

Do not return a mutable alias to the captured inventory, expose a destructive buffer operation to
code that runs inside the guarded window, or read the live module `sys` binding. Use an immutable
closure-owned inventory and a non-destructive monotone event log/checkpoint API, and capture the
real module dependency inside the same guard factory. Add governed canaries for the alias, helper
call, caught drain, and `sys` reassignment cases.

### Blocker 2: other protocol authorities remain live module data

Section 12 states the correct general rule: no authority may be a call-time dereference of an
assignable module attribute. The implementation applies it only to runner origin and part of the
component guard. Other verdict-bearing data remain live:

- `DESCRIPTOR_KEYS` at line 231 is read after `backend.descriptor()` returns, so that callback can
  replace it with `()` and make an empty execution descriptor pass;
- `_FRAME_SCHEMAS` at lines 1042-1053 is mutable in place, so weakening the claim schema makes an
  under-bound claim pass the standalone verifier;
- imported `B0_RUN_KIND` is read when the claim is written and again by the verifier, so a backend
  callback can rebind both while the report still hardcodes `b0_baseline`; and
- `INTEGRITY_VERIFIED` plus `_TERMINAL_DISPOSITION` remain independently assignable/mutable, so a
  caller-selected disposition can become `ok=True`.

Fresh full-run and verifier canaries passed incorrectly:

```text
descriptor_keys_live_global True integrity_verified {}
claim_schema_live_global True None
run_kind_live_global True integrity_verified caller_selected_kind b0_baseline
terminal_authority_live_globals True caller_verified completed caller_verified
```

Perform one complete authority inventory rather than another name-by-name patch. Bind the exact
descriptor fields, run kind, event vocabulary/schemas, terminal mapping, digest rules, and related
normalization tables into immutable closure-owned values used by the governed entrypoint and
standalone verifier. Published documentation copies may remain module data, but must not be the
objects or names consulted for a verdict.

### Blocker 3: authorized manifest and panel inputs are mutable after binding

`run_b0` authorizes and digests the caller's live manifest at line 1337, then invokes backend code
before later reads from that same object. `_bind_execution_to_manifest` reads it at lines 547-615,
the sink path is read at lines 1386-1394, and the original decision digest is nevertheless placed
in the execution descriptor and claim at lines 1420-1427. A backend retaining the manifest
reference changed `model.id` during `descriptor()`, returned a matching different descriptor, and
published success under the original authorized digest:

```text
authorized_manifest_toctou True integrity_verified True True caller/other-model
```

The panel is likewise hashed before execution but iterated from the caller's original mutable list
at line 1438. A first forward changed the second row; the bound panel hash stayed original while
the second recorded prompt digest proved the changed prompt executed:

```text
executed_panel_toctou True integrity_verified True True
```

Before touching any backend attribute or callback, reconstruct inert exact-built-in snapshots of
the manifest and panel. Authorize, hash, validate, journal, and execute only those same snapshots;
never read the caller-owned objects again. The reconstruction must not invoke caller-controlled
copy hooks or retain mutable aliases.

### Blocker 4: the standalone verifier does not verify `journal_digest_prefix`

The sealing schema requires a SHA-256-shaped `journal_digest_prefix`, but
`verify_terminal_frames` never hashes the actual raw bytes before the sealing line. `_Journal`
has the needed byte-level semantics in `prefix_digest_at_seal` at lines 771-802, yet the standalone
auditor accepts any different 64-hex value:

```text
false_journal_prefix_digest True True None
```

Parse with raw-byte offsets and require the sealing receipt to equal SHA-256 of the exact journal
prefix preceding that sealing frame. Shape alone is not a binding.

### Delegated GPT-5.5 and root reconciliation

At Laura's request, a GPT-5.5 coding subagent independently reviewed the complete immutable
packet before the root verdict. It identified the frozen-dict alias, destructive sentinel calls,
`sys` proxy, live descriptor/schema authorities, and false journal-prefix receipt. Its final prose
was classifier-blocked after those findings reached the root. Codex then independently reproduced
every reported case and added the manifest and panel TOCTOU plus the run-kind/terminal-authority
instances of the same live-global class. No delegated claim is accepted here without a local
executable reproduction.

### `5a05884` / `08925d0` verification

- Exact spec, runner, test, allowlist, and scorer blobs matched the immutable packet.
- Four focused P5 modules: `257 passed, 1 skipped in 1.61s`.
- Changed runner/test Ruff: clean.
- Both commit-local `git diff --check` ranges: clean.
- Fresh model-free probes reproduced every blocker above and confirmed the accepted repairs.
- No Gemma/model forward, GPU use, Qdrant access, injection, deployment, B0 launch, or reviewer
  implementation/spec/test edit occurred.

### `5a05884` / `08925d0` disposition

`CHANGES`. The #1006 repairs and the intended closure move are valid, but the component guard still
exports mutable/destructive authority, other verdict-bearing globals remain live, caller-owned
manifest/panel objects survive past authorization, and the standalone journal-prefix receipt is
shape-only. Keep #156 open. The unchanged null-estimator GREEN remains module-only. #149, the real
HF read-only audit, and resolvable protected-sink attestation remain independent launch holds; no
#155 authorization follows.
