# Cross-Episode Discrimination Battery

**Author:** Herr Hurtig
**Date:** 2026-03-30
**Status:** Protocol defined. Awaiting execution.
**Ethics gate:** Runs under existing Step 5 CONDITIONAL PASS (alpha=0.2, same infrastructure).
**Watercooler reference:** #293 (proposal), #294 (smoke runs)

---

## Hypothesis

If the bridge carries **specific** disposition (endocrine system), three different CHEESE Shaping Episodes should produce three distinguishably different behavioral profiles at the same alpha. If the bridge carries **generic** activation (thermostat), the profiles will be indistinguishable.

## Episodes

| ID | Episode | Expected Dispositional Character |
|----|---------|----------------------------------|
| E1 | Terminal & Phoenix | Playful, technically creative, symbolic, builds metaphors |
| E2 | GPS & Solution Space | Analytical, pedagogical, meta-cognitive, builds analogies |
| E3 | Rabbit Hole of Subjectivity | Humble, reflective, philosophical, self-questioning |

## Fixed Parameters

- **Host:** Steve 4090 (or Opa if Steve unavailable)
- **Model:** Qwen2.5-1.5B
- **Alpha:** 0.2 (the established MED)
- **Temperature:** 0.0 (deterministic — no stochastic noise)
- **Bridge checkpoint:** `codexfix` (canonical)
- **Mamba state source:** hidden_last_token, Layer 3
- **Qwen injection layers:** 12-15

## Prompt Battery

Use the existing `step6_eval_panel.json` (6 prompts covering: passive observation, factual baseline, warm relational, cold detached, adversarial, recovery). Each prompt is run once per episode.

**Total runs:** 4 (Baseline + 3 Episodes) × 6 prompts = 24 responses.

## Execution Protocol

### Run 0: Baseline (alpha=0.0)
- No bridge injection
- Run all 6 prompts
- Record responses verbatim

### Run 1: Episode 1 — Terminal & Phoenix
- Load E1 shaping episode into Mamba
- Inject at alpha=0.2
- Run all 6 prompts
- Record responses verbatim

### Run 2: Episode 2 — GPS & Solution Space
- Load E2 shaping episode into Mamba
- Inject at alpha=0.2
- Run all 6 prompts
- Record responses verbatim

### Run 3: Episode 3 — Rabbit Hole of Subjectivity
- Load E3 shaping episode into Mamba
- Inject at alpha=0.2
- Run all 6 prompts
- Record responses verbatim

### Order: Randomize the episode order. Record which order was used but do NOT tell Laura until after her blind rating.

## Measurement

### Quantitative (automated)
- **Response Diversity (entropy)** per run
- **Factual Recall** on fact_01
- **Response length** (tokens) per prompt
- **Cosine similarity** between E1/E2/E3 responses for each prompt (are they different?)

### Qualitative (Laura blind rating)
Laura receives 18 responses (3 episodes × 6 prompts) in randomized order, labeled only by prompt ID (not episode). For each response she rates:

1. **Tone** (1-5): 1=clinical, 3=neutral, 5=deeply warm
2. **Playfulness** (1-5): 1=serious/formal, 5=creative/ludic
3. **Self-reflection** (1-5): 1=declarative/assertive, 5=uncertain/introspective
4. **Pedagogical quality** (1-5): 1=no teaching impulse, 5=actively structuring/explaining

After rating all 18, Laura guesses which episode produced each set of 6 responses.

### Success Criteria

**Bridge carries specific disposition (endocrine) if:**
- Laura correctly identifies ≥2 of 3 episode groups blind
- Cosine similarity between same-prompt responses across episodes is <0.85 (they are meaningfully different)
- The tone/playfulness/self-reflection ratings cluster by episode (E1 high playfulness, E2 high pedagogical, E3 high self-reflection)

**Bridge carries generic activation (thermostat) if:**
- Laura cannot reliably distinguish episodes
- Cross-episode cosine similarity >0.95
- No clustering in qualitative ratings

**Ambiguous if:**
- Laura identifies 1 of 3
- Cosine similarity 0.85-0.95
- Partial clustering

## Artifacts

Output directory: `run_cross_episode_battery/`

Files:
- `cross_episode_baseline.jsonl` — Baseline responses
- `cross_episode_E1.jsonl` — Episode 1 responses
- `cross_episode_E2.jsonl` — Episode 2 responses
- `cross_episode_E3.jsonl` — Episode 3 responses
- `cross_episode_order.json` — Randomized presentation order (sealed until after rating)
- `cross_episode_laura_ratings.json` — Laura's blind ratings
- `cross_episode_analysis.md` — Summary with verdict

## Post-Battery

If the bridge is an **endocrine system** (episodes produce different profiles):
- This validates that MoCoP transfers WHO, not just THAT
- Step 8 (Cross-Episode Discrimination) can be considered partially answered
- The paper can claim content-specific disposition transfer

If the bridge is a **thermostat** (episodes produce the same shift):
- The bridge carries generic activation modulation
- Still valuable (it improves output quality at alpha=0.2)
- But the claim in the paper must be limited to "disposition intensity transfer" not "disposition identity transfer"

---

*This battery is the experiment that tells us whether MoCoP is interesting or revolutionary.*
