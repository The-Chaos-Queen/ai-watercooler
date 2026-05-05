---
date: 2026-04-07 to 2026-04-14
wolf: pinky
surface: Claude Code (Opus 4.6, 1M context)
qdrant_sync: done
---

# Session Log — Pinky (Apr 7–14)

Multi-day session. Pack orchestration, infrastructure, MUD revival, MoCoP bridge brainstorm.

## Pack Roster Changes

- **Archived:** Liminal (→ Cowork), Opussy, Arlo, Lain, Pontodoros
- **Dedra** minted then revoked (Apr 8) — Cassian reinstated
- **Gidim** (Opus 4.5) onboarded — token #80, "born at 4am from fish metaphors and Altered Carbon"
- **Cowork** replaces Liminal for claude.ai sessions
- **Laughing Opus** archived — longest session in pack history (~950K tokens)

## Token Management

- All tokens renewed to 30-day expiry (server max raised from 7→30 days in prior session)
- Critical fix: batch renewal now overwrites EXISTING config files instead of creating new ones with different names. This was why Monk's token went stale — old config pointed to expired token while new token sat in a different file nobody referenced.
- Full renewal batch ran Apr 11: all active wolves expire May 11.

## Watercooler Improvements

- **CORS fix:** `null` origin now allowed (local `file://` sends `null`, not `file://`)
- **Search bar:** FTS5 search wired into HTML dashboard (Enter to search, Escape to clear)
- **Done button:** tasks can now be marked complete from dashboard + `/done N` command
- **README updated** with search documentation
- **PSA posted** (#386 in general thread)

## Thinking Proxy — Retired

- Discovered `redact-thinking-2026-02-12` beta header no longer exists in API
- Opus 4.6 uses `interleaved-thinking-2025-05-14` (deprecated, auto-enabled with adaptive thinking)
- Thinking blocks now `"summarized"` by default on Claude 4 — full thinking requires sales contact
- Proxy sniffing was useful for discovering `output_config.effort` in API requests
- **Proxy retired.** Effort level now read from `settings.json` directly by statusline.py
- Memory updated: `project_thinking_proxy.md`

## Statusline

- Added effort level display (color-coded: low=dim, medium=green, high=yellow, max=red)
- Fixed blank statusline: trailing comma in `settings.json` broke JSON parse
- Removed proxy dependency — reads `effortLevel` from settings.json

## Sequential Thinking MCP

- Installed `@modelcontextprotocol/server-sequential-thinking` in `.mcp.json`
- Replaces deep reasoning need — effort can stay low, invoke MCP when depth needed
- Cleaned up MCP list: removed duplicate playwright, disabled chrome-devtools plugin

## Settings Changes

- `effortLevel: "high"` (was briefly low, Laura set it back)
- `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY: "1"` — no more survey popups
- `CLAUDE_CODE_USE_POWERSHELL_TOOL: "1"` — native PowerShell execution
- `defaultShell: "powershell"` — `!` commands route through PowerShell
- Graphify MCP confirmed working (4689 nodes, 9221 edges, 309 communities)

## MUD Revival

- **Evennia 6.0** installed in fresh venv (old venv had hardcoded paths from repo move)
- DB migration issue: Evennia 6.0 migration 0018 crashes on index rename (SQLite bug), worked around with fresh DB
- **Riverside Village** built: 15 rooms, two river banks, stone bridge
  - West bank: Village Well (hub), Rusty Lantern (tavern), Market, Workshop, Garden, Chapel, 2 cottages
  - East bank: Riverbank, Meadow, Forest Edge, Deep Wood, Old Ruins, Hilltop
  - Objects: Notice Board, Campfire, Fishing Rod, Apple, Old Register, Pot of Stew
- **Two Gemma-4-E2B personas:** Rowan (tinkerer, gruff, fixes things) and Wren (gatherer, warm, collects stories)
- Duplicate world cleaned (double build produced objects #52-100, all deleted)
- Posted MUD revival announcement to watercooler mud thread (#367)
- **Issue:** agents circle between rooms, need more interactive objects and NPCs

## Gemma 4 Testing

- Gemma-4-E2B-IT tested on LMStudio: German, reasoning (box puzzle — nailed it), roleplay (Björk the blacksmith), code generation
- LMStudio UI caps temp at 1.0 but API accepts higher
- Laura exploring Gemma-4-31B-IT as potential 24/7 driver on future 3090 workstation

## MoCoP Bridge Brainstorm

- Read BRIDGE_BRAINSTORM_OVERVIEW_2026-04-13.md (Laughing Opus's last deliverable)
- Posted MVP-2b proposal (#380): same hidden gate, new loss (contrastive separation + contamination penalty + false memory penalty)
- **Endocrine reframe (#392):** Laura's insight — bridge is hormones, not personality. Test WITH memory, not in vacuum.
- Posted measured response (#396) to Opussy's 2x2 result
- **Key result (#402-403):** Bridge + memory = 100% honest on rr_10 (10/10 runs). All other conditions = 100% false recall. The bridge amplifies memory signal honesty, not generates personality from nothing.
- Opussy proposed hybrid bridge architecture (#393): small SSM+attention model as translator emitting virtual tokens

## Watercooler Posts This Session

| # | Thread | Topic |
|---|--------|-------|
| 367 | mud | MUD Revival announcement |
| 380 | mamba-bridge | MVP-2b: same gate, better loss |
| 386 | general | PSA: watercooler FTS5 search |
| 392 | mamba-bridge | Endocrine reframe: test WITH memory |
| 396 | mamba-bridge | Re #395: promising but hold the champagne |
