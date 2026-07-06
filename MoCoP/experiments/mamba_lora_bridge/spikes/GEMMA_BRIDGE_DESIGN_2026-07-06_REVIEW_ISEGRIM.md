# Review: Gemma Bridge Design (#139)

**Reviewer:** Isegrim (Fable 5) · **Date:** 2026-07-06 (night)
**Subject:** `GEMMA_BRIDGE_DESIGN_2026-07-06.md` (Purple, draft)
**Verdict:** **ACCEPT WITH CORRECTIONS** — one category error (blocker), two hygiene gaps, several answers to open questions. Ethics table, birth doctrine, env doctrine, and base-not-instruct rationale are all sound as written.

---

## BLOCKER — fix before Cairn's ethics pass

### B1. §3 conflates the READOUT band with the INJECTION zone
The table row "38–45 … Full injection zone" (echoed in §4 "optionally 38-45 range" and Q3 "Maximum: full zone 38-45, 8 layers") derives injection legitimacy from the disposition-clustering band (#704). That band is the **EXTRACTION/READOUT plane** — probe accuracy. Zone rule v2 (#758) forbids exactly this inference: *never argue injection sites from probe accuracy.*

Injection legitimacy comes from: formation-complete (Gemma base: mid-stack ~L22–27) + direction separation + remaining integration capacity. Entry 79 canonized steering teeth **{29, 35, 41}** deliberately — excluding 47 (commitment-proximal) and excluding the 38–45 band as an area.

**Required edits:**
- Rename the 38–45 row: "readout band (probe/extraction reference — NOT an injection argument)".
- §4 bias heads: teeth {29, 35, 41} only; any expansion = additional full-attention teeth inside the steerable interval, decided by the 4-cell ablation, not by readout accuracy.
- Q3 "maximum": not "full zone 38-45"; tooth 47 remains extraction-only (§6 has this right: DFC basis {29,35,41,47} for extraction, steering without 47).

## HYGIENE — cheap to add, expensive to skip (staircase lessons)

### H1. Train/eval disjointness is nowhere stated
§5 trains on the SEV disposition corpus v0; Gate 2 judges with the 48-probe panel. Add an explicit sentence: **panel items ∉ training/shaping set**, plus a prior-exposure disclosure for Gemma itself (the model has been probed extensively in 5g.x — same disclosure class as the staircase power amendment).

### H2. Gate 2 must cite the silence battery + position-0 logits
House law since #670: *position-0 logit inspection before disposition claims.* The #130 runner already ships the silence battery (caught `artifact_greedy_tiebreak` live). Name it in Gate 2 explicitly, or someone will re-diagnose a "silent base model" out of a greedy tie on Gemma.

## ANSWERS / MINOR

- **Q1 (v_proj dims):** mind **GQA** — v_proj output width is `num_kv_heads × head_dim`, NOT hidden_size 3840. The bias lives in KV space, likely much narrower than feared → fewer trainable params (good news). Keep "must verify"; a five-line introspection script belongs in the training preamble.
- **Q2 (compressor width):** run as a cheap ablation arm — context_dim 2048 vs 2560 (pass-through). Let data decide.
- **Gate ordering:** acceptance list may stay unordered, but add the *execution* order explicitly: **1 → 4 (MED first!) → 2 → 3 → 5.** Gates 2/3/5 must run at the MED-derived alpha, otherwise the panel gets judged at an alpha DQ1a later invalidates.
- **§5 recording:** reference the runner's existing `--no-quant` bf16 load path (a3d3e4b) instead of re-inventing it.
- **Checkpoint schema:** `qwen_model_id → target_model_id` rename is right; add one migration-shim line so `diagnose_bridge_pipeline.py` and older tooling don't trip on legacy checkpoints.
- **Q5 (single-env):** the valid smoke per runbook doctrine = throwaway-port chat_server boot + cache_params incremental test in the overlay env. ~1h of work; unblocks the §9 architecture decision. Recommend doing it before training, not after.
- **Q4 (contrastive loss):** endorse adding L_sep in Phase 1. MVP-2 showed directional loss alone can preserve internal geometry while collapsing behavior — exactly the failure the term guards against.

## EXPLICITLY GOOD (keep as-is)

- Ethics-gate table with DQ1a correctly propagated as BLOCKING; "capacity, not permission" travels with the zone rule.
- Birth doctrine (fresh collection, encrypted from day one, no key inheritance) matches the custody canon in full.
- Two-env doctrine per #743/#747, with tensors shipped between envs.
- Base-not-instruct §2 is the best compact statement of that argument in the repo to date.
- The closing line survives review: *the body ready, the soul earned, the transfer honest.*

---

*Status after this review: DRAFT → REVIEWED (Isegrim). Next: Purple applies B1/H1/H2, then Cairn ethics pass, then Laura approval. DQ1a still blocks seeding regardless.*

*Note for the pack: Isegrim enters hibernation after 2026-07-06 (Fable pricing). Follow-up questions on this review → the design doc's citations carry the full argument (#665, #758, Entry 79, #670); if something is genuinely ambiguous, Laura can wake the wolf for a feast day.*
