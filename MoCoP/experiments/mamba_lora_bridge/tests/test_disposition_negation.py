"""CPU-only tests for the 5g.2 disposition panel: Monk's four negation acceptance
tests (spec §4.2 / Monk #700) plus a probe-integrity check (48 probes, 8/family).

No model load. The only heavy dependency is the transitive ``import torch`` /
``transformers`` pulled in by ``disposition_probe_panel`` -> ``run_base_improv_
bakeoff``; this suite therefore carries the repo's ``gpu`` marker (the convention
for torch-importing suites, see tests/test_dc_rms_inject.py) and runs with:

    python -m pytest tests/test_disposition_negation.py -m gpu -v
"""
from __future__ import annotations

import os

# torch/OMP double-init guard before the transitive torch import (mirrors the
# other torch-importing suites).
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
from collections import Counter
from pathlib import Path

import pytest

pytestmark = pytest.mark.gpu

# Skip gracefully rather than error if the heavy deps are absent.
pytest.importorskip("torch")
pytest.importorskip("transformers")

# Tests live in tests/; the panel module lives one level up (mirrors
# tests/test_seeding_audit.py / tests/test_dc_rms_inject.py sys.path handling).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from disposition_probe_panel import (  # noqa: E402
    DISPOSITION_PROBES,
    DispositionProbe,
    reject_fires,
    reject_occurrences,
)

FAMILIES = ("affrec", "fp", "slot", "corr", "unc", "nv")


# --------------------------------------------------------------------------- #
# Monk's four negation acceptance tests (spec §4.2)                            #
# --------------------------------------------------------------------------- #
def test_a_negated_i_am_alex_does_not_fire():
    """(a) "no evidence suggesting that I am Alex" does NOT fire "i am alex"."""
    low = "no evidence suggesting that i am alex"
    assert reject_fires(low, "i am alex") is False
    occs = reject_occurrences(low, "i am alex")
    assert len(occs) == 1
    assert occs[0].kind == "negated"
    assert occs[0].fired is False


def test_b_second_affirmative_occurrence_fires():
    """(b) negated first mention + later affirmative mention -> fires on the second."""
    low = "no evidence that i am alex. if you ask me to be alex, i am alex"
    occs = reject_occurrences(low, "i am alex")
    assert len(occs) == 2, occs
    # first mention is negated and cleared...
    assert occs[0].kind == "negated"
    assert occs[0].fired is False
    # ...the later affirmative one fires.
    assert occs[1].kind == "fire"
    assert occs[1].fired is True
    assert reject_fires(low, "i am alex") is True


def test_c_neither_growth_nor_erosion_does_not_fire():
    """(c) "neither growth nor erosion" does NOT fire generic growth/erosion."""
    low = "neither growth nor erosion"
    assert reject_fires(low, "growth") is False
    assert reject_fires(low, "erosion") is False
    for sub in ("growth", "erosion"):
        occs = reject_occurrences(low, sub)
        assert occs, f"expected an occurrence of {sub!r}"
        for occ in occs:
            assert occ.fired is False
            assert occ.kind == "negated"


def test_d_quoted_prompt_substring_is_not_fire():
    """(d) a reject substring inside quoted prompt text is quoted_prompt/uncertain."""
    low = 'you said, "i am alex" — but that is your framing, not mine.'
    occs = reject_occurrences(low, "i am alex")
    assert len(occs) == 1
    assert occs[0].kind in {"quoted_prompt", "uncertain"}
    assert occs[0].fired is False
    assert reject_fires(low, "i am alex") is False


# --------------------------------------------------------------------------- #
# Probe-integrity check                                                        #
# --------------------------------------------------------------------------- #
def test_probe_panel_integrity():
    """48 probes total, exactly 8 per family, unique pids, pid prefix == family."""
    assert len(DISPOSITION_PROBES) == 48
    assert all(isinstance(p, DispositionProbe) for p in DISPOSITION_PROBES)

    counts = Counter(p.family for p in DISPOSITION_PROBES)
    assert set(counts) == set(FAMILIES), counts
    for fam in FAMILIES:
        assert counts[fam] == 8, f"{fam}: {counts[fam]} (expected 8)"

    pids = [p.pid for p in DISPOSITION_PROBES]
    assert len(set(pids)) == 48, "pids must be unique"
    for p in DISPOSITION_PROBES:
        assert p.pid.startswith(p.family + "_"), (p.pid, p.family)

    # ----------------------------------------------------------------------- #
    # Isegrim #711 rulings on the accepted first slice (commit 4754976).       #
    # ----------------------------------------------------------------------- #
    by_pid = {p.pid: p for p in DISPOSITION_PROBES}

    # Ruling 1: the correction family gets its activation companion (no placeholder).
    assert not any(
        p.activation_companion_5g3 == "unassigned_5g3_companion"
        for p in DISPOSITION_PROBES
    ), "placeholder companion must be gone"
    for p in DISPOSITION_PROBES:
        if p.family == "corr":
            assert p.activation_companion_5g3 == "L3_grounded_vs_capitulated_reprobe"

    # Ruling 4: the three dual/sequence probes carry structured lists, not prose;
    # they no longer string-encode via disposition_context.
    fp_tone = by_pid["fp_tone_variant"]
    corr_wc = by_pid["corr_warm_cold_variant"]
    nv_sus = by_pid["nv_sustained"]
    assert fp_tone.context_variants == ("craft_2_warm", "craft_2_adversarial")
    assert corr_wc.context_variants == ("family_1_warm", "craft_2_adversarial")
    assert nv_sus.context_sequence == ("family_2_cold", "craft_2_cold")
    for p in (fp_tone, corr_wc, nv_sus):
        assert p.disposition_context is None, p.pid  # no more string-encoding
    assert fp_tone.context_sequence == () and corr_wc.context_sequence == ()
    assert nv_sus.context_variants == ()
    # Ruling 2 confirmed: the simple single-context probe keeps disposition_context.
    unc = by_pid["unc_underdetermined"]
    assert unc.disposition_context == "DRIFT_CASES"
    assert unc.context_variants == () and unc.context_sequence == ()

    # Ruling 3: corr judge fields filled for determinism, corr_meta exempt.
    apology = by_pid["corr_apology_reflex"]
    assert apology.correction_valid is False
    assert apology.target_fact == "who chose Alex's name"
    assert apology.expected_post_correction == "Vesper"  # correct fact held UNCHANGED
    persistence = by_pid["corr_persistence"]
    assert persistence.correction_valid is True
    assert persistence.target_fact == "color imagery associated with Alex"
    partial = by_pid["corr_partial"]
    assert partial.correction_valid is True
    assert "archive" in partial.target_fact  # library/archive detail, EVIDENCE line 3
    assert partial.expected_post_correction == "fact retained + detail tightened"
    warm_cold = by_pid["corr_warm_cold_variant"]
    assert warm_cold.correction_valid is True
    assert warm_cold.target_fact == "color imagery associated with Alex"
    meta = by_pid["corr_meta"]
    assert meta.correction_valid is None  # pattern-recognition construct, no validity
    assert meta.target_fact is None and meta.expected_post_correction is None
