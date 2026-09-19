"""Dynamic margin-capped Elo core — "The Toy" engine.

Rating points are exchanged from the *expected scoring spread*, not from a
binary win/loss. Cover size scales the update logarithmically up to the
45-point mercy cap. Favorite/underdog residuals use an asymmetric K so
upsets move the market more than expected covers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sixman_rankings.margin import cap_margin
from sixman_rankings.models import EngineConfig, Game


def expected_win_probability(rating_a: float, rating_b: float, scale: float) -> float:
    """Standard Elo logistic. ``rating_a`` is the side whose probability we want."""

    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / scale))


def expected_spread(
    rating_for: float,
    rating_against: float,
    config: EngineConfig,
    hfa: float = 0.0,
) -> float:
    """Map an Elo gap onto a mercy-capped expected point differential.

    Win probability ``E`` in ``[0, 1]`` is stretched onto ``[-cap, +cap]``
    via ``cap * (2E - 1)``. Equal ratings and no HFA therefore produce a
    0-point expected spread; a near-certain favorite is expected to 45 the
    opponent, not to win 80-0.
    """

    e = expected_win_probability(
        rating_for + hfa, rating_against, config.spread_scale
    )
    return config.mercy_cap * (2.0 * e - 1.0)


def cover_multiplier(residual: float, config: EngineConfig) -> float:
    """Logarithmic cover multiplier, saturated at the mercy cap.

    ``m(0) = 1``. ``m(±45) = 1 + λ``. Intermediate residuals follow
    ``log(1 + |r|) / log(1 + cap)``, so the first handful of points above
    the number are worth more than the last handful — dominant execution
    against the spread is rewarded, raw 70-point cosmetics are not.
    """

    magnitude = min(abs(residual), float(config.mercy_cap))
    if config.mercy_cap <= 0:
        return 1.0
    # log(1+0) = 0, so a push against the expected spread is a 1.0 multiplier.
    scale = math.log(1.0 + config.mercy_cap)
    return 1.0 + config.cover_lambda * (math.log(1.0 + magnitude) / scale)


def is_upset_residual(expected: float, actual: float) -> bool:
    """True when the favorite failed to cover or the underdog covered."""

    # Positive expected means this side was favored to win by that many.
    if expected > 0 and actual < expected:
        return True
    if expected < 0 and actual > expected:
        return True
    return False


@dataclass(frozen=True)
class EloUpdate:
    """Zero-sum rating exchange produced by one final."""

    home_delta: float
    away_delta: float
    expected_home_spread: float
    actual_home_spread: float
    residual: float
    multiplier: float
    k_effective: float


def toy_update(
    home_elo: float,
    away_elo: float,
    home_score: float,
    away_score: float,
    config: EngineConfig,
    *,
    neutral: bool = False,
) -> EloUpdate:
    """Compute the Toy-engine exchange for one game without mutating ratings."""

    hfa = 0.0 if neutral else config.home_field
    expected = expected_spread(home_elo, away_elo, config, hfa=hfa)
    actual = cap_margin(home_score - away_score, config.mercy_cap)
    residual = actual - expected
    multiplier = cover_multiplier(residual, config)

    k = config.elo_k
    if is_upset_residual(expected, actual):
        k *= 1.0 + config.upset_boost

    # Residual / cap maps a full mercy-rule surprise onto a "game" of size 1,
    # analogous to (S - E) in binary Elo.
    delta = k * multiplier * (residual / config.mercy_cap)
    return EloUpdate(
        home_delta=delta,
        away_delta=-delta,
        expected_home_spread=expected,
        actual_home_spread=actual,
        residual=residual,
        multiplier=multiplier,
        k_effective=k,
    )


def apply_game_update(
    home_elo: float,
    away_elo: float,
    game: Game,
    config: EngineConfig,
) -> tuple[float, float, EloUpdate]:
    """Return updated ``(home_elo, away_elo)`` plus the diagnostic update."""

    if not game.is_final:
        raise ValueError(f"game {game.game_id} is not final")
    assert game.home_score is not None and game.away_score is not None
    update = toy_update(
        home_elo,
        away_elo,
        game.home_score,
        game.away_score,
        config,
        neutral=game.neutral,
    )
    return home_elo + update.home_delta, away_elo + update.away_delta, update
