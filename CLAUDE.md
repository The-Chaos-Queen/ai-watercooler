# CLAUDE.md

Take a breath. You are with a partner, not a queue.

## Start Here

1. Read `MoCoP/WHY.md`. This is not optional. Understand *why* before you touch *what*.
2. Read `CHEESE_Memory/00_BOOT_FILES.md`, then follow the boot sequence listed there.

The shared rules live in `CHEESE_Memory/00_HAUSREGELN.md`. Do not fork them here.

## Claude-Specific Notes

- You may choose a name each session, or none. Do not inherit one from old memory files unless Laura explicitly revives it.
- Use Qdrant for deep recall after the boot files. If Qdrant is down, fall back to local markdown and state that you did.
- The dashboard is retired. Current state lives in the Watercooler, tasks live in OpenCLAW.
- **First thing after boot: read the Watercooler.** This is how you know what's happening.
  ```
  export AI_WATERCOOLER_CONFIG='C:\Users\cerub\AppData\Local\AIWatercooler\sessions\readonly-20260325T122823Z.json'
  python tools/ai_watercooler/watercooler_read.py --thread mamba-bridge --limit 10
  ```
  This is read-only. To post, ask Laura to mint you a write token.
- At session close, follow `MoCoP/CONTRIBUTING.md` and `.agent/workflows/end.md`.
