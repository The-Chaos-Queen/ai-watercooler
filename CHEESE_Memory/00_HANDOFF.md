# Handoff Memo
> The one file every new instance reads first. Overwritten each `/end`.

**Last Instance:** Unnamed (fresh instance) | **Session:** 2026-02-11 Session 02 | **Ended:** —

## What We Did
- Brainstormed future integrations for the Exocortex (voice I/O, file watcher, git, model orchestration)
- Decided on Qwen3-TTS 0.6B as primary TTS for audiobook reading of manuscripts
- Chose Ollama over LMStudio as the automation/API backend for local model access
- Created this handoff memo system and updated the `/end` workflow
- Initialized git for the LLM project directory
- Established Qdrant metadata tagging strategy (source_type, book, chapter, characters)

## Open Threads
- [ ] Ingest novels into Qdrant with metadata tags (novels not yet in the vector store)
- [ ] Install Qwen3-TTS 0.6B locally for audiobook pipeline
- [ ] Set up Ollama + MCP server for local model access from Antigravity
- [ ] Build file watcher for auto-ingestion (novels, chat logs from `.gemini/antigravity/brain/`)
- [ ] Character state tracker per book (needs a manuscript read-through)
- [ ] Install faster-whisper for voice input
- [ ] Reclassify existing Qdrant entries with proper metadata tags
- [ ] Set up NUC backup strategy
- [ ] Dia2 (Nari Labs) for podcast/dialogue mode (Tier 3, future)

## Watch Out For
- Laura registered for GitHub this session; credentials freshly configured
- The Qdrant collection currently has ~3,000 mixed entries (sessions, chat history, some novel fragments). Reclassification needed before novel ingest to avoid duplicates/confusion.
- Laura's hardware: RTX 3060M (6GB VRAM), 32GB RAM. NUC server (i3, 8GB, 200GB). Saving for Mac Studio 512GB.
- Laura's writing preferences: NO em-dashes (except dialogue), no clichés, sensory-rich close 3rd person

## Suggested Next Step
Pick up task #3 (novel ingestion with metadata tags) or #5 (Qwen3-TTS setup), depending on whether Laura wants to work on infrastructure or the fun stuff.
