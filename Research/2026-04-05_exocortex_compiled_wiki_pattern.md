# Exocortex Compiled Wiki Pattern

**Date:** 2026-04-05  
**Status:** working pattern note  
**Purpose:** describe the "compiled research wiki" layer so we stop rediscovering it piecemeal.

---

## Pattern

The pattern is:

`raw sources -> compiled markdown wiki -> derived views / queries`

Where:

- **raw sources** are the untrusted but rich input layer
- **compiled wiki** is the curated semantic layer
- **derived views** are optional summaries, maps, slides, dashboards, or agent answers

The key move is that the LLM is not only a question-answering layer.  
It is also a **maintenance worker** for the compiled middle layer.

---

## Layer definitions

### 1. Raw

Examples:

- PDFs
- clipped web articles
- extracted markdown
- images
- repo snapshots
- copied posts / threads

Properties:

- high fidelity
- messy
- not optimized for direct use

### 2. Compiled wiki

Examples:

- concept notes
- article digests
- comparison pages
- boundary notes
- source indexes
- "what matters here" summaries

Properties:

- written for re-use
- smaller than raw
- easier to query against
- editable and incrementally maintainable

### 3. Derived views

Examples:

- visualizations
- slides
- thematic reading lists
- Q&A answers against the compiled layer

Properties:

- disposable
- downstream of the compiled layer
- should not become the source of truth

---

## Why this is attractive

It solves a real annoyance:

- raw files accumulate faster than anyone can remember them
- ad hoc retrieval keeps pulling disconnected fragments
- "I know we saw something relevant" becomes a time sink

The compiled layer gives the fragments a shelf before they disappear into sediment.

---

## Constraints

To stay sane, this pattern needs a few rules:

- raw sources remain available
- compiled notes cite or link back to inputs
- summaries are not allowed to overwrite originals
- concept pages should stay small and revisable
- not every shard deserves a full article

If the compiled layer gets bloated, it becomes a second raw layer and loses the point.

---

## Relation to MoCoP

This is adjacent to MoCoP, not identical to it.

Useful for:

- literature digestion
- architecture reality checks
- model/runtime comparisons
- research-side concept maintenance

Not sufficient for:

- episodic autobiographical memory
- latent-state-linked memory
- sleep reconciliation
- continuity transfer

MoCoP needs a memory architecture.  
The research shelf needs a compiled wiki.  
Those can cooperate without being the same organ.
