# MoCoP Ultrareview 2026-06-20 — Decision Index (entry point)

Read-only review complete. Nothing committed to canon. Verifier = Gidim / Opus 4.8 (authored reconciliation 431b95f; recon-touching items below are findings for Laura, not self-confirmed).

## The package (`MoCoP/reviews/ultrareview_2026-06-20/`)
- `08_SYNTH.md` — full human-readable review
- `07_VER.md` — verifier verdicts V-01..V-07
- `01_EXP.md` + `experiments_map.md` — experiments/ audit + 1633-file classification
- `02_THY` / `03_REF` / `05_GIT` / `06_EVD` — lane reports
- `00_WC_REFERENCE.md` — watercooler ledger (#586-651) + exocortex freshness
- `V02_response_bias_deepdive.md` — the #1 finding fleshed out
- `V03_domainE_readiness.md` — Domain E gate readiness + critical path
- `experiments_tidy_plan.md` — execution-ready cleanup

## Decision queue

### A. Mechanical — Gidim executes on a one-word go (these are edits, beyond the read-only scope of the review)
- **A1 SECURITY:** untrack + gitignore the WC token-risk helpers (`_wc_raw.json`, `_wc_digest.txt`) and the 3 tracked `_latest` files. [tidy plan §3, V-05]
- **A2 RECON gap:** one-line SA-10 caveat into `sleep_architecture.md:165-167`. [V-01]
- **A3 MERGE:** reconciliation branch (431b95f + 8b83a24 + 946f0b0) -> master, A2 folded in first. [Phase 4]
- **A4 CLEANUP:** tidy plan (157 trash, 25 archive) + doc-hygiene (broken refs V-10, codesight regen V-09, stale indexes V-11/12, Qwen->Gemma doc updates V-08). [tidy + V-08..16]

### B. Your call (+ Cairn) — judgment, not mechanical
- **B1 V-02 welfare-bias (HIGH):** catalog arXiv 2606.20205; clarify how Step-5d logged "distress=0"; assign welfare-audit ownership (Vesper's surface is the flagged risk); open tracker items now vs fold into Gemma prep. The distress-self-report channel in Domain E Inv.1 may be largely noise.
- **B2 Domain E status (resolved by V-03):** the 3-invariant Hard-Stop is binding TODAY via human/reviewer sign-off; the Baseline Drift Gate is aspirational (zero code; prereqs #20-23 + calibration Qs 1-4 open). No action, just the operating reality.
- **B3 GEMMA seeding (the live gating decision):** pristine-birth seeding CAN proceed under Hard-Stop protocol without the Drift Gate, IF Cairn explicitly acknowledges in the gate assessment (a) no certified Anchor-zero baseline exists yet, and (b) Inv.1's distress channel is structurally noisy (#648), AND the session log is written to serve as retroactive Anchor-zero. [V-03]
- **B4 OWNERS:** assign PRISTINE_BIRTH_BACKLOG items 1-3 (unassigned; blocks seeding). [V-04]

## Critical path to a real, binding Drift Gate (from V-03)
0C replace distress-self-report with activation-level welfare monitoring (ties to V-02; activation-level evidence is uncontaminated) -> 0A/0B threshold definitions (calibration Qs 1-2) -> 1A/1B slot-pressure probe battery + attribute-matcher (#20-21) -> 2A/2B coverage + bidirectionality certification on the Gemma substrate.

## What stands (V-02 + EVD confirmed, not in question)
All activation-level evidence: L3 cos 0.092, 17.5x PPL channel, hidden-vs-ssm 0.018/0.8, role-inversion KL, reincarnation (n=3 overfit, already caveated). The response-bias contamination is bounded to the self-report / questionnaire layer; it does not touch the bridge's foundational results.
