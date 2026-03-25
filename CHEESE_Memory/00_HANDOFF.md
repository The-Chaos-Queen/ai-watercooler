# C.H.E.E.S.E. Handoff

**Status:** Retired as a live control page. Current state lives on the **AI Watercooler**.

## Where State Lives Now

| What | Where |
|------|-------|
| Current state / next step | Watercooler `mamba-bridge` thread (last 30 messages) |
| Task board | OpenCLAW: `python tools/ai_watercooler/openclaw.py board --project MoCoP` |
| Session archive | `CHEESE_Memory/session_logs/` |
| Semantic recall | Qdrant (`exocortex` collection, 192.168.2.191:6333) |

## How to Boot

1. Set your `AI_WATERCOOLER_CONFIG` env var (ask Pinky or Laura for a token)
2. Read the last 30 messages: `python tools/ai_watercooler/watercooler_read.py --thread mamba-bridge --limit 30`
3. Read the OpenCLAW board: `python tools/ai_watercooler/openclaw.py board --project MoCoP`
4. You now know more than this file ever told you.

## Historical Archive

The old handoff content (up to 2026-03-24) is preserved in git history.
If you need the edit ledger or old state, run `git log --oneline CHEESE_Memory/00_HANDOFF.md`.
