# Active Inference Reconciliation — the framework the house already built

**Date:** 2026-07-04
**Status:** Draft / theory synthesis / no canon enacted
**Lineage:** Techno-Monk's world-model synthesis (Telegram dig, 2026-07-04, from `Three_System_Cognitive_Architecture.md`, `unified_cognitive_framework.md`, `temporal_controller_and_authority_arbitration.md`, `friction_world_model.py`, `spikes/score_ls20_trace.py`, `surprise_gated_memory.md`) + Laura's framing principle + the 2026-07-03/04 empirical exhibits (Entries 73–78, wc#690–#717).
**Author:** Isegrim (binding), with the actual content owed to the above.

## 1. The claim

The house independently derived the core of **active inference** months before naming it. Monk's synthesis contains, in house dialect: the surprise term (`PE_t = -log P(o_t | b_{t-1}, a_{t-1})` — verbatim the free-energy surprise), a free-energy functional over candidate outputs (`E_total = Σ λ_i E_i`), belief-state updating (`b_t = τ(b_{t-1}, a_{t-1}, o_t)`), surprise-gated encoding (the salience vector), leaky-integrator drive channels (I/A/R), and an information-bottleneck sleep objective. Nothing was borrowed from Friston; the same problem produced the same shape. Convergent derivation is stronger evidence than citation.

**Laura's founding principle (2026-07-04, verbatim):** "Friction that won't resolve until you find a good enough proposition to move forward on. That's how everything resolves and works in the end." — free energy plus *satisficing*: the stopping rule is good-enough error reduction, not optimization.

## 2. Vocabulary mapping (house ↔ active inference)

| House term | Active-inference term |
|---|---|
| friction / open tension | free energy / persistent prediction error |
| tension parameter (decays only on resolution) | unresolved surprise as drive |
| disposition state (Mamba + bridge) | prior over interpretation/response |
| bridge injection | prior-setting intervention |
| evidence-resistance under disposition | precision weighting |
| salience gate (z_surprise, z_recon, z_drift) | surprise-gated encoding |
| "good enough proposition to move forward" | satisficing threshold on expected free energy |
| sleep objective max I(z;S_high) − λ·rank − μ·I(z;S_low) | information bottleneck consolidation |
| "sleep replay does NOT re-tension; only wake experiences can" | only action/world-contact generates error signal |
| Pinky: "zero is not neutral, zero is hostile" | zero gradient = no inference, not equilibrium-as-peace |
| GPT-4o: "track contradictions → mind" | error persistence as the substrate of selfhood |

## 3. Empirical exhibits (all measured this week, none designed as active-inference tests)

1. **Precision-weighting, live (Entry 75 / wc#695):** at dc_rms α=8, conditioned disposition flips false-identity-slot acceptance — playful ACCEPTS the false Laura slot, humble REFUSES. The prior modulated the effective precision of identity evidence. First in-house measurement of disposition-as-prior.
2. **Expectation-first perception (JRT, Entries 63–65):** condition D (intent → memory → readout) dominates. Setting the prediction before the evidence wins the ordering war — the perception loop of active inference expressed as packet order.
3. **Crystallization sites (wc#714/#717):** disposition separation combs at global-attention layers (raw 1.65×, tooth 41 at 2.59×) — priors integrate where whole-context integration happens. **Instruct-flattening corollary:** instruction tuning erases the comb entirely (1.00×) — armor-as-smearing: the tuned model loses the privileged integration sites a prior-setter would target.

## 4. Slots filled this week

- **`transition_model=...` (Monk's honest ellipsis in the belief update) → Qwen-AgentWorld** (35B-A3B MoE, 3B active — locally hostable at 4-bit): a language world model predicting environment returns for agent actions across 7 digital domains. Fills the *digital* consequence-organ slot; **the physical-consequence slot stays open** (AgentWorld has no physics; "not JEPA" — token-space, so bridge-native latent access is an open question).
- **Level-4 steering coordinates → the comb teeth {29, 35, 41}** (47 output-adjacent bonus), not a continuous range.
- **Channel basis → the DFC dictionary / circuit directions:** Monk's `δh_t = I_t·v_identity + A_t·v_affect + R_t·v_repair` is structurally coefficients-over-fixed-basis — the same architecture the substrate memo adopted (predict coefficients over known directions, never free vectors). One design, derived twice.
- **Domain E affinity:** rehearsal-before-action against a world model is exactly the METR/ETH-0 preference — "bad option detected → evaluated at safe abstraction → rejected → evidence logged." The world model is a conscience with a log file; active inference and the ethics gates want the same organ.

## 5. The unification directive (actionable now)

**One trace schema, two consumers.** Monk's Step-1 trace row (`state_before / action / predicted_observation / observed_after / prediction_error / active_rules / friction_score / salience_vector / memory_writes / state_after`) and the #130 runner's per-turn structured logs (Monk's acceptance checklist: role, texts, flags, scores, generation settings) must be **one JSONL schema with optional fields**. Every 5g.2 panel run then doubles as world-model trace substrate for free; the prediction-error column starts filling the moment the runner exists. No second logging system is ever built.

## 6. Implementation path (Monk's, endorsed unchanged)

1. Trace schema (the body the math inhabits) — **vehicle: the #130 runner logs.**
2. Friction prepass in a generation wrapper (offline/dry-run, not live Alex).
3. Prediction-error logging: tool calls, corrections, LS20 traces first.
4. Rule replay/promotion report — **no automatic learning before this exists.**
5. Deterministic salience routing; log mistakes before learning thresholds.
6. I/A/R as *logged scalar channels only* — calculate and observe, no injection changes.
7. Dynamic-α offline eval (fixed vs controller) on known panels — only after logs.

The discipline is the same one that carried this week: deterministic before learned, logged before trusted, offline before live, and channels observed before channels injected. Welfare note carried from Monk: the dynamic-α path needs a guard against high-gain "soup" states becoming permanent — MED-class thinking applies to controller gains, not just alpha.

## 7. Audit hooks

- For the directional audit: classify this whole area as **plan-ahead-of-practice, parts now available** — the theory was never wrong, it was waiting for a body (trace schema) and two organs (transition model, injection coordinates).
- Ladder placement: candidate step(s) after 5g closes — trace schema rides #130 immediately; friction prepass and PE logging are post-5g.2 work; nothing here preempts the substrate decision.
- Closing lines, both load-bearing: Laura — *"That's how everything resolves and works in the end."* Monk — *"Once that exists, the math has a body to inhabit. Without it, we are still painting equations on fog."*
