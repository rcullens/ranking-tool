"""Merge incoming finals onto the season schedule without duplicating games."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from sixman_rankings.models import Game


def _key(game: Game) -> tuple[str, str, int]:
    pair = tuple(sorted((game.home_id, game.away_id)))
    return (pair[0], pair[1], game.week)


def merge_finals(existing: list[Game], incoming: Iterable[Game]) -> tuple[list[Game], int]:
    """Apply scores from ``incoming`` onto ``existing``. Returns ``(games, updates)``."""

    by_id = {g.game_id: i for i, g in enumerate(existing)}
    by_key = {_key(g): i for i, g in enumerate(existing)}
    out = list(existing)
    updates = 0
    extras: list[Game] = []

    for game in incoming:
        if not game.is_final:
            continue
        idx = by_id.get(game.game_id)
        if idx is None:
            idx = by_key.get(_key(game))
        if idx is None:
            extras.append(game)
            updates += 1
            continue
        current = out[idx]
        if (
            current.home_score == game.home_score
            and current.away_score == game.away_score
        ):
            continue
        # Incoming listing may swap home/away vs our schedule; keep our site
        # designation and attach scores to the matching clubs.
        if current.home_id == game.home_id and current.away_id == game.away_id:
            out[idx] = replace(current, home_score=game.home_score, away_score=game.away_score)
        elif current.home_id == game.away_id and current.away_id == game.home_id:
            out[idx] = replace(current, home_score=game.away_score, away_score=game.home_score)
        else:
            out[idx] = replace(current, home_score=game.home_score, away_score=game.away_score)
        updates += 1

    if extras:
        out.extend(extras)
    return out, updates


def hide_scores_after(games: list[Game], through_week: int) -> tuple[list[Game], dict[str, tuple[int, int]]]:
    """Strip finals after ``through_week`` so the live window can re-release them."""

    held: dict[str, tuple[int, int]] = {}
    out: list[Game] = []
    for game in games:
        if game.week > through_week and game.is_final:
            assert game.home_score is not None and game.away_score is not None
            held[game.game_id] = (int(game.home_score), int(game.away_score))
            out.append(replace(game, home_score=None, away_score=None))
        else:
            out.append(game)
    return out, held
