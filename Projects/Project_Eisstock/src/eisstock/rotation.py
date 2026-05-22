"""Tournament rotation generation ("Spiegel") for 3-8 team Eisstock tournaments.

Uses the standard circle method for round-robin scheduling: team 1 is held fixed
at position 0, all other teams rotate one slot per round. Each round, opposite
positions on the circle pair up. For odd team counts a "bye" slot is added —
the team paired with the bye sits the round out (Spielfrei / break).

Bahn assignment maps the highest-priority pair (the one containing team 1) to
Bahn 1, then sequentially. For 8 teams there's a 4th pair per round labeled
"Zusatzspiel" (matches image6 in the requirements doc).

Doppelrunde (5'er, 4'er, etc.): the second pass through the rotation mirrors
the first with the Anschuss swapped — both passes are produced when
`durchgaenge=2`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BahnLabel = Literal["1", "2", "3", "Zusatz"]


@dataclass(frozen=True)
class Pairing:
    """One game in the schedule.

    `bahn` is the human label ('1', '2', '3', or 'Zusatz' for the 4th game in
    8'er Spiegel). `anschuss` is the team that starts the game (the very
    first throw of round 1).
    """

    runde: int
    bahn: BahnLabel
    team_a: int
    team_b: int
    anschuss: int
    durchgang: int = 1


@dataclass(frozen=True)
class RoundPlan:
    runde: int
    games: tuple[Pairing, ...]
    bye: int | None  # team sitting out this round, or None


def _bahn_label_for(index: int, team_count: int) -> BahnLabel:
    """Bahn label for the n-th pair in a round, given the format."""
    if team_count == 8 and index == 3:
        return "Zusatz"
    return ("1", "2", "3", "Zusatz")[index]  # type: ignore[return-value]


def _circle_pairings(team_count: int) -> list[RoundPlan]:
    """Generate the single-pass round-robin schedule via circle method.

    Pairs are kept in circle-position order: the pair at the innermost
    opposing slots (containing team 1 in even-team formats) goes to Bahn 1,
    the next-outer pair to Bahn 2, and so on. For 8 teams the 4th pair
    is the "Zusatzspiel". This matches image6 of the requirements doc.

    The team paired with the dummy bye slot in odd-team formats is recorded
    as `bye` on the RoundPlan and skipped in the games list.

    Anschuss defaults to team_a; for 8 teams it's overridden later from the
    canonical table since the official rule isn't trivially derivable.
    """
    if not 3 <= team_count <= 8:
        raise ValueError(f"team_count must be 3..8, got {team_count}")

    if team_count % 2 == 1:
        slots = list(range(1, team_count + 1)) + [0]
    else:
        slots = list(range(1, team_count + 1))

    n_slots = len(slots)
    n_rounds = n_slots - 1
    rounds: list[RoundPlan] = []

    positions = list(slots)
    for runde in range(1, n_rounds + 1):
        ordered_pairs: list[tuple[int, int] | None] = []
        bye: int | None = None
        for i in range(n_slots // 2):
            a, b = positions[i], positions[n_slots - 1 - i]
            if a == 0:
                bye = b
                ordered_pairs.append(None)
            elif b == 0:
                bye = a
                ordered_pairs.append(None)
            else:
                ordered_pairs.append((a, b))

        # Compact, preserving order, and assign Bahnen in that order.
        live_pairs = [p for p in ordered_pairs if p is not None]
        games = tuple(
            Pairing(
                runde=runde,
                bahn=_bahn_label_for(idx, team_count),
                team_a=p[0],
                team_b=p[1],
                anschuss=p[0],
            )
            for idx, p in enumerate(live_pairs)
        )
        rounds.append(RoundPlan(runde=runde, games=games, bye=bye))

        # Standard circle-method rotation: keep pos 0 fixed; the team at the
        # last position cycles to position 1, all others shift down by one.
        positions = [positions[0]] + [positions[-1]] + positions[1:-1]

    if team_count == 8:
        rounds = _apply_eight_team_anschuss(rounds)

    return rounds


def _apply_eight_team_anschuss(rounds: list[RoundPlan]) -> list[RoundPlan]:
    """Override Anschuss for 8'er Spiegel using the canonical image6 table.

    The schedule rule isn't trivially derivable, so we look up the Anschuss
    team per game from EIGHT_TEAM_REFERENCE. Pairs already match by virtue
    of the circle method — we just need to set Anschuss correctly.
    """
    new_rounds: list[RoundPlan] = []
    for r_idx, plan in enumerate(rounds):
        ref_row = EIGHT_TEAM_REFERENCE[r_idx]
        new_games: list[Pairing] = []
        for g_idx, game in enumerate(plan.games):
            _, _, ref_anschuss, _ = ref_row[g_idx]
            new_games.append(
                Pairing(
                    runde=game.runde,
                    bahn=game.bahn,
                    team_a=game.team_a,
                    team_b=game.team_b,
                    anschuss=ref_anschuss,
                    durchgang=game.durchgang,
                )
            )
        new_rounds.append(RoundPlan(runde=plan.runde, games=tuple(new_games), bye=plan.bye))
    return new_rounds


def generate_spiegel(team_count: int, *, durchgaenge: int = 1) -> list[RoundPlan]:
    """Generate the full rotation for a team-count format.

    Args:
        team_count: 3, 4, 5, 6, 7, or 8.
        durchgaenge: 1 = single pass, 2 = Hin- und Rückrunde (Anschuss
            swapped on second pass).

    Returns a flat list of RoundPlan in order. With `durchgaenge=2` the
    second pass continues the round numbering (e.g. 3'er Spiegel becomes
    runde 1..6).
    """
    if durchgaenge not in (1, 2):
        raise ValueError(f"durchgaenge must be 1 or 2, got {durchgaenge}")

    first_pass = _circle_pairings(team_count)
    if durchgaenge == 1:
        return first_pass

    n_first = len(first_pass)
    second_pass: list[RoundPlan] = []
    for plan in first_pass:
        new_runde = plan.runde + n_first
        new_games = tuple(
            Pairing(
                runde=new_runde,
                bahn=g.bahn,
                team_a=g.team_a,
                team_b=g.team_b,
                anschuss=g.team_b if g.anschuss == g.team_a else g.team_a,
                durchgang=2,
            )
            for g in plan.games
        )
        second_pass.append(RoundPlan(runde=new_runde, games=new_games, bye=plan.bye))

    return first_pass + second_pass


# Canonical 8'er Spiegel reference from image6 of the requirements doc.
# Used by tests to verify our circle method matches the official table.
EIGHT_TEAM_REFERENCE: tuple[tuple[tuple[int, int, int, BahnLabel], ...], ...] = (
    # (team_a, team_b, anschuss, bahn)
    ((1, 8, 1, "1"), (2, 7, 2, "2"), (3, 6, 3, "3"), (4, 5, 4, "Zusatz")),
    ((1, 7, 7, "1"), (8, 6, 8, "2"), (2, 5, 5, "3"), (3, 4, 3, "Zusatz")),
    ((1, 6, 1, "1"), (7, 5, 7, "2"), (8, 4, 8, "3"), (2, 3, 2, "Zusatz")),
    ((1, 5, 5, "1"), (6, 4, 6, "2"), (7, 3, 3, "3"), (8, 2, 8, "Zusatz")),
    ((1, 4, 1, "1"), (5, 3, 5, "2"), (6, 2, 6, "3"), (7, 8, 7, "Zusatz")),
    ((1, 3, 3, "1"), (4, 2, 4, "2"), (5, 8, 8, "3"), (6, 7, 6, "Zusatz")),
    ((1, 2, 1, "1"), (3, 8, 3, "2"), (4, 7, 4, "3"), (5, 6, 5, "Zusatz")),
)
