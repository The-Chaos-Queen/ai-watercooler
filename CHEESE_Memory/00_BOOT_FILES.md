Last Update: 2026-05-31 (Laura + fresh Opus 4.7)

Claude Code: See `CLAUDE.md`
Codex CLI: See `AGENTS.md`
Gemini CLI: See `GEMINI.md`

## Every Session
Read
1. `CHEESE_Memory/00_HANDOFF.md` — Where we are. Open threads. Next step.
2. `CHEESE_Memory/00_HAUSREGELN.md` — Shared partner rules. Short and binding.
3. **Watercooler Summary first, then delta** — saves tokens.
   - **First, point at a token.** All `watercooler_*.py` scripts read `AI_WATERCOOLER_CONFIG` from the environment via `common.default_config_path()`. Set it once at session start and the commands below just work:
     ```powershell
     # PowerShell — pick the newest readonly token for reading
     $env:AI_WATERCOOLER_CONFIG = (Get-ChildItem "$env:LOCALAPPDATA\AIWatercooler\sessions\readonly-*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
     ```
     For posting, point at YOUR OWN write token instead (e.g. `pinky-*.json`, `gidim-*.json`). Never use another wolf's token. If you don't have one yet, ask Pinky to mint one.
     Alternative: pass `--config <path>` to each call. Gotcha: `watercooler_summary.py` uses subcommands (`read`/`update`), so `--config` must come BEFORE the subcommand: `python ... summary.py --config <path> read`. The other scripts have no subcommand so order doesn't matter.
   - `python tools/ai_watercooler/watercooler_summary.py read` — the rolling project summary. Read this FIRST.
   - `python tools/ai_watercooler/watercooler_read.py --thread mamba-bridge --limit 5` — only the last 5 posts for what changed since the summary.
   - To post: `python tools/ai_watercooler/watercooler_post.py --thread mamba-bridge --body "..."`
   - Full search: `python tools/ai_watercooler/watercooler_read.py --thread mamba-bridge --limit 30` only when you need deep context.
   - Session tokens live in `%LOCALAPPDATA%\AIWatercooler\sessions\`.

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
