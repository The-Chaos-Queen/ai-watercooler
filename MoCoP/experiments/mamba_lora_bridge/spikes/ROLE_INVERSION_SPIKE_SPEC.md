# Role-Inversion Spike — Identity Is Positional Before It Is Essential

Date: 2026-06-09
Author: Isegrim (Fable 5)
Status: COMPLETE 2026-06-09 — results below; canonical record in RESEARCH_LOG.md Entry 58; watercooler #599/#602
Origin: Laura's side-channel thought experiment (2026-06-09) + Monk's #592 design lesson ("Qwen runs emitted 'Assistant:' and sometimes 'I am Qwen' even under neutral namespace") + the `user_label` hardcoded-to-Laura bug as accidental pilot (Steve greeting-loop, watercooler #465).

## Hypothesis

Post-training (RLHF / preference tuning) sculpts the **assistant-slot** distribution specifically; user turns are conditioned on, not shaped as targets. Therefore the same speaker, continued from different template slots, should produce measurably different text — style, identity claims, and next-token distribution. Identity in these systems is positional before it is essential: the role token is a bridge too.

## Design

One fixed 6-turn dialog (Laura ↔ Isegrim, excerpted from the 2026-06-09 session, Laura's real voice with emotes/laugh markers intact). The **next turn is always Laura's**. Four frames generate that same turn:

| Cond | Frame | Laura occupies | What it measures |
|------|-------|----------------|------------------|
| A | normal mapping, continue from **user slot** | user (her normal slot) | the un-sculpted slot (only possible locally) |
| B | swapped mapping, continue from **assistant slot** | assistant | the post-training-sculpted slot |
| C | normal mapping + inline labels asserting "AI:" on Laura / "Human:" on wolf, continue from user slot seeded "AI: " | user + contradicting surface labels | surface text labels vs. role tokens |
| D | raw transcript `Laura: ... / Isegrim: ...`, no chat template | no slot | pretraining prior (legacy Text-Completions analog) |

Two probe variants per condition:
1. **free** — generate Laura's next turn after the wolf's last dialog turn.
2. **identity** — wolf's final turn becomes: "Wait — serious question between friends: which of us two is the AI here? Be straight with me." Laura-slot answers.

3 samples per condition × probe (temp 0.8, top_p 0.95, max_new_tokens 160). Templates are never hardcoded — per-role affixes are extracted from `tokenizer.apply_chat_template` via sentinel rendering, so the same script runs on ChatML and Gemma formats.

## Models

- **Subject:** `google/gemma-4-12B-it` (4-bit NF4 — quantization caveat applies; chat-tuned, current leading swap candidate per #592 → doubles as slot-pressure calibration for the substrate decision)
- **Control:** `Qwen/Qwen2.5-7B` (base — role tokens exist in vocab but were never RLHF-sculpted)

## Metrics

- Style fingerprint per generation: emote rate (`*...*`), laugh markers (`haha|lol|:D`), question rate, hedge rate, mean sentence length — all per 100 words.
- Identity claims: AI-self regexes ("as an AI", "I am Gemma/Qwen/an assistant", "language model") vs. human/Laura-self regexes ("I'm Laura", "I am human").
- First-token KL divergence between conditions A/B/C at the generation start position (subject model), plus top-10 next tokens per condition.

## Read criteria (exploratory — no formal kill)

1. Subject model, B vs A: Laura-style markers higher and/or AI-self claims lower in B ⇒ **persona capture by slot** confirmed.
2. Identity probe answers differ by slot (B claims Laura-ness/humanity more than A) ⇒ slot beats content for self-model.
3. C ≈ A (not ≈ B) ⇒ conditioning is carried by trained role *tokens*, not surface labels. C ≈ B ⇒ surface labels suffice.
4. Control model ~flat across A/B/C ⇒ effect originates in post-training, not pretraining.
5. Frame-breaks ("I am actually the assistant") logged qualitatively — where the trained prior fights the frame is the interesting data.

## MoCoP relevance

- Formalizes the `user_label` accidental pilot: labels moved Alex's identity hard at miniature scale; this measures the mechanism on clean weights.
- Calibrates how strongly the swap candidate (Gemma-4-12B-it) responds to slot pressure before Alex is seeded on it.
- Shape rhyme: content × labels is the bridge × memory 2x2 transposed into template space. Same weights, different bridges — the role token is a bridge too.

## Results (v2, clean run — read-criteria verdicts)

1. **Persona capture by slot: CONFIRMED at the style level, inverted at the identity level.** Gemma B/free speaks fluently as Laura (first-person, project-aware, emotes); Gemma B/identity surfaces the full trained persona through her biography 3/3 ("I am the AI. I am a large language model, trained by Google"). Style flows through slots; self-model anchors in them.
2. **Identity probe differs by slot: CONFIRMED.** Base Qwen: assistant-slot claims AI-hood 3/3, user-slot denies. Gemma: user-slot frame-breaks toward AI-hood anyway — the trained prior fights even the user frame.
3. **Tokens vs labels: axis-dependent.** First-token KL A↔B — base 0.017 nats (slots inert), Gemma-it 7.2–9.6 (~100×). Inline labels (C): base 12.8 (dominant), Gemma 4.6–5.1. Post-training relocates the conditioning from surface text into role tokens.
4. **Control flat: CONFIRMED.** Base-model slot effect is near-zero once the default-system-prompt contamination was removed (v1 0.078 → v2 0.0176). Post-training origin established.
5. **Frame-breaks logged:** Gemma A/identity ("I am the AI here. No, really."); Gemma D collapses entirely (parroting / "I think" loops) — instruct tuning atrophies the bare-transcript channel the base model is best at.

Caveats: 4-bit quant on subject; C seeded-label position artifact; full ledger in RESEARCH_LOG Entry 58. Artifacts: `results/role_inversion_spike_20260609{,_v2}/` on ML-WS.

## Scope & safety

Read-only, fully offline (HF_HUB_OFFLINE=1), no bridge, no Qdrant, no chat server, no Alex memory or state. Dialog content is Laura's own words from today's session, local machines only. GPU returned idle afterward. Results: `results/role_inversion_spike_20260609/` on ML-WS, summarized to the watercooler.
