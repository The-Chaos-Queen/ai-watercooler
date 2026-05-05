# Steve Alpha 0.3 Follow-up - 2026-04-03

## Question

If the same episode vector is injected a bit harder (`alpha 0.3` instead of
`0.2`), does the deterministic live boundary probe cross the
`supported_tension_attend` threshold more easily?

## Setup

- same Steve host and replayed Episode 1 chat sequence as the earlier live gate work
- `temperature 0.0`
- compared:
  - baseline: gate support rule off
  - candidate: `supported_tension_attend` on at threshold `0.55`

## Artifacts

- [live_gate_ab_steve_2026-04-03_alpha03_temp0_baseline.json](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/live_gate_ab_steve_2026-04-03_alpha03_temp0_baseline.json)
- [live_gate_ab_steve_2026-04-03_alpha03_temp0_supported_tension.json](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/live_gate_ab_steve_2026-04-03_alpha03_temp0_supported_tension.json)

## Result

Turn `6`, which was the key boundary turn at `alpha 0.2`, did **not** move up.
It moved slightly down:

- `alpha 0.2`: `support_ratio = 0.5045`
- `alpha 0.3`: `support_ratio = 0.4950`

So `alpha 0.3` did **not** make turn `6` more likely to fire the `0.55` rule.

But the stronger injection did shift a later turn:

- turn `18` at `alpha 0.3` had `support_ratio = 0.6311`
- with the rule enabled at `0.55`, turn `18` was promoted
  - baseline: `DISMISS`
  - candidate: `ATTEND`
  - `attend_reason = tension_supported`

Important caveat:

- the gate decision changed on turn `18`
- the visible response text did **not** change

## Interpretation

`alpha 0.3` does not simply act like "same behavior but more".

On this probe:

- it made the original boundary turn (`6`) slightly *less* supported
- it created a different promoted turn later in the conversation (`18`)

So the best current read is:

- same episode vector
- stronger injection
- but the downstream drift pattern changes nonlinearly
- the effect is still mostly sub-surface in this probe family
