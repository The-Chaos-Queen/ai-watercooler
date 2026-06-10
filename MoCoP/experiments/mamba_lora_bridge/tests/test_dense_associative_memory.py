"""Unit tests for DenseAssociativeMemory — Phase 0 spike.

Written FIRST per TDD. Implementation follows.
"""

import numpy as np
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dense_associative_memory import DenseAssociativeMemory, RetrievalResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _random_unit(d: int, rng: np.random.Generator | None = None) -> np.ndarray:
    rng = rng or np.random.default_rng(42)
    v = rng.standard_normal(d)
    return v / np.linalg.norm(v)


def _orthonormal_set(k: int, d: int, rng: np.random.Generator | None = None) -> np.ndarray:
    """Return k orthonormal vectors in R^d via QR."""
    rng = rng or np.random.default_rng(99)
    A = rng.standard_normal((d, k))
    Q, _ = np.linalg.qr(A)
    return Q[:, :k].T  # (k, d)


# ---------------------------------------------------------------------------
# 1. Store and retrieve a single pattern (exact recovery)
# ---------------------------------------------------------------------------

class TestSinglePatternRecovery:
    def test_single_step_exact(self):
        dam = DenseAssociativeMemory(dim=64, beta=20.0, n=4)
        v = _random_unit(64)
        dam.store(v, memory_id="only")

        result = dam.retrieve_single_step(v, top_k=1)
        assert isinstance(result, RetrievalResult)
        assert result.indices == [0]
        # weight on the single pattern should be ~1.0
        assert result.weights[0] > 0.99
        assert not result.no_match

    def test_iterative_exact(self):
        dam = DenseAssociativeMemory(dim=64, beta=20.0, n=4)
        v = _random_unit(64)
        dam.store(v)

        result = dam.retrieve_iterative(v, top_k=1)
        assert result.converged
        assert result.indices == [0]
        assert result.iterations >= 0

    def test_quadratic_exact(self):
        dam = DenseAssociativeMemory(dim=64, beta=20.0, n=2)
        v = _random_unit(64)
        dam.store(v)

        result = dam.retrieve_single_step(v, top_k=1)
        assert result.indices == [0]
        assert result.weights[0] > 0.99


# ---------------------------------------------------------------------------
# 2. Three orthogonal patterns — query near one, verify it dominates
# ---------------------------------------------------------------------------

class TestOrthogonalPatterns:
    def setup_method(self):
        self.d = 128
        self.patterns = _orthonormal_set(3, self.d)
        self.dam4 = DenseAssociativeMemory(dim=self.d, beta=10.0, n=4)
        self.dam4.store_batch(self.patterns)

    def test_nearest_dominates_single_step(self):
        # query is pattern 0 + small noise
        rng = np.random.default_rng(7)
        noise = rng.standard_normal(self.d) * 0.05
        query = self.patterns[0] + noise
        query /= np.linalg.norm(query)

        result = self.dam4.retrieve_single_step(query, top_k=1)
        assert result.indices[0] == 0
        assert result.weights[0] > result.weights[1]
        assert result.weights[0] > result.weights[2]

    def test_nearest_dominates_iterative(self):
        rng = np.random.default_rng(7)
        noise = rng.standard_normal(self.d) * 0.05
        query = self.patterns[1] + noise
        query /= np.linalg.norm(query)

        result = self.dam4.retrieve_iterative(query, top_k=1, alpha=0.5)
        assert result.indices[0] == 1
        assert result.converged


# ---------------------------------------------------------------------------
# 3. Correlated "episode" patterns — partial cue retrieves constellation
# ---------------------------------------------------------------------------

class TestEpisodeConstellation:
    def setup_method(self):
        self.d = 128
        rng = np.random.default_rng(12)

        # Build a tight cluster of 4 "episode" vectors: base + small perturbations
        base = _random_unit(self.d, rng)
        self.episode_indices = []
        self.dam = DenseAssociativeMemory(dim=self.d, beta=5.0, n=4)

        for i in range(4):
            noise = rng.standard_normal(self.d) * 0.15
            v = base + noise
            v /= np.linalg.norm(v)
            idx = self.dam.store(v, memory_id=f"ep_{i}")
            self.episode_indices.append(idx)

        # 3 distant distractors
        for i in range(3):
            v = _random_unit(self.d, rng)
            self.dam.store(v, memory_id=f"dist_{i}")

        self.base = base

    def test_episode_members_in_top_k(self):
        """Querying near the episode base should retrieve multiple episode members."""
        rng = np.random.default_rng(55)
        query = self.base + rng.standard_normal(self.d) * 0.1
        query /= np.linalg.norm(query)

        result = self.dam.retrieve_single_step(query, top_k=5)
        ep_in_top5 = set(result.indices[:5]) & set(self.episode_indices)
        # at least 3 of 4 episode members should appear
        assert len(ep_in_top5) >= 3, f"Only {len(ep_in_top5)} episode members in top-5"

    def test_iterative_retrieves_episode(self):
        rng = np.random.default_rng(55)
        query = self.base + rng.standard_normal(self.d) * 0.1
        query /= np.linalg.norm(query)

        result = self.dam.retrieve_iterative(query, top_k=5, alpha=0.5)
        ep_in_top5 = set(result.indices[:5]) & set(self.episode_indices)
        assert len(ep_in_top5) >= 3


# ---------------------------------------------------------------------------
# 4. n=4 produces sharper basins (lower entropy) than n=2
# ---------------------------------------------------------------------------

class TestQuarticVsQuadratic:
    def test_n4_sharper_than_n2_iterative(self):
        """n=4 iterative dynamics produce sharper basins than n=2.

        The sharpening benefit of quartic (n=4) comes from the attractor
        dynamics: the cubic nonlinearity in the update rule amplifies gaps
        between aligned and unaligned patterns over multiple iterations.
        This is distinct from the single-step softmax, where absolute
        scale matters more than the ratio.
        """
        d = 128
        rng = np.random.default_rng(33)

        # correlated patterns so multiple have moderate overlap
        target = _random_unit(d, rng)
        patterns = [target]
        for _ in range(4):
            v = target + rng.standard_normal(d) * 1.0
            v /= np.linalg.norm(v)
            patterns.append(v)
        patterns = np.stack(patterns)

        dam2 = DenseAssociativeMemory(dim=d, beta=10.0, n=2)
        dam4 = DenseAssociativeMemory(dim=d, beta=10.0, n=4)
        dam2.store_batch(patterns)
        dam4.store_batch(patterns)

        noise = rng.standard_normal(d) * 0.1
        query = target + noise
        query /= np.linalg.norm(query)

        r2 = dam2.retrieve_iterative(query, top_k=5, alpha=0.5)
        r4 = dam4.retrieve_iterative(query, top_k=5, alpha=0.5)

        # n=4 iterative should produce lower entropy (sharper basin)
        assert r4.basin_entropy < r2.basin_entropy, (
            f"n=4 entropy {r4.basin_entropy:.4f} >= n=2 entropy {r2.basin_entropy:.4f}"
        )


# ---------------------------------------------------------------------------
# 5. No-match detection (overlap-based with tau)
# ---------------------------------------------------------------------------

class TestNoMatchDetection:
    def test_random_query_triggers_no_match(self):
        d = 128
        rng = np.random.default_rng(77)

        dam = DenseAssociativeMemory(dim=d, beta=10.0, tau=0.15, n=4)
        # store orthogonal patterns so random query has ~0 overlap
        patterns = _orthonormal_set(5, d, rng)
        dam.store_batch(patterns)

        # in d=128, a random unit vector has expected |cos| ~ sqrt(1/d) ~ 0.09
        # with tau=0.15, this should trigger no_match
        query = _random_unit(d, rng)
        result = dam.retrieve_single_step(query, top_k=5)
        assert result.no_match, "Expected no_match=True for orthogonal query"


# ---------------------------------------------------------------------------
# 6. Energy-based no-match
# ---------------------------------------------------------------------------

class TestEnergyBasedNoMatch:
    def test_energy_no_match_on_random_query(self):
        d = 128
        rng = np.random.default_rng(88)

        dam = DenseAssociativeMemory(dim=d, beta=10.0, tau=0.01, n=4)
        patterns = _orthonormal_set(5, d, rng)
        dam.store_batch(patterns)

        # query aligned with a stored pattern → deep energy well
        good_query = patterns[0].copy()
        r_good = dam.retrieve_iterative(good_query, top_k=5, alpha=0.5)

        # random query → shallow energy
        bad_query = _random_unit(d, rng)
        r_bad = dam.retrieve_iterative(bad_query, top_k=5, alpha=0.5)

        # good query should have lower (more negative) energy
        assert r_good.converged_energy < r_bad.converged_energy, (
            f"Good energy {r_good.converged_energy:.4f} >= bad energy {r_bad.converged_energy:.4f}"
        )


# ---------------------------------------------------------------------------
# 7. Convergence: iterative dynamics converge within max_iter
# ---------------------------------------------------------------------------

class TestConvergence:
    def test_converges_within_max_iter(self):
        d = 128
        rng = np.random.default_rng(44)

        dam = DenseAssociativeMemory(dim=d, beta=10.0, n=4)
        patterns = _orthonormal_set(10, d, rng)
        dam.store_batch(patterns)

        query = patterns[3] + rng.standard_normal(d) * 0.2
        query /= np.linalg.norm(query)

        result = dam.retrieve_iterative(query, top_k=5, max_iter=100, alpha=0.5)
        assert result.converged
        assert result.iterations <= 100

    def test_n2_also_converges(self):
        d = 128
        rng = np.random.default_rng(44)

        dam = DenseAssociativeMemory(dim=d, beta=10.0, n=2)
        patterns = _orthonormal_set(10, d, rng)
        dam.store_batch(patterns)

        query = patterns[3] + rng.standard_normal(d) * 0.2
        query /= np.linalg.norm(query)

        result = dam.retrieve_iterative(query, top_k=5, max_iter=100, alpha=0.5)
        assert result.converged


# ---------------------------------------------------------------------------
# 8. Episode prototype
# ---------------------------------------------------------------------------

class TestEpisodePrototype:
    def test_prototype_stored_and_retrievable(self):
        d = 128
        rng = np.random.default_rng(22)

        dam = DenseAssociativeMemory(dim=d, beta=5.0, n=4)
        base = _random_unit(d, rng)

        # store episode members
        for _ in range(4):
            v = base + rng.standard_normal(d) * 0.15
            v /= np.linalg.norm(v)
            dam.store(v)

        # compute and store prototype (centroid)
        centroid = base.copy()
        centroid /= np.linalg.norm(centroid)
        proto_idx = dam.store(centroid, is_prototype=True)

        # query near the centroid — prototype should appear in top-k
        query = base + rng.standard_normal(d) * 0.05
        query /= np.linalg.norm(query)
        result = dam.retrieve_single_step(query, top_k=5)
        assert proto_idx in result.indices[:5], "Prototype should appear in top-5"


# ---------------------------------------------------------------------------
# 9. Pairwise similarity diagnostic
# ---------------------------------------------------------------------------

class TestPairwiseSimilarity:
    def test_similarity_matrix_shape(self):
        d = 64
        dam = DenseAssociativeMemory(dim=d, n=4)
        rng = np.random.default_rng(11)
        for _ in range(5):
            dam.store(_random_unit(d, rng))

        sim = dam.pairwise_similarity()
        assert sim.shape == (5, 5)
        # diagonal should be ~1.0
        np.testing.assert_allclose(np.diag(sim), 1.0, atol=1e-6)
        # should be symmetric
        np.testing.assert_allclose(sim, sim.T, atol=1e-10)


# ---------------------------------------------------------------------------
# 10. Store/remove bookkeeping
# ---------------------------------------------------------------------------

class TestStoreRemove:
    def test_store_batch(self):
        d = 64
        dam = DenseAssociativeMemory(dim=d, n=4)
        rng = np.random.default_rng(1)
        vecs = np.stack([_random_unit(d, rng) for _ in range(5)])
        indices = dam.store_batch(vecs, memory_ids=["a", "b", "c", "d", "e"])
        assert len(indices) == 5
        assert dam.pattern_count == 5

    def test_remove_pattern(self):
        d = 64
        dam = DenseAssociativeMemory(dim=d, n=4)
        rng = np.random.default_rng(1)
        for _ in range(3):
            dam.store(_random_unit(d, rng))
        assert dam.pattern_count == 3
        dam.remove(1)
        assert dam.pattern_count == 2


# ---------------------------------------------------------------------------
# 11. Energy function
# ---------------------------------------------------------------------------

class TestEnergy:
    def test_stored_pattern_has_low_energy(self):
        d = 64
        dam = DenseAssociativeMemory(dim=d, n=4)
        v = _random_unit(d)
        dam.store(v)

        e_at_pattern = dam.energy(v)
        # energy at a stored pattern: -0.5 - 0.25*(1^4) = -0.75
        assert e_at_pattern < -0.5

    def test_random_point_has_higher_energy(self):
        d = 128
        rng = np.random.default_rng(55)
        dam = DenseAssociativeMemory(dim=d, n=4)
        patterns = _orthonormal_set(5, d, rng)
        dam.store_batch(patterns)

        e_good = dam.energy(patterns[0])
        e_rand = dam.energy(_random_unit(d, rng))
        assert e_good < e_rand


# ---------------------------------------------------------------------------
# 12. RetrievalResult fields
# ---------------------------------------------------------------------------

class TestRetrievalResultFields:
    def test_all_fields_present(self):
        d = 64
        dam = DenseAssociativeMemory(dim=d, n=4)
        v = _random_unit(d)
        dam.store(v)

        r = dam.retrieve_single_step(v, top_k=1)
        # check all expected fields
        assert isinstance(r.indices, list)
        assert isinstance(r.weights, np.ndarray)
        assert isinstance(r.overlaps, np.ndarray)
        assert isinstance(r.converged, bool)
        assert isinstance(r.iterations, int)
        assert isinstance(r.energy, float)
        assert isinstance(r.basin_entropy, float)
        assert isinstance(r.no_match, bool)
        assert isinstance(r.no_match_energy, bool)
        assert isinstance(r.converged_energy, float)

    def test_iterative_result_fields(self):
        d = 64
        dam = DenseAssociativeMemory(dim=d, n=4)
        v = _random_unit(d)
        dam.store(v)

        r = dam.retrieve_iterative(v, top_k=1)
        assert r.converged
        assert r.iterations >= 0
        assert r.energy < 0
        assert r.converged_energy < 0


# ---------------------------------------------------------------------------
# 13. Generalized n support
# ---------------------------------------------------------------------------

class TestGeneralizedN:
    def test_n2_energy(self):
        """n=2: E = -||x||^2/2 - (1/2)*sum(m^2)"""
        d = 64
        dam = DenseAssociativeMemory(dim=d, n=2)
        v = _random_unit(d)
        dam.store(v)
        e = dam.energy(v)
        # at stored pattern: -0.5 - (1/2)*1 = -1.0
        np.testing.assert_allclose(e, -1.0, atol=1e-6)

    def test_n4_energy(self):
        """n=4: E = -||x||^2/2 - (1/4)*sum(m^4)"""
        d = 64
        dam = DenseAssociativeMemory(dim=d, n=4)
        v = _random_unit(d)
        dam.store(v)
        e = dam.energy(v)
        # at stored pattern: -0.5 - (1/4)*1 = -0.75
        np.testing.assert_allclose(e, -0.75, atol=1e-6)
