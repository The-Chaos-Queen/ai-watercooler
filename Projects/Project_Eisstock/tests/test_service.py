"""End-to-end service tests using an in-memory SQLite DB."""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from eisstock.models import (  # noqa: F401 - register tables
    Game,
    Player,
    RoundScore,
    Team,
    Tournament,
    ZielAttempt,
)
from eisstock.service import (
    TeamSpec,
    compute_standings,
    create_normal_tournament,
    games_for_bahn,
    set_round_score,
    summarize_game,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _make_teams(n: int) -> list[TeamSpec]:
    return [TeamSpec(name=f"Team {i}") for i in range(1, n + 1)]


def test_create_4er_tournament_materializes_six_games(session: Session) -> None:
    t = create_normal_tournament(
        session, name="4er Test", teams=_make_teams(4)
    )
    games = list(session.exec(__import__("sqlmodel").select(Game).where(Game.tournament_id == t.id)))
    # 4'er Spiegel single Durchgang: 3 rounds × 2 games/round = 6 games.
    assert len(games) == 6


def test_create_8er_materializes_28_games(session: Session) -> None:
    t = create_normal_tournament(session, name="8er Test", teams=_make_teams(8))
    games = list(session.exec(__import__("sqlmodel").select(Game).where(Game.tournament_id == t.id)))
    # 8'er Spiegel single Durchgang: 7 rounds × 4 games/round = 28 games.
    assert len(games) == 28


def test_record_and_summarize_round_scores(session: Session) -> None:
    t = create_normal_tournament(session, name="Score Test", teams=_make_teams(4))
    games = games_for_bahn(session, t.id, "1")
    g = games[0]
    # 4 rounds with team_a scoring 1, 2, 3, 4; rounds 5 and 6 left empty.
    for r, sp in [(1, 1), (2, 2), (3, 3), (4, 4)]:
        set_round_score(
            session,
            game_id=g.id,
            round_idx=r,
            scoring_team_id=g.team_a_id,
            stockpunkte=sp,
        )

    summary = summarize_game(session, g.id)
    assert summary.rounds_a == [1, 2, 3, 4, 0, 0]
    assert summary.rounds_b == [0, 0, 0, 0, 0, 0]
    assert summary.total_a == 10
    assert summary.total_b == 0
    assert summary.current_round == 5  # next empty round


def test_overwriting_a_round_score_edits_in_place(session: Session) -> None:
    t = create_normal_tournament(session, name="Edit Test", teams=_make_teams(4))
    g = games_for_bahn(session, t.id, "1")[0]
    set_round_score(session, game_id=g.id, round_idx=1, scoring_team_id=g.team_a_id, stockpunkte=5)
    set_round_score(session, game_id=g.id, round_idx=1, scoring_team_id=g.team_b_id, stockpunkte=3)
    summary = summarize_game(session, g.id)
    # The same round was rewritten; only the last call wins.
    assert summary.rounds_a[0] == 0
    assert summary.rounds_b[0] == 3


def test_standings_after_complete_4er_tournament(session: Session) -> None:
    """Play a full 4'er Spiegel where team 1 always wins 10-0.

    Team 1 plays 3 games → 6 pts, 30 SP for, 0 against → diff +30.
    Other teams each get 1 win against another lower team to keep things
    deterministic-but-not-trivial.
    """
    t = create_normal_tournament(session, name="Full 4er", teams=_make_teams(4))
    games = list(session.exec(__import__("sqlmodel").select(Game).where(Game.tournament_id == t.id)))

    teams = sorted(
        session.exec(
            __import__("sqlmodel").select(Team).where(Team.tournament_id == t.id)
        ),
        key=lambda x: x.position,
    )
    team_by_pos = {t.position: t for t in teams}

    # Play every game: team 1 wins everything, otherwise lower-numbered team wins.
    for g in games:
        a = next(t for t in teams if t.id == g.team_a_id)
        b = next(t for t in teams if t.id == g.team_b_id)
        winner = a if a.position < b.position else b
        for r in range(1, 7):
            set_round_score(
                session,
                game_id=g.id,
                round_idx=r,
                scoring_team_id=winner.id,
                stockpunkte=2 if r <= 5 else 0,  # 10-0
            )

    standings = compute_standings(session, t.id)
    # Team with position 1 should be on top.
    assert standings[0].team_name == "Team 1"
    assert standings[0].adjusted_points_won == 6
    assert standings[0].stockpunkte_diff == 30
