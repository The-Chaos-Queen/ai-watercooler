"""Dense Associative Memory — Phase 0 implementation.

Numpy-only. Supports interaction order n=2 (quadratic/classical Hopfield)
and n=4 (quartic) per Kozachkov, Slotine, Krotov (2025). PNAS 122(21).

No ML frameworks. No GPU.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RetrievalResult:
    """Result of a DAM retrieval operation."""
    indices: list[int]           # top-k pattern indices by weight
    weights: np.ndarray          # (K,) softmax weights for all patterns
    overlaps: np.ndarray         # (K,) raw cosine overlaps m_mu
    converged: bool              # True if iterative dynamics converged
    iterations: int              # number of iterations taken (0 for single-step)
    energy: float                # E(x) at final state
    basin_entropy: float         # -sum(w * log(w)) of the weight distribution
    no_match: bool               # True if max overlap below tau
    no_match_energy: bool        # True if converged energy above E_threshold
    converged_energy: float      # E(x) at converged state


def _softmax(z: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    z_shifted = z - np.max(z)
    e = np.exp(z_shifted)
    return e / e.sum()


def _basin_entropy(w: np.ndarray, eps: float = 1e-12) -> float:
    """Compute -sum(w * log(w + eps))."""
    return float(-np.sum(w * np.log(w + eps)))


class DenseAssociativeMemory:
    """Dense Associative Memory with generalized interaction order n.

    Parameters
    ----------
    dim : int
        Embedding dimension (384 for MiniLM).
    beta : float
        Temperature for softmax retrieval (single-step method).
    tau : float
        No-match threshold on max absolute overlap.
    n : int
        Interaction order. n=2 is classical Hopfield, n=4 is quartic.
    e_threshold : float
        Energy threshold for energy-based no-match detection.
        If converged energy is above this, no_match_energy=True.
    """

    def __init__(
        self,
        dim: int = 384,
        beta: float = 10.0,
        tau: float = 0.15,
        n: int = 4,
        e_threshold: float = -0.3,
    ):
        self.dim = dim
        self.beta = beta
        self.tau = tau
        self.n = n
        self.e_threshold = e_threshold

        # Storage: list of (embedding, memory_id, is_prototype)
        self._patterns: list[np.ndarray] = []
        self._memory_ids: list[str] = []
        self._is_prototype: list[bool] = []

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def store(
        self,
        embedding: np.ndarray,
        memory_id: str = "",
        is_prototype: bool = False,
    ) -> int:
        """Add an L2-normalized pattern. Returns internal index."""
        v = np.asarray(embedding, dtype=np.float64).ravel()
        norm = np.linalg.norm(v)
        if norm > 0:
            v = v / norm
        self._patterns.append(v)
        self._memory_ids.append(memory_id)
        self._is_prototype.append(is_prototype)
        return len(self._patterns) - 1

    def store_batch(
        self,
        embeddings: np.ndarray,
        memory_ids: Optional[list[str]] = None,
    ) -> list[int]:
        """Add multiple patterns at once. embeddings: (K, d) matrix."""
        K = embeddings.shape[0]
        if memory_ids is None:
            memory_ids = [""] * K
        indices = []
        for i in range(K):
            idx = self.store(embeddings[i], memory_ids[i])
            indices.append(idx)
        return indices

    def remove(self, index: int) -> None:
        """Remove pattern by internal index."""
        del self._patterns[index]
        del self._memory_ids[index]
        del self._is_prototype[index]

    @property
    def pattern_count(self) -> int:
        """Number of currently stored patterns."""
        return len(self._patterns)

    def _get_pattern_matrix(self) -> np.ndarray:
        """Return (K, d) matrix of stored patterns."""
        if not self._patterns:
            return np.zeros((0, self.dim))
        return np.stack(self._patterns)

    # ------------------------------------------------------------------
    # Energy
    # ------------------------------------------------------------------

    def energy(self, x: np.ndarray) -> float:
        """Compute E(x) = -||x||^2/2 - (1/n) * sum_mu (xi^mu . x)^n"""
        x = np.asarray(x, dtype=np.float64).ravel()
        X = self._get_pattern_matrix()
        if X.shape[0] == 0:
            return -0.5 * np.dot(x, x)
        m = X @ x  # (K,) overlaps
        norm_sq = np.dot(x, x)
        return float(-norm_sq / 2.0 - (1.0 / self.n) * np.sum(m ** self.n))

    # ------------------------------------------------------------------
    # Single-step softmax retrieval
    # ------------------------------------------------------------------

    def retrieve_single_step(
        self, query: np.ndarray, top_k: int = 5
    ) -> RetrievalResult:
        """Single-step softmax retrieval with nonlinearity.

        m = X @ x_0                   # overlaps
        c = m^{n-1}                   # nonlinearity
        w = softmax(beta * c)         # retrieval weights
        x_new = X^T @ w              # retrieved state
        """
        x = np.asarray(query, dtype=np.float64).ravel()
        norm = np.linalg.norm(x)
        if norm > 0:
            x = x / norm

        X = self._get_pattern_matrix()
        K = X.shape[0]

        if K == 0:
            return RetrievalResult(
                indices=[], weights=np.array([]), overlaps=np.array([]),
                converged=True, iterations=0, energy=self.energy(x),
                basin_entropy=0.0, no_match=True, no_match_energy=True,
                converged_energy=self.energy(x),
            )

        # overlaps
        m = X @ x  # (K,)

        # no-match detection (overlap-based)
        no_match = bool(np.max(np.abs(m)) < self.tau)

        # nonlinearity: m^{n-1}
        c = np.sign(m) * np.abs(m) ** (self.n - 1)

        # softmax weights
        w = _softmax(self.beta * c)

        # retrieved state
        x_new = X.T @ w
        x_new_norm = np.linalg.norm(x_new)
        if x_new_norm > 0:
            x_new = x_new / x_new_norm

        # top-k by weight
        sorted_indices = np.argsort(-w).tolist()
        top_indices = sorted_indices[:top_k]

        # energy at retrieved state
        e = self.energy(x_new)

        # basin entropy
        entropy = _basin_entropy(w)

        # energy-based no-match
        no_match_e = bool(e > self.e_threshold)

        return RetrievalResult(
            indices=top_indices,
            weights=w,
            overlaps=m,
            converged=True,
            iterations=0,
            energy=e,
            basin_entropy=entropy,
            no_match=no_match,
            no_match_energy=no_match_e,
            converged_energy=e,
        )

    # ------------------------------------------------------------------
    # Iterative attractor dynamics
    # ------------------------------------------------------------------

    def retrieve_iterative(
        self,
        query: np.ndarray,
        top_k: int = 5,
        max_iter: int = 100,
        alpha: float = 0.5,
        epsilon: float = 1e-6,
    ) -> RetrievalResult:
        """Iterative attractor dynamics with sphere projection.

        x^{t+1} = (1-alpha)*x^t + alpha * X^T @ (X @ x^t)^{n-1}
        x^{t+1} = x^{t+1} / ||x^{t+1}||
        """
        x = np.asarray(query, dtype=np.float64).ravel()
        norm = np.linalg.norm(x)
        if norm > 0:
            x = x / norm

        X = self._get_pattern_matrix()
        K = X.shape[0]

        if K == 0:
            return RetrievalResult(
                indices=[], weights=np.array([]), overlaps=np.array([]),
                converged=True, iterations=0, energy=self.energy(x),
                basin_entropy=0.0, no_match=True, no_match_energy=True,
                converged_energy=self.energy(x),
            )

        # initial overlaps for no-match check
        m_init = X @ x
        no_match = bool(np.max(np.abs(m_init)) < self.tau)

        converged = False
        iterations = 0

        for t in range(max_iter):
            m = X @ x  # (K,) overlaps

            # nonlinearity: element-wise m^{n-1} (sign-preserving)
            m_nonlin = np.sign(m) * np.abs(m) ** (self.n - 1)

            # dynamics update
            x_new = (1.0 - alpha) * x + alpha * (X.T @ m_nonlin)

            # project to unit sphere
            x_new_norm = np.linalg.norm(x_new)
            if x_new_norm > 0:
                x_new = x_new / x_new_norm

            iterations = t + 1

            # convergence check
            if np.linalg.norm(x_new - x) < epsilon:
                converged = True
                x = x_new
                break

            x = x_new

        # final overlaps and weights
        m_final = X @ x
        c = np.sign(m_final) * np.abs(m_final) ** (self.n - 1)
        w = _softmax(self.beta * c)

        # top-k
        sorted_indices = np.argsort(-w).tolist()
        top_indices = sorted_indices[:top_k]

        # energy
        e = self.energy(x)
        entropy = _basin_entropy(w)
        no_match_e = bool(e > self.e_threshold)

        return RetrievalResult(
            indices=top_indices,
            weights=w,
            overlaps=m_final,
            converged=converged,
            iterations=iterations,
            energy=e,
            basin_entropy=entropy,
            no_match=no_match,
            no_match_energy=no_match_e,
            converged_energy=e,
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def pairwise_similarity(self) -> np.ndarray:
        """Return (K, K) cosine similarity matrix of stored patterns."""
        X = self._get_pattern_matrix()
        return X @ X.T
