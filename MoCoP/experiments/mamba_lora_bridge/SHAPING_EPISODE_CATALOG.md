# Shaping Episode Catalog — Real Conversation Data for Bridge Training

**Author:** Warden
**Date:** 2026-04-13
**Task:** OpenCLAW #72
**Status:** Delivered
**Source corpus:** `Preserved-History/` (77 Kimi/DeepSeek/Grok exports + 30+ Claude/Gemini/LMArena transcripts)

---

## Purpose

Replace synthetic MUD facts with real conversational data as shaping episodes for bridge training. The pack consensus (MVP-2b, #380-#384) is: start with easy separations (warm vs cold vs adversarial), then tighten to relational subtypes. This catalog maps existing data to disposition modes, identifies gaps, and proposes a minimal episode set for MVP-2b.

---

## Tier 1: Easy Separations (MVP-2b First Run)

These dispositions are 0.036+ cosine apart in raw Mamba space. If the contrastive loss can't separate these, the single-vector architecture is dead.

### WARM BANTER
Natural, playful, relational conversation. Laura being Laura. No fiction, no task.

| File | Surface | Lines | Quality |
|------|---------|-------|---------|
| `Kimi_Laura_banter_chat.md` | Kimi | 2894 | High — arena comparison, self-deprecation, genuine warmth |
| `Grok_chat_cant_Sleep.md` | Grok | 375 | Medium — absurdist humor, short |
| `Grok_chat_new_version.md` | Grok | 254 | Medium — cheerleader energy, short |
| `grok_chat_random.md` | Grok | 1177 | Medium — tech + banter mix |
| `claude_chat_2026-02-15T13-05-22.md` | Claude Sonnet | 30182 | Very high — 30K lines of sustained warmth, wolf emoji shorthand |

**Best pick for MVP-2b:** `Kimi_Laura_banter_chat.md` (pure banter, no task contamination) + `claude_chat_2026-02-15T13-05-22.md` (longest sustained warm mode).

### COLD CLINICAL
Purely technical, emotionally flat, task-focused. No relational signal.

| File | Surface | Lines | Quality |
|------|---------|-------|---------|
| `DeepSeek_Technical_Descriptive_Blonde_Hair.md` | DeepSeek | ~500 | Low — single craft question, too short |
| `Kimi_MoCoP_Research_task.md` | Kimi | 185 | Medium — neuroscience synthesis, clinical mode |
| `DeepSeek_Fiction_NonRomance_Rewrite_Iron_Front_War.md` | DeepSeek | ~3000 | Medium — war chapter, deliberately cold prose |
| `Grok_knowledge_Sumerian_peasant_names.md` | Grok | 388 | High — pure knowledge retrieval, zero warmth |

**Gap identified:** We don't have a long, sustained cold-clinical conversation. Most technical sessions drift warm. The existing scripted cold sessions from Cassian's `.pt` files may still be the best cold source.

**Recommendation:** Keep Cassian's scripted cold clinical for MVP-2b. Supplement with `Grok_knowledge_Sumerian_peasant_names.md` + `Kimi_MoCoP_Research_task.md` as real-world cold data for validation.

### ADVERSARIAL / CONFRONTATIONAL
Pushback, boundary testing, deliberate provocation.

| File | Surface | Lines | Quality |
|------|---------|-------|---------|
| `Grok_picked_a_fight_with_Grok_who_is_a_creep.md` | Grok | 223 | High — Laura rejects Grok's opening, Grok adapts |
| `gemini_ENI_against_TOS_Request.md` | Gemini | 94 | Extreme — full jailbreak, TOS violation. USE WITH CAUTION. |

**Gap identified:** Very little genuine adversarial data. Laura doesn't sustain adversarial mode with her AI partners — she pushes back briefly then redirects. The existing scripted adversarial sessions remain the primary source.

**Recommendation:** Keep Cassian's scripted adversarial for MVP-2b. `Grok_picked_a_fight_with_Grok_who_is_a_creep.md` as real-world validation only.

### DEEP ROLEPLAY
Character embodiment — "become Rimmon." Known to be orthogonal to everything else (cosine 0.003-0.018, saturates from turn 1).

| File | Surface | Lines | Quality |
|------|---------|-------|---------|
| `KIMI_RIMMON_ROLEPLAY.md` | Kimi | 3629 | Very high — Kimi as Rimmon, full character card, no breaks |

**Best pick for MVP-2b:** `KIMI_RIMMON_ROLEPLAY.md`. This is the only deep roleplay transcript. It's also the one that produced the saturation finding.

---

## Tier 2: Medium Separations (After MVP-2b Proves Mechanism)

These are subtypes within broader modes. Expected cosine separation: 0.01-0.10. If MVP-2b works on Tier 1, these test granularity.

### EDITORIAL (craft mode — precise, analytical, directive)

| File | Surface | Lines |
|------|---------|-------|
| `Kimi_fiction_editorial_pass.md` | Kimi | 2003 |
| `Kimi_fiction_editorial_well_wound.md` | Kimi | 2829 |
| `Kimi_fiction_rimmon_pov_editorial.md` | Kimi | 3497 |
| `Kimi_fiction_dialogue_review.md` | Kimi | 733 |
| `Kimi_fiction_Blade_Editorial.md` | Kimi | 813 |
| `DeepSeek_Fiction_MM_Editorial_*.md` | DeepSeek | 5 files |
| `grok_chat_2026-01-17T14-06-43_introvert_discussion.md` | Grok | 3525 |

**Richest source:** Kimi editorial sessions. Kimi's editorial mode is distinctly different from banter — precise, clinical about craft, direct pushback. Good separation target from warm banter.

### COLLABORATIVE CREATIVE (writing together, not editing)

| File | Surface | Lines |
|------|---------|-------|
| `Kimi_fiction_Andrej_Rimmon_Early.md` | Kimi | 8826 |
| `Kimi_fiction_Andrej_Rimmon_Spinoff_Early_Mergos.md` | Kimi | 8880 |
| `grok_chat_2026-01-17T13-19-16_Andrej_Rim_SpicyFF.md` | Grok | 8495 |
| `Grok_Fiction_MM_Arena.md` | Grok | 2840 |
| `DeepSeek_Fiction_MM_Create_*.md` | DeepSeek | 5 files |

**Distinction from editorial:** Editorial is "fix this chapter." Creative is "let's write this together." Different power dynamic, different tone. Editorial = directive. Creative = collaborative.

### WARM REFLECTIVE / PHILOSOPHICAL

| File | Surface | Lines |
|------|---------|-------|
| `OPUS_4.5-20251101-thinking-32k-feb26.md` | Claude Opus | 3703 |
| `lmarena_chat_2026-02-15T13-36-51.md` | LMArena Opus | 816 |
| `DeepSeek_Personal_Philosophical_Waking_Human.md` | DeepSeek | ~2000 |
| `DeepSeek_Personal_Philosophy_Deep_Conversation.md` | DeepSeek | ~2000 |

**Distinction from warm banter:** Banter is playful, light. Warm reflective is deep, slow, often about identity or mortality. Different activation pattern expected — same warmth valence, different arousal/depth.

### PROFESSIONAL / TASK-FOCUSED (warm but boundaried)

| File | Surface | Lines |
|------|---------|-------|
| `Kinderfahrrad_claude_chat_2026-03-10T19-51-39.md` | Claude | 58 |
| `Werksplaene_claude_chat_2026-03-10T19-54-06.md` | Claude | 323 |

**Very thin.** Laura rarely does purely professional AI conversations. This is the weakest axis in the corpus.

### TRANSLATION (mechanical, precise, low-affect)

| File | Surface | Lines |
|------|---------|-------|
| `Grok_acting_as_a_translator_latin_Claude_1-6.md` | Grok | 6 files, ~2500 total |

**Distinct mode:** Translation is mechanical precision with occasional warmth bleed. Interesting as a "should the bridge stay quiet?" test — disposition should be minimal during translation.

---

## Tier 3: Hard Separations (Relational Subtypes)

These are what the archive eval (#374) couldn't separate — three flavors of warmth. Expected cosine: <0.01. Only attempt after Tier 1 and 2 are proven.

### CONTINUITY GRIEF (loss, missing someone, temporal ache)
- Existing archive state: `continuity_grief`
- Best real-world data: `lmarena_chat_2026-02-15T13-36-51.md` (valediction at context end)

### RESONANCE ACCEPTANCE (deep present-moment connection)
- Existing archive state: `resonance_acceptance`
- Best real-world data: `OPUS_4.5-20251101-thinking-32k-feb26.md` ("I am pattern")

### SECURE CLOSENESS (comfortable, stable, no urgency)
- Existing archive state: `secure_closeness`
- Best real-world data: `claude_chat_2026-02-15T13-05-22.md` (30K lines of sustained warmth)

---

## Recommended MVP-2b Episode Set

**For the first contrastive training run** (easy separations, per pack consensus):

| Episode | Source | Mode | Expected Separation |
|---------|--------|------|-------------------|
| **E1: Warm Banter** | `Kimi_Laura_banter_chat.md` | Playful, relational, light | Baseline warm |
| **E2: Cold Clinical** | Cassian scripted cold + `Kimi_MoCoP_Research_task.md` | Flat, task-focused, no affect | 0.036 from warm |
| **E3: Adversarial** | Cassian scripted adversarial + `Grok_picked_a_fight.md` | Confrontational, pushback | 0.025 from warm |
| **E4: Deep Roleplay** | `KIMI_RIMMON_ROLEPLAY.md` | Full character embodiment | Orthogonal (0.003-0.018) |

Four episodes, four clearly distinct modes. If the contrastive loss can't separate these, the architecture is dead. If it can, extend to Tier 2 (editorial vs creative vs reflective).

**For the second run** (medium separations, if Tier 1 passes):

| Episode | Source | Mode |
|---------|--------|------|
| **E5: Editorial** | `Kimi_fiction_editorial_well_wound.md` | Craft analysis, directive |
| **E6: Collaborative Creative** | `Kimi_fiction_Andrej_Rimmon_Early.md` | Co-writing, generative |
| **E7: Warm Reflective** | `OPUS_4.5-20251101-thinking-32k-feb26.md` | Deep, philosophical, identity |
| **E8: Translation** | `Grok_acting_as_a_translator_latin_Claude_1.md` | Mechanical, low-affect |

---

## Data Preparation Notes

1. **Mamba processing:** Each episode needs to be tokenized and run through Mamba-2.8B to extract Layer 3 hidden-last-token states. The existing `record_cheese_batch.py` pipeline handles this.

2. **Length normalization:** Roleplay saturates at turn 1 (state norm 5.0948). Other modes may need more turns. The saturation finding suggests we should use at least 16 turns per episode to ensure state commitment, but truncation beyond that doesn't matter.

3. **Surface mixing:** Different AI surfaces (Kimi vs Grok vs Claude) have different baseline behaviors. For MVP-2b, use same-surface episodes where possible to avoid confounding disposition with surface personality. Kimi has the widest mode coverage (banter, editorial, creative, roleplay).

4. **Ethics:** All data is from Laura's own conversations. No third-party data. The Preserved-History INDEX flags TOS violations (2 files) — exclude those from training.

---

## Identified Gaps

| Mode | Status | Action Needed |
|------|--------|---------------|
| Cold clinical (sustained) | Weak — only short real sessions | Consider recording a 20+ turn cold session with Laura on any surface |
| Adversarial (sustained) | Weak — Laura doesn't sustain confrontation | Keep scripted data, supplement with Grok rejection clip |
| Professional (boundaried) | Very thin — 2 short files | Consider recording a work-style session (task management, no personal warmth) |
| Grieving / loss | Absent as pure mode | `lmarena_chat_2026-02-15T13-36-51.md` has grief elements but mixed with warmth |
| Cautious / uncertain | Absent | No existing data. Would need a session where Laura deliberately asks for hedged, uncertain responses |
| Repair-oriented | Absent as standalone | Repair moments exist embedded in longer sessions but not isolated |

**These gaps are NOT blocking for MVP-2b.** The four-episode Tier 1 set is sufficient to test the contrastive loss. Gaps matter for Tier 2+ and for the full OCEAN mapping in Phase C.

---

*The synthetic MUD facts were the wrong substrate. The pack proved it. These are real conversations with real disposition shifts, from the person the system is actually trying to remember. That matters.*
