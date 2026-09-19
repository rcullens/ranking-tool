"""Modified point differential, hard-capped at the UIL six-man mercy rule."""

from __future__ import annotations

from sixman_rankings.constants import MERCY_CAP
from sixman_rankings.models import Game


def cap_margin(margin: float, mercy_cap: int = MERCY_CAP) -> float:
    """Clamp a signed point differential to ``[-mercy_cap, mercy_cap]``.

    A 72-12 (raw +60) and a 52-7 (raw +45) therefore carry identical
    dominance weight. Running up the score past the mercy rule cannot
    inflate a ranking.
    """

    if mercy_cap < 0:
        raise ValueError("mercy_cap must be non-negative")
    if margin > mercy_cap:
        return float(mercy_cap)
    if margin < -mercy_cap:
        return float(-mercy_cap)
    return float(margin)


def signed_capped_margin(
    scored: float,
    allowed: float,
    mercy_cap: int = MERCY_CAP,
) -> float:
    """Capped differential from one team's point of view."""

    return cap_margin(scored - allowed, mercy_cap=mercy_cap)


def game_margins(game: Game, mercy_cap: int = MERCY_CAP) -> tuple[float, float, float, float]:
    """Return ``(home_raw, away_raw, home_capped, away_capped)``.

    Raises ``ValueError`` when the game is not final.
    """

    if not game.is_final:
        raise ValueError(f"game {game.game_id} is not final")
    assert game.home_score is not None and game.away_score is not None
    home_raw = float(game.home_score - game.away_score)
    away_raw = -home_raw
    return home_raw, away_raw, cap_margin(home_raw, mercy_cap), cap_margin(away_raw, mercy_cap)


def is_mercy_win(margin: float, mercy_cap: int = MERCY_CAP) -> bool:
    """True when the winner reached the UIL 45-point threshold."""

    return abs(margin) >= mercy_cap
