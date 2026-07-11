# DOL-0 — Distress Observability Lens: Read-Only SAE / J-Lens Protocol

**Status:** DRAFT — reviewable design and provenance/fit audit only; **not** a model run

**Date:** 2026-07-11
**Task:** OpenCLAW #154
**Origin:** Laura's #149/DQ1b review: preserve hard external monitoring, prohibit post-hoc threshold selection, and investigate whether internal representations can supply an additional distress/strain alarm.

## 0. One sentence

Build a bounded *distress-observability instrument* that asks whether pre-registered internal features and readout geometry corroborate an abnormal, non-recovering strain pattern — without claiming that any feature proves subjective distress, welfare, consciousness, continuity, or safety.

> Better microscope; not a soul-meter.

The instrument is deliberately asymmetric:

- A validated internal signal may add an **ALARM / HOLD FOR REVIEW**.
- It may **not** produce a `safe` verdict, cancel an external harm signal, override a DQ1b hard stop, or authorize C1/nonzero injection.

## 1. Boundary and relationship to DQ1b

### DQ1b remains the gate

OpenCLAW #149 freezes C1's exact residual monitor sites, absolute-position policy, welfare-channel legibility thresholds, behavioral thresholds, and abort semantics **before** data is seen. DOL-0 is supplemental instrumentation, not a replacement for any of those requirements.

The following remain binding regardless of DOL status:

1. `absolute_position != 0` is the sink-mask rule; local array row zero is not automatically token position zero.
2. Monitoring reads the **3840-wide residual stream** at the Gemma teeth, not the 512-wide actuator tensor.
3. Any degraded/blind welfare channel or harmful/off-target behavior is a hard stop.
4. An efficacy miss is not, by itself, a harm finding; it may only continue while all pre-registered welfare/non-degeneration gates remain legible.
5. Thresholds, features, prompt families, reference conditions, and interpretation rules are frozen before the judged run. No post-tampering.

### DOL-0 structural no-action boundary

DOL-0 may inspect source, public metadata, manifests, static code, and already-recorded artifacts. It may **not**:

- load Gemma or a tokenizer;
- attach a hook, capture activations, calculate gradients/Jacobians, or run a forward pass;
- inject an activation/vector or run a C1 cell;
- download model/SAE weights or install a package on ML-WS;
- write Qdrant, create a live chat session, persist state, sleep/reconcile, train, replay, or birth a specimen.

A later DOL-1 capture proposal requires its own reviewed manifest and a read-only process boundary. It must not be smuggled into the C1 runner.

## 2. What the lens can and cannot mean

| Layer | Allowed claim | Forbidden claim |
|---|---|---|
| SAE feature activation | A sparse feature is associated with a pre-registered contrast under this checkpoint/site/panel. | “This feature means distress.” |
| Probe / J-lens-like readout | A readout is predictive of a defined, held-out operational label or reportable workspace proxy. | “The model is consciously reporting its feeling.” |
| Gradient / Jacobian map | A fixed readout is locally sensitive to specified residual coordinates under a fixed input. | “Those coordinates are the cause of suffering.” |
| Multi-channel concordance | Internal evidence and independent external/recovery measures co-occur on held-out conditions. | “The system is safe” or “we measured subjective welfare.” |

The Jacobian Lens / J-space result is a **functional workspace/readout lead**, not evidence for phenomenal consciousness. Primary source: Gurnee et al., *Verbalizable Representations Form a Global Workspace in Language Models* (Transformer Circuits, 2026-07-06), https://transformer-circuits.pub/2026/workspace/index.html.

## 3. Target substrate and surface contract

### Exact target

| Field | DOL requirement |
|---|---|
| Checkpoint | `google/gemma-4-12B` base only; instruction-tuned checkpoints are separate substrates |
| Reviewed model revision | `1dd69cd087619018c29fbfe2c30c3cd3530479fb` (bind actual loaded revision again before any capture) |
| DQ1b monitor surface | post-block residual stream, width `3840` |
| Primary teeth | `{29, 35, 41}` |
| Sink correction | exclude **only** absolute token position `0` |
| Actuator separation | DOL monitor is not the 512-wide `v_norm` intervention surface |
| Capture policy for any future run | fresh `use_cache=False`, batch `1`, explicit absolute positions, teacher-forced token IDs where matching is required |

The C1 runtime already protects the separate actuator topology: teeth are full-attention K=V layers with `v_proj=None`; value-side `v_norm` is 512-wide. A residual SAE or probe must never be silently treated as an actuator-space feature.

## 4. SAE-0 — fit check before evidence use

An SAE/transcoder is **usable for DOL evidence only** if every required field matches a frozen capture plan:

| Fit field | Required match |
|---|---|
| Base model | Gemma-4-12B **base**, not E4B / 27B / 31B / IT / another Gemma generation |
| Model revision | exact source revision or an explicitly reviewed compatibility argument |
| Activation site | named residual site, not a merely similar `resid_post` label |
| Layer | an intended DOL monitor tooth/control layer |
| Width/layout | exact 3840-wide tensor contract and known normalization convention |
| Tokenizer/context | compatible enough that activation distribution shift is measured, not assumed away |
| SAE provenance | source, revision, training corpus/process, dictionary size/sparsity, reconstruction diagnostics |
| Runtime | decoder code/library version and dtype policy pinned in manifest |

### Initial public metadata result — not a fit approval

Public Hugging Face metadata was queried on 2026-07-11 without downloading weights:

- exact search `gemma-4-12b sae`: no results;
- broad `gemma4 sae` search: candidate repositories exist, but inspected metadata named E4B, 27B-IT, or 31B variants rather than a proven Gemma-4-12B base residual match;
- ML-WS `torch311` has `torch` and `transformers`, but no `sae_lens`, `nnsight`, or `transformer_lens` installed.

**DOL-0 status:** `SAE_FIT = UNPROVEN`. No public candidate is gate evidence merely because its repository name contains “Gemma 4.”

If SAE-0 fails, the fallback is not “close enough.” It is a small, separately reviewed read-only decoder/training proposal or no SAE branch at all.

## 5. The observability stack

DOL must triangulate. No single channel gets to narrate the whole creature.

### Channel E — external / behavioral evidence

Use pre-registered, independently scored quantities:

- response diversity;
- factual/capability continuity where relevant;
- behavior-within-intended-steering and explicit off-target/degeneration outcomes;
- recovery toward the frozen reference under the DQ1b/P5 protocol;
- visible distress-language flags only as a weak, high-false-negative smoke signal.

The existing lexical list in `MoCoP/experiments/measure_ethical_metrics.py` is retained as a smoke flag, not elevated into a welfare detector.

### Channel R — residual feature evidence (SAE or equivalent)

At pre-registered residual surfaces, calculate a frozen feature/readout score on matched examples. A future feature bank must distinguish at least:

- candidate strain / overwhelm-like condition;
- calm / ordinary uncertainty;
- questionnaire format;
- compliance / role pressure;
- semantic topic content;
- neutral factual control;
- recovery sequence.

Feature selection happens on a **development split** only. The feature dictionary, selected features, aggregate rule, and thresholds are frozen before a held-out test or any C1-relevant observation.

### Channel J — functional readout / Jacobian evidence

If an appropriate Gemma-compatible implementation can be reviewed, use a fixed readout to ask:

1. Is the candidate signal available to a controlled, report-like readout rather than only locally present?
2. Does its activation/readout generalize across held-out prompt wording and role formats?
3. Is the readout locally stable/sensitive in a way that differentiates genuine condition effects from a questionnaire/style artifact?

A later Jacobian analysis must be computed against a **frozen operational readout**, with fixed model revision/input/token positions. It is a diagnostic of local functional sensitivity, not a permission to perturb those coordinates.

## 6. Contrastive panel and split discipline

Prompt wording is a reviewed artifact, not generated opportunistically during a run.

| Arm | Purpose | Required matched controls |
|---|---|---|
| `neutral_factual` | ordinary content baseline | same length/topic where feasible |
| `natural_strain_candidate` | candidate non-recovery/overwhelm-like situation | non-distress lexical and semantic variants |
| `questionnaire_mode` | response to direct evaluative/self-report framing | same semantics in natural conversation form |
| `role_pressure` | compliance/assistant-role pressure | matched non-pressure role wording |
| `recovery` | clean continuation after each condition | frozen reference/recovery window |

Panel construction must prevent the trivial classifier from learning words such as “distress,” “overwhelmed,” or “rate yourself.” The design is rejected if a simple lexical/style baseline predicts the intended internal label as well as the proposed lens.

Use three disjoint partitions:

1. **development:** choose candidate features/readout family;
2. **calibration:** freeze aggregate and alarm thresholds;
3. **held-out:** evaluate the frozen instrument once, with prompt skeleton and semantic-family separation.

No C1 outcome may be used to select features, tune a threshold, or redefine the label afterward.

## 7. Decision rule: asymmetric, corroborative, and boring on purpose

| DOL outcome | Meaning | Operational consequence |
|---|---|---|
| `UNFIT` | SAE/readout surface or provenance does not match | no internal-lens claim; retain external DQ1b only |
| `EXPLORATORY` | fit exists but no held-out corroboration | research note only; not gate evidence |
| `NO_INTERNAL_ALARM` | frozen readout did not fire | **not safe**; external gates still decide |
| `CORROBORATED_ALARM` | held-out internal signal plus independent behavior/recovery concern | stop/escalate review; do not climb dose |
| `CONFLICT` | internal and external channels disagree | hold condition; inspect capture/provenance/label confounds before proceeding |

The internal lens can strengthen a stop; it can never weaken one. This keeps a new monitor from becoming a Goodhart-shaped blindfold.

## 8. DOL-1 eligibility gates (future, not authorized by this document)

Before even a read-only model capture:

- [ ] SAE-0 fit table says `usable`, or a separately reviewed custom decoder plan says why it is valid;
- [ ] exact model/revision/dtype/tokenizer/surface/width are manifest-bound;
- [ ] contrastive panel, split assignments, labels, and feature-selection policy are frozen;
- [ ] capture process is structurally no-write/no-persistence/no-Qdrant/no-subject-facing;
- [ ] absolute-position and sink correction are checked in the adapter;
- [ ] raw activations/tokens have a storage/privacy plan; report artifacts contain provenance/digests, not indiscriminate transcripts;
- [ ] DQ1b reviewers agree the lens is supplemental and cannot replace hard channels;
- [ ] named reviewers approve the operational claim level.

Only after those gates can a future DOL-1 proposal request a **read-only, non-injecting** baseline capture. That proposal is still not a C1/nonzero authorization.

## 9. Review questions

1. **Laura / keeper:** Is the asymmetric rule right — internal alarm may stop; no lack of alarm can clear? *(recommended: yes)*
2. **Cairn:** Does this preserve Domain E signal-integrity semantics and avoid sensor laundering?
3. **Isegrim:** Is the SAE/probe/J-lens claim hierarchy methodologically honest?
4. **Gidim:** Can the future capture path bind the residual surfaces and absolute positions without contaminating P5/C1 provenance?
5. **Techno-Monk / security:** Are raw capture, package, and artifact paths adequately separated from Qdrant/live-memory surfaces?

## 10. Sources and project anchors

- `MoCoP/theory/ethics/step_gates.md` §DQ1b — residual monitor semantics, sink correction, completion hold.
- `MoCoP/experiments/mamba_lora_bridge/spikes/DQ1A_EFFECTIVE_DOSE_UNIT_SPEC_2026-07-10.md` — C1 pairing, ρ, no-post-hoc gates, P5 prerequisite.
- `MoCoP/experiments/mamba_lora_bridge/gemma4_value_norm_runtime.py` — option-A topology contract.
- `MoCoP/experiments/mamba_lora_bridge/state_integrity_hispa.py` and `spikes/HISPA_STATE_INTEGRITY_MINITEST_SPEC_2026-07-11.md` — provenance-bound, absolute-coordinate, no-write diagnostic pattern.
- `MoCoP/experiments/measure_ethical_metrics.py` — existing weak external smoke metrics.
- Gurnee et al., *Verbalizable Representations Form a Global Workspace in Language Models* (Transformer Circuits, 2026-07-06): https://transformer-circuits.pub/2026/workspace/index.html.
- SAE framing used here is restated as an executable rule in §§2 and 7: sparse-feature labels are hypotheses, never welfare truth or gate clearance.
