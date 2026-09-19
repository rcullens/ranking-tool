"""Published sort order: power → SOS → head-to-head → capped point differential.

This is a *display* tie-break only. It does not feed back into The Toy,
SOS, or the panel blend. Cycles in H2H fall through to capped PD, then
``team_id`` so the table is always a total order.
"""

from __future__ import annotations

from functools import cmp_to_key
from typing import Callable, Iterable, Sequence

from sixman_rankings.models import EngineConfig, Game, TeamState


def head_to_head_cmp(
    team_a: str,
    team_b: str,
    games: Iterable[Game],
) -> int:
    """``-1`` if A leads the season series, ``+1`` if B leads, ``0`` otherwise."""

    a_wins = 0
    b_wins = 0
    for game in games:
        if not game.is_final:
            continue
        pair = {game.home_id, game.away_id}
        if pair != {team_a, team_b}:
            continue
        assert game.home_score is not None and game.away_score is not None
        if game.home_score == game.away_score:
            continue
        winner = game.home_id if game.home_score > game.away_score else game.away_id
        if winner == team_a:
            a_wins += 1
        elif winner == team_b:
            b_wins += 1
    if a_wins > b_wins:
        return -1
    if b_wins > a_wins:
        return 1
    return 0


def compare_states(
    a: TeamState,
    b: TeamState,
    games: Sequence[Game],
    config: EngineConfig,
) -> int:
    """Comparator for descending rank (better team first)."""

    if abs(a.power - b.power) > config.tie_power_eps:
        return -1 if a.power > b.power else 1
    if abs(a.sos - b.sos) > config.tie_sos_eps:
        return -1 if a.sos > b.sos else 1
    h2h = head_to_head_cmp(a.team_id, b.team_id, games)
    if h2h != 0:
        return h2h
    if abs(a.capped_pd - b.capped_pd) > 1e-9:
        return -1 if a.capped_pd > b.capped_pd else 1
    if a.team_id < b.team_id:
        return -1
    if a.team_id > b.team_id:
        return 1
    return 0


def rank_key(
    games: Sequence[Game],
    config: EngineConfig,
) -> Callable:
    """``sorted(states, key=rank_key(finals, config))``."""

    return cmp_to_key(lambda a, b: compare_states(a, b, games, config))
