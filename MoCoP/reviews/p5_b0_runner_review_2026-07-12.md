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
