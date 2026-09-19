"""Core data structures for teams, games, adjustments, and ratings."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

from sixman_rankings.constants import (
    COVER_LAMBDA,
    DEFAULT_PANEL_MIX,
    DENSITY_ELO_FLOOR,
    DENSITY_FLOOR,
    DENSITY_MIN_SCHEDULED,
    ELO_BLEND,
    ELO_K,
    ELO_SCALE,
    HOME_FIELD_ADVANTAGE,
    INITIAL_RATING,
    MERCY_CAP,
    PANEL_HALF_LIFE_GAMES,
    RECENCY_HALF_LIFE_WEEKS,
    CONFIDENCE_BASE_SIGMA,
    CONFIDENCE_DENSITY_PENALTY,
    CONFIDENCE_FLAG,
    CONFIDENCE_MIN_GAMES,
    CONFIDENCE_PRIOR_GAMES,
    SOS_ALPHA,
    SOS_BLEND,
    SOS_DEPTH,
    SOS_OPP_OPP_WEIGHT,
    SOS_OPPONENT_WEIGHT,
    SOS_TO_ELO,
    SPREAD_SCALE,
    TURNOVER_FLOOR,
    TURNOVER_FULL,
    TIE_POWER_EPS,
    TIE_SOS_EPS,
    TURNOVER_STRIP,
    UPSET_BOOST,
)


@dataclass(frozen=True)
class EngineConfig:
    """All knobs for one ranking run. Frozen so a week-to-week job is reproducible."""

    mercy_cap: int = MERCY_CAP
    initial_rating: float = INITIAL_RATING
    elo_scale: float = ELO_SCALE
    spread_scale: float = SPREAD_SCALE
    elo_k: float = ELO_K
    home_field: float = HOME_FIELD_ADVANTAGE
    cover_lambda: float = COVER_LAMBDA
    upset_boost: float = UPSET_BOOST
    sos_depth: int = SOS_DEPTH
    sos_alpha: float = SOS_ALPHA
    sos_opponent_weight: float = SOS_OPPONENT_WEIGHT
    sos_opp_opp_weight: float = SOS_OPP_OPP_WEIGHT
    sos_to_elo: float = SOS_TO_ELO
    elo_blend: float = ELO_BLEND
    sos_blend: float = SOS_BLEND
    turnover_strip: float = TURNOVER_STRIP
    turnover_floor: float = TURNOVER_FLOOR
    turnover_full: float = TURNOVER_FULL
    density_floor: float = DENSITY_FLOOR
    density_elo_floor: float = DENSITY_ELO_FLOOR
    density_min_scheduled: int = DENSITY_MIN_SCHEDULED
    panel_mix: float = DEFAULT_PANEL_MIX
    panel_half_life: float = PANEL_HALF_LIFE_GAMES
    recency_half_life: float = RECENCY_HALF_LIFE_WEEKS
    confidence_prior_games: float = CONFIDENCE_PRIOR_GAMES
    confidence_base_sigma: float = CONFIDENCE_BASE_SIGMA
    confidence_density_penalty: float = CONFIDENCE_DENSITY_PENALTY
    confidence_min_games: int = CONFIDENCE_MIN_GAMES
    confidence_flag: float = CONFIDENCE_FLAG
    tie_power_eps: float = TIE_POWER_EPS
    tie_sos_eps: float = TIE_SOS_EPS


@dataclass
class Team:
    """A UIL six-man program plus the geographic keys used by the density coefficient."""

    team_id: str
    name: str
    district: str
    region: str
    classification: str = "1A"
    city: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass
class Game:
    """One final or scheduled result.

    Scores may be omitted for future weeks; the pipeline skips those when
    updating Elo and still uses them for schedule-based density.
    """

    game_id: str
    week: int
    date: str
    home_id: str
    away_id: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    district_game: bool = False
    neutral: bool = False

    @property
    def is_final(self) -> bool:
        return self.home_score is not None and self.away_score is not None


@dataclass
class RosterFactor:
    """Graduation / positional-turnover inputs for the one-hit-wonder filter.

    Both rates are in ``[0, 1]``. ``positional_turnover`` is the share of
    starting spots (QB, skill, line, DB) that must be replaced; it is weighted
    more heavily than raw senior-class graduation.
    """

    team_id: str
    season: int
    graduation_rate: float = 0.0
    positional_turnover: float = 0.0
    notes: str = ""


@dataclass
class PanelAdjustment:
    """Optional human-panel prior, modeled after Dave Campbell's Texas Football.

    ``panel_rating`` lives on the same scale as Elo (league mean ≈ 1500).
    ``weight`` scales the engine's default panel mix for this team only.
    """

    team_id: str
    season: int
    panel_rating: float
    weight: float = 1.0
    notes: str = ""


@dataclass
class PriorRating:
    """Previous-season computer rating that turnover decay is applied to."""

    team_id: str
    season: int
    rating: float


@dataclass
class TeamState:
    """Mutable per-team rating state as the season is replayed week by week."""

    team_id: str
    elo: float
    preseason_elo: float
    power: float = 0.0
    sos: float = 0.0
    sos_elo: float = 0.0
    density: float = 1.0
    efficiency: float = 0.0
    turnover_decay: float = 0.0
    panel_weight_used: float = 0.0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    games_played: int = 0
    capped_pd: float = 0.0
    raw_pd: float = 0.0
    district_wins: int = 0
    district_losses: int = 0
    district_ties: int = 0
    confidence: float = 0.0
    sigma: float = 0.0
    notes: list[str] = field(default_factory=list)

    def snapshot(self) -> "TeamState":
        return replace(self, notes=list(self.notes))

    @property
    def record(self) -> str:
        return _record_string(self.wins, self.losses, self.ties)

    @property
    def district_record(self) -> str:
        return _record_string(self.district_wins, self.district_losses, self.district_ties)


def _record_string(wins: int, losses: int, ties: int) -> str:
    if ties:
        return f"{wins}-{losses}-{ties}"
    return f"{wins}-{losses}"


@dataclass(frozen=True)
class RankedTeam:
    """One row of the published table."""

    rank: int
    team_id: str
    name: str
    district: str
    region: str
    classification: str
    record: str
    district_record: str
    power: float
    elo: float
    sos: float
    density: float
    capped_pd: float
    raw_pd: float
    turnover_decay: float
    panel_weight: float
    wins: int
    losses: int
    ties: int
    district_wins: int
    district_losses: int
    district_ties: int
    games_played: int
    confidence: float
    sigma: float
    low_confidence: bool
    notes: str
    rank_delta: Optional[int] = None
    power_delta: Optional[float] = None
    prev_rank: Optional[int] = None
