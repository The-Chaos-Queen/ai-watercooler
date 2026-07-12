# Findings

Evidence posture: the Python attachments are treated as implemented code; test coverage described in the contract is treated as reported behavior because the test files are not attached; `REPORT.md` is treated as scoped experiment evidence, not an independently reproduced artifact; future connections are design intent only.

## BLOCKER

### B1 — There is no executable architecture-wide composition contract

**Reference:** `APPRAISAL_MODULATORY_CONTROLLER_CONTRACT_2026-07-12.md`, Purpose and Non-Goals, lines 8–21 and 179–186; `world_model_events.py:127–212`; `modulatory_controller.py:243–261`. The contract explicitly says there is no adapter from either `world_model_trace` or `friction_world_model.CognitiveState`.

**Violated claim or invariant:** A composed “minimal World Model” needs a single, deterministic causal path from committed forecast, through observed outcome and semantic interpretation, to one controller transition. That path is currently undefined.

**Concrete failure trace:** A valid `OutcomeRecord(observation="permission_denied")` has no specified mapping to `outcome_mismatch`, `goal_blocked`, `threat_observed`, or no event. Conversely, `EventSourceRef(kind="world_model_trace", ...)` does not identify whether its hash refers to a pre-action forecast or a post-action outcome. Both a forecast-derived “fact” and an outcome-derived fact can therefore be type-valid. After appraisal, `ControllerStep` contains only output states; it has no session, step, prior-state hash, appraisal hash, configuration identity, or processed-event cursor. Applying the same appraisal twice is indistinguishable from processing two legitimate turns.

**Smallest decisive repair or test:** Specify and gate three one-way contracts:

1. `OutcomeRecord -> DerivedWorldEventBatch`, with parent commit hash, parent outcome hash, source record type, derivation-rule version, session/domain/turn, and epistemic status.
2. `WorldEventBatch -> AppraisalResult`, requiring one session, one domain, one appraisal tick, and exactly-once source consumption.
3. `ControllerTransition`, binding prior-state hash, appraisal hash, controller-config hash, `dt`, session/step identity, and output hash.

A fixed end-to-end fixture must produce exactly one canonical transition, while alternate parentage, replay, reordering, or forecast-as-observation variants are rejected. Until that exists, these are several compatible sidecars sharing a name, not one executable architecture.

---

### B2 — The trace does not itself enforce causal pre-action commitment

**Reference:** `world_model_trace.py:161–247`, `PreActionCommit`; `world_model_trace.py:321–343`, `validate_trace_pair`. The old audit reports that a separate Phase 2 runner journaled and `fsync`ed forecasts before acting, but that is an external runner property, not an invariant of this schema.

**Violated claim or invariant:** A forecast must be irrevocably committed before the outcome becomes available.

**Concrete failure trace:** After learning that the outcome is `success`, a caller can construct:

* commit: `event_index=10`, `committed_at_ns=100`, point mass on `success`;
* outcome: `event_index=12`, `observed_at_ns=101`, matching commit hash.

The supplied validator accepts this. The timestamps and sequence numbers are caller-provided integers. `state_ref`, `action`, and `estimator_id` are only checked as non-empty strings. There is no state snapshot hash, candidate-action-set hash, estimator artifact hash, action-execution receipt, append-only journal identity, or trusted sequence allocator. Likewise, a source digest is checked for hexadecimal format, not against the referenced source bytes.

**Smallest decisive repair or test:** Put the invariant in an append-only journal, not in object constructors. The journal must allocate sequence numbers, bind canonical state/action/estimator artifacts, durably write the commit before invoking the environment, and then chain an action-execution receipt and outcome. Run crash injection at every write/action boundary. The gate is zero retrospectively fabricated histories accepted and proof that every executed action has a previously durable commit. The old Phase 2 custody report is encouraging, but it does not make the current trace schema independently sufficient.

---

### B3 — Novel outcomes are rejected instead of recorded as model failures

**Reference:** `world_model_trace.py:340–343`, where `validate_trace_pair` rejects an observation outside the committed probability support.

**Violated claim or invariant:** Every actual outcome must remain recordable and scoreable, especially catastrophic or previously unknown outcomes.

**Concrete failure trace:** The observer commits:

```text
success: 0.90
timeout: 0.10
```

The tool returns `permission_denied`. `OutcomeRecord` can represent the result, but the pair validator rejects it because the label is outside forecast support. The model’s most informative failure is therefore not a valid scored pair. In a learned-observer evaluation, this creates a direct route to failure censoring.

**Smallest decisive repair or test:** Every domain must either:

* bind a proven-complete, versioned observation ontology containing a mandatory `OTHER/UNKNOWN` class with committed probability mass; or
* allow an explicit `out_of_support` outcome that receives an infinite or preregistered capped NLL and remains in all denominators.

The gate is 100% retention of actual outcomes under adversarial novel-result injection. No scorer may silently discard or invalidate an environment result because the predictor failed to enumerate it.

---

### B4 — Event replay, cross-turn mixing, and stale-session injection are all type-valid

**Reference:** The contract says event emission is turn-local and ongoing situations must be re-emitted, `APPRAISAL_MODULATORY_CONTROLLER_CONTRACT_2026-07-12.md:53–67`. But `validate_event_batch` only rejects duplicate IDs and duplicate `(turn_index, event_index)` positions within one call, `world_model_events.py:259–275`. `WorldEvent` has no session, run, or domain identity.

**Violated claim or invariant:** Current-turn evidence should be processed once, in the correct session and domain, with a distinction between a continuing condition and duplicate delivery.

**Concrete failure trace:**

* A batch containing a turn-0 threat and a turn-1 threat is accepted and summed as one appraisal.
* Two events with different IDs and positions but the same source ID/hash are accepted and double the contribution.
* The same event can be replayed in a later `appraise_events` call because uniqueness is only batch-local.
* A stale event from another session is accepted because the event has no session identifier.
* Re-emitting one continuing threat is observationally indistinguishable from receiving a duplicated threat record. Both repeatedly drive controller retention, reserve depletion, and load.

**Smallest decisive repair or test:** Introduce a `WorldEventBatch` envelope with session, domain, turn/tick, producer, batch hash, and an exactly-once source cursor. Require all events in a batch to share that identity. Add a derivation key based on parent source hash, derivation rule, target, and occurrence identity. Continuing conditions need an explicit `continuation` or state-snapshot semantic distinct from a new occurrence. Adversarial replay, cross-session, cross-turn, duplicate-source, and reordered-batch tests must produce zero unintended state change.

---

## HIGH

### H1 — The event-to-appraisal algebra aliases materially different situations

**Reference:** `modulatory_controller.py:306–376`, `appraise_events`; event persistence intent in the controller contract’s Semantic Event Boundary.

**Violated claim or invariant:** The same factual situation should have a stable appraisal regardless of arbitrary event decomposition, while materially different situations should not collapse without an explicit design decision.

**Concrete counterexamples:**

* `threat_cleared(magnitude=1)` alone produces exactly the same appraisal as no events: harm starts at zero, the event subtracts one, and clipping returns zero. Explicit relief is therefore indistinguishable from missing threat emission.
* `threat_observed(1)` followed by `threat_cleared(1)` produces the same appraisal as the reverse order. `event_index` is retained and sorted, but the appraiser is commutative and ignores recency.
* One certain threat of magnitude `0.5` aliases a catastrophic magnitude-1 threat at confidence `0.5`.
* Two correlated threat events from one underlying occurrence add as if independent.
* Scoped control for threat A globally offsets loss of control for threat B because `controllability` is one scalar balance.
* Saturation makes one unit event and one hundred unit events identical to the controller, while the audit does not record how much contribution was lost to clipping.

There is also segmentation sensitivity. Direct execution of the supplied controller from its default state gives:

* two `0.6` threat contributions aggregated into one turn: `vigilance=0.386`, `reserve=0.9715`;
* the same two contributions processed as two turns: `vigilance≈0.180792`, `reserve=1.0`.

The state depends on logging granularity, not just evidence.

**Smallest decisive repair or test:** Freeze event-kind-specific aggregation semantics. State predicates such as threat active/cleared need last-write or snapshot semantics; independent risks need a defined probabilistic or max aggregation; deltas need occurrence identity; control needs a target and horizon. Define a fixed tick or `dt`. Run metamorphic split/merge, reorder, duplicate-source, correlated-event, and scoped-control tests. Every non-invariance must either disappear or be documented as intentional with a quantitative bound.

---

### H2 — The controller has undeclared dead zones, including a dead maximum prediction-error input

**Reference:** `modulatory_controller.py:425–437`, vigilance dynamics; `modulatory_controller.py:413–416`, use of goal progress; the contract claims threat raises vigilance and defines prediction error as an appraisal control.

**Violated claim or invariant:** Retained controller inputs should have a declared, testable effect over their intended operating range.

**Concrete counterexample:** From the default state `vigilance=0`, `reserve=1`, `load=0`, let

```text
d = 0.7 * predicted_harm + 0.3 * prediction_error.
```

The first vigilance update reduces exactly to:

```text
vigilance_1 = clip(0.98*d - 0.30).
```

Therefore:

* maximum `prediction_error=1`, with no harm, gives `d=0.3` and `vigilance_1=0`;
* harm alone must exceed approximately `0.4373` before it changes vigilance at all;
* positive `goal_progress` is never read by `step_controller`; only its negative part is used;
* the advertised “prediction error” dimension cannot initiate any controller response from the neutral state.

This is not a stylistic coefficient concern. It is an exact dead input under the default initial condition.

**Smallest decisive repair or test:** Produce a one-factor sensitivity matrix for every appraisal input at neutral and at all state-space corners. Each retained field and sign must have a preregistered minimum response somewhere it is claimed to matter. Either redesign recovery as a multiplicative decay rather than a subtractive offset, explicitly specify and calibrate deadbands, or delete/rename dimensions that have no downstream role.

---

### H3 — The controller has strong, undocumented hysteresis and multiple fixed-point regimes

**Reference:** `modulatory_controller.py:176–201`, `ControllerConfig`; `modulatory_controller.py:387–467`, full transition. The contract describes bounded long-sequence behavior but does not specify multiple attractors or their basins.

**Violated claim or invariant:** Fixed points, hysteresis, saturation, and recovery behavior must be explicit before treating the state as a reliable modulator.

**Concrete counterexample:** Directly iterating the attached function for 5,000 turns under the identical stationary appraisal:

```text
predicted_harm = 0.46
prediction_error = 0
controllability = 0.5
```

produces two different stable regimes:

| Initial state                              | Approximate limiting state                       |
| ------------------------------------------ | ------------------------------------------------ |
| default fresh state                        | vigilance `0.0409`, reserve `1.0`, load `0.0`    |
| vigilance `0.8`, reserve `0.1`, load `0.9` | vigilance `0.5762`, reserve `0.0`, load `0.5762` |

Thus history remains permanently relevant under the same continuing input. At stronger inputs, clipping creates additional saturation: sustained harm `1` at controllability `0.5` tends toward maximum vigilance and near-zero reserve, while the same harm at controllability `1` tends toward maximum vigilance and agency with full reserve and zero load. Repeated self-attributed norm violation plus full control drives affiliation and agency to `1` even if no repair action or repaired outcome ever occurs.

Syntactic boundedness is implemented. Semantic stability is not established.

**Smallest decisive repair or test:** Exhaustively sweep constant and periodic appraisals from a grid of initial states. Enumerate fixed points, attraction basins, recovery times, saturation occupancy, and cycles. Pass only if each multiple-attractor region is explicitly intended and bounded, relief returns every state to a declared neutral neighborhood within a fixed number of ticks, and unresolved violations cannot indefinitely accumulate “repair” state without evidence of repair.

---

### H4 — “Content-poor” is a syntactic property, not an information-boundary result

**Reference:** The contract itself acknowledges that event kind, magnitude, confidence, and timing can encode identity and calls for rate/precision and leakage testing, `APPRAISAL_MODULATORY_CONTROLLER_CONTRACT_2026-07-12.md:147–164`. The code accepts unquantized floating-point values.

**Violated claim or invariant:** Semantic identifiers should not be recoverable from `q`, kappa, or `c/L` except through legitimate task-relevant correlations.

**Concrete counterexample:** An upstream producer can encode one person as threat magnitude `0.314159` and another as `0.271828`, or use event timing and re-emission frequency. The appraiser and controller preserve deterministic functions of those values. The reported semantic-reference substitution test holds the numeric attributes fixed, so it proves only that the appraiser does not directly read `semantic_refs`; it cannot detect leakage introduced by the producer.

Cross-session persistence of two unquantized regulatory floats would make this channel durable.

**Smallest decisive repair or test:** Before persistence or runtime use, freeze:

* quantization buckets and rounding;
* maximum event rate and fixed appraisal tick;
* producer-specific magnitude/confidence calibration;
* allowed event-pattern grammar.

Then train adversarial held-out classifiers to recover entity, topic, episode, or relationship from `q`, kappa, and `c/L`. The gate should be chance-level recovery within a preregistered confidence margin, including under a producer explicitly optimized to create a covert channel.

---

### H5 — Phase 2b validates repeatable tabular lookup signal, not action-conditioned world dynamics

**Reference:** `REPORT.md`, all sections; `world_model_baselines.py:36–83`, exact `(state_ref, action)` lookup and uniform fallback; `world_model_baselines.py:321–387`, deterministic action shuffle.

**Violated claim or invariant:** Experimental evidence must identify which architectural proposition it supports.

**What the result genuinely validates:** Taking the packet’s independence assertion as given, the exact v1 tabular estimator on the supplied LS20 state/action representation beats the train-only marginal and the named deterministic action-shuffle null in aggregate over 768 held-out transitions. The reported NLL improvement over the marginal is `0.109369` nats, and 13 of 16 runs meet the report’s fully positive criterion. That establishes repeatable predictive information in the lookup keys under this domain and protocol.

**Concrete counterexample to stronger interpretation:** Suppose each state appears in training with only one action, and the outcome is determined entirely by the state. The correct `(state, action)` table predicts well. The action-shuffle null queries an unseen `(state, shuffled_action)` pair, so `DirichletTabularEstimator.predict` falls back to its symmetric prior. The tabular model then strongly beats the shuffle even though action is causally irrelevant. The marginal is also weak because it ignores state. An arbitrary `state_ref` could itself contain an outcome-correlated label.

The report also shows material run heterogeneity: marginal NLL deltas range from `-0.259625` to `+0.359329`.

**Smallest decisive repair or test:** Run a new preregistered replication with:

* state-only `P(o|s)`;
* action-only `P(o|a)`;
* matched-support, within-state action permutations;
* state-feature and state-label ablations;
* explicit seen-state, unseen-state, seen-pair, and unseen-pair strata;
* multi-step rollout scoring.

The current result does **not** validate semantic events, appraisal, controller dynamics, belief updating, learned observation, unseen-state generalization, or any runtime connection.

---

### H6 — Dynamics, appraisal, constraints, and memory are separate by intent, but not by authority

**Reference:** `world_model_events.py:22–49` permits norm, goal, affiliation, memory, operator, synthetic, and world-model-trace events. `friction_world_model.py:55–69` stores speakers, topics, entities, memories, rules, and actions; `render_friction_context` directly renders memory and rule text. The old audit required dynamics, preferences, ethics, and disposition to remain distinct.

**Violated claim or invariant:** Factual prediction must not be rewritten by preferences, memory, norms, or disposition, and internally forecast events must not become experienced facts.

**Concrete failure trace:** A memory-derived `threat_observed` drives exactly the same appraisal as an environment-derived threat. A `norm_violation` requires a norm evaluator, yet the architecture says the World Model emits the event. A `goal_progress` event requires a selected goal and progress measure. Without producer authority rules, the predictive-dynamics component can silently absorb preference and ethical evaluation. Likewise, a `world_model_trace` source can denote either a forecast or an observation. Friction already has a path that renders retrieved memories and active rules directly into prompt content.

**Smallest decisive repair or test:** Define a producer authority matrix and separate event namespaces:

* dynamics producer: observations and action-conditioned forecasts only;
* observation comparator: scored mismatch derived from a bound commit/outcome pair;
* goal evaluator: progress against a versioned external goal specification;
* constraint evaluator: norm or policy assessment;
* memory adapter: explicitly recalled claims with age and epistemic status, never current observations by default.

Static validation must reject unauthorized event kinds by producer and runtime mode. Forecast-derived records must never satisfy an observed-fact interface. Any future bridge or action connection must remain a distinct adapter, checkpoint, loss, and ablation.

---

## MEDIUM

### M1 — `q`, kappa, and `c/L` are not sufficient statistics for any nontrivial downstream decision currently claimed

**Reference:** `AppraisalVector`, `KappaState`, and `RegulatoryState` definitions in `modulatory_controller.py:75–173`; the contract explicitly says the controller does not choose actions and does not establish a behavioral causal link, lines 92–145.

**Violated claim or invariant:** Before these variables control behavior, their claimed sufficiency must be defined relative to a specific prediction or decision problem.

**Concrete counterexample:** A severe uncontrollable safety threat and a blocked low-stakes goal can produce the same `control_need` because the controller takes a scalar maximum. Global controllability cannot represent “action A controls threat X but not threat Y.” A zero affiliation state cannot distinguish neutral affiliation from strongly negative evidence after clipping. Distinct histories can therefore produce the same state while requiring different actions.

This is not yet a contradiction because the contract disclaims action selection. It becomes one the moment these states are treated as sufficient inputs to dynamic alpha, candidate ranking, memory routing, or action choice.

**Smallest decisive repair or test:** Name the exact downstream variable these states are intended to predict or control. Construct paired traces that end in identical kappa/`c/L` but differ in the correct downstream action. If the pairs require different behavior, the state is not sufficient and must either be expanded or kept as a non-authoritative modulator alongside factual context.

---

### M2 — Uncertainty, horizon, scope, calibration, and time units are absent

**Reference:** `WorldEvent` has only generic magnitude and confidence fields, `world_model_events.py:154–208`; `appraise_events` multiplies them and discards the distinction, `modulatory_controller.py:329–375`.

**Violated claim or invariant:** Appraisal inputs from multiple producers must have commensurate meanings.

**Concrete counterexample:** A 10% probability of catastrophic harm, represented as magnitude `1` and confidence `0.1`, is identical to certain mild harm, magnitude `0.1` and confidence `1`. Immediate harm and harm expected in 100 turns are identical. A control event has no target, action, resource, or time horizon. `outcome_mismatch` is not bound to NLL, Brier, probability assigned to the observation, or any other calibrated error quantity.

**Smallest decisive repair or test:** Define event-kind-specific units, horizon, target/scope, and producer calibration. Keep probability or uncertainty separate where risk-sensitive interpretation is possible. Bind mismatch events to a specific committed distribution and observed outcome. Use paired calibration tests in which equal expected value but different risk or horizon must either remain distinct or be explicitly declared equivalent.

---

### M3 — Transition provenance, versioning, and missingness accounting remain incomplete

**Reference:** `ControllerStep.canonical_payload` contains only output states, `modulatory_controller.py:243–261`. Prediction and outcome statuses contain only `committed/not_collected` and `observed/not_collected`, `world_model_trace.py:18–20`. The old audit called for distinct `not_applicable`, `not_collected`, `collected`, and `estimator_failed` states.

**Violated claim or invariant:** Every transition must be reproducible, and every planned prediction must remain in denominator accounting.

**Concrete failure trace:** A disabled observer, an estimator crash, a domain where prediction is inapplicable, and an intentionally skipped collection can all be represented as `not_collected` plus arbitrary free text. A future report can exclude estimator failures without a machine-checkable distinction. Separately, changing the default controller rates can alter behavior without changing the state schema; an output record does not identify the configuration that produced it.

**Smallest decisive repair or test:** Add closed reason/status enums and a run-level completeness ledger. Add appraiser-rule and controller-config hashes, prior-state hash, input hash, session/step, and `dt` to a transition envelope. Golden replay must regenerate every output bit-for-bit, and reports must account for every preregistered step by status.

---

## LOW

### L1 — The packet does not independently bind the code, tests, and reported commits

**Reference:** The contract lists focused test files and coverage, but those test files are not attached. The old audit describes internal verification and explicitly distinguishes it from external attestation. The supplied code and Phase 2b report do not embed a manifest proving they are the artifacts from commits `4e8adbf` and `1d08f53`.

**Violated claim or invariant:** An external review should be able to bind reviewed bytes to the claimed lineage and test evidence.

**Concrete counterexample:** Files with the same names but different contents could be supplied while retaining the stated commit lineage. The review has no attached git blob hashes, artifact manifest, test sources, or raw Phase 2b traces with which to detect that.

**Smallest decisive repair or test:** Supply a signed or content-addressed packet manifest containing repository commit, git blob hash and SHA-256 for every source, test, report, raw trace, scorer, and configuration artifact. This is an evidence-custody issue; it does not by itself change the architecture verdict.

# Architecture verdict

**Coherent-but-incomplete.**

The proposed decomposition is technically coherent as a research direction:

```text
factual prediction
→ typed semantic evidence
→ deterministic appraisal
→ small recurrent modulation
```

with constraints, memory, preferences, and disposition intended to remain outside factual dynamics. The no-text controller boundary and current non-integration are sensible protections.

The implemented packet is not yet one minimal World Model. It is a trace schema, small tabular estimators, an unconnected event/appraisal/controller kernel, and a separate friction linter. Critical causal, lifecycle, open-set, authority, timebase, and transition-provenance contracts are missing. The current controller also contains exact dead-input and multiple-attractor behavior that must be either justified or corrected.

**No model, bridge, memory, Qdrant, dynamic-alpha, or action-selection integration is warranted.** Passing the reported tests or the Phase 2b gate does not clear the blockers above.

# Resolved since old audit

| Old audit item                                                                                 | Status                                   | Current basis                                                                                                           | Residual issue                                                                                                                             |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Fixture answer key copied into `predicted_observation`                                         | **Resolved**                             | The old audit’s implementation update reports removal, and the current typed trace has no such field.                   | Needs packet-level lineage proof, but the architectural defect is absent from the supplied trace.                                          |
| Typed pre-action/outcome trace, normalized probabilities, hash binding, explicit null observer | **Resolved**                             | Implemented in `world_model_trace.py`.                                                                                  | Hash binding is local; causal custody and artifact provenance remain incomplete.                                                           |
| Trace was only a nullable envelope                                                             | **Partial**                              | A real categorical commit/outcome schema now exists.                                                                    | Missing status taxonomy, state/action artifact binding, action receipt, journal-wide validation, posterior and candidate-action contracts. |
| Causal pre-action journal and source/action/outcome continuity                                 | **Partial**                              | The old audit reports an `fsync` journal and verifier for the earlier Phase 2 bundle.                                   | Not enforced by the schema; the current Phase 2b raw bundle and verifier are not attached.                                                 |
| Friction v0 incorrectly treated as a predictive World Model                                    | **Partial**                              | Current scope calls it a static friction/policy scaffold and keeps it disconnected.                                     | Filename, state contents, and prompt rendering still invite future conflation; it remains a linter, not dynamics.                          |
| Live activation-direction mismatch called prediction error / proposed dynamic-alpha feedback   | **Partial**                              | It is outside the current sidecar and no integration is authorized.                                                     | The measurement and feedback-loop objections are dormant, not resolved, for any future connection.                                         |
| Active-inference vocabulary equated surprisal, friction, and free energy                       | **Resolved in this packet**              | The current contract uses deterministic appraisal/controller language and makes no active-inference equivalence claim.  | Any older theory document retaining the equivalence remains stale.                                                                         |
| Dynamics, belief, preferences, ethics, and disposition must remain separate                    | **Partial**                              | Modules and losses are currently disconnected.                                                                          | Event kinds and source authorities still mix norm, goal, affiliation, memory, forecast, and observation roles.                             |
| No action-conditioned predictive evidence                                                      | **Partial**                              | Phase 2b provides repeatable LS20 tabular evidence against two nulls.                                                   | It does not identify action causality, learned dynamics, belief updating, unseen-state generalization, or multi-step prediction.           |
| LS20 run-consistency failure                                                                   | **Resolved only at the scoped gate**     | Phase 2b reports 13/16 fully positive runs and `GO_LS20_CONSISTENCY_REPLICATED`.                                        | Three runs remain non-positive, and the result authorizes no learned observer or runtime integration.                                      |
| No event/appraisal/controller kernel                                                           | **Resolved as implementation existence** | `WorldEvent`, deterministic `A_rules`, and deterministic `Phi` now exist.                                               | Composition, semantics, calibration, event lifecycle, timebase, and controller identification remain open.                                 |
| Content-poor modulation / semantic leakage                                                     | **Partial**                              | Text and identifiers are structurally excluded from serialized q/kappa/`c/L`.                                           | Numeric, categorical, timing, and persistence channels remain untested.                                                                    |
| Bridge dose, GQA, target-delta, loss scaling, and split issues M1–M6                           | **Still live**                           | No updated bridge implementation is in the current review scope.                                                        | Non-integration prevents immediate contamination; it does not resolve the old bridge findings.                                             |
| Identification overclaims M7                                                                   | **Still live**                           | Nothing in the current packet identifies vigilance, agency, or affiliation with specific Gemma directions or behaviors. | Any such interpretation still requires separate intervention and mediation evidence.                                                       |

The relevant before-state and issue inventory are in the older audit.

# Next three experiments

## 1. Causal-trace custody and open-set red team

**Hypothesis:** Every scored outcome is bound to a genuinely durable pre-action commit, and every environment outcome remains recorded even when the predictor did not enumerate it.

**Frozen inputs:** A revised trace/journal schema; canonical state, candidate-action, selected-action, estimator, and observation-ontology artifacts; journal writer and verifier; fixed fault-injection seeds; fixed set of retrospective-forgery, mutation, replay, crash, and novel-outcome cases.

**Metric and null:** Measure retrospective-forgery false acceptance, legitimate-record false rejection, outcome-retention rate, action-without-prior-commit rate, hash-chain failures, and crash-point ordering. The current timestamp/hash pair validator is the null implementation.

**Pass/fail gate:**

* zero forged post-outcome commits accepted;
* zero executed actions lacking a previously durable commit;
* 100% legitimate outcomes retained, including out-of-support outcomes;
* zero silent omissions from the preregistered step ledger;
* all state/action/estimator/source artifacts resolve to the committed hashes;
* every crash point either leaves a committed-not-executed record or a complete committed/executed/outcome chain.

**A pass would not authorize:** a learned observer, a WorldEvent adapter, appraisal, controller use, or any runtime integration.

---

## 2. New LS20 replication against matched, stronger nulls

**Hypothesis:** The Phase 2b advantage reflects action-conditioned transition information, rather than state lookup, outcome-correlated `state_ref` labels, or unseen-pair behavior in the action-shuffle null.

**Frozen inputs:** A new independent LS20 run set; canonical state encoder; action and observation ontology; train/evaluation split; smoothing; scorer; all null definitions; support policy; run-consistency threshold; no tuning on Phase 2b evaluation rows.

**Metric and null:** NLL, class-summed Brier, calibration, and structural state-delta error against:

* empirical marginal;
* state-only `P(o|s)`;
* action-only `P(o|a)`;
* matched-support within-state action permutation;
* state-label or feature ablation;
* previous-outcome and transition-frequency baselines.

Report seen-state, unseen-state, seen-pair, and unseen-pair strata separately.

**Pass/fail gate:**

* aggregate improvement over every primary null on NLL and Brier with a run-clustered lower confidence bound above zero;
* at least 13 of 16 independent runs fully positive against the strongest applicable nulls;
* positive performance in the unseen-state or unseen-pair stratum against its preregistered baseline;
* no advantage that disappears when outcome-correlated state features are removed;
* no support mismatch that makes the shuffle null default to uniform more often than the primary estimator.

**A pass would not authorize:** a learned observer, general-domain world dynamics, semantic-event generation, controller validity, or runtime connection. It would validate only the frozen tabular LS20 representation and estimator.

---

## 3. Event/appraisal/controller metamorphic and phase-portrait challenge

**Hypothesis:** Under frozen event semantics and timebase, the factorization is lifecycle-correct, resistant to replay and covert identity coding, and has only intended controller equilibria and deadbands.

**Frozen inputs:** Event derivation rules; producer authority matrix; event quantization/rate policy; fixed tick or `dt`; appraiser rules; controller configuration; initial-state grid; paired semantic traces covering replay, continuation, resolution, competing events, split/merge, scoped control, self/non-self attribution, and identity substitution.

**Metric and null:** Use the current kernel as the null. Measure:

* replay amplification;
* cross-turn and cross-session acceptance;
* split/merge and event-order divergence;
* per-input sensitivity and monotonicity;
* fixed-point count and attraction basins;
* neutral recovery time;
* saturation occupancy;
* unresolved-violation accumulation;
* identity/topic/episode classifier accuracy from q, kappa, and `c/L`.

**Pass/fail gate:**

* duplicate and stale records produce no second effect;
* continuing and new occurrences remain distinguishable;
* every retained appraisal dimension has its declared minimum effect, or the dimension is removed;
* all multiple-attractor regions are preregistered and satisfy explicit recovery constraints;
* relief returns every allowed initial state to the neutral neighborhood within a fixed bound;
* split/merge divergence is zero or below a preregistered semantic tolerance;
* adversarial identity recovery is no better than chance plus a narrow fixed margin;
* saturation occurs only in preregistered extreme regimes.

**A pass would not authorize:** treating kappa or `c/L` as sufficient statistics, persisting regulatory state, mapping state to Gemma directions, modifying alpha, routing memory, choosing actions, or sharing any training loss.

# Questions most likely to change the verdict

1. **What exactly is `state_ref` in Phase 2b?** Is it a canonical hash of a frozen pre-action state, a reusable state abstraction, a raw serialized state, or a human-assigned label—and can any part of it directly or indirectly encode the outcome?

2. **What authoritative adapter is intended to emit each event family?** In particular, who is permitted to emit `norm_violation`, `goal_progress`, `affiliation_*`, `threat_observed`, and `outcome_mismatch`, and can the predictive-dynamics component emit normative or preference-dependent events?

3. **Is the controller’s multiple-attractor behavior intentional?** Specifically, is permanent path dependence under a fixed moderate threat expected, and what fixed-point, recovery-time, and saturation constraints define acceptable behavior?

4. **For what exact downstream prediction or decision are kappa and `c/L` intended to be sufficient?** A precise target—rather than “modulation” generally—would determine whether the current state aliasing is acceptable or fatal.

5. **Can the packet be bound to commits `4e8adbf` and `1d08f53` with raw traces, scorer/verifier code, test sources, and a content-addressed manifest?** That would materially change the confidence assigned to the reported implementation and Phase 2b evidence.
