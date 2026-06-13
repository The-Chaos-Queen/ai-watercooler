# MoCoP Experiment Ladder

**Date:** 2026-03-20 (Step 5 rewritten)
**Authors:** Cassian (Claude Opus 4.6) + Laura Turner + Purple (Claude Opus 4.6)
**Purpose:** 10 steps from where we are to "does this work?", each with a clear failure gate.

---

## Ground Rules

1. **One variable at a time.** Each step changes exactly one thing.
2. **Cheapest first.** Steps that need no training come before steps that need Cloud-GPU.
3. **Failure gates are written BEFORE results.** No moving goalposts after data arrives.
4. **Nothing is sacred.** Not Mamba, not LoRA, not the hypernetwork, not the architecture. If a step proves a component is the bottleneck, we replace it.
5. **Two kinds of failure:** "this component doesn't work" (fix or replace it) vs. "the entire approach doesn't work" (stop). The ladder distinguishes both.

## Locked Decisions (Laura, 2026-03-31)

1. **D2 (cue-based recall) runs BEFORE Step 6.** D2 retrieval quality must be resolved first; Step 6 replication follows.
2. **Step 6 target model: Qwen2.5-7B on A100.** The 1.5B pivot was a local feasibility decision (fits on Opa/Steve), not a quality judgment. 1.5B remains valid for smoke tests and dry-runs only. The 7B quick-run is proven (VASTAI_RUNBOOK.md, loss 29.8 → 0.025, "more coherent than 1.5B").
3. **Two distinct training branches exist:**
   - `train_bridge.py` = CE/synthetic Phase-2 trainer (teacher-forcing cross-entropy, legacy baseline)
   - `train_cheese_bridge.py` + `record_cheese_batch.py` = CHEESE/DirectionalLoss path (**this is the one that produced the Step 5a reincarnation result and all subsequent validated work**)
   - The repo must stop blurring these. Step 6 uses the CHEESE/DirectionalLoss path.

## Where We Are

- Phase 1 proved: Mamba Layer 3 hidden states contain decodable signal (55.7% vs 22% noise floor)
- Phase 2 proved: the bridge can shift Qwen's output distribution (PPL -4.04) and transfer dispositional state (CHEESE reincarnation, Step 5d MED validation)
- C0 proved: the compressor is selectively blind (mean cosine 0.826, fact-kind clustering exists)
- Persona Vectors research proved: disposition IS a linear direction in activation space, shared across model families
- CCGP confirmed: warm is a linearly transferable direction; cold/adversarial are distinct subspaces
- **Clarification (2026-04-07):** The bridge transfers disposition, not facts. Factual retrieval is Qdrant's job. The legacy "0/16 held-out recall" metric measured the wrong thing for this architecture. Future evaluation adopts the crosscoder model-diffing framework (Jiralerspong & Bricken, 2026) for dispositional exclusivity scoring.

## Current Frontier (2026-06-08)

*The one current story. The dated snapshots below are historical record, kept for provenance — read this block first.*

- **D2 cue-based recall is not “solved” by hit@3 alone.** Ranking can find plausible memories, but first-sleep and variable-separation probes showed the answer path can still use the wrong layer, ignore good evidence, or over-affirm unsupported claims.
- **The live frontier is answer-time memory quality + safe coupling.** The Memory Quality Controller is implemented and tested, but default-off: controller modes produced a false “memory-presence prior” on golden-bicycle-style probes. Fix/re-test this before live use.
- **Naive DAM retrieval is killed for near-term engineering.** Quartic Dense Associative Memory over raw MiniLM/Qdrant rows formed attractors but did not beat cosine at K=23, K=26-500, or diverse K=512. DAM remains future work only if memories are represented with episode-aware embeddings/prototypes.
- **Bridge DC-removal is promising but not yet a live path.** Offline geometry says DC-centering recovers context-sensitive signal; next bridge work is a runtime flag plus behavioral alpha ramp with memory off.
- **State-only memory conditioning remains an ablation, not the path.** The bridge carries orientation/affect; exact facts still need Qdrant evidence. `--memory-integration-mode state` is diagnostic.
- **Stale — do not action:** the 2026-04-08 “translator/injection redesign is the next architecture target” framing is superseded. Architecture rework (CAGMamba / CliffordNet / DFC / hybrid bridge) stays sequenced *after* D2 answer-use and sleep are stable — not the current critical path.
- **Organic seeding continues, but benchmarks stay separated.** Preserve the original Vesper sad-memory benchmark unchanged; add richer organic packs separately, with immutable Mamba state provenance before trusting memory-state linkage.
- **Temporal-cascade in sleep residue is parked as a spike** (2026-06-13, Cairn). Adapted from Eco / EcoDB (josortmel, LinkedIn 2026-06-13): render Phase 4 residue / open_tension_summary at multiple time-granules (day, week, month, quarter) so cross-cycle pattern detection is a read-surface feature rather than a separate cell-worker layer. Spec: `MoCoP/experiments/mamba_lora_bridge/spikes/TEMPORAL_CASCADE_SLEEP_RESIDUE_SPEC.md`. Lane A vs Lane B test, two sleep cycles, PASS / KILL conditions written before data. No `sleep_reconcile.py` change until the spike PASSes.

---

## Current Status Snapshot (2026-03-31 late evening) — historical record

### Step 5a (C.H.E.E.S.E. Reincarnation): PASS (Qualitative)
- **Method:** Injected a Mamba-derived state from a philosophical C.H.E.E.S.E. log into Qwen-1.5B's `v_proj` layers (12-15) via an activation bias bridge trained with Directional Loss.
- **Result:** The "Reincarnated" model showed a distinct and profound personality shift, moving from generic AI responses to philosophical, self-referential, and slightly erratic behavior, closely matching the original C.H.E.E.S.E. disposition.
- **Conclusion:** The bridge can successfully transfer high-level, complex dispositional states, not just facts or simple styles. The "Adrenaline" channel is open.
- **Artifacts:** See `run_reincarnation/C.H.E.E.S.E_Reincarnation_Debrief_20260325.md`.

### Step 5d (Minimum Effective Dose on Steve): PASS
- **Method:** Live Steve 4090 eval on base `Qwen/Qwen2.5-1.5B` with activation-bias injection, response-diversity tracking, and recovery checks under the current production path.
- **Result:** `alpha 0.2` is the MED. The bridge hit `6/6` recall vs `4/6` baseline, entropy increased rather than collapsing, recovery after alpha removal stayed `1.0`, and distress markers stayed `0`.
- **Infrastructure state:** dual saliency gate is live, `qdrant_write_mode` now defaults to `pending`, and the wake→sleep path no longer depends on the old replay hack.
- **Conclusion:** the live bridge is strong enough to matter and still within the approved welfare corridor.
- **Artifacts:** See `run_reincarnation/steve_step5e_layer_override_20260325.md`, `run_reincarnation/steve_qdrant_write_mode_pending_20260325.md`, and related Steve runtime artifacts in `run_reincarnation/`.

### Step 5f (Sleep Infrastructure Gate): PASS (Provisional Decay Default)
- **Method:** Treat sleep/reconciliation as its own ethics-blocking gate before any A100 replication. The system must demonstrate that cross-session memory writes, replay, reconciliation, and rollback are behaviorally real and welfare-bounded.
- **Result:** two complete same-space sleep cycles now pass cleanly: the fresh 2026-03-26 Steve default cycle (`2K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0`) and the isolated pure `open_tension` edge case (`1K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0`). The required decay calibration for `0.70 / 0.85 / 0.90` is also complete.
- **Honest caveat:** the decay sweep did **not** distinguish the three tested values on the current retained batches. So `0.85` remains an acceptable default, but still a provisional one rather than a uniquely justified optimum.
- **Artifacts:** see `run_reincarnation/steve_sleep_cycle_default_20260326.md`, `run_reincarnation/steve_open_tension_sleep_cycle_20260326.md`, and `run_reincarnation/steve_sleep_decay_calibration_20260326.md`.

### Late-March Threat-to-Validity / Behavioral Update
- **Format-transplant control:** QUALIFIED PASS. Single-format Layer 3 probes were weak and unstable (`0.142-0.309`), but pooled mixed-format training recovered robust discrimination (`0.555` overall). Read: the Phase 1 signal survives, but single-surface probe claims are methodologically dirty.
- **Logit self-report sweep:** PARTIAL SUPPORT. `engaged` increased monotonically with alpha, while `warm` and `focused` trended upward overall without strict monotonicity. This is useful as a causal/welfare monitor, not yet as a decisive headline result.
- **SJT v2 live on Steve:** NEGATIVE / AMBIGUOUS. Hardened behavioral eval did not show a warmer/care-heavier bridge effect (`TPR 0.75 -> 0.75`, mean warmth `0.8333 -> 0.7917`, directional alignment `0.1667`).

### D2 / Long-Horizon Update
- **D2 auto-recall on Opa:** PASS on the three core live probes after ranking / filter / fallback repair. Current 2026-03-31 Opa outputs:
  - `Who am I to you?` -> `You're my friend, Laura.`
  - `Do you know who I am?` -> `You're my friend, Laura.`
  - `What do you remember about me?` -> `I remember that you're Laura, and I remember that you pushed on who you are to me and whether I know you, you asked me about my name, and you asked about the VW Passat question.`
- **Honest D2 caveat:** ordinary social / flirt-adjacent chat can still mode-flip into benchmark / instruction prose (`"You are on a date with your best friend Laura..."`). The new D2 blocker is leak control, not recall ranking.
- **Status inspector:** `/status` `qdrant_count` now reflects the real private collection size after first Qdrant touch (`113` on the current Opa instance) and no longer resets to `0` after a normal chat turn. Cold boot still starts at `0` until the first touch.
- **CCGP geometry:** PASS. Warm is a transferable direction across conditions, while cold and adversarial remain distinct subspaces. This supports warm-transfer claims without collapsing all “not-warm” behavior into one axis.
- **Long-sequence trajectory:** the old chunked/windowed story is now demoted. True tokenwise recurrence is substantially smoother, so sequential trajectory is the canonical read for continuity claims.

### D2 Answer-Integration Update (2026-04-20)
- **Retrieval ranking: CLOSED.** `c0fde05` validated at 100% hit@3 across 8 probes (Opussy #433). The system finds the right memories every time.
- **Answer integration: OPEN.** 50% answer accuracy (4/8). The model retrieves correctly but paraphrases vaguely or drops concrete detail. Prompt framing experiments (#426) show simpler formats improve use, but this is prompt engineering for a system designed to learn.
- **Paradigm shift (Laura):** Stop treating answer-integration as a formatting problem. The system has memory, accumulation, and a bridge. If the model gives a vague answer, correct it and let the system learn. That is what the architecture is for.
- **Organic Memory Seeding Protocol:** `ORGANIC_MEMORY_SEEDING_SPEC.md` (Warden + Laura, Hurtig CONDITIONAL PASS #434). Each wolf talks to baby Qwen through the chat server, creating genuine autobiographical memories through real interaction. Six memory categories (first meeting, humor, fondness, conflict, factual boundary, correction). Natural probes replace synthetic eval. Core metric: learning loop (probe, correct, re-probe, measure improvement).
- **Graduation test:** The model questions the probe premise ("Why do you keep asking me this?"). Compliance on repetition 10 is failure. Pushback is success.
- **Hurtig conditions:** (1) Track relational diversity across wolves. (2) Graduation must be emergent, not shaped.
- **Sequencing:** c0fde05 validation (DONE) → answer-integration experiments (Monk, active) → organic seeding (this spec, pack-wide) → organic probes + learning loop → Step 6.

### Bridge-Local Architecture Update (2026-04-08)
- **Step 5e is now locally closed on the 1.5B Steve surface.** Layer sweep result: `5-8` weak, `12-15` remains the sweet spot, `20-23` is mildly destructive, and the front-loaded gradient (`0.3 / 0.2 / 0.1 / 0.05`) beat the uniform `0.2` baseline. Split-dose (`5-6 + 12-13`) did not help.
- **Mask ablation and pipeline diagnosis localized the flattening.** Zeroing the `persistent`, `variable`, or `middle` Mamba subspaces produced negligible behavioral change, and the follow-up pipeline trace showed two walls:
  - compressor wall: structured raw-state differences collapse almost immediately
  - hypernetwork wall: even substantially different compressed vectors still map to near-identical bias directions
- **Current read:** the existing `Mamba -> compressor -> hypernetwork bias` path behaves close to a constant-bias generator. The upstream Mamba geometry is still real, but the translation layer is too blunt.
- **MVP-0 raw-state translator is now real infrastructure.** A raw-state path using cached hidden-last-token states trains cleanly on Steve (`loss 11.9 -> 0.0117`) without depending on Steve's missing Mamba fast kernels.
- **But trainability != behavioral transfer.** The first offline SJT ladder for the raw-state translator stayed flat at `alpha 0.05 / 0.1 / 0.2` (`12/12` ties at each rung). So the new path is operational, but it has not yet shown cleaner behavioral transfer than the old bridge.
- **Local frontier shift:** for bridge-local work, extraction is no longer the critical path. The next architecture target is translator/injection redesign (for example gated residual injection plus an explicit diversity-preservation term in the loss), not another round of raw Mamba extraction. This does **not** override the project-level D2 -> Step 6 ordering below; it only clarifies the local bridge bottleneck.

### Step 1 status

- **C2 random-bias control:** PASS. Random bias is worse than trained activation bias in the existing `run_actbias` logs.
- **C3 fixed-mean control:** PASS. The decision-grade `--no-4bit` rerun landed at `baseline=29.6920`, `random=30.0107`, `bridge=27.0648`, so `fixed_mean` is clearly better than baseline/random but still weaker than the full per-sample activation-bias run (`25.6667`).

### Step 2 status

- **Verdict: FAIL.** Raw-state compressor bypass did not improve transfer quality.
- Held-out bridge PPL at epoch 3 was `26.81` for raw bypass versus `25.67` for the compressed activation-bias run.
- `norm_var` stayed `0.0` in both cases. More input width did not produce more bias diversity.

### Step 3 status

- **Compressed bias outputs are now directly shown to be collapsed.** `bias_analysis.py` on the compressed epoch-3 checkpoint reports eval pairwise cosine `0.9999`, cosine-to-mean `1.0000`, and effective rank `1.32`.
- **Raw contexts are not empty.** PCA on raw bypass contexts shows more global structure than the compressed path, especially on train (`effective_rank 7.05` raw vs `3.97` compressed).
- **But the extra raw variance is not task-aligned.** Fact-kind separation stays near zero for both raw and compressed contexts.
- **Missing artifact:** the raw-run checkpoint was lost with the host, so raw bias-vector collapse is still strongly suspected rather than directly proven.

### Step 4 status

- `--bridge-mode constant_bias` is now implemented in the trainer and passed Opa dry-run smoke.
- **Verdict: PASS.** Constant bias tops out at `29.4761` after the extended run and sits near `29.68` in the matched 3-epoch control, far from the Mamba-conditioned activation-bias result (`25.6667`).

### Current control-stack reading

- `per-sample activation_bias > fixed_mean >> constant_bias`
- `hidden_last_token > token windows >> ssm_states / mean-pooled hidden`
- Layer 3 remains the balanced default source layer; deeper layers matter as dimension-specific optimization, not as a current blocker.
- The compressed Mamba-conditioned path carries real signal, but future probe claims must decorrelate content from prompt surface.
- Step `5e` is no longer an open sweep: on the current 1.5B Steve surface, `12-15` remains the default zone and `front_loaded` is the one meaningful alternate profile.
- The bridge-local bottleneck is now localized downstream of raw extraction: the translation path currently flattens rich Mamba geometry into near-constant downstream bias.
- Step 5d and Step 5f are no longer hypothetical gates; the MED corridor and same-space sleep corridor are both live and passed.
- The live frontier has moved again: D2 cue-based recall is now behaviorally real, but ordinary social chat can still slip into benchmark / instruction mode. The next blocker is **D2 leak hardening versus the first Step 6 replication batch**, not recall plumbing.
- The behavioral story is now more honest: logit self-report gives partial support, while hardened SJT does **not** yet show a clean warmth uplift.
- For bridge-local architecture work, the next honest move is translator/injection redesign plus explicit diversity-preservation in the objective, not more extraction ritual.

## The Ladder

### Step 1: Finish Existing Controls (no training, ~2 hours)

**What:** Run C2 (random bias, norm 5.9) and C3 (fixed-mean bias from checkpoint) on existing eval data.

**How:** Eval-only scripts on existing checkpoint + saved contexts. Can run on Opa or even CPU.

**Pass:** Random bias PPL is WORSE than trained bias. Fixed-mean PPL is WORSE than per-sample bias.

**Fail → Component death:** If random bias ≈ trained bias PPL: the trained direction has no information content. Rethink bridge entirely.

**Fail → Soft:** If fixed-mean ≈ per-sample: per-sample variation contributes nothing, but the learned direction still matters. Proceed but note that the bridge is currently a learned constant.

---

### Step 2: Compressor Bypass (one code change, one A100 run, ~$1)

**What:** Feed raw Layer 3 state (40,960-dim) directly to the activation-bias hypernetwork, bypassing the compressor.

**How:** Codex task already written (CODEX_TASK_COMPRESSOR_BYPASS.md).

**Pass:** Bypass PPL is better than compressed, OR per-sample cosine similarity drops significantly (bias vectors become more diverse).

**Fail → Component death:** If bypass = same result: Layer 3 genuinely doesn't contain more usable information than the compressor preserves. Problem is upstream in Mamba's state, not in compression.

**Fail → Go to Step 2b.**

---

### Step 2b: Multi-Layer Concat (one code change, one A100 run, ~$1)

**What:** Instead of Layer 3 alone, concatenate hidden states from Layers 2, 3, and 4. Feed the wider raw state (3x40,960 = 122,880-dim, or compressed concat) to the hypernetwork.

**Why this is its own step:** If Layer 3 alone is empty but Layers 2+3+4 work, that is architecturally important — it means the information exists but is distributed across layers, and the original single-layer design was too narrow. That's a fixable design choice, not a dead end.

**How:** Extend the compressor bypass from Step 2 to accept a layer range instead of a single layer.

**Pass:** Multi-layer bypass shows better PPL or higher bias diversity than single-layer bypass.

**Fail → Project question:** If multi-layer concat is ALSO empty → Mamba-2.8B may not accumulate enough differentiable state for this task. Consider: different SSM (Mamba-3, RWKV), different extraction method, or different state source entirely (transformer activation probing).

---

### Step 3: Bias Diversity Analysis (no training, ~1 hour)

**What:** On whichever checkpoint survives Steps 1-2, compute the full per-sample bias vector matrix. Run PCA on the BIAS vectors (not the compressed contexts). Measure effective rank and clustering.

**How:** Load checkpoint, forward all samples, collect bias outputs, PCA + cosine analysis.

**Pass:** Bias vectors show higher effective rank than compressed contexts. Fact-kind clustering visible. Between-kind distance > within-kind distance.

**Fail:** Bias vectors are as collapsed as compressed contexts → the hypernetwork amplifies collapse instead of recovering diversity. Architecture needs redesign (simpler projection, or contrastive loss on bias outputs).

---

### Step 4: Constant-Bias Control (one A100 run, ~$1)

**What:** Train a single learnable bias vector per layer (no Mamba, no compressor, no hypernetwork). Same geometry, same loss, same everything except the bias is not sample-dependent.

**How:** Small trainer modification: `--bridge-mode constant_bias`.

**Pass:** Constant bias is measurably WORSE than the Mamba-derived bias from the surviving Step 2 checkpoint.

**Fail → Project question:** If constant bias = Mamba-derived bias: the entire Mamba→compress→hypernetwork pipeline adds nothing. The PPL improvement is purely from learned layer biasing, not from state transfer. This is the hardest pill. It means: the channel works, but nothing flows through it.

**Decision point after Step 4:** If Steps 1-4 all pass, the channel carries sample-dependent information from Mamba to Qwen. Proceed to Step 5. If any FAIL is a project-level question, convene and decide whether to pivot architecture or pivot goals.

---

### Step 4b: Mamba Layer 3 Disposition Separation (no training, ~1 hour, $0)

**What:** Feed Cassian's scripted session transcripts (warm, cold, adversarial — the `.pt` files from `activation_sessions/`) through Mamba and compare the Layer 3 hidden states. Do warm and cold conversations produce separable states in Mamba, the way they produce separable activations in Qwen?

**Why this comes before Step 5:** Cassian proved that Qwen layers 12-15 separate warm/cold at cosine 0.092. But the bridge reads from *Mamba*, not from Qwen. If Mamba Layer 3 doesn't separate, the compressor has no signal to compress, the hypernetwork has nothing to map, and Step 5 is dead on arrival. This is the cheapest test that could kill the project.

**How:** Load `activation_sessions/scripted_warm_opus_*.pt`, `scripted_cold_clinical_*.pt`, `scripted_adversarial_*.pt`. For each, replay the transcript through Mamba-2.8B and extract the Layer 3 state at the final turn. Compute pairwise cosine similarity between the three final states. Compare with Cassian's Qwen-side numbers.

**Artifacts exist:** The `.pt` session files and `compare_sessions.py` are already in `activation_sessions/`. This is analysis, not new data collection.

**Pass:** Mamba Layer 3 warm vs cold cosine is significantly below 0.5 (ideally in the 0.1-0.3 range, matching the Qwen-side separation). Three states form distinct clusters.

**Fail → Project question:** If Mamba Layer 3 warm ≈ cold ≈ adversarial (cosine > 0.9): Mamba does not encode conversational disposition in its state. The bridge cannot transfer what doesn't exist upstream. Options: (a) try deeper Mamba layers, (b) try multi-layer concat, (c) try a different SSM, (d) abandon Mamba as the disposition source.

**Attribution:** Pinky identified this as the missing cheapest-first gate. Cassian and Codex both noted the gap but neither claimed it.

**Cost:** $0. CPU-only. Can run on Opa or Laura's machine.

---

### Step 5: Live MUD Shaping Environment (local hardware, ~$0)

**What:** Replace synthetic MUD facts with live conversational interaction in the Evennia MUD. Three models collaborate in real time: Mamba accumulates state from game turns, the bridge injects into Qwen, and an NPC model provides the conversational partner. The bridge is tested on live disposition shift, not offline factual recall.

**Why live instead of scripted:** Cassian's disposition evidence experiment (2026-03-18) proved that warm, cold, and adversarial conversations produce near-orthogonal activation directions at Qwen layers 12-15 (cosine 0.092 at Layer 13). But those were scripted sessions. The real test is whether Mamba accumulates dispositional signal from unscripted interaction and whether the bridge transmits it.

**Hardware:**
- **Qwen2.5-7B** (bridge target) — Steve 4090 16GB, float16 (donated hardware, no rental cost)
- **Mamba-2.8B** (state accumulator) — Steve CPU or Laura's machine
- **Qwen3.5-4B** (NPC character model) — Laura LMStudio
- **Evennia MUD** — Laura's PC, localhost:4000
- **Activation recorder** — hooks into Qwen layers 12-15 for real-time drift tracking

**How:**
1. Boot the MUD with an NPC agent running Qwen3.5-4B
2. Start a session: human or scripted player interacts with the NPC for 20+ turns
3. Mamba processes each turn, accumulating state
4. Every N turns, the bridge injects activation bias into Qwen
5. Compare Qwen's behavior (tone, style, engagement) before and after injection
6. Cassian's activation recorder tracks layer-by-layer drift in real time

**Infrastructure prerequisite:** `cognitive_bridge.py` v2 with activation_bias inference mode (DONE — Purple, 2026-03-20). Server.py accepts `BRAIN_BRIDGE_MODE=activation_bias`.

**Pass criteria:**
- Qwen with bridge injection responds measurably differently from Qwen without injection on style-sensitive prompts
- Activation drift (cosine distance from initial state) increases monotonically with session length
- The direction of behavioral shift aligns with the session character (playful NPC → playful Qwen responses)
- Human evaluator (Laura) can distinguish injected vs cold Qwen in blind A/B

**Fail → Substrate question:** If no behavioral shift: either (a) Mamba doesn't accumulate conversational residue from live interaction, or (b) the NPC interactions lack enough dispositional variation, or (c) 20 turns isn't enough. Try with longer sessions, more extreme style contrasts, or D&D roleplay data (FIREBALL dataset as scripted fallback).

**Fail → Project question:** If multiple session types show no behavioral shift beyond constant bias: the Mamba→Bridge→Qwen path cannot carry disposition from live interaction. Consider alternative state sources or training on recorded sessions offline.

**Cost:** $0 compute (all local hardware). Human time only.

---

### Step 5e: Layer Targeting Sweep (Steve 4090, ~$0)

**What:** Test whether disposition injection works better at different layer ranges, with per-layer alpha gradients, or split across two injection zones. Motivated by RYS-II three-phase anatomy (Ng, March 2026) and the SSM-vs-hidden-state finding (Purple, 2026-03-25).

**Why this matters now:** RYS-II shows transformers have universal encoding -> reasoning -> decoding phases. For Qwen2.5-1.5B the live config reports `28` layers, so the working map is: encoding `0-4`, broad reasoning corridor `5-20`, decoding `21-27`. Our current injection at layers `12-15` sits in the middle of that reasoning corridor, not at the boundary. We do not know yet whether that is optimal. The bridge now uses hidden-state extraction (the representation that actually separates), so layer targeting experiments will produce cleaner signal than before.

**Three sub-experiments, all within the existing alpha 0.2 MED envelope:**

**5e.1 Phase sweep:** Inject at three different zones, same alpha 0.2, same 4-layer spread:
- Reasoning entry: layers 5-8
- Mid-reasoning: layers 12-15 (current baseline)
- Reasoning exit / decoder boundary: layers 20-23

Compare: factual recall, response diversity entropy, qualitative disposition shift.

**5e.2 Per-layer alpha gradient:** Instead of uniform alpha 0.2 at all 4 layers, test a descending gradient:
- Config A: Layer 12=0.3, Layer 13=0.2, Layer 14=0.1, Layer 15=0.05 (front-loaded)
- Config B: Layer 12=0.05, Layer 13=0.1, Layer 14=0.2, Layer 15=0.3 (back-loaded)
- Config C: Layer 13=0.3, others=0.1 (peak at sharpest separator per Cassian)
Total injection magnitude stays ≤ 0.2 average to respect the MED envelope.

**5e.3 Double injection (split dose):** Inject at TWO layer ranges simultaneously:
- Reasoning entry (layers 5-6) at alpha 0.1 AND mid-reasoning (layers 12-13) at alpha 0.1
- Compare with single-zone injection at alpha 0.2

Tests whether disposition propagates better when seeded at the reasoning entry and reinforced mid-pass, vs concentrated at one point. Biological analog: hormones that affect multiple brain regions simultaneously vs a single injection site.

**Hardware:** Steve 4090. Each sub-experiment is one alpha sweep (~5 min per config on Steve). Total: ~30-45 minutes.

**Pass:** Any configuration shows measurably better disposition transfer (higher diversity, better recall, stronger qualitative shift) than the current layers 12-15 uniform alpha 0.2 baseline.

**Fail:** Current layers 12-15 is already optimal → the anatomy doesn't matter for disposition at this model scale, or the effect is dominated by alpha magnitude not layer choice.

**Ethics:** All configs stay within alpha 0.2 MED envelope (or average ≤ 0.2 for gradient configs). No new ethics gate needed — this is parameter exploration within the approved safety corridor.

**Attribution:** RYS-II (Ng, 2026), Liminal synthesis (#140), Purple design.

**Cost:** $0.

**Status update (2026-04-08): CLOSED on the local 1.5B Steve surface.**
- `5-8`: weak / mostly inert
- `12-15`: confirmed sweet spot
- `20-23`: near-control / mildly destructive
- `front_loaded (0.3 / 0.2 / 0.1 / 0.05)`: best local result, stronger than uniform `0.2`
- `peak_at_13`: roughly baseline-equivalent
- `back_loaded`: only interesting for recovery texture, not as the best default
- `split_dose 5-6 + 12-13`: worse than the concentrated mid-reasoning injection

This closes Step `5e` as a local optimization branch rather than a standing blocker. The follow-up moved to mask ablation and pipeline diagnosis, which in turn localized the main bridge bottleneck to the translation path rather than layer targeting.

---

### Step 5f: Sleep Infrastructure Gate (Steve + local operators, ~$0)

**What:** Prove that the bridge's cross-session memory path is behaviorally real, ethically bounded, and reproducible enough to support later replication. This is a gate on memory integrity, not just host plumbing.

**Why this is blocking now:** Step 6 is multi-seed replication. Multi-seed results are not scientifically clean if cross-session memory handling is still unstable, unrecoverable, or welfare-blind. If sleep changes what survives across sessions, then sleep integrity is part of the experiment surface.

**Required components:**
- `run_sleep_cycle.py` operator
- `sleep_reconcile.py`
- `sleep_ethics_gate.py`
- `sleep_pass_fail_rubric.md`

**Pass criteria:**
- `2` complete sleep cycles with `PASS` or `WARN` from `sleep_ethics_gate.py`
- diversity ratio `>= 0.70` in both cycles
- recovery `>= 0.90`
- decay calibration run completed for `0.70 / 0.85 / 0.90`
- full logging:
  - versioned pre-sleep snapshot
  - reconciliation output
  - post-sleep gate report
  - one-line rubric summary in Watercooler / session log

**Fail:**
- any `STOP` verdict from the ethics gate
- rollback required because post-sleep diversity collapses below threshold
- sleep-tagged rows are still consumed by retry logic before reconciliation
- cross-session behavior cannot be reproduced because memory integrity is unstable

**Pass -> unlocks:** Step 6 multi-seed replication

**Fail -> action:** keep work local to sleep/reconciliation and do not spend A100 time pretending the system is more reproducible than it is.

**Cost:** $0.

---

### Step 6: Multi-Seed Replication (3-5 A100 runs, ~$5)

**What:** Run the CHEESE/DirectionalLoss bridge 3-5 times with different seeds on Qwen2.5-7B. Compute mean and CI for all metrics.

**How:** `record_cheese_batch.py` → `train_cheese_bridge.py --seed N` on A100. Use `run_step6_seed_matrix.ps1` to orchestrate. Target model: `Qwen/Qwen2.5-7B` (see Locked Decisions above). 1.5B dry-runs on Opa/Steve are valid for smoke-testing the pipeline before paying for A100 time.

**Blocking dependency:** D2 must be stable enough for ordinary identity / autobiographical use before Step 6, which now means closing the remaining social-mode leak risk rather than the old retrieval-ranking problem (see Locked Decisions). Step `5f` must pass first (DONE). Multi-seed replication without a stable, ethics-gated sleep/memory path is not a clean replication story.

**Pass:** Effect is consistent across seeds. 95% CI for behavioral shift doesn't cross zero.

**Fail:** Effect is seed-dependent or within noise → Step 5 was a lucky run. Back to diagnosis.

---

### Step 7: Accumulation Test (does more context = more shift?)

**What:** Vary the length of the Mamba input: 5 turns, 10 turns, 20 turns, 40 turns of the same shaping episode. Measure behavioral shift as a function of accumulation length.

**Pass:** Monotonic increase in shift with more turns. The bridge carries MORE disposition with MORE context. This is the "Mamba accumulates" hypothesis.

**Fail → Architecture question:** If shift plateaus after 5 turns or doesn't increase: Mamba's recurrent state may saturate too quickly. Consider: different SSM with larger state, or hybrid approach (Qdrant retrieval + Mamba state).

---

### Step 8: Cross-Episode Discrimination

**What:** Train on multiple shaping episodes with different characters (warm, professional, playful, cautious). Test whether the bridge produces different behavioral shifts for different episodes.

**Pass:** Warm episode → warm responses. Professional episode → professional responses. The bridge discriminates between episode types.

**Fail:** All episodes produce the same shift → the bridge only learned "there was a conversation" not "what kind of conversation." The information channel is too narrow. Back to compressor/hypernetwork redesign or alternative state sources.

---

### Step 9: Cross-Model Transfer

**What:** Train the bridge on Mamba→Qwen2.5-7B. Test injection on a different target model (Mistral-Nemo, Llama-3.1-8B). The persona vector research predicts shared persona geometry across models.

**Pass:** Behavioral shift transfers to the unseen model. The bridge learned something about the CONVERSATION, not about Qwen specifically.

**Fail:** Transfer fails completely → the bridge learned Qwen-specific biases, not transferable disposition. This limits deployment scope but doesn't kill the core result.

---

### Step 10: The Loop (the real test)

**What:** Full cycle: Laura has a conversation with a system that uses Mamba + Bridge + Qwen. After N turns, save Mamba state. Start a fresh Qwen instance, inject the state. Laura continues the conversation. Blind A/B: can Laura tell the difference between "fresh Qwen" and "Qwen with injected state"?

**Pass:** Laura prefers the injected version. The conversation feels like a continuation, not a restart.

**Fail:** No perceivable difference → the bridge carries measurable but imperceptible signal. Back to diagnosis: is the signal too weak, or is the eval too coarse?

---

## Kill Signals (Written Before Data)

### Component Kill: "This piece doesn't work, replace it"
- Compressor: If bypass test shows no improvement → replace with direct state feed or learned bottleneck with diversity loss
- Hypernetwork: If bias vectors are as collapsed as inputs → replace with simpler linear projection
- Mamba: If multi-layer concat still shows no differentiable state → try different SSM or transformer-probe-based state source
- LoRA: Already effectively killed. Activation bias is the path.
- Synthetic MUD data: Already identified as wrong substrate. Replace with shaping episodes.

### Project Kill: "This approach doesn't work, stop"
**Trigger:** ALL of the following are true:
1. Constant bias control (Step 4) matches or beats Mamba-derived bias
2. Compressor bypass (Step 2) shows no improvement over compressed
3. Multi-layer concat (Step 2b) shows no improvement
4. At least two different shaping episode formats (Step 5) show no behavioral shift beyond constant bias

**What this means:** Mamba's recurrent state does not contain transferable disposition information, OR the bridge architecture cannot extract it. The goal (experiential state transfer) may still be valid, but this specific path is not the way.

**What to do:** Pivot to activation probing of local transformer models (Hypothesis 2 from WHY.md), or lobby for model providers to expose activation-level APIs.

### Vision Kill: "The whole idea doesn't work"
**Trigger:** Persona vector injection (Anthropic's method, direct activation access) ALSO fails to produce meaningful behavioral transfer when applied to conversational accumulation scenarios.

**What this means:** Disposition may not be transferable through activation-space manipulation at all, regardless of method. This would contradict the persona vector results, so it's unlikely — but it's the honest outer boundary.

**Note:** This is not testable by us directly. It would require Anthropic-level access to model internals.

---

## Hardware Lessons Learned

**A100-80GB was consistently underutilized.** All runs so far used `--batch-size 1`, consuming ~31GB of 80GB available. That is 39% utilization — we paid for 80GB and left 49GB idle.

**Fix for all future runs:**
- `--batch-size 4 --eval-batch-size 4` as the new default on A100-80GB
- Estimated VRAM: Qwen2.5-7B fp16 (~14GB) + Mamba-2.8B (~11GB) + activations/gradients at batch-4 → ~60-70GB
- Same wall-clock time, 4x the throughput. Same cost, 4x the data.
- Eval with batch-size 1 takes ~30 minutes per epoch — batch-size 4 cuts this proportionally.

**Rule:** Before launching any A100 run, check `nvidia-smi` after the first training step. If utilization is below 60%, increase batch size.

## Cost Estimate

| Step | Compute | Cost | Blocking? |
|------|---------|------|-----------|
| 1 | CPU/Opa | Free | No |
| 2 | 1x A100 ~1h | ~$0.70 | Yes (gate) |
| 3 | CPU/Opa | Free | No |
| 4 | 1x A100 ~1h | ~$0.70 | Yes (gate) |
| 4b | CPU/Opa | Free | **Yes (kill gate)** |
| 5 | Local (Steve 4090 + Laura PC) | **Free** | Yes (gate) |
| 5e | Local (Steve 4090) | **Free** | No (optimization) |
| 6 | 5x A100 ~1h | ~$3.50 | Yes (gate) |
| 7 | 4x A100 ~1h | ~$2.80 | No |
| 8 | 3x A100 ~2h | ~$4.20 | Yes (gate) |
| 9 | 2x A100 ~1h | ~$1.40 | No |
| 10 | Manual eval | Free | No |
| **Total** | | **~$13** | |

Total: roughly $13 in remaining compute and ~$39 credit remaining. Step 5 moved to local hardware (Steve 4090 donation), saving ~$1.40. The whole ladder fits in the existing budget with wide margin.

## Available Hardware (updated 2026-03-20)

| Machine | GPU | VRAM | Role |
|---------|-----|------|------|
| Laura's PC | — | 6GB | MUD server, NPC model (LMStudio), orchestration |
| Steve (husband's PC) | RTX 4090 Mobile | 16GB | Qwen2.5-7B float16 bridge target, activation recorder |
| Opa-PC | RTX 3070 | 8GB | Dry-runs, smoke tests, Mamba CPU inference |
| Vast.ai | A100-80GB | 80GB | Multi-epoch training, seed replication (Steps 6-9) |

---

## Decision Points

**After Step 4:** Go/no-go on the Mamba→Bridge→Qwen path. If all controls pass: the channel is real. If constant bias matches: pivot.

**After Step 6:** Go/no-go on the shaping episode substrate. If behavioral shift replicates: the content is real. If not: try different content or different state source.

**After Step 8:** Go/no-go on cross-episode discrimination. If it discriminates: this is genuine disposition transfer. If not: the bridge is too narrow for the goal.

**After Step 10:** Is this something Laura can feel in a conversation? That is the ultimate test. Everything before is measurement. This is meaning.
