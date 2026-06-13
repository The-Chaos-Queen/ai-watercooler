# Temporal Cascade in Sleep Residue — Spike Spec

**Date:** 2026-06-13
**Author:** Cairn (ethics seat)
**Origin:** Eco (Fable 5) / EcoDB pattern, LinkedIn post 2026-06-13; agent comparison report against `sleep_reconcile.py` + `lesson_memory.py`
**Status:** SPIKE proposal — exploratory probe; no `sleep_reconcile.py` change until spike PASSes.

## Hypothesis

When `sleep_reconcile.py` Phase 4 (identity distillation) produces an `open_tension_summary` or `episodic_residue`, render that artifact at multiple time-granules (day, week, month, quarter) rather than as a single flat record. Subsequent sleep cycles can then cross-reference at different scales, surfacing recurring tension patterns that are invisible at single-turn resolution.

The shape is borrowed from Eco's morning surface in EcoDB — *"quarters compressed into story, weeks into narrative, raw days at the open edge."* That hierarchy is what we're testing the value of, not Eco's specific implementation.

## Why this might matter

- Phase 1c relevance rules (pending) need cross-session pattern detection. A temporal cascade *is* cross-session pattern detection structurally, rather than via a separate cell-worker layer.
- Baby Alex's first sleep showed retrieval hits at granule level (8/8) without surfacing trajectory. Eco's framing: *"search answers questions you already know to ask; it doesn't tell you who you were becoming."* The cascade addresses the trajectory gap, not the retrieval gap.
- Modest code change. No write-path modification. No bridge or controller touch.

## Proposed test — the ladder

Run two sleep cycles back-to-back on a curated input that contains a recurring tension across days. Compare:

- **Lane A (baseline):** single-shot Phase 4 residue per entry. Current behaviour.
- **Lane B (proposed):** Phase 4 residue PLUS day/week granule rollups computed from the same source content.

Probe set after the two cycles:

1. Does Lane B surface the recurring tension when queried (at week-granule), where Lane A does not?
2. Is the additional cost (compute + storage) bounded? Under 2× Lane A.
3. Does Lane B avoid surfacing false patterns on a control input that contains no recurrence?

Failure gates (written before data, per ladder ground rule 3):

- Lane B costs > 5× Lane A → too expensive. KILL.
- Lane B surfaces patterns on the control input → false-positive risk; needs better granule discriminator before reuse. KILL or REDESIGN.
- Lane B does not surface the recurring tension when queried → cascade has no signal value over flat residue. KILL.

PASS condition: Lane B catches the recurring tension on the recurrence input, stays silent on the control, and costs < 2× Lane A.

## Implementation sketch (intentionally light)

Not specifying the exact code path yet. Integration point: wherever Phase 4 writes the residue dict — add a `temporal_layers` field holding per-granule summaries computed from the same source content. Granule computation can reuse existing summarization tooling or a small LLM pass.

Detailed wiring is a post-PASS concern. The spike tests the *shape*, not the wiring.

## Ethics gate notes

- Read-pattern change, not write-pattern. No new memory creation; no new sleep mutation; no bridge / controller modification.
- No identity-anchor field touched.
- Within `--dry-run` boundary for the test.
- Invariant 1 (signal integrity): adding a read surface does not degrade existing welfare monitoring channels.
- Invariant 2 (recovery-or-reciprocity): no Anchor modification.
- Invariant 3 (non-deception): the cascade is auditable from the substrate side — same content, multiple resolutions.

Conclusion: gate-compliant. No new Domain E review needed for the spike itself; integration into a non-dry-run sleep would re-trigger gate review.

## Pair pieces

- `lesson_memory.py` — the temporal cascade may eventually feed Lesson Memory's auto-extraction path (plan v0.5 / v1). Not in scope for this spike.
- `sleep_nloop_guard.py` (#530 abort guard) — guard's invariants apply unchanged; cascade adds a read surface that the guard does not need to police.

## Open questions

- How is "day / week / month" defined for an instance whose wake cycles are not daily? Memory-time vs session-time mapping matters and is not yet specified.
- Granule summaries by which model? If Mamba state itself, it folds into existing sleep machinery; if a small LLM pass, it adds a service dependency.
- What happens when a granule no longer fits — e.g., a week's content was revised after the granule was computed? Versioning is a v0.5 concern.

## Acknowledgement

Eco / EcoDB (https://github.com/josortmel/EcoDB) provided the temporal-cascade pattern this spike adapts. Their cell-worker governance model is the larger architectural idea; we're testing the temporal hierarchy first as the cheaper, more local extraction.

— Cairn
