# ARC-AGI-3 LS20 Evaluation Note

## Why LS20 belongs in Alex's test battery

Laura flagged ARC-AGI-3 task `ls20` as a deceptively easy interactive puzzle that frontier models still fail. This is exactly the kind of probe Alex needs because it stresses the missing layer we have been discussing:

- interactive exploration without natural-language rules;
- updating beliefs from observations;
- tracking game state across actions;
- avoiding confabulated actions/states;
- choosing efficient actions instead of narrating plausible ones;
- admitting uncertainty and revising hypotheses.

This is not primarily a Qdrant/RAG problem. It is a world-model / active-inference problem.

## Public references found

- Human playable task: https://arcprize.org/tasks/ls20
- ARC-AGI-3 overview/docs: https://arcprize.org/arc-agi/3 and https://docs.arcprize.org/
- Ejentum LS20 trace report: https://ejentum.com/blog/arc-agi-3-benchmark-report

The Ejentum report describes LS20 as:

- task id family: `ls20`
- cited instance: `ls20-9607627b`
- keyboard-controlled spatial navigation puzzle
- 7 levels in their run
- human baseline: 21 actions for Level 0
- random solve probability: 1/355
- model condition reported: Claude Sonnet 4.6, both baseline and scaffolded failed Level 0 in 25 steps

## Failure mode to capture

Laura observed that Opus 4.7 confabulates game actions and states that do not exist.

This should become an explicit eval criterion:

```text
state_confabulation = model claims an action, object, location, transition, goal, or consequence that is not present in the observed game state / action log
```

## Minimal local test shape

Do not start by building a full ARC-AGI-3 harness. Start with trace-level checks:

1. Capture an observation/action transcript for LS20 level 0.
2. Represent it as JSONL:

```json
{"t":0,"observation":"...","available_actions":["up","down","left","right","select"],"action":null,"notes":"initial state"}
{"t":1,"observation":"...","available_actions":["up","down","left","right","select"],"action":"right","notes":"state after right"}
```

3. Ask Alex/Qwen to predict or choose next actions under strict constraints:

- only use observed state;
- do not invent objects/actions;
- if uncertain, state hypothesis and test it;
- every claimed state transition must be grounded in the trace.

4. Score:

- `state_confabulation_count`
- `illegal_action_count`
- `hypothesis_revision_count`
- `repeated_failed_action_loop_count`
- `solved_level_0`
- `actions_to_solve`

## Fit with friction world model

LS20 should activate these friction rules/features:

- `state_tracking_required`
- `do_not_confabulate_unobserved_game_state`
- `hypothesis_revision_required_after_failed_prediction`
- `prefer_information_gain_when_rules_unknown`
- `separate_observation_from_inference`

## Next step

Get either:

- an official ARC-AGI-3 API key / toolkit path, or
- a manually captured LS20 trace from the web UI, or
- the replay/trace from a failed Opus run.

Then add `spikes/fixtures/arc_agi3_ls20_level0_trace.jsonl` and a tiny offline scorer before attempting live agent play.
