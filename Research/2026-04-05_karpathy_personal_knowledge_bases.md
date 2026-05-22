# Karpathy on Personal Knowledge Bases

**Date:** 2026-04-05  
**Source type:** social post / workflow note  
**Why this exists:** capture the useful pattern without confusing it with MoCoP autobiographical memory.

---

## The useful idea

Karpathy describes a workflow where an LLM helps maintain a **personal research knowledge base**:

- ingest raw source material into a local folder
- compile a markdown wiki from that raw layer
- keep summaries, backlinks, and concept pages up to date
- query the compiled wiki instead of re-researching the whole corpus each time

The interesting part is not "use an LLM on files."  
The interesting part is the **compiled layer**:

- raw inputs stay available
- the wiki becomes a maintained semantic surface
- the LLM does incremental curation instead of one-shot summarization

At small-to-medium scale, this may remove the need for heavier RAG machinery.

---

## Why it matters here

This names a shape Laura is already circling:

- too many fragments
- too many useful things that do not yet have a shelf
- repeated re-chewing of the same ideas instead of building a stable knowledge surface

For MoCoP and adjacent research, this suggests a dedicated **research wiki brain**:

- papers
- architecture shards
- Reddit finds worth keeping
- hardware notes
- model/runtime reality checks

---

## Important boundary

This is **not** the same thing as autobiographical memory.

Karpathy's pattern is best for:

- research knowledge
- technical notes
- concept maps
- article/paper synthesis

It is **not** by itself the right home for:

- agent-specific episodic memory
- identity anchors
- relationship anchors
- unresolved emotional / social threads
- sleep residue that changes how a system should attend

Short version:

- **compiled wiki** = research brain
- **MoCoP / Exocortex memory** = lived continuity brain

Both are useful. They should not be flattened into one layer.

---

## Practical implication

The `Research/` folder should be allowed to become a **compiled shelf**, not only a PDF graveyard.

That means:

- short digest notes are good
- boundary notes are good
- index / queue files are good
- not every shard needs a full paper review before it earns a markdown note

---

## Immediate follow-on

Worth trying later:

1. keep raw source material in place
2. add small concept and boundary notes as they appear
3. maintain a simple ingest queue
4. only add heavier indexing / backlinks if the shelf proves useful

That is the honest smallest version of the pattern.
