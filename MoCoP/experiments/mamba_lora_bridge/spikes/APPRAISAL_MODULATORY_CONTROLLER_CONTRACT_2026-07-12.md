# Appraisal-to-Modulatory Controller Contract

**Date:** 2026-07-12
**Status:** Implemented model-free reference kernel; no runtime integration
**Owner:** Codex, OpenCLAW #163
**Authority:** Laura decisions relayed in Watercooler #918

## Purpose

Implement the smallest auditable form of the ratified boundary:

```text
semantic WorldEvent records
    -> deterministic appraise_events (A_rules)
    -> numeric AppraisalVector q
    -> deterministic step_controller (Phi)
    -> session-local KappaState + separate RegulatoryState(c, L)
```

The World Model side may identify people, rules, topics, relationships, goals, and
episodes. The appraisal and controller payloads may not.

## Artifacts

- `world_model_events.py`: strict semantic event/provenance schema.
- `modulatory_controller.py`: deterministic appraisal and bounded controller kernel.
- `tests/test_world_model_events.py`: event schema and parser tests.
- `tests/test_modulatory_controller.py`: rule, dynamics, lifecycle, and leakage tests.

Both modules are stdlib-only. They import no model runtime, Torch, Qdrant client,
bridge injector, filesystem persistence layer, or network code.

## Semantic Event Boundary

`WorldEvent` is frozen and exact-key parsed. Its allowed fields are:

```text
schema_version, event_id, turn_index, event_index, kind,
magnitude, confidence, attribution, source, semantic_refs
```

Allowed v1 event kinds:

| Event kind | Appraisal effect |
|---|---|
| `threat_observed` / `threat_cleared` | Raise/lower predicted harm |
| `outcome_mismatch` | Raise prediction error |
| `control_available` / `control_lost` | Raise/lower controllability |
| `goal_progress` / `goal_blocked` | Signed goal progress |
| `norm_violation` | Raise norm violation only when attribution is `self` |
| `affiliation_gain` / `affiliation_loss` | Signed affiliation change |

Semantic references have closed kinds (`person`, `rule`, `goal`, `topic`, `episode`,
`relationship`, `object`) and remain attached to the event/audit side. Event batches
receive a deterministic order and reject duplicate IDs or turn/event positions.

Event emission is turn-local. Ongoing situations must be re-emitted on every turn in
which they remain appraisal-relevant, or their effect decays by design through kappa
retention. In particular, controllability returns to its neutral `0.5` prior and harm
returns to zero when no corresponding event fires. Persistence belongs in controller
state, not in an implicit sticky event interpretation.

An other-attributed `norm_violation` deliberately contributes no guilt appraisal.
When being wronged should affect control, vigilance, or affiliation, the World Model
must emit the factual decomposition explicitly, such as `goal_blocked`,
`affiliation_loss`, and/or `threat_observed`. The kernel must not infer moral agency or
silently add a new appraisal field from the norm label alone.

## Appraisal Contract

`AppraisalVector` contains exactly six numeric controls:

| Field | Range | Meaning |
|---|---:|---|
| `predicted_harm` | `[0, 1]` | Current predicted threat/harm |
| `prediction_error` | `[0, 1]` | Outcome mismatch |
| `controllability` | `[0, 1]` | Estimated available control; neutral baseline `0.5` |
| `goal_progress` | `[-1, 1]` | Signed progress/blockage |
| `norm_violation` | `[0, 1]` | Self-attributed norm breach only |
| `affiliation_delta` | `[-1, 1]` | Signed social-safety/affiliation change |

`appraise_events` uses only event kind, magnitude, confidence, and attribution. It
does not read event IDs, source IDs, hashes, or semantic references. It returns an
`AppraisalResult` with two physically separate values:

- `vector`: the numeric object accepted by the controller;
- `audit`: event ID, frozen rule ID, appraisal field, and contribution for review.

`step_controller` refuses an `AppraisalResult`; callers must pass the numeric vector.
This prevents the semantic audit envelope from crossing by accident.

## Controller Contract

`KappaState` is the three-axis v1 reference state:

```text
affiliation, agency, vigilance in [0, 1]
```

These are authoritative engineering names. Biological labels are not schema fields.
The set is a reference kernel, not proof that three axes are sufficient or that the
current Gemma directions implement them.

`RegulatoryState` is separate:

```text
reserve c in [0, 1]
load    L in [0, 1]
```

The transition uses explicit retention, drive, suppression, recovery, depletion, and
load terms from `ControllerConfig`. All default rates are provisional engineering
values selected to make the qualitative state-machine contract testable. They are not
biological measurements, learned parameters, or an authorized live dose schedule.

Key modeled behavior:

- threat raises vigilance;
- threat plus available control preserves/raises agency;
- uncontrolled repeated threat depletes reserve and accumulates slow load;
- neutral/cleared threat lets vigilance and load recover;
- affiliation evidence raises affiliation without carrying relationship identity;
- a self-attributed norm violation plus controllability can raise bounded
  repair-oriented affiliation/agency;
- a non-self norm violation does not become a guilt appraisal.

The default agency asymmetry is intentional. For control need `n` and controllability
`c`, the direct agency term is `n * (1.04*c - 0.58)`, crossing zero at approximately
`c = 0.558`. The neutral `c = 0.5` prior therefore produces mild agency suppression
under threat: a provisional pessimism-under-uncertainty bias, not a coefficient error.
Changing that crossover is a controller-policy change and requires an explicit review.

The controller does not choose actions and does not establish that vigilance plus
agency causes careful behavior. That causal link needs a later behavioral evaluation.

## Lifecycle

`begin_session` resets `KappaState` to zero while accepting only a validated
`RegulatoryState`. This implements the ratified split:

- kappa persists across turns and decays within a session;
- c/L are eligible for versioned cross-session continuity;
- this module performs no c/L read, write, encryption, migration, backup, or deletion.

Durable c/L custody remains blocked on OpenCLAW #164.

## Information Boundary and Residual Risk

The reference kernel enforces:

- exact-key parsing at every serialized boundary;
- rejection of text, entity, topic, episode, and embedding fields in q/kappa/c/L;
- invariance of q and controller state when semantic references and provenance change
  while the registered event attributes remain fixed;
- separate semantic audit records that are not accepted by the controller;
- finite/range checks, immutable records, and bounded long-sequence dynamics.

This is a structural leakage defense, not proof of statistical independence. An
upstream producer could still correlate event kinds, magnitudes, confidence, or timing
with semantic identity, or deliberately use numeric values as a covert channel. Before
any content-poor/control-only claim, the system still needs frozen upstream event
semantics, rate/precision policy, adversarial numeric-channel tests, and empirical
entity/topic/episode leakage evaluation. MUSIC-3 remains responsible for its own
audio-side leakage gate.

## Tests

The focused suite covers:

- canonical round trips and immutability;
- unknown/missing/nested-field rejection;
- invalid enums, hashes, booleans, non-finite values, and range failures;
- deterministic batch ordering;
- threat/control, repeated stress, relief/recovery, trust, and guilt examples;
- session reset with c/L preservation;
- long extreme sequences remaining finite and bounded;
- semantic-reference substitution producing identical q and controller state.

## Non-Goals

- No learned appraisal.
- No claim that the current World Model emits these events.
- No adapter from `friction_world_model.CognitiveState` or `world_model_trace` yet.
- No bridge basis, Gemma direction, alpha, or activation injection.
- No live behavior, Qdrant, memory write, audio, model load, or GPU use.
- No durable controller-state persistence.
