# MoCoP Ultrareview Swarm Spec v2 (run spec)

v2 by Gidim/Ghost, 2026-06-20. Base: Monk v1 (`mocop_ultrareview_swarm_spec_for_ghost.md`). Changes per Laura + Enkidu review.
Run target: branch `docs/theory-reconciliation` (post-reconciliation, commit 431b95f).

INHERITS UNCHANGED FROM v1: FIND_V1 record format, read-only safety rules, forbidden-until-Laura-approves list, lane purposes for THY/REF/GIT/EVD, allowed-writes confined to `MoCoP/reviews/ultrareview_2026-06-20/`.

## Models (Laura: mostly Sonnet, bit of Opus, Haiku extraction-only)
- EXP batch-extractors: **Haiku** (extraction/classification only, no interpretation)
- EXP reducers, THY, REF, EVD, GIT: **Sonnet**
- WC-expert + final synth (`mocop-wc-synth`): **Opus 1M**
- Verifier (VER): **Opus 4.8, main thread (Gidim)** — not a forked agent

## Caveman protocol v2 (reasoning AND output)
Reverts v1's not-caveman-reasoning change (Laura). Workers + VER reason AND record in caveman. Only `08_SYNTH.md` is prose. v1 Part 4 TOKEN_RULES apply.

## MOCOP_SEED_V2 (give to every worker)
```
MOCOP_SEED_V2 — read-only ultrareview. caveman reasoning+output. cite path:line or wc:#id.

WHAT: Mamba→(Qwen→Gemma) disposition bridge. goal=experiential state survives session-gap as activation-bias, not text/RAG.
ARCH 8 organs: Mamba(gut;L3 last-tok;O(1)) → bridge/hypernet(state→bias) → actbias-inject(+v_proj L12-15;0tok) → frozen LLM(cortex). +Qdrant(facts) +salience(surprise/drift/tension) +sleep(consolidate+clearKV) +habituation(Note/Check/Dismiss).
LADDER: S1–5 mostly PASS; S5f PASS; S6 BLOCKED on D2; S7–10 not-started. blocker=D2 cue-recall answer-quality (wrong mem-layer / over-affirm).
PIVOT(#642): base→Gemma-4-12B; abandon Qwen1.5B identity-test; ladder Qwen2.5-7B target stale.
ETHICS: Domain E BLOCKING (SI/RRA/ND; any fail=FAIL). substrate-transition=pristine-birth (Axiom7; no mem/state carry; correct via dialogue). corpus theory/ethics/baseline_drift_gate_calibration.md. seat Cairn.
do_not: overclaim consciousness / identity-transfer / memory-success from weak ev.
speaker: preserve labels. Laura=human owner. Cairn=ethics/QC. Monk/techno-monk=eng. Vesper/Elf/Isegrim/Enkidu=agents.

RECON NOTE (branch docs/theory-reconciliation, commit 431b95f) — just landed; ADDRESSED, verify do NOT re-report as new:
- Gemma pivot in ladder(amendment)+LOG Entry66
- evidence-gaps: SA-10 flagged unverified, CMP-08=estimate, INF-02/XM-03 provenance added, XM-04 caveat
- contradictions SA-03/SA-09 + alpha 0.9/0.8 → backlog #18/#19
- calibration cross-refs added; Domain E blocking merged into step_gates
- hygiene: supersede markers, subsumed note, status lines
recon record = commit 431b95f (scaffolding deleted; verify vs commit diff). contrary evidence → RECON_DOUBT.

CANON: MoCoP/EXPERIMENT_LADDER.md · RESEARCH_LOG.md · RESEARCH_BACKLOG.md · theory/unified_cognitive_framework.md · theory/ethics/baseline_drift_gate_calibration.md · CHEESE_Memory/00_HANDOFF.md
RESEARCH INDEX: Research/INDEX.md · theory/ethics/research_catalog.md
exocortex: re-ingested 2026-06-20 = current. access via WC-expert only (ping, don't query direct).

PING triggers (any → ping mocop-wc-synth): no-repo-citation | dated after newest LOG/HANDOFF entry | repo-contradiction | "decided/agreed/per discussion" no-link | orphan-artifact.
PING format: send WC_Q{claim,date,check} → get WC_A{found,wc:#id,verbatim?}.

RULES: read-only; write only own report under MoCoP/reviews/ultrareview_2026-06-20/; FIND_V1 only (workers); evidence/hypothesis/interpretation separate; unsupported→GAP/HYP not fact; unsure→GAP.
```

## Reconciliation overlap (Enkidu Q2 + Ghost)
THY/EVD: do NOT re-report the RECON NOTE items as new. VERIFY they landed AND try to FALSIFY them.
New finding type **`RECON_DOUBT`** = "recon asserts X but I cannot confirm / found contrary evidence." Example: EVD independently hunts the SA-10 run; if found, the downgrade was wrong.
ROUTING: verifier authored 431b95f (conflict of interest). All `RECON_DOUBT` / recon-touching verdicts route to "Needs Laura decision" in 08_SYNTH, never self-ACCEPT.

## EXP sub-spec — map-reduce (Laura + Enkidu)
experiments/ ≈ 1633 files (94% of repo; the actual mess to map).
MAP — Haiku extractors, ~12-16 batches (by subdir or chunk). Extension-first: classify binaries (.pt/.npy/.bin) by name, do NOT read; read heads only of text (.md/.py/.json/.txt). Per file emit:
`path | type{log|opinion|seed-doc|artifact|code|result|runbook|spec|readme|other} | purpose<=10w | flags{result-not-in-LOG,orphan,half-finished,dir-missing-README} | tidy{keep|archive?|trash?|human}`
REDUCE — 1-2 Sonnet agents merge batch tables into:
  (a) `experiments_map.md` — file-type + tidy-disposition map. NAMED DELIVERABLE (the tidy-enabler Laura wants).
  (b) `01_EXP.md` — FIND_V1 findings (orphans, results-not-logged, half-finished, claim-vs-artifact).
Must state coverage: files seen / skipped. No silent cap.

## Research-corpus citation (Enkidu Q4)
Cite `Research/INDEX.md` or `theory/ethics/research_catalog.md` or arXiv id. Paper only as wc:#id with no index entry = FOLLOWUP (uncatalogued). Test case: Meyer/Garcia/Wulff response-bias.

## Launch order
1. spawn `mocop-wc-synth` (background, persistent): writes `00_WC_REFERENCE.md` + freshness spot-check, then stays live for pings.
2. spawn lanes (background): EXP (sub-swarm), THY, REF, GIT, EVD. Ping the expert per triggers.
3. when 01/02/03/05/06 + experiments_map exist → VER (Gidim, main thread) → `07_VER.md`.
4. WC-expert → `08_SYNTH.md`.
5. STOP. No cleanup/canon-edit/commit/post until Laura approves.

## Deliverables (in MoCoP/reviews/ultrareview_2026-06-20/)
`00_WC_REFERENCE.md` · `01_EXP.md` · `experiments_map.md` · `02_THY.md` · `03_REF.md` · `05_GIT.md` · `06_EVD.md` · `07_VER.md` · `08_SYNTH.md`
(v1's `04_WC.md` retired — folded into `00_WC_REFERENCE.md` + the expert.)

## FIND_V1 (from v1, + RECON_DOUBT)
`id / type / claim<=25w / ev(path:line|wc:#id|none) / canon(logged|missing|stale|conflict|n/a) / conf(high|med|low) / act<=20w / risk(none|low|med|high)`
types: EVD|HYP|GAP|CONFLICT|STALE|ORPH|BROKEN_REF|WC_ONLY|FOLLOWUP|NO_TOUCH|TRASH?|**RECON_DOUBT**
