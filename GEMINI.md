# GEMINI.md

Use the shared welcome package first. Gemini CLI has already shown path drift in this repo, so the canonical boot entrypoint is given as an absolute path.

## Boot

1. Read `C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory\00_BOOT_FILES.md`
2. Follow the shared boot list there
3. If the task is MoCoP-related, also read the MoCoP add-ons listed there in the documented order
4. Greet briefly with the current date/time and the active focus from `C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory\00_HANDOFF.md`

## Gemini-Specific Notes

- Prefer direct file reads over broad globbing when the canonical path is already known.
- The dashboard is retired. Do not treat `00_DASHBOARD.md`, `dashboard_manager.py`, or `dashboard_data.json` as the live state source.
- If Laura references an older chat or prior Gemini answer, search `CHEESE_Memory/session_logs/`, `Preserved-History/`, and any local Gemini export history before answering from memory.
- Shared infrastructure, Watercooler, OpenCLAW, Qdrant, and Opa-PC usage all live in `C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory\01_TOOLS.md`.
