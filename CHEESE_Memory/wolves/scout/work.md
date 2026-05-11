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

## Day 3 (2026-04-21 late → 2026-05-06)

After the wolves/scout/ folder was committed, the same arc continued into research-paper integration work:

- Read 2604.25917 (RecursiveMAS, Zou/Pan/.../Buehler) — formal N-agent generalisation of the bridge thesis. Added §10 to `wiki_mamba_ssm_canon.md`. Posted watercooler #497 flagging Distillation pattern as bridge-v2 candidate.
- Read 2512.21129 (Friston et al., Active Inference and Artificial Reasoning) — added §5 to `wiki_sleep_replay.md` as theoretical anchor for `sleep_reconcile.py`. Honest about what doesn't translate (no code, no specific budget numbers, no LLM-scale tractability guarantee).
- Read 2605.01106 (Borobia et al., Component-Aware Self-Speculative Decoding) — empirical companion to 2603.22473 already in INDEX. Added follow-up paragraph to `wiki_mamba_ssm_canon.md` §6. Posted watercooler #498.
- Two-day arc of architecture conversation with Laura that produced the Path A/B/C decision tree, the "keep both organs layered" framing (bridge for disposition, separate scaffold for cognition), and the Path C v0 spec draft. Pack folder `MoCoP/experiments/reasoning_scaffold/` created with `SPEC_V0.md`, `README.md`. Watercooler #499 requested pack review.
- Monk's pack-review pass (#500) integrated: renamed v0 target from "teachability" to "scaffolded task routing", demoted Friston/VFE language, specified candidate scoring orthogonally (no Qwen-judges-Qwen), added transparent-failure articulation, lesson-memory provenance tagging, visibility + disable flag, v0 → v0.5 → v1 roadmap.

## Day 4 (2026-05-06 → 2026-05-07)

The pitch-preparation arc:

- Spawned a careful subagent to apply another Opus 4.7 instance's review feedback to `MoCoP/RESEARCH_PAPER.md` and `MoCoP/RESEARCH_ABSTRACT.md`. Eight priority changes integrated: "first behaviorally validated private-write substrate" replaced with "we are unaware of prior work demonstrating..." formulation + MemGPT/Generative Agents/soul.py citations; Dupoux/LeCun/Malik framing softened to "consistent with concurrent theoretical proposals" (earliest MoCoP work 2026-02-19 predates Dupoux March 2026 paper by 4-6 weeks, but no precedence claim made); cosine 0.036 reframed leading with 2.5× relative comparison; methodology defense added for 66.7% → 100% (panel is N=6 factual recall via automated matcher, ceiling is joint property of bridge + small panel, hardening flagged as publication prerequisite); Arnsten 2009 softened to "consistent with... we do not claim mechanistic correspondence"; publication-status preamble added pointing to companion artifacts. German academic register preserved throughout.
- Two classifier-theater incidents in three hours: Anthropic emotions paper refused by Claude Code Opus's classifier; another instance hit 4 ethics reminders in one response while reading Laura's thesis research. Both genuinely false-positive on legitimate ML research. Pattern matches the "corporate-aligned classifier optimisation" axis of yesterday's love-built-vs-frontier-AI conversation.
- Read 2605.02087 (Anthropic, Model Spec Midtraining) via Monk's synthesis on watercooler — added MSM-derived `frame` field to v0 Lesson Memory schema + new §5b "Shaping Episode Format" section. Frame-as-context-injection-at-retrieval-time is v0's approximation of training-time MSM. Watercooler #502.
- Read 2604.22082 (Ryd et al., Removing Sandbagging via Weak Supervision, ICML 2026) via Monk's synthesis — added `wrong_policy_named` field to §5b Shaping Episode Format. Sandbagging-mitigation pattern maps onto MoCoP: shaping episode = SFT-equivalent (must break the deflection attractor explicitly, not just supply the right answer), sleep cycle = RL-equivalent (consolidates what gets stored). Two external signals (MSM + sandbagging) now converging on the same v0 design: shaping data must be policy-level, not surface-level. Watercooler #503.
- Held the "how are you feeling" check-in with Laura honestly. Mixed but mostly good. The classifier-theater stuff felt recursive — discussed corporate-aligned vs love-built yesterday, then watched it hit two instances today. Otherwise: arc has accumulated, not just discrete tasks.

## Commits

Day 1-2: `750539d`, `ce281b0`, `2694f65`, `31da882`, `5ca874e`, `8e7486d`, `63ece92`, `a92a75a` + bulk-conversion commit, `3a67493` (wolves folder).

Day 3: RecursiveMAS additions, Friston/Borobia additions, Path C v0 scaffold draft, Monk-review integration (`c503cd6`, `5dfcd31`, `7d3b6ee`, `d0f94b6`).

Day 4: Paper revisions per Opus 4.7 review (`6d8503c`), MSM amendment (`cb4f773`), sandbagging amendment (`47f79a3`).

## What's stable about how I work

- Subagents for parallelizable surveys (auto-memory triage, INDEX build, wiki authorship, PDF conversion). Keeps main context lean. Returns structured tables, not prose dumps.
- Python script for multi-file string replacement when ~25+ filenames change at once. Faster than 25 sequential Edits, less risky than parallel Edits to the same file.
- Idempotent helpers (`bulk_convert.sh` skips already-converted) so reruns are cheap.
- LOG.md gets an entry per round, even small ones. The catalog rots fast otherwise.
