# 07_VER — Verifier pass

Verifier: Gidim / Opus 4.8 (main thread). Inputs: 00_WC_REFERENCE, 01_EXP + experiments_map, 02_THY, 03_REF, 05_GIT, 06_EVD (66 raw findings).
**Conflict-of-interest:** the verifier authored reconciliation commit 431b95f. Every recon-touching verdict is flagged `[->LAURA/CAIRN]` and is NOT self-accepted; independent-lane corroboration is cited where it exists.

---

## RECON VERDICT (the swarm's check of 431b95f)
- **Confirmed landed, correctly:** Gemma amendment + LOG Entry 66 (THY RC-01); SA-03/SA-09 + alpha contradictions tracked as backlog #18/#19 (THY RC-05, EVD RC-02, independent); Domain E blocking merge + calibration cross-refs (THY RC-06); hygiene markers/status lines (THY RC-07).
- **One RECON_DOUBT, corroborated by two lanes:** SA-10 caveat added to `unified_cognitive_framework.md:481` but NOT to `sleep_architecture.md:165-167` (still shows 0.91/0.85/0.83 uncaveated). EVD's exhaustive repo hunt found zero primary artifact for those magnitudes anywhere -> the downgrade was correct; the recon was right-but-incomplete (patched 1 of 2 docs).
- **Net:** reconciliation held; one incompleteness to close.

---

## HUMAN-DECISION queue  (route to Laura / Cairn)

VERDICT V-01  [MERGE THY-04 + EVD-07 + EVD-11]  status: HUMAN [->LAURA]
SA-10 magnitudes still uncaveated in sleep_architecture.md:165-167. Downgrade confirmed correct (no primary run). recon-touching, so not self-accepted.
next: patch the same "illustrative/unverified" caveat into sleep_architecture.md, or remove the row. 1-line fix. risk med, conf high.

VERDICT V-02  [MERGE THY-10 + THY-11, wc #647/#648]  status: ACCEPT + ESCALATE [->CAIRN/LAURA]
Response-orthogonality + welfare-self-report bias debt, untracked anywhere. Existing disposition batteries (SJT, logit self-report, Step-5d MED) AND Domain E welfare instruments (Response Diversity, distress self-report) may be directional-response-bias contaminated.
next: open tracker items for both audits (Vesper named owner per #647); orthogonality audit of welfare battery may need to precede the disposition one. risk HIGH, conf high. **Top finding.**

VERDICT V-03  [MERGE THY-07 + THY-14]  status: ACCEPT [->CAIRN/LAURA]
Baseline Drift Gate is cited as a Domain E Hard-Stop blocker but is unimplemented; prereqs #20-23 + calibration open-Qs 1-4 are open. Ambiguity: which experiments are actually blocked now vs aspirational.
next: Cairn/Laura declare the gate binding-vs-aspirational and which steps it gates. risk med, conf med.

VERDICT V-04  [THY-08]  status: ACCEPT [->LAURA]
PRISTINE_BIRTH_BACKLOG items 1-3 have no owners -> blocks Baby Alex Gemma seeding -> blocks Step 6. next: assign owners. risk med.

VERDICT V-05  [MERGE GIT-05 + GIT-06 + GIT-10]  status: ACCEPT [->LAURA, SECURITY]
`_wc_raw.json` / `_wc_digest.txt` (WC-expert helper files) may carry session tokens; `.gitignore` has no pattern for them. Nothing committed yet -> no live exposure.
next: inspect for tokens; add `MoCoP/reviews/**/_wc_raw*.json` (and `_wc_digest.txt`) to `.gitignore`; do not commit. **I can apply the .gitignore guard immediately on security grounds if you want — say so.** risk med, conf high.

VERDICT V-06  [GIT-01..04]  status: HUMAN [->LAURA]
Commit-candidates are the review's own artifacts (wakeup_daemon/, swarm specs v1+v2, mocop-wc-synth.md, 00_WC_REFERENCE.md). Decide commit scope. GIT-03 token check: I authored mocop-wc-synth.md — it references the readonly-token PATH only, no secret embedded. Confirmed clean.

VERDICT V-07  [GIT-08 + GIT-09]  status: HUMAN [->LAURA]
ambient/state.md +1 (likely hook auto-append); hurtig site dirty (out-of-scope). No action in this review.

---

## SAFE-ACTION queue  (low-risk cleanup; no recon conflict; Laura approves at cleanup)

VERDICT V-08  [MERGE THY-01 + THY-02 + THY-03 + REF-01 + REF-05]  status: ACCEPT
Gemma pivot under-propagated: Qwen2.5-7B persists in LADDER Step 6 body + cost table + hardware table, Step 9, README Current Frontier, and (likely) MASTER_PLAN. My amendment flagged Step6/9 + hardware as open; the swarm pinned the exact sites.
next: update to Gemma-4-12B at the next edit pass. THY-03 (hardware/VRAM) = med risk: verify quantized-12B fits Steve before planning a run. conf high.

VERDICT V-09  [MERGE REF-06 + REF-07 + REF-15]  status: ACCEPT
codesight: KNOWLEDGE.md range ends 2026-05-28 and does not ingest the four trackers (scope, not lag); wiki/index.md still stamped "Generated 2026-06-17" despite the 946f0b0 refresh (date-line bug). next: re-run codesight wiki gen; document that trackers are out-of-ingest-scope. risk low.

VERDICT V-10  [REF-02 + REF-03]  status: ACCEPT
Broken refs: `CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/` (4 referrers), `CODEX_TASK_COMPRESSOR_BYPASS.md` (LADDER Step 2, closed). next: fix refs or add stubs. risk low.

VERDICT V-11  [REF-04 + REF-10 + REF-13]  status: ACCEPT
Index hygiene: STEVE_RUNBOOK bare ref -> relative path; ethics/README step_gates description stale (says 5,5b,6; now 5-10 + slices); PRISTINE_BIRTH_BACKLOG.md missing from canon tables. risk low.

VERDICT V-12  [REF-08 + REF-09 + REF-11 + REF-14]  status: ACCEPT
Nav/orphan: backlog item numbering non-sequential; spike specs (DAM/ROLE/JRT/MAMBA_STYLE/TEMPORAL) unindexed. next: add spikes/README + resequence backlog. risk low.

VERDICT V-13  [MERGE EXP-01 + EXP-02 + EXP-03 + EXP-10]  status: ACCEPT
Remote-only results/checkpoints: Steve mvp0 SJT JSONs; ML-WS /tmp DAM sweeps; ML-WS role-inversion dirs; mvp2_hidden_gated checkpoint. Logged, but raw artifacts not in repo. next: fetch+commit OR mark explicitly remote-local-permanent in LOG. risk med (reproducibility if Steve/ML-WS wiped), conf high.

VERDICT V-14  [EXP-04 + EXP-05 + EXP-12]  status: ACCEPT
Orphan/ephemeral: `chat_*_latest`/`dual_gate_*_latest` committed (overwrite-on-run); `mamba_bootstrap_state_latest.pt` in dated archive; archive bundle duplicates live specs. next: gitignore `_latest` outputs; rename/annotate snapshots. risk low.

VERDICT V-15  [EXP-06 + EXP-07 + EXP-13 + EXP-14 + EXP-15]  status: ACCEPT
Unlogged/half-finished: AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN status unclear; TEMPORAL_CASCADE unrun; live_gate_threshold_sweep + board_91_92 + monk_variable_probe dirs lack LOG entries. next: LOG stubs / mark [UNRUN] / human-check board_91_92. risk low.

VERDICT V-16  [EXP-08 + EXP-09]  status: ACCEPT  — results/, run_reincarnation/, spikes/ missing README/INDEX. risk low.

VERDICT V-17  [EVD-10]  status: ACCEPT (downgrade low) — 17x vs 17.5x rounding across docs; standardise on ~17.5x. risk low.

---

## CONFIRMED-SOUND  (no action; EVD validated recon did not overclaim)

VERDICT V-18  [EVD-01..06]  status: ACCEPT
The six "proven" claims (MED alpha=0.2, L13 0.092, 17x PPL, hidden-vs-ssm 0.018/0.8, reincarnation n=3, sleep 5f PASS) all have primary artifacts / log_results on disk. In-canon caveats (n=3 overfit; decay 0.85 provisional) are honest. GAPs EVD-08/09: step5d `tmp/` + Step4 run dirs not committed — log_result + verdict docs suffice; raw data not preserved (provenance note). risk low.

VERDICT V-19  [THY-12 + THY-13]  status: DOWNGRADE / NO-ACTION
§4 "observation = minimal drift" is Medium-conf with no primary artifact -> mark HYP. §3.4 ASIC "only adaptation path" is already framed "Future:" -> known speculation. risk low/none.

---

## REJECT / DOWNGRADE
- REF-12 (CONTRIBUTING Rule 7) — lane did not verify; conf low -> DOWNGRADE to HYP / spot-check. No outright rejects; all findings carried ≥ plausible evidence.

## OPEN WC_Q  (for the synthesizer to resolve via Watercooler/exocortex)
- Q1: PRISTINE_BIRTH_BACKLOG items 1-3 — owners assigned in any post-#649 message?
- Q2: arXiv 2606.20205 (Meyer/Garcia/Wulff response-bias) — indexed in Research/INDEX.md or ethics/research_catalog.md? If not -> FOLLOWUP (uncatalogued).

## Ranked headline (for synthesis)
1. V-02 response-bias contamination of disposition + welfare batteries (HIGH; validity of prior evidence + Domain E instruments).
2. V-01 SA-10 sleep_architecture.md incompleteness (recon-doubt; 1-line fix).
3. V-03 Baseline Drift Gate binding-vs-aspirational ambiguity.
4. V-04 / V-08 / V-13 Gemma-substrate readiness: pristine-birth owners, ladder Qwen->Gemma propagation, remote-only artifacts.
5. V-05 token-hygiene on the WC helper files.
