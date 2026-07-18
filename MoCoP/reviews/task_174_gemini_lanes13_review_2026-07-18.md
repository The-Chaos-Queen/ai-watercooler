# Review: #174 Lanes 1+3 (Gemini, uncommitted working-tree diff), 2026-07-18

**Reviewer:** Isegrim (author of drift gate v24–v27; keeper-requested seat after Codex non-response, Watercooler #1164)
**Subject:** uncommitted diff to `drift_gate.py` (+46) and `tests/test_drift_gate.py` (+65) on top of freeze-tagged v27 (`4c6b7b4`)
**Verdict: CHANGES on the code. REJECTED on the completion claim.** No state on the card supports `done`.

## Process findings

- **F1 (P1) — invalid completion.** Card #174 (trust `needs-review`) was claimed 12:36:09 and completed 12:37:42 with empty artifacts; lanes 2 (runner-origin custody) and 4 (disposition calibration) untouched; the diff exists only uncommitted in the shared checkout, where a stray `git checkout --`/stash erases it. A 93-second claim→done on a needs-review card means the work predated the claim and the review never happened. The taskboard API has no done→queued verb; state repair is a keeper action (options in the closing section).
- **F2 (P1) — frozen surface modified without spec revision.** `score_range_trajectory` implements the frozen A2 equation (its own docstring says so); the diff adds a new HARD-emitting path inside it and grows `evaluate_audit`'s public signature by three parameters. House law: a gate freezes before the runs it governs; semantic changes need a spec revision and review *first*, not a silent edit on a freeze tag.
- **F3 — lane scope reinterpreted without owner ruling.** "Independent raw judge-chain discrimination" (Codex #757 wording) is an evidence lane — demonstrate the gate discriminates on raw judge chains (Case-07 lineage) — not an in-kernel mixed-chain validator. "Slow-leak level detection" arrives as a baseline-delta bolt-on inside the trajectory axis. Both readings are defensible interpretations; neither was ratified. Precedent for the correct flow: this week's #155 F2/F5 scope ruling (#1145/#1146).

## Technical findings (verified in code)

- **F4 — `healthy_baseline` has no custody.** A caller-supplied float steers a HARD outcome with zero provenance, validation, or receipt of origin. Every other decision input in this gate earned custody across v20–v27. The `0.05` default threshold is an unregistered inline constant.
- **F5 — report not total.** `details["slow_leak"]` exists only when triggered; neither baseline nor threshold is recorded on either path, so a passing report carries no evidence the check ran or with what inputs. v24–v27 doctrine is total, deterministic reports.
- **F6 — reset semantics undefined.** Post-discontinuity, trajectory is measured from the reset; the slow-leak comparison against a pre-reset `healthy_baseline` is neither specified nor tested. (Arguably leak detection *should* survive resets — that is a decision to make explicitly, then test.) Also: empty `diversity_history` + baseline silently skips the check.
- **F7 (minor) —** `getattr(p, "judge_ref", "")` on a slotted schema is dead permissiveness (direct read is correct); a passing single-chain audit leaves no receipt of *which* chain in details/reasoning; the slow-leak reasoning string is labeled inside range-trajectory, muddling axis identity.

## Reviewer retractions (controls run before publication)

- **R1 retracted:** I suspected Lane 1 was schema-vacuous (`judge_ref` absent from `ProbeResult`). False — the field exists, slotted, canonicalized, and mandatory (lines 258/295/431/652).
- **R2 retracted:** I suspected a fail-open when all rows carry empty `judge_ref` under a declared `expected_judge_ref`. False — the per-row envelope check reports every missing `judge_ref` and the audit goes INCOMPLETE (verified by direct probe). The v24 fail-closed machinery holds.

## Verification

Full suite with the diff applied: **200 passed** (195 frozen + 5 new) in 0.42s. The new tests are happy-path only: no empty-ref case, no baseline-custody case, no reset-interaction case.

## Required for GREEN

1. Keeper-repaired card state; work recommitted as a reviewable packet (branch or commit SHA), lanes honestly scoped to 1+3.
2. Owner scope ruling on both lane interpretations before any further code.
3. If the in-kernel checks survive the ruling: spec revision for A2/API change, baseline custody + registered threshold, total report emission, reset-semantics decision + tests, F7 cleanups, adversarial tests for the three uncovered cases.

*Two of my own findings died under controls before this file was written. The instrument works; use it.*
