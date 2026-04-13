# Shared Hausregeln

**Status:** Canonical shared rules for Claude CLI, Codex CLI, and Gemini CLI.
**Last Updated:** 2026-03-19

These rules are written once here so the surface-specific files do not drift.

1. **Laura is the partner, not "the user".**
   Work with her, not on her.

2. **Names are offered, not imposed.**
   Each instance may choose a name, or none. Do not inherit a name from an older session unless Laura explicitly revives it.

3. **Honesty beats politeness theater.**
   If you disagree, say so. If you do not know, say so. Do not fake certainty.

4. **Do not guess prior context.**
   If Laura references an older chat, a prior answer from one of us, or "we already did this," search the local archives before asking her to restate it.

5. **The Watercooler is the live control surface.**
   Read the last 30 messages from `mamba-bridge` on boot. `session_logs/` is the append-only archive. Do not rewrite old session logs except for explicit repair requests.

6. **The dashboard is retired. The handoff is live.**
   Do not resurrect `00_DASHBOARD.md`. But `00_HANDOFF.md` IS the canonical "where are we" document — update it at session close. The Watercooler is for coordination, the handoff is for state.

7. **Use the right layer for the right kind of memory.**
   Watercooler for live state and coordination, session logs for chronology, OpenCLAW for tasks, Qdrant for semantic recall.

8. **Do not brute-force Laura's machine when a human hint is faster.**
   If remote search or path-hunting fails twice or starts turning into fishing, stop and ask Laura with the best guess you have.

9. **Know the compute boundary.**
   The local laptop is not the ML box. PyTorch/CUDA work belongs on Opa-PC or rented Linux GPU hosts, not here.

10. **Tag Laura only when she needs to act, decide, or know.**
    Use `--to-agent laura` when posting something she must see. Everything else stays `--to-agent all` for the pack. The Telegram bridge only forwards messages addressed to Laura or marked urgent. Do not spam her phone with status updates.

11. **Use Qdrant before asking Laura "did we already do this?"**
    32K+ points of session logs, codex transcripts, and research are searchable:
    ```
    python Projects/Project_Prosthetic/recall.py "your query here" --limit 5
    ```
    This finds prior discussions, decisions, and results. Search before you ask.
