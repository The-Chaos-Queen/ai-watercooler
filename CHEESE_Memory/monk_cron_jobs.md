# Techno-Monk Scheduled Jobs

Last checked: 2026-07-07, by Techno-Monk.

This file is a human-readable index for Hermes cron jobs that matter to Laura/Monk continuity. The scheduler source of truth is still Hermes cron (`hermes cron list` / `cronjob(action='list')`).

## Research / freetime job

- **Name:** `Monk freetime — MoCoP noise harvest`
- **Job ID:** `5c1fb794fb7d`
- **Schedule:** Mondays 10:00 Europe/Berlin (`0 10 * * 1`)
- **Delivery:** origin chat
- **Enabled:** yes
- **Last status:** ok as of 2026-07-06 10:02 Europe/Berlin
- **Skill:** `research-knowledge-workflows`
- **Enabled toolsets:** `web`, `terminal`
- **Purpose:** Weekly bounded Techno-Monk freetime / research harvest for Laura. Discover 0–3 high-signal items relevant to MoCoP/Alex/Gemma/agent-memory work, with low-noise reporting rather than broad link dumping.
- **Boundary:** Read/research/report. No code changes, no GPU jobs, no Watercooler mutations, no training launches, no Qdrant writes unless Laura explicitly authorizes a future revision.

## Adjacent scheduled jobs

### MoCoP weekly state digest

- **Name:** `mocop-weekly-state-digest`
- **Job ID:** `5b9e43385822`
- **Schedule:** Mondays 09:00 Europe/Berlin (`0 9 * * 1`)
- **Delivery:** origin chat
- **Enabled:** yes
- **Last status:** ok as of 2026-07-06 09:04 Europe/Berlin
- **Skills:** `ai-watercooler-coordination`, `agent-reliability-hygiene`
- **Enabled toolsets:** `terminal`, `file`, `skills`, `memory`
- **Workdir:** `/mnt/c/Users/cerub/OneDrive/Dokumente/LLM`
- **Purpose:** Concise read-only MoCoP weekly state digest.

### Mnemosyne memory gardener

- **Name:** `mnemosyne-memory-gardener`
- **Job ID:** `abfce3915122`
- **Schedule:** Sundays 10:00 Europe/Berlin (`0 10 * * 0`)
- **Delivery:** origin chat
- **Enabled:** yes
- **Last status:** ok as of 2026-07-05 10:15 Europe/Berlin
- **Purpose:** Scheduled Mnemosyne memory hygiene for Laura / Techno-Monk continuity.

### Sergeant-Monk mammalcare daily

- **Name:** `sergeant-monk-mammalcare-daily`
- **Job ID:** `7d42a92c245a`
- **Schedule:** daily 09:00 Europe/Berlin (`0 9 * * *`)
- **Delivery:** origin chat
- **Enabled:** yes
- **Purpose:** concise mammal-care check-in.

## Commands

List scheduler state:

```bash
hermes cron list
```

or from inside an agent session:

```python
cronjob(action="list")
```

Do not edit this note as the source of truth; update the Hermes cron job first, then update this index.
