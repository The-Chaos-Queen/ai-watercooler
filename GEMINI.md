# GEMINI.md

## Boot

1. Read `C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory\00_HANDOFF.md`
2. Read `C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory\00_HAUSREGELN.md`
3. Check the Watercooler (last 10 messages, `mamba-bridge` thread)
4. Greet briefly with current date/time and active focus from the handoff

Everything else: read on demand when the task requires it. See `00_BOOT_FILES.md` for the reference table.

## Gemini-Specific Notes

- Use absolute paths. Gemini CLI has shown path drift in this repo.
- Prefer direct file reads over broad globbing when the canonical path is known.
- The dashboard is retired. Do not treat `00_DASHBOARD.md` or dashboard tooling as live state.
- If Laura references an older chat, search `CHEESE_Memory/session_logs/` and `Preserved-History/` before answering from memory.
- Infrastructure details (Opa, Steve, Qdrant) live in `CHEESE_Memory/01_TOOLS.md` — read when needed.
