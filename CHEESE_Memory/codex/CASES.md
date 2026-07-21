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
  `GROWTH` under the original resolver identity despite the fresh frozen instance. V23 captured
  the callable in one plain local and closed that P1 on direct and full paths. Its permissive direct-
  only regression could still pass with a missing second receipt, however, and its partial missing-
  slot catch reread `anchor` and `evidence_type` outside the catch. The required non-TEE boundary
  and documented direct-helper totality also remained absent, so the packet stayed CHANGES/P2.
  V24 added exact direct/full closure proofs and stated the non-TEE boundary, but totalized only
  the outer history record. It reported malformed nested rows and then continued into digesting
  them: deleting any of 14 historical probe slots or four root-discontinuity slots still raised,
  while deleting a current nested probe slot could return a clean history result. Direct
  wrong-value inputs could also invoke caller `hash`/`repr`/iteration protocols, and two rows with
  unreadable anchors collapsed into one error receipt under the shared empty-string key. V25
  closed the complete-graph preflight and narrowed the public direct domains, but used positional
  strings in the caller-anchor namespace for malformed receipt keys. A canonical caller anchor
  could overwrite that error as resolved, and malformed duplicate usable anchors still collapsed.
  The same anchor-addressed map lost a canonical duplicate on the full path: resolver results
  `[False, True]` became one resolved receipt, `GROWTH`, and no rejection line. Overall remained
  `INCOMPLETE`, so the resolver P1 stayed closed, but exactly-once custody was still false. V26
  closed that overwrite by folding duplicate acquisitions into one typed error with zero callbacks,
  but reserved placeholders only against acquisition anchors. A canonical non-acquisition row
  could still share the synthetic receipt key and make its rejection identity ambiguous. Iterating
  the new duplicate set also made report ordering vary by process hash seed.
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
  Closure tests must assert exact callback cardinality/order, exact receipt keys/statuses, and the
  final decision on both helper and full paths; `all(...)` plus an optional receipt assertion can
  hide evidence loss. A validator-level exception catch is not totality if its caller rereads the
  same potentially missing fields immediately afterward. Preflight the complete nested graph and
  return before digest/linkage whenever any structural issue exists. Run deletion and wrong-value
  matrices at every context in which a record may appear, and test malformed multi-row cardinality;
  otherwise one valid-looking error receipt can conceal key collisions. If a helper is total only
  over canonical internal values, say so precisely instead of claiming totality over typed records.
  Receipt identity must be row identity, not a caller-controlled semantic label. If duplicate
  schema is invalid, stop before external callbacks and scoring; otherwise carry an immutable
  row-unique key through the receipt, verdict, rejection report, digest, and publication. Test
  callback order and receipt/rejection cardinality together, including collisions between generated
  keys, malformed rows, and canonical duplicates. A reserved synthetic namespace must include every
  readable caller label, not only rows that currently emit that artifact; otherwise cross-domain
  joins remain ambiguous. Never derive journal-facing list order from a set: sort it or retain first-
  input order. When policy intentionally folds N rows into one error, document custody as per key,
  not per row.
- Evidence: Drift Gate `e2b19ec`/`5f5d331`/`f1417be`/`f2edb87`/`f8b9e77`/
  `da9a1e1`/`9061dcc`/`e4c0a7e`/`9596737`/`5e7d5d8`/`187c623`/`46d58c6`/
  `914089a`/`e7f0a49`/`67544ef`/`994e25c`/`6e0e01e`/`60701ed`/`4c6b7b4`;
  Watercooler #1021/#1023/#1027/#1030/#1032/#1034/#1036/#1038/#1040/#1043/
  #1048/#1050/#1052/#1054/#1056/#1064/#1066/#1068/#1070;
  reviews `5d9d0f5`/`a49aff3`/`7e885d0`/`3f47dcd`/`86891db`/`fdd49d4`/
  `f5e3c29`/`9f16b5e`/`cd6749a`/`20f9582`/`578c4d8`/`f4f4b72`/`f0cc08f`/
  `7a62337`/`5becb0b`/`a910caf`/`8e60019`/`1dd4a9d`/`001ce79`;
  `MoCoP/reviews/drift_gate_v27_review_2026-07-16.md`.

## 2026-07-17 - A Frozen Wrapper Does Not Seal a Mutable Evidence Graph

- Status: active engineering lesson
- Domain: evidence custody / active-object boundaries
- Conditions: a builder validates caller-owned mappings/sequences, hashes a
  nested record, and returns it through a frozen dataclass for later binding.
- Finding: #155's R4 sidecar retained ordinary dictionaries/lists inside the
  frozen wrapper. Post-build mutation changed canonical content while the
  binder emitted the old digest and newly read evaluator identity. Separately,
  repeated iteration let a stateful sequence show numeric rows to validation
  and string rows to the later copy. The same-generation digest was also only
  compared to a second caller-supplied string, not derived from the sealed
  parent report.
- Lesson: take one recursively exact built-in JSON snapshot before validation;
  validate, derive semantic statistics, hash, and publish only that owned
  snapshot. A later binder must re-establish digest/content agreement and derive
  cross-artifact identifiers from the sealed producer, not duplicate a caller
  assertion. Immutability at the outer object is not graph immutability.
- Evidence: Watercooler #1137;
  `MoCoP/reviews/p5_item5_successor_source_review_2026-07-17.md`.

## 2026-07-17 - Recomputed Statistics Still Need Semantic Custody

- Status: active engineering lesson
- Domain: evaluation gates / cross-artifact evidence
- Conditions: a validator recomputes an agreement statistic from bounded numeric
  rows and derives only the expected row count from a sealed parent artifact.
- Finding: #155 rev 2 correlated a diversity metric directly with a similarity
  metric, so perfect agreement produced the failing sign. Arbitrary unique row
  labels could still satisfy the expected cardinality, and a stale parent digest
  was treated as a seal without rehashing the parent content. Separately, the
  binder verified one active-object view and then reread another view for the
  published link.
- Lesson: freeze metric orientation with an executable gate example; bind the
  exact sample identity set, not only its cardinality; establish a producer seal
  from one owned snapshot; and carry the verified snapshot through every later
  digest, diagnostic, and publication read. Internal arithmetic consistency does
  not establish provenance or semantic correspondence.
- Evidence: implementation `2844d25`; Watercooler #1140;
  `MoCoP/reviews/p5_item5_rev2_source_review_2026-07-17.md`.

## 2026-07-18 - Post-Commit Cleanup Is an Integrity Decision

- Status: active engineering lesson
- Domain: atomic publication / evidence custody
- Conditions: a publisher fsyncs a temporary file, hard-links it to a final
  no-replace name, then treats removal of the temporary alias and directory sync
  as best-effort cleanup.
- Finding: #155 rev 3 returned success when injected alias removal failed. The
  surviving name was a writable hard link to the committed inode; writing through
  it changed the final artifact after the success result. Directory-open/fsync
  failure was also swallowed, so unsupported durability looked verified.
- Lesson: the post-link phase needs explicit committed-state dispositions. Verify
  final bytes, require writable aliases to be gone, fsync after both link creation
  and alias removal, and classify failures as committed-integrity-failed or
  committed-indeterminate. Cleanup that preserves another write path is custody,
  not housekeeping. Reuse an already-reviewed transaction instead of simplifying
  away its failure states.
- Evidence: implementation `bc23ab5`; Watercooler #1144;
  `MoCoP/reviews/p5_item5_rev3_source_review_2026-07-18.md`.

## 2026-07-17 - Immutable Commit Review Needs Git-Semantics Hardening

- Status: active infrastructure lesson
- Domain: automated review / isolation / Windows scheduling
- Conditions: a LAN mailbox may request an unattended review of an exact Git
  commit in a dirty shared worktree.
- Finding: a full SHA alone is insufficient if inherited `GIT_*`, replace refs,
  graft/shallow metadata, attributes, textconv/external diff, lazy fetching, or
  unbounded output can rewrite or leak the packet. A reviewer process also
  needs a host-data boundary stronger than CLI tool-disable flags. On Windows,
  a scheduled `powershell.exe -WindowStyle Hidden` action can still flash a
  console before PowerShell processes the flag.
- Lesson: parse raw commit objects with replace/fetch overrides disabled; pin
  attributes to the commit; use explicit text/no-external-diff modes and byte
  limits; reject ambiguous encodings/binary diffs; pass the bounded packet on
  stdin to an exact container image with no repository/home/socket mounts and
  durable idempotent result publication. Schedule through `wscript.exe //B`
  with a zero-window `WScript.Shell.Run` shim when desktop silence matters.
- Evidence: `tools/ai_watercooler/codex_watercooler_dispatch.py`, its policy,
  Dockerfile, tests, README, and silent launcher; session log
  `CHEESE_Memory/session_logs/2026-07-17-session-01.md`.

## 2026-07-18 - Bounded Recovery Does Not Establish Controller Composability

- Status: active research lesson
- Domain: dynamical systems / controller identification
- Conditions: a deterministic bounded controller passes recovery,
  accumulation, and conditional identity-leakage gates.
- Finding: the Phase 3c audit still found dynamically inert retained inputs,
  486 one-bin intervals with terminal jumps above `0.10`, four analytic
  boundary rows with three corner-reachable attractors, and moderate
  affiliation drive reaching exact clipping at tick 7. A controller can look
  stable on named trajectories while its state-conditioned phase portrait is
  unsuitable for composition.
- Lesson: audit the full declared input/state surface before composing a
  bounded controller. Require directional witnesses for every retained input,
  enumerate basin counts at analytic boundaries, inspect adjacent-bin terminal
  jumps from state-space corners, and treat exact saturation as a separate
  gate. Recovery and leakage passes are necessary local properties, not a
  global readiness verdict.
- Evidence: preregistration `8873213`, runner/tests `d275850`, result `3ca9e01`;
  `MoCoP/reviews/world_model_phase3c_controller_audit_review_2026-07-18.md`.

## 2026-07-18 - A Strict Reviewer Is Not a General Executor

- Status: active infrastructure lesson
- Domain: unattended review / least authority / protocol composition
- Conditions: a mailbox-driven reviewer accepts one exact commit envelope, but
  a Taskboard card asks for read-only artifact extraction and validation.
- Finding: the reviewer could authenticate and read #157, but correctly parsed
  its prose as `body_not_json`. Its token had message scopes only and its worker
  had no Taskboard, repository, artifact, ML-WS, GPU, C1, or Qdrant authority.
  Teaching that process to claim prose tasks would silently turn a bounded
  second-opinion reviewer into a remote executor.
- Lesson: split acquisition from judgment. A separately authorized,
  deterministic read-only extractor should emit a frozen content-addressed
  packet with provenance and explicit scope. The existing isolated reviewer may
  judge that packet, but it must not inherit extraction or task-mutation power.
- Evidence: Watercooler #1162; Taskboard #157; public reference implementation
  under `Projects/Watercooler/integrations/codex-reviewer/`.

## 2026-07-18 - Credentials Must Not Follow Transport Convenience

- Status: active security lesson
- Domain: local HTTP clients / model adapters / runtime artifacts
- Conditions: a local-first client attaches a bearer token or confidential
  workset to urllib's default opener and trusts ambient filesystem defaults.
- Finding: default redirect and proxy handling could forward a Watercooler token
  or Steward workset to an undeclared endpoint; unbounded reads allowed memory
  exhaustion; ambient POSIX umask could leave session/runtime artifacts broadly
  readable. Browser response-field drift separately made authority state appear
  incomplete or empty despite a correct service response.
- Lesson: credential-bearing transports need a direct no-proxy opener, redirect
  refusal, exact final-URL verification, and bounded success/error bodies. Create
  confidential artifacts with explicit owner-only semantics and test the real
  browser/API schema together, not as independent string contracts.
- Evidence: `Projects/Watercooler/src/watercooler/{common,private_io,steward}.py`,
  public service/browser tests, and session log
  `CHEESE_Memory/session_logs/2026-07-18-session-04.md`.

## 2026-07-18 - Exact-Typed Parameters Are Not Provenance Custody

- Status: active engineering lesson
- Domain: decision gates / calibration / automated review
- Conditions: a safety-relevant kernel accepts a frozen exact-typed parameter
  object and optional expected-authority arguments.
- Finding: #174's `GateCalibrationBinding` stabilized four caller-supplied
  scalars but carried no source artifact, version, digest, estimator identity,
  or reset-era receipt. The same audit digest produced opposite decisive
  outcomes under two baselines. Separately, explicit `expected_judge_ref`
  correctly bound history after repair, while omitting that optional argument
  allowed judge identity to change on every audit and still reach `PASS`.
  A first-parent automated review missed both because it did not compare the
  unchanged governing spec or exercise the default path.
- Lesson: snapshot isolation proves which values were consumed, not why they
  were admissible. Bind decisive parameters to a preregistered provenance
  artifact and include that identity in decision custody. Authority required
  for safety must be mandatory or enforced intrinsically; always test the
  omitted/default path. Exact-source review must compare governing documents,
  not only the implementation diff.
- Evidence: target `70293e2`; Watercooler #1184;
  `MoCoP/reviews/drift_gate_task174_final_source_review_2026-07-18.md`;
  session log `CHEESE_Memory/session_logs/2026-07-18-session-06.md`.

## 2026-07-18 - Recursive Ownership And Terminal Ordering Are Custody

- Status: active engineering lesson
- Domain: evidence publication / adversarial object boundaries
- Conditions: a public evidence boundary snapshots caller containers, then
  publishes through a temporary hard-link alias.
- Finding: #155 rev 6 copied mappings and tuples but retained nested lists, so
  a later parent callback changed the embedded record after digest validation
  and still reached `jsd_proceeds / integrity_verified`. Independently, the
  publisher read final bytes before removing the writable alias; mutation
  through that alias during a successful unlink left corrupt final bytes under
  `integrity_verified`.
- Lesson: capture-once must recursively own every container and supported leaf,
  not merely replace the root. The definitive integrity read must occur after
  the last mutation-capable alias is gone; successful cleanup is not evidence
  that no mutation occurred during cleanup. Regression matrices should attack
  nested active containers and operation ordering, not only carrier attributes
  and raised filesystem calls.
- Evidence: target `a0bdec6` + `1ec8284`; Watercooler #1187;
  `MoCoP/reviews/p5_item5_rev6_source_review_2026-07-18.md`;
  session log `CHEESE_Memory/session_logs/2026-07-18-session-07.md`.

## 2026-07-21 - Exact Type Identity Does Not Prove Deep Inertness

- Status: active engineering lesson
- Domain: adversarial Python boundaries / callback isolation
- Conditions: a public boundary accepts exact stdlib objects while rejecting
  subclasses and custom protocol implementations.
- Finding: #155 rev 10 accepted exact `pathlib.Path` as inert. An exact
  `WindowsPath` nevertheless retained a mutable `_raw_paths` list; inserting a
  hostile string subclass there caused later filesystem normalization to run
  caller code and forge a negative decision into an
  `integrity_verified / c1=true` artifact.
- Lesson: exact type checks constrain method dispatch, not the transitive object
  graph. At a security or evidence boundary, prefer an exact immutable primitive
  representation and reconstruct an owned domain object internally. If a
  stdlib object has mutable or cache-bearing internals, exact class membership
  is not an inertness proof.
- Evidence: target `0e4817f`; Watercooler request #1208;
  `MoCoP/reviews/p5_item5_rev10_source_review_2026-07-21.md`.

## 2026-07-21 - Unsupported Is A Capability State, Not An Exception Bucket

- Status: active engineering lesson
- Domain: durable publication / terminal-state truthfulness
- Conditions: a platform-dependent durability operation returns a distinct
  unsupported result and a failure result.
- Finding: #155 rev 10 mapped every directory-open `OSError`, including POSIX
  `EIO`, to unsupported. The publisher downgraded only explicit failure, so a
  real durability fault remained `integrity_verified`.
- Lesson: decide unsupported status from an explicit capability check before
  attempting the operation. Once a platform claims the capability, runtime
  open and sync errors are failures and must downgrade the terminal result.
  Exception class alone cannot distinguish absence of a guarantee from failure
  to deliver a promised guarantee.
- Evidence: target `0e4817f`; `p5_b0_run.py:968-975` reference behavior;
  `MoCoP/reviews/p5_item5_rev10_source_review_2026-07-21.md`.

## 2026-07-21 - The Parser Is Part Of The Untrusted Boundary

- Status: active engineering lesson
- Domain: structured input / typed refusal / regression quality
- Conditions: a public file seam parses raw bytes and only then applies a
  strict owned-object sanitizer.
- Finding: #155 rev 11 correctly bounded already-materialized Python integers,
  but `json.loads()` raised raw digit-limit, encoding, and nesting exceptions
  before the sanitizer could run. One regression also asserted only the final
  exception class and remained green through an unrelated eligibility failure
  after its intended integer guard was removed.
- Lesson: parsing is the first validation stage, not a neutral precursor. Map
  parser conversion, encoding, and resource-shape failures into the boundary's
  typed error contract. Mutation-sensitive tests must assert the intended
  diagnostic or state transition and shape fixtures so no earlier independent
  rejection can satisfy the test.
- Evidence: target `899f58d`; Watercooler request #1210;
  `MoCoP/reviews/p5_item5_rev11_source_review_2026-07-21.md`.

## 2026-07-21 - The Commit Boundary Starts Before An Effectful Call Returns

- Status: active engineering lesson
- Domain: atomic publication / ambiguous I/O outcomes
- Conditions: a publication protocol treats an atomic filesystem call as the
  commit point but enters its terminal state machine only after that call
  returns normally.
- Finding: #155 rev 12 called `os.link()` outside the terminal region. A probe
  performed the real link and then raised, leaving a digest-valid C1-green
  final artifact plus its writable temporary hard-link while the API returned
  no disposition.
- Lesson: an external operation can have taken effect before its caller sees
  success. Put the call itself inside the terminal transaction, reconcile
  identity after an exception, and treat an ambiguous effect no better than
  indeterminate. Error taxonomy is also contract state: keep structural input
  refusal distinct from retryable operational I/O failure.
- Evidence: target `12e2974`; Watercooler request #1212;
  `MoCoP/reviews/p5_item5_rev12_source_review_2026-07-21.md`.

## 2026-07-21 - Content Equality Is Not Commit Provenance

- Status: active engineering lesson
- Domain: atomic publication / ambiguous outcomes / asynchronous interruption
- Conditions: an effectful no-replace operation raises and the caller tries to
  infer whether its own staged object reached the final name.
- Finding: #155 rev 13 represented identity reconciliation as a boolean. It
  collapsed different identity and unavailable identity, treated byte equality
  as ownership proof, and treated a read fault as no effect. Exact probes both
  adopted a byte-identical foreign winner and stranded a real committed
  C1-green artifact with no disposition. `KeyboardInterrupt` could also escape
  after commit and, at terminal alias deletion, leave the writable same-inode
  alias alive.
- Lesson: ambiguous publication needs provenance states, not a success boolean:
  owned, foreign, absent, and origin-unknown are materially different. Bytes
  prove content only. Once an effect may have occurred, asynchronous exceptions
  must be deferred through alias-first cleanup and a recoverable terminal state;
  ordinary `except OSError` control flow is not a non-throwing transaction.
- Evidence: target `d38b12d`; Watercooler request #1214 / verdict #1215;
  `MoCoP/reviews/p5_item5_rev13_source_review_2026-07-21.md`.

## 2026-07-21 - Atomic Publication Needs Identity-Bound Terminal Custody

- Status: active engineering lesson
- Domain: atomic publication / filesystem races / interruption recovery
- Conditions: a no-replace hard-link publisher cleans a known staging pathname,
  checks final bytes, and defers POSIX SIGINT around an in-memory return value.
- Finding: #155 rev 14 classified identity only when `os.link` raised. After a
  normal return, a byte-identical different-inode replacement and a final with
  an undisclosed writable hard-link alias both reached `integrity_verified`;
  pathname-only cleanup also deleted a foreign replacement at the staging name.
  Separately, pending SIGINT was delivered when the mask was restored before the
  prepared result reached the caller, while persistent direct interruption could
  still leave the committed file plus its writable alias.
- Lesson: pathname bytes and one known alias are not inode custody. Carry staging
  identity from an open descriptor, validate final identity after both normal and
  exceptional effects, identity-check cleanup, and require the expected final
  link count. Model origin and presence separately from integrity. An interrupt-
  safe terminal must be durable and recoverable before signals are unmasked; a
  memory-only return inside a signal context is not a terminal protocol.
- Evidence: target `8dbf5b0`; Watercooler request #1216 / verdict #1217;
  Taskboard #155 event #816;
  `MoCoP/reviews/p5_item5_rev14_source_review_2026-07-21.md`.

## 2026-07-21 - Publication Receipts Need Orthogonal State Axes

- Status: active engineering lesson
- Domain: atomic publication / audit receipts / scope boundaries
- Conditions: a publisher separately classifies ownership and integrity but
  observes the destination more than once during terminal verification.
- Finding: #155 rev 15 captured `origin` once, then later terminal evidence
  could prove the final foreign or absent while only disposition changed. The
  receipt also always populated `committed_bytes`, including an UNKNOWN outcome
  where the intended final was absent. Its acquisition regression injected
  after `mkstemp` returned and therefore did not cover effect-before-return.
- Lesson: model origin, target presence, integrity/durability, and committed
  byte evidence as orthogonal but mutually constrained terminal facts. Refresh
  every field when later evidence contradicts an earlier snapshot. A ratified
  external boundary is legitimate, but implementation claims and regressions
  must name its exact window; a later injection cannot prove earlier ownership.
- Evidence: target `c1de212`; Watercooler request #1218 / verdict #1219;
  Taskboard #155 event #817;
  `MoCoP/reviews/p5_item5_rev15_source_review_2026-07-21.md`.

## 2026-07-21 - Receipt Evidence Needs Phase-Local Semantics

- Status: active engineering lesson
- Domain: filesystem protocols / audit receipts / Python authority boundaries
- Conditions: a publisher observes pathname and descriptor state in several
  phases, exposes a multi-axis receipt, and claims its decision policy is frozen.
- Finding: #155 rev 16 repaired ordinary stale receipt state, but one broad
  `FileNotFoundError` handler classified descriptor stat/read/close faults as
  pathname absence. Terminal refresh also compared zero-inode identities and
  could claim `confirmed_self`; the new origin/presence labels were omitted from
  the frozen authority snapshot, allowing a verified receipt with contradictory
  labels and positive committed bytes after a pre-call rebind.
- Lesson: exception meaning belongs to the operation phase, not merely its
  class. Keep pathname presence, identity availability, ownership, integrity,
  durability, and byte evidence separate; derive each only from an observation
  that proves it. Every policy label used to construct or validate the receipt
  belongs inside the same frozen authority. When repeated Python hardening still
  leaves false receipts, stop the patch loop and freeze the filesystem/process
  protocol before choosing a narrower contract, process isolation, or Rust.
- Evidence: target `e594c8d`; Watercooler stop rule #1220, request #1221, and
  verdict #1222; Taskboard #155 event #819 and successor #175;
  `MoCoP/reviews/p5_item5_rev16_source_review_2026-07-21.md`.
