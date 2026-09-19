"""Recency weights for week-to-week Elo and SOS.

Early August results still count — a 5-week half-life keeps them on the
board — but a mid-October tape should move The Toy and the schedule terms
more than a Week 1 mercy rule against a side that no longer exists.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Optional

from sixman_rankings.models import Game


def recency_weight(
    game_week: int,
    as_of_week: int,
    half_life: float,
) -> float:
    """``0.5 ** (age / half_life)``. ``half_life <= 0`` disables decay."""

    if half_life <= 0:
        return 1.0
    age = max(0, int(as_of_week) - int(game_week))
    return 0.5 ** (age / half_life)


def weights_by_game(
    games: Iterable[Game],
    as_of_week: int,
    half_life: float,
) -> dict[str, float]:
    return {
        game.game_id: recency_weight(game.week, as_of_week, half_life)
        for game in games
    }


def resolve_as_of_week(
    games: Iterable[Game],
    as_of_week: Optional[int],
) -> int:
    if as_of_week is not None:
        return as_of_week
    weeks = [g.week for g in games]
    return max(weeks) if weeks else 0


def lookup_weight(game: Game, weights: Optional[Mapping[str, float]]) -> float:
    if not weights:
        return 1.0
    return float(weights.get(game.game_id, 1.0))
