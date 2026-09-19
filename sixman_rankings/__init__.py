"""Texas UIL six-man football ranking toolkit."""

from sixman_rankings.models import (
    EngineConfig,
    Game,
    PanelAdjustment,
    PriorRating,
    RankedTeam,
    RosterFactor,
    Team,
)
from sixman_rankings.pipeline import RankingEngine, rank_season, weekly_snapshots
from sixman_rankings.whatif import WhatIfReport, simulate_what_if

__version__ = "0.3.0"

__all__ = [
    "EngineConfig",
    "Game",
    "PanelAdjustment",
    "PriorRating",
    "RankedTeam",
    "RankingEngine",
    "RosterFactor",
    "Team",
    "WhatIfReport",
    "rank_season",
    "simulate_what_if",
    "weekly_snapshots",
    "__version__",
]
