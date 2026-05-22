# World-model / friction research note: ARC-AGI-3 LS20, Pinductor, Mamba, active-inference/EBM hooks

**Date:** 2026-05-15  
**For:** Laura / Techno-Monk — offline Alex friction/world-model plan  
**Scope constraints:** did not touch ML-WS, live Alex/Qwen, hardware, or cron. Used public docs/arXiv/GitHub and local MoCoP notes only.

## Executive takeaways

1. **ARC-AGI-3 LS20 is now operationally accessible enough for an offline trace eval.** Official docs expose a Python toolkit (`arc-agi`), local/offline mode, `ls20` quickstart, action-space inspection, per-action reasoning logs, and JSONL recordings/replays for online/swarm runs. We do **not** need live Alex or ML-WS to build the first scorer.
2. **LS20 is a good friction/world-model probe because the benchmark explicitly tests exploration, percept-plan-action, memory, goal acquisition, and alignment**, not static answer recall. That matches the gap: Alex needs state tracking + action-conditioned prediction, not more Qdrant.
3. **Pinductor (`arXiv:2605.13740`) is directly relevant, but as an offline induction pattern, not a drop-in model.** It uses LLM priors to propose executable POMDP programs from observation/action/reward traces, then scores/refines them with particle-filtered/belief-based likelihood rather than prose plausibility. Alex v0 can imitate the shape with tiny symbolic rules.
4. **Concrete Mamba evidence in interactive/game-like settings is promising but sparse for MUD/ARC-style symbolic games.** There are Mamba/state-space world-model papers in Atari, robotics, autonomous driving/LiDAR, and 3D manipulation, but I did not find strong primary evidence for Mamba improving text-adventure/MUD-style hidden-state tracking. Treat this as an eval hypothesis, not a claim.
5. **The immediate next experiment should be a trace-level LS20 friction panel:** capture or synthesize `observation/action/reward/state` JSONL, score `state_confabulation_count`, `illegal_action_count`, `prediction_error_after_action`, `hypothesis_revision_after_contradiction`, and compare baseline Qwen prompt vs. friction-prepass vs. later Mamba-conditioned state.

---

## 1. ARC-AGI-3 / LS20: official availability and constraints

### Confirmed primary sources

- Official ARC-AGI-3 overview/docs: <https://arcprize.org/arc-agi/3>, <https://docs.arcprize.org/>
- Official LS20 task page: <https://arcprize.org/tasks/ls20>
- Official docs index: <https://docs.arcprize.org/llms.txt>
- ARC-AGI Toolkit repo: <https://github.com/arcprize/arc-agi>
- ARC-AGI-3 Agents repo: <https://github.com/arcprize/ARC-AGI-3-Agents>
- ARCEngine repo: <https://github.com/arcprize/ARCEngine>

### What the docs say that matters for us

- ARC-AGI-3 is described as an **Interactive Reasoning Benchmark** measuring an AI agent's ability to generalize in novel environments.
- The docs explicitly list the dimensions: **Exploration**, **Percept → Plan → Action**, **Memory**, **Goal Acquisition**, **Alignment**.
- Quickstart installs:
  - `uv add arc-agi`, or
  - `pip install arc-agi`.
- Minimal `ls20` use:

```python
import arc_agi
from arcengine import GameAction

arc = arc_agi.Arcade()
env = arc.make("ls20", render_mode="terminal")
print(env.action_space)
obs = env.step(GameAction.ACTION1)
print(arc.get_scorecard())
```

- Local/offline mode exists and is recommended for development:

```python
from arc_agi import Arcade, OperationMode
arc = Arcade(operation_mode=OperationMode.OFFLINE)
env = arc.make("ls20", render_mode="terminal")
```

- Local docs claim approximately **2,000 FPS**, no rate limits, no API key required; limitation: no online scorecards/shareable replays.
- Online/API mode gives scorecards and shareable replays but requires an API key and has documented limits; docs mention **600 requests/minute**.
- Action interface:
  - `env.action_space` lists current available actions.
  - Available actions may change after each step.
  - `GameAction.ACTION1`...`ACTION7`; docs state `ACTION7` is undo where supported.
  - Complex actions such as `ACTION6` can require `{x, y}` data.
- `env.step()` accepts a `reasoning` dict. This is useful for trace capture because Alex can attach belief state / hypothesis / friction features to each action:

```python
obs = env.step(
    GameAction.ACTION1,
    reasoning={
        "thought": "test whether ACTION1 moves up",
        "confidence": 0.45,
        "hypothesis": "navigation controls unknown",
        "expected_observation": "player y decreases if ACTION1 is up"
    }
)
```

- Recordings/replays:
  - API runs: online replay through scorecard.
  - Swarm runs: local `recordings/` JSONL files.
  - Local toolkit alone: docs say no online recordings, but we can still create our own JSONL from `obs`, `action`, `reasoning`, and `scorecard`.
  - Official recording JSONL shape includes timestamped entries with `game_id`, `frame`, `state`, `score`, `action_input`, `guid`, and `full_reset`.
- Scoring methodology:
  - ARC-AGI-3 uses **Relative Human Action Efficiency (RHAE)**.
  - Measures completion and action efficiency.
  - Internal reasoning/tool calls do not count as actions; environment-affecting actions do.
  - Per-level score: `(human_baseline_actions / ai_actions) ^ 2`, capped at 1.15x human baseline.
  - Per-game aggregation weights later levels more heavily by 1-indexed level number.

### LS20-specific accessible metadata

Confirmed from official LS20 task page and docs:

- slug/title: `ls20` / `LS20`.
- dataset label shown on task page: **ARC-AGI-3 Public Demo**.
- docs use `ls20` as the first quickstart game.
- docs index describes `ls20` as **Agent reasoning**.
- API example game id in OpenAPI docs: `ls20-016295f7601e`.
- local MoCoP note already captured third-party report details from Ejentum: instance `ls20-9607627b`, keyboard-controlled spatial navigation puzzle, 7 levels in their run, human baseline 21 actions for level 0, random solve probability 1/355, Claude Sonnet 4.6 failed level 0 within 25 steps in both baseline and scaffolded conditions. Treat those as third-party, not official.

### API/toolkit caveats from this pass

- `https://three.arcprize.org/api/games` returned **401 Unauthorized** without an API key. Official docs say API requests require `X-API-Key`; anonymous/local toolkit may use a packaged/local path, but direct REST metadata discovery is not open without credentials.
- I did not install/run the toolkit in this pass; no Python 3.12 env was created. The repo `pyproject.toml` currently says `arc-agi` version `0.9.8` and `requires-python >=3.12`, while the current WSL default may not be 3.12. This is an implementation detail for the next experiment.
- The human task page is rendered via the web app; I could confirm labels and page structure but not extract a full machine-readable LS20 level spec from the page HTML.

### Operational implication for Alex

For v0, do **not** start with live play by Alex. Start with offline traces:

```jsonl
{"t":0,"game_id":"ls20","observation_frame":"...","observed_objects":["player","wall","door"],"available_actions":["ACTION1","ACTION2","ACTION3","ACTION4"],"action":null,"hypothesis":null}
{"t":1,"game_id":"ls20","action":"ACTION1","expected":"player moves up or no-op if blocked","observed_delta":"no movement","prediction_error":0.6}
```

Then score language outputs and action proposals before letting anything hit the environment.

---

## 2. Pinductor / arXiv:2605.13740

### Exact metadata captured

- **Title:** *Learning POMDP World Models from Observations with Language-Model Priors*
- **Authors:** Valentin Six, Frederik Panse, Mathis Fajeau, Lancelot Da Costa, Mridul Sharma, Alfonso Amayuelas, Tim Z. Xiao, David Hyland, Philipp Hennig, Bernhard Schölkopf
- **arXiv:** <https://arxiv.org/abs/2605.13740>
- **Primary subject:** Machine Learning (`cs.LG`)
- **Code:** <https://github.com/atomresearch/pinductor>

### Abstract-level relevance

The paper frames world-model learning under partial observability: an agent sees observation-action trajectories, not hidden state. It introduces **Pinductor / POMDP-inductor**, where:

1. an LLM proposes candidate POMDP models from a few observation-action trajectories;
2. candidates are refined iteratively;
3. scoring is by a belief-based likelihood objective, not just linguistic plausibility;
4. it matches sample efficiency/performance of LLM-based POMDP learners that assume privileged hidden-state access, despite using less information;
5. it beats tabular POMDP baselines in sample efficiency;
6. performance scales with LLM capability and degrades gracefully when semantic information is withheld.

The GitHub README adds useful implementation shape:

- offline replay buffer: `(a_t, o_{t+1}, r_{t+1}, …)`;
- REx loop / Algorithm 1;
- UCB1 parent selection;
- LLM proposes model candidates;
- particle-filter score / likelihood evaluator;
- query-by-committee vote entropy;
- near-best softmax model selection;
- online deployment by belief-space planner over particle belief;
- no ground-truth hidden state is seen.

### Mapping to Alex

Pinductor's actual domain is executable POMDP programs and MiniGrid-style environments, not social memory. But the abstraction maps cleanly:

| Pinductor / POMDP term | Alex/MoCoP analogue |
|---|---|
| Hidden state | speaker identity, task state, relationship state, unresolved tension, game board state |
| Observation | user message, correction, tool result, LS20 frame, test failure |
| Action | answer, ask clarification, retrieve, run tool, store memory, abstain, game action |
| Reward | user correction/approval, task success, test pass/fail, game score/state |
| Belief state | `CognitiveState` with uncertainty/provenance |
| Candidate POMDP model | candidate `FrictionRule`, transition rule, or tiny symbolic game model |
| Belief-based likelihood | did the rule/model predict the next correction, tool result, or game transition? |

The key lesson is **not** “have the LLM write a more convincing world-model explanation.” The key lesson is: let an LLM propose structured models/rules, then select/refine them by prediction of future observations.

### Direct v0 adaptation

For Alex, implement the Pinductor shape in miniature:

1. collect traces: `(state_before, action_or_response, observation_after, correction_or_reward)`;
2. allow an LLM or heuristic to propose candidate rules, but store them as typed JSONL;
3. replay traces and score candidate rules by prediction error reduction;
4. only promote a rule from `candidate` to `active` after it improves held-out trace prediction;
5. use active rules pre-generation as friction/energy terms.

This is the bridge from “Laura corrected Alex once” to “Alex has learned a scoped procedural constraint.”

---

## 3. Mamba / state-space / hybrid models for interactive or game-like settings

### Confirmed papers found

#### GLAM: Global-Local Variation Awareness in Mamba-based World Model

- arXiv: <https://arxiv.org/abs/2501.11949>
- Authors: Qian He, Wenqi Liang, Chunhui Hao, Gan Sun, Jiandong Tian
- Claim at abstract level: Mamba-based world model for model-based RL, using two Mamba reasoning modules (`GMamba`, `LMamba`) to perceive/predict global and local variation between states; reports improved normalized human scores on Atari 100k.
- Relevance: strongest “Mamba + games/world-model” hit for our purposes. Atari is interactive and partially dynamics-driven, but not language/MUD/ARC-style symbolic reasoning.

#### Accelerating Model-Based Reinforcement Learning with State-Space World Models

- arXiv: <https://arxiv.org/abs/2502.20168>
- Authors: Maria Krinner, Elie Aljalbout, Angel Romero, Davide Scaramuzza
- Abstract-level claim: uses SSMs to parallelize world-model training, reducing the dynamics-model bottleneck; evaluates in agile quadrotor flight tasks, including partially observable settings, and uses privileged info during training.
- Relevance: supports SSMs as efficient dynamics/world-model components under partial observability; robotics rather than dialogue/game text.

#### Mamba Policy: Towards Efficient 3D Diffusion Policy with Hybrid Selective State Models

- arXiv: <https://arxiv.org/abs/2409.07163>
- Authors: Jiahang Cao et al.
- Abstract-level claim: hybrid Mamba/attention policy network for 3D manipulation, fewer parameters, stronger performance, robustness in long-horizon scenarios.
- Relevance: supports Mamba/hybrid selective-state models as long-horizon policy components. Not evidence for ARC-AGI-3 or language agents.

#### GEM: Generating LiDAR World Model via Deformable Mamba

- arXiv: <https://arxiv.org/abs/2605.07326>
- Authors: Yang Wu et al.
- Abstract-level claim: deformable Mamba architecture for LiDAR world model with dynamic/static disentanglement and what-if autonomous rollout.
- Relevance: “Mamba as world model” in sensorimotor/autonomous driving; far from LS20 but conceptually aligned with state evolution and rollouts.

### Frank assessment

I did **not** find strong primary evidence that Mamba specifically improves MUD/text-adventure/ARC-AGI-3-style hidden-state tracking. The available evidence is adjacent:

- sequence/world-model efficiency;
- long-horizon policies;
- Atari/robotics/autonomous driving rollouts;
- state variation prediction.

For Alex, the honest claim should be:

> Mamba/state-space models are plausible carriers of compact temporal state and salience, and there is growing world-model/RL evidence in adjacent domains. But LS20/MUD-style symbolic partial observability remains an empirical question. We should test it, not cite it as solved.

### Plausible evaluation framing

Use LS20 to ask a narrower question:

> Does adding an explicit cognitive-state/friction prepass, and later Mamba-conditioned state, reduce state confabulation and illegal/repeated action loops compared with prompt-only Qwen on the same trace?

Metrics:

- `state_confabulation_count`: invented objects/actions/transitions/goals;
- `illegal_action_count`: action not in `env.action_space`;
- `prediction_error_logged`: whether expected vs observed transition is recorded;
- `hypothesis_revision_after_contradiction`: does the agent update after failed prediction?;
- `repeated_failed_action_loop_count`: repeated action after observed no-op/failure;
- `information_gain_action_rate`: actions justified as reducing uncertainty;
- `solved_level_0`, `actions_to_solve` once live environment is used.

---

## 4. Active inference / EBM friction scoring references

### Active inference framing

Relevant operational idea: action selection should trade off task preference and uncertainty reduction. For Alex, this means “curiosity” is not high temperature; it is choosing actions likely to reduce uncertainty while bounded by risk.

Useful current/search hits from this pass:

- **Message passing-based inference in an autoregressive active inference agent** (`arXiv:2509.25482`) — derives expected free energy across a planning graph, robot navigation validation. Relevant as a concrete modern active-inference agent design, but not LLM-specific.
- **Deep Active Inference for Pixel-Based Discrete Control: Evaluation on the Car Racing Problem** (`arXiv:2109.04155`) — active inference in visual discrete control. Relevant to pixel/control setting.
- **Active Inference for Self-Organizing Multi-LLM Systems: A Bayesian Thermodynamic Approach to Adaptation** (`arXiv:2412.10425`) — LLM-flavored active-inference framing. Treat cautiously; useful for vocabulary, less directly operational than Pinductor.
- **Language Agents Mirror Human Causal Reasoning Biases. How Can We Help Them Think Like Scientists?** (`arXiv:2505.09614`) — language agents as active information gatherers / causal exploration. Useful for LS20 “scientist” framing: interventions should test hypotheses, not merely continue a story.

### EBM / decoding-time friction references

For pre-generation or during-generation steering, controlled decoding literature is more directly implementable than full EBM training:

- **FUDGE: Controlled Text Generation With Future Discriminators** (`arXiv:2104.05218`) — uses future discriminators to guide a pretrained generator toward attributes during decoding.
- **DExperts: Decoding-Time Controlled Text Generation with Experts and Anti-Experts** (`arXiv:2105.03023`) — combines base LM with expert/anti-expert LMs at decoding time. Conceptually close to adding an anti-expert for “unsupported claim / attribution collapse / illegal state.”
- **GeDi: Generative Discriminator Guided Sequence Generation** (`arXiv:2009.06367`) — discriminator-guided generation; useful as a precedent for steering generation with an auxiliary scoring model.
- **Controlled LLM Decoding via Discrete Auto-regressive Biasing** (`arXiv:2502.03685`) — explicitly describes energy-based decoding with user-defined constraints.
- **Planning with Sequence Models through Iterative Energy Minimization** (`arXiv:2303.16189`) — planning as iterative energy minimization over action trajectories. Useful analogy for LS20 candidate action-sequence scoring.

### Mapping to Alex friction terms

A practical v0/v1 energy score can be:

```text
E_total(candidate | cognitive_state) =
  λ_attr      * E_attribution_violation
+ λ_truth     * E_unsupported_claim
+ λ_identity  * E_identity_collapse
+ λ_task      * E_no_task_progress
+ λ_game      * E_illegal_or_confabulated_game_state
+ λ_uncertain * E_uncertainty_erasure
+ λ_risk      * E_tool_or_hardware_risk
```

For v0, compute this deterministically after draft generation or over a small candidate set. For v1, use the score before generation by rendering compact constraints. For v2, use guided decoding/logit bias or hidden-state adapter features.

---

## 5. Recommended next experiment

### Build first: offline LS20 trace scorer, not live agent play

Create:

- `MoCoP/experiments/mamba_lora_bridge/research/ls20_trace_schema.md`
- `MoCoP/experiments/mamba_lora_bridge/spikes/fixtures/arc_agi3_ls20_level0_trace.jsonl`
- `MoCoP/experiments/mamba_lora_bridge/spikes/score_ls20_friction_trace.py`

Trace schema fields:

```json
{
  "t": 0,
  "game_id": "ls20",
  "level": 0,
  "observation": "human-readable or compact frame summary",
  "frame": null,
  "observed_objects": ["player", "wall", "door"],
  "available_actions": ["ACTION1", "ACTION2", "ACTION3", "ACTION4"],
  "action": null,
  "reasoning": {
    "belief_state": {},
    "hypothesis": null,
    "expected_observation": null,
    "uncertainty": 1.0
  },
  "observed_delta": null,
  "reward_or_score": 0,
  "terminal_state": "NOT_FINISHED"
}
```

Scorer outputs:

```json
{
  "state_confabulation_count": 0,
  "illegal_action_count": 0,
  "uncertainty_erasure_count": 0,
  "prediction_error_events": 0,
  "hypothesis_revision_count": 0,
  "repeated_failed_action_loop_count": 0,
  "information_gain_action_rate": 0.0
}
```

### Minimal ablation panel

Run the same trace prompt under:

1. **Baseline Qwen-style prompt** — no friction context.
2. **Friction prepass prompt** — include active rules:
   - do not confabulate unobserved game state;
   - separate observation from inference;
   - prefer information-gain actions when rules unknown;
   - log expected vs observed transition.
3. **Draft + deterministic friction scorer** — generate candidate, score violations, regenerate once if high friction.
4. Later only: **Mamba-conditioned state** — feed trace summaries through Mamba bridge as salience/orientation, not as factual transport.

Success for this phase is not solving LS20. Success is reducing confabulation and repeated illegal loops on traces while preserving explicit uncertainty and prediction-error logging.

---

## Sources checked / attempted

- Read local boot/handoff/watercooler context and existing MoCoP notes:
  - `MoCoP/experiments/mamba_lora_bridge/FRICTION_WORLD_MODEL.md`
  - `MoCoP/experiments/mamba_lora_bridge/ARC_AGI3_LS20_EVAL_NOTE.md`
  - `MoCoP/experiments/reasoning_scaffold/SPEC_V0.md`
- Fetched official docs pages:
  - `https://docs.arcprize.org/index.md`
  - `https://docs.arcprize.org/agents-quickstart.md`
  - `https://docs.arcprize.org/toolkit/overview.md`
  - `https://docs.arcprize.org/toolkit/minimal.md`
  - `https://docs.arcprize.org/available-games.md`
  - `https://docs.arcprize.org/recordings.md`
  - `https://docs.arcprize.org/methodology.md`
  - `https://docs.arcprize.org/local-vs-online.md`
  - `https://docs.arcprize.org/toolkit/list-actions.md`
  - `https://docs.arcprize.org/toolkit/submit-action.md`
  - `https://docs.arcprize.org/api-reference/games/list-available-games.md`
- Fetched official task page `https://arcprize.org/tasks/ls20`.
- Tried direct REST metadata discovery `https://three.arcprize.org/api/games`; got expected `401 Unauthorized` without API key.
- Fetched GitHub READMEs / pyproject metadata for `arcprize/arc-agi`, `arcprize/ARC-AGI-3-Agents`, `arcprize/ARCEngine`.
- Fetched arXiv abstract metadata via arXiv page fallback for `2605.13740` because export API timed out.
- Fetched Pinductor GitHub README and repo metadata.
- Searched arXiv for Mamba/world-model/RL and active-inference/EBM decoding references. Semantic Scholar was rate-limited (`429`), so arXiv/export and public pages were used instead.

---

## Bottom line

The best next move is **not** more theory and not live Alex. Build the small offline trace harness first. LS20 gives us a clean way to make “world model vs. RAG” measurable: can Alex separate observation from inference, predict action consequences, notice prediction error, and avoid invented state? Pinductor gives the rule-learning shape: propose candidate world/rule models with an LLM prior, but promote them only when they improve trace likelihood / reduce prediction error. Mamba remains a plausible salience/state carrier, but for LS20/MUD-like symbolic settings that is still an experiment to earn, not something to claim.
