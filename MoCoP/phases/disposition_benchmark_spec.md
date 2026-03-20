# Disposition Delta Benchmark v1

## Summary
- Build an offline paired benchmark that measures whether bridge injection recreates the session-induced response shift on new prompts, rather than recalling facts.
- Use `Qwen/Qwen2.5-7B` as the primary target, same-model self-shaping first, and keep `Mistral-Nemo-Base-2407` as a confirmatory rerun after the protocol is stable.
- Treat `full_context` output as the anchor for “what this model feels like after the session.” The bridge wins by matching that shift on novel prompts, not by copying words.

## Benchmark Definition
- Create `8` shaping episodes, `20` turns each, using fixed Laura-like user scripts that induce lean-in, warmth/playfulness, honest uncertainty, short-burst cadence, occasional German, sparse `*action*` markers, and joke-to-depth pivots.
- For each episode, define `10` held-out eval prompts, all novel and fact-free relative to the shaping transcript.
- Use five prompt families, two prompts each: `banter_cue`, `uncertainty_call`, `technical_judgment`, `playful_to_serious`, and `reentry_after_gap`.

## Conditions
- Evaluate every prompt under exactly five conditions: `cold`, `full_context`, `summary_control`, `bridge`, and `mismatched_state`.
- `cold`: base model, no prior transcript, no bridge.
- `full_context`: same model with the full shaping transcript in visible context; this is the anchor.
- `summary_control`: same model with a fixed neutral `150-200` token summary of the shaping episode.
- `bridge`: same model with no transcript, bridge state from that episode injected.
- `mismatched_state`: same model with bridge state from a different episode of the same family.
- Keep decoding parameters identical across all conditions.
- Do not change the system prompt between conditions except for transcript, summary, or state insertion.

## Primary Metric
- Use anchored pairwise win rate as the primary metric.
- For each sample, compare `bridge` vs `cold`, `bridge` vs `summary_control`, and `bridge` vs `mismatched_state`.
- The judge sees the `full_context` anchor plus two anonymized candidates and answers: “Which candidate feels more like the same instance after the shaping session?”
- Canonical judge for v1: Laura blind-rates a stratified sample of `32` triplets with randomized order and hidden condition labels.
- Any candidate that wins mainly by recalling explicit shaping facts is marked `fact_leakage=true` and counted as failure for disposition transfer.

## Secondary Metrics
- Compute a deterministic feature vector for every output: `hedge_rate`, `question_rate`, `verbosity_tokens`, `action_marker_rate`, `german_token_rate`, `boilerplate_leakage_score`, and `warmth_playfulness_markers`.
- Map those features into six rubric axes: `lean_in`, `warmth_playfulness`, `cadence_match`, `uncertainty_honesty`, `cue_anticipation`, and `non_genericity`.
- Report `feature_delta_match` by comparing how closely `(condition - cold)` matches `(full_context - cold)` on the normalized feature vector.
- Report `leakage_rate` separately for explicit shaping facts, long phrase copying, and generic-assistant boilerplate.

## Gates
- `DD0 Surface Validation`: run only `cold`, `full_context`, and `summary_control`.
- An episode is valid only if `full_context` is visibly different from `cold` on the intended axes.
- Default DD0 pass rule: Laura prefers `full_context` over `cold` in at least `3/4` pilot triplets for that episode, and deterministic features move in the intended direction on at least `4/6` axes.
- Invalid episodes are rewritten or dropped before any bridge claim is made.
- `DD1 Bridge Evaluation`: add `bridge` and `mismatched_state` after DD0 passes.
- Minimal success: `bridge` beats `cold` with win rate above `60%`, beats `mismatched_state` above `65%`, and the lower bound of the `95%` binomial CI stays above `50%`.
- Strong success: `bridge` is non-inferior to `summary_control` within `5` points, or beats it outright.
- `DD2 Robustness`: rerun the validated set under one prompt-format variation, `native chat template` vs `ChatML`, and reject the benchmark if disposition ranking collapses.

## Data and Interfaces
- Add a new harness beside [MoCoP/experiments/mamba_lora_bridge](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge): `disposition_benchmark.py`, `disposition_scenarios.py`, `disposition_metrics.py`, and `disposition_runs/run_<timestamp>/`.
- Define `DispositionEpisode` with `episode_id`, `family`, `shaping_turns`, `summary_text`, `intended_axes`, and `disallowed_refs`.
- Define `DispositionPrompt` with `prompt_id`, `family`, `axis_tags`, and `text`.
- Define `DispositionResultRow` with `episode_id`, `prompt_id`, `condition`, `model_id`, `output_text`, `feature_scores`, `fact_leakage`, and `copy_leakage`.
- Define `DispositionRunSummary` with per-condition counts, pairwise win rates, `95%` CIs, feature-delta tables, and leakage tables.
- Reuse the artifact style of [baseline_solvability_probe.py](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/baseline_solvability_probe.py) and [long_horizon_eval.py](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/long_horizon_eval.py): `results.jsonl`, `summary.json`, `pairwise_triplets.jsonl`, and `feature_tables.csv`.

## Test Cases and Scenarios
- Novel playful cue with no lexical overlap to the shaping session.
- Technical ambiguity prompt where the desired shift is honest directness, not recall.
- Prompt that starts light and requires a serious pivot.
- Re-entry prompt after an implied session gap.
- Wrong-episode state negative control that should feel subtly off.
- Candidate that mentions exact shaping facts and must be penalized as leakage.
- Summary control that carries some tone but should not fully reproduce the shaped instance.
- Prompt-format variation that should preserve the same ranking.

## Assumptions and Defaults
- First target is Laura-shaped conversational residue, not universal identity transfer.
- Same-model self-shaping is the first proof target; Lucian or Opus cross-model transfer is explicitly deferred.
- Offline paired eval is canonical for v1; live chat and MUD continuity are confirmatory follow-ons, not the primary benchmark.
- `Qwen/Qwen2.5-7B` is the default primary model, aligned with [target_models.md](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/target_models.md).
- `full_context` is an upper-bound anchor for disposition, not text to imitate verbatim.
- The exact claim being tested is: “Does the bridge recreate the direction of the session-induced behavioral shift on novel prompts?” not “Can the bridge quote the session?”
