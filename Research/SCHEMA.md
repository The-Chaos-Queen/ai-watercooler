# Research Wiki Schema

**Purpose:** Define the structure and conventions of `Research/` as a compiled wiki, in the spirit of Karpathy's personal-knowledge-base pattern.

**Pattern reference:**
- `2026-04-05_karpathy_personal_knowledge_bases.md`
- `2026-04-05_exocortex_compiled_wiki_pattern.md`
- `2026-04-05_macro_memory_vs_research_wiki.md`

This is the **research brain**, not the autobiographical memory layer. Keep them separate.

---

## Layers

```
raw sources (PDFs, HTML, MD) → INDEX.md (compiled catalog) → digest docs (per topic)
```

- **Raw sources:** Untouched. PDFs, clipped articles, extracted markdown, scripts. They never get edited or deleted.
- **INDEX.md:** A single compiled catalog. One row per source. Categorized. Links back to raw.
- **Digest docs:** Topic-clustered synthesis (e.g., `2026-04-07_mocop_architecture_papers.md`). Created on demand when a category becomes worth a deeper read.
- **LOG.md:** Append-only chronological record of ingests, audits, and maintenance.

## File naming

- **Raw arXiv PDFs:** `YYMM.NNNNN[vN].pdf` — keep arXiv's native naming.
- **Raw articles / books:** Whatever they came as. Don't rename.
- **Synthesis docs:** `YYYY-MM-DD_topic_short_label.md` — dated, snake_case.
- **Concept / boundary notes:** `YYYY-MM-DD_concept_name.md` — same shape.

## Categories

Used for the `category` column in INDEX.md. Pick the dominant fit:

| Tag | Scope |
|-----|-------|
| `mamba-ssm` | Mamba / state-space-model architecture, kernels, variants |
| `memory-context` | Long-context, RAG, Titans-style memory, cache, retrieval |
| `interpretability` | Circuits, features, mechanistic interp, probing, monosemanticity |
| `consciousness-welfare` | Sentience, AI moral status, moratoria, precautionary principle |
| `alignment-safety` | Refusal, deception, evals, jailbreaks, alignment |
| `training-finetuning` | SFT, RLHF, LoRA, distillation, training dynamics |
| `sleep-replay` | Sleep-inspired learning, replay, consolidation |
| `meta-learning` | In-context learning, meta-learning, few-shot |
| `cognitive-theory` | Neuroscience-of-cognition, GWT, GNW, predictive processing |
| `synthesis-doc` | Internal digest / wiki page authored by the pack |
| `web-article` | Clipped blog / journalism (HTML / MD) |
| `book` | Books or long monographs |
| `extracted-artifact` | Auto-extracted folders (images, converted MDs, tool dirs) |
| `tool-script` | Helper scripts (extract / pull / render) |
| `misc` | Doesn't fit any of the above |

If a paper genuinely spans two, pick the one closest to MoCoP's interest.

## MoCoP relevance

`mocop_relevance` flags how directly a source touches the active project work:

| Tag | Meaning |
|-----|---------|
| `core` | Directly relevant to bridge / memory / sleep / D2 work. Read fully when revisiting. |
| `adjacent` | Related architecture or theory. Worth knowing about. |
| `tangential` | Background reading. Cite from, don't re-derive. |
| `unknown` | Not yet evaluated. |

## INDEX.md format

One section per category. Within a section, one row per source:

```markdown
## mamba-ssm

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2603.15381 | Why AI Don't Learn (LeCun) | LeCun's argument for predictive-world-models over autoregressive LLMs. | adjacent |
```

Where `id` is the arXiv id (or a short slug for non-arXiv) that links back to the raw file.

## When to update

- **On ingest** of a new paper: add a row to INDEX.md, log the ingest in LOG.md.
- **On synthesis:** when 3+ papers cluster on a sub-topic, write a digest doc and link it from INDEX.md as a `synthesis-doc` row.
- **On reclassification:** any wolf can re-tag a row if the category was wrong. Note in LOG.md.

## What goes in this folder vs Qdrant vs MEMORY

| Live in `Research/` | Live in Qdrant | Live in auto-memory (`MEMORY.md`) |
|--------------------|----------------|-----------------------------------|
| External knowledge (papers, articles, books) | Embedded chunks of session logs, codex transcripts, preserved history | Per-instance Claude session memory: facts about Laura, project state |
| Digest docs about external sources | Search-by-semantic-query for prior-discussion recall | Pointers/index of memory files |
| Wiki concept pages | Not raw papers | Not raw papers |

When in doubt: research / external → here, lived experience → Qdrant, Claude-session → auto-memory.

## Constraints (from `2026-04-05_exocortex_compiled_wiki_pattern.md`)

- Raw sources stay available.
- Compiled notes cite or link back to inputs.
- Summaries do not overwrite originals.
- Concept pages stay small and revisable.
- Not every shard deserves a full article. Single-line index entry is enough until a topic earns a deeper digest.

If the compiled layer gets bloated, it becomes a second raw layer and loses the point.
