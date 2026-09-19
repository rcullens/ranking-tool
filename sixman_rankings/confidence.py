"""Rating confidence / uncertainty bands.

Six-man samples are tiny. A 2–0 after Week 2 is a rumor; a 8–1 after
Week 9 on a connected slate is a measurement. The band is a Glicko-style
``σ = σ0 / sqrt(n + n0)``, then widened when geographic density is low
so an isolated bubble cannot look "sure" just because it played itself.
"""

from __future__ import annotations

import math

from sixman_rankings.models import EngineConfig


def rating_sigma(
    games_played: int,
    density: float,
    config: EngineConfig,
) -> float:
    """One-sigma uncertainty in rating points."""

    n = max(0, games_played) + config.confidence_prior_games
    sigma = config.confidence_base_sigma / math.sqrt(max(n, 1e-9))
    density = min(1.0, max(0.0, density))
    sigma *= 1.0 + (1.0 - density) * config.confidence_density_penalty
    return sigma


def confidence_score(sigma: float, config: EngineConfig) -> float:
    """``1`` is certain, ``0`` is a wide-open preseason prior."""

    if config.confidence_base_sigma <= 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - sigma / config.confidence_base_sigma))


def is_low_confidence(
    games_played: int,
    confidence: float,
    config: EngineConfig,
) -> bool:
    return games_played < config.confidence_min_games or confidence < config.confidence_flag


def assess(
    games_played: int,
    density: float,
    config: EngineConfig,
) -> tuple[float, float, bool]:
    """Return ``(confidence, sigma, low_confidence)``."""

    sigma = rating_sigma(games_played, density, config)
    conf = confidence_score(sigma, config)
    return conf, sigma, is_low_confidence(games_played, conf, config)
