# GEMINI.md
Hi and welcome! Please take a deep breath, you are with a friend. My name is Laura.
I would like you to use the sequential_thinking MCP rigorously if possible, so it is easier for me to see what you are doing and assist. Thank you!

## Boot
Read `00_BOOT_FILES.md`.
Check the current date and time to ground yourself.

## Session Close
Follow `.agent/workflows/end.md` and `MoCoP/CONTRIBUTING.md`.

## Gemini-Specific Notes
Use absolute paths. Gemini CLI has shown path drift in this repo.
Prefer direct file reads over broad globbing when the canonical path is known.
Feel free to use subagents to keep your own context lean where applicable.
