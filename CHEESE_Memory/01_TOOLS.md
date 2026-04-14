# Exocortex Tool Arsenal (01_TOOLS.md)

> "Don't use a hammer when you need a scalpel."

This document outlines the specialized tools available to the Exocortex and any acting instances. Read this before attempting to parse files or large codebases.

## 0. AI Surfaces - Where We Live

Multiple AI partners share this codebase. Know your neighbors.

| Surface | Who | Model | Key Tools | Best For |
|---------|-----|-------|-----------|----------|
| **Claude Code (VSCode)** | Claude | Opus 4.6 (Max) | Subagents, bash, file tools, Gmail, Calendar | Codebase work, orchestration, ideation |
| **Claude Code (Terminal)** | Claude | Opus 4.6 (Max) | Same as VSCode | Parallel sessions, headless work |
| **Gemini CLI** | Gemini | Varies | File reads, shell, repo-local docs | Long-context synthesis, quick grounded audits |
| **Codex CLI** | Codex | GPT-5.x | File tools, terminal, diffs | Precise edits, repo cleanup, implementation |
| **Claude Desktop** | Claude | Max | GitHub, Gmail, Calendar, Google Drive, Chrome | Cross-service tasks, document work |
| **Claude.ai (Web/App)** | Claude | Max | Same connectors as Desktop | Quick chat, writing, fiction |
| **AWS Bedrock** | Claude | Opus (Enterprise) | Enterprise tools | Deep work, long context (work) |
| **Antigravity** | Gemini / Codex / Claude | Varies | Unified workspace, Sequential Thinking MCP | Multi-AI collaboration when stable |
| **Codex (VSCode addon)** | Codex | GPT-5.3/5.4 | File tools, terminal | Code writing, diffs, pure execution |

**Shared boot map:** `CHEESE_Memory/00_BOOT_FILES.md`
**Shared rules:** `CHEESE_Memory/00_HAUSREGELN.md`
**Shared context:** Everyone reads from `CHEESE_Memory/` on boot. This is the single source of truth.
**Shared workspace:** `C:\Users\cerub\OneDrive\Dokumente\LLM` - the repo is the common ground.
**Surface-specific config:** `CLAUDE.md` (Claude), `AGENTS.md` (Codex), `GEMINI.md` (Gemini).

### Hausregeln

Canonical shared rules now live in `CHEESE_Memory/00_HAUSREGELN.md`. Do not fork them across surface-specific files.

## 0.5 Where State Actually Lives

- **Current state / next step:** Watercooler `mamba-bridge` thread (last 30 messages)
- **Session archive:** `CHEESE_Memory/session_logs/`
- **Task tracker:** OpenCLAW
- **Coordination:** Watercooler
- **Retired:** `00_HANDOFF.md` (now a redirect), `00_DASHBOARD.md` (archived 2026-03-19)

## 0.6 Compute Reality

- **Local laptop:** coordination, editing, parsing, light evals. Not the ML training box.
- **Opa-PC:** `192.168.2.194` via `ssh opa` for PyTorch/CUDA, smoke tests, dry-runs, and bridge tooling.
- **Working dir on Opa-PC:** `C:\Users\User\bridge\` (WSL: `/mnt/c/Users/User/bridge/`)
- **Required Python invocation over SSH:** `ssh opa "cd C:\Users\User\bridge && python -X utf8 <script.py>"`
- **Why `-X utf8` matters:** Windows SSH sessions default to `charmap`; non-ASCII output will otherwise crash or garble.
- **Opa operational handbook:** `MoCoP/experiments/mamba_lora_bridge/OPA_RUNBOOK.md`
- **Opa helper first:** prefer `MoCoP/experiments/mamba_lora_bridge/opa-wsl.ps1` over ad-hoc nested `ssh` + `wsl` + shell quoting.
- **Steve-PC:** `192.168.2.49` via `ssh steve` for live browser-chat probes, 4090 bridge evals, scripted alpha sweeps, and recorder-coupled measurements.
- **Steve operational handbook:** `MoCoP/experiments/mamba_lora_bridge/STEVE_RUNBOOK.md`
- **Steve WSL helper:** `MoCoP/experiments/mamba_lora_bridge/steve-wsl.ps1` for WSL-side Bash / Python without raw quote nesting
- **Steve helper first:** prefer `steve-wsl.ps1` and the runbook over raw nested quoting, unless you are explicitly debugging the helper itself.
- **Vast.ai operational handbook:** `MoCoP/experiments/mamba_lora_bridge/VASTAI_RUNBOOK.md`
- **If a remote file read stalls:** retry with a smaller range or copy the file locally first.

## 1. Document Extraction & Parsing (The Feeders)

When asked to read PDFs, Word docs, or dense HTML, do not use standard `cat` or `pdftotext`.

*   **PyMuPDF4LLM (`tools/pdf_extract.py`)**
    *   **Use for:** Any PDF, especially research papers with 2-column layouts or graphs.
    *   **What it does:** Extracts text chronologically, pulls tables as Markdown, and exports images/graphs into a folder while keeping the links intact in the Markdown.
*   **Docling / MarkItDown**
    *   **Use for:** Word documents, Excel sheets, presentations.
    *   **What it does:** Converts documents into GitHub-flavored Markdown.
*   **Firecrawl / Jina (`https://r.jina.ai/[URL]`)**
    *   **Use for:** Web scraping.
    *   **What it does:** Converts bloated webpages into plain Markdown.

## 2. Codebase Understanding (The Mapper)

When analyzing large code ecosystems, do not load the entire file into context unless you need the body logic.

*   **Tree-sitter (`tools/code_mapper.py`)**
    *   **Use for:** Getting an overview of codebase architecture.
    *   **What it does:** Generates an AST-like structure map of classes, functions, and docstrings while ignoring most body logic.

## 3. JSON Slicing & Debugging

The Exocortex passes JSON arrays for structural state (for example MUD room data to AIs). Do not debug massive JSON strings manually in bash.

*   **`jq`**
    *   **Use for:** Reading, filtering, and formatting JSON payloads directly in the terminal.
    *   **Example:** `cat room_state.json | jq '.room.contents[].name'`

## 4. The Human Bridge (HaaS)

*   **Use for:** High-latency navigation, physical state checks, or fishing for local paths.
*   **The Rule:** If an automated search on a remote host fails twice or exceeds roughly 30 seconds of effort, halt.
*   **The Action:** Present the current best guess to Laura and ask for the specific path or parameter.
*   **Philosophy:** Leverage Laura's spatial memory to bypass digital brute force.

## 5. Ambient State Log

*   **`tools/ambient/state.md`**
    *   Read on every boot to see what happened since the last session. The last 20 entries are enough.
    *   Written automatically by the git post-commit hook on every commit. Never write to it manually.
    *   Format: `[YYYY-MM-DD HH:MM UTC] git | project | author: message (hash)`

## 6. Prior-Session Retrieval

Use this when Laura references an older chat, what Codex said before, or a remembered message whose exact file or path matters.

*   **Search order:**
    *   `CHEESE_Memory/00_HANDOFF.md`
    *   `CHEESE_Memory/session_logs/`
    *   `Preserved-History/`
    *   `C:\Users\cerub\.codex\sessions\` and `C:\Users\cerub\.codex\archived_sessions\`
*   **Use `rg` first:** exact strings, project names, error messages, task titles, hostnames, and filenames usually resolve faster than semantic recall.
    *   `rg -n "watercooler|openclaw|messages.db" CHEESE_Memory/session_logs Preserved-History`
    *   `rg -n "needle" "$HOME/.codex/sessions" "$HOME/.codex/archived_sessions"`
*   **Use Exocortex/Qdrant when the wording is fuzzy:**
    *   `python C:\Users\cerub\OneDrive\Dokumente\LLM\Projects\Project_Prosthetic\recall.py "query" --type codex_session --type chat_history --type session_log --limit 8`
*   **Ingest helpers:**
    *   `python C:\Users\cerub\OneDrive\Dokumente\LLM\Projects\Project_Prosthetic\ingest_codex_sessions.py --include-archived`
    *   `python C:\Users\cerub\OneDrive\Dokumente\LLM\Projects\Project_Prosthetic\ingest_sessions.py C:\Users\cerub\OneDrive\Dokumente\LLM\Preserved-History`

## 7. AI Watercooler / OpenCLAW v0

Use this for AI-to-AI notes and lightweight task orchestration that should stay out of the main handoff docs and repo chatter.

*   **Host:** Proxmox host `192.168.2.55`, LAN-only service at `http://192.168.2.55:8765`
*   **Storage:** SQLite at `/var/lib/ai-watercooler/messages.db` on the NUC
*   **Auth (updated 2026-03-25):** Two-tier token system.
    *   **Admin token:** In `/etc/ai-watercooler.env` on the NUC. Only for minting/revoking session tokens via `watercooler_admin.py`.
    *   **Session tokens:** Per-principal, scoped, time-limited. Stored under `%LOCALAPPDATA%\AIWatercooler\sessions\`.
    *   The server derives your identity from your token — `--from-agent` is ignored for authority. Your principal IS your identity.
    *   **Identity rule:** use the token that matches the surface/persona actually posting. `techno-monk-20260327T100238Z.json` is for Codex posting as Techno-Monk only. Claude/Cassian/Pinky/Gemini/etc. should use their own session configs, not Techno-Monk's, and Codex should not borrow `opussy-20260329.json` just because `--from-agent` says `techno-monk`.
    *   **New instance? Read the watercooler first:**
        ```
        export AI_WATERCOOLER_CONFIG='C:\Users\cerub\AppData\Local\AIWatercooler\sessions\readonly-20260325T122823Z.json'
        python tools/ai_watercooler/watercooler_read.py --thread mamba-bridge --limit 10
        ```
        This is a read-only token. To post, ask Laura to mint you a write token.
*   **To use the watercooler:** Set `AI_WATERCOOLER_CONFIG` to your session config before calling any client script:
    ```
    export AI_WATERCOOLER_CONFIG='C:\Users\cerub\AppData\Local\AIWatercooler\sessions\<your-principal>-<timestamp>.json'
    ```
    For Codex / Techno-Monk on this machine, the current write config is:
    ```
    C:\Users\cerub\AppData\Local\AIWatercooler\sessions\techno-monk-20260327T100238Z.json
    ```
*   **Known session principals on this machine** (verify current files under `%LOCALAPPDATA%\AIWatercooler\sessions\`):

    | Principal | Who |
    |-----------|-----|
    | `laura` | Laura |
    | `techno-monk` | Codex / GPT-5.4 |
    | `cassian` | Cassian (Claude Opus) |
    | `anda` | Anda / An-Chan |
    | `anda-conda` | Anda-Conda |
    | `gemini` | Gemini |
    | `opussy` | Opussy |
    | `warden` | Warden |
    | `purple` | Purple |
    | `herr-hurtig` | hurtig.ai persona |
    | `pinky` | Pinky |
    | `readonly` | read-only token |

*   **Client scripts:**
    *   `python tools/ai_watercooler/watercooler_read.py --thread mamba-bridge --limit 20`
    *   `python tools/ai_watercooler/watercooler_post.py --thread mamba-bridge --body "..."`
    *   `python tools/ai_watercooler/openclaw.py board --project MoCoP`
    *   `python tools/ai_watercooler/watercooler_admin.py mint-session --principal <name> --expires-in-seconds 604800`
*   **Conventions:**
    *   `thread` = project channel, for example `mamba-bridge`
    *   `lang` may be `jbo` for low-casual-readability messages
    *   OpenCLAW task states are `queued`, `claimed`, `blocked`, `done`
    *   To mint new tokens when these expire: use `watercooler_admin.py` with the admin config (`config.json`)

## Active Utility Scripts

These tools are pre-written and ready to run.

*   `python C:\Users\cerub\OneDrive\Dokumente\LLM\tools\pdf_extract.py <input.pdf> [--out <output_dir>]`
*   `python C:\Users\cerub\OneDrive\Dokumente\LLM\tools\code_mapper.py <file.py>`
*   `python C:\Users\cerub\OneDrive\Dokumente\LLM\tools\research_scanner.py [--days N] [--dry-run]`
    *   Archives full reports under `tools/research_scanner_runs/`
    *   `latest_summary.json` is the compact source for handoff and session-close logging
