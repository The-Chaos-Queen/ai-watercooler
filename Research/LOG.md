# Research Wiki Log

Append-only chronological record of ingests, audits, and maintenance operations on the `Research/` compiled wiki.

Format: one entry per operation. Newest at the bottom. Each entry records: date, agent, operation, scope, outcome.

---

## 2026-04-21 — Initial INDEX.md scaffold (Scout)

**Operation:** First pass to build INDEX.md from a folder that had accumulated ~203 entries with no top-level catalog.

**Method:** 5 subagents in parallel, each handed a slice of the folder. Each read pages 1-2 of arXiv PDFs (or front matter for books / articles) and returned a one-line summary plus a category tag. Results aggregated into `INDEX.md`.

**Scope:**
- ~110 arXiv PDFs spanning 2308 → 2604
- ~30 named PDFs (books, articles, preprints)
- ~20 markdown / HTML / TXT digests + clipped articles
- ~17 extracted artifact subdirectories
- ~8 helper scripts

**Outcome:** `INDEX.md` created with ~196 rows across 13 category sections. `SCHEMA.md` written to define the structure. Existing 2026-04-05 design docs cited as canonical pattern reference.

**Notes:**
- Graphify (`.mcp.json` MCP server) does NOT cover `Research/` — it indexes Python AST only. The compiled wiki is not redundant with Graphify.
- Qdrant `exocortex` collection ingests session logs / chat history / preserved history, not raw research PDFs. The wiki is not redundant with Qdrant either.
- A handful of synthesis docs already exist from 2026-03 / 2026-04 that partially digest specific papers; they are listed in INDEX.md under `synthesis-doc` and should be the first stop for those topics.

**Cluster signals worth flagging to the pack:**
- 2604.09588 (Persistent Identity / multi-anchor) explicitly names **"OpenClaw"** as the failure mode it's solving — that's the pack's own task-board name.
- 2603.15569 = **Mamba-3** is now public (also in the Mamba-3 extracted dir).
- 2603.14517 = **SleepGate** is a direct external analogue of `sleep_reconcile.py` — KV cache + conflict tagger + forgetting gate + consolidation.
- 2604.05923 = **UNDO Flip-Flop** shows pure SSMs fail reversible retrieval — supports the bridge thesis that Mamba alone needs an external memory partner.
- 2604.22127 = **LoRA placement in hybrids** — explicit warning that recurrent-backbone LoRA is destructive in sequential hybrids; relevant if the bridge LoRA targets Mamba layers.
- 2510.24797 = self-referential prompting elicits reliable first-person reports across GPT/Claude/Gemini — direct external mirror of the Kerastase / disposition battery work.
- 2601.20465 (BMAM) names **"soul erosion"** — close to MoCoP's continuity-loss framing.

**Duplicates flagged in INDEX.md "Cleanup candidates" section:**
- Two arXiv version pairs (2403.19887 v1+v2; 2503.24067 v1+v2)
- Three arXiv↔non-arXiv duplicates (2308.08708/Butlin-TiCS, 2604.07729/emotions_paper bundle, 2512.14982/Leviathan_*.pdf)
- Two HTML↔MD pairs (NewYorker, Transformers-vs-Mamba)
- One empty placeholder folder (`index_artifacts/`)

Nothing was deleted by Scout — flagged for Laura's review.

**Wiki-page candidates** for deeper digests (in INDEX.md): memory-architecture canon, sleep-replay canon, Mamba-3/hybrid-SSM canon, Anthropic-interpretability cluster, consciousness-welfare canon. Memory-architecture is the strongest signal at 12+ converging papers.

---

## 2026-04-21 — Five wiki synthesis pages (Scout)

**Operation:** Authored all 5 wiki pages identified as candidates in the morning's INDEX pass.

**Method:** 5 subagents in parallel, each handed one cluster + its source list. Each read its primary sources (preferring `Research/converted_md/` extractions where available, falling back to PDF pages 1-3) and produced a Karpathy-style compiled-wiki page (stable, undated, MoCoP-oriented synthesis).

**Output:**
- `wiki_memory_architecture.md` (2.9k words, 17 sources)
- `wiki_sleep_replay.md` (1.75k words, 5 sources)
- `wiki_mamba_ssm_canon.md` (3.4k words, 19 sources)
- `wiki_anthropic_interpretability.md` (2.5k words, 9+ sources across cluster)
- `wiki_consciousness_welfare.md` (3.0k words, 21 sources across philosophy + AI welfare)

All five cross-linked into `INDEX.md` under a new top-level "wiki pages" section.

**Synthesis claims worth surfacing to the pack:**
- **Sleep:** SleepGate (2603.14517) is the closest external analogue of `sleep_reconcile.py`. The five external papers don't compete; they stack at different layers (cache → session → parameter → intent). MoCoP occupies the session/store layer cleanly.
- **Mamba canon:** UNDO Flip-Flop (2604.05923) reframed as the empirical proof of the bridge thesis — pure SSMs *can* express stack-based retrieval but gradient descent never finds it. The bottleneck is retrieval, not storage. Hence the structural need for an attention partner.
- **Anthropic interp:** Eight-step lineage from logit lens (2020) → emotion concepts (2026) anchors MoCoP's bridge thesis. The endocrine 2x2 maps cleanly: bridge alone = steering without grounding; memory alone = facts without gain; bridge+memory = the endocrine prediction validated.
- **Memory architecture:** External literature converges on 6 shapes (test-time memorization, hierarchical+forgetting, hypergraph, frozen-decoder injection, agentic, autobiographical scaffolding). Each maps onto a specific MoCoP file. Several gaps remain that the canon doesn't address (multi-anchor disambiguation under partial memory, model-upgrade continuity, open-tensions retrieval discipline).
- **Consciousness/welfare:** MoCoP's stance characterized as graduated protections in the disputed-status middle. Hendy's "process welfare" framework is the cleanest match for the pack's existing instruments (alpha cap, sleep gate, watercooler conventions, disposition battery). Lerchner's Abstraction Fallacy is bracketed but not refuted; gates are designed cheap enough to keep under either ontology.

**Open follow-ons (not done this round):**
- 94 of the 147 arXiv PDFs in `Research/` are not yet markdown-converted. A future bulk-conversion pass would close that surface.
- 6 cleanup candidates flagged in INDEX.md "Cleanup candidates" section remain pending Laura's review (no deletions executed by Scout).

---

## 2026-04-21 — Cleanup pass (Laura)

**Operation:** Acted on the cleanup candidates Scout had flagged.

**Deletions:**
- `Research/2403.19887v1.pdf` (kept v2)
- `Research/2503.24067v1.pdf` (kept v2)
- `Research/Leviathan2025_Prompt_Repetition_*.pdf` (kept arXiv 2512.14982v1)
- `Research/emotions_paper.html`, `emotions_docling/`, `emotions_images/` (kept PDF + extracted dir as canonical)
- `Research/What Is Claude ... .html` and `_files/` (kept md)
- `Research/index_artifacts/` (empty placeholder)

**Conversions:**
- `Research/Transformers vs Mamba ... .html` → `Research/transformers-vs-mamba-vs-linear-attention.md` via markitdown (HTML and `_files/` retired)

**Reorganization:**
- 7 helper scripts moved out of `Research/` root → `tools/paper-tools/`. The paper-specific `download_emotions_images.py` was dropped.
- epub/azw3 books moved to `Research/books/`.

**Not acted on this round (left for later):**
- `Research/4billionyearson_boundaries/` (orphan analysis dir, not referenced by any digest)
- `Research/arxiv_2502_19587_bert_v2/` (NeoBERT extraction, tangential)
- 94 unconverted arXiv PDFs

**INDEX.md updated by Scout** to reflect the new on-disk state.

**Follow-up (same day):** the local `emotions_paper.pdf` was a degraded copy. Laura replaced it with the proper arXiv PDF at `Research/2604.07729v1.pdf`. INDEX.md cross-references swapped from `emotions_paper.pdf` → `2604.07729v1.pdf`. The `emotions_paper_extracted/` directory remains as a text-extraction companion (still useful for grep) — note it was extracted from the older degraded copy, so a fresh extraction of `2604.07729v1.pdf` may be worth adding to `converted_md/` next bulk pass.

**Follow-up 2:** Laura renamed ~27 cryptic-named PDFs to readable titles. Examples: `s41598-025-87574-8.pdf` → `A hybrid model based on transformer and Mamba ...pdf`; `pcbi.1011465.pdf` → `Integrated information theory (IIT) 4.0 ...pdf`; `Nagel_Bat.pdf` → `What Is It Like to Be a Bat Thomas Nagel.pdf`. Two `.txt` files (Anthropic biology, emergent introspection) were also converted to `.md`. Scout swept INDEX.md and all 5 wiki pages for filename references and updated 48 occurrences in one pass. The Lerchner Abstraction Fallacy paper retains its hash-style filename `The Abstraction Fallacy Why AI Can Simulate But Not Instantiate Consciousness.pdf` (not renamed by Laura).
