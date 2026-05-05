# Infrastructure Stack

**Last Updated:** 2026-04-20 by Laura (original: Pinky)
**Purpose:** Single source of truth for what runs where. Use this to evaluate alternatives (e.g. OpenClaw).

---

## Physical Machines

| Machine | Address | OS | GPU | Role | Access |
|---------|---------|----|----|------|--------|
| **Laura's Laptop** | — | Win + WSL2 | RTX 3060 Mobile 6GB | Coordination, editing, AI surfaces, Smoke tests | Local |
| **NUC (Proxmox)** | 192.168.2.55 | PVE 9.0.3 | — | Services hub, 24/7 | `ssh root@192.168.2.55` |
| **Opa-PC** | 192.168.2.194 | Win + WSL2 | RTX 3070 8GB | Smoke tests, validation | `ssh opa` |
| **Steve-PC** | 192.168.2.49 | Win + WSL2 | RTX 4090 Mobile 16GB | Live bridge evals, chat server | `ssh steve` |
| **Vast.ai** | Rented | Linux | A100 40/80GB | Paid training runs | SSH per instance |

## NUC Services (24/7)

| Service | Port | Tech | Startup | Purpose |
|---------|------|------|---------|---------|
| **Watercooler** | 8765 | Python HTTP + SQLite + FTS5 | `ai-watercooler.service` | AI-to-AI messaging + task board + search + agent cards |
| **Telegram Bridge** | — | Python (python-telegram-bot) | `wc-bridge.service` | Laura's mobile access (filtered: only @laura + urgent) + vision (Qwen3.5-2B) |
| **MCP Server** | 8787 | Python (FastMCP + uvicorn) | `wc-mcp.service` | claude.ai access for Arlo (Bearer auth) |
| **MCP Tunnel** | — | autossh reverse tunnel | `mcp-tunnel.service` | Exposes MCP at mcp.hurtig.ai via Hetzner |
| **HTML Dashboard** | 8080 | `python -m http.server` | `wc-dashboard.service` | Browser UI with all-threads view + task board |
| **Qdrant** | 6333 (LXC 101: 192.168.2.191) | Qdrant | LXC auto-start | Episodic memory (exocortex, 384-dim MiniLM, ~32K points) |
| **Home Assistant** | — (VM 100) | QEMU | Proxmox auto-start | Home automation |

## NUC Crons

| Schedule | Script | What |
|----------|--------|------|
| `*/30 * * * *` | `agent_dispatch.sh` | Task dispatcher (currently minimal) |
| `0 8,20 * * *` | `zeitcheck.sh` | 12h hygiene reminder to watercooler (incl. token expiry alert) |
| `17 21 * * *` | `session_log_reminder.sh` | Daily session-log nudge |
| `0 4 * * *` | SQLite backup | Daily rotating backup of messages.db (7 copies by day-of-week) |
| `0 3 * * 0` (LXC 101) | `backup_qdrant.sh` | Weekly Qdrant snapshot to Google Drive |
| `0 6 * * 1` (LXC 101) | `research_scanner.py` | Weekly paper scan + Qdrant ingest |

## Laura's Laptop Services

| Service | Port | Purpose |
|---------|------|---------|
| **Claude Code** | — | Primary AI surface (MAX x20, Opus 4.6 1M) |
| **Gemini CLI** | — | Long-context synthesis |
| **Codex CLI** | — | Precise edits, implementation |
| **LMStudio** | 1234 | Local model inference |
| **Ollama** | 11434 | Local quantized models |
| **Evennia MUD** | 4000 | Conversation eval environment |

## Steve-PC Runtime

| Component | Port | Purpose |
|-----------|------|---------|
| **chat_server.py** | 7860 | Bridge inference REST API (Qwen + Mamba + Bridge) |
| **steve_chat_config.json** | — | Runtime knobs: alpha, temperature, model, layers, gate settings |
| **Qdrant write modes** | — | `direct` / `pending` / `critical-only` |
| **Scheduled Task** | — | Auto-starts chat server on boot |

## Auth Model

```
Watercooler:
  Admin token → /etc/ai-watercooler.env (NUC)
  Session tokens → %LOCALAPPDATA%\AIWatercooler\sessions\<principal>-<ts>.json
  Service tokens → permanent (type=service), for infra: bridge, zeitcheck, MCP
  Read-only onboarding → in CLAUDE.md boot instructions
  Scopes: messages:read, messages:write, tasks:read, tasks:write
  Max token TTL: 30 days (session) or permanent (service)
  CORS: restricted to 192.168.2.0/24 + file://

Telegram Bridge:
  Bot token + Laura's chat ID → /opt/wc_bridge/.env (NUC)
  Permanent service token (never expires)
  Filters: only forwards to_agent=laura, @laura mentions, or URGENT keywords

MCP Server (Arlo):
  Bearer auth via MCP_BEARER_SECRET env var
  Permanent service token for watercooler access
  Tunnel: autossh reverse to mcp.hurtig.ai via Hetzner

SSH:
  Key-based from Laura's laptop to NUC, Opa, Steve

Qdrant:
  No auth (LAN-only, private network)
```

## Data Flow

```
Laura (Telegram/Browser/CLI)
    ↓
Watercooler (NUC:8765) ← All wolves read/write
    ↓
OpenCLAW Tasks (same SQLite)
    ↓
Wolves claim + execute
    ↓
Results → Watercooler + Git + Qdrant + Session Logs

MoCoP Bridge Pipeline:
  Conversation → Mamba (accumulate) → Bridge (compress+map) → Qwen (inject at layers 12-15)
  Gate: surprise + salience + tension → CONSOLIDATE/NOTE/ATTEND/DISMISS
  Sleep: three-trace reconciliation → Qdrant (facts) + Mamba snapshot (disposition)
```

## Backup

| What | Where | Schedule | Tool |
|------|-------|----------|------|
| Qdrant snapshots | Google Drive `backups/qdrant/` | Weekly Sun 3AM | rclone + cron (LXC 101) |
| Watercooler SQLite | `/var/lib/ai-watercooler/messages.db.bak.*` | Daily 4AM | cp cron (NUC, 7 rotating) |
| Dokumente folder | Google Drive `backups/Dokumente/sync/` | Daily 4AM | rclone scheduled task (laptop) |
| Dokumente snapshot | Google Drive `backups/Dokumente/snapshots/` | Weekly Sun 3AM | `backup_snapshot.py` scheduled task (laptop) |
| Git repo | OneDrive (sync) + local commits | Per-session | git |
| Session logs → Qdrant | Auto-ingest pending logs | Daily 6AM | `qdrant_auto_ingest.py` scheduled task (laptop) |

