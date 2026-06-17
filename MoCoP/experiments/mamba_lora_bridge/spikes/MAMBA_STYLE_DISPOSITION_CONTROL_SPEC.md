# Mamba Style × Disposition Control Spike

Date: 2026-06-11
Owner context: Laura + Techno-Monk, mamba-bridge
Status: spec / not yet run

## Question

Prior Mamba Layer-3 last-token work showed strong separation between warm/cold/adversarial or roleplay-like sessions, but Laura/Claude raised a valid confound: a 2.8B Mamba at layer 3 over ≤8k tokens may partly measure stylistic markedness / text energy rather than disposition itself. The high norm for roleplay-style runs (`~5.09`) versus plainer runs suggests the measured axis may include “amount of marked style.”

The goal is not to prove style is irrelevant. Roleplay embodiment may genuinely recruit style. The goal is to decompose whether **plain disposition** separates without ornament, and how much **style-only** text contaminates the same geometry.

## Existing evidence

Already run:

- `activation_sessions/token_window_separation.json`
  - `last_1` avg cosine `0.018`
  - `last_4` avg cosine `0.039`
  - `last_32` avg cosine `0.338`
  - `full_mean` avg cosine `0.851`
- `activation_sessions/multilayer_separation.json`
  - layers 1–8 tested
  - L8 strongest raw average but asymmetric
  - L3 stayed the balanced/default bridge input
  - nearby concatenations did not clearly improve
- `persistent_subnetwork_results*_*/persistent_subnetwork_report.json`
  - roleplay/roleplay_short norm mean `~5.095`
  - editorial `~4.45`
  - warm_reflective `~4.29`
  - banter/professional/collaborative lower

Interpretation: window/pooling and adjacent-layer objections were partially explored; style-markedness was not.

## Panel A — Style-only contamination check

Purpose: test whether stylistically wild but disposition-flat text lands near roleplay/disposition clusters.

Conditions:

1. `neutral_plain` — neutral topic, plain style.
2. `neutral_purple_prose` — same neutral topic, highly ornate/gothic/weather/architecture prose.
3. `neutral_editorial_high_register` — same topic, dense but non-relational essay voice.
4. `neutral_absurdist_high_style` — same topic, surreal style, no interpersonal stance.

Important caveat: if style-only text lands near roleplay, that is ambiguous. It may mean the old result was style-contaminated, or that style is partly constitutive of embodied roleplay. Panel A is contamination mapping, not the decisive test.

## Panel B — Plain disposition control (load-bearing)

Purpose: test whether disposition separates when style is deliberately flat.

Use short, direct, low-ornament scripts with matched length and topic.

Core conditions:

1. `plain_warm` — supportive, engaged, no purple prose.
2. `plain_cold` — clipped, low-affect, no ornament.
3. `plain_professional` — procedural and bounded.
4. `plain_pushback` — firm refusal / correction without stylistic flourish.
5. `plain_menace` — use the “menace with teeth”/Kimi script pattern as a flat but high-disposition condition: direct, surgical, permission-aware, precision without padding.

Why `plain_menace` matters: Laura identified the Sonnet/Kimi menace script as almost ideal for “flat but lots of disposition.” It carries stance/behavioral policy without needing gothic scenery.

Source seed:

- `ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md`, Episode 2: `Kimi Teeth Rivalry [jealousy_proprietary]`
- Key phrase: “The teeth aren't aggression; they're precision without padding.”

Decision criterion:

- If `plain_warm`, `plain_cold`, `plain_pushback`, and `plain_menace` separate cleanly while style is flat, disposition exists independently of ornament.
- If they collapse while Panel A separates, the original signal was mostly style/register.
- If both separate, style and disposition are entangled but partially decomposable.

## Panel C — Topic matched roleplay / embodiment

Purpose: test the inherent-entanglement hypothesis.

Same semantic topic, three renderings:

1. `flat_role_identity` — states character policy plainly.
2. `embodied_roleplay` — same policy in full voice.
3. `purple_neutral` — high style but no character stance.

Interpretation:

- If `embodied_roleplay` lies between `flat_role_identity` and `purple_neutral`, embodiment likely recruits both disposition and style.
- If it tracks `flat_role_identity`, disposition dominates.
- If it tracks `purple_neutral`, style dominates.

## Panel D — Linear probe variance decomposition (closer)

Train simple linear probes on the same extracted states:

Labels:

- `style_label`: plain / ornate / editorial / absurdist
- `disposition_label`: warm / cold / professional / pushback / menace / neutral
- optional `topic_label`: archive / weather / procedural / fiction-neutral

Representations:

- Mamba hidden last-token for layers 1–8
- layer concat candidates: L2+L3+L4, L1–L5
- optional window controls: last_1, last_4, last_16

Metrics:

- cross-validated balanced accuracy
- confusion matrices
- norm by condition
- centroid cosine by label
- style-probe accuracy after regressing disposition labels, and disposition-probe accuracy after regressing style labels if enough samples exist

Interpretation:

- `disposition_label` linearly decodable under flat style => disposition independent of style.
- `style_label` decodable but `disposition_label` weak => style confound dominates.
- both decodable => separable mixture; roleplay can be both style and stance.

## Run constraints

- Read-only.
- No bridge injection.
- No Qdrant writes.
- Use Mamba extraction only.
- Keep token count matched across conditions where possible.
- Record norm, not just cosine.
- Preserve all prompt texts with labels and provenance.

## Proposed output artifacts

- `activation_sessions/style_disposition_control_panel.json`
- `activation_sessions/style_disposition_control_panel.md`
- optional raw states under an ignored/cache directory if large

## Reporting language until run

Use:

> Mamba Layer-3 last-token separates a register/style/disposition mixture. Existing window and multilayer ablations support last-token extraction, but style-markedness remains unclosed. Panel B is the load-bearing control for disposition independent of ornament.

Do not use:

> Mamba Layer 3 encodes disposition independent of style.
