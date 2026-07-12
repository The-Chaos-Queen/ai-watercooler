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
