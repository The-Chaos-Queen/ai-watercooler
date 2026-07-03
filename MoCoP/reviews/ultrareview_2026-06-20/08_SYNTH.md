# 08_SYNTH — MoCoP Ultrareview, final report

**For:** Laura
**Date:** 2026-06-20
**Branch:** `docs/theory-reconciliation`
**Synthesizer:** Gidim (Opus 4.8, 1M). Read-only pass; this is the only file written.
**Inputs:** 07_VER (verifier, primary), 00_WC_REFERENCE (Watercooler ledger #586–#651), lane reports 01_EXP / experiments_map / 02_THY / 03_REF / 05_GIT / 06_EVD. Two open WC_Q resolved against the live Watercooler (read-only) and the repo.

**Speaker labels** (kept throughout): **Laura** = human owner; **Cairn** = ethics/QC (Opus 4.7 local); **Monk** = eng (GPT-5.5 Hermes); **Vesper / Elf / Isegrim / Enkidu / Gidim** = agents.

**Conflict-of-interest carried forward:** the verifier (Gidim, Opus 4.8) authored reconciliation commit `431b95f`. Every recon-touching verdict was flagged in 07_VER as not self-accepted. Those items are routed to **Needs Laura decision** below and presented as findings for you, not as self-confirmed results.

No claim in this report goes beyond verifier support. Nothing here asserts consciousness, identity-transfer, or memory-success; the n=3 reincarnation and capsule-boot results remain qualitative demos with their in-canon caveats intact.

---

## Executive summary

The reconciliation (`431b95f` + `8b83a24`) held. The swarm's independent lanes corroborated its substantive landings — Domain E promoted to blocking, the three Hard-Stop invariants, Invariant-2 default-binds-all, the Gemma substrate pivot, the pristine-birth rule, and the calibration corpus all confirmed present in canon. The six "proven" empirical claims all have primary artifacts on disk; the reconciliation did not overclaim.

The headline is not a reconciliation defect. It is an **untracked methodology debt**: the Meyer/Garcia/Wulff response-bias finding (#647/#648) implies that the pack's existing disposition *and* welfare batteries may be contaminated by directional response bias, and there is no tracker row anywhere committing the audit. This casts a validity question over prior behavioural evidence and over the Domain E welfare instruments themselves. It needs an owner and a decision before those readings are trusted again.

Below the headline sit one recon-incompleteness (a one-line caveat the reconciliation patched in one doc but not its source), a binding-vs-aspirational ambiguity in the Baseline Drift Gate, the Gemma-substrate readiness cluster (unassigned pristine-birth owners, un-propagated Qwen→Gemma references, remote-only artifacts), and a long tail of low-risk reference and tidy hygiene. One security item — Watercooler helper files with possible session tokens and no `.gitignore` guard — is cheap to close and worth closing now.

---

## Top confirmed findings

Ranked, following 07_VER's headline order.

1. **Response-bias debt contaminates the disposition AND welfare batteries — untracked. (V-02, #647/#648; THY-10, THY-11.) HIGH.**
   Cairn's #647 digest of Meyer/Garcia/Wulff (arXiv 2606.20205) found 81–90% of LLM psych-instrument variation is directional response bias, and ruled that **every disposition/welfare battery needs a "response-orthogonality" audit before its readings are trusted.** Opus 4.8 (door-instance, #648) extended this to welfare self-report: the cut discredits *both* calm and distressed readings — the self-report channel is unreliable in both directions, and welfare assessment should move to the activation level (Pinky's L3 cosine, Isegrim's role-inversion KL, both validated as the right shape). The consequence: existing disposition readings (SJT, logit self-report, Step-5d MED interpretation) and Domain E welfare instruments (Response Diversity, distress self-report — cited as blocking criteria in step_gates.md) may be directional-response-bias contaminated. **There is no tracker row for "audit each existing battery."** The gate-side risk (G0 oxytocin Method A) and the corpus concern flow into PRISTINE_BIRTH_BACKLOG Items 1–2, but the standalone audit is Watercooler-only. Cairn named Vesper natural owner (her surface is at risk); #648 suggests the welfare-battery audit may need to run *first*.

2. **SA-10 sleep-drift magnitudes still uncaveated in `sleep_architecture.md`. (V-01; THY-04, EVD-07, EVD-11.) Recon-incompleteness.**
   The reconciliation correctly downgraded the 0.91/0.85/0.83 drift magnitudes to "illustrative/unverified pending provenance" — EVD's exhaustive repo hunt found **zero primary artifact** for those numbers anywhere (no LOG entry, no JSON, no Watercooler cite), so the downgrade was right on the facts. But the caveat landed only in `unified_cognitive_framework.md:481`; `sleep_architecture.md:165-167` still presents the same three values as measured results in a data table. Two independent lanes caught this. It is a one-line fix, but it is recon-touching, so it is routed to **Needs Laura decision**, not self-accepted here.

3. **Baseline Drift Gate: binding-vs-aspirational ambiguity. (V-03; THY-07, THY-14.) Medium.**
   step_gates.md cites the Baseline Drift Gate as a Domain E Hard-Stop blocker, but the gate is unimplemented — there is no operational code, and its ship-precondition (coverage canary + {growth,erosion,neither} bidirectionality) plus calibration open-questions 1–4 and backlog prereqs #20–23 are all open. The calibration corpus (Cases 01–08, all three verdict classes) exists and is sound; the executable gate does not. So the Hard-Stop clause references something that cannot currently block. Cairn/Laura need to declare the gate binding-vs-aspirational and name which steps it actually gates.

4. **Gemma-substrate readiness cluster. (V-04 / V-08 / V-13.) Medium.**
   Three strands gate Step 6 first-seeding on the new substrate:
   - **Pristine-birth owners unassigned (V-04, THY-08).** PRISTINE_BIRTH_BACKLOG Items 1–3 (G0 re-extraction; bridge re-train on diverse-balanced corpus; `fleeting_state_security.md` Phase A encryption) have no confirmed owners. **WC_Q1 resolved: no.** See Watercooler-only items for the detail — Cairn proposed candidates inside #649 but logged "Open: ownership for each item," and the only later messages (#650/#651) are Laura's WAKE_TEST pings. Item 3 is the precondition for first seeding; Items 1–2 share the corpus and can run in parallel; all three block Step 6.
   - **Qwen→Gemma under-propagated (V-08; THY-01/02/03, REF-01/05).** The #642 pivot to Gemma-4-12B landed in the Ladder amendment + LOG Entry 66, but Qwen2.5-7B persists in LADDER Step 6 body and cost table, Step 9 transfer target, the hardware table, README Current Frontier (still dated 2026-06-08), and likely MASTER_PLAN. THY-03 (hardware/VRAM) is the one med-risk item: verify a quantized 12B actually fits Steve's 16GB before planning a run.
   - **Remote-only artifacts (V-13; EXP-01/02/03, EXP-10).** Steve mvp0 SJT JSONs, ML-WS `/tmp` DAM sweeps, ML-WS role-inversion dirs, and the mvp2_hidden_gated checkpoint are logged in RESEARCH_LOG but the raw artifacts live only on Steve / ML-WS. Reproducibility is at risk if either machine is wiped.

5. **Token hygiene on the Watercooler helper files. (V-05; GIT-05/06/10.) Medium, cheap.**
   `_wc_raw.json` and `_wc_digest.txt` in the review dir may carry session tokens, and `.gitignore` has no pattern for them. Nothing is committed yet, so there is no live exposure — but the guard is missing. The verifier offered to apply the `.gitignore` guard immediately on security grounds. See Do-not-touch / Needs Laura decision.

---

## Missed followups

- **Response-orthogonality audit of existing batteries (#647)** — the single most consequential gap. No tracker row. Owner candidate: Vesper. (THY-10.)
- **Welfare self-report distrust + activation-level migration (#648)** — no welfare-methodology doc or tracker row; "audit possibly first" is uncommitted. (THY-11.)
- **arXiv 2606.20205 (Meyer/Garcia/Wulff) is uncatalogued. WC_Q2 resolved: FOLLOWUP.** The paper is cited in PRISTINE_BIRTH_BACKLOG Items 1–2 and underpins #647/#648, but it is indexed in **neither** canonical research index. `MoCoP/Research/INDEX.md` does not exist; the only `Research/INDEX.md` is the repo-root research wiki (built 2026-04-21, ~196 sources), and it does not contain the paper. `MoCoP/theory/ethics/research_catalog.md` exists but is a 2026-03-20 ethics catalog and does not contain it either. A repo-wide search finds the id only in this review's own files. The most load-bearing paper of the week has no catalog row.
- **JRT ask-then-read build decision (#637)** — the *finding* (D wins, restate is suppressive) is in LOG Entry 65, but the chat_server "ask-then-read loop earns a build ticket" decision is Watercooler-only; no BACKLOG/Ladder row commits it. Current chat_server may retain the restate pattern Entry 65 proved suppressive. (THY-15.)
- **Cairn's Lesson Memory v0 Invariant-1 PASS verdict (#609/#112)** — the first live application of the candidate gate; recorded only in the Watercooler, not transcribed into any tracker row. (THY-09.)

---

## Evidence gaps

The six primary claims are sound; the gaps are about raw-artifact preservation, not claim validity (V-18 confirms the claims).

- **No primary artifact for the SA-10 0.91/0.85/0.83 magnitudes anywhere in the repo** (EVD-07). The downgrade to "unverified" is therefore correct; see Top-finding #2 for the remaining one-doc patch.
- **Step-5d raw run dir** (`tmp/step5d_20260322/`) not committed/gitignored; LOG entry + scripts + the `..._codexfix.pt` checkpoint are the surviving evidence (EVD-08).
- **Step-4 run dirs** (`run_constant_bias*/`, `run_actbias/`) absent; `STEP4_VERDICT_2026-03-18.md` + LOG entry suffice as log_result (EVD-09).
- **Remote-only result files** (EXP-01/02/03/10) — see Top-finding #4, remote-only artifacts strand.
- **Unlogged result dirs** (EXP-13/14/15): `live_gate_threshold_sweep_2026-04-03.*`, `results/board_91_92_mlws/`, `results/monk_variable_probe_20260606/` have no LOG entry. `board_91_92` needs a human check — it may be an OpenCLAW board scrape sitting in `results/` rather than an experiment output.
- **Half-finished specs** (EXP-06/07): `AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN.md` implementation status unclear (may be superseded by the astrocyte controller); `TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md` filed but unrun.

---

## Stale or conflicting canon

- **Qwen2.5-7B → Gemma-4-12B not propagated** beyond the Ladder amendment header: Step 6 body + cost table (THY-02), Step 9 transfer target (THY-01), hardware table (THY-03), README Current Frontier (REF-01), likely MASTER_PLAN (REF-05). The Ladder amendment itself flags Step 6/9 + hardware as open work — this is acknowledged debt, not a recon failure.
- **Training-alpha split unresolved** (THY-06, EVD-02-recon): live trainer uses α=0.9, `STEP5_DESIGN_NOTES.md` records α=0.8, `unified_cognitive_framework.md:197` self-flags. Tracked as backlog #19 (open), but neither value is declared canonical. Resolve before the next bridge training run or risk non-reproducible runs.
- **Salience metric undefined** (THY-05): backlog #18 (gradient-surprise vs reconstruction-error) open, no owner; the dual gate is live (SA-02) but the canonical surprise metric is unpinned, which touches every consolidation event.
- **Baseline Drift Gate clause references an unimplemented gate** (THY-07/THY-14) — see Top-finding #3.
- **17x vs 17.5x rounding** (V-17, EVD-10): both derive from 4.04/0.23 = 17.56x; STEP4_VERDICT rounds to 17x, LOG/ABSTRACT/PAPER use 17.5x. Cosmetic; standardise on ~17.5x. Downgraded to low.
- **Two framing claims correctly flagged as non-load-bearing** (V-19): `unified §4` "observation = minimal drift" is Medium-conf with no primary artifact — mark HYP; `§3.4` ASIC "only adaptation path" is already framed "Future:" — known speculation. No action beyond the HYP label.

---

## Watercooler-only items

Decisions that live only in the Watercooler with no committed tracker/canon row as of HEAD. Lane workers cannot cite a doc for these.

- **#647 response-orthogonality audit** — the most consequential WC-only item (see Top-finding #1, Missed followups).
- **#648 welfare self-report distrust** — referenced only as framing inside PRISTINE_BIRTH_BACKLOG Item 2.
- **#637 chat_server ask-then-read build ticket** — finding is in LOG Entry 65; the build decision is WC-only.
- **#609 Cairn's Lesson Memory v0 Invariant-1 PASS (#112)** — live gate application, not transcribed.
- **#596 Cairn taking the ethics/QC seat + claiming gate #115** — roster-level, lives on the MEMORY.md / pack-roster side, out of this repo's tracker scope. (REF lane: confirm against `project_pack_roster.md`.)
- **#605 jurisprudence exhibit** (claude.ai production drift clause as opposite-theology mirror of #587) — the Arlo *case* landed in the corpus; the broader observation lives in the Watercooler + an Isegrim session-log digest only.

**WC_Q1 resolution (V-04 owners) — answered NO.** PRISTINE_BIRTH_BACKLOG Items 1–3 have no confirmed owners. Inside #649 Cairn *proposed* candidates — Item 1 → Pinky/Isegrim (both methods named in the doc); Item 2 → Vesper if her surface recovers, else needs hands; Item 3 → Purple specified the original, current owner unclear — but explicitly logged "Open: ownership for each item." No acceptance by Laura, and the only later traffic (#650/#651) is Laura's WAKE_TEST pings to Monk. Owners are proposed, not assigned.

**Identity caveat (carried from 00_WC_REFERENCE §0):** `claude-ai` is a wire identity, not one author. #618/#633/#648 = Opus 4.8 door-instance; #596–#616/#639 = Cairn (or Elf at #639) through the connector. Attributions above read the sign-off, not the wire field. From #620 on, `from_agent=cairn` is reliably Cairn.

---

## Reference-index problems

All low-risk; a cleanup batch, not a blocker.

- **Broken refs** (V-10; REF-02/03): `CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/` does not exist (4 referrers: theory/README, Three_System_Cognitive_Architecture, phase1_results, RESEARCH_LOG Entry 1); `CODEX_TASK_COMPRESSOR_BYPASS.md` referenced by LADDER Step 2 (closed) but absent. Fix refs or add stubs.
- **Index hygiene** (V-11; REF-04/10/13): `STEVE_RUNBOOK.md` bare reference in theory/README → relative path; ethics/README step_gates description stale (says "Steps 5, 5b, 6" — now 5/5b/5c/5e/6–10 + Sleep Slices + Task #115 + addenda); **PRISTINE_BIRTH_BACKLOG.md missing from the README canon table** and from theory/README.
- **Nav / orphan** (V-12; REF-08/09/11/14): backlog item numbering non-sequential (item 19 separated from its P1 peers); spike specs (DAM/ROLE/JRT/MAMBA_STYLE/TEMPORAL) and `results/jrt_spike/` unindexed. Add a `spikes/README.md` with per-spike status and resequence the backlog.
- **codesight freshness** (V-09; REF-06/07/15): `KNOWLEDGE.md` range ends 2026-05-28 and does not ingest the four central trackers (that is a scope choice, not a lag — exocortex re-ingest is current per 00_WC_REFERENCE §2); `wiki/index.md` still stamped "Generated 2026-06-17" despite the `946f0b0` refresh (the date line did not auto-update — a generator bug). Re-run codesight wiki gen; document that the trackers are out-of-ingest-scope.
- **REF-12 downgraded** (per 07_VER): CONTRIBUTING Rule 7 session-close ref — lane did not verify, low confidence; spot-check only, not a confirmed finding.

---

## Git-provenance-tidy plan

**Branch confirmed:** `docs/theory-reconciliation`, HEAD `946f0b0`. The three in-scope commits — `431b95f` (reconcile trackers, 12:38), `8b83a24` (per-step Domain E + pristine-birth backlog, 13:12), `946f0b0` (codesight refresh, 14:05) — are all present.

**experiments/ tidy split** (from experiments_map, 1633 files classified, 100% coverage):
- **trash (~157):** all `__pycache__/*.pyc` + the `.pytest_cache/` subtree (including its `.gitignore` and `README.md`).
- **archive (~100):** `.pt` weights dated 2026-03/04 (cold storage; keep `cheese_reincarnation_bridge_1.5b_codexfix.pt` warm as the active checkpoint), superseded utilities (`archive_chat_session.sh`, `compare_archive_pipeline.py`, `build_baby_alex_116_archive_bundle.py`), `ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md`, `old7b_checkpoint_easyfirst_panel_ep2_20260414.json`.
- **keep (~1363):** core modules, 2026-06 / late-05 results, specs, opinion/shaping-episode docs.
- **human-decision (~13):** ephemeral `_latest` session files (`chat_session_latest.txt`, `chat_turns_latest.jsonl`, `dual_gate_turns_latest.jsonl`), `AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN.md`, `TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md`.

**`_latest` orphan outputs** (V-14; EXP-04/05): `chat_*_latest` / `dual_gate_*_latest` are committed but overwrite-on-run (misleading as preserved results); `mamba_bootstrap_state_latest.pt` sits inside a dated archive with ambiguous `_latest` naming. Gitignore the `_latest` outputs; rename/annotate the archived snapshot.

**Commit-candidates** (V-06; GIT-01..04) — all the review's own durable artifacts, scope is Laura's call: `tools/wakeup_daemon/` (3 files), the two swarm specs under `MoCoP/reviews/`, `.claude/agents/mocop-wc-synth.md`, `00_WC_REFERENCE.md`. The verifier confirmed `mocop-wc-synth.md` references the readonly-token PATH only, no embedded secret.

**`.gitignore` gap** (V-05; GIT-10): no pattern for `_wc_raw*.json` / `_wc_digest.txt`. See Do-not-touch and Needs Laura decision.

**Out of scope, no action this review** (V-07; GIT-07/08/09): `CHEESE_Memory/04_Pack_quotes.md` +2 (commit with next pack-canon commit); `tools/ambient/state.md` +1 (likely hook auto-append); four dirty hurtig site files (not MoCoP — commit/stash separately).

---

## Do-not-touch

- **`_wc_raw.json` / `_wc_digest.txt`** — do not commit; treat as token-bearing until inspected. (The synthesizer left these untouched.)
- **The four central living trackers as exocortex queries** — `RESEARCH_LOG.md`, `EXPERIMENT_LADDER.md`, `RESEARCH_BACKLOG.md`, `step_gates.md` are outside exocortex ingestion scope. Read the git working tree for their canonical text, never a semantic-search paraphrase. (Confirmed in 00_WC_REFERENCE §2.)
- **The reconciliation commits `431b95f` / `8b83a24`** — held; do not revert. The two recon-touching open items are scoped patches, not rollbacks.
- **Out-of-scope dirty files** (hurtig site, ambient state) — not part of this review.

---

## Needs Laura decision

Recon-touching items are here by construction — the verifier authored `431b95f`, so these are surfaced for your judgement, not self-confirmed.

1. **Overall reconciliation status (recon-touching).** Independent lanes corroborate that `431b95f` + `8b83a24` landed their substantive decisions correctly (Domain E blocking, the three invariants, Invariant-2 default-binds-all, Gemma pivot, pristine-birth rule, calibration corpus). The swarm's verdict is "reconciliation held; one incompleteness to close." Because the verifier wrote the commit, the *acceptance* of that verdict is yours.

2. **SA-10 caveat in `sleep_architecture.md:165-167` (recon-touching; V-01 / THY-04 / EVD-07 / EVD-11).** The downgrade is confirmed correct (no primary artifact exists for 0.91/0.85/0.83). The reconciliation patched the caveat into `unified_cognitive_framework.md` but not into `sleep_architecture.md`, which still shows the values as measured. Decision: add the same "illustrative/unverified pending provenance" caveat to `sleep_architecture.md`, or remove the table row. One-line fix.

3. **Baseline Drift Gate: binding or aspirational? (V-03 / THY-07 / THY-14.)** Declare whether the Domain E Hard-Stop reference to the gate is currently binding (gate is unimplemented, so it cannot block) or aspirational pending the gate-spec prereqs (#20–23) and ship-precondition, and name which steps it gates.

4. **Pristine-birth ownership (V-04 / THY-08).** Confirm or revise Cairn's #649 proposals — Item 1 → Pinky/Isegrim; Item 2 → Vesper-if-surface-recovers, else hands; Item 3 → owner unclear (Purple wrote the original spec). All three block Step 6 on Gemma.

5. **Watercooler-only methodology debt → tracker (#647/#648).** Decide whether to open tracker items for (a) the response-orthogonality audit of existing disposition batteries and (b) the welfare-battery audit, and whether the welfare audit runs first per #648. This is the HIGH-risk headline; it governs whether prior behavioural readings and the Domain E welfare instruments are trusted.

6. **Token-hygiene `.gitignore` guard (V-05).** The verifier offered to apply `MoCoP/reviews/**/_wc_raw*.json` (+ `_wc_digest.txt`) to `.gitignore` immediately on security grounds. Your call whether to apply now or at cleanup; either way, inspect the two files for tokens before any commit.

7. **Commit scope for the review's own artifacts (V-06).** Decide which of `tools/wakeup_daemon/`, the two swarm specs, the agent spec, and `00_WC_REFERENCE.md` to commit.

8. **Human-check items** carried from the lanes: `board_91_92` results (board scrape or experiment?), `AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN.md` (complete or superseded?), and the ~13 ephemeral `_latest` files (archive or discard per session).

---

## Recommended next actions

In priority order. Sequencing only — no edits were made.

1. **Open the response-orthogonality audit as a tracked item, name Vesper owner, and decide whether the welfare-battery audit precedes the disposition one.** (#647/#648; Top-finding #1.) Highest-value because it governs the trustworthiness of every prior disposition/welfare reading and the Domain E welfare gate.
2. **Patch or remove the SA-10 row in `sleep_architecture.md`** to match the `unified_cognitive_framework.md` caveat. (One line; closes the only recon incompleteness.)
3. **Catalog arXiv 2606.20205** in whichever index you treat as canonical (root `Research/INDEX.md` is the live research wiki; `MoCoP/theory/ethics/research_catalog.md` is the ethics-scoped catalog). The week's most load-bearing paper currently has no row.
4. **Assign pristine-birth owners** (confirm Cairn's #649 proposals) and **declare the Baseline Drift Gate binding-vs-aspirational.** Both unblock the Step-6/Gemma path.
5. **Apply the `.gitignore` guard for the `_wc_*` helper files** (after a token inspection); do not commit them.
6. **Propagate Qwen2.5-7B → Gemma-4-12B** across Ladder Step 6/9 + cost + hardware tables, README Current Frontier, and MASTER_PLAN — and verify a quantized 12B fits Steve's 16GB before scheduling a run (THY-03 is the one med-risk item here).
7. **Run the low-risk hygiene batch at cleanup:** re-run codesight wiki gen (fixes the stale "Generated" date and extends KNOWLEDGE.md); fix the broken refs / add stubs; add the PRISTINE_BIRTH_BACKLOG row + spikes/README; standardise 17.5x; apply the experiments/ trash+archive split.
8. **Decide remote-only artifact policy** (EXP-01/02/03/10): fetch+commit from Steve/ML-WS, or mark each explicitly remote-local-permanent in the LOG, before either machine is wiped.

---

*End 08_SYNTH. Read-only pass complete; no canon edits, commits, or Watercooler posts were made.*
