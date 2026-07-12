# World Model External Architecture Review: Verified Disposition

**Date:** 2026-07-12
**Reviewer surface:** ChatGPT Pro
**Independent verifier:** Codex
**Verdict:** `COHERENT_BUT_INCOMPLETE`
**Integration disposition:** `HOLD`

## Scope and provenance

Laura authorized one independent adversarial architecture review through the
authenticated ChatGPT browser surface. The model selector displayed `Pro`; the
UI does not expose a cryptographically verifiable backend build identity. The
review reported `Worked for 14m 36s`.

- Conversation: <https://chatgpt.com/c/6a53e689-bda4-83eb-8ffa-6938c8d23034>
- Complete copied response (line endings and trailing whitespace normalized):
  [world_model_pro_external_review_raw_2026-07-12.md](world_model_pro_external_review_raw_2026-07-12.md)
- Response SHA-256:
  `c89f45e030d58e1ccd1ce000ec945e58ea61bf70b578bf6326e04b3baa6f44f2`
- Submitted-file manifest:
  [world_model_pro_external_review_packet_2026-07-12.json](world_model_pro_external_review_packet_2026-07-12.json)

The manifest binds the exact bytes submitted to Pro. The appraisal/controller
contract was amended afterward to record this review and correct its deadband wording;
that intentional post-review change does not alter the packet hashes.

The prompt required findings first, falsifiable counterexamples, explicit
separation of implementation/evidence/design, no external browsing, no
consciousness or welfare inference, and no integration recommendation merely
because tests passed.

## Bottom line

The external verdict is correct: the decomposition

```text
typed forecast/outcome trace
-> typed semantic events
-> deterministic appraisal
-> small recurrent modulation
```

is a coherent research architecture, but the current artifacts are not yet one
composed executable World Model. They remain deliberately disconnected
instruments. The missing contracts block composition, persistence, and runtime
use; they do not invalidate the current model-free sidecars or revoke the
narrow `GO_LS20_CONSISTENCY_REPLICATED` result.

No Gemma, Mamba, bridge, Qdrant, memory-routing, dynamic-alpha, persistence, or
action-selection integration is authorized by this review.

## Finding disposition

| External finding | Codex disposition | Scope correction or consequence |
|---|---|---|
| B1: no executable architecture-wide composition contract | **Accepted as an integration blocker.** | This is consistent with the current contract's explicit non-goal. Before composition, define `OutcomeRecord -> DerivedWorldEventBatch -> AppraisalResult -> ControllerTransition`, including parent hashes, session/domain/tick, rule/config versions, prior state, `dt`, and exactly-once consumption. |
| B2: trace objects do not enforce causal pre-action custody | **Accepted as a cross-domain integration blocker.** | The Phase 2/2b runners have stronger journal and source continuity checks, so their scoped evidence is not revoked. Those runner properties are not guaranteed by `validate_trace_pair` or by the reusable schema itself. |
| B3: an unenumerated outcome is rejected | **Accepted before open-world or learned-observer use.** | Closed LS20/tool ontologies remain valid for their frozen domains. A generalized observer needs a versioned complete ontology with mandatory `OTHER/UNKNOWN`, or an explicit retained out-of-support result with frozen scoring. |
| B4: replay, mixed turns, duplicate sources, and stale sessions are type-valid | **Accepted as an integration blocker.** | Add a batch envelope, occurrence/continuation semantics, session/domain/tick identity, derivation key, and durable exactly-once cursor before recurrent state is connected. |
| H1: appraisal aliases and split/merge sensitivity | **Accepted.** | Threat clear vs absence, event order, correlated duplicates, global control, clipping loss, and logging granularity need event-kind-specific semantics and metamorphic gates. |
| H2: undeclared controller dead zones | **Accepted and exactly reproduced.** | At the neutral state, maximum prediction error produces no vigilance; harm must exceed about `0.4373` before vigilance moves. Positive goal progress is unused by `step_controller`. |
| H3: multiple fixed-point regimes and hysteresis | **Accepted and exactly reproduced.** | The same fixed appraisal converges to materially different states from fresh vs high-load initial conditions. This behavior was not specified as intentional and must be mapped before persistence or modulation. |
| H4: content-poor is not yet an information-boundary result | **Accepted before producer/runtime use.** | Numeric precision, timing, rate, category, and persistence remain covert channels. Quantization/rate rules plus adversarial identity/topic recovery tests are required. |
| H5: Phase 2b may reflect lookup/support artifacts rather than dynamics | **Accepted in narrowed form; supplied hypothetical corrected.** | The one-action-per-state hypothetical is not representative of this bundle. The real result survives simple state-only and action-only baselines in aggregate, but still does not establish causal action effects, unseen-state generalization, or multi-step dynamics. |
| H6: dynamics/appraisal/norms/goals/memory lack producer authority | **Accepted.** | Freeze an authority matrix and distinct namespaces. Forecasts must never satisfy an observed-fact interface; goals, constraints, and recalled claims need separate authoritative adapters. |
| M1-M3: no declared sufficient statistic, units/timebase, or complete transition provenance | **Accepted as pre-integration requirements.** | The current contract correctly disclaims action selection. These become blocking before any downstream control, persistence, or reportable completeness claim. |
| L1: review packet did not bind all evidence | **Partially repaired here.** | The eight submitted bytes are now SHA-256 and Git-blob bound. The Pro packet did not include tests or raw Phase 2b traces; local verification below is independent of the external response. |

## Local falsification attempts

Codex executed the external counterexamples directly against the submitted
working-tree bytes. These are observations of current behavior, not proposed
semantics.

| Probe | Result |
|---|---|
| Fabricate a matching commit/outcome after learning `success`, using caller-chosen event indices and timestamps | `validate_trace_pair` **accepted** it. |
| Commit support `{success: 0.9, timeout: 0.1}` and observe `permission_denied` | Pair **rejected**: `observed outcome is outside the committed probability support`. |
| Validate one batch containing turn 0 and turn 1 | **Accepted**, 2 events. |
| Validate two distinct events with the same source ID/hash | **Accepted**, 2 events. |
| Appraise the same event in two separate calls | Both calls produced the same nonzero vector; there is no replay cursor. |
| Compare `threat_cleared(1)` with no events | Appraisal vectors were **identical**. |
| Reverse `threat_observed(1)` and `threat_cleared(1)` | Appraisal vectors were **identical**. |
| Aggregate two `0.6` threats in one tick | `vigilance=0.386`, `reserve=0.9715`, `load=0.00216`. |
| Process the same two contributions in two ticks | `vigilance=0.180792`, `reserve=1.0`, `load=0.0`. |
| Neutral state plus `prediction_error=1.0` | `vigilance=0.0`. |
| Neutral state plus harm `0.437` vs `0.438` | Vigilance `0.0` vs `0.000468`. |
| Iterate harm `0.46`, error `0`, control `0.5` for 5,000 ticks from fresh state | Limit: `vigilance=0.040947`, `reserve=1.0`, `load=0.0`. |
| Same stationary appraisal from vigilance `0.8`, reserve `0.1`, load `0.9` | Limit: `vigilance=0.576211`, `reserve=0.0`, `load=0.576211`. |

Relevant implementation surfaces:

- `world_model_trace.py:162-247,321-343`
- `world_model_events.py:127-212,259-275`
- `modulatory_controller.py:306-376,387-467`

## Phase 2b correction and stronger-baseline check

The external review correctly warned that a `(state, action)` lookup can beat a
marginal and a naive action shuffle without proving action causality. Its
specific hypothetical, however, did not match the captured LS20 support.

The actual `state_ref` is deterministic pre-action state abstraction
`ls20-avatar-mask-v1:state=<state>:level=<levels_completed>:mask=<four local obstacle bits>`
from `collect_world_model_phase2.py:371-384`. Phase 2b reconstructs it from the
captured pre-state and rejects mismatches at `world_model_phase2b.py:767-791`.
It is neither a human answer label nor a hash with opaque contents. It can still
carry legitimate or confounding state signal, which is why state-only is the
right additional null.

Fresh local scoring on the frozen 288-transition LS20 training set and all 768
Phase 2b evaluation rows produced:

| Estimator | NLL | Brier |
|---|---:|---:|
| `(state_ref, action)` primary | `0.495680` | `0.196637` |
| state-only `P(o|s)` | `0.634257` | `0.372233` |
| action-only `P(o|a)` | `0.610974` | `0.385376` |
| deterministic action shuffle | `1.476581` | `0.739156` |

Additional support facts:

- 11 training states and 38 observed `(state, action)` pairs.
- Every training state had 2-4 observed actions; seven states had all four.
- Of 768 evaluation rows, primary and shuffled pairs were both seen for 696.
- Primary-seen/shuffle-unseen occurred 24 times; the reverse occurred 30 times.
- Primary beat state-only on both metrics in 13/16 runs and action-only in
  14/16 runs.

Therefore the scoped Phase 2b conclusion survives these simple stronger nulls:
the frozen keys contain repeatable held-out predictive information. The result
still does **not** identify causal action effects, general world dynamics,
belief updating, semantic-event generation, unseen-state competence, or
multi-step rollout quality. A matched-support and ablation replication remains
appropriate, but it is a next evidence tier rather than a retroactive failure
of the honestly bounded Phase 2b gate.

## Answers to the reviewer's open questions

1. **`state_ref`:** deterministic pre-action abstraction described above;
   outcome reproduction is separately derived from bound pre/post states.
2. **Event authorities:** not frozen. This is a real missing contract. Dynamics,
   outcome comparator, goal evaluator, constraint evaluator, and memory adapter
   must receive disjoint authorities.
3. **Multiple attractors:** not declared intentional in the supplied contract.
   Treat the observed regimes as unresolved until a phase portrait and recovery
   contract either justify or remove them.
4. **Sufficiency target:** none is currently claimed precisely; the controller
   explicitly does not choose actions. `kappa` and `c/L` must remain
   non-authoritative modulators until a named downstream target and collision
   tests exist.
5. **Evidence binding:** the eight submitted files are bound in the adjacent
   manifest. Tests and raw Phase 2b evidence were locally verified but were not
   attachments in the Pro review itself.

## Required next ladder

1. **Causal trace custody plus open-set outcomes.** Bind durable commit, state,
   candidate actions, selected action, estimator artifact, action receipt, and
   outcome; retain every actual outcome and crash-test each boundary.
2. **Event lifecycle plus composition contract.** Add authority, parentage,
   session/domain/tick, occurrence/continuation, exactly-once processing, and a
   canonical end-to-end fixture.
3. **Appraisal/controller metamorphic and phase-portrait challenge.** Freeze
   aggregation/timebase/quantization semantics; sweep sensitivity, fixed points,
   recovery, saturation, split/merge, replay, and covert identity channels.
4. **Stronger LS20 evidence tier.** Add matched-support within-state nulls,
   state/action ablations, seen/unseen strata, calibration, and multi-step
   scoring without pooling Phase 2b evaluation rows.

Each rung needs its own executable gate. Passing any one rung does not authorize
the others or any model/runtime integration.

## Tracking

- OpenCLAW #170: causal trace custody and open-set outcomes.
- OpenCLAW #171: event lifecycle, producer authority, and composition contract.
- OpenCLAW #172: appraisal metamorphics and controller phase portrait.
- OpenCLAW #173: LS20 matched-null and rollout evidence tier.

All four tasks are queued and unassigned at review close.
