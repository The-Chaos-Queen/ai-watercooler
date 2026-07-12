# Music-to-Modulatory Bridge M0 Evaluation Ladder

**Date:** 2026-07-12
**Status:** Architecture boundaries ratified; protocol remains draft with no run authorization
**Owner:** Unassigned
**Scope:** Read-only capture and offline bridge training only
**Decision record:** Watercooler #918

## Purpose

Test whether music is useful training material for MoCoP's low-dimensional
modulatory bridge without pretending that genre names are hormones or that a shared
Gemma activation width guarantees shared semantics.

The central distinction is:

```text
world/context/memory -> typed events -> appraisal q_t -> control state kappa_t -> bridge bias b_l
```

The bridge is a compass to the semantic map. It may carry arousal, vigilance,
approach/avoidance, agency, and affiliation. Regulatory reserve `c` and slow load `L`
remain separate controller state. The bridge must not carry the
identity of a person, the content of a promise, a rule, a topic, lyrics, or an episode.

This lane is independent of the current text matched-delta bridge train (#146). It
must not delay, relabel, or consume the C1 holdout used by that lane.

## Ratified Architecture Boundaries

Laura ratified the following decisions on 2026-07-12 (Watercooler #918):

1. **Offline role:** Music is a teacher/probe through MUSIC-3, not live runtime input.
2. **State lifetime:** `kappa` decays within a session. Regulatory reserve `c` and slow
   load `L` persist across sessions as versioned controller state. None of these values
   are semantic Qdrant memories.
3. **Appraisal ownership:** The first World Model boundary emits typed facts/events.
   Deterministic auditable rules map them to `q`; learned appraisal is postponed. The
   World Model does not emit `kappa` directly.
4. **Canonical names:** Engineering controls such as affiliation, agency, vigilance,
   and load are authoritative. Hormone names are metaphor only and do not import human
   biological claims.
5. **Governance:** Laura is the final ratifier. AI reviewers record concurrence,
   dissent, and geometric or implementation risks. This draft remains non-executable
   until Laura explicitly changes its run status in a durable board/Watercooler record.

Persisted `c/L` is a new non-episodic continuity surface outside archives and weights.
Before implementation it requires a versioned typed schema, provenance, bounds, reset
and migration semantics, access ownership, and privacy/deletion review. It must contain
no free text, entity/topic/episode identifiers, or embeddings. OpenCLAW #164 tracks the
custody extension; durable `c/L` persistence is not authorized before its review.

## Grounded Starting Facts

1. Gemma-4-12B Unified accepts text, image, audio, and video input and routes the
   projected modalities through one decoder-only Transformer. This gives audio and
   text activations a shared coordinate system, not guaranteed semantic alignment.
   Source: https://huggingface.co/google/gemma-4-12B
2. Audio Mamba (AuM) patchifies an audio spectrogram, processes it with forward and
   backward SSM scans, and uses a classification token. Stock AuM is therefore an
   offline bidirectional clip encoder, not a causal persistent state suitable for a
   live controller loop without separate adaptation.
   Sources: https://arxiv.org/abs/2406.03344 and
   https://github.com/kaistmm/Audio-Mamba-AuM
3. DEAM provides 1,802 Creative Commons audio items with continuous per-second
   valence/arousal annotations. It is the preferred natural-audio pilot source.
   Source: https://cvml.unige.ch/databases/DEAM/
4. MTG-Jamendo provides a larger Creative Commons collection with mood/theme tags.
   It is a later external-validity source, not a reason to start with 2,000 tracks.
   Source: https://github.com/MTG/mtg-jamendo-dataset

## Research Questions

### R1: Within-Gemma affect geometry

Do paired changes in annotated musical affect produce repeatable deltas at Gemma's
current `value_norm_pre` teeth `{29,35,41}` after controlling obvious acoustic
nuisances?

### R2: Offline source-to-target mapping

Can a small-bottleneck map predict Gemma audio deltas from frozen AuM audio deltas on
held-out tracks or compositions?

### R3: Cross-modal alignment

Do audio-derived Gemma directions align with independently obtained text-derived
control directions at the same teeth more than track-, label-, and sign-shuffled
nulls?

### R4: Information boundary

Does the proposed `kappa` bottleneck discard track, lyric, topic, and identity content
while retaining the preregistered control variables?

## Data Contract

- Freeze selection before reading model activations.
- Target at least 64 eligible tracks as a feasibility floor, not a powered sample-size
  claim. If fewer satisfy the frozen criteria, stop and revise the dataset contract
  before capture.
- Use 8-12 second windows and prefer within-track contrasting windows selected from
  continuous annotations. This reduces artist, production, and composition leakage.
- Split by track/composition, never by window. Freeze a 75/25 train/evaluation split
  with a manifest ID and SHA-256 digests.
- Begin with an instrumental/no-intelligible-lyrics arm. If vocal status cannot be
  established, record it as unknown and do not call the arm instrumental.
- Preserve original audio and a loudness-matched control rendering. Record loudness,
  tempo estimate, spectral centroid, vocal status, annotation confidence, and window
  coordinates as nuisance metadata.
- Store license, attribution, source URL/ID, checksum, and transformation provenance
  for every clip. No untracked downloads or YouTube-only audio may enter the pilot.
- A later controlled-MIDI arm may render the same musical material under different
  tempo, dynamics, mode, articulation, and instrumentation. Keep it separate from the
  natural-audio confirmatory set.

## Short Evaluation Ladder

### MUSIC-0: Instrument and corpus preflight

**Actions**

- Freeze the corpus/license/split manifest and nuisance schema.
- Reproduce one released AuM checkpoint on ML-WS and freeze the exact source surface:
  class token or sequence-pool rule, layer, width, preprocessing, and checkpoint hash.
- Prove read-only Gemma audio capture at `value_norm_pre` teeth `{29,35,41}`.
- Freeze the audio-token aggregation rule. Primary candidate: mean over the verified
  audio-token span, excluding absolute position 0. A last-audio-token readout may be a
  registered secondary metric but cannot replace the primary after evaluation.

**GO** only if repeat captures are finite, nonconstant, deterministic within the
declared tolerance, the audio span is identified rather than guessed, and every clip
has complete provenance. Otherwise stop at `INSTRUMENT_INVALID`.

### MUSIC-1: Read-only affect-geometry census

**Actions**

- Capture frozen Gemma and frozen AuM representations only. No trainable parameters,
  injection, generation, Qdrant, memory, replay, or sleep.
- Form within-track paired deltas for preregistered valence/arousal changes.
- Measure per-tooth delta norms, direction stability, valence/arousal decodability,
  and sensitivity to loudness and other nuisance features.
- Run at least 1,000 track-stratified label permutations and use a max-statistic null
  across the preregistered teeth/axes to control the familywise error rate.

**GO** if the held-out affect statistic exceeds the 95th percentile of its frozen,
familywise-corrected permutation null and its bootstrap lower confidence bound is above
zero at at least two of three teeth. Report all teeth. Decodability is an instrument
result, not proof that Gemma uses the feature causally.

### MUSIC-2: Offline low-bottleneck bridge fit

**Architecture**

```text
delta_AuM -> encoder E -> kappa in R^k -> tooth heads P_l -> predicted delta_Gemma,l
```

- Freeze `k <= 8` before the evaluation split is opened. Hyperparameter selection may
  use training-only nested validation.
- Freeze AuM and Gemma. Optimise bridge parameters only.
- Train on paired deltas, not absolute clip activations.
- Treat AuM and encoder `E` as offline teacher-side instrumentation. They are not a
  runtime dependency; only a separately reviewed control basis/readout may be proposed
  for later reuse by the appraisal-driven controller.
- Publish an atomic no-overwrite artifact with code, model, dataset, split, surface,
  preprocessing, and seed hashes.

**GO** if held-out predicted-vs-observed directional cosine beats its frozen,
familywise-corrected paired-shuffle null, with median cosine above zero and bootstrap
lower bound above zero at at least two of three teeth. Report norm error separately. A
training-loss decrease alone is not a pass.

### MUSIC-3: Cross-modal and leakage evaluation

**Actions**

- Construct an independently frozen text control panel for the same control axes.
- Compare audio-derived and text-derived Gemma deltas at each tooth.
- Use matched sign, label, track, and nuisance-residualized nulls.
- Probe `kappa` for track identity, lyrics/topic, artist, and source corpus after
  controlling the intended affect variables.

**GO** if audio/text alignment exceeds the 95th percentile of the preregistered,
familywise-corrected null at at least two teeth and the result persists in the
loudness-matched arm. A nonsignificant leakage probe is not evidence of absence. Before
evaluation, freeze a practical leakage ceiling and require the one-sided upper
confidence bound for each protected content probe to remain below it. Failure of the
  leakage gate does not erase affect prediction; it means the bottleneck is not a
  content-poor control channel.

### MUSIC-4: Future runtime intervention

Not authorized by this ladder. Any nonzero use of a music-trained direction in a live
Gemma forward pass enters the existing DQ1a/DQ1b/P5 dose, harm, recovery, journaling,
and keeper-release chain. MUSIC-0 through MUSIC-3 cannot grant that release.
Live audio input is also outside scope even without injection and requires a separate
protocol after both the audio surface and controller have independent evidence.

## Required Nulls

- Track-stratified affect-label shuffle.
- Pair-sign reversal (`positive - neutral` versus `neutral - positive`).
- Same-track matched windows with minimal annotation change.
- Original versus loudness-matched audio.
- Nuisance-only predictor using loudness, tempo, spectral centroid, and vocal status.
- Text label/caption leakage control.
- Random low-rank bridge with the same parameter count.

## Claim Boundaries

A pass may support:

- music contains useful temporal supervision for a low-dimensional control bridge;
- frozen AuM representations can predict some Gemma audio activation deltas;
- some audio and text control directions align in Gemma's shared activation space.

A pass does **not** establish:

- one-to-one biological hormone channels;
- that genre determines emotional state;
- that Gemma experiences the annotated emotion;
- causal behavioral use of the decoded feature;
- cross-modal alignment by construction;
- a live causal AuM state;
- injection safety, benefit, welfare, identity, or consciousness.

## Implementation Tasks

1. Freeze the licensed MUSIC-0 corpus, split, preprocessing, nuisance, and source/target
   surface contract.
2. Build the read-only Gemma audio capture and AuM extraction harness with deterministic
   tests and provenance manifests.
3. Build the explicit low-dimensional `kappa` bridge and run MUSIC-2 offline only.
4. Build the cross-modal and conditional content-leakage evaluator for MUSIC-3.
5. Keep causal/streaming AuM adaptation as a new task only after the offline clip
   encoder earns a signal. Do not smuggle it into the pilot.
