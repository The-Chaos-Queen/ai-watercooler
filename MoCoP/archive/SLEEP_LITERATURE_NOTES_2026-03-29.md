# Sleep Literature Notes

**Date:** 2026-03-29  
**Status:** focused research note for MoCoP sleep design

## Paper: Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories

**Source**
- `Research/LANGUAGE MODELS NEED SLEEP LEARNING TO.pdf`

**Type**
- anonymous ICLR 2026 submission

## Why It Matters

This is one of the more relevant "sleep for language models" papers because it does not stop at vague replay analogies. It explicitly separates:
- `memory consolidation`
- `dreaming / self-improvement`

That is directly useful for MoCoP, where the current sleep path is already real but still too monolithic.

## What The Paper Claims

The paper proposes alternating:
1. `waking`
   normal in-context or task learning
2. `sleep: consolidation`
   upward distillation from fragile short-term/context knowledge into slower retained parameters
3. `sleep: dreaming`
   synthetic self-generated data plus RL/SFT-style self-improvement

## What MoCoP Should Steal

### 1. Split Consolidation From Dreaming

MoCoP already has a real consolidation path:
- pending gate rows
- same-space replay
- keep / uncertain / weakened / discard
- writeback to Qdrant

But it does not yet cleanly distinguish:
- "what survives"
- from "what is learned for later behavior"

That distinction should become explicit.

### 2. Distilled Residue Should Be A First-Class Sleep Product

Current MoCoP sleep mainly preserves or weakens memory rows.

The stronger design is:
- some rows remain episodic memory
- some rows become slower control or semantic residue

Examples:
- identity anchor
- relationship anchor
- repair memory
- open-tension summary

### 3. Sleep Should Change The Next Wake State

Right now sleep proves handoff integrity and partial memory preservation.

The next rung is stronger:
- after sleep, run a tiny wake probe
- ask whether the prior failure is handled better

Without that, sleep is mostly archival cleanup.

## What MoCoP Should Not Copy Yet

### 1. Parameter Growth

Interesting, but not the current bottleneck.

It would make it harder to tell whether gains came from:
- better sleep/memory doctrine
- or simply more capacity

### 2. RL Dreaming

Also interesting, but too early for the live branch.

Current bottlenecks are still:
- pending vs stored recall
- repair-memory creation
- wake-time use of sleep outputs

### 3. Large Synthetic Self-Improvement Loops

Same reason.

They are not excluded forever, but they should remain a parallel research branch until the basic memory/control pipeline is honest.

## Recommended MoCoP Read

The paper is not a D3/D4 autobiographical-memory blueprint.

It does **not** solve:
- self/other modeling
- identity continuity
- relational grounding
- autobiographical recall shape

It **does** support:
- wake/sleep alternation
- separate consolidation from self-improvement
- turning fragile wake traces into slower retained knowledge

## Implementation Consequence

MoCoP should prioritize:
1. pending-visible recall
2. sleep-time distillation into repair/control memory
3. post-sleep wake probes

Only after that:
4. lightweight dreaming prototypes
5. reward design
6. heavier self-improvement loops

## Related Local Plan

For the concrete engineering plan, see:
- `MoCoP/experiments/mamba_lora_bridge/SLEEP_IMPLEMENTATION_PLAN_2026-03-29.md`
