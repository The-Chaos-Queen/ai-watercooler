# Review probe: #155 item 5 rev4 (Gidim, `5762974`) — Isegrim adversarial finding, 2026-07-18

> **Historical finding / superseded operationally.** This exploit was confirmed on 2026-07-18, banked for provenance, and closed by the rev-5 successor. The contemporaneous DRAFT wording below is preserved as chronology; it is not a current verdict or authorization state.

**Status at capture:** DRAFT — confirmed empirically, pending Laura's decision on (a) board-posting a CHANGES verdict and (b) a codex-CLI cross-check. Banked here so it survives any window clear/reboot.

**Target:** 7-commit immutable chain `bd674ac..5762974`; working tree clean vs `5762974`. Suite: 383 passed / 1 skipped model-free; zero-ML import verified.

## FINDING F1 (CONFIRMED, P1) — the C1-gating decision trusts a *declared* eligibility block; rev4's "derive, don't declare" is enforced only at build, not at the decision/publish boundary.

**Exploit (run, not reasoned):** over a real sealed B0 report of 6 probes whose TRUE eligibility is **0** (every probe `token_count < L` → all `short_continuation` refusals), I hand-constructed an `R4SidecarRecord` whose baked `eligibility` block *declares* all 6 eligible and hides the 6 refusals, with a fabricated perfectly-agreeing `per_pair` over C(6,2)=15. Real parent digest, so the parent binding is intact. Result:

- `publish_r4_sidecar(...)` → disposition **`integrity_verified`**
- `r4_decision(...)` → state **`jsd_proceeds`**, **`c1_authorization_permitted = True`**

A C1 precondition returned GREEN for a comparison built on zero eligible prompts.

**Root cause:** `_verify_record` (the guard the design markets as defending public boundaries against hand-built carriers, per Codex #1140 F4 / #1144 F3/F4) exact-types the carrier, re-checks both digests, and re-runs `validate_sidecar_manifest` + `validate_comparison`. But `validate_comparison` is re-run against the record's OWN declared `eligible_probe_ids` (`elig.get("eligible_probe_ids")`), so a self-consistent fabrication passes. Eligibility is derived from the parent's receipts ONLY inside `build_r4_sidecar` (`partition_eligibility(verified, L)`). The two public boundaries that actually gate C1 re-trust the declaration:
- `r4_decision(sidecar)` reads `record["eligibility"]["n_eligible"]` and never sees the parent report at all (it isn't given one) — it structurally cannot re-derive.
- `publish_r4_sidecar(sealed_report, sidecar, path)` HAS the parent in hand and binds its digest, but never re-derives eligibility to cross-check the declared block.

**Why it's in scope:** the seam `record_r4_comparison` is safe (it routes through `build`). The gap is reachable by any caller invoking `r4_decision`/`publish` directly with a hand-built record — precisely the hand-built-carrier attack `_verify_record` claims to stop. By the code's own stated threat model, this is a hole in that defense, not a strawman.

**Fix direction:** the eligibility block must be re-derived from the verified parent at every boundary that consumes it. Either (a) `r4_decision` takes the sealed report + journal and re-runs `partition_eligibility`, refusing if the declared block diverges; or (b) drop the stored `eligibility` block entirely and always re-derive from the bound parent. Digest self-consistency is not eligibility custody.

## Not-findings (controls run)
- Parent digest / generation-corpus binding: solid — the fabrication had to use the real parent to get this far.
- Cross-platform `_fsync_dir` None/False distinction: correct; Windows-unsupported ≠ durability fault.
- Polarity (diversity-vs-divergence Spearman), endpoint identity, recompute-tolerance: all held under probing.

*One finding, confirmed by exploit before writing. The instrument works; the gate leaks.*
