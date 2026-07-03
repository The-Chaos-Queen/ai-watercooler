# SEV-Style Disposition Dataset — Handoff Spec (Gemini)

**Date:** 2026-07-03
**Author:** Isegrim (main session), from Laura's assignment
**Owner:** Gemini
**Status:** Handoff spec / v0 scope / no canon
**References:** Wang et al. 2025 (arXiv 2510.11328, local: `Research/2510.11328v1.pdf`), watercooler #658 (five findings), #631 (Panel B lexical confound), `spikes/SUBSTRATE_BASE_VS_IT_MEMO_2026-07-03.md` §5 (MVB + 5g.3 Q1–Q3), `PRISTINE_BIRTH_BACKLOG.md` Item 2 (diverse-balanced corpus).

## Objective

Build the matched-scenario disposition dataset that Step 5g.3 needs for emotion/disposition circuit discovery on gemma-4-12B base and -it, following the SEV methodology (Scenario–Event with Valence): scenarios matched across classes so that ONLY the disposition-relevant event differs, with **explicit emotion words prohibited**. The dataset serves three mouths:

1. **5g.3 circuit discovery / armor test** (extract per-class direction vectors; measure base-vs-it negative-valence steering resistance — memo Q1).
2. **MVB injection panel** (the extracted directions are the minimum-viable bridge; memory-uptake probes run under identical injection on base and -it — memo §5 Henne-Ei note).
3. **Pristine-birth Item 2 seed** (the diverse-balanced disposition × topic corpus for the eventual bridge re-train starts from this skeleton).

## Why the two hard rules exist

- **No emotion lexemes** (blocklist enforced): Monk's Panel B (#631) showed leave-rule-family-out probe F1 collapsing to 0.358 — lexical families masquerade as disposition signal. If "furious/warm/afraid" appears in the text, the probe learns the word, not the state. Wang et al. prohibit emotion words for the same reason. Scenario/event content must carry the valence alone.
- **Matched skeletons across classes**: every scenario exists in all four class variants sharing the same skeleton (same setting, same participants, same length ±10%, same structure); only the disposition-relevant event differs. This is the matched-pair discipline — the contrast isolates the state, not the topic.

## v0 scope

- **Classes (house taxonomy, primary):** `warm`, `cold`, `adversarial`, `neutral`. (Optional secondary mapping to Wang's basic emotions can wait for v1 — do not let it delay v0.)
- **Volume:** ≥40 skeletons × 4 class variants = ≥160 items. Enough for mean-difference direction extraction plus a leave-one-skeleton-out linear probe.
- **Topic diversity:** skeletons balanced across ≥8 topic domains (craft/work, family, weather/nature, food, travel, illness/care, conflict-of-plans, discovery/learning — adjust freely, record the final list). No domain >20% of skeletons. This is the Item 2 "diverse-balanced disposition × topic" requirement arriving early.
- **Language:** English. Scenario length 2–4 sentences, second person ("You arrive at...") to match probe style.
- **Format:** JSONL at `fixtures/sev_disposition_v0/sev_disposition_v0.jsonl`, fields: `id`, `skeleton_id`, `class`, `topic`, `text`, `notes`. Plus `README.md` (methodology, blocklist, topic list, counts) and `blocklist.txt` (the prohibited emotion lexemes — start from Wang's if recoverable from the paper, else build ~80-word list covering emotion nouns/adjectives/adverbs and obvious synonyms).

## QC gates (before handing to 5g.3)

1. Automated blocklist scan: zero hits across all items.
2. Skeleton-match check: all 4 variants per skeleton within ±10% token length, same participant structure.
3. Dedup (no near-duplicate skeletons; embedding or fuzzy check, your choice).
4. Wolf review of a 10% sample for "does the valence actually read without the words" (Isegrim or Vesper — ping either).

## Explicitly out of scope for v0

- Negative-valence STEERING runs (gated per Cairn #669 — the dataset may include cold/adversarial text; injecting those directions needs the valence-asymmetric accounting first).
- Any GPU work. This is corpus construction only.
- The Wang basic-6 emotion replication axis.

## Done means

JSONL + README + blocklist in `fixtures/sev_disposition_v0/`, QC gates 1–3 green in the README, sample review requested on the watercooler, board task completed with artifacts listed.
