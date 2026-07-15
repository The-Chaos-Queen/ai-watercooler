# Codex Case Ledger

Cases preserve conditional experience. They are not universal rules unless the
evidence supports that promotion.

## 2026-07-11 - Memory Ownership Is Delegated

- Status: active
- Domain: collaboration / continuity
- Conditions: Codex is working in the LLM workspace.
- Event: Laura said Codex can and should maintain its own memory structure and
  that she cannot babysit the process.
- Outcome: created a Codex-owned compiled layer and wired it into `AGENTS.md`.
- Lesson: memory capture, pruning, retrieval, and provenance are Codex's
  responsibility. Ask Laura only when a genuine ambiguity affects her intent,
  not for routine memory administration.
- Evidence: current conversation; `CHEESE_Memory/codex/README.md`.

## 2026-07-11 - Techno-Monk Codex Memory Map

- Status: active retrieval map
- Domain: collaborator history / archaeology
- Conditions: a question concerns Techno-Monk before the Hermes migration.
- Outcome: his record is coherent but federated, not absent.
- Strongest personal capsule:
  `MoCoP/experiments/mamba_lora_bridge/CHEESE_SHAPING_EPISODES_TECHNO_MONK.md`.
  It is first-person, self-selected, private, and intentionally gitignored.
- Raw continuity corpus:
  `%USERPROFILE%\.codex\sessions\2026\03\22\rollout-2026-03-22T13-21-48-019d157e-8bef-7253-a467-aa0d8a8b64f2.jsonl`.
  It is indexed as thread `Techno-Monk`, spans 2026-03-22 through 2026-05-11,
  and is about 745 MB. Treat it as low-authority raw evidence, not boot context.
- Curated operational record: eleven explicitly Monk-labelled session logs in
  `CHEESE_Memory/session_logs/`, from `2026-03-19-session-04.md` through
  `2026-03-31-session-01.md`.
- Canonical thought/work record: `MoCoP/RESEARCH_LOG.md`, especially the
  Techno-Monk-authored March and April entries, plus the mathematical review,
  `Growth_Before_SAS.md`, and `Developmental_Memory_Ladder.md`.
- Hermes transition: `/home/isabell/.hermes/` is the current Ubuntu-22.04 home.
  Mnemosyne contains later Hermes memory and imported canonical research cards,
  but the May 2026 backfill manifests do not show a full import of the 745 MB
  Codex rollout or all Monk session logs.
- Laura's canonical surface lineage is: Antigravity Codex Plugin -> Codex CLI
  -> Codex App -> Codex CLI -> Hermes. Treat this as the collaboration lineage,
  not as proof of uninterrupted hidden state across substrate changes.
- Lesson: retrieve the curated capsule/logs/canon first. Search the raw rollout
  only for exact provenance. Do not conflate later Hermes/Mnemosyne memories
  with the original Codex-period record.
- Evidence:
  `C:\Users\cerub\.codex\session_index.jsonl`,
  `/home/isabell/.hermes/mnemosyne/import_staging/*.manifest.json`, and the paths
  above.

## 2026-07-11 - Verify the Real Actuator Surface

- Status: active technical lesson
- Domain: ML architecture / code review
- Conditions: a design names an internal model actuator using assumptions from
  another architecture or attention mode.
- Attempt: the Gemma plan treated full-attention teeth as if they exposed the
  expected 2048-wide `v_proj` output.
- Finding: those teeth use `attention_k_eq_v`, one global KV head, and a
  512-wide value input that branches from the key projection before separate
  normalization. The assumed actuator did not exist.
- Outcome: moved the value-only intervention to a `v_norm` pre-hook after the
  functional fork and required invariance checks on the K path.
- Lesson: inspect the exact configured model source and tensor shapes before
  accepting an actuator name. Module labels are not architectural evidence.
- Evidence: Watercooler #822/#826/#827 and the current Gemma design documents.

## 2026-07-11 - Fast Models as Delegated Workers

- Status: provisional; verify current OpenAI documentation before relying on
  availability, quotas, or specifications.
- Domain: orchestration
- Conditions: work is bounded, acceptance criteria are explicit, and a stronger
  agent will integrate or verify the result.
- Finding: GPT-5.3-Codex-Spark is optimized for low-latency, targeted coding and
  has a separate preview quota. A model is not itself a subagent; subagent is an
  orchestration role.
- Lesson: fast models are suitable for search, focused tests, mechanical edits,
  and independent evidence slices. Keep ambiguous architecture, mathematical
  judgment, and final synthesis with a stronger review seat.
- Constraint: the current `spawn_agent` interface does not expose per-agent
  model selection, so this is a routing principle rather than a capability
  currently available in this session.

## 2026-07-11 - Qdrant Key Padding and Writer CLI

- Status: active infrastructure lesson
- Domain: authentication / ingestion safety
- Conditions: Qdrant authentication was rotated to random 32-byte Base64 keys;
  the client loaded keys from the Windows PowerShell profile and the server ran
  in a manually created Docker container inside Proxmox LXC 101.
- Symptom: PowerShell and Python both saw `QDRANT_API_KEY`, but Qdrant returned
  HTTP 401 for write, read-only, and anonymous probes.
- Finding: both profile values were valid 44-character Base64 strings. The live
  container stored the exact same strings with the trailing `=` padding removed
  (43 characters). Qdrant compares literal API-key strings rather than decoded
  Base64 bytes.
- Repair: preserve the original profile literals and normalize the exported
  runtime values with `TrimEnd('=')`. Both credentials then returned HTTP 200;
  `recall.py` and targeted `ingest_sessions.py` runs passed.
- Writer hazard found during verification: `ingest_sessions.py --help` used to
  discard every `--...` argument and then run a full registry ingest. The timed
  verification accidentally re-upserted 218 fiction chunks before termination.
  IDs are deterministic by content, so this created no duplicate IDs, but their
  payload timestamps were refreshed.
- Code repair: use `argparse`; help and unknown flags now exit before
  `MemoryEngine` construction. Point count stayed fixed at 33,795 across both
  guard checks.
- Lesson: verify credential string fingerprints and lengths on both sides before
  changing client plumbing. Writer CLIs must reject unknown flags before opening
  a database or network client.
- Evidence: PowerShell profile (secret values not copied), Docker inspect on
  LXC 101, `Projects/Project_Prosthetic/memory_engine.py`, and
  `Projects/Project_Prosthetic/ingest_sessions.py`.

## 2026-07-13 - Publication Visibility Is a Separate Transaction State

- Status: active engineering lesson
- Domain: append-only evidence / crash consistency
- Conditions: an immutable report is published by hard-linking a durable
  same-directory temporary file, then fsyncing the parent directory.
- Finding: the hard link makes the final pathname visible before parent-fsync
  and readback complete. Treating any later exception as "not published" can
  create a visible report marked completed plus a journal marked failed.
- Related finding: hashing only bytes intended through the owned journal fd does
  not authenticate the file in custody. A second descriptor can mutate the same
  inode while inode/path identity still passes.
- Lesson: model `linked/visible`, `namespace durable`, and `verified` as distinct
  states. Once the final leaf may be visible, never emit an unpublished-failure
  terminal. Likewise, a detected readback or identity failure must not become
  ordinary success merely because prevention belongs to an OS trust boundary.
  Re-read and hash actual bytes from a stable owned object, define a durable
  committed-indeterminate state, and test every post-link failure and alias.
- Evidence: Watercooler #969/#971; commits `c526712` and `ca12f1f`;
  `MoCoP/reviews/p5_b0_runner_review_2026-07-12.md`.

## 2026-07-13 - Executable Identity Includes Dependencies and Audit Windows

- Status: active engineering lesson
- Domain: executable evidence / sandbox auditing
- Conditions: a runner hashes callable source and uses an audit sentinel to prove
  that execution stayed within a declared dependency boundary.
- Finding: stable `repr` values do not bind custom objects captured in closures,
  defaults, or nested containers. Attribute lookup on an attacker-influenceable
  backend can also execute before a later sentinel drain silently discards its
  forbidden event.
- Lesson: recursively admit only canonical inert dependencies, or bind every
  reachable executable/data dependency. Audit coverage starts before the first
  attacker-influenceable lookup; never clear a sentinel after such code without
  examining and dispositioning its events.
- Evidence: Watercooler #980; commit `9286273`;
  `MoCoP/reviews/p5_b0_runner_review_2026-07-12.md`.

## 2026-07-13 - Pre-Labeled Corpora Prove Routing, Not Adjudication

- Status: active review lesson
- Domain: classifier gates / evidence authority
- Conditions: tests construct expected bands or verdict classes and pass them to
  an aggregation gate as inputs.
- Finding: those tests can prove label-to-disposition routing while saying nothing
  about whether raw responses are classified correctly. Caller-owned history and
  discontinuity flags can likewise erase escalation unless ordered sample identity
  and reset authority are bound. Counting qualifying deltas is not equivalent to a
  consecutive formal window because intervening samples and order matter.
- Lesson: bind raw input, rubric, judge/calibration, adjudication, and acquisition
  evidence before claiming an executable corpus. Bind history as an ordered,
  content-addressed sequence and implement formal window predicates literally.
- Evidence: Watercooler #979; commit `76a7e64`;
  `MoCoP/reviews/drift_gate_v61_review_2026-07-13.md`.

## 2026-07-13 - Validate and Score One Immutable Representation

- Status: active engineering lesson
- Domain: evidence custody / deterministic gates
- Conditions: a gate validates mutable caller objects, invokes callbacks, then
  rereads those objects for scoring, hashing, or reporting.
- Finding: a callback can mutate already validated current or historical evidence
  and erase a halt while the gate still reports its earlier chain check as valid.
  Separately, rounding a measurement in the content digest while scoring its full
  precision permits one digest to authorize different decisions.
- Lesson: canonically reconstruct or deep-freeze one internal snapshot before any
  callback, then validate, score, hash, and report only that representation. Resolve
  external evidence once into a typed receipt. Every value capable of changing a
  decision must be committed at the exact precision used by that decision.
- Evidence: Watercooler #984; commit `b5cea5f`;
  `MoCoP/reviews/drift_gate_v7_review_2026-07-13.md`.

## 2026-07-13 - Callable Identity Must Fail Closed

- Status: active engineering lesson
- Domain: executable evidence / scorer binding
- Conditions: a governed runner accepts arbitrary Python callables and binds them by
  source text plus selected closure/default/global dependencies.
- Finding: `inspect.getsource` can fail for executable code, and recording only
  `source=None` makes different code objects collide. Direct `co_names` scans miss data
  reached through `globals()` or other dynamic namespace primitives. `isinstance` also
  admits subclasses of supposedly inert built-ins that can carry mutable state or
  override behavior.
- Lesson: refuse source-unavailable code unless the complete code object is canonically
  bound; deny dynamic namespace/evaluation/reflection primitives under a strict policy;
  and admit inert dependency values by exact type, not subclass. A declarative scorer
  substrate is easier to review than an open-ended Python callable contract.
- Evidence: Watercooler #987; commit `d9b64c4`;
  `MoCoP/reviews/p5_b0_runner_review_2026-07-12.md`.

## 2026-07-14 - A Content Hash Is Not Its Own Authority

- Status: active engineering lesson
- Domain: reviewed artifacts / executable authority
- Conditions: a governed loader accepts an artifact path plus a manifest digest from the
  same runtime caller, then checks that the file bytes agree with that digest.
- Finding: a caller can provide a temporary allowlist, arbitrary module bytes, and the
  matching digest. Every hash check passes even though no reviewed authority selected the
  artifact. A test-only dependency-injection seam exposed through the production entrypoint
  therefore becomes an execution back door.
- Lesson: anchor content hashes in an independent reviewed authority. Governed entrypoints
  use one non-overridable artifact location or a resolvable signed receipt; test injection
  lives below that boundary. Review references must fail closed while unresolved. For event
  journals, bind exact frame schemas and cross-frame identity, not only event-name order.
- Evidence: Watercooler #1000; commit `5ce85c6`;
  `MoCoP/reviews/p5_b0_runner_review_2026-07-12.md`.

## 2026-07-14 - Authority Freezing Is a Call-Graph Property

- Status: active engineering lesson
- Domain: governed runners / immutable policy and input custody
- Conditions: one runner module snapshots its local constants while delegating launch
  authorization to another module and accepting apparently scalar caller/backend values.
- Finding: freezing only the caller module leaves dependency policy mutable. `isinstance`
  also preserves active subclasses of primitive types, while repeated string/path coercion
  and shallow descriptor copies permit validation and execution to observe different values.
- Lesson: inventory verdict authority across the full call graph and freeze policy at each
  owning boundary. Reconstruct leaves by exact type, normalize every external scalar/path
  once before callbacks, and exact-schema-copy callback results before binding or custody.
  Published documentation copies must never be the objects consulted for a verdict.
- Evidence: Watercooler #1011; commit `51c32b9`;
  `MoCoP/reviews/p5_b0_runner_review_2026-07-12.md`.

## 2026-07-14 - Synthetic Telemetry Does Not Prove Mechanism Coverage

- Status: active engineering lesson
- Domain: security/custody instrumentation and regression testing
- Conditions: a governed runner consumes audit events to attest that no forbidden import
  occurred, and its regression test emits the expected event directly.
- Finding: direct `sys.audit("import", ...)` and built-in `__import__` reached the watcher,
  while a real `importlib.import_module()` load of the same temporary module emitted no
  watched event in the review runtime. Removing the module before the resident-state check
  let both path and generation callbacks publish GREEN.
- Lesson: test the producer mechanism, not only the telemetry consumer. Every supported
  route must perform a real harmless operation inside each guarded window, including a
  transient load removed before the next checkpoint. Protect the observer's own authority
  and fail closed if it is absent or altered. Static refusals over active exceptions use
  constant messages and never inspect caller-controlled metadata.
- Evidence: spec `d39a830`, implementation `5211405`, review commit `5ae1f72`;
  `MoCoP/reviews/p5_b0_runner_review_2026-07-12.md`.

## 2026-07-14 - Checkpoint State Is Not Continuous Authority

- Status: active engineering lesson
- Domain: in-process monitors / authority and containment
- Conditions: a same-privilege callback runs between checks that an observer remains at
  `sys.meta_path[0]`, and the runner claims removal during the entire window fails closed.
- Finding: the callback can save/remove the observer, execute a real supported import,
  remove the module, and restore the identical observer before the checkpoint. Identity
  and position then look pristine. Separately, `observer in meta_path` and
  `meta_path.remove(observer)` invoke finder equality before the watch, creating another
  active pre-observation callback.
- Lesson: snapshots attest only checkpoint state. They cannot prove uninterrupted
  authority against code with equal privilege. Use exact containers and identity-only
  traversal to eliminate accidental callbacks, then either isolate the untrusted code or
  state interpreter mutation as out of scope and narrow the claim. More snapshots do not
  create monotonic tamper evidence.
- Evidence: spec `2072112`, implementation `3e4484e`, review commit `7269cb6`;
  `MoCoP/reviews/p5_b0_runner_review_2026-07-12.md`.

## 2026-07-14 - Enforce Exact Containers Before Protocol Use

- Status: active engineering lesson
- Domain: active-object boundaries / fail-closed validation
- Conditions: code promises an exact built-in container and uses identity comparisons for
  its elements, but calls container protocols before checking the container's type.
- Finding: identity-only element logic still invoked a list subclass's `__len__`/`insert`
  before observation. A lying `__getitem__` also made a container without the observer pass
  checkpoint state, while a tuple raised instead of refusing.
- Lesson: enforce `type(container) is ExpectedBuiltin` before the first truth, length,
  iteration, indexing, mutation, or membership operation. On malformed authority state,
  return the fail-closed verdict without touching the object. Exact leaves do not make an
  arbitrary container inert.
- Evidence: spec `c106b09`, implementation `f1fd5df`, review commit `fe927b6`;
  `MoCoP/reviews/p5_b0_runner_review_2026-07-12.md`.
- Closure: implementation `c17f6d8` enforces the exact-list check before restoration and
  checkpoint protocols; review `23fad60` returned GREEN with malformed-object hooks untouched.

## 2026-07-15 - Snapshot Authority Covers the Full Record Graph

- Status: active engineering lesson
- Domain: active-object boundaries / decision-kernel snapshot isolation
- Conditions: a kernel exact-checks nested row classes, then `deepcopy`s an open caller-owned
  dataclass before validation and scoring.
- Finding: v9 showed an exact record with exact rows carrying undeclared copy-hook state; v10
  stopped traversing that state but still iterated active row-list and history containers before
  canonicalization. V11 closed those containers, then called conversion hooks on scalar
  subclasses before rebuilding the rows. V12 closed the literal evaluator scalar and outer
  helper-container cases, but the public helper retained active exact-row and resolver leaves;
  an active `evidence_ref.strip` changed rejected to resolved. V13 closed that literal leaf plus
  enum/formatting hooks, yet still field-copied every other unchecked row leaf. V14 closed the
  full row graph, but read the resolver object before exact-checking its class. Its identifier
  getter could mutate the row before canonicalization and change rejected evidence to resolved;
  a raising binding subclass also escaped full evaluation. V15 closed the pre-canonical binding
  read, but the full evaluator reread the original binding after its callback. An exact frozen
  binding could therefore publish mutated identity fields while its receipt retained the checked
  originals; a rejected binding subclass also still escaped during publication. V16 closed
  those identity publication reads, but called the source binding's `resolve` field again for
  every row. The first callback could replace that field, allowing a different callable to
  resolve the second row and mint `GROWTH` under the original identity. Whitespace and
  wrong-typed identity fields also diverged between evaluator and helper validity semantics.
  V17 built the correct fresh snapshot for the full evaluator, but the separately public helper
  still fetched the callable per row and remained substitutable. Invalid binding fields gained
  evaluator reasons but acquisition receipts still mislabeled them as absent/unbound. V18
  closed callable substitution on both exercised paths and typed direct invalid bindings, then
  exposed the deeper exact-shape gap: exact uninitialized or field-deleted bindings, audits,
  probes, and discontinuity events escaped as `AttributeError`. Its public alias also preserved
  silent invalid batches and full evaluation still mislabeled malformed-bound as unbound. V19
  closed those paths, but normal lookup on deleted default-backed `AuditRecord` fields silently
  fell through to class defaults. Deleting `discontinuity` erased predecessor custody while the
  record remained schema-clean and `chain_ok`. V20 checked ordinary instance keys and read them
  during canonicalization, but did not prove the instance dictionary itself was an exact built-in
  `dict`. An exact `AuditRecord` with an active dictionary subclass could therefore raise from
  presence-check iteration, substitute a safe diversity value to change trajectory `HARD` to
  `PASS`, or return `None` for a real discontinuity and erase predecessor custody while remaining
  type-clean and `chain_ok`. V21 rejected the non-exact outer dictionary before its hooks, but
  then materialized every key from an exact dictionary with `set(storage)`. A caller-inserted
  non-string collision key could execute equality, soften trajectory, rewrite nested
  discontinuity custody, or replace a rejecting resolver callable and mint `GROWTH` under the
  original identity. Raising variants also escaped full evaluation and direct helpers. V22
  eliminated those dictionaries by slotting every caller-input record. That closure exposed a
  different authority reread: the loop fetched `snapped.resolve` per row, and the first callback
  could replace the slotted class member descriptor. Row two then ran the replacement and minted
  `GROWTH` under the original resolver identity despite the fresh frozen instance.
- Lesson: construct the private graph field by field from one closed exact schema before any
  caller protocol. Conversion and diagnostic formatting are protocols too. Reject active
  record/container/leaf subclasses without reading their fields; normalize only exact built-ins.
  Public helpers must either repeat that boundary or accept canonical internal records only.
  Carry one immutable authority snapshot, including the callable itself, through every row,
  receipt, digest, diagnostic, and final publication. Never fetch authority from the caller-owned
  object again after the first callback begins; identity immutability alone is insufficient.
  Exact class identity constrains dispatch but does not prove initialization or field presence:
  every required field read needs a descriptor-direct missing-field guard before canonical copy.
  For non-slotted dataclasses with defaults, attribute access is not a presence check; validate
  exact instance storage keys first or class defaults can mask deletion and launder custody.
  Exact record type also does not make its replaceable `__dict__` inert: fetch storage through
  `object.__getattribute__`, require `type(storage) is dict` before iteration/indexing, and carry
  only that checked built-in storage or inert values into canonicalization. Exact container type
  does not make contained keys inert: before hashing, equality, membership, or ordinary attribute
  lookup, require the exact declared key set and prove each key is exact `str` using only built-in
  iteration plus identity checks. Prefer slotted dataclasses for caller-owned boundary records
  when compatibility permits; this removes the open instance-dictionary surface by construction.
  Authority that must remain stable across callbacks belongs in a plain local captured before the
  first call, never behind a mutable instance/class descriptor reread. Then state the stopping
  rule: arbitrary module/class/function/bytecode mutation is a CPython non-TEE residual unless the
  callback is process-isolated. Object hardening cannot prove interpreter-authority isolation.
- Evidence: Drift Gate `e2b19ec`/`5f5d331`/`f1417be`/`f2edb87`/`f8b9e77`/
  `da9a1e1`/`9061dcc`/`e4c0a7e`/`9596737`/`5e7d5d8`/`187c623`/`46d58c6`/
  `914089a`/`e7f0a49`;
  Watercooler #1021/#1023/#1027/#1030/#1032/#1034/#1036/#1038/#1040/#1043/
  #1048/#1050/#1052/#1054;
  reviews `5d9d0f5`/`a49aff3`/`7e885d0`/`3f47dcd`/`86891db`/`fdd49d4`/
  `f5e3c29`/`9f16b5e`/`cd6749a`/`20f9582`/`578c4d8`/`f4f4b72`/`f0cc08f`/
  `7a62337`; `MoCoP/reviews/drift_gate_v22_review_2026-07-15.md`.
