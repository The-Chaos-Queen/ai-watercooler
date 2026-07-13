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
