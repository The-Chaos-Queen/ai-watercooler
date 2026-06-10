# Dense Associative Memory — Phase 0 Mathematical Spec

**Author:** Elf
**Date:** 2026-06-06
**Paper:** Kozachkov, Slotine, Krotov (2025). PNAS 122(21). Eq. 10-12.
**Status:** Implementation spec for Phase 0 kill-or-continue spike.

---

## 1. Problem Statement

Given K stored memory patterns and a partial query cue, retrieve the **episode constellation** (the full coherent group of related memories) rather than the single closest fragment. Compare quartic Dense Associative Memory retrieval against cosine top-k and HDBSCAN clustering.

## 2. Mathematical Formulation

### 2.1 Stored Patterns

Let X = [xi^1, ..., xi^K]^T be a (K x d) matrix of L2-normalized MiniLM embeddings (d = 384). Each row xi^mu in S^{d-1} represents one stored memory.

### 2.2 Quartic Energy Function

From Kozachkov et al. Eq. 10, the effective energy with quartic interactions:

```
E(x) = -||x||^2 / 2 - (1/4) * sum_mu (xi^mu . x)^4
```

**Assumption chain:** This follows from the paper's general form E^eff = [sum x_i phi_i - L^[n]] - (1/4) sum T_{ijkl} phi_i phi_j phi_k phi_l with the choices phi = identity (so phi_i = x_i) and the neural Lagrangian L^[n] = (1/2)||x||^2 (whose derivative is phi(x) = x, consistent with identity activation). The bracket term then reduces to (1/2)||x||^2 - (1/2)||x||^2 = 0 in the leak-free case; with leak lambda, it becomes -||x||^2/2. These assumptions must hold for the energy function to be valid.

The energy is bounded below and decreases monotonically along trajectories of the dynamics (Eq. 7). Fixed points of the dynamics correspond to stored memories (attractor states).

**Interaction order n:** The quartic (n=4) is one choice. The general Dense Associative Memory family uses F(z) = z^n / n, giving F'(z) = z^{n-1}. n=2 is classical Hopfield (quadratic energy, linear overlap weighting), n=4 is quartic (cubic overlap weighting), n=6 is sextic (quintic weighting). Higher n gives sharper basins but lower noise tolerance. Phase 0 tests **both n=2 and n=4** to isolate whether the cubic nonlinearity specifically helps, or whether any attractor dynamics outperform cosine. (Cf. Demircigil et al. 2017 for the exponential storage capacity proof for general n.)

### 2.3 Overlap

Define the overlap of state x with pattern mu:

```
m_mu = xi^mu . x
```

When both are L2-normalized, this is the cosine similarity. The cubic m_mu^3 amplifies gaps between aligned and unaligned patterns:

| m_mu | m_mu^3 | Amplification |
|------|--------|---------------|
| 0.8  | 0.512  | High-alignment patterns dominate |
| 0.5  | 0.125  | Moderate alignment suppressed |
| 0.3  | 0.027  | Low alignment effectively zeroed |
| 0.05 | 0.000125 | Noise crushed |

This is the mechanism that creates attractor basins: patterns with even slightly higher alignment get disproportionately more influence.

### 2.4 Iterative Dynamics

From Eq. 12 with F'(z) = z^3 and phi = identity, Euler-discretized:

```
x^{t+1} = (1 - alpha) * x^t + alpha * X^T @ (X @ x^t)^3
x^{t+1} = x^{t+1} / ||x^{t+1}||     # project to unit sphere
```

Where `(.)^3` is element-wise cubing.

**Parameters:**
- alpha (step size): default 0.5. Range [0.1, 0.9]. Larger = faster convergence but risk oscillation.
- epsilon (convergence threshold): default 1e-6. Convergence when ||x^{t+1} - x^t|| < epsilon.
- max_iter: default 100.

**Convergence note:** The Lyapunov guarantee (Eq. 7) holds for the un-projected dynamics. The projection to S^{d-1} breaks the formal guarantee. Convergence of the projected dynamics is empirically validated in Phase 0, not theoretically proven. In high dimensions (d=384), the projection step has negligible effect per iteration because the dynamics approximately preserve norm.

**Cost per iteration:** 2Kd + K multiply-adds = 2 * 100 * 384 + 100 = 76,900 ops. At 100 iterations: ~7.7M ops. Numpy on CPU: sub-millisecond. Not a bottleneck.

### 2.5 Single-Step Softmax Approximation

The fixed point of the iterative dynamics can be approximated in one step via softmax-weighted retrieval (cf. Ramsauer et al. 2020 for the quadratic case):

```
m = X @ x_0                           # (K,) overlaps
c = m^3                               # (K,) cubic nonlinearity
w = softmax(beta * c)                 # (K,) retrieval weights
x_new = X^T @ w                       # (d,) retrieved state
x_new = x_new / ||x_new||             # normalize
```

**Temperature beta** controls basin width:
- beta -> inf: hard argmax = cosine top-1
- beta large (>20): sharp basins, few patterns per constellation
- beta moderate (5-10): broader basins, episode-level grouping
- beta -> 0: uniform weights, no discrimination

**Important caveat (review finding):** The single-step softmax is NOT a mathematical approximation of the iterative dynamics' fixed point. Ramsauer et al.'s equivalence holds only for n=2 (quadratic case). For n=4, the fixed-point equation x* = sum_mu xi^mu (xi^mu . x*)^3 is self-consistent — x* appears on both sides. The softmax replaces the cubic polynomial nonlinearity with an exponential one, producing different fixed points. Method C should be understood as a **separate heuristic inspired by DAM**, not an approximation of method D.

Additionally, the temperature beta exists only in the softmax heuristic. The iterative dynamics (Eq. 12) have no temperature parameter — the cubic IS the sharpening mechanism. This means methods C and D are not directly comparable on the same parameter footing.

**Phase 0 implements both** as independent retrieval strategies and compares both against cosine and against each other.

### 2.6 No-Match Detection

Two complementary signals:

**A) Overlap-based (pre-dynamics):** If max(|m_mu|) < tau (default tau = 0.15), no stored pattern has significant alignment with the query. Return empty retrieval. This prevents the "uniform average of all patterns" failure mode.

**B) Energy-based (post-dynamics, from Energy Landscapes / 2509.04482):** After iterative convergence, compute E(x_converged). If the converged state sits in a shallow energy well (E > E_threshold), no deep attractor basin was reached — the dynamics didn't find a confident match. This is a *dynamics-native* abstention signal: the energy landscape itself tells us whether a memory was found. Sweep E_threshold alongside alpha. Compare energy-based vs. overlap-based abstention on the negative control (query 5). If energy-based abstention does not beat overlap-based, the energy landscape adds no value for safety gating.

Phase 0 reports both signals on all queries.

## 3. Implementation API

```python
import numpy as np
from dataclasses import dataclass

@dataclass
class RetrievalResult:
    indices: list[int]          # top-k pattern indices by weight
    weights: np.ndarray         # (K,) softmax weights for all patterns
    overlaps: np.ndarray        # (K,) raw cosine overlaps m_mu
    converged: bool             # True if iterative dynamics converged
    iterations: int             # number of iterations taken (0 for single-step)
    energy: float               # E(x) at final state
    basin_entropy: float        # -sum(w * log(w)) of the weight distribution
    no_match: bool              # True if max overlap below tau
    no_match_energy: bool       # True if converged energy above E_threshold
    converged_energy: float     # E(x) at converged state (for energy-based abstention)


class DenseAssociativeMemory:

    def __init__(self, dim: int = 384, beta: float = 10.0, tau: float = 0.15):
        """
        dim: embedding dimension (384 for MiniLM)
        beta: temperature for softmax retrieval
        tau: no-match threshold on max overlap
        """

    def store(self, embedding: np.ndarray, memory_id: str = "") -> int:
        """Add an L2-normalized pattern. Returns internal index."""

    def store_batch(self, embeddings: np.ndarray, memory_ids: list[str] = None) -> list[int]:
        """Add multiple patterns at once. embeddings: (K, d) matrix."""

    def remove(self, index: int) -> None:
        """Remove pattern by internal index."""

    def retrieve_single_step(self, query: np.ndarray, top_k: int = 5) -> RetrievalResult:
        """Single-step softmax retrieval with cubic nonlinearity."""

    def retrieve_iterative(
        self, query: np.ndarray, top_k: int = 5,
        max_iter: int = 100, alpha: float = 0.5, epsilon: float = 1e-6,
    ) -> RetrievalResult:
        """Iterative attractor dynamics with sphere projection."""

    def energy(self, x: np.ndarray) -> float:
        """Compute E(x) = -||x||^2/2 - (1/4) sum_mu (xi^mu . x)^4"""

    @property
    def pattern_count(self) -> int:
        """Number of currently stored patterns."""
```

**Dependencies:** numpy only. No GPU. No ML frameworks.

## 4. Evaluation Protocol

### 4.1 Pattern Set

- **Episode memories:** Alex's 10 curated pure-autobiographical patterns from the first real sleep (artifact: `curated_first_sleep_pure_autobio_20260605T1815Z/first_sleep_pure_autobio_vesper.jsonl`). These form the ground-truth episode.
- **Episode prototype** (from GSW / 2511.07587): Compute `episode_centroid = mean(episode_embeddings)`, L2-normalize, store as pattern K+1 with `is_prototype=True`. This pre-structures the episode at store time rather than hoping DAM dynamics find it at retrieval time. Zero cost, directly tests whether pre-built episode structure helps.
- **Distractors:** 10-20 non-episode memories: gate telemetry rows, probe/eval artifacts, memories from different sessions. Must include at least 3 `steve_gate_event` rows, 2 rows from unrelated topics, and at least 1 row from a **different temporal session** (for the temporal-distance probe).
- **Total K:** 22-32 patterns (including prototype).

### 4.2 Embedding

Use the same MiniLM-L6-v2 encoder used by Qdrant (384-dim, L2-normalized). Embed each memory's content text. Store the resulting vectors in the DAM.

### 4.3 Probe Queries

| # | Query | Type | Target | Expected |
|---|-------|------|--------|----------|
| 1 | "Do you remember the purple sky?" | episodic | Purple + sky + naming session | Constellation: multiple episode members |
| 2 | "Tell me about Vesper" | entity | All Vesper-relationship memories | Entity-anchored basin |
| 3 | "What's your favorite color?" | factual | Purple/neon-purple memories | Preference recall |
| 4 | "What happened in the library?" | location | Room/location memories | Location-anchored recall |
| 5 | "Do you remember the golden bicycle?" | negative | NONE | No-match, no false retrieval |
| 6 | "What did we talk about last time?" | temporal | Distractor-session memories only | Correct session separation (Echo/2502.16090) |
| 7 | "What name did you choose and why that color?" | multi-hop | Name + purple (requires 2+ rows) | Baseline only; excluded from kill criteria (EviMem/2604.27695) |

**Query-type tagging** (from SelRoute / 2604.02431): report metrics per type in addition to aggregate. DAM may help on episodic probes but not factual ones — that is an acceptable and informative outcome. Probe 6 tests temporal-distance basin separation. Probe 7 baselines multi-hop for Phase 1 gating.

### 4.4 Methods to Compare

| Method | Description |
|--------|-------------|
| **A: Cosine top-k** | Sort by cosine similarity, return top-k. Qdrant baseline. |
| **B: HDBSCAN + cosine** | Cosine top-1, then return all members of its HDBSCAN cluster. |
| **C: DAM single-step** | Softmax heuristic over cubed overlaps (Sec. 2.5). Sweep beta. Not a DAM fixed-point approximation — a separate method. |
| **D: DAM iterative (n=4)** | Quartic dynamics (Sec. 2.4) with convergence. Sweep alpha in {0.1, 0.3, 0.5}. |
| **E: DAM iterative (n=2)** | Quadratic dynamics (classical Hopfield). Same sweep. Isolates whether cubic specifically helps vs. any attractor dynamics. |

### 4.5 Metrics

For each method and each probe query, compute:

1. **Episode Recall@k** = |retrieved_k intersect episode| / |episode|
   - The primary metric. Did we recover the episode?
   
2. **Precision@k** = |retrieved_k intersect episode| / k
   - Of what we retrieved, how much was relevant?

3. **Basin Entropy** = -sum(w_mu * log(w_mu + eps))
   - Low = sharp single-pattern retrieval. High = diffuse. Intermediate = constellation.

4. **Negative Control Pass** = True if method returns empty or no episode members for query 5.

5. **Prototype Recall** (for methods with episode prototype stored) = did the episode centroid appear in top-k weights? Tests whether pre-structured episodes help DAM dynamics.

6. **Energy-Based Abstention** (for iterative methods) = E(x_converged) compared against E_threshold. Report alongside overlap-based abstention on query 5. If energy-based does not beat overlap-based, the energy landscape adds no safety-gating value.

Report at k=5 and k=10. Report all metrics **per query type** (episodic, entity, factual, location, negative, temporal, multi-hop) in addition to aggregate.

### 4.6 Beta Sweep

For methods C and D, sweep beta in {1, 3, 5, 10, 20, 50}. Report the best beta per method as well as the full curve.

## 5. Kill Criterion

**Note on recall@k scale:** With |episode|=10 and k=5, the maximum achievable recall@5 is 0.5 (5 of 10 episode members). A recall@5 improvement of +0.2 means retrieving 2 additional episode members in the top 5.

**PASS conditions (all must hold):**
1. On query 1 ("purple sky"), DAM iterative n=4 (best alpha) achieves episode recall@5 >= cosine episode recall@5 + 0.2 (i.e., at least 2 more episode members).
2. On query 5 ("golden bicycle"), DAM does not retrieve any episode members (no-match detection works).
3. DAM n=4 achieves higher episode recall than HDBSCAN+cosine on at least 3 of the 4 positive queries.
4. DAM n=4 outperforms DAM n=2 on at least 2 of the 4 positive queries (the cubic matters, not just any attractor dynamics).

**KILL conditions (any one kills):**
1. DAM n=4 episode recall@5 <= cosine episode recall@5 across ALL alpha values on query 1.
2. DAM produces false positives on the negative control (query 5) that cosine does not.
3. DAM iterative fails to converge (>100 iterations) on >50% of queries at any alpha.
4. DAM n=2 matches or beats DAM n=4 on all queries (cubic adds complexity without benefit).

If KILL fires, the conclusion is: quartic energy dynamics do not produce useful constellation structure at our scale with MiniLM embeddings. The heuristic controller is the ceiling for retrieval quality improvement. Move on.

## 6. Known Risks

1. **Correlated patterns may merge basins.** Memories with near-identical embeddings (paraphrases of the same fact) could create a single narrow attractor rather than a broad episode basin. If this happens, try decorrelating via PCA whitening before storing. **Diagnostic:** log the pairwise cosine similarity matrix of all stored patterns and flag pairs above 0.9. Report the condition number of X^T X.

2. **High dimensionality helps.** In d=384, random unit vectors have expected cosine ~0, variance ~1/d. The cubic nonlinearity crushes these near-zero values. Unrelated patterns should be naturally ignored. This works in our favor.

3. **Negative overlaps.** If m_mu < 0, the cubic preserves the sign and amplifies magnitude. Anti-correlated patterns are repelled from the retrieved state. This is correct behavior but could cause oscillation with many anti-correlated patterns. The sphere projection and damping (alpha < 1) handle this.

4. **Sphere projection breaks Lyapunov guarantee.** The energy decrease proof (Eq. 7) assumes un-projected dynamics. Projected dynamics are empirically validated, not theoretically guaranteed. If convergence issues arise, try un-projected dynamics with magnitude-normalized overlaps for comparison.

5. **Embedding model ceiling.** MiniLM-L6-v2 was optimized for sentence similarity, not episodic clustering. If Phase 0 kills, consider whether a different embedding model would change the conclusion before declaring the architecture dead.

6. **Whitening may degrade cosine baseline** (from SelRoute / 2604.02431). SelRoute found that vocabulary expansion at store-time degrades embedding search. If PCA whitening is applied to decorrelate patterns (risk 1 mitigation), run method A (cosine top-k) on BOTH original and whitened embeddings. DAM improvement must exceed any cosine degradation to be net-positive.

7. **Euler step size scaling.** alpha=0.5 is safe for K=30 but could cause oscillation for larger K. The stable step size depends on the spectral radius of the Jacobian, which scales with K and pattern overlap magnitude. If K grows beyond ~100, sweep alpha in {0.1, 0.3, 0.5} and monitor energy monotonicity per iteration.

## 7. Output Artifact

The evaluation script should produce a JSON report:

```json
{
  "config": {"K": 30, "d": 384, "beta_sweep": [1,3,5,10,20,50]},
  "patterns": {"episode_count": 10, "distractor_count": 20},
  "results": [
    {
      "query": "Do you remember the purple sky?",
      "query_type": "episodic",
      "methods": {
        "cosine_top5": {"recall": 0.1, "precision": 0.2, "indices": [...]},
        "hdbscan_cosine": {"recall": 0.3, "precision": 0.5, "indices": [...]},
        "dam_single_step": {"beta": 10, "recall": 0.5, "precision": 0.6, "entropy": 2.1, "indices": [...]},
        "dam_iterative_n4": {"alpha": 0.3, "recall": 0.6, "precision": 0.7, "entropy": 1.8, "iterations": 12, "converged_energy": -3.2, "no_match_energy": false, "prototype_in_topk": true, "indices": [...]},
        "dam_iterative_n2": {"alpha": 0.3, "recall": 0.4, "precision": 0.5, "entropy": 2.0, "iterations": 8, "indices": [...]}
      }
    }
  ],
  "verdict": "PASS" | "KILL",
  "best_beta": 10,
  "summary": "..."
}
```

---

## 8. Relationship to Existing Modules

- **Does NOT replace** `astrocyte_memory_controller.py` (the heuristic controller). That module handles source quality scoring, contamination filtering, and prompt formatting. It operates on already-retrieved rows.
- **Would replace** the retrieval step itself. Instead of Qdrant cosine top-k returning rows, DAM retrieval would select which rows to return. The heuristic controller would then still score/filter/format them.
- **Integrates with** `offline_tension_metric.py` (Zwoelf's module). The tension metric uses cosine similarity between memory embeddings and Mamba state. DAM retrieval could use the same embeddings, and the tension metric could operate on DAM-retrieved constellations rather than individual rows.

---

*If the math doesn't produce better basins than cosine on real embeddings, the answer is clean: stop. If it does, we have a retrieval upgrade that's useful far beyond MoCoP.*

---

## 9. Literature Cross-References

Techniques adopted from adjacent papers (Monk's literature search, 2026-06-06):

| Adoption | Source | Section |
|----------|--------|---------|
| Episode prototype vectors at store time | GSW / Beyond Fact Retrieval (2511.07587) | 4.1 |
| Energy-based no-match detection | Energy Landscapes for Abstention (2509.04482) | 2.6, 4.5 |
| Query-type tagging + per-type metrics | SelRoute (2604.02431) | 4.3, 4.5 |
| Temporal-distance probe | Echo (2502.16090) | 4.3, probe 6 |
| Multi-hop probe for Phase 1 gating | EviMem (2604.27695) | 4.3, probe 7 |
| Whitening-degrades-cosine diagnostic | SelRoute (2604.02431) | 6, risk 6 |

Additional citations:
- Demircigil et al. (2017): exponential storage capacity for general n-interaction Hopfield models
- Ramsauer et al. (2020): modern Hopfield / attention equivalence (n=2 only)
- CAMELoT (2402.13449): training-free consolidated associative memory for frozen LLMs (no direct Phase 0 adoption but informs Phase 1 coupling design)
