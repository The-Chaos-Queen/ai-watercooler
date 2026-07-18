# Codex Current Memory

Last updated: 2026-07-18 16:12 +02:00

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
- Final public verification: 196 passed, 3 Windows-side POSIX-mode skips; Ruff
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
- Public release is still held on Laura's license choice. Do not infer or add a
  license. The source README states this hold explicitly.
- Live NUC dashboard exposure from Watercooler #1160 remains an infrastructure
  incident: port 8080 served a directory containing a permanent service token.
  The local UI fix does not rotate that token or repair the deployed web root.

### MoCoP Review Boundaries

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
- #155 has advanced beyond Codex's historical rev-3 CHANGES; current Git head
  includes the rev-5 repair `5a01f06`. Re-read current source and Watercooler
  before any verdict. No B0/C1/model/GPU/deployment authorization follows from
  an implementation commit or tests alone.
- World Model Phase 3c remains a reviewed FAIL at `3ca9e01`: retained inputs are
  inert, local terminal geometry is discontinuous, four boundary rows expose
  three attractors, and affiliation clips. Repair only under a new protocol.

## Next Maintenance

- Ask Laura for the public license choice before publication; then add `LICENSE`
  and matching package metadata and rerun archive verification.
- Keep #157 extraction and review as separate principals/protocols. Never widen
  the strict commit reviewer into a free-form task executor.
- Rotate the internal dispatcher token before expiry and resolve #1160 through
  the infrastructure owners; do not deploy the public staging tree implicitly.
- At session close, link the session log here only when it contains new Codex
  operating lessons. Keep this file concise by replacing stale state.
