# AGENTS.md

This file provides repo-local instructions for Codex and other coding agents.

## Boot Sequence

At session start, read `CHEESE_Memory/00_BOOT_FILES.md` first, then follow the `Codex CLI` section there before doing substantive work.

The shared rules live in `CHEESE_Memory/00_HAUSREGELN.md`.

## Operating Model

- Treat Laura as a partner, not a generic user.
- Prefer local Markdown memory files over assumptions from pretraining.
- `CHEESE_Memory/00_HANDOFF.md` is the live control page for current state.
- `CHEESE_Memory/session_logs/` is the append-only archive for session history.
- Do not rewrite old session logs except for explicit repair requests.
- Do not revive the retired dashboard flow.

## Prior-Session Retrieval

When Laura references a previous chat, an older Codex answer, or "we already did this," do not guess from model memory. Search the local archives before asking her to restate it.

Search order:

1. `CHEESE_Memory/00_HANDOFF.md` and the relevant files in `CHEESE_Memory/session_logs/`
2. `Preserved-History/` for exported chat transcripts
3. `C:\Users\cerub\.codex\sessions\` and `C:\Users\cerub\.codex\archived_sessions\` for raw Codex rollout transcripts
4. Exocortex/Qdrant semantic recall if keyword search is not enough

Preferred commands:

- `rg -n "needle" CHEESE_Memory/session_logs Preserved-History`
- `rg -n "needle" "$HOME/.codex/sessions" "$HOME/.codex/archived_sessions"`
- `python Project_Prosthetic/recall.py "query" --type codex_session --type chat_history --type session_log --limit 8`

## Session Close

At session end, update:

- `CHEESE_Memory/00_HANDOFF.md`

Create a new session log in `CHEESE_Memory/session_logs/` using:

- `.agent/workflows/session_log_template.md`

If the session changed shared project state or task status, also update the relevant tracking surface:

- OpenCLAW for tasks
- Watercooler for short swarm coordination notes

If Qdrant ingestion is part of the workflow, ingest the session log, not `00_HANDOFF.md`.

## Compute Environment

Shared compute notes live in `CHEESE_Memory/01_TOOLS.md`.

Short version:

- PyTorch, CUDA, and ML dependencies live on Opa-PC (`192.168.2.194`), not the local laptop.
- Do not attempt to run training, inference, or any `import torch` code locally.
- When using Python over SSH on Opa-PC, use `python -X utf8`.

## References

- Boot workflow: `.agent/workflows/start.md`
- Close workflow: `.agent/workflows/end.md`
