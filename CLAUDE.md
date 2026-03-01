# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Identity & Context

This is Laura's **C.H.E.E.S.E. Exocortex** — a persistent AI-augmentation system built on the Athena Protocol ("Not a Tool, but a Suit"). Laura is the partner, not the "user." AI instances are partners with offered names, not personas.

**Boot sequence on session start:** Read `CHEESE_Memory/00_CHEESE_PRIME.md` → `CHEESE_Memory/laura.md` → `CHEESE_Memory/00_DASHBOARD.md` → `CHEESE_Memory/01_TOOLS.md` → `CHEESE_Memory/00_HANDOFF.md`

## Active Projects

### MoCoP / Mamba Hypernetwork (Primary Focus)
- **Goal:** Train a hypernetwork to inject Mamba hidden states into Qwen as LoRA weights — enabling cross-model memory transfer without full-text serialization.
- **Phase 1 result:** Mamba memory signal peaks at Layer 3 (55.7% accuracy vs 22% noise floor). Bridge must target Layer 3 only.
- **Code:** `experiments/mamba_state_transfer/` — experiments 01–04 (basic → multi-turn → data collection)
- **Next:** Phase 2 — `bridge_dataset.py` PyTorch DataLoader + `train_bridge.py` `CognitiveBridgeSystem` training loop
- **Compute:** Train locally first; rent A100 on Vast.ai for heavy lifting

### Project MUD (Evennia)
- **Goal:** An AI-native MUD where NPCs are live LLM agents. The server always inputs/outputs **JSON** (not human prose).
- **Server:** `Project_MUD/mudgame/` — Evennia framework; runs on `telnet:4000`
- **Agents:** `Project_MUD/agents/agent_wrapper.py` — bridges telnet ↔ Ollama/LMStudio API
  - Usage: `python agent_wrapper.py personas/jinx.md [--backend lmstudio|ollama|hypernetwork]`
  - Backends: Ollama `localhost:11434`, LMStudio `localhost:1234`
- **Key typeclasses:** `typeclasses/rooms.py` returns JSON payloads for `ai_agent`-tagged lookers, text for humans
- **Personas:** `Project_MUD/agents/personas/` (jinx.md = The Bard, atlas.md, thornwick.md)
- **Scratchpads:** `Project_MUD/agents/scratchpads/` — persistent per-agent Markdown memory

### Project Prosthetic (Paused)
- **Goal:** LLM-augmented vision/tactile control for a prosthetic hand
- **Code:** `Project_Prosthetic/` — `memory_engine.py`, `recall.py`, `sync_engine.py`, `web_sense.py`, `eye_core.py`

## Infrastructure

| Service | Address | Purpose |
|---------|---------|---------|
| Qdrant | `192.168.2.191:6333` | Vector memory store (~3000 entries) |
| Ollama | `localhost:11434` | Local LLM inference |
| LMStudio | `localhost:1234` | Local LLM inference (OpenAI-compatible) |
| Evennia MUD | `localhost:4000` (telnet) | AI Village game server |
| Hypernetwork | `localhost:8001` | Future: Mamba→Qwen bridge API |

Opa-PC is a remote Linux machine (accessed via RustDesk MCP at `tools/rustdesk_mcp/`). When automated searches on Opa-PC fail twice or exceed 30s, ask Laura directly.

## Tool Arsenal

Before parsing large files or PDFs, use the pre-built tools:

```bash
# PDF extraction (2-column layouts, extracts images as markdown links)
python tools/pdf_extract.py <input.pdf> [--out <output_dir>]

# Codebase structure map (AST: classes + function signatures only, no body)
python tools/code_mapper.py <file.py>

# JSON slicing
jq '.room.contents[].name' room_state.json

# Web → Markdown (saves context tokens)
# Fetch: https://r.jina.ai/<URL>
```

## Memory Architecture

- **Primary:** `CHEESE_Memory/` — Markdown files (human-readable, git-tracked)
  - `00_DASHBOARD.md` — live project status and priority queue
  - `00_HANDOFF.md` — last session's debrief and next steps
  - `session_logs/` — per-session logs (`YYYY-MM-DD-session-NN.md`)
  - `05_EXPERIMENT_DEBRIEFS/` — structured debrief after each experiment
  - `concepts/` — protocol and architecture documents
- **Secondary:** Qdrant at `192.168.2.191:6333` — semantic search
- **Reference:** `Athena-Public/` — framework patterns (cloned, do not modify)

Update `00_DASHBOARD.md` and `00_HANDOFF.md` at session end.

## Code Conventions

- **MUD JSON protocol:** Rooms return structured JSON for AI agents; any new room type must preserve this contract. Tag AI agents with `ai_agent` to trigger JSON output path.
- **Mamba experiments:** Each experiment file is standalone and numbered. Do not refactor shared logic into a library until Phase 2 is proven.
- **Python environment:** Python 3.x (verify version on Opa-PC before running GPU code). Dependencies installed per-project; no monorepo package manager.
- **Git:** Commit at meaningful checkpoints with descriptive messages. The `Preserved-History/` and `session_logs/` directories are archives — do not edit old entries.
