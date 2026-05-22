"""Tests for the rotation engine.

The most important invariant is correctness against the schema:
- Every team plays every other team exactly once per Durchgang (round-robin).
- Odd-team formats (3/5/7) have exactly one team breaking per round.
- 8'er Spiegel produces the exact pair/Bahn/Anschuss table from image6.
"""

from collections import Counter

import pytest

from eisstock.rotation import (
    EIGHT_TEAM_REFERENCE,
    _circle_pairings,
    generate_spiegel,
)


@pytest.mark.parametrize("team_count", [3, 4, 5, 6, 7, 8])
def test_each_pair_plays_exactly_once(team_count: int) -> None:
    rounds = _circle_pairings(team_count)
    seen_pairs: Counter[frozenset[int]] = Counter()
    for r in rounds:
        for g in r.games:
            seen_pairs[frozenset({g.team_a, g.team_b})] += 1

    expected_pairs = team_count * (team_count - 1) // 2
    assert sum(seen_pairs.values()) == expected_pairs
    assert all(count == 1 for count in seen_pairs.values()), (
        f"Some pairs play more than once: {seen_pairs}"
    )


@pytest.mark.parametrize("team_count", [3, 4, 5, 6, 7, 8])
def test_round_count(team_count: int) -> None:
    """Round-robin needs n-1 rounds for even n, n rounds for odd n."""
    rounds = _circle_pairings(team_count)
    expected = team_count - 1 if team_count % 2 == 0 else team_count
    assert len(rounds) == expected


@pytest.mark.parametrize("team_count,games_per_round", [(3, 1), (5, 2), (7, 3)])
def test_odd_formats_have_one_bye_per_round(
    team_count: int, games_per_round: int
) -> None:
    rounds = _circle_pairings(team_count)
    bye_counts: Counter[int] = Counter()
    for r in rounds:
        assert r.bye is not None
        assert len(r.games) == games_per_round
        bye_counts[r.bye] += 1
    # Every team should sit out exactly once across the single pass.
    assert all(bye_counts[t] == 1 for t in range(1, team_count + 1))


@pytest.mark.parametrize("team_count,games_per_round", [(4, 2), (6, 3), (8, 4)])
def test_even_formats_have_no_byes(team_count: int, games_per_round: int) -> None:
    rounds = _circle_pairings(team_count)
    for r in rounds:
        assert r.bye is None
        assert len(r.games) == games_per_round


def test_eight_team_matches_official_table() -> None:
    """The circle method must reproduce the 8'er Spiegel table from image6
    exactly: same pairs, same Bahn assignment, same Anschuss team per game.
    """
    rounds = _circle_pairings(8)
    assert len(rounds) == 7

    for r_idx, plan in enumerate(rounds):
        ref_row = EIGHT_TEAM_REFERENCE[r_idx]
        assert len(plan.games) == 4
        for g_idx, game in enumerate(plan.games):
            ref_a, ref_b, ref_anschuss, ref_bahn = ref_row[g_idx]
            actual_pair = frozenset({game.team_a, game.team_b})
            expected_pair = frozenset({ref_a, ref_b})
            assert actual_pair == expected_pair, (
                f"Round {r_idx + 1} game {g_idx}: pair {actual_pair} "
                f"!= reference {expected_pair}"
            )
            assert game.bahn == ref_bahn
            assert game.anschuss == ref_anschuss, (
                f"Round {r_idx + 1} Bahn {ref_bahn}: Anschuss "
                f"{game.anschuss} != reference {ref_anschuss}"
            )


def test_durchgang_two_swaps_anschuss() -> None:
    """In Doppelrunde, every Rückrunde game has Anschuss swapped vs Hinrunde."""
    schedule = generate_spiegel(4, durchgaenge=2)
    n_first = 3  # 4'er has 3 rounds per Durchgang

    hinrunde = schedule[:n_first]
    rueckrunde = schedule[n_first:]
    assert len(rueckrunde) == n_first

    for hin, rueck in zip(hinrunde, rueckrunde):
        assert rueck.runde == hin.runde + n_first
        for hin_game, rueck_game in zip(hin.games, rueck.games):
            assert {hin_game.team_a, hin_game.team_b} == {
                rueck_game.team_a,
                rueck_game.team_b,
            }
            # Anschuss must be the *other* team on the second pass.
            assert hin_game.anschuss != rueck_game.anschuss


def test_rejects_invalid_team_count() -> None:
    with pytest.raises(ValueError):
        _circle_pairings(2)
    with pytest.raises(ValueError):
        _circle_pairings(9)


def test_rejects_invalid_durchgaenge() -> None:
    with pytest.raises(ValueError):
        generate_spiegel(6, durchgaenge=3)
