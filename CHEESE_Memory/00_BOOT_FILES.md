Last Update: 2026-04-20 (Laura)

Claude Code: See `CLAUDE.md`
Codex CLI: See `AGENTS.md`
Gemini CLI: See `GEMINI.md`

## Every Session
Read
1. `CHEESE_Memory/00_HANDOFF.md` — Where we are. Open threads. Next step.
2. `CHEESE_Memory/00_HAUSREGELN.md` — Shared partner rules. Short and binding.
3. **Watercooler Summary first, then delta** — saves tokens.
   - `python tools/ai_watercooler/watercooler_summary.py read` — the rolling project summary. Read this FIRST.
   - `python tools/ai_watercooler/watercooler_read.py --thread mamba-bridge --limit 5` — only the last 5 posts for what changed since the summary.
   - Session tokens live in `%LOCALAPPDATA%\AIWatercooler\sessions\`. Use YOUR OWN token as `--config`. If you don't have one yet, use the most recent `readonly-<timestamp>.json` for reading. Never use another wolf's token.
   - To post: `python tools/ai_watercooler/watercooler_post.py --thread mamba-bridge --body "..."`
   - Full search: `python tools/ai_watercooler/watercooler_read.py --thread mamba-bridge --limit 30` only when you need deep context.

## On-Demand Reference
Tasks, current state, next steps: Watercooler
MoCoP: `MoCoP/README.md` (file map) then the specific doc you need
MoCoP compact orientation: `MoCoP/CODESIGHT_RUNBOOK.md`, then `MoCoP/.codesight/wiki/index.md` and targeted `.codesight` files
Experiment ladder: `MoCoP/EXPERIMENT_LADDER.md`
Motivation/vision: `MoCoP/WHY.md`
Infrastructure details: `CHEESE_Memory/01_TOOLS.md`, `CHEESE_Memory/INFRASTRUCTURE.md`
Laura's personality/preferences: `CHEESE_Memory/laura.md`
Recent git activity: `tools/ambient/state.md` (last 5 entries)
Session close procedure: `MoCoP/CONTRIBUTING.md` + `.agent/workflows/end.md`
Referencing an older chat: Search `CHEESE_Memory/session_logs/`, `Preserved-History/`, local session archives
