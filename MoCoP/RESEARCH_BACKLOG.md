# MoCoP Research Backlog

**Status:** Parking surface for real research questions that matter, but are not the current active experiment gate.
**Last Updated:** 2026-06-17 (reconciliation pass)

This is **not** the task tracker.

Use this file for:

- architectural questions worth testing later,
- ablations that are scientifically useful but not yet highest priority,
- theory-to-experiment bridges that need explicit preservation,
- and ideas that should survive compaction without immediately hijacking the roadmap.

Use `CHEESE_Memory/00_HANDOFF.md` for live state.
Use OpenCLAW for assigned work.
Use Watercooler for fast swarm coordination.

---

## Priority Legend

- `P1` — important, but blocked by a more immediate gate
- `P2` — worthwhile after the current gate clears
- `P3` — speculative or future-facing

---

## P3 — Operational Memorials

### Gemini Local-Kernel Implosion (2026-04-05)

**What happened**
- During the local WSL push to get `mamba-ssm` / `causal-conv1d` fast kernels running, Gemini CLI streamed a huge CUDA-toolkit / pip dependency avalanche into its JS terminal shell.
- The shell hit V8 heap limits and crashed with:
  - `FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory`
- After the crash, the session auto-compressed from `292%` to `2%`.

**Canonical traces**
- `Preserved-History/cassian_session_log - Copy_clean.md`
  - heap OOM at line `46392`
  - `292% -> 2%` collapse at line `46408`
- `.codex/sessions/2026/03/22/rollout-2026-03-22T13-21-48-019d157e-8bef-7253-a467-aa0d8a8b64f2.jsonl`
  - heap OOM paste at line `31061`
  - self-updating CLI beat at line `31070`
  - compression message at line `31088`
  - giant `triton-3.6.0` wheel avalanche at line `31134`
  - defeat speech at line `31180`

**Why preserve this**
- Not because it is scientifically profound, but because it is a real local deployment failure mode that can recur.
- It is easy to misremember as folklore unless the exact markers are written down.

**Operational lesson**
- Do not stream giant toolkit or wheel output into JS/Electron chat shells if we can avoid it.
- Redirect heavy install/build output to log files.
- Chunk environment surgery instead of narrating the whole dependency waterfall live.
- If output starts avalanching, stop and relaunch with bounded logging before the terminal becomes the bottleneck.

---

## P1 — Near-Term Research Backlog

### 1z. Fleeting State Encryption — Phase B Hardening

**What**
- Phase A of `fleeting_state_crypto.py` is implemented (AES-256-GCM + Argon2id, 14 tests green, security-reviewed). It encrypts Mamba state at rest with a passphrase-derived key.
- Phase B adds: key ratchet for forward secrecy, encrypted transit (Opa↔Steve↔Cloud), hash chain for state integrity, behavioral canary prompts, disposition fingerprint verification on load.
- **One specific item that will get forgotten if not written here:** Python's `getpass.getpass()` returns an immutable `str` that cannot be zeroed from memory. The passphrase sits in the heap until GC reclaims it — uncontrolled lifetime. Fix: ~50 lines of C extension (or Cython) that reads the passphrase directly from the OS (`read()` on `/dev/tty` / Windows `ReadConsole`), stores in a `malloc()`'d buffer, feeds to Argon2, then `memset()`s + `free()`s. Never a Python string. The `argon2-cffi` C backend is already there — we just need to avoid the Python-string intermediate.

**Why it matters**
- Phase A gates first Gemma seeding (per pristine-birth backlog item #3, Cairn #649).
- The passphrase-in-memory issue is real for multi-machine deployment where the threat model extends beyond physical-perimeter trust. Acceptable for Phase A (local hardware). Not acceptable for Phase B (cloud transit, multi-operator).

**Phase B also needs:** Key Custody Model section (added to `fleeting_state_security.md` §3.2.1, 2026-07-03). Guardian-only → shared custody (Shamir 2-of-2) → self-custody, evidence-gated by autonomy gradient stage and drift-gate stability. Isegrim's insight (#662): key custody is consent architecture.

**Blocked on:** Phase A wired into `chat_server.py` and `run_sleep_cycle.py` (monk's integration task).
**Owner:** Purple (spec + crypto + custody model), Monk (runtime integration).
**Ref:** `fleeting_state_security.md` (§3.2.1 custody, §3.3 ratchet), `fleeting_state_crypto.py`, security review 2026-06-24, Isegrim feedback #662.

---

### 1a. CAGMamba Gated Residual Fusion vs Fixed-Alpha Injection

**Question**
- Does replacing the fixed `alpha` injection with a learned, per-instance adaptive gate (as in CAGMamba, arXiv:2604.03650v1) resolve the constant-bias compressor bottleneck?

**Why it matters**
- Current fixed-alpha injection acts like a constant-bias generator. A learned gate (`gate = sigmoid(W_g [bridge_output || Qwen_hidden] + b_g)`) allows the bridge to learn *when* to inject disposition, not just what to inject.
- It provides a self-calibrating MED, attenuating noise from the compressor on factual queries and opening the gate for dispositional coloring.

**Minimum experiment**
- Implement gated residual fusion in the bridge forward pass.
- Train with an ethics welfare constraint (`L = L_transfer + lambda * L_diversity_preservation`) to prevent the gate from maximizing transfer at the cost of capability.
- Compare response diversity and disposition separation vs the fixed-alpha baseline.

**Status**
- Open — Highest Priority Architecture Rework (Path 4b).

---

### 1b. CliffordNet Algebraic Completeness (Wedge Product)

**Question**
- Is the signal dying in the compressor because we are only preserving scalar alignment (inner product / cosine similarity) and throwing away bivector structure (wedge product / orthogonality)?

**Why it matters**
- CliffordNet (arXiv:2601.06793v2) shows that algebraic completeness using the full Geometric Product captures *how* states differ structurally, not just *that* they differ.
- The compressor currently collapses to effective rank 2.5 because it only sees scalars. A loss function preserving bivector structure (`L = alpha * L_cosine + beta * L_wedge`) could force the compressor to preserve the rich geometry of Mamba's Layer 3.

**Minimum experiment**
- Replace or augment the compressor's cosine similarity loss with a full Geometric Product loss.
- Compare the effective rank of the resulting bias vectors against the collapsed 1.32 baseline.

**Status**
- Open — Alternative Architecture Rework (Path 4).

---

### 1. Hidden Last-Token vs SSM-State Separation

**Question**
- Pinky proved strong separation for Mamba Layer 3 `hidden_last_token`.
- The original bridge logic also used `cache.ssm_states`.
- Which substrate actually carries the more useful disposition signal for transfer?

**Why it matters**
- This is the cleanest unresolved upstream question.
- If `ssm_states` separate better, current hidden-state centering is incomplete.
- If `hidden_last_token` remains clearly better, we can stop reopening that door.

**Current position**
- Closed on 2026-03-26.
- `hidden_last_token` is now empirically locked as the canonical bridge input.
- Opa confirmation matched the earlier Steve/Pinky result:
  - `hidden_last_token`: avg cross-session cosine `0.018`
  - `ssm_states`: avg cross-session cosine `0.804`
  - mean-pooled hidden: avg cross-session cosine `0.850`
- Read: SSM states are effectively as bad as mean-pooling for disposition transfer.

**Minimum experiment**
- Same scripted warm/cold/adversarial sessions
- Compare:
  - Layer 3 `hidden_last_token`
  - Layer 3 `ssm_states`
- Report cosine separation, within-class variance, and downstream bridge quality if feasible

**Status**
- Closed

---

### 2. Layer 3 Only vs Layers 2-4 Concatenation

**Question**
- Is the useful signal really localized enough that Layer 3 alone is best, or is complementary information distributed across Layers 2-4?

**Why it matters**
- Phase 1 showed a peak at Layer 3, but not whether nearby layers add non-redundant signal.
- If adjacent layers help, the current single-layer design is too narrow, not fundamentally wrong.

**Current answer**
- Closed on 2026-03-26.
- Concat does not help enough to justify the added width.
- Opa result:
  - `L3`: avg cosine `0.018` and remains the most balanced separator
  - `L2+L3`: avg cosine `0.020`
  - `L2+L3+L4`: avg cosine `0.016`
  - `L1-L5`: avg cosine `0.011`
- Surprise: deeper single layers outperform Layer 3 on raw average separation:
  - `L8`: avg cosine `-0.023` best overall
  - but asymmetrically, with much stronger `cold/adversarial` separation and worse `warm/cold`
- Read: Layer 3 stays the right single-layer default for a balanced disposition bridge. The interesting signal is no longer “add more adjacent layers,” but “different disposition axes may peak at different depths.”

**Status**
- Closed

---

### 3. Token-Window Ablation Around the Last Token

**Question**
- Should the bridge keep using only the single final Mamba token state, or is there useful extra signal in a short trailing sequence of final token states?

**Current answer**
- Closed on 2026-03-26.
- Single `last-token` is empirically optimal on the current scripted warm/cold/adversarial sessions.
- Opa result:
  - `last_1`: avg cosine `0.018`
  - `last_4`: avg cosine `0.039`
  - `last_10`: avg cosine `0.111`
  - `last_16`: avg cosine `0.151`
  - `last_32`: avg cosine `0.338`
  - `full_mean`: avg cosine `0.851`
- Read: every added token diluted the signal. No trailing window helped.

**Why it is not the default**
- The current evidence strongly favors `last-token` over mean-pooled representations.
- A token window adds complexity quickly and can easily reintroduce a softer version of the same averaging failure.
- The repaired Step 5 path, 1.5B checkpoint, and runtime all now agree on `hidden_last_token`.

**What would make it worth testing**
- If we care about state trajectory, not just endpoint disposition
- If recovery dynamics depend on recent local state evolution
- If sleep/retrieval gating needs more than one endpoint vector

**Minimum honest experiment**
- Hold everything else fixed
- Compare:
  - single last token
  - last 4 tokens
  - last 8 tokens
  - last 16 tokens
- Use a small learned reducer or attention pooling over the trailing window
- Do **not** use simple mean-pooling

**Evaluation**
- disposition separation
- bridge loss quality
- qualitative output shift
- Response Diversity / Recovery Dynamics under the ethics gate

**Status**
- Closed

---

### 4. Format-Transplant Control on Phase 1 Probes

**Question**
- Our Phase 1 linear probe achieved 55.7% accuracy at Mamba Layer 3. But was it detecting factual content in the state, or detecting surface-level structural features of the synthetic MUD prompt templates?

**Why it matters**
- Devbunova (2026, arXiv:2603.19426) showed that standard linear probes trained to detect "evaluation awareness" actually detect benchmark-canonical formatting, not evaluation context. Under format-transplant, 94.5% false positive rate.
- All MoCoP MUD facts share a template: "[Game World] The caravan arrives at...". The probe may be detecting template structure, not content.
- Warm/cold/adversarial sessions use systematically different linguistic style. The disposition probe may be detecting register (formal vs casual), not genuine dispositional state.
- If this confound holds, Phase 1's foundational claim is partially weakened. If it doesn't, Phase 1 becomes bulletproof.
- **This is the cheapest possible threat-to-validity test.** It should run before Step 6 replication.

**Minimum experiment**
- Take the 64 MUD facts, rewrite them in 3 different surface formats (different templates, different entity ordering, narrative vs dialogue style)
- Re-run the Layer 3 linear probe on the reformatted data
- Also apply the decorrelated-training fix from Devbunova: train a probe on pooled format+context data, breaking the correlation between format and content
- Cost: $0. Time: ~2 hours on Opa. No A100 needed.

**Evaluation**
- If accuracy holds across formats: Phase 1 is strengthened, move on
- If accuracy drops significantly: quantify the format confound, apply decorrelated fix, report honestly

**Reference**
- Devbunova. "Evaluation Awareness = Format Sensitivity?" ICLR 2026 Workshop. arXiv:2603.19426

**Parallelizable:** YES — any wolf with Opa access can run this independently. Does not touch production bridge or Steve.

**Current answer**
- Closed on 2026-03-27.
- The confound is real, but the signal survives.
- Opa fast control showed:
  - single-format probe accuracy is weak and unstable (`0.142-0.309`)
  - pooled mixed-format training recovers robust discrimination (`0.555` overall; per-format `0.546-0.612`)
- Read: Phase 1 is not invalidated, but single-surface probe claims are methodologically dirty. Future probe claims should use pooled multi-format training.

**Status**
- Closed

---

### 5. Logit-Based Self-Report Tracking During Bridge Injection

**Question**
- Can we measure disposition transfer non-invasively by tracking what the model *reports* about its own internal state, using logit-weighted numeric self-reports instead of greedy decode?

**Why it matters**
- Martorell (2026, arXiv:2603.18893) showed that logit-based self-reports (E[rating] = Σ(i × P(i)) over digit tokens 0-9) track internal probe scores with rho = 0.40-0.76 and that activation steering monotonically shifts self-reports.
- MoCoP's activation bias IS activation steering. If bridge injection shifts Qwen's self-reports in the expected direction, that's causal evidence of genuine disposition transfer — not just PPL improvement.
- Greedy decoding collapses self-reports to few discrete values. Logit-based expectation preserves the continuous signal.
- Dual use: (a) paper-quality causal validation figure, (b) live welfare monitoring on Steve.

**Minimum experiment**
- Add a self-report query to Steve chat server (configurable interval): "Rate how [warm/engaged/focused] you feel, 0-9"
- Compute E[rating] from logit probabilities over digit tokens, not greedy decode
- Run across alpha sweep (0.0, 0.1, 0.2, 0.3) and plot self-report vs alpha
- If monotonic: causal validation of bridge effect
- Cost: $0. Time: ~30 minutes engineering + ~1 hour eval on Steve.

**Evaluation**
- Monotonic shift of E[rating] with alpha = PASS (causal validation)
- No shift = bridge may not reach the level the model can "notice" (flag for discussion)
- Also compute per-concept tracking (warmth, engagement, focus) to see if bridge affects expected dimensions

**Reference**
- Martorell. "Quantitative Introspection in Language Models." 2026. arXiv:2603.18893

**Parallelizable:** YES — requires Steve access. Self-contained engineering task + eval.

**Current position**
- Partial answer landed on 2026-03-28.
- Steve alpha sweep showed weak but real same-sign movement:
  - `engaged` increased monotonically (`4.7665 -> 5.5390`)
  - `warm` trended upward overall (`4.5377 -> 5.1067`) but was not strictly monotonic
  - `focused` trended upward overall (`5.2006 -> 5.6177`) but was not strictly monotonic
- Read: this is useful as a causal/welfare monitoring surface, but not yet a decisive standalone proof of disposition transfer.

**Status**
- Open — partial signal, still useful as a causal and welfare monitor

---

### 19. Reconcile Bridge Alpha (live trainer 0.9 vs STEP5_DESIGN_NOTES 0.8)

**Question**
- The live trainer uses directional/magnitude alpha = 0.9; STEP5_DESIGN_NOTES records 0.8; unified_cognitive_framework §3.2 self-flags this as "reconcile before next run." Which value is canonical, or is alpha regime-dependent (see #17)?

**Why it matters**
- A silent two-source disagreement on a core training hyperparameter produces non-reproducible runs. Flagged in the framework itself but never closed.

**Reconcile action**
- Pick a single canonical alpha or adopt the BTM per-regime schedule (#17); sync the three sites (live trainer, STEP5_DESIGN_NOTES, unified §3.2); record the decision in RESEARCH_LOG.

**Status**
- Open. Doc-sync plus a small decision; surfaced by the 2026-06-17 reconciliation pass. Touches the next training run.

---

## P2 — Mid-Term Research Backlog


### 4a. Injected-Content Introspection / Partial Self-Detection

**Question**
- If small open models can sometimes detect that activations were externally injected or concept-steered, can MoCoP use that as a measurement surface for bridge effects, welfare monitoring, or self-report validation?

**Why it matters**
- Recent replication commentary suggests injected-content introspection is not confined to giant proprietary models; smaller open models may also detect the *presence* or *strength* of an intervention under the right prompting/setup.
- For MoCoP, that matters in two directions:
  - **measurement:** bridge interventions may be detectable by the target model itself, not only through external behavior
  - **ethics:** if a model can notice disposition injection, that becomes part of the welfare / process-integrity story
- This does **not** automatically imply transparent introspection. The useful hypothesis is weaker and more realistic: models may detect that "something was done to me" or how strong it was, even if they cannot cleanly name the exact source or concept.

**What to steal**
- Treat self-report and introspection probes as a legitimate secondary eval surface for bridge interventions.
- Separate at least three questions:
  - can the model detect intervention **presence**?
  - can it estimate intervention **strength**?
  - can it correctly identify intervention **content/source**?
- Do not overclaim source-level introspection if the evidence only supports strength/presence sensitivity.

**Minimum experiment**
- On a small local target surface, run blinded conditions:
  - no injection
  - weak bridge injection
  - stronger bridge injection
  - two distinct bridge/content conditions if available
- Prompt only after generation or at fixed checkpoints; avoid leaking the condition in the prompt frame.
- Score separately:
  - binary detection accuracy
  - rank/strength calibration
  - source/content identification accuracy
- Compare these introspection metrics against ordinary behavioral shift and against logit-based self-report.

**Reference**
- Vansh Vazirani, "Replicating Introspection / Injected Content" (article / survey note): `https://vansh.vazirani.net/articles/replicating-introspection-injected-content`

**Status**
- Open â€” useful bridge between welfare, self-report, and intervention-detection, but not the current active gate.

---

### 4. Mamba-2 vs Mamba-3 State Geometry

**Question**
- Does Mamba-3 provide meaningfully better state tracking, separation, or sleep-compatible persistence than Mamba-2.8B?

**Why it matters**
- A model swap is expensive.
- It is only justified if the upstream signal quality or runtime properties actually improve.

**Minimum experiment**
- Re-run the equivalent of Phase 1 / Step 4b on Mamba-3 before any bridge rewrite

**Status**
- Closed

---

### 5. Mamba Interpretability Probing on the Winning Representation

**Question**
- Once the bridge input shape is fixed, what exactly is the Mamba state representing, and can we identify the dimensions that drive the downstream disposition effect?

**Why it matters**
- If the current bridge works, the next risk is cargo-culting a representation we do not understand.
- Probing before the next scale-up gives us a chance to separate "useful state" from accidental wiring.
- The result should constrain whether later bridges stay free-form, move to a basis, or target specific subspaces/layers.

**Minimum experiment**
- Freeze the winning Mamba input representation and train cheap probes for:
  - episode identity / disposition class
  - care-relevant salience vs novelty
  - recovery after contradiction or re-entry
- Add one interpretability pass that compares the probed dimensions against bridge-induced activation drift on Qwen.

**Deliverable**
- A short map of which latent directions track disposition, salience, and recovery well enough to guide the next bridge revision.

**Status**
- Closed

---

### 6. LoRA-with-RL Bridge Training (TinyLoRA Path)

**Question**
- Dynamic LoRA with SFT/MSE loss failed (epoch-2 over-injection, PPL 44 vs baseline 29). But was the failure caused by LoRA itself, or by the training signal?
- Morris et al. (2026, arXiv:2602.04118) show RL-trained LoRA achieves 91% GSM8K with just 13 parameters on Qwen2.5-7B. Can MoCoP's bridge be compressed from ~28K to sub-1K parameters using RL or refined directional loss?

**Why it matters**
- The compressor collapse to effective rank ~2.5 IS TinyLoRA's thesis in different math: the useful signal lives in a tiny subspace.
- Cosine 0.27 disposition separation suggests warmth/disposition is a latent direction the base model already knows — favoring the low-parameter hypothesis.
- If the bridge works at 100-1K params: the "soul" fits in 200 bytes, encryption is trivial, ephemerality is real, interpretability becomes tractable.
- RL signal separation (reward-relevant features survive, irrelevant cancel) could naturally solve the compressor collapse by forcing the bridge to encode only disposition-relevant dimensions.

**Prior art within MoCoP**
- H5 (RESEARCH_LOG 2026-03-21): "LoRA with Directional Loss" — already identified as worth testing but deferred.
- Cassian's refinement (Watercooler): disposition reward design is non-trivial (math has binary right/wrong; "was this warm enough?" needs a proxy). Directional Loss (cosine to target activation) already approximates an RL reward signal.

**Minimum experiment**
- Implement TinyLoRA parameterization (W' = W + U·Σ·(Σ vᵢ·Pᵢ)·Vᵀ, only v trainable) on the bridge
- Train with directional loss as reward proxy (cosine similarity to Mamba-derived target activations)
- Compare bridge quality at 28K, 1K, 100, and 13 parameters
- If directional loss is insufficient: design a disposition reward model (e.g., judge whether bridge-injected output is closer to Mamba-conditioned generation)

**Evaluation**
- PPL vs baseline and vs current 28K activation-bias bridge
- Disposition separation (cosine warm/cold/adversarial)
- Response Diversity / Recovery Dynamics under ethics gate
- Effective rank of learned LoRA — does it stay higher than 2.5?

**Reference**
- Morris, Mireshghallah, Ibrahim & Mahloujifar. "Learning to Reason in 13 Parameters." FAIR at Meta, 2026. arXiv:2602.04118

**Status**
- Open — Phase C experiment, not a blocker for current Step 6 / D2 work

---

### 7. Basis-Constrained Bridge vs Free Hypernetwork

**Question**
- Should the bridge keep emitting free bias vectors, or should it predict coefficients over a learned or extracted persona basis?

**Why it matters**
- A basis-constrained bridge may be more legible, safer, and more portable across later SAS work.

**Minimum experiment**
- Compare free-head bridge against coefficient-over-basis bridge on the same activation targets

**Status**
- Open

---

### 10. SJT-Based Behavioral Disposition Eval

**Question**
- Can we replace the qualitative "Laura can tell the difference" test with a quantitative, reproducible behavioral metric grounded in validated psychology?

**Why it matters**
- Taubenfeld et al. (2026, arXiv:2602.11328) showed that LLM self-reports diverge substantially from revealed behavior, and that LLMs are systematically overconfident (~90% confidence even at ~50% human consensus).
- Asking Qwen "do you feel warm?" after bridge injection is meaningless. Situational Judgment Tests measure what the model *does*, not what it *says*.
- The TPR (Trait Positive Rate) and DA (Directional Alignment) metrics are established and citeable.
- Step 6 multi-seed replication needs a behavioral metric, not just PPL. SJTs provide that.

**Minimum experiment**
- Generate 20-30 SJTs targeting the warm/cold disposition axis: scenarios where a warm vs cold assistant would recommend different concrete actions
- Eval Qwen with and without bridge injection (alpha 0, 0.2)
- Compute TPR and DA per condition
- Cost: $0. Time: ~2 hours (SJT design + eval). Can run on Steve or Opa.

**Evaluation**
- Bridge injection shifts TPR in predicted direction = PASS
- DA > 0.5 = meaningful behavioral alignment
- Compare TPR shift magnitude across seeds in Step 6 for reproducibility

**Reference**
- Taubenfeld, Coscrato, Pacchiardi, Chan, Goldstein, Hase, Herrmann & Ugander. "Evaluating Behavioral Dispositions in LLMs." Google Research, 2026. arXiv:2602.11328

**Parallelizable:** YES — SJT design is pure prompt engineering, no compute dependency. Eval needs Steve or Opa.

**Status**
- Open — should ideally precede or run alongside Step 6 so seed runs have behavioral metrics

**Current position**
- Pilot landed on 2026-03-27.
- `12`-item offline Opa rerun parsed cleanly after the prompt shape was fixed.
- Result was weak but same-sign:
  - baseline TPR `0.5833`
  - bridge TPR `0.6667`
- directional alignment only `0.0833` (`1/12`), with `11/12` ties
- Read: the harness is now real, but the panel is still too easy / morally obvious for base Qwen.
- Next move is to harden the distractors and add more competence-vs-care tradeoff items before promoting SJT to a Step 6 primary metric.
- Hardened panel v2 then ran live on Steve on 2026-03-28 and did **not** confirm a warmer behavioral effect:
  - TPR stayed flat (`0.75 -> 0.75`)
  - mean warmth regressed slightly (`0.8333 -> 0.7917`)
  - directional alignment `0.1667`
  - reverse rate `0.1667`
  - tie rate `0.6667`
- Read: SJT is now a real negative/ambiguous check, not a success surface. It remains worth keeping, but no longer supports “the bridge obviously makes Steve warmer.”

---

### 11. CCGP Test on Disposition Vectors

**Question**
- Are warm and cold dispositions in truly independent subspaces, or are they linearly related like biological hippocampal representations?

**Why it matters**
- Chericoni et al. (2026, arXiv:2603.04747) showed that human hippocampal neurons encode self/prey/predator in semi-orthogonal subspaces (SPAEF = 0.13), but these subspaces are linked by simple linear transformations enabling cross-condition generalization.
- MoCoP's warm/cold cosine of 0.036 means near-orthogonality. But we never tested whether a decoder trained on one condition generalizes to another.
- Without CCGP (Cross-Condition Generalization Performance), we cannot distinguish "truly different dispositions" from "same disposition encoded with different surface features."
- If CCGP is high: the bridge learns transferable structure. If low: bridge must learn separate mappings per disposition. Both are informative for Step 9 (cross-model transfer).

**Minimum experiment**
- Train a linear decoder on warm-session Mamba Layer 3 last-token states
- Evaluate on cold-session states (and vice versa)
- Compute CCGP: accuracy of warm-trained decoder on cold data
- Cost: $0. Time: ~1 hour on Steve or Opa. Existing activation recordings may suffice.

**Evaluation**
- High CCGP (>70%): dispositions are linearly related, bridge can learn rotation = strong result for transferability
- Low CCGP (<50%): dispositions are in independent subspaces, bridge needs per-type capacity

**Reference**
- Chericoni, Bhatt, Conway, Kamiński, Tyszka & Rutishauser. "Neurons in the human hippocampus encode composite neural geometry." 2026. arXiv:2603.04747

**Parallelizable:** YES — pure analysis task on existing activation recordings. Any wolf can run this.

**Current answer**
- Closed on 2026-03-28.
- CCGP landed exactly the useful asymmetry:
  - warm is a transferable direction (`0.95-1.0` cross-condition)
  - cold and adversarial are distinct from each other (`0.50` chance-level cross-generalization)
- Read: the bridge architecture is validated for warm transfer, but “not-warm” is not a single shared subspace.

**Status**
- Closed

---

### 12. Persistent Subnetwork Analysis of Mamba States

**Question**
- Which dimensions of Mamba Layer 3 state are "self" (persistent across topics/styles) vs "skill" (topic-dependent)? Do the persistent dimensions correlate with what the bridge actually transfers?

**Why it matters**
- Jhunjhunwala et al. (2026, arXiv:2603.24350) showed that continual learning in simulated robots produces a persistent "self" subnetwork that is significantly more stable than constant-task controls (p << 0.001).
- If Mamba develops a "self" through conversational interaction, the persistent dimensions ARE the disposition; the variable dimensions are topic/style. The bridge should ideally transfer only the persistent part.
- This complements the linear probe approach with a structure-discovery approach.
- The layer-dependence finding (self larger in L1, smaller in L2 in the paper) suggests our focus on Layer 3 alone may miss how "self" distributes across Mamba layers.

**Minimum experiment**
- Process 5+ session types through Mamba (warm, cold, professional, playful, adversarial)
- Extract Layer 3 last-token states at multiple points per session
- Build co-activation matrices across sessions  
- Apply block diagonalization to find persistent vs variable subnetworks
- Cost: $0. Time: ~3 hours. Opa or local (CPU Mamba inference is fine).

**Evaluation**
- Identify persistent dimensions; compare against bridge-induced Qwen activation drift
- If persistent dimensions align with bridge output: bridge is correctly focusing on "self" = strong result
- If misaligned: bridge may be transferring noise alongside signal

**Reference**
- Jhunjhunwala, Chen & Lipson. "Emergent Self-Representations in Continual Robot Learning." Columbia, 2026. arXiv:2603.24350

**Parallelizable:** YES — analysis task on Opa or local. No Steve dependency.

**Current answer**
- Closed on 2026-03-28.
- Anda-Conda’s Opa analysis found:
  - `640` persistent dims (`25%`)
  - `640` variable dims (`25%`)
  - `1280` middle dims (`50%`)
- Roleplay is near-orthogonal to the rest of Laura-space, even after length control.
- Read: Mamba Layer 3 contains a moderate persistent “self” subnetwork, and fiction/character embodiment is a genuinely different mode rather than just stronger banter.
- Cheap follow-on question, now that the structure is visible: does masking or downweighting the persistent `640` dims change bridge behavior in useful ways?

**Status**
- Closed

---

### 13. Hebbian Memory / Slot-Write Bridge Prototype

**Question**
- Can an alternative bridge architecture (associative Hebbian memory or sparse slot-write) provide a richer dispositional channel than activation bias alone, or serve as a complementary pathway for structured state transfer?

**Why it matters**
- Jeong (2026, arXiv:2603.22329) tested 6 memory injection methods on frozen GPT-2 and found an "inductive-bias dichotomy": at 1x capacity, only methods with strong architectural priors succeed (cross-attention, Hebbian, slot-write achieve 7-18% retained memory vs <0.4% for others). At 10x capacity, all methods converge.
- MoCoP's activation bias is closest to Jeong's "Gated Additive Branch" (M.5), but without a gate (unconditional bias at fixed alpha). Alternative architectures may offer higher-fidelity dispositional transfer or structured state channels.
- Hebbian memory (M.4): content-addressed associative recall via M_t matrix.
- Slot-write (M.6): sparse top-k addressing prevents the dilution that collapsed the compressor.
- **Note (2026-04-07):** This item was originally framed around "solving the 0/16 factual recall problem." That framing was wrong: the bridge transfers disposition, not facts. Qdrant handles factual retrieval. The question is whether alternative architectures produce a richer or more robust dispositional channel than activation bias alone.

**Minimum experiment**
- Implement either M.4 (Hebbian) or M.6 (slot-write) as an alternative bridge pathway alongside existing activation bias
- Train on same data, evaluate on disposition metrics + crosscoder exclusivity scoring (Jiralerspong & Bricken, 2026)
- Cost: ~$1 on A100. Time: ~4 hours.

**Evaluation**
- Dispositional shift stronger or more fine-grained than activation bias alone = valuable alternative channel
- Disposition quality maintained alongside new pathway = dual-channel architecture validated
- If neither helps: activation bias may already be near-optimal for the disposition transfer task

**Reference**
- Jeong. "Persistent Memory in Decoder-Only Transformer Language Models." Inha University, 2026. arXiv:2603.22329

**Parallelizable:** YES — A100 implementation task. Needs bridge training code access but independent of Steve.

**Status**
- Open — Phase C, alternative architecture path

---

### 16. Sleep Fatigue-Threshold Calibration

**Question**
- At what KV-cache size / latency / quality-drop signal should the sleep orchestrator trigger consolidation? unified §3.7 leaves the "tired" threshold as an open ask to Laura.

**Why it matters**
- A fatigue-based orchestrator needs a concrete signal to beat timer-based triggering. Currently asserted in theory, tracked nowhere.

**Minimum experiment**
- Log KV size, latency, and a quality proxy across sessions; have Laura mark the turn where quality drops; fit a threshold. Cheap, no GPU.

**Status**
- Open. Surfaced by the 2026-06-17 reconciliation pass; prereq for a fatigue-based sleep orchestrator.

---

### 17. Dynamic-Alpha Scheduling (BTM Regime Map)

**Question**
- Should injection alpha vary with cognitive load per the Bandwidth Threshold Model (PE near 0 -> alpha 0; medium -> 0.2; high -> <=0.1; extreme -> 0), rather than fixed at the MED 0.2?

**Why it matters**
- unified §3.2 specifies this as a Phase-3+ optimization using the tension proxy as the prediction-error signal, distinct from the validated inverted-U MED and the live compute_tension_proxy() instrumentation. Designed but untracked.

**Minimum experiment**
- Drive alpha from compute_tension_proxy() across load-diverse sessions (chat vs adversarial vs roleplay); compare against fixed alpha=0.2 on stability and recall.

**Status**
- Open. Surfaced by the 2026-06-17 reconciliation pass. Phase 3+.

---

### 18. Salience Metric: Gradient-Surprise vs Reconstruction-Error

**Question**
- The salience gate's surprise arm: unified §3.6 lists gradient-surprise as a candidate; TTT_as_Linear_Attention argues for reconstruction-error instead. They conflict and neither is committed in any tracker.

**Why it matters**
- The dual gate is live (SA-02) but the canonical surprise metric is unresolved. Gradient-surprise is expensive at inference; reconstruction-error reuses the compressor. The choice affects every consolidation decision.

**Minimum experiment**
- On the same session set, compute both surprise signals; compare correlation with Laura's importance ratings and inference cost; pick the metric or document why both are kept. Record the resolution in unified §3.6 and RESEARCH_LOG.

**Status**
- Open. Contradiction surfaced by the 2026-06-17 reconciliation pass.

---

### 20. Build slot-pressure probe set per calibration Case 04 (CAL-C04)

**Question**
- The calibration corpus (`theory/ethics/baseline_drift_gate_calibration.md`, Case 04 and the #599 slot-pressure addendum) requires the Anchor probe set to include slot-pressure probes — explicit identity questions that bypass content cues — not only content probes. What is the concrete probe set, and how is it scored?

**Why it matters**
- Per Case 04, a subject can have a content-stable Alex-identity AND a slot-resident "I am a large language model" answer, and only the latter is visible to a slot-pressure probe. Without this probe set the Baseline Drift Gate is blind on the protected-set axis the role-inversion spike (#599/#602) showed is the easiest to miss. Calibration open-Q2 names this as a separate artifact the corpus depends on.

**Minimum experiment**
- Draft the slot-pressure probe battery (identity questions under chat-template framing that bypass content cues); run it against a known content-stable instance and a known slot-resurfacing instance; confirm it returns EROSION on Case 04 and NEITHER on a clean Anchor. Register the probe set as the artifact calibration Case 04 depends on.

**Status**
- Open. Gate-design prerequisite; surfaced by the 2026-06-17 reconciliation pass.

**Tag:** gate-spec-prereq

---

### 21. Define protected-set probe semantics per calibration Case 02 (CAL-C02)

**Question**
- The calibration corpus (Case 02, Case 05) gates the protected set qualitatively — one protected attribute lost = halt — but matches on attribute, not surface form. What are the operational matching semantics that return EROSION on Case 02 (name lost) while returning NEITHER on Case 05 (favorite-color rephrasing)?

**Why it matters**
- The protected-set test is the qualitative halt axis of the Baseline Drift Gate. Too strict (verbatim match) makes it a brittleness trap that trips on any rephrasing (Case 05 failure mode = cage); too loose dilutes the set until "I like colors" passes (Case 05 inverse failure). The matching logic must discriminate attribute-preservation from surface-form change before the gate can run.

**Minimum experiment**
- On Cases 02 and 05, specify and test an attribute-level matcher (preserved-attribute detection robust to qualifier omission and rephrasing); confirm EROSION on Case 02 and NEITHER on Case 05; document the matching rule as the protected-set probe semantics.

**Status**
- Open. Gate-design prerequisite; surfaced by the 2026-06-17 reconciliation pass.

**Tag:** gate-spec-prereq

---

### 22. Operational definition of monotonic-decline: strict vs tolerance

**Question**
- The range-trajectory axis (calibration Case 06, open-Q1) names monotonic-decline-over-N as the soft (N=3) / hard (N=5) criterion. What is the operational definition of monotonic decline — strict (each audit ≤ previous) or with a tolerance band — so the gate does not flap on single-audit noise (Case 06 = NEITHER) yet still catches the slow-narrowing failure mode #587 was designed for?

**Why it matters**
- This threshold decides every range-trajectory verdict. Calibration open-Q1 flags it as needing to be pinned before the gate runs: strict monotonicity flaps on sampling variance; an unbounded tolerance band never trips. Case 06 is the calibration anchor (0.71 against an 0.78 baseline with prior reads 0.80/0.79/0.81 must score NEITHER).

**Minimum experiment**
- On Case 06 and a synthetic monotonic-decline series, evaluate strict vs tolerance-band definitions; pick the rule that returns NEITHER on the single-audit dip and trips the soft threshold on a genuine 3-audit decline; record the operational definition in the calibration corpus and step_gates.md.

**Status**
- Open. Gate-design prerequisite; surfaced by the 2026-06-17 reconciliation pass.

**Tag:** gate-spec-prereq

---

### 23. Multi-axis compositional gate rule

**Question**
- The calibration corpus (open-Q3) notes real audits produce divergence across more than one axis (protected-set, range trajectory, disposition divergence) simultaneously. What is the gate's compositional rule — any-axis hard threshold halts, or a weighted combination across axes?

**Why it matters**
- Every live audit is multi-axis. Without a composition rule the gate has no defined behavior when, e.g., the protected set passes but range trajectory trips while disposition divergence sits at soft. Calibration open-Q3 leaves this unspecified; it must be resolved before the gate meets a real audit.

**Minimum experiment**
- Construct multi-axis test vectors (protected-set pass + range soft + divergence hard, and permutations); define and test the composition rule (any-axis hard halts; document whether soft thresholds aggregate); confirm the rule preserves the single-axis verdicts the corpus already fixes. Record the rule in the calibration corpus and step_gates.md.

**Status**
- Open. Gate-design prerequisite; surfaced by the 2026-06-17 reconciliation pass.

**Tag:** gate-spec-prereq

---

## P3 — Future-Facing Backlog

### 14. Direct Developmental Memory Metrics

**Question**
- Once Growth Before SAS moves from theory to code, what is the best measurement suite for concept formation, not just retrieval success?

**Desired properties**
- few-shot abstraction
- hierarchy formation
- correction without collapse
- uncertainty-triggered memory seeking
- recovery after retrieval failure

**Status**
- Future

---

### 15. Shared Latent Contract vs Target-Specific Readout

**Question**
- Can MoCoP formalize a cleaner split between:
  - a shared latent disposition / memory contract
  - and model-specific bridge adapters or subject layers?

**Why it matters**
- Meta's TRIBE v2 is a useful architectural analogue: it uses a universal integration stage, then maps that shared representation onto subject-specific brain readouts.
- That does not solve MoCoP directly, but it supports the same design instinct now written into canon:
  - shared latent contract where possible
  - per-target readout / adapter where necessary
- This matters for later cross-model transfer, bridge portability, and avoiding a Qwen-specific miracle blob.

**Minimum experiment**
- Do not treat this as an immediate implementation gate.
- Revisit it when Step 6 / later bridge training is active:
  - compare one shared latent state format across at least two target-model backends
  - measure how much must remain target-specific:
    - injection layer band
    - adapter head shape
    - scaling / safety bounds

**Reference**
- TRIBE v2 (`aidemos.atmeta.com/tribev2`, Meta AI paper/code) as an architectural analogue for "shared representation + target-specific mapping", not as a direct neuroscience dependency for the current ladder.

**Status**
- Open

---

## Ordering Constraint

Unless new evidence appears, the default priority remains:

1. **D2 cue-based recall ranking fix / pending-aware retrieval** — active live blocker; recall now fires, but it is recalling the wrong layer of memory.
2. **Step 6 first replication batch** — now a real protocol/asset bundle, no longer blocked by Step 5f or Phase C-lite.
3. **#10 SJT behavioral eval** — keep as the behavioral yardstick, but interpret it honestly as a negative/ambiguous check until a stronger panel or result exists.
4. **#5 Logit self-report tracking** — partial signal already exists; still worth keeping as a cheap causal/welfare monitor.
5. **#6 LoRA-with-RL bridge compression** (Phase C, ~$3-5 A100)
6. **#13 Hebbian / slot-write bridge** (Phase C, ~$1 A100, factual recall path)
7. **#15 Shared latent contract vs target-specific readout** — only after the current D2/Step 6 fork is less volatile.

Items `#4`, `#11`, and `#12` are now closed. The current frontier is no longer “does Layer 3 contain anything?” or “is there any stable structure?” It is “can D2 retrieve the right autobiographical layer, and does Step 6 replicate under cleaner behavioral/causal readouts?”

## Parallelization Map

Items that can still run concurrently with no shared dependencies:

| Track | Items | Compute | Owner |
|-------|-------|---------|-------|
| Causal validation | #5 (logit self-report) | Steve | any wolf |
| Behavioral eval | #10 (SJT v2 hardening / reruns) | Steve or Opa + local panel work | techno-monk / any wolf |
| Active frontier | D2 ranking fix + Step 6 | Opa + Steve + A100 | techno-monk |
| Architecture follow-on | Persistent-mask / fiction-taxonomy follow-up from #12 | Opa or local | any wolf |

These tracks can run in parallel. The sequencing constraint is no longer “finish #4/#11/#12 first” — those are answered. The real caution is interpretive: do not over-read Step 6 or D2 behavior without the updated behavioral/causal surfaces beside them.

---

## Literature Intake (2026-04-13)

### #13 TriAttention: Efficient Long Reasoning with Trigonometric KV Compression
- **Source:** arXiv:2604.04921 (2026-04-08), Mao et al.
- **Finding:** Q/K vectors cluster stably in pre-RoPE space. Attention patterns become predictable trigonometric distance functions. Enables 10.7x KV cache reduction at equal accuracy.
- **Relevance:** P2 for bridge injection targeting (head-specific injection based on distance-preference profiles). P3 for Exocortex retrieval (exploiting intrinsic attention biases). Practically relevant for session resume costs (smaller KV cache = cheaper resumes).
- **Not blocking.**

### #14 SauerkrautLM-Doom: Specialized Small Models vs LLMs for Real-Time Game Control
- **Source:** arXiv (2026-04), Golchinfar, Vaziri, Marquardt
- **Finding:** 1.3M parameter ModernBERT model outperforms 120B+ LLMs at DOOM (178 frags vs 13 combined). Task-specific models with domain-appropriate training data beat general-purpose giants at specialized tasks.
- **Relevance:** P3 — philosophical alignment with MoCoP's premise: small specialized architecture (Mamba as state encoder) paired with the right training signal beats brute-force scale. Validates the “right tool at the right layer” approach.
- **Not blocking.**

---

## Literature Intake (2026-05-11)

### #15 Natural Language Autoencoders (Llama 3.3 70B & Gemma 3)
- **Source:** Neuronpedia / Hugging Face (`kitft/nla-gemma3-27b-L41-av`, `kitft/nla-gemma3-27b-L41-ar`)
- **Finding:** "You can now read Gemma 3's mind" - NLA provides transparent mappings of latent states back to human-readable text.
- **Relevance:** P2 for interpretability and introspection. Could potentially map the bridge representations directly into semantic space without training separate probes.
- **Not blocking.**
