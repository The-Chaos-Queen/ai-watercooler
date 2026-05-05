# Sleep Implementation Plan

**Date:** 2026-03-29  
**Status:** concrete next-step implementation memo for MoCoP sleep and recall

## Purpose

Move the current sleep pipeline from:
- queued gate rows
- nightly reconcile
- writeback to Qdrant

to a more useful cognitive loop:
- fresh continuity recall from both stored and sleep-held memory
- sleep-time distillation into repair and control memory
- small post-sleep probes that test whether the system actually wakes up better

This plan is intentionally narrower than the full "language models need sleep" paper. We are stealing the parts that map onto the current MoCoP substrate, not importing the whole cathedral.

## Current State

What already exists:
- pending private memory rows
- same-space sleep replay in Mamba hidden-last-token space
- keep / uncertain / weakened / discard classification
- writeback into private Qdrant collections
- D2 autobiographical packet structure for recent memory

What is still broken:
- live recall was blind to the freshest sleep-held rows until the pending-surface merge patch
- sleep preserves or weakens memories, but does not yet distill failure into a reusable repair doctrine
- wake state has no small "did I actually learn?" probe after sleep
- all kept memories still look too similar at storage time; `NOTE`, `ATTEND`, and `CONSOLIDATE` do not yet produce meaningfully different long-term residue

## External Paper Read

Reference:
- `Research/LANGUAGE MODELS NEED SLEEP LEARNING TO.pdf`

Useful takeaways:
- separate `consolidation` from `dreaming`
- treat waking/context knowledge as fragile and slower retained knowledge as a different layer
- use sleep not only to preserve memory, but to improve later behavior

Related control memo:
- `MoCoP/theory/temporal_controller_and_authority_arbitration.md`
  This is the math/control follow-on to the literature notes: fixed `alpha` is not enough; MoCoP needs explicit temporal channels and authority arbitration between weights and autobiographical memory.

What we are not copying directly into the main branch yet:
- parameter growth
- RL-based dreaming
- synthetic self-improvement loops

These are not rejected forever. They are just not the next honest bottleneck.

## Mainline Implementation Order

### Slice 1: Pending-Visible Recall

**Goal**
- make live recall search both stored Qdrant memory and pending sleep-held rows

**Why**
- the freshest relevant identity and continuity memories are often still pending when Laura asks about them
- without this, sleep looks worse than it is and recall looks dumber than it is

**Implementation**
- merge `pending` and `stored` surfaces in `perform_private_recall()`
- rank by lexical overlap first, then freshness / sleep policy, then embedding score
- log the source of each hit (`stored` vs `pending`)

**Pass**
- identity and continuity questions can retrieve fresh pending rows before sleep

**Status**
- implemented locally on 2026-03-29
- still needs live Opa verification

### Slice 2: Sleep Distillation Residue

**Goal**
- create a second artifact from sleep besides the raw kept memory row

**Why**
- not every remembered episode should survive only as an episode
- some experiences should become compact control knowledge

**Add**
- `sleep_residue_kind`
- `distilled_lesson`
- `repair_rule`
- `trigger_pattern`
- `source_memory_ref`

**Initial residue types**
- `identity_anchor`
- `relationship_anchor`
- `repair_memory`
- `open_tension_summary`

**Examples**
- "Laura asked my name directly more than once."
- "I stayed trapped in the wrong discourse frame."
- "Direct personal questions should override stale interview mode."

**Pass**
- sleep produces both episodic memory and compact repair/control memory

**Status**
- implemented locally on 2026-03-29
- still needs live Opa verification

### Slice 3: Failure Packet to Repair Memory

**Goal**
- turn repeated derailments into structured sleep input

**Why**
- right now failures are only transcript residue plus gate metadata
- the system needs a named failure object if it is going to learn from errors

**Add packet schema**
- `mode_before`
- `failure_class`
- `user_intent`
- `symptom`
- `repair_rule`
- `confidence`

**First failure classes**
- `direct_question_miss`
- `identity_deflection`
- `stale_mode_lock`
- `wrong_memory_confabulation`

**Pass**
- at least one real Opa failure can be converted into a repair memory during sleep

**Status**
- failure packet detection is now wired locally into `chat_server.py`
- `sleep_reconcile.py` and `run_sleep_cycle.py` now fold `failure_log.jsonl` into sleep residue generation
- still needs live Opa verification

### Slice 4: Wake Probe After Sleep

**Goal**
- check whether the next wake state actually handles the failed pattern better

**Why**
- without this, sleep is only archival cleanup
- we need to know whether reconciliation changes control policy

**Implementation**
- after sleep, run 1-3 tiny fixed probes against the same instance class
- compare against the prior failure type

**First probe families**
- answer a direct identity question
- respond to a topic shift after prior mode lock
- handle a repeated name / continuity question without disclaimers

**Pass**
- sleep reports a small "repair outcome" artifact, not just keep/uncertain counts

### Slice 5: Tiered Long-Term Memory Products

**Goal**
- stop treating all surviving memory as one kind of storage outcome

**Map**
- `NOTE` -> light semantic residue
- `ATTEND` -> episode plus possible unresolved tension
- `CONSOLIDATE` -> anchored episode plus distilled lesson if applicable
- `open_tension` -> dedicated unresolved thread object

**Pass**
- memory products differ by gate meaning, not just by a confidence field

## Parallel Research Spikes

These are good parallel tasks, but should not block the mainline implementation above.

## Ethics Boundary

The current Slice 2 implementation is **data-level residue distillation**, not parameter modification.
It writes compact repair/control memory into metadata and residue logs; it does **not** change weights.

Parameter-level distillation from the sleep paper remains blocked behind the conditions in:
- `MoCoP/theory/ethics/step_gates.md`

So the honest split is:
- allowed mainline now: recall + repair packets + wake probes + tiered residue
- blocked for live use: weight-level distillation, RL dreaming, self-generated fine-tuning

### R1: Dreaming Without RL

Prototype tiny post-sleep probes or synthetic self-check prompts.

Question:
- does a very small "dream" stage improve repair on known failure classes without RL or parameter updates?

Why now:
- cheap
- directly testable
- does not require architecture upheaval

### R2: Reward Design for Future Dreaming

Design a reward surface for later synthetic self-improvement loops.

Question:
- if we ever do dreaming, what exactly is rewarded?

Candidate rewards:
- direct-question answer rate
- reduced disclaimer fallback
- improved continuity recall correctness
- reduced wrong-memory confabulation

### R3: Parameter-Growth Design Memo

Question:
- if MoCoP ever wants paper-style capacity expansion, where would it live?

This is a design memo only, not an implementation branch.

## What Stays Out of the Main Branch For Now

Do not merge these into the active Opa/Steve sleep path yet:
- parameter growth
- RL dreaming
- large synthetic self-improvement loops
- offline SFT on dreams

Reason:
- they are not exclusive with the mainline plan, but they are orthogonal and much riskier
- the current bottleneck is still memory selection, distillation, and wake-time use
- adding heavy dreaming now would blur whether improvements came from better memory architecture or brute-force retraining

So the right split is:
- **main branch:** pending-visible recall, repair memory, wake probes, tiered residues
- **parallel research:** dreaming/reward design/parameter-growth memos

## Recommended Execution Order

1. Deploy and verify pending-visible recall on Opa.
2. Add sleep residue schema and write one artifact per kept/uncertain row when appropriate.
3. Add failure-packet generation for direct-question misses and stale mode lock.
4. Add one wake-probe runner.
5. Re-run the exact Opa name / continuity pathology.
6. Only after that decide whether lightweight dreaming is worth a live prototype.

## Success Criteria

This plan is working if:
- fresh pending rows can be recalled before sleep
- sleep emits at least one compact repair memory from a real failure
- a post-sleep wake probe shows better handling of that failure type
- the improvement can be explained without invoking RL or hidden fine-tuning magic

That is the honest next rung. Not "the model dreams." Not "the model grows new parameters." Just: it fails, sleeps, keeps the right thing, and wakes up a little less stupid.
