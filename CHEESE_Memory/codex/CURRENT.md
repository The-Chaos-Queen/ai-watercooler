# Codex Current Memory

Last updated: 2026-07-18 22:17 +02:00

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
- #155 item 5 rev 6 (`a0bdec6` + `1ec8284`) is `CHANGES` by exact-source
  verdict of record. Canon:
  `MoCoP/reviews/p5_item5_rev6_source_review_2026-07-18.md`; Watercooler
  `#1187`; Taskboard event #806. F2 generation-corpus binding is closed, but
  canonical-parent authority, recursive snapshot custody, and final-readback /
  writable-alias ordering remain P1-blocking. Public row identity, caller
  pair-ID handling, the zero/one-eligible `INCOMPLETE` outcome, and exact
  key/schema/numeric totality remain P2. No B0/C1/model/GPU/deployment
  authorization follows from the repair or its 438-pass suite.
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

- Review only a new immutable #155 item-5 repair that closes the complete rev-6
  public-boundary matrix together. Preserve eligibility and F2 corpus
  re-derivation; do not accept another one-finding patch or run B0/C1 from a
  green unit suite.
- Review only a new immutable #174 successor that preserves the six accepted
  fixes and carries the ratified protocol, provenance-bearing calibration,
  mandatory cross-audit judge authority, closed numeric domains, and honest
  external raw/origin scope together.
- Ask Laura for the public license choice before publication; then add `LICENSE`
  and matching package metadata and rerun archive verification.
- Keep #157 extraction and review as separate principals/protocols. Never widen
  the strict commit reviewer into a free-form task executor.
- Rotate the internal dispatcher token before expiry and resolve #1160 through
  the infrastructure owners; do not deploy the public staging tree implicitly.
- Session 07 (`CHEESE_Memory/session_logs/2026-07-18-session-07.md`) contains
  the recursive-container and publication-order custody lesson. Keep this file
  concise by replacing stale state.
