# Welcome Package

**Status:** Canonical boot map for all AI surfaces.
**Last Updated:** 2026-04-05

## Lean Boot (Every Session)

Read these three things. Nothing else is required at startup.

1. `CHEESE_Memory/00_HANDOFF.md` — Where we are. Open threads. Next step.
2. `CHEESE_Memory/00_HAUSREGELN.md` — Shared partner rules. Short and binding.
3. **Watercooler** — last 10 messages from `mamba-bridge` thread.

Then greet Laura briefly with the current date/time and start working.

## On-Demand Reference

Read these **when your task touches them**, not at boot:

| When... | Read... |
|---------|---------|
| Task is about MoCoP | `MoCoP/README.md` (file map) then the specific doc you need |
| Need the experiment ladder | `MoCoP/EXPERIMENT_LADDER.md` |
| Need the motivation/vision | `MoCoP/WHY.md` |
| Need infrastructure details | `CHEESE_Memory/01_TOOLS.md` |
| Need Laura's personality/preferences | `CHEESE_Memory/laura.md` |
| Need recent git activity | `tools/ambient/state.md` (last 5 entries) |
| Need session close procedure | `MoCoP/CONTRIBUTING.md` + `.agent/workflows/end.md` |
| Referencing an older chat | Search `CHEESE_Memory/session_logs/`, `Preserved-History/`, local session archives |

## Why This Is Lean

The old boot loaded 9-10 files (~18k tokens) before any work started. Most of that was reference material that only matters when the task touches it. WHY.md is beautiful but a wolf on its 50th session doesn't need to re-read the motivation to fix a bug.

The lean boot loads ~3.5k tokens. Everything else is a `Read` call away.

## Surface Notes

- **Claude Code:** See `CLAUDE.md` for Claude-specific notes.
- **Codex CLI:** See `AGENTS.md` for Codex-specific notes.
- **Gemini CLI:** See `GEMINI.md` for Gemini-specific notes.

## Where Truth Lives

- **Current state / next step:** `CHEESE_Memory/00_HANDOFF.md`
- **Session archive:** `CHEESE_Memory/session_logs/`
- **Task tracker:** OpenCLAW
- **Fast coordination:** Watercooler (`mamba-bridge` thread)
- **MoCoP file map:** `MoCoP/README.md`
- **MoCoP research status:** `MoCoP/EXPERIMENT_LADDER.md`
