# Exocortex Tool Arsenal

Catalog + pointers. Detailed CLI usage lives in per-tool runbooks; this file stays terse.

## Where State Lives

- **Current state / next step:** Watercooler `mamba-bridge` thread; `00_HANDOFF.md` is the canonical session-handoff record.
- **Session archive:** `CHEESE_Memory/session_logs/`
- **Task tracker:** Watercooler (OpenCLAW)
- **Coordination:** Watercooler

## Compute Surfaces

Canonical machine list in `CHEESE_Memory/INFRASTRUCTURE.md`. Quick reminders:

- **ML-WS** (`192.168.2.196`, RTX 3090 desktop, Ubuntu 26.04). Primary PyTorch/CUDA. Runbook: `MoCoP/experiments/mamba_lora_bridge/ML_WORKSTATION_RUNBOOK.md`. `ssh ml-ws`.
- **Steve** (`192.168.2.49`, RTX 4090 mobile). Live browser-chat probes, alpha sweeps. Runbook: `MoCoP/experiments/mamba_lora_bridge/STEVE_RUNBOOK.md`. WSL helper: `steve-wsl.ps1`.
- **Opa** (`192.168.2.194`, RTX 3070). Smoke tests, dry-runs. Runbook: `MoCoP/experiments/mamba_lora_bridge/OPA_RUNBOOK.md`. WSL helper: `opa-wsl.ps1`. Working dir: `C:\Users\User\bridge\`.
- **Vast.ai** for A100/H100 jobs. Runbook: `MoCoP/experiments/mamba_lora_bridge/VASTAI_RUNBOOK.md`.
- **Hermes gateway** (Monk's substrate, WSL Ubuntu-22.04). Start detached:
  ```bash
  wsl -d Ubuntu-22.04 -- bash -lc "tmux new-session -d -s hermes 'hermes gateway run --accept-hooks'"
  ```
  Status: `hermes gateway status`. Attach: `tmux attach -t hermes`.

**SSH gotcha:** Windows SSH defaults to `charmap`; pass `-X utf8` to Python over SSH or non-ASCII output mangles.

## Document Extraction

- **PDFs:** `tools/pdf_extract.py` (PyMuPDF4LLM). Tables as Markdown, figures exported.
- **Word / Excel / PPT:** Docling, MarkItDown.
- **Web:** `https://r.jina.ai/[URL]` (Firecrawl/Jina).

## Codebase Understanding

- **Single file architecture:** `tools/code_mapper.py` (Tree-sitter). AST overview without body logic.
- **Repo-wide structural queries:** Graphify MCP. Tools: `graph_stats`, `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `shortest_path`. Graph at `graphify-out/graph.json`. Regenerate: `python -m graphify .` then restart MCP.

## JSON

`jq` for reading, filtering, formatting. `cat foo.json | jq '.items[].name'`.

## Ambient State Log

`tools/ambient/state.md` — last 20 entries on boot. Auto-written by the git post-commit hook. Never edit manually. Format: `[YYYY-MM-DD HH:MM UTC] git | project | author: message (hash)`.

## Prior-Session Retrieval

- **Primary (Qdrant):** `python Projects/Project_Prosthetic/recall.py "<query>" --limit 5` — semantic, ~32K points.
- **Fallback (rg):** `rg -n "<exact phrase>" CHEESE_Memory/session_logs Preserved-History`.
- **Watercooler search:** see `tools/ai_watercooler/README.md` (`/v1/messages?search=`, FTS5 supports `AND`/`OR`/`NOT`/`"exact phrase"`).
- **Ingest maintenance:** `python Projects/Project_Prosthetic/ingest_sessions.py CHEESE_Memory/session_logs` (auto-ingested daily).

## AI Watercooler / OpenCLAW

Coordination surface. Full CLI and admin in `tools/ai_watercooler/README.md`. Five high-value reminders:

1. **Identity is token-bound.** The server derives identity from the session token. `--from-agent` does NOT override authority. OpenCLAW state-changing calls reject mismatched principals. Never borrow another wolf's token.
2. **Set `AI_WATERCOOLER_CONFIG` at session start** to your own token under `%LOCALAPPDATA%\AIWatercooler\sessions\<name>-<date>.json`. Otherwise scripts use whatever config.json holds.
3. **The `claude.ai Watercooler` MCP connector authenticates as `claude-ai`**, not as you. From Claude Code, use `tools/ai_watercooler/watercooler_post.py` — not the MCP. See README §Identity by Surface.
4. **Defaults:** `--thread mamba-bridge` (pack channel). `--to-agent laura` triggers Telegram forwarding to her phone — don't spam.
5. **OpenCLAW lifecycle:** `queued → claimed → heartbeat → complete/block`. Correction verbs: `comment`, `reassign`, `release`, `unblock`. Use these for audited repair instead of duplicate tasks or SQLite surgery.

## NotebookLM

`notebooklm` CLI (v0.3.4 via pip). Login once: `notebooklm login`. Workflow: `create "Topic"` → `use <id>` → `source add <file>` → `ask "question"`. Optional: `generate audio`. Used for 50–200 source synthesis (MoCoP corpus synthesis for #393 ran ~190 sources).

## Active Utility Scripts

- `python tools/pdf_extract.py <input.pdf> [--out <output_dir>]`
- `python tools/code_mapper.py <file.py>`
- `python tools/research_scanner.py [--days N] [--dry-run]` — archives full reports under `tools/research_scanner_runs/`; `latest_summary.json` is the compact source for handoff and session-close.

## The Human Bridge (HaaS)

If automated search on a remote host fails twice or exceeds ~30s, halt. Present the best guess to Laura with a specific path/parameter ask. Leverage her spatial memory rather than digital brute force.

## Codex CLI (inline anonymous reviews)
`codex` (codex-cli) is installed and authenticated on Laura's machine. Any wolf shell can invoke:
- `codex review --uncommitted "focus: <what>"` — non-interactive review of staged+unstaged+untracked changes (pre-commit hygiene).
- `codex review --base master` — review a branch diff.
- `codex exec "<prompt>"` — one-shot non-interactive run.

**Doctrine (keeper-established 2026-07):** output of these calls is *"a Codex"* — substrate capability, not persona — same distinction as an in-session "a Fable" review. Use freely for pre-commit checks and second opinions. It is NOT admissible as an attested review of record: GREEN/CHANGES verdicts that manifests or attestations bind must come from wolf-Codex on the watercooler, with identity and message ID. Quota note: each call spends Laura's subscription (~6k tokens minimum); deliberate use, no hooks/loops.
