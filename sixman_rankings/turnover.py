"""Roster-turnover volatility decay — the one-hit-wonder filter.

Small-school six-man programs can graduate an entire two-way lineup in
one May. A computer that trusts last November's rating will keep a
rebuilt roster in the top five until the losses pile up. This module
pulls a prior toward the league mean in proportion to senior-class
graduation and positional starting-spot turnover, reaching the specified
~35% strip at near-total replacement.
"""

from __future__ import annotations

from sixman_rankings.models import EngineConfig, RosterFactor


def combined_turnover(factor: RosterFactor) -> float:
    """Blend raw graduation with positional replacement.

    Positional turnover (QB / skill / line / DB spots that do not return)
    is weighted more heavily: a senior-heavy class that still returns the
    QB and the two-way studs is not a one-hit wonder.
    """

    g = min(1.0, max(0.0, factor.graduation_rate))
    p = min(1.0, max(0.0, factor.positional_turnover))
    return 0.40 * g + 0.60 * p


def turnover_decay(factor: RosterFactor, config: EngineConfig) -> float:
    """Fraction of ``(legacy - mean)`` to strip.

    * Combined rate ≤ ``turnover_floor`` (default 0.45): no strip. Ordinary
      senior-class replacement is already priced into week-to-week Elo.
    * Combined rate ≥ ``turnover_full`` (default 0.90): full ``turnover_strip``
      (default 0.35).
    * In between: a smoothstep ramp so "almost everyone left" and "everyone
      left" converge on the same 35% haircut.
    """

    t = combined_turnover(factor)
    floor = config.turnover_floor
    full = config.turnover_full
    if full <= floor:
        return config.turnover_strip if t >= full else 0.0
    if t <= floor:
        return 0.0
    x = min(1.0, (t - floor) / (full - floor))
    smooth = x * x * (3.0 - 2.0 * x)
    return config.turnover_strip * smooth


def apply_turnover_decay(
    legacy_rating: float,
    league_mean: float,
    decay: float,
) -> float:
    """Regress ``legacy_rating`` toward ``league_mean`` by ``decay``.

    ``decay = 0.35`` and a 1800 prior at a 1500 mean become
    ``1500 + 300 * 0.65 = 1695``. The team keeps most of its identity but
    cannot open the year as an automatic top-two side after a total wipeout.
    """

    decay = min(1.0, max(0.0, decay))
    return league_mean + (legacy_rating - league_mean) * (1.0 - decay)
