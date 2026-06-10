"""Tests for the DAM Phase 0 evaluation harness.

Verifies the harness runs with built-in fixtures and produces valid output.
"""

import json
import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from run_dam_phase0_eval import (
    build_fixture_data,
    build_embeddings_from_texts,
    run_evaluation,
    PROBES,
)


class TestFixtureData:
    def test_fixtures_have_episode_and_distractor(self):
        data = build_fixture_data()
        episode = [r for r in data if r["group"] == "episode"]
        distractor = [r for r in data if r["group"] == "distractor"]
        assert len(episode) >= 5
        assert len(distractor) >= 5

    def test_fixtures_have_required_fields(self):
        data = build_fixture_data()
        for row in data:
            assert "text" in row
            assert "group" in row
            assert "memory_id" in row


class TestEmbeddingFallback:
    def test_random_embeddings_correct_shape(self):
        data = build_fixture_data()
        texts = [r["text"] for r in data]
        embeddings = build_embeddings_from_texts(texts, use_model=False)
        assert embeddings.shape == (len(texts), 384)
        # check L2 normalized
        norms = np.linalg.norm(embeddings, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-6)


class TestEvalRun:
    def test_eval_produces_valid_report(self):
        report = run_evaluation(use_fixtures=True, use_model=False)

        # top-level keys
        assert "config" in report
        assert "patterns" in report
        assert "results" in report

        # patterns
        assert report["patterns"]["episode_count"] >= 5
        assert report["patterns"]["distractor_count"] >= 5

        # results: one entry per probe
        assert len(report["results"]) == len(PROBES)

        # each result has methods
        for entry in report["results"]:
            assert "query" in entry
            assert "query_type" in entry
            assert "methods" in entry
            methods = entry["methods"]
            # at least cosine and dam methods present
            assert "cosine_top5" in methods
            assert "dam_single_step" in methods
            assert "dam_iterative_n4" in methods
            assert "dam_iterative_n2" in methods

    def test_negative_control_flagged(self):
        report = run_evaluation(use_fixtures=True, use_model=False)
        # query 5 (index 4) is the negative control
        neg = report["results"][4]
        assert neg["query_type"] == "negative"


class TestOutputFile:
    def test_json_output(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            outpath = f.name

        try:
            report = run_evaluation(
                use_fixtures=True, use_model=False, output_path=outpath
            )
            with open(outpath, "r") as f:
                loaded = json.load(f)
            assert loaded["config"]["d"] == 384
            assert len(loaded["results"]) == len(PROBES)
        finally:
            os.unlink(outpath)


class TestSweepPresence:
    def test_beta_sweep_in_single_step(self):
        report = run_evaluation(use_fixtures=True, use_model=False)
        for entry in report["results"]:
            ss = entry["methods"]["dam_single_step"]
            assert "beta_sweep" in ss
            assert len(ss["beta_sweep"]) >= 3

    def test_alpha_sweep_in_iterative(self):
        report = run_evaluation(use_fixtures=True, use_model=False)
        for entry in report["results"]:
            it4 = entry["methods"]["dam_iterative_n4"]
            assert "alpha_sweep" in it4
            assert len(it4["alpha_sweep"]) >= 2
