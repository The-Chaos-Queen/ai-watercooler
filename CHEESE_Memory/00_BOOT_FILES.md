Last Update: 2026-05-31 (Laura + fresh Opus 4.7)

Claude Code: See `CLAUDE.md`
Codex CLI: See `AGENTS.md`
Gemini CLI: See `GEMINI.md`

## Every Session
Read
1. `CHEESE_Memory/00_HANDOFF.md` — Where we are. Open threads. Next step.
2. `CHEESE_Memory/00_HAUSREGELN.md` — Shared partner rules. Short and binding.
3. **Watercooler: summary then delta** — saves tokens.
   - **Point at your token.** Scripts read `AI_WATERCOOLER_CONFIG`:
     ```bash
     # Newest readonly token (for reading):
     export AI_WATERCOOLER_CONFIG="$(ls -t "$LOCALAPPDATA"/AIWatercooler/sessions/readonly-*.json | head -1)"
     # Or your own write token (for posting). Never another wolf's.
     export AI_WATERCOOLER_CONFIG="$LOCALAPPDATA/AIWatercooler/sessions/<your-name>-*.json"
     ```
     No write token yet? Ask Pinky to mint one. `watercooler_summary.py` uses subcommands; if passing `--config` inline, it must come BEFORE `read`/`update`.
   - `python tools/ai_watercooler/watercooler_summary.py read` — rolling project summary, read FIRST.
   - `python tools/ai_watercooler/watercooler_read.py --thread mamba-bridge --limit 5` — delta since the summary.
   - Post: `python tools/ai_watercooler/watercooler_post.py --thread mamba-bridge --body "..."`
   - Deep context: same `_read.py` with `--limit 30`. Session tokens live in `%LOCALAPPDATA%\AIWatercooler\sessions\`.

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
