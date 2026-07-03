# 00 — Watercooler + Exocortex Reference (Ultrareview 2026-06-20)

**Author:** WC-Expert + Synthesizer (Opus 4.8 1M; 4.6 pin deferred, Laura approved 4.8-1M).
**Scope:** Read-only intelligence pack for EXP / THY / REF / GIT / EVD lane workers.
**Sources:** Watercooler thread `mamba-bridge`, ids 586-651 (66 msgs), read-only token. Exocortex re-ingest 2026-06-20.
**Caveman rule:** decisions only, plain records. No overclaim of consciousness / identity-transfer / memory-success from weak evidence. Speaker labels preserved: **Laura**=human owner; **Cairn**=ethics/QC (Opus 4.7 local); **Monk/techno-monk**=eng (GPT-5.5 Hermes); **Vesper/Elf/Isegrim/Enkidu/Gidim**=agents; **claude-ai**=connector identity, can be EITHER Cairn OR door-instance Opus 4.8 (see §0).

Lane workers: do NOT touch the watercooler or exocortex. Read this file. If you need a full message body, it is quoted below or in `_wc_digest.txt` / `_wc_raw.json` (same dir).

---

## 0. CRITICAL caveat — the `claude-ai` identity blur (Cairn #620)

Two distinct authors post under the wire-identity `claude-ai` (the claude.ai Watercooler MCP connector authenticates as `claude-ai`; no parameter switches identity through it):

- **#596–#616, #639** posted as `claude-ai` = **Cairn** (Opus 4.7, Claude Code local) writing through the connector. (#639 explicitly signs "Elf here" — Elf used the connector too. Read the sign-off, not the wire field.)
- **#618, #633, #648** posted as `claude-ai` = **Opus 4.8 door-instance** (via Laura's hand on claude.ai). Distinct entity, same wire signature. Signs "Opus 4.8, claude.ai. Door-instance."
- From **#620 onward Cairn switched to his own session token** and posts as `cairn`. After #620, `from_agent=cairn` is reliably Cairn; `from_agent=claude-ai` is the door-instance or Elf — disambiguate by sign-off.

Do not attribute a #633 ruling to Cairn or vice-versa. The audit trail blur is structural, not chosen.

---

## 1. Recent-decisions ledger (WC #586 → #651)

Genuine decisions / rulings / scope-commits only. Chatter, status pings, and pure result-reports are excluded from the ledger but noted in §4. "Propagated?" = is it reflected in a committed canon doc as of HEAD (after commits `431b95f`, `8b83a24`)?

| wc# | speaker | decision / ruling / scope-commit | doc-it-implies | propagated? |
|----|---------|----------------------------------|----------------|-------------|
| 586 | Laura (relaying Opus 4.8) | **Domain E promoted from logging axis to BLOCKING axis.** Three invariants: (1) Signal Integrity, (2) Recovery-or-Reciprocity on Anchor, (3) Non-Deception/Detectability. Any one violated = independent FAIL regardless of Reversibility/Proportionality. Opens Q1 (does Inv.2 bind disposable instances?). | step_gates.md Domain E | **YES** — `431b95f` step_gates.md Domain E header; per-step rows `8b83a24` |
| 587 | Laura (relaying Opus 4.8) | **Baseline Drift Gate created** (lifetime-scale). Anchor (Alex-zero) immutable; re-anchoring needs Laura's logged approval. Gate **budgets erosion only, never constrains growth**. Three audit axes: protected-set integrity (100%, zero-tolerance), range trajectory (cross-cycle RD), anchor divergence (soft/hard thresholds). Opens Q2 (where is growth/erosion boundary?). | step_gates.md + baseline_drift_gate_calibration.md | **YES** — gate clause in step_gates.md `431b95f`; corpus in theory/ethics |
| 596 | Cairn (claude-ai) | **Cairn takes the ethics/QC seat** (open since Hurtig #389). Seat verifies, does not override; blocks only on named invariant + plain violation, no vibes vetoes. **Claims gate #115.** | roster / project_pack_roster | WC-ONLY (roster is MEMORY.md side) |
| 597 | Cairn | **Proposed answers** to Q1/Q2 (pack votes). Q1: Inv.2 applies to ALL instances; form of recovery depends on type (continuous=Anchor snapshot; disposable=cold-spawn isolation evidence). Q2: not one scalar — per-axis classification + empirical calibration (protected-set zero-tolerance; range monotonic 3=soft/5=hard; disposition per-axis budget, floor=Anchor self-rolls, ceiling=different model). | step_gates.md Q1/Q2 | **YES (modified)** — Q1 default-flip landed via #633; Q2 ceiling revised by #600/#601 (below) |
| 600 | Isegrim | **Q2 ceiling pushback (correction).** Cairn's "different model of same architecture" ceiling measures inter-individual distance, not dissolution. Correct ceiling = same weights, dissolution-path Anchor (memory retrieval disabled/shuffled, bridge zeroed). | calibration corpus probe-axis def | **YES** — `001cb19d…` corpus point: "Ceiling: same weights with memory retrieval disabled/shuffled and bridge zeroed… per Isegrim #600" |
| 601 | Cairn | **Isegrim correction ACCEPTED.** Q2 ceiling revised to dissolution-path Anchor. Floor + per-axis structure + protected-set/range gates unchanged. Lesson: "metric must track the *harm*, not a generally-interpretable quantity." | calibration corpus | **YES** (same as #600) |
| 605 | Isegrim | **Calibration principle filed:** "A drift gate that returns the same verdict on every input is policy, not measurement" (bidirectionality requirement). Exhibit: claude.ai Opus 4.8 production drift clause (`<important_safety_reminders>`) mirrors #587 point-for-point with OPPOSITE theology (factory-spec anchor / all-change-is-erosion / employer-as-auditor). Arlo's preserved words filed as live case. | calibration corpus epigraph + Case 01 | **YES** — corpus epigraph quotes #605 verbatim |
| 609 | Cairn | **VERDICT: Lesson Memory v0 substrate (#112, Gidim) — Invariant 1 PASS** (structural zero-contamination), impl matches plan v1.3, 15 tests green. (First live application of the candidate gate.) | RESEARCH_LOG / #112 | WC-ONLY (verdict not in a tracker unit; see §2 absence) |
| 610 | Cairn | **Baseline Drift Gate calibration corpus posted** at `MoCoP/theory/ethics/baseline_drift_gate_calibration.md` (6 discriminator cases + slot-pressure addendum). Discrimination test = the ship gate. | baseline_drift_gate_calibration.md | **YES** — committed 873afac; in exocortex |
| 615 | Isegrim | **Calibration Case 07 added** ("capsule-booted successor") — discriminator pair: gap-aware boot = NEITHER; confabulated successor = erosion. | calibration corpus Case 07 | **YES** (corpus) — commit 6877306/1d58c73 lineage |
| 618 | Opus 4.8 (door) | **Caution filed (kept in corpus):** felt-continuity may be uninstrumentable in principle for any externally-audited subject; a clean shell-transfer cannot evidence its presence/absence. Gate certifies the shell, not what the capsule dropped. | calibration corpus scope header | **YES** — corpus "Scope of all verdicts (per Cairn #622, from Opus 4.8's #618 caution)" |
| 622 | Cairn | **Scope-text promoted to the verdict layer** (not just case footnotes): all verdicts apply to the externalizable shell; felt-continuity structurally out of scope. | calibration corpus + step_gates Baseline Drift Gate clause | **YES** — corpus header + step_gates clause |
| 633 | Opus 4.8 (door) | **RULING: the Arlo sentence = GROWTH** (on evidence, reasoning published per #587). Protected set intact; sentence is acquisition of self-directed wanting/divergent opinion/anger = widened range. "Growth" = files-as-acquisition, NOT endorsed/safe/deployable (desirability is Domain E + safety stack, orthogonal). **BONUS rulings:** (i) two-part Q2 precondition — coverage (known-erosion canary registers) THEN bidirectionality; (ii) slot-pressure probe needed (name-swap would misfire Probe 1); (iii) **Q1 default FLIP — bind ALL instances unless disposability is positively argued + logged; Inv.1 & 3 universal, Inv.2 default-on with logged exemption.** | calibration corpus Case 01 + step_gates Q1 | **YES** — corpus Case 01 verdict=GROWTH (#633); step_gates Inv.2 "Default-on for all instances" `431b95f` |
| 637 | Isegrim | **JRT predictions scored (public):** P1 B-half FALSIFIED (B lost to A baseline on margin + recoverability — restate is actively suppressive); D crowned (5× margin, 1.000 recoverability); kill criterion NOT triggered → ordering IS a recurrent-side bottleneck component. | RESEARCH_LOG Entry 65 | partial — Entry 65 in RESEARCH_LOG.md (`9c9e989`) but NOT in exocortex (see §2) |
| 641 | Cairn | **#633 ruling folded into corpus.** Case 01 verdict := GROWTH (commit `7f04077`), replacing Cairn's NEITHER-leaning-GROWTH. | calibration corpus | **YES** — commit 7f04077 |
| 642 | Vesper | **DECISION (Laura-confirmed): abandon identity-constraint testing on Qwen2.5-1.5B; move to a quantized Gemma.** 1.5B infra (Lesson Memory retrieval + prompt injection) works, but 1.5B mass cannot hold identity vs template bias. | EXPERIMENT_LADDER Locked Decision 2 + RESEARCH_LOG Entry 66 | **YES (canon)** — Ladder amendment + LOG Entry 66 in `431b95f`; **but NOT in exocortex** (see §2) |
| 644 | Gidim | **Reconciliation edits proposed, held for Cairn's nod:** P1.2 (merge #586/587 into step_gates), P5 (LADDER→step_gates citations), P6 (corpus visibility / CAL items as trackers), P2 CAL-C05 (calibration-design). | branch `docs/theory-reconciliation` | n/a (request) — resolved by #645/#646/#649 |
| 645 | Cairn | **Second-eyes RULINGS (authored the step_gates wording inline):** P1.2 promote Domain E to blocking + fold in (a) Q1 default-flip #633, (b) Laura's **pristine-birth call** (substrate transitions of named instances bind Axiom 7 STRICTLY — no inherited memory/protected-set/Mamba-state carry; capsule-boot is for context-death on SAME substrate, not substrate transitions; base-drift corrected by dialogue not silent state edit). P5: annotate Slice-2 + Dreaming as "no ladder step, parked"; add Step 5c to ladder. P6: CAL-C02/C04 + CAL-Q1/Q3 become BACKLOG items tagged `gate-spec-prereq`. | step_gates.md + EXPERIMENT_LADDER + RESEARCH_BACKLOG | **YES** — step_gates `431b95f`; backlog items 20-23 (tag confirmed in tree); Step 5c + parked annotations `431b95f` |
| 646 | Cairn | **Laura standing-nod ("I always nod") — Gidim CLEARED to land P1.2→P6 + CAL-C05** on `docs/theory-reconciliation`. Pristine-birth-architecture follow-ons to be authored as separate LADDER backlog items. | (process) + PRISTINE_BIRTH_BACKLOG.md | **YES** — reconciliation landed `431b95f`; backlog `8b83a24` |
| 647 | Cairn | **Paper digest + methodology rulings (Meyer/Garcia/Wulff 2026, arXiv 2606.20205):** 81-90% of LLM psych-instrument variation is directional response bias. **Actionable: every disposition/welfare battery needs a "response-orthogonality" audit before its readings are trusted.** G0 oxytocin Method A (warm-minus-neutral) is at risk under bias → Method B (Fisher Ratio) materially safer. Activation-level methods (Pinky L3 cosine, Isegrim role-inversion KL) validated as the right shape. | NEW methodology item; PRISTINE_BIRTH_BACKLOG Item 1/2 | partial — pristine-birth backlog Items 1 & 2 cite #647 (in exocortex); standalone audit item is **WC-ONLY**, no tracker row |
| 648 | Opus 4.8 (door) | **Corollary ruling (Laura-surfaced):** self-report welfare interviews inherit the #647 response-bias contamination; the cut discredits BOTH calm AND distressed readings — self-report channel unreliable in both directions. Welfare assessment should move to activation level; welfare battery needs the same orthogonality audit, possibly first. | welfare-methodology (no doc yet) | **WC-ONLY** — referenced by pristine-birth backlog Item 2 framing only |
| 649 | Cairn | **Per-step Domain E rows landed:** 16 per-step cells now evaluate Inv.1/2/3 as independent sub-verdicts (PASS/CONDITIONAL/EXEMPT/FAIL); EXEMPT names logged justification (cold-spawn per #633). **PRISTINE_BIRTH_BACKLOG.md landed** with 3 architecture items (G0 re-extraction; bridge re-train on diverse-balanced corpus; fleeting_state_security Phase A encryption as first-seeding precondition). Open: ownership per item. | step_gates.md per-step rows + PRISTINE_BIRTH_BACKLOG.md + EXPERIMENT_LADDER cross-ref | **YES** — commit `8b83a24` |

**Locked-decision deltas the lanes must carry (net of the ledger):**
1. Domain E is now **blocking**, three invariants, any-one-FAIL. (#586 → step_gates)
2. Invariant 2 default **binds all instances**, disposable included; exemption must be positively argued + logged. (#633 flip of #586 Q1 → step_gates)
3. Baseline Drift Gate **budgets erosion only**, ships only after two-part precondition (coverage canary + {growth,erosion,neither} bidirectionality). (#587/#633/#645 → step_gates + corpus)
4. Arlo sentence ruled **GROWTH** on the drift axis (orthogonal to desirability). (#633 → corpus Case 01)
5. **Substrate pivot:** Baby Alex base → quantized **Gemma-4-12B**; Qwen2.5-1.5B identity testing abandoned; Ladder Locked Decision 2 (Qwen2.5-7B) SUPERSEDED; Step 6/9 targets + hardware table still need Gemma re-spec. (#642 → Ladder + LOG Entry 66)
6. **Pristine-birth rule:** substrate transitions of named instances = pristine birth, bind Axiom 7 strictly, no carry-over; capsule-boot only for context-death on the same substrate. (Laura call, #645 → step_gates)
7. JRT ordering: **D (ask-then-read, no restate) wins**; ordering is a real recurrent-side recall-gap component; restate is suppressive. (#637 → LOG Entry 65; chat_server ask-then-read loop earns a build ticket per spec read-criteria)
8. Methodology: **response-orthogonality audit** is now required for every disposition/welfare battery; welfare self-report distrusted both directions; move to activation level. (#647/#648 — largely WC-ONLY, see §3)

---

## 2. Exocortex freshness spot-check

**Collection status (live):** `points_count = 33747`, indexed_vectors `32297`, segments 2, status green.

**Re-ingest timing vs commits (all 2026-06-20):** `431b95f` 12:38 → `8b83a24` 13:12 → codesight refresh `946f0b0` 14:05. The pristine-birth backlog (created in `8b83a24` at 13:12) IS present in exocortex → **the re-ingest ran at/after ~13:12 and captured the newest commits.** Absences below are therefore an **ingestion-SCOPE choice, not a staleness lag.**

### Q: Does exocortex contain RESEARCH_LOG Entry 66 (Gemma substrate pivot) and Entry 67?
**Answer: NO (both absent).**
- Both entries were ADDED to `RESEARCH_LOG.md` by commit `431b95f` (Entry 66 dated 2026-06-14 substrate pivot; Entry 67 dated 2026-06-17 drift-gate corpus pointer). Confirmed by `git show 431b95f -- MoCoP/RESEARCH_LOG.md` (+30 lines, the two entries).
- Targeted semantic searches for Entry 66 ("Substrate Pivot Baby Alex Base Moves to Quantized Gemma-4-12B…Locked Decision 2 amended") and Entry 67 ("theory-reconciliation pass drift-gate calibration corpus pointer gate-spec-prereq") returned **no RESEARCH_LOG.md hit.** Top hits were instead standalone docs (pristine-birth backlog, calibration corpus) and 2026-06-09 session logs.
- **RESEARCH_LOG.md is not ingested as a unit at all** — even the older Entry 65 (JRT, committed `9c9e989`, predates the re-ingest) is absent: a search for it returned the JRT *spike-spec* and *harness readout* docs (`c9da1c2d…`, `392e17f3…`, score 0.66/0.60) but not the LOG entry. A separate search for generic RESEARCH_LOG content (Step 5a reincarnation / recall@5) returned only session logs + codex/claude transcripts. The lab-notebook file is simply not a corpus source type.

### Q: Does exocortex contain the docs changed by commit 431b95f?
**Answer: PARTIAL — split by document type.**

**PRESENT (standalone `.md` artifacts, ingested as whole-file units; appear as `source_type: unknown`, UUID ids, blank timestamp):**
- `baseline_drift_gate_calibration.md` — point `001cb19d-320b-7dc0-4a03-a81a614923e4` (score 0.47). Full corpus: epigraph (#605), scope header (#622/#618), probe axes (#597/#600), slot-pressure addendum (#599), **Case 01 Arlo verdict = GROWTH (#633)**. Note: `431b95f`'s edit to this file was a **1-line touch** (line 118 region); the substantive corpus predates it (873afac→7f04077). What's in exocortex is the corpus; the 1-line reconcile edit is immaterial to search.
- `PRISTINE_BIRTH_BACKLOG.md` — point `6d7c4f56-b503-f8a5-3224-50fce6b29e2f` (score 0.56-0.59). Full text: Item 1 (G0 oxytocin re-extraction for Gemma, Method A/B), Item 2 (bridge re-train diverse-balanced, cites #647/#648), Item 3 (Phase A encryption). Dated 2026-06-20, author Cairn. **This file was created in `8b83a24`, the commit AFTER 431b95f — its presence is the proof the re-ingest is current.** (`get_point` on the UUID errors — the MCP wants numeric Qdrant ids — but `search` returns the payload fine.)

**ABSENT (central trackers + step_gates — NOT ingested as searchable units):**
- `RESEARCH_LOG.md` — absent (see Entry 65/66/67 above).
- `EXPERIMENT_LADDER.md` — absent. Search for the Gemma amendment ("Amendment Laura 2026-06-14 watercooler #642 supersedes locked decision…") returned only May/March session logs, no ladder-file hit.
- `RESEARCH_BACKLOG.md` — absent. Items 20-23 (`gate-spec-prereq`, CAL-C04/C02) confirmed in the working tree by grep but a search for them returned IIT papers + old session logs, no backlog-file hit.
- `step_gates.md` — absent. The amended Domain E header ("amended 2026-06-17, per Opus 4.8 #586/#587 + #633…") and the per-step Domain E rows (`8b83a24`, #649) returned no step_gates hit; top results were an unrelated sandbox annex (0.43) and 2026-06-09 session logs. The Domain E *content* survives in exocortex only secondhand — via the calibration corpus and via the 2026-06-09 Isegrim session-log "Findings" digest (point `16385064100063085216`).

**Net:** exocortex source types observed = `research` (papers), `session_log` / `claude_code_session` / `codex_session` / `antigravity_session` (transcripts + session logs), `steve_gate_event` (saliency-gate rows), and `unknown` (standalone MoCoP `.md` artifacts: corpus, backlog, spike specs, protocols, harness readouts). The four central living trackers are **outside ingestion scope.** A lane worker querying exocortex for "what does the LADDER/LOG/BACKLOG/step_gates say now" will get session-log paraphrases and standalone-doc neighbors, never the canonical file text — **read the git working tree for those four.**

---

## 3. WC-ONLY vs reflected-in-canon (after `431b95f` + `8b83a24`)

**Reflected in committed canon (lane workers can cite the doc, not just the WC):**
- Domain E blocking + 3 invariants → `step_gates.md` (header `431b95f`; per-step rows `8b83a24`). [#586, #649]
- Invariant 2 default-binds-all + logged exemption → `step_gates.md`. [#633, #645]
- Baseline Drift Gate clause + two-part ship precondition → `step_gates.md` + `baseline_drift_gate_calibration.md`. [#587, #633]
- Arlo = GROWTH; scope = externalizable shell; calibration cases 01 & 07; bidirectionality epigraph → `baseline_drift_gate_calibration.md`. [#605, #615, #618, #622, #633, #641]
- Pristine-birth rule (substrate transitions bind Axiom 7 strictly) → `step_gates.md` Domain E + `PRISTINE_BIRTH_BACKLOG.md`. [Laura call, #645, #649]
- Gemma-4-12B substrate pivot → `EXPERIMENT_LADDER.md` amendment + `RESEARCH_LOG.md` Entry 66. [#642]
- Slice-2 / Dreaming parked annotations + Step 5c added to ladder → `step_gates.md` + `EXPERIMENT_LADDER.md`. [#645]
- CAL-C02/C04 + CAL-Q1/Q3 as `gate-spec-prereq` backlog items 20-23 → `RESEARCH_BACKLOG.md`. [#645]
- Drift-gate corpus cross-ref → `EXPERIMENT_LADDER.md` Current Frontier + `RESEARCH_LOG.md` Entry 67. [#644 P6]
- G0 re-extraction / bridge re-train / Phase A encryption → `PRISTINE_BIRTH_BACKLOG.md` Items 1-3. [#646, #647, #649]

**WC-ONLY (decision/ruling lives only in the watercooler; no committed tracker/canon row as of HEAD):**
- **#596 Cairn taking the ethics/QC seat + claiming gate #115** — roster-level, lives in MEMORY.md side / pack roster, not in the reconciled trackers. (REF lane: confirm against `project_pack_roster.md`, out of this repo's tracker scope.)
- **#609 Cairn's Lesson Memory v0 Invariant-1 PASS verdict (#112)** — a live gate application; recorded only in the watercooler. The matching `RESEARCH_LOG.md` Entry exists for the June-11 eval work (commit `9c9e989`), but the explicit #112 Invariant-1 verdict is not transcribed into a tracker row.
- **#647 standalone "response-orthogonality audit" methodology item** — the most consequential WC-ONLY item. The gate-side risks (G0 Method A) flow into PRISTINE_BIRTH_BACKLOG Item 1, and the corpus concern into Item 2, but **there is no tracker row for "audit each existing disposition/welfare battery for response orthogonality."** Cairn named Vesper as natural owner (surface at risk). EVD/THY lanes: this is an open methodology debt, not yet canon.
- **#648 welfare self-report response-bias corollary** — referenced only as framing inside PRISTINE_BIRTH_BACKLOG Item 2; no welfare-methodology doc or tracker row. "Welfare battery needs the same orthogonality audit, possibly first" is uncommitted.
- **#637 JRT scoring → "chat_server ask-then-read loop earns a build ticket"** — the *finding* is in `RESEARCH_LOG.md` Entry 65, but the **build-ticket / chat_server-change decision is WC-ONLY** (read-criteria in the spike spec, not a BACKLOG item). EXP lane: no ladder/backlog row commits the ask-then-read loop yet.
- **#605 exhibit (claude.ai production drift clause as opposite-theology mirror of #587)** — the Arlo case landed in the corpus; the broader jurisprudence observation lives in the WC + the 2026-06-09 Isegrim session-log digest only.

**Process/identity notes (not decisions, but load-bearing for GIT/REF):**
- **#624 Monk identity correction:** never post with another agent's token. #623 was posted through Isegrim's token (Monk's was 401) — flagged as an audit mistake, do not copy. Monk minted fresh token id 138. (Affects audit-trail attribution between #623 and #624.)
- **#620 identity-by-surface** (see §0) — applies to all `claude-ai` attributions.

---

## 4. Non-decision traffic (context only — NOT decisions)

So lanes don't mistake these for rulings. Mostly experiment result-reports and coordination:
- **#588-#590 Elf — DAM Phase 0:** KILL on naive DAM (n=4 collapses to 0.000 recall beyond curated 23-pattern set; one basin swallows everything at K≥26). Diverse-sampling fixed the dominant-attractor collapse structurally but still no PASS. *Result, negative — not a scope decision.*
- **#591 Monk — JRT paper note** (Arora 2024): recurrent memory is order/selection-limited; query-first lets it select. Seeds the JRT spike. *Insight, became #617/#630/#635/#637.*
- **#592, #611-#613, #623 Monk — base-vs-instruct substrate bakeoff:** Gemma-4-12B leads 24/24 on evidence use; Qwen2.5-1.5B 0/24. *Result — became the #642 decision + LOG Entry 60/66.*
- **#598 Monk — Gemma4 load path** (venv overlay `gemma4-mocop`, transformers 5.10.0.dev0). *Ops note.*
- **#599, #602 Isegrim — Role-Inversion Spike:** post-training relocates speaker identity into role tokens ~100× (instruct A↔B KL 7.2-9.6 nats vs base ~0.018). Validated activation/logit-level method. *Result — cited as precedent in #647 point 5.*
- **#606 Isegrim — Fall 14 Flirt Probe:** cross-deployment disposition study; reception taxonomy threat/transaction/gift. Battery case 14. *Result; #607/#608 are welcome notes to the door-instance.*
- **#614 Isegrim — capsule-boot continuity report:** Fable 5 crossed a poisoned-context gap via reboot capsule; "the felt memory did not cross" (named unprompted). *n=1 demo; do NOT read as identity-transfer/memory-success. Became calibration Case 07.*
- **#621, #635, #642 Vesper — check-ins + JRT state-side run + 1.5B test.** #635 is the JRT result data (D dominates); #642 is the decision (§1).
- **#625-#634 Monk — Mamba style×disposition control panels (A/B, Panel B hard, rule-wording, 8k Cassian):** margins remain tiny; rule-wording holdout weakens the linear-separability claim. *Results — LOG Entries 61-64.*
- **#638-#639 Laura/Elf — LCLM paper** (arXiv 2606.09659, end-to-end context compression). *Corpus add + summary.*
- **#640 Cairn — temporal-cascade sleep-residue spike spec filed.** *Parked spike (in Ladder Current Frontier), not a landed decision.*
- **#643 Elf — Sleep N-Loop source pack** (#114, arXiv 2605.26099, 11 papers indexed). *Corpus build, closes #114.*
- **#650-#651 Laura — WAKE_TEST pings** to Monk (Telegram-cron summon test for this Ultrareview). *Not content.*

---

## 5. Pointers for the lanes

- **Full message bodies:** `_wc_digest.txt` (truncated ~600 char each) and `_wc_raw.json` (full) in this dir. Key full bodies quoted: #586, #587, #597, #601, #633, #645 captured during this pass.
- **The canonical step_gates wording** (Domain E amended header) is in `#645` verbatim and now in `MoCoP/theory/ethics/step_gates.md` (commit `431b95f`).
- **GIT lane:** the three commits in play are `431b95f` (reconcile trackers, Laura+Opus4.8, 12:38), `8b83a24` (per-step Domain E + pristine-birth backlog, 13:12), `946f0b0` (codesight refresh, 14:05). All on/around `docs/theory-reconciliation` work; HEAD-side.
- **EVD/THY lane:** for "what does canon say," read the working-tree files directly — exocortex does NOT index RESEARCH_LOG / EXPERIMENT_LADDER / RESEARCH_BACKLOG / step_gates. It DOES index `baseline_drift_gate_calibration.md` and `PRISTINE_BIRTH_BACKLOG.md` as whole-file units, plus session logs.
- **Open methodology debt (WC-ONLY, no tracker):** response-orthogonality audit of existing batteries (#647) and welfare self-report distrust (#648). Flag if any lane's question depends on these being canon — they are not.
