"""Hybrid human-panel blend (Dave Campbell's Texas Football style).

Preseason magazines and coaches' polls know about the transferred QB and
the graduating two-way star before the computer has a single snap. This
module mixes an optional panel rating into the computer power score, then
lets that mix decay as Friday nights accumulate so the model can take over.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Optional

from sixman_rankings.models import EngineConfig, PanelAdjustment


def panel_weight(
    games_played: int,
    adjustment: Optional[PanelAdjustment],
    config: EngineConfig,
) -> float:
    """Effective panel mix after exponential decay in games played.

    At 0 games the mix is ``config.panel_mix * adjustment.weight``.
    After roughly ``panel_half_life`` games it has halved. Known roster
    depletions can still be expressed by pairing this with
    :mod:`sixman_rankings.turnover` rather than leaving a stale panel
    rating on a gutted roster all year.
    """

    if adjustment is None or games_played < 0:
        return 0.0
    team_scale = min(1.0, max(0.0, adjustment.weight))
    base = config.panel_mix * team_scale
    # half-life τ: w = base * 0.5 ** (games / τ)
    if config.panel_half_life <= 0:
        return 0.0 if games_played else base
    return base * (0.5 ** (games_played / config.panel_half_life))


def blend_panel(
    computer_rating: float,
    games_played: int,
    adjustment: Optional[PanelAdjustment],
    config: EngineConfig,
) -> tuple[float, float]:
    """Return ``(blended_rating, weight_used)``."""

    w = panel_weight(games_played, adjustment, config)
    if adjustment is None or w <= 0:
        return computer_rating, 0.0
    blended = (1.0 - w) * computer_rating + w * adjustment.panel_rating
    return blended, w


def panel_index(
    adjustments: Mapping[str, PanelAdjustment] | Iterable[PanelAdjustment],
) -> dict[str, PanelAdjustment]:
    if isinstance(adjustments, Mapping):
        return dict(adjustments)
    return {adj.team_id: adj for adj in adjustments}
