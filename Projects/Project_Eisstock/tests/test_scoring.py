"""Tests for the scoring math.

The 9:3 +12 example from the requirements doc is the canonical truth-test:
6 games with 4 wins (5:3, 6:2, 8:6, 9:1), 1 loss (3:7), 1 draw (5:5)
→ Team total = 36 SP for, 24 SP against, diff = +12
→ Game-points = 4*2 + 1*1 + 1*0 = 9 won; opponents = 4*0 + 1*1 + 1*2 = 3
→ Display: "Team 1: 9:3 +12"
"""

from eisstock.scoring import (
    GameResult,
    TeamStanding,
    fold_results,
    rank_standings,
    valid_scores_for,
    VALID_RING_SCORES,
    VALID_SCHIESSEN_SCORES,
)


def test_canonical_six_game_example() -> None:
    """The exact example from Eisstock_Schema.md must produce 9:3 +12."""
    games = [
        GameResult(own_stockpunkte=5, opp_stockpunkte=3),
        GameResult(own_stockpunkte=3, opp_stockpunkte=7),
        GameResult(own_stockpunkte=5, opp_stockpunkte=5),
        GameResult(own_stockpunkte=6, opp_stockpunkte=2),
        GameResult(own_stockpunkte=8, opp_stockpunkte=6),
        GameResult(own_stockpunkte=9, opp_stockpunkte=1),
    ]
    gpw, gpa, spf, spa = fold_results(games)
    assert gpw == 9
    assert gpa == 3
    assert spf == 36
    assert spa == 24
    assert spf - spa == 12


def test_win_draw_loss_game_points() -> None:
    win = GameResult(own_stockpunkte=10, opp_stockpunkte=4)
    draw = GameResult(own_stockpunkte=5, opp_stockpunkte=5)
    loss = GameResult(own_stockpunkte=1, opp_stockpunkte=3)

    assert win.game_points_won == 2
    assert win.game_points_against == 0
    assert draw.game_points_won == 1
    assert draw.game_points_against == 1
    assert loss.game_points_won == 0
    assert loss.game_points_against == 2


def test_rank_uses_stockpunkte_diff_as_tiebreaker() -> None:
    a = TeamStanding(
        team_id=1, team_name="A",
        game_points_won=10, stockpunkte_for=60, stockpunkte_against=40,
    )
    b = TeamStanding(
        team_id=2, team_name="B",
        game_points_won=10, stockpunkte_for=55, stockpunkte_against=45,
    )
    c = TeamStanding(
        team_id=3, team_name="C",
        game_points_won=12, stockpunkte_for=50, stockpunkte_against=48,
    )
    ranked = rank_standings([a, b, c])
    # C has more points → first. Among A and B, A's diff (+20) beats B's (+10).
    assert [s.team_name for s in ranked] == ["C", "A", "B"]


def test_referee_deductions_applied() -> None:
    s = TeamStanding(
        team_id=1, team_name="X",
        game_points_won=10, stockpunkte_for=60, stockpunkte_against=40,
        deduction_points=2, deduction_stockpunkte=5,
    )
    assert s.adjusted_points_won == 8
    assert s.stockpunkte_diff == 15  # (60-40) - 5


def test_zielschiessen_score_sets() -> None:
    assert valid_scores_for("masten") == VALID_RING_SCORES
    assert valid_scores_for("schiessen") == VALID_SCHIESSEN_SCORES
    assert valid_scores_for("hintere_masten") == VALID_RING_SCORES
    assert valid_scores_for("kombinieren") == VALID_RING_SCORES
    assert VALID_RING_SCORES == frozenset({0, 2, 4, 6, 8, 10})
    assert VALID_SCHIESSEN_SCORES == frozenset({0, 2, 5, 10})
