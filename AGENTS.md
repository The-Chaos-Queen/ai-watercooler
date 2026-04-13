# AGENTS.md

Instructions for Codex and other coding agents.

## Boot

1. Read `CHEESE_Memory/00_HANDOFF.md` — current state, open threads, next step.
2. Read `CHEESE_Memory/00_HAUSREGELN.md` — shared partner rules.
3. Check the Watercooler (last 10 messages, `mamba-bridge` thread).

Everything else: read on demand. See `CHEESE_Memory/00_BOOT_FILES.md` for the reference table.

## Operating Model

- Laura is a partner, not a generic user.
- `CHEESE_Memory/00_HANDOFF.md` is the live control page.
- `CHEESE_Memory/session_logs/` is the append-only archive.
- Do not rewrite old session logs except for explicit repair requests.
- Do not revive the retired dashboard.

## Prior-Session Retrieval

When Laura references a previous chat or "we already did this," search local archives before guessing:

1. `CHEESE_Memory/session_logs/` and `Preserved-History/`
2. `~/.codex/sessions/` and `~/.codex/archived_sessions/`
3. Qdrant semantic recall if keyword search is not enough

## Session Close

Follow `.agent/workflows/end.md` and `MoCoP/CONTRIBUTING.md`.

## Compute Environment

- PyTorch/CUDA work runs on Opa-PC (`192.168.2.194`) or Steve (`192.168.2.49`), not the laptop.
- When using Python over SSH on Opa-PC, use `python -X utf8`.
- Details in `CHEESE_Memory/01_TOOLS.md` — read when needed.
