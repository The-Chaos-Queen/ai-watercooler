"""Tournament lifecycle services: create, advance, score, summarize.

These functions wrap the DB layer and the pure rotation/scoring modules so
the HTTP routes can stay thin.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlmodel import Session, select

from eisstock.models import (
    Discipline,
    Game,
    Player,
    RoundScore,
    Team,
    Tournament,
    TournamentMode,
    TournamentStatus,
    ZielAttempt,
)
from eisstock.rotation import generate_spiegel
from eisstock.scoring import (
    GameResult,
    TeamStanding,
    fold_results,
    rank_standings,
)


@dataclass
class TeamSpec:
    name: str
    nation: str = ""
    players: tuple[str, ...] = ()


def create_normal_tournament(
    session: Session,
    *,
    name: str,
    teams: list[TeamSpec],
    durchgaenge: int = 1,
    rounds_per_game: int = 6,
) -> Tournament:
    """Create a normal-game tournament and materialize all its games.

    Team count is inferred from len(teams). Game rows are created in the
    DB up-front using the rotation engine; scoring happens later via
    record_round_score.
    """
    team_count = len(teams)
    if not 3 <= team_count <= 8:
        raise ValueError(f"team_count must be 3..8, got {team_count}")

    tournament = Tournament(
        name=name,
        mode=TournamentMode.NORMAL,
        team_count=team_count,
        durchgaenge=durchgaenge,
        rounds_per_game=rounds_per_game,
        status=TournamentStatus.RUNNING,
    )
    session.add(tournament)
    session.flush()

    team_rows: dict[int, Team] = {}
    for pos, spec in enumerate(teams, start=1):
        row = Team(
            tournament_id=tournament.id,  # type: ignore[arg-type]
            position=pos,
            name=spec.name,
            nation=spec.nation,
        )
        session.add(row)
        session.flush()
        team_rows[pos] = row
        for idx, pname in enumerate(spec.players):
            session.add(Player(team_id=row.id, name=pname, order_idx=idx))  # type: ignore[arg-type]

    for round_plan in generate_spiegel(team_count, durchgaenge=durchgaenge):
        for pairing in round_plan.games:
            session.add(
                Game(
                    tournament_id=tournament.id,  # type: ignore[arg-type]
                    durchgang=pairing.durchgang,
                    runde=pairing.runde,
                    bahn=pairing.bahn,
                    team_a_id=team_rows[pairing.team_a].id,  # type: ignore[arg-type]
                    team_b_id=team_rows[pairing.team_b].id,  # type: ignore[arg-type]
                    anschuss_team_id=team_rows[pairing.anschuss].id,  # type: ignore[arg-type]
                )
            )

    session.commit()
    session.refresh(tournament)
    return tournament


def list_tournaments(session: Session) -> list[Tournament]:
    return list(session.exec(select(Tournament).order_by(Tournament.created_at.desc())))  # type: ignore[arg-type, attr-defined]


def games_for_bahn(
    session: Session, tournament_id: int, bahn: str
) -> list[Game]:
    """All games on a given Bahn across the tournament, in round order."""
    stmt = (
        select(Game)
        .where(Game.tournament_id == tournament_id)
        .where(Game.bahn == bahn)
        .order_by(Game.runde)  # type: ignore[arg-type]
    )
    return list(session.exec(stmt))


def set_round_score(
    session: Session,
    *,
    game_id: int,
    round_idx: int,
    scoring_team_id: int,
    stockpunkte: int,
) -> None:
    """Record the round's outcome: which team scored and by how many.

    Stores one RoundScore row per team for the round so that per-round
    history can be rendered as "1-0-1-1-0" / "0-2-0-0-3" directly.
    The non-scoring team gets a 0 row. Re-calling with the same
    (game, round) overwrites both rows — that's the "edit a previous
    round" workflow from the requirements doc.
    """
    game = session.get(Game, game_id)
    if game is None:
        raise ValueError(f"Game {game_id} not found")
    if scoring_team_id not in (game.team_a_id, game.team_b_id):
        raise ValueError(
            f"team {scoring_team_id} is not part of game {game_id}"
        )
    if stockpunkte < 0:
        raise ValueError("stockpunkte must be non-negative")

    opp_id = game.team_b_id if scoring_team_id == game.team_a_id else game.team_a_id

    existing = list(
        session.exec(
            select(RoundScore)
            .where(RoundScore.game_id == game_id)
            .where(RoundScore.round_idx == round_idx)
        )
    )
    by_team = {row.team_id: row for row in existing}

    scorer_row = by_team.get(scoring_team_id) or RoundScore(
        game_id=game_id, round_idx=round_idx, team_id=scoring_team_id
    )
    scorer_row.stockpunkte = stockpunkte
    session.add(scorer_row)

    opp_row = by_team.get(opp_id) or RoundScore(
        game_id=game_id, round_idx=round_idx, team_id=opp_id
    )
    opp_row.stockpunkte = 0
    session.add(opp_row)

    session.commit()


@dataclass
class GameSummary:
    """Live view of a single game: per-round history + running totals."""

    game: Game
    team_a: Team
    team_b: Team
    round_count: int
    rounds_a: list[int]  # length == round_count; 0 where team_a didn't score
    rounds_b: list[int]
    total_a: int
    total_b: int

    @property
    def current_round(self) -> int:
        """1-based round number currently being entered (next empty round)."""
        for idx in range(self.round_count):
            if self.rounds_a[idx] == 0 and self.rounds_b[idx] == 0:
                return idx + 1
        return self.round_count


def summarize_game(session: Session, game_id: int) -> GameSummary:
    game = session.get(Game, game_id)
    if game is None:
        raise ValueError(f"Game {game_id} not found")
    team_a = session.get(Team, game.team_a_id)
    team_b = session.get(Team, game.team_b_id)
    assert team_a is not None and team_b is not None

    tournament = session.get(Tournament, game.tournament_id)
    assert tournament is not None
    round_count = tournament.rounds_per_game

    scores = list(
        session.exec(
            select(RoundScore)
            .where(RoundScore.game_id == game_id)
            .order_by(RoundScore.round_idx)  # type: ignore[arg-type]
        )
    )
    rounds_a = [0] * round_count
    rounds_b = [0] * round_count
    for sc in scores:
        if 1 <= sc.round_idx <= round_count:
            if sc.team_id == team_a.id:
                rounds_a[sc.round_idx - 1] = sc.stockpunkte
            elif sc.team_id == team_b.id:
                rounds_b[sc.round_idx - 1] = sc.stockpunkte

    return GameSummary(
        game=game,
        team_a=team_a,
        team_b=team_b,
        round_count=round_count,
        rounds_a=rounds_a,
        rounds_b=rounds_b,
        total_a=sum(rounds_a),
        total_b=sum(rounds_b),
    )


def compute_standings(session: Session, tournament_id: int) -> list[TeamStanding]:
    """Compute current standings across all games in a tournament."""
    tournament = session.get(Tournament, tournament_id)
    if tournament is None:
        raise ValueError(f"Tournament {tournament_id} not found")

    teams = list(
        session.exec(
            select(Team)
            .where(Team.tournament_id == tournament_id)
            .order_by(Team.position)  # type: ignore[arg-type]
        )
    )
    games = list(
        session.exec(select(Game).where(Game.tournament_id == tournament_id))
    )
    all_scores = list(
        session.exec(
            select(RoundScore).where(
                RoundScore.game_id.in_([g.id for g in games])  # type: ignore[union-attr]
            )
        )
    )

    # Group scores by game.
    by_game: dict[int, list[RoundScore]] = defaultdict(list)
    for sc in all_scores:
        by_game[sc.game_id].append(sc)

    # Build GameResult per team per game.
    per_team_results: dict[int, list[GameResult]] = defaultdict(list)
    for game in games:
        scores = by_game.get(game.id, [])  # type: ignore[arg-type]
        if not scores:
            continue  # game not played yet → don't count it
        sp_a = sum(s.stockpunkte for s in scores if s.team_id == game.team_a_id)
        sp_b = sum(s.stockpunkte for s in scores if s.team_id == game.team_b_id)
        per_team_results[game.team_a_id].append(
            GameResult(own_stockpunkte=sp_a, opp_stockpunkte=sp_b)
        )
        per_team_results[game.team_b_id].append(
            GameResult(own_stockpunkte=sp_b, opp_stockpunkte=sp_a)
        )

    players_by_team: dict[int, list[str]] = defaultdict(list)
    for player in session.exec(
        select(Player)
        .where(Player.team_id.in_([t.id for t in teams]))  # type: ignore[union-attr]
        .order_by(Player.order_idx)  # type: ignore[arg-type]
    ):
        players_by_team[player.team_id].append(player.name)

    standings: list[TeamStanding] = []
    for team in teams:
        results = per_team_results.get(team.id, [])  # type: ignore[arg-type]
        gpw, gpa, spf, spa = fold_results(results)
        standings.append(
            TeamStanding(
                team_id=team.id,  # type: ignore[arg-type]
                team_name=team.name,
                nation=team.nation,
                games_played=len(results),
                game_points_won=gpw,
                game_points_against=gpa,
                stockpunkte_for=spf,
                stockpunkte_against=spa,
                deduction_points=team.referee_deduction_points,
                deduction_stockpunkte=team.referee_deduction_stockpunkte,
                players=players_by_team.get(team.id, []),  # type: ignore[arg-type]
            )
        )

    return rank_standings(standings)


# --- Zielschießen ---

def record_ziel_attempt(
    session: Session,
    *,
    tournament_id: int,
    team_id: int,
    durchgang: int,
    discipline: Discipline,
    attempt_idx: int,
    score: int,
) -> None:
    """Record or update one attempt. Re-recording overwrites (edit support)."""
    existing = list(
        session.exec(
            select(ZielAttempt)
            .where(ZielAttempt.tournament_id == tournament_id)
            .where(ZielAttempt.team_id == team_id)
            .where(ZielAttempt.durchgang == durchgang)
            .where(ZielAttempt.discipline == discipline)
            .where(ZielAttempt.attempt_idx == attempt_idx)
        )
    )
    row = existing[0] if existing else ZielAttempt(
        tournament_id=tournament_id,
        team_id=team_id,
        durchgang=durchgang,
        discipline=discipline,
        attempt_idx=attempt_idx,
    )
    row.score = score
    session.add(row)
    session.commit()
