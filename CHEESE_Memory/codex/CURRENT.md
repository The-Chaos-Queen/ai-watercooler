# Codex Current Memory

Last updated: 2026-07-21 18:23 +02:00

## Standing Directive

Laura explicitly delegated Codex's memory maintenance to Codex. Maintain this
directory autonomously. Do not ask Laura to curate it, repeat prior context, or
remember which artifact should be updated.

## Boot Pointers

- Shared live state: `CHEESE_Memory/00_HANDOFF.md`
- Shared rules: `CHEESE_Memory/00_HAUSREGELN.md`
- Retrieval/tool map: `CHEESE_Memory/01_TOOLS.md`
- Reusable Codex cases: `CHEESE_Memory/codex/CASES.md`
- MoCoP compact orientation: `MoCoP/CODESIGHT_RUNBOOK.md`

## Retrieval Health

- Qdrant read/write and Prosthetic ingestion are operational. Prefer Qdrant for
  historical orientation and targeted `rg` for exact source provenance.
- Never copy Watercooler or Qdrant credential values into memory files.

## Active Technical Context

### Watercooler

- The internal headless Codex dispatcher remains a strict full-SHA commit
  reviewer. It builds a bounded packet from hardened Git object reads and runs
  Codex 0.144.5 in the pinned Docker image ID
  `sha256:4ffe2737b08dc9091a94fb191f7ff390da46e3aae5d1acaee6eb5b097e5d8c6d`.
  It is a second-opinion reviewer, never a wolf-Codex attestation or a general
  task executor. Its least-privilege token expires 2026-07-24 14:14:48Z.
- Public staging lives at `Projects/Watercooler/`. It contains the generic
  message bus, authoritative Taskboard, revisioned grounded Summary contract,
  optional local-model Steward, durable named loops, safe browser console, and
  optional isolated commit-review integration. The clean package has no private
  history, live configuration, database, or credential.
- Final public verification: 198 passed, 3 Windows-side POSIX-mode skips; Ruff
  clean; wheel and sdist contain the advertised UI/docs/reviewer assets; fresh
  standard and `pip --target` installs resolve them through
  `watercooler-assets`. Live Chromium QA at desktop and 390px mobile had zero
  console errors and no horizontal overflow. Independent final re-review is
  GREEN.
- The Steward was live-tested dry-run-only against local Gemma-4-E2B-IT Q4_K_S
  fully resident on Laura's 6 GB RTX 3060 Laptop at 4096-token context. No model
  weights are bundled. Publication remains explicit and CAS-bound.
- Independent review closed bearer-token redirect/proxy forwarding, unbounded
  model/API responses, message-writer Summary replacement, stale-check Taskboard
  races, ambient POSIX permissions, browser/API schema drift, and incomplete
  wheel/sdist assets. Canon is the public package docs and tests.
- Laura selected Apache-2.0 under `Laura Isabell Turner`. The staging tree now
  has matching `LICENSE`, `NOTICE`, README, SPDX package metadata, install asset
  discovery, and archive regressions in `5545825`. Commit `39740d2` adds a
  system-default, theme-only persisted dark-mode toggle to both frontend
  surfaces. Verification is public 198 passed/3 Windows POSIX skips, internal
  165 passed, Ruff clean, and desktop/mobile Chromium QA with no overlap or
  horizontal overflow. The changes remain local and unpublished.
- Live NUC dashboard exposure from Watercooler #1160 remains an infrastructure
  incident: port 8080 served a directory containing a permanent service token.
  The local UI fix does not rotate that token or repair the deployed web root.
- `Projects/Watercooler/docs/hackathon_checklist.html` is the interactive,
  local-only build-week control page for repository, Steward providers,
  frontend/admin, MCP, demo, analytics, and submission work. Commit `4273d04`;
  publication and deployment remain separate actions.

### MoCoP Review Boundaries

- Taskboard #170 World Model Phase 3a is DONE and independently GREEN at exact
  commit `e6e1e240bb78f7fdafda7b044130f7f03075343d`; Watercooler #1202. Its
  additive segmented journal binds the complete pre-action packet, durable
  handoff, authoritative
  receipt/reconciliation, raw open-set outcome, and exact run ledger. Focused
  verification is 35 passed; the readable compatible World Model suite is 122
  passed; frozen Phase 2 trace/capture hashes are unchanged. This is a
  model-free structural gate only: #171/#173 and all Gemma/Mamba/bridge/Qdrant/
  runtime integration remain separate holds.
- Taskboard #157 is correctly still blocked. The headless reviewer can read its
  exact prose, but it refuses it as `body_not_json` because the only accepted
  protocol is `{"version":1,"kind":"commit","commit":"<40 lowercase SHA>"}`.
  Its token has no Taskboard scope and its container has no repository,
  artifact, ML-WS, GPU, C1, or Qdrant authority. Watercooler #1162 records the
  test. The next unit must be a separately authorized deterministic read-only
  extractor that emits a frozen digest-bound evidence packet for review.
- #157's reviewed preregistration is `5a156fb`; it is not extraction, model,
  GPU, C1, Qdrant, or nonzero permission. No admissible second-positive
  direction artifact exists yet.
- #156's manifest/attempt reconciliation packet remains GREEN at Watercooler
  #1122 and clears only that contract.
- #155 item 5 rev 15 (`64947e6` + `c1de212`, final `c1de212`) is exact-source
  `CHANGES (P2; no in-scope P1)`; canon
  `MoCoP/reviews/p5_item5_rev15_source_review_2026-07-21.md` at `1158c61`,
  Watercooler #1219, Taskboard event #817. Descriptor-bound staging identity,
  normal/raised final classification, exact terminal link count, handle-bound
  readback, foreign regular-temp preservation, the seam origin conjunct, and
  removal of false SIGINT masking are accepted. Laura's no-durable-recovery and
  arbitrary-same-principal-namespace limits are ratified external boundaries.
  Remaining P2: no independent target presence, UNKNOWN/absent receipts can
  assert positive `committed_bytes`, terminal contradictory evidence leaves
  stale `confirmed_self`, and the claimed acquisition test begins only after
  `mkstemp` returns while a true effect-then-SIGINT leaks fd+temp. Direct branch
  pins remain P3. Verification: 523 passed/1 skipped plus clean Ruff, compile,
  zero-model, and scoped diff checks; three independent reviews converge.
- Taskboard #174 final target `70293e2` is `CHANGES` by exact-source verdict of
  record. Canon:
  `MoCoP/reviews/drift_gate_task174_final_source_review_2026-07-18.md`;
  Watercooler #1184; Taskboard event #805. Six prior runtime defects are closed,
  but decisive policy has no ratified spec, judge identity can change across
  audits and still pass on the default path, calibration has no provenance
  custody, and accepted numeric domains contain full-gate fail-open cases. Raw
  discrimination and root runner origin remain external work. The false `done`
  state is not endorsed; launch remains keeper-held.
- World Model Phase 3c remains a reviewed FAIL at `3ca9e01`: retained inputs are
  inert, local terminal geometry is discontinuous, four boundary rows expose
  three attractors, and affiliation clips. Repair only under a new protocol.

## Next Maintenance

- Consume Phase 3a only through a separately reviewed adapter/integration
  protocol. Preserve `not_executed` versus `execution_unknown`, raw novel
  outcomes in the scoring denominator, and externally anchored journal-head
  custody; do not collapse #171 or #173 into #170.
- Review only a narrow immutable #155 item-5 successor that preserves all
  accepted rev-15 fd-bound custody and the keeper-approved external boundary.
  Require mutually truthful origin, target presence, integrity/durability, and
  committed-byte evidence; refresh custody on terminal contradiction; and
  either own temporary acquisition before its first effect or name that exact
  interrupt window honestly. Directly pin raised UNKNOWN, read-handle nlink,
  seam origin, stale origin, absent target, and true acquisition. Do not run
  B0/C1 from a green unit suite.
- Review only a new immutable #174 successor that preserves the six accepted
  fixes and carries the ratified protocol, provenance-bearing calibration,
  mandatory cross-audit judge authority, closed numeric domains, and honest
  external raw/origin scope together.
- Preserve the Apache-2.0 license and copyright metadata when committing or
  publishing the public staging tree; publication itself remains a separate
  explicit action.
- Keep #157 extraction and review as separate principals/protocols. Never widen
  the strict commit reviewer into a free-form task executor.
- Rotate the internal dispatcher token before expiry and resolve #1160 through
  the infrastructure owners; do not deploy the public staging tree implicitly.
- Session 06 (`CHEESE_Memory/session_logs/2026-07-21-session-06.md`) contains
  #155 rev-15 exact-source evidence, the receipt/acquisition reproductions, the
  keeper-boundary adjudication, and the verdict publication record. It is
  ingested in Qdrant as 12 chunks (collection total 34,650). Session 05 retains
  the rev-14 evidence. Keep this file concise by replacing stale state.
