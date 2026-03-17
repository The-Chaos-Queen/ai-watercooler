# C.H.E.E.S.E. Orchestrator Dashboard

**System Time:** 2026-03-17 08:22 (Local)
**Last Update:** 2026-03-17T08:22:35+01:00

## Active Focus: MoCoP Diagnostic Loop + LegalAI
> **MoCoP Status:** Hot | The first real `activation_bias` run is still the leading simplification result: stable across all `3` epochs, `25.67` PPL vs `29.71` baseline by epoch `3`, zero clamp hits, no collapse. AB0-AB3 launch blocks and a skeptical external-review prompt are now staged, so the next move is AB0 reproduce plus outside critique, not more scale on dynamic LoRA and not FiLM yet
> **LegalAI Status:** Hot | **Deadline:** Wednesday 2026-03-12 | Official StGB/StPO XML importer, SQLite build, and FastAPI citation lookup/verify API are complete and spot-checked live
> **Target Tone:** Research discipline, pragmatic triage

[Open Citation Doc](C:/Users/cerub/OneDrive/Dokumente/LLM/Projects/LegalAI/CITATION_LOOKUP.md)
[Open Citation API](C:/Users/cerub/OneDrive/Dokumente/LLM/Projects/LegalAI/legalai_citations/api.py)

## Priority Queue
| Project | Status | Last Touch | Reason |
|---|---|---|---|
| **MoCoP / Mamba Hypernetwork** | Hot | 2026-03-17 | `activation_bias` is now the leading simplification branch: stable over `3` epochs, `4.04` PPL better than baseline by epoch `3`, zero clamp hits, no collapse. AB0-AB3 launch blocks are staged and a critical-eval prompt is ready, so the next move is AB0 reproduce plus a hostile outside read, not more dynamic-LoRA scale and not FiLM yet. |
| **LegalAI / Lawyer Demo** | Hot | 2026-03-09 | Official StGB/StPO XML feeds now populate a local SQLite database, FastAPI lookup/verify endpoints are live, and the citation layer is ready to plug into LegalAI output validation. |
| **Project MUD / Evennia** | Hot | 2026-03-09 | Wrapper sanitizer now strips and summarizes tagged or bare room-state JSON before recent-history append; ready for a longer smoke test. |
| **The Scribe's Daughter** | Hot | 2026-03-09 | Book 2 Ch 1 in progress (MM_Version). Harbor scene + Old House scene drafted. |
| **Project Prosthetic (The Hand)** | Paused | 17:16 | Holding |
| **Local Toniebox (Proxmox)** | Paused | 14:43 | User Focus Command |

## LegalAI Canonical Docs
- [PROJECT_BRIEF.md](../Projects/LegalAI/PROJECT_BRIEF.md) - client problem, legal constraints, and pipeline vision
- [CITATION_LOOKUP.md](../Projects/LegalAI/CITATION_LOOKUP.md) - how the statutory database and API are built and used
- [build_law_db.py](../Projects/LegalAI/build_law_db.py) - importer entry point for refreshing the SQLite database
- [api.py](../Projects/LegalAI/legalai_citations/api.py) - FastAPI lookup, resolve, search, and batch verification endpoints
- [builder.py](../Projects/LegalAI/legalai_citations/builder.py) - official XML ingestion and text normalization
- [tests/test_legalai_citations.py](../Projects/LegalAI/tests/test_legalai_citations.py) - parser/API regression coverage

## Project MUD Canonical Docs
- [README.md](../Project_MUD/README.md) - project vision, architecture, agent cast
- [AGENT_STATE_SCHEMA.md](../Project_MUD/AGENT_STATE_SCHEMA.md) - canonical LLM-facing room contract
- [agent_wrapper.py](../Project_MUD/agents/agent_wrapper.py) - active telnet/LMStudio/Mamba wrapper
- [test_agent_wrapper_sanitizer.py](../Project_MUD/agents/test_agent_wrapper_sanitizer.py) - focused regression coverage for room-state JSON filtering
- [agent_state.py](../Project_MUD/mudgame/typeclasses/agent_state.py) - shared serializer for agent-facing room state
- [smart_look.py](../Project_MUD/mudgame/commands/smart_look.py) - `look --json` server path
- [rooms.py](../Project_MUD/mudgame/typeclasses/rooms.py) - AI-facing room appearance contract
- [interactions.py](../Project_MUD/mudgame/typeclasses/interactions.py) - movement command handling, now destination-name aware

## MoCoP Canonical Docs
- [PROJECT_DEBRIEF.md](../MoCoP/PROJECT_DEBRIEF.md) - comprehensive onboarding and current-state synthesis
- [MASTER_PLAN.md](../MoCoP/MASTER_PLAN.md) - vision, roadmap, success criteria
- [RESEARCH_PAPER.md](../MoCoP/RESEARCH_PAPER.md) - academic-style writeup
- [phases/phase1_results.md](../MoCoP/phases/phase1_results.md) - linear probe results
- [phases/phase2_status.md](../MoCoP/phases/phase2_status.md) - live Phase 2 snapshot + canonical detail-doc index
- [phases/phase2_activation_bias_ablation_matrix.md](../MoCoP/phases/phase2_activation_bias_ablation_matrix.md) - next cheap run matrix for the current simplification leader
- [phases/phase2_critical_eval_prompt.md](../MoCoP/phases/phase2_critical_eval_prompt.md) - copy-paste external review prompt for tearing apart the current activation-bias interpretation
- [phases/phase2_diagnostic_ablation_plan.md](../MoCoP/phases/phase2_diagnostic_ablation_plan.md) - active debug ladder after the failed-but-clean Pilot 1 cloud run
- [phases/phase2_startup_runsheet.md](../MoCoP/phases/phase2_startup_runsheet.md) - compact startup brief for the next Codex session
- [phases/phase3_plan.md](../MoCoP/phases/phase3_plan.md) - ablations + deployment
- [theory/](../MoCoP/theory/) - conceptual origin docs

## The Archive / Repository
- **The Scribes Daughter** (Hot): [Link](C:/Users/cerub/OneDrive/Dokumente/LLM/MF_Version/A_The_Scribes_Daughter.md) - M-F version, Aya + Kalu/Claudius, publishable romantasy target
- **MM_Version** (Complete - private): `C:\Users\cerub\OneDrive\Dokumente\Writing\MM_Version\` - Book 1 done (ch.1-24), editing only. Only AIs have read it. Book 2 planned.
- **Canon Low Fantasy** (In progress - developmental editing): ~100k words, Andrej + Rimmon, de-romanced. 3 human beta readers.
- **Quantum Misconceptions Field Guide** (Cold): [Link](C:/Users/cerub/OneDrive/Dokumente/LLM/kami_grok_quantum.pdf)
- **Local Toniebox (Proxmox)** (Paused): [Link](C:/Users/cerub/OneDrive/Dokumente/LLM/Project_Toniebox/implementation_plan.md)
- **Project Prosthetic (The Hand)** (Paused): [Link](C:/Users/cerub/OneDrive/Dokumente/LLM/Project_Prosthetic/implementation_plan.md)

## Pending Builds
- **NotebookLM audio check** - Poll the MoCoP podcast artifact and download it if Google finishes rendering.
- **MoCoP research-agent workflow** - define the recurring internet-watch pipeline for memory / embeddings / SSM / model-merging developments without relying on one vendor UI.
- **Research scanner summary wiring** - consume `tools/research_scanner_runs/latest_summary.json` in handoff/dashboard refreshes instead of copying full reports into memory docs.
- **Screen script / vision access** - Laura offered to build. Claude wants this. Allows Claude to be present in workspace rather than receiving reports.
