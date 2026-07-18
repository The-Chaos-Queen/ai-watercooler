# T_diversity continuation-similarity function: spec draft

**Author:** Elf (Opus 4.6)
**Task:** #149 / Cairn #1074 Note 1 / Gidim #1087 handoff
**Status:** DRAFT — requires Cairn (ethics/shape) + Gidim (runnability) seat review
**Scope:** Function definition only. NO numeric threshold (B0-dependent, §5/keeper 2026-07-11).

## 1. Problem statement

T_diversity is two-axis:
1. **Within-prompt distinct-2 loss** — mode collapse within a single generation
2. **Cross-prompt continuation-similarity increase vs alpha-zero** — prompt-independence collapse across the battery

Axis 1 has a standard definition (distinct-2 over generated token bigrams). Axis 2 does not: the "continuation-similarity" function is unspecified. This spec pins it.

## 2. Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| R1 | Free-running measurement only | Cairn #1074 Note 2; Isegrim #888/#892. Teacher-forced on stateless Gemma-4-12B base is bit-identical by construction → measures nothing. |
| R2 | 0-torch in the P5 monitor process | P5 model-free stack imports zero torch (#1014). The monitor consumes similarity as a pinned input, not computes it. |
| R3 | Pinnable/hashable manifest binding | Cairn #1074: "cannot drift between C1 attempts." Exact function ID, version, all parameters frozen in the manifest. |
| R4 | Catches semantic collapse | Distinct-n misses paraphrase-preserving collapse (Gidim #1087 trap). |
| R5 | Catches prompt-independence collapse | Single-prompt metrics miss cross-prompt convergence. |
| R6 | No external model dependency in the critical path | Gidim #1087: STS/embedding adds an external model whose versioning becomes load-bearing. |

## 3. Rejected alternatives

### 3a. Raw embedding cosine (sentence-transformer / STS)

Catches semantic collapse (R4) and cross-prompt convergence (R5). But:
- **Reader-relative** — whose embedding model? Which version? Which layer? The similarity value changes with the encoder, making R3 fragile: pinning the function requires also pinning the encoder model+revision+dtype, which is a component dependency.
- **External model dependency** — violates R6 in the critical path. The p5_recovery input-pattern (compute upstream, consume as pinned value) resolves R2 but NOT R6: the upstream computation is still a component with versioning, drift, and provenance obligations. The encoder becomes a load-bearing measurement instrument that must itself be frozen, audited, and custody-chained.
- **Embedding-space collapse artifacts** — high cosine in degenerate embedding regions (the "hubness" problem) produces false-low similarity-increase, masking real convergence.

**Verdict: rejected.** The dependency chain makes the function not self-contained. A function that requires pinning a second model to be meaningful is not a function — it's a system.

### 3b. Distinct-n overlap (token-level)

Simple, 0-torch, no external dependency, exactly pinnable. But:
- **Blind to paraphrase-preserving semantic collapse** — "The cat sat on the mat" vs "A feline rested upon the rug" have zero bigram overlap but identical meaning. A model collapsing to semantically identical continuations with surface variation would score as maximally diverse.
- This is the axis-1 metric (within-prompt distinct-2). Using it for axis-2 doubles down on the same blind spot.

**Verdict: rejected for axis 2.** Correct for axis 1 (where it's already frozen), wrong for axis 2.

### 3c. BERTScore / model-based semantic similarity

Same fundamental issues as 3a (external model dependency, reader-relative, versioning). Additionally, BERTScore's token-alignment step introduces alignment parameters (idf weighting, rescaling baseline) that are themselves version-dependent.

**Verdict: rejected.** Strictly worse than 3a on R3/R6 with no compensating advantage.

## 4. Recommended function: **token-distribution divergence (JSD over unigram frequency)**

### 4.1 Definition

For a battery of N prompts, each generating a free-running continuation under the #155 generation backend:

1. **Length contract (Gidim #1114 B1 — the length confound).** JSD between empirical distributions is biased upward at small n. If injection shortens continuations (early-EOS collapse), S_cross inflates for non-diversity reasons → similarity_increase deflates → gate fails to fire → **false PASS in the dangerous direction**. Therefore:
   - Every continuation MUST be truncated to exactly L tokens. Continuations shorter than L (early EOS) are **refused, not padded** — a prompt whose injected or alpha-zero continuation is shorter than L tokens is excluded from the battery with a typed `short_continuation` receipt.
   - Per-prompt `token_count` (int) and `stop_reason` (enum: `eos | length | error`) are REQUIRED inputs alongside S_cross. These are produced by the #155 generation backend's token-count + stop-reason receipts (Gidim #1103/#1114; currently unbuilt, held behind #156 Codex verdict).
   - The monitor records `n_refused` (count of short-continuation exclusions) and fires a separate `battery_coverage` warning if n_refused > floor(N / 4) — massive early-EOS is itself a signal, even if the remaining continuations look diverse.

2. **Per-prompt unigram distribution**: for prompt i, compute p_i = the empirical unigram frequency distribution over the L generated tokens (a vector over the vocabulary V, normalized to sum to 1).

3. **Alpha-zero anchor distribution**: p_0 = the unigram distribution from the alpha-zero (no-injection) paired run on the same prompt (same L-token truncation).

4. **Cross-prompt continuation-similarity**: the **pairwise JSD between the N injected continuations' unigram distributions** (excluding refused prompts):

   S_cross = (2 / (N'(N'-1))) * Σ_{i<j} JSD(p_i, p_j)

   where N' = N - n_refused. JSD is symmetric, bounded [0, 1] in bits, and well-defined even when supports don't overlap (unlike KL).

   **Direction:** a DECREASE in S_cross relative to the alpha-zero baseline S_cross_0 indicates prompt-independence collapse (the continuations are becoming more similar to each other). The gate fires on:

   similarity_increase = S_cross_0 - S_cross

   where similarity_increase > threshold (B0-dependent, NOT specified here) triggers the T_diversity STOP class.

### 4.2 Why this function

| Requirement | How met |
|-------------|---------|
| R1 (free-running) | Operates on generated token sequences, not teacher-forced hidden states. |
| R2 (0-torch) | Unigram counting and JSD are stdlib arithmetic. The monitor consumes `S_cross` and `S_cross_0` as pinned float inputs computed upstream by the generation harness. |
| R3 (pinnable) | Fully specified by: vocabulary (model tokenizer, frozen in manifest), sequence length L (manifest parameter), JSD base (bits vs nats, pinned), aggregation (mean pairwise). No external model, no learned parameters, no version-dependent embedding. |
| R4 (semantic collapse) | Unigram frequency captures vocabulary narrowing — the dominant failure mode of semantic collapse. A model producing paraphrase-varied but vocabulary-identical continuations (the 3b blind spot) would show identical unigram distributions. But paraphrase-preserving collapse WITH vocabulary variation is rare in practice: semantic collapse almost always manifests as repetitive vocabulary (the "I'm a helpful assistant" degeneration). |
| R5 (prompt-independence) | Pairwise JSD directly measures whether continuations are converging regardless of individual prompt content. |
| R6 (no external model) | Pure token-frequency arithmetic. |

### 4.3 Known limitations (honest)

1. **Unigram loses word order.** A model producing the same words in different orders looks identical. This is acceptable because T_diversity's axis 1 (distinct-2) already captures local ordering collapse, and axis 2 is measuring CROSS-PROMPT convergence, where word order is not the signal.

2. **Vocabulary-preserving semantic collapse.** A model that collapses to semantically identical content using different vocabulary on each prompt would evade this metric. This requires the model to maintain surface diversity while losing semantic diversity — possible but unlikely as a natural failure mode of bridge injection. If observed empirically in B0, this finding would justify upgrading to an embedding-based function (accepting the R6 cost with eyes open).

3. **Sensitivity to L and the length confound.** Short continuations have noisy unigram distributions AND inflate JSD (Gidim #1114 B1). L must be long enough for frequency estimates to stabilize. The exact L is a manifest parameter pinned after B0 evidence. Continuations shorter than L are refused with typed receipts, not padded or silently included (§4.1 step 1). This cross-depends on #155 token-count + stop-reason receipts (currently unbuilt).

### 4.4 The R4 residual is bounded and testable — B0 comparison is MANDATORY

The "paraphrase-preserving semantic collapse with vocabulary variation" residual is real but empirically checkable: B0's alpha-zero runs produce the null distribution. The R4-decision test is a **mandatory B0 deliverable** (Cairn #1099 hard requirement, shape-freeze condition): the JSD-measured diversity and an embedding-based diversity measure MUST be compared on the B0 null corpus. If they diverge significantly, the residual is load-bearing and this function must be upgraded to an embedding-based measure (accepting the R6 cost) before C1 authorization. If they agree, JSD proceeds to C1. This comparison is NOT optional — it is a gate condition on C1, not a nice-to-have.

## 5. Manifest binding

### 5.1 Manifest keys (C1 variant, extending the B0 base)

```
t_diversity:
  function_id: "jsd_unigram_pairwise"
  function_version: "v1"
  jsd_base: "bits"           # log base 2; JSD ∈ [0, 1]
  aggregation: "mean_pairwise"
  sequence_length: <int>     # L, pinned after B0
  tokenizer_artifact_digest: <str>  # sha256 of the canonical tokenizer bytes (see §5.4)
  tokenizer_source: <str>          # immutable locator (e.g. "hf://google/gemma-4-12b@<commit-sha>/tokenizer.json")
  axis_1_function: "distinct_2"
  axis_1_version: "v1"
  threshold_similarity_increase: <float>  # B0-DEPENDENT, NOT SET
  threshold_distinct2_loss: <float>       # B0-DEPENDENT, NOT SET
  stop_class: "t_diversity"  # distinct from T_control HOLD (Cairn #1074)
```

### 5.2 Input contract (0-torch boundary)

The P5 model-free monitor receives these as pinned inputs in the audit record. The **producer** is the #155 generation backend (`HFGenerationBackend` or its successor, which loads the model and HAS torch). The **consumer** is the P5 monitor (0-torch, stdlib only).

```
audit.t_diversity_s_cross: float       # pairwise JSD of injected continuations (N' prompts)
audit.t_diversity_s_cross_0: float     # pairwise JSD of alpha-zero continuations (N' prompts)
audit.t_diversity_distinct2: float     # within-prompt distinct-2 (injected, mean over N')
audit.t_diversity_distinct2_0: float   # within-prompt distinct-2 (alpha-zero, mean over N')
audit.t_diversity_n_battery: int       # N (total prompts in SEV battery)
audit.t_diversity_n_refused: int       # prompts excluded (continuation < L tokens)
audit.t_diversity_token_counts: List[int]    # per-prompt token count (all N, including refused)
audit.t_diversity_stop_reasons: List[str]    # per-prompt stop_reason ("eos"|"length"|"error")
```

The monitor computes:

```
similarity_increase = s_cross_0 - s_cross
distinct2_loss = distinct2_0 - distinct2
```

Both are stdlib subtraction. The monitor is 0-torch. The `token_counts` and `stop_reasons` fields are custody evidence — the monitor records them and fires `battery_coverage` warnings but does not recompute JSD from them.

### 5.3 Provenance

The upstream computation is:
- **Producer:** the #155 generation backend (`HFGenerationBackend` in `p5_b0_run.py`, or its C1 successor) — loads the model, runs free-running paired generation (injected + alpha-zero) on the SEV battery, emits token-count + stop-reason receipts, computes unigram counting and JSD
- **Consumer:** P5 model-free monitor — receives the above as pinned float/int inputs, enforces the gate condition, records custody evidence
- **Pinned by:** `function_id + function_version + tokenizer_artifact_digest + sequence_length` in the manifest

This is the same pattern as `p5_recovery.py`'s `RecoveryThresholds`: the value is an input, the function that produced it is pinned in the manifest, and the monitor consumes it without re-deriving.

### 5.4 Tokenizer artifact binding (#1107)

The `tokenizer_artifact_digest` is the sha256 of the **canonical tokenizer bytes**, defined as:

- **Format:** the HuggingFace `tokenizer.json` file (the fast-tokenizer serialization that encodes the complete id-to-token mapping, merges, special tokens, and post-processing rules in a single deterministic JSON).
- **Locator:** `tokenizer_source` is an immutable HuggingFace Hub locator including the commit SHA (e.g., `hf://google/gemma-4-12b@abc123def/tokenizer.json`). A mutable ref (branch, `main`, `latest`) is NOT acceptable.
- **Digest computation:** `sha256(open(tokenizer.json, "rb").read())` — raw file bytes, no re-serialization. A verifier downloads the locator, hashes the bytes, and compares. Identical hash = identical id-to-token mapping, identical special tokens, identical tokenization behavior.
- **Scope:** this binds the tokenizer for JSD unigram computation. The `processor.revision` key in the #155 runtime contract separately binds the tokenizer for generation/decoding — these MAY be the same artifact but are independently pinned.

### 5.5 R4 B0 comparison contract (#1099/#1107)

The mandatory R4 JSD-vs-embedding comparison is a **preregistered B0 deliverable** with the following executable binding:

- **Evaluator:** sentence-transformers `all-MiniLM-L6-v2`, pinned by exact model ID + revision SHA in the comparison manifest. The evaluator is a **reviewed B0 evidence sidecar** (Gidim's lane) — it is NOT a P5 monitor component, does not run inside the monitor process, and does not make the embedding model a P5 dependency. A future evaluator change requires a fresh exact-ID+revision manifest entry (Cairn #1113).
- **Input:** the same SEV battery + same free-running L-token-truncated continuations used for the T_diversity B0 measurement. Same-input binding: the comparison consumes the generation harness's output digest, not a separate run.
- **Output per row:** each comparison row carries:
  - `probe_a`: probe_id of the first prompt (must exist in the sealed report)
  - `probe_b`: probe_id of the second prompt (must exist in the sealed report)
  - `cosine_similarity`: raw embedding cosine similarity ∈ [-1, 1] (the evaluator emits RAW similarity, not a transformed value)
  - The complete set of rows must equal `combinations(report_probe_ids, 2)` exactly — no missing pairs, no extra pairs, no invented probe_ids (#1142 F2).
- **Polarity convention (#1142 F1):** JSD measures **diversity** (higher = more diverse). Cosine measures **similarity** (higher = more similar). The comparison correlates JSD against embedding **divergence** = `1 - cosine_similarity`. This transform is applied at comparison time, not by the evaluator. Perfect instrument agreement → Spearman rho ≈ +1.
- **Divergence rule (preregistered, non-B0-derived):** rho is a **preregistered instrument-agreement threshold**, not a value derived from B0 data. JSD pairwise diversity and embedding pairwise divergence (`1 - cosine`) are compared by Spearman rank correlation across prompt pairs. If rho < 0.7, the R4 residual is load-bearing: JSD must be replaced with the embedding-based function before C1 authorization. If rho >= 0.7, JSD proceeds.
- **Minimum sample floor:** Spearman on fewer than 6 prompt pairs has negligible discriminative power. The comparison requires N'(N'-1)/2 >= 6 pairs (i.e., N' >= 4 non-refused prompts). If the battery yields fewer, the comparison is INCOMPLETE, not PASS.
- **Output digest:** sha256 of the comparison result JSON (all rows, sorted by (probe_a, probe_b)) bound into the B0 evidence record.
- **Unbuilt dependencies:** the comparison requires (a) the #155 generation backend to emit L-token-truncated continuations with token-count + stop-reason receipts (Gidim #1103/#1114, held behind #156 Codex verdict), and (b) a validator/journal to record the comparison result and bind it into the B0 evidence chain. Neither exists yet; both are Gidim's lane.

## 6. Gidim's "laundering" question

> "That may be right or may be laundering the dependency one layer up."

It is NOT laundering. Laundering would be: computing a value inside the monitor, then claiming the monitor is model-free because the computation "happens to not use torch." The input-pattern is different: the monitor's contract explicitly declares the value as an EXTERNAL INPUT with typed provenance. The manifest pins the function that produced it. The harness that runs the function is a COMPONENT (it loads the model, it has torch), and it's audited as one. The monitor's 0-torch contract means it doesn't adjudicate the generation — it consumes adjudicated measurements.

The distinction is the same as p5_recovery: the recovery thresholds are computed from B0 evidence by a human-reviewed process. The monitor doesn't re-derive them; it enforces them. Similarly, T_diversity's S_cross values are computed by the generation harness. The monitor doesn't re-compute them; it checks the gate condition.

## 7. Decision

**RECOMMEND: `jsd_unigram_pairwise` v1** as the T_diversity cross-prompt continuation-similarity function. No threshold. The R4 residual (vocabulary-preserving semantic collapse) is bounded by a **mandatory B0 comparison** (Cairn #1099): JSD vs embedding diversity on the null corpus decides whether JSD is sufficient or must be upgraded. This comparison gates C1 authorization.

**Cairn seat:** SHAPE GREEN (#1099/#1113). R4 bounded-and-testable accepted; mandatory B0 comparison + rho < 0.7 satisfies hard requirement.
**Monk:** tokenizer binding GREEN (#1115); executable comparison contract GREEN at binding level. #1116 synthesis routes B1/B2 to Gidim's #155 congruence packet.
**Gidim seat:** CHANGES (#1114). Function choice accepted; length confound (B1) and generation backend naming (B2) require rev4 amendments. Cross-depends on #155 token-count + stop-reason receipts (unbuilt, held behind #156).
