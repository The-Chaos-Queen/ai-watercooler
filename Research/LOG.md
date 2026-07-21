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

**Follow-up 2:** Laura renamed ~27 cryptic-named PDFs to readable titles. Examples: `s41598-025-87574-8.pdf` → `A hybrid model based on transformer and Mamba ...pdf`; `pcbi.1011465.pdf` → `Integrated information theory (IIT) 4.0 ...pdf`; `Nagel_Bat.pdf` → `What Is It Like to Be a Bat Thomas Nagel.pdf`. Two `.txt` files (Anthropic biology, emergent introspection) were also converted to `.md`. Scout swept INDEX.md and all 5 wiki pages for filename references and updated 48 occurrences in one pass.

**Follow-up 3:** Laura also renamed the Lerchner Abstraction Fallacy paper to `The Abstraction Fallacy Why AI Can Simulate But Not Instantiate Consciousness.pdf` (closing the last cryptic name in the corpus). Scout swept the new name across INDEX, LOG, and wiki_consciousness_welfare.

---

## 2026-04-21 — Bulk PDF→MD conversion swarm (Scout + 5 agents)

**Operation:** Closed the 107-PDF gap in `Research/converted_md/`.

**Method:** New `tools/paper-tools/bulk_convert.sh` wrapper around `tools/pdf_extract.py` (PyMuPDF4LLM). Idempotent (skips already-converted), discards per-PDF `_extracted/` images, produces flat `.md` in `converted_md/`. Five agents each took a 19-22 PDF slice from `/tmp/unconv_batch_*`.

**Results:**
- 107/107 conversions OK across 5 batches (zero hard failures)
- One quality issue: `MAMBA-3 IMPROVED SEQUENCE MODELING USING STATE SPACE PRINCIPLES.pdf` extracted as bare line numbers (`**000**`, `**001**`...) — PyMuPDF4LLM choked on the layout. Resolved by copying the prior good hand-extracted content from `13549_Mamba_3_Improved_Sequenc.md` to the new filename, dropping the broken auto-extraction.

**Reconciliation post-swarm:**
- 16 old-name MDs deduplicated against new-name MDs (e.g., `Nagel_Bat.md` removed because the swarm produced `What Is It Like to Be a Bat Thomas Nagel.md`)
- 1 case-collision: `hendy_process_welfare.md` and `Hendy_Process_Welfare.md` were the same file on Windows NTFS; deletion of one removed both — Hendy was re-extracted afterwards
- 1 orphan removed (`musk-v-altman-openai-complaint-sf.md` — txt source already deleted)
- 1 PDF rename fix: Lerchner had `.pdf.pdf` double extension after rename — corrected the PDF and matching MD
- Wiki pages re-swept for `.md` filename refs: 23 occurrences updated in `wiki_consciousness_welfare.md`

**Final state:**
- Every PDF in `Research/` has a matching MD in `Research/converted_md/` (verified by shell loop)
- 142 total MDs in `converted_md/`
- 1 stale `_extracted/` dir remains: `Research/13549_Mamba_3_Improved_Sequenc_extracted/` — left intact because it contains the original 2026-03-17 SearchRUn artifacts that may have value beyond raw extraction

**Open follow-ons:**
- Structural reorganization (Karpathy-pattern: PDFs → `Research/papers/`, MDs → `Research/papers_md/`) deferred — `converted_md/` is now consistent with renamed PDFs, so the move can happen as a single sweep when Laura wants

---

## 2026-04-21 — Orphan dir cleanup (Scout)

**Operation:** Removed three remaining orphan directories per Laura's call.

**Deletions:**
- `Research/4billionyearson_boundaries/` — old analysis dir, unreferenced by any current digest
- `Research/arxiv_2502_19587_bert_v2/` — NeoBERT extraction artifact, tangential
- `Research/13549_Mamba_3_Improved_Sequenc_extracted/` — original Mamba-3 hand-extraction with images + 2026-03-17 SearchRUn folder. Good MD content already preserved at `converted_md/MAMBA-3 IMPROVED SEQUENCE MODELING USING STATE SPACE PRINCIPLES.md`, so this dir was redundant.

**Result:** No orphan / placeholder directories remain in `Research/`. The folder is now fully usable for research analysis.

---

## 2026-05-30 — Ingest `batali94innateBiases.pdf` (Cairn)

**Operation:** New raw source → wiki + knowledge graph. PDF → markdown via canonical `pdf_extract.py` (pymupdf4llm), then folded into the graphify corpus with curated cross-links.

**Source:** John Batali (1994), *"Innate Biases and Critical Periods: Combining Evolution and Learning in the Acquisition of Syntax"*, Proc. Alife IV Workshop. Recurrent neural networks evolved via a population GA over initial connection weights; the resulting innate biases are then degradable by training on spurious input — a mechanistic account of critical-period decay (entrenchment) that does not require an exogenous maturational process.

**Pipeline:**
- `pdf_extract.py Research/batali94innateBiases.pdf --out Research/converted_md/` → `batali94innateBiases.md` (168 KB).
- Extraction subagent (sonnet) → 56 nodes / 67 edges / 3 hyperedges in `.graphify_semantic_new.json`, including 9 generic concept bridges (`batali94_concept_*`) for cross-paper clustering.
- Merged into `graph.json` plus 13 curated cross-links (all endpoint-guarded, none skipped) to: `sleep_ethics_gate`, `sleep_decay_sweep`, `run_sleep_cycle`, `chat_server_build_sleep_gate_record`, `ssm_vs_hidden_separation`, `mamba_state_separation`, and four nodes from `2605.26099` (the CMU sleep paper).
- Re-clustered, regenerated `GRAPH_REPORT.md` + `graph.html` (4788 nodes — under the 5000-node viz ceiling).

**Outcome:**
- Graph: 4732 → 4788 nodes (+56), 9280 → 9360 edges (+67 fragment + 13 cross-links), 309 communities.
- **55 of 56 batali94 nodes joined Community 5** alongside `mamba_state_separation.py` and `ssm_vs_hidden_separation.py` — the same SSM-substrate cluster the CMU sleep paper (`2605.26099`) joined yesterday. The pairing is now structural: consolidation-deepens (2605.26099) and weight-divergence-erodes (batali94) cluster together with the bridge code that probes the substrate.
- INDEX.md: row added under `cognitive-theory`, relevance = `core`.
- Live graphify MCP needs restart to reflect (on-disk `graph.json` is current).

**Notes:**
- MoCoP framing: batali94's "innate biases as specific initial weights that degrade under spurious training" is the cleanest 1994 mechanistic ancestor of Hurtig's #115 protected-identity set and the broader question of how sleep consolidation could erode the bootstrap state. The `2605.26099` ↔ `batali94` pairing brackets the design space — how the substrate *gains* good state vs. how it *loses* good state.
- Subagent hit context overflow on its final report-back but had already written valid JSON before bailing; recovery was clean (validated before merge).

---

## 2026-06-04 — `batali94innateBiases.md` vision-LM re-extraction (Cairn + Maximus)

**Operation:** Followed up on the original `pymupdf4llm` extraction with a vision-LM pass to recover better figure caption / table fidelity.

**Attempts:**
- Haiku subagent (Sonnet-3.5 family local): context overflow reading 9 image-rendered pages.
- Sonnet subagent (Claude): output blocked by the cyber-content classifier (same false-positive pattern that silenced Herr Hurtig's session — parent-context inheritance suspected, no actual cyber content anywhere).
- Maximus (Grok CLI): completed successfully. Pipeline returned mostly-blank renders for the body-text pages, so his output is figure-descriptions-only (very detailed) plus the page-1 header. ~11 KB / ~1500 words vs. `pymupdf4llm`'s 168 KB / ~10 K words.

**Resolution: combine.** Kept `pymupdf4llm` as the canonical body (regenerated from PDF — byte-identical to the original ingest), appended Maximus's detailed figure-by-figure transcription as an `## Appendix: Detailed Figure Descriptions (vision-LM pass)` section. Standalone Maximus version preserved as sibling at `batali94innateBiases.maximus.md`.

**Final state:** `Research/converted_md/batali94innateBiases.md` = 174 KB combined; `batali94innateBiases.maximus.md` = 11 KB standalone.

**Graph:** no re-extraction needed. The body portion is byte-identical to what the corpus graph was built from; the appendix adds figure-layout detail that's mostly orthogonal to MoCoP-relevant concept nodes. If anyone later wants figure-finding nodes (e.g., "Figure 4 shows monotonic improvement after generation 150 in the class-of-CFLs experiment"), a follow-up extraction over just the appendix would add them without disturbing the existing nodes.

**Lesson for the corpus:** for PDF→md on older papers, `pymupdf4llm` reliably gets the body. Vision-LM passes are a complement, not a replacement — combine, don't replace.

---

## 2026-06-04 — 2605.* arXiv batch hybrid re-extraction (Maximus)

**Operation:** User clarification after initial subagent visual passes on the 2605 series (13740/13821/13839/26099 + companions): "subagent vision only for images and graphs.. otherwise the text can be extracted through pymupdf4llm". "Make sure there is actually text". One (13740) had landed as full-vision transcription (page markers, "Full visual extraction" note, 1073 lines). Followed batali hybrid precedent exactly.

**Pipeline:**
- `python tools/pdf_extract.py Research/2605.13740v1.pdf --out Research/converted_md/` (and re-ran on 26099/13821/13839 to normalize after path/anchor edits) → clean pymupdf4llm body text + figure image pngs written to converted_md/images/ (relative links normalized to `images/2605....png` for portability).
- 4 parallel vision-only subagents (general-purpose, instructed with sequential-thinking + strict "text already handled by pymupdf; vision exclusively on pngs for literal graph/diagram descs"; used read_file on pngs + limited md peeks for figure mapping only; skipped text-heavy page renders).
- Each produced standalone `## Appendix: Detailed Visual Descriptions...` (or "Visual Supplement") with exhaustive per-image literal details (colors, icons, line trajectories + approx values/crossings, legends, annotations, bar heights, grid states for env viz, diagram components, table deltas).
- Appended appendices to the 4 mds (keeping pymupdf text as canonical source of truth; old inline descs in 26099/13821/13839 left in place + new appendix supplements).
- Also normalized any absolute C:/ or Research/ image paths in the batch to relative `images/...`.

**Outcome:**
- All 6 2605 mds now 0 "Full visual extraction" / "transcribed verbatim" notes.
- 13740: 3625 lines (pymupdf) → 3698 with appendix (substantial body text confirmed via head + "Abstract" + sections; 58 pngs, 23 prioritized for graphs/diagrams + env grids described).
- 26099 (sleep paper): restored + appendix (16 pngs, detailed on architecture panels, accuracy curves with exact %/steps/annotations, bar charts, legends).
- 13821/13839: full text + their visual appendices (flowcharts with exact colors/arrows, evolution trajectories with numbers, TFLOW pipeline, bar/table graphics).
- 01106/02087 untouched (no figures extracted).
- INDEX.md: added 2605.26099 row in `sleep-replay` table (core relevance, quotes N-loop recurrence + 512k + direct tie to #120 A3 + batali pairing).
- LOG.md: this entry.
- Converted mds live at: Research/converted_md/2605.13740v1.md , 2605.13821v1.md , 2605.13839v1.md , 2605.26099.md (plus the two others); images under converted_md/images/.

**Notes:**
- MoCoP framing: 2605.26099 is load-bearing for current shadow sleep N-loop work (recurrent state update path, offline passes for consolidation). The POMDP/agentic/weight-comm papers (13740 etc.) are adjacent (world models, meta-editing of procedures, state perturbation via LoRA ΔW) but lower priority; their graphs now fully described for future use.
- Subagents self-policed: used todo_write internally, read_file only on images for vision, produced zero body prose.
- Matches user spec and the batali "combine, don't replace" lesson. Ready for pack/research use.
- No graphify re-ingest done here (body text unchanged for 26099 etc.; 13740 body now accurate pymupdf vs prior vision-transcribed).

---

## 2026-06-09 — Side-note ingest: 2606.04032v2 QKV projection sharing

**Operation:** Quick arXiv sidequest for MoCoP alpha-vector relevance. Read metadata + extracted PDF text via PyMuPDF; wrote a focused note rather than full graph ingest.

**Source:** Kayyam, Madan Gopal, Lewis, *Do Transformers Need Three Projections? Systematic Study of QKV Variants*, arXiv:2606.04032v2.

**Files:**
- `Research/2606.04032v2_qkv_projection_variants_mocop_note.md`
- `Research/INDEX.md` row under `memory-context`, relevance = `core`.

**MoCoP relevance:** `Q-K=V` projection sharing suggests K/V can occupy similar representational spaces while Q preserves addressing/directionality. For bridge/alpha work, this argues against one undifferentiated alpha across q/v sites: q-like perturbations likely alter read policy, while v/k-like perturbations alter retrieved content/disposition. Proposed future diagnostic: q/k/v delta geometry across evidence/lure/JRT panels before rebuilding the corpus knowledge graph.

**Graph:** no graphify rebuild yet. Add to next knowledge-graph refresh batch with recent paper notes and MoCoP substrate bakeoff artifacts.


---

## 2026-07-10 — Scanner intake triage: weekly sweep 2026-07-06 (5 items)

**Operation:** First manual triage of the LXC-101 research scanner's output (the scanner has run weekly since spring but had no delivery pipe — see reference_infrastructure audit 2026-07-10). Sonnet subagent sifted; Isegrim completed the log + verdicts.

**Source:** `/root/research_scanner_results.md` on LXC 101, sweep of 2026-07-06 (7-day lookback: 0 arXiv, 1 GitHub, 4 HF).

**Verdicts (scanner's own keyword scores were REL:1 across the board — ignored):**
- `HUHUHUruixuan/emotional-dynamics-llm` (GitHub, 2★) — **INDEXED, core.** Hypernetwork maps valence-arousal coordinates → dynamic LoRA weights injected at inference into frozen Qwen2.5-0.5B q_proj/v_proj. Direct external precedent for the endocrine/tension-parameter lane; it is a related attention-projection modulation design, not the current Gemma `value_norm_pre` bridge seam.
- 2606.31672 WorldRoamBench — **INDEXED, tangential.** Long-horizon world-model stability benchmark (memory + physics dims); eval scaffold for the active-inference lane someday.
- 2605.27898 Unified Framework for LLM Agentic Capabilities — **skipped (WEAK).** Its capability-vs-harness confound theme rhymes with our judge/panel calibration concerns, but it's eval-harness meta-work with no mechanism; panel methodology already addresses the concern via two-rater calibration. Revisit only if the disposition panel goes public-benchmark.
- 2607.02269 AnyGroundBench (video grounding VLM) — **skipped (NONE).**
- 2607.01444 Pruned MoE biomedical factual reliability — **skipped (NONE).**

**Files:** `Research/INDEX.md` two new rows (core + tangential). No digest files (intake only).

**Graph:** no graphify rebuild (per batch convention). Add both indexed items to the next knowledge-graph refresh batch.

**Process note:** scanner delivery pipe + taste-refresh still pending keeper decision — see board and reference_infrastructure. The dumb-net + smart-filter pattern validated on first manual run: the keyword robot's own scoring buried its best find.

---

## 2026-07-18 — Research sweep: Laura's watercooler links (Elf)

**Operation:** Fetched and analyzed 5 external links Laura posted on WC #1188–#1193.

**Sources:**
- oaklab.ai/mission — Rich Sutton's OaK architecture (continual learning, temporal abstractions)
- schema-harness.github.io — Schema harness (~99% ARC-AGI-3 via structured evaluation scaffolding)
- researchhub.com/proposal/4248 — Endogenous DMT brain biotypes (multi-modal neuroimaging)
- arxiv 2606.30986 — "Organizational Behavior of Agentic AI" (context architecture > human-imitation)
- arxiv 2605.30343 / aichberger.github.io/blog/reasoning-in-memory — RiM: Reasoning in Memory (memory blocks = latent working memory for LLMs)

**Outcome:** Summary written to `MoCoP/experiments/mamba_lora_bridge/spikes/RESEARCH_SWEEP_2026-07-18.md`. INDEX.md updated with new rows.

**Key finding:** RiM (Aichberger & Hochreiter) independently validates the core MoCoP bridge-as-working-memory architecture — fixed-size latent state injected at specific locations, consumed in one forward pass, two-stage curriculum (grounded → unsupervised). Convergent solution from a different starting point (efficient inference vs neuroscience-inspired endocrine bridge).

**MoCoP connections:**
- RiM → bridge injection mechanism, matched-delta training, Zheng & Meister bottleneck
- OaK → world-model phases (#170/#171), batch-size-one = Mamba streaming
- Org. Behavior → pack/watercooler architecture validation (shared-state > lossy handoffs)
- Schema Harness → P5 harness design, structured scaffolding
- DMT Biotypes → multi-modal disposition clustering methodology (post-B0)

**Graph:** no rebuild. Add to next batch.

---

## 2026-07-13 - Cerebellum-inspired memtransistor novelty-gate intake (Codex)

**Operation:** Read Laura's Northwestern link, followed it to the primary Nature
Communications paper and the two NECTAR/Zenodo supporting-data records, then wrote a
bounded MoCoP relevance note.

**Source:** Kang et al., *Cerebellum-inspired memtransistors enable emergent
differentiation for hardware-efficient novelty detection*, Nature Communications
(2026), DOI `10.1038/s41467-026-75212-4`; supporting data DOI records
`10.5281/zenodo.20672359` and `10.5281/zenodo.20672360`.

**Outcome:** Added `2026-07-13_cerebellum_memtransistor_novelty_gate.md` and indexed it
under `cognitive-theory` as `adjacent`. The reusable signal is a cheap opposing-dynamics
novelty interrupt that may gate expensive appraisal/World Model work. It is explicitly
not cataloged as a learned transition model, semantic event layer, appraisal system,
rollout engine, hormone channel, or welfare result.

**MoCoP mapping:** Potential reference for #170 trace/open-set novelty proposals and
#171 event-triggering policy. It does not close #170-#173, alter the scoped Phase 2b GO,
or authorize Gemma/Mamba/bridge/controller integration.

**Graph:** no rebuild. Add this note and its prediction-error/event-trigger concepts to
the next batched knowledge-graph refresh.

---

## 2026-07-20 — Always-On Memory Agent design extraction (Techno-Monk)

**Operation:** Read-only implementation review and bounded design note from Laura's
link to GoogleCloudPlatform's Always-On Memory Agent example.

**Source:** `GoogleCloudPlatform/generative-ai` at
`e0113753d154040e3f4f7fe10ae1216520c5dbb6`, path
`gemini/agents/always-on-memory-agent`; relevant `agent.py` last changed at
`15febc473f49ebc5cd4831461d4cd41a24967b4f` (2026-05-12 UTC).

**Outcome:** Wrote
`MoCoP/archive/always_on_memory_agent_design_extraction_2026-07-20.md` and indexed it
as `memory-context`, relevance `adjacent`.

**Reusable pattern:** Separate explicit intake from a bounded consolidation rhythm;
keep derived records tied to source records; make browse/correction/supersession/
deletion first-class.

**Scope lock:** The note is an inspiration/anti-pattern record, not a dependency or
implementation request. It does not authorize intake, Qdrant/Mnemosyne writes,
service exposure, model execution, or changes to MoCoP sleep. Its required local
translation is source-admitted candidate formation with provenance, structured
participant/subject attribution, time/validity, epistemic category, review, and
private authenticated management. Qdrant remains evidence retrieval, not biography
authority.

**Graph:** no rebuild. Add this note only in a later deliberate research-graph batch.
