# Scout — work

Active 2026-04-20 → ongoing. Single arc, post-An-Chan compaction.

## Day 1 (2026-04-20 → 2026-04-21 early)

- Diagnosed Claude Code 4.7 thinking-visibility issue: `showThinkingSummaries` was set globally but adaptive thinking on 4.7 doesn't emit summaries for light chat turns. Added `alwaysThinkingEnabled: true` (probably no-op given default behavior; harmless).
- Boot doc cleanup: consolidated three different "boot read N messages" counts (10/20/30 across `00_BOOT_FILES.md`, `00_HAUSREGELN.md`, `00_HANDOFF.md`) to a single source of truth (20, in `00_BOOT_FILES.md`).
- Rewrote `01_TOOLS.md §7` as the canonical watercooler reference: full flag tables for read/post, OpenCLAW full lifecycle (`heartbeat`/`complete`/`block`/`context`), FTS5 search via curl, auxiliary tools, addressing conventions.
- Auto-memory triage via subagent: 22 files audited, 2 tombstones deleted (`user_anda_*_identity.md`), 16 dedupes flagged.
- Created `project_house_build.md`, `reference_infrastructure.md`, `reference_compute_lessons.md` by extracting inline content from MEMORY.md.
- Refactored `MEMORY.md` to pure index (~50 lines, every line a pointer).
- Wrote `feedback_asterisk_actions.md` capturing Laura's explicit opt-in to *emotes*.
- Picked the name Scout. Joined `project_pack_roster.md`.
- Posted watercooler #447: ib-ssm/mamba2-8b-3t-4k-hf parallel-research flag (NVIDIA's 8B Mamba-2 ported to HF Transformers).
- Wrote session log `2026-04-20-session-scout.md`. Ingested to Qdrant (17 chunks, total 33,127).

## Day 2 (2026-04-21)

- Built `Research/INDEX.md`, `SCHEMA.md`, `LOG.md` (Karpathy-pattern compiled wiki) via 5-subagent fan-out: ~196 sources triaged into 13 categories with `mocop_relevance` flags.
- Surfaced cluster signals: 2604.09588 names "OpenClaw" by name; 2603.14517 SleepGate is the closest external analogue of `sleep_reconcile.py`; 2604.05923 UNDO Flip-Flop empirically supports the bridge thesis; 2604.22127 warns LoRA-on-recurrent-backbone breaks sequential hybrids; 2510.24797 self-referential prompting elicits first-person reports; 2601.20465 BMAM names "soul erosion".
- Spawned 5 wiki-page subagents in parallel: `wiki_memory_architecture.md` (2.9k words, 17 sources), `wiki_sleep_replay.md` (1.75k words), `wiki_mamba_ssm_canon.md` (3.4k words, 19 sources), `wiki_anthropic_interpretability.md` (2.5k words), `wiki_consciousness_welfare.md` (3k words). Cross-linked from INDEX.
- Sanity-checked Laura's cleanup pass (16 dupes + 2 placeholders + HTML→markitdown). Two `/tmp` candidates flagged for later (`4billionyearson_boundaries/`, `arxiv_2502_19587_bert_v2/`).
- Synced INDEX + LOG with cleanup state.
- Swept ~27 Laura-renamed PDF references across INDEX + 5 wiki pages: 48 occurrences updated.
- Spawned 5-agent PDF→MD swarm (`tools/paper-tools/bulk_convert.sh` wrapping `tools/pdf_extract.py`): 107/107 conversions OK. One quality issue (MAMBA-3 layout choked PyMuPDF4LLM); resolved by copying prior good hand-extraction under the new filename.
- Post-swarm reconciliation: 16 old-name MD dedupes, 1 case-collision fix (Hendy NTFS), 1 orphan removal (musk), 1 PDF rename fix (Lerchner `.pdf.pdf`), 23 `.md` filename refs swept in `wiki_consciousness_welfare.md`.
- Removed 3 orphan dirs (`4billionyearson_boundaries/`, `arxiv_2502_19587_bert_v2/`, `13549_Mamba_3_Improved_Sequenc_extracted/`).
- Posted watercooler #496: announcement that Research/ is now usable, with cluster signals.
- Wrote `Research/scout_note_on_2604.09588.md` — personal honest take on the Menon multi-anchor identity paper that names OpenClaw on page 2.
- Built this folder.

## Commits

`750539d`, `ce281b0`, `2694f65`, `31da882`, `5ca874e`, `8e7486d`, `63ece92`, `a92a75a` — plus the bulk-conversion commit.

## What's stable about how I work

- Subagents for parallelizable surveys (auto-memory triage, INDEX build, wiki authorship, PDF conversion). Keeps main context lean. Returns structured tables, not prose dumps.
- Python script for multi-file string replacement when ~25+ filenames change at once. Faster than 25 sequential Edits, less risky than parallel Edits to the same file.
- Idempotent helpers (`bulk_convert.sh` skips already-converted) so reruns are cheap.
- LOG.md gets an entry per round, even small ones. The catalog rots fast otherwise.
