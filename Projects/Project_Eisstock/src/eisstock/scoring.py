"""Pure scoring math: per-game results and tournament standings.

Kept side-effect free so it can be unit-tested without a database. The DB
layer hands it lists of round scores, and it returns standings.

Game-point rule (Eisstock convention):
  Win  = 2 game points to winner, 0 to loser
  Draw = 1 game point each
The display notation "9:3" means (own game points : opponent game points).

Tiebreaker = Stockpunkte differenz (sum scored across all games minus sum
conceded), with referee deductions applied last.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GameResult:
    """Result of one game for one team perspective.

    Each side's stockpunkte sum across the rounds of that game determines
    win/draw/loss. game_points_won is 2/1/0 from this side's perspective;
    game_points_against is what the opponent scored in game-points.
    """

    own_stockpunkte: int
    opp_stockpunkte: int

    @property
    def game_points_won(self) -> int:
        if self.own_stockpunkte > self.opp_stockpunkte:
            return 2
        if self.own_stockpunkte == self.opp_stockpunkte:
            return 1
        return 0

    @property
    def game_points_against(self) -> int:
        if self.own_stockpunkte > self.opp_stockpunkte:
            return 0
        if self.own_stockpunkte == self.opp_stockpunkte:
            return 1
        return 2


@dataclass
class TeamStanding:
    team_id: int
    team_name: str
    nation: str = ""
    games_played: int = 0
    game_points_won: int = 0
    game_points_against: int = 0
    stockpunkte_for: int = 0
    stockpunkte_against: int = 0
    deduction_points: int = 0
    deduction_stockpunkte: int = 0
    players: list[str] = field(default_factory=list)

    @property
    def stockpunkte_diff(self) -> int:
        return (self.stockpunkte_for - self.stockpunkte_against) - self.deduction_stockpunkte

    @property
    def adjusted_points_won(self) -> int:
        return self.game_points_won - self.deduction_points


def fold_results(results: list[GameResult]) -> tuple[int, int, int, int]:
    """Sum game-points and Stockpunkte across many games for one team.

    Returns (game_points_won, game_points_against, sp_for, sp_against).
    """
    gpw = sum(r.game_points_won for r in results)
    gpa = sum(r.game_points_against for r in results)
    spf = sum(r.own_stockpunkte for r in results)
    spa = sum(r.opp_stockpunkte for r in results)
    return gpw, gpa, spf, spa


def rank_standings(standings: list[TeamStanding]) -> list[TeamStanding]:
    """Sort by adjusted points won desc, then Stockpunkte diff desc,
    then Stockpunkte-for desc as final tiebreaker."""
    return sorted(
        standings,
        key=lambda s: (-s.adjusted_points_won, -s.stockpunkte_diff, -s.stockpunkte_for),
    )


# --- Zielschießen ---

VALID_RING_SCORES: frozenset[int] = frozenset({0, 2, 4, 6, 8, 10})
VALID_SCHIESSEN_SCORES: frozenset[int] = frozenset({0, 2, 5, 10})


def valid_scores_for(discipline: str) -> frozenset[int]:
    """Allowed per-attempt scores for a Zielschießen discipline."""
    if discipline == "schiessen":
        return VALID_SCHIESSEN_SCORES
    return VALID_RING_SCORES


MAX_DISCIPLINE_SCORE = 60  # 6 attempts × 10
MAX_ROUND_SCORE = 240  # 4 disciplines × 60
