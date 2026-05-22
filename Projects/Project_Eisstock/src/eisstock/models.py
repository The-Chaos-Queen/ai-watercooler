"""SQLModel entities for the tournament app.

One database = one server instance. A Tournament owns its Teams, Games, and
RoundScores. Zielschießen tournaments share the Tournament/Team tables but
use ZielAttempt instead of Game/RoundScore.

NOTE: Do not add `from __future__ import annotations` here. SQLModel reads
annotations at class definition time to wire relationships; making them
strings breaks the SQLAlchemy mapper.
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class TournamentMode(StrEnum):
    NORMAL = "normal"
    ZIELSCHIESSEN = "ziel"


class TournamentStatus(StrEnum):
    SETUP = "setup"
    RUNNING = "running"
    FINISHED = "finished"


class Discipline(StrEnum):
    MASTEN = "masten"
    SCHIESSEN = "schiessen"
    HINTERE_MASTEN = "hintere_masten"
    KOMBINIEREN = "kombinieren"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tournament(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    mode: TournamentMode
    team_count: int  # 3-8 for normal; for Ziel = participant count
    durchgaenge: int = 1  # 1 or 2 for normal; 1-4 for Ziel
    rounds_per_game: int = 6  # configurable, mostly 6
    status: TournamentStatus = TournamentStatus.SETUP
    created_at: datetime = Field(default_factory=utcnow)

    teams: list["Team"] = Relationship(back_populates="tournament", cascade_delete=True)
    games: list["Game"] = Relationship(back_populates="tournament", cascade_delete=True)
    ziel_attempts: list["ZielAttempt"] = Relationship(
        back_populates="tournament", cascade_delete=True
    )


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tournament_id: int = Field(foreign_key="tournament.id", index=True)
    position: int  # 1..team_count, the Spiegel slot
    name: str
    # Live scoreboard colors are per-side (green=left, red=right) at render
    # time, not a team attribute. Keep team data minimal.
    nation: str = ""
    referee_deduction_points: int = 0  # subtracted from final game-points won
    referee_deduction_stockpunkte: int = 0  # subtracted from final Stockpunkte diff

    tournament: Tournament = Relationship(back_populates="teams")
    players: list["Player"] = Relationship(back_populates="team", cascade_delete=True)


class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    name: str
    order_idx: int = 0  # display order within the team

    team: Team = Relationship(back_populates="players")


class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tournament_id: int = Field(foreign_key="tournament.id", index=True)
    durchgang: int = 1
    runde: int  # 1..n_rounds (overall pass through the Spiegel)
    bahn: str  # "1", "2", "3", or "Zusatz"
    team_a_id: int = Field(foreign_key="team.id")
    team_b_id: int = Field(foreign_key="team.id")
    anschuss_team_id: int = Field(foreign_key="team.id")

    tournament: Tournament = Relationship(back_populates="games")
    round_scores: list["RoundScore"] = Relationship(
        back_populates="game", cascade_delete=True
    )


class RoundScore(SQLModel, table=True):
    """One round within a single game.

    Most rounds have exactly one scoring team with stockpunkte > 0, but we
    store one row per (game, round, team) so that:
      - per-round history can be rendered directly (image2/3 style "1-0-1-1-0")
      - extensions (overtime rounds) and edit history flow naturally
    Where a team didn't score in a round, stockpunkte is 0.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id", index=True)
    round_idx: int  # 1..rounds_per_game
    team_id: int = Field(foreign_key="team.id")
    stockpunkte: int = 0

    game: Game = Relationship(back_populates="round_scores")


class ZielAttempt(SQLModel, table=True):
    """One throw in Zielschießen.

    Allowed scores per discipline:
      - MASTEN, HINTERE_MASTEN, KOMBINIEREN: 0, 2, 4, 6, 8, 10
      - SCHIESSEN: 0, 2, 5, 10
    Discipline max is 6 attempts × 10 = 60, round total max = 240.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    tournament_id: int = Field(foreign_key="tournament.id", index=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    durchgang: int  # 1..rounds_per_game (here used as Ziel "round"/pass count)
    discipline: Discipline
    attempt_idx: int  # 1..6
    score: int = 0

    tournament: Tournament = Relationship(back_populates="ziel_attempts")


# Convenience export
__all__ = [
    "Discipline",
    "Game",
    "Player",
    "RoundScore",
    "Team",
    "Tournament",
    "TournamentMode",
    "TournamentStatus",
    "ZielAttempt",
    "utcnow",
]
