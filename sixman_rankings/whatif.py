"""Provisional what-if ratings that never mutate the caller's season state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from sixman_rankings.history import attach_movement
from sixman_rankings.margin import cap_margin
from sixman_rankings.models import (
    EngineConfig,
    Game,
    PanelAdjustment,
    PriorRating,
    RankedTeam,
    RosterFactor,
    Team,
)


@dataclass(frozen=True)
class WhatIfReport:
    """Before/after tables plus the hypothetical game that was injected."""

    game: Game
    before: list[RankedTeam]
    after: list[RankedTeam]
    through_week: int

    def row_before(self, team_id: str) -> Optional[RankedTeam]:
        return next((r for r in self.before if r.team_id == team_id), None)

    def row_after(self, team_id: str) -> Optional[RankedTeam]:
        return next((r for r in self.after if r.team_id == team_id), None)


def scores_from_margin(margin: float, mercy_cap: int) -> tuple[int, int]:
    """Synthesize a final from a home-perspective margin (then mercy-capped)."""

    capped = int(round(cap_margin(margin, mercy_cap)))
    return 28 + capped, 28


def simulate_what_if(
    teams: Sequence[Team],
    games: Sequence[Game],
    *,
    home_id: str,
    away_id: str,
    home_score: Optional[int] = None,
    away_score: Optional[int] = None,
    margin: Optional[float] = None,
    through_week: Optional[int] = None,
    neutral: bool = False,
    district_game: bool = False,
    roster: Optional[Sequence[RosterFactor]] = None,
    panel: Optional[Sequence[PanelAdjustment]] = None,
    priors: Optional[Sequence[PriorRating]] = None,
    config: Optional[EngineConfig] = None,
    season: Optional[int] = None,
) -> WhatIfReport:
    from sixman_rankings.pipeline import RankingEngine

    cfg = config or EngineConfig()
    known = {t.team_id for t in teams}
    if home_id not in known:
        raise ValueError(f"unknown home_id {home_id}")
    if away_id not in known:
        raise ValueError(f"unknown away_id {away_id}")
    if home_id == away_id:
        raise ValueError("what-if teams must be different")

    if home_score is None or away_score is None:
        if margin is None:
            raise ValueError("provide home_score and away_score, or margin")
        home_score, away_score = scores_from_margin(margin, cfg.mercy_cap)

    finals_weeks = [g.week for g in games if g.is_final]
    base_week = through_week if through_week is not None else (max(finals_weeks) if finals_weeks else 0)
    hypo_week = base_week if base_week > 0 else 1

    hypo = Game(
        game_id=f"whatif-{home_id}-{away_id}-w{hypo_week}",
        week=hypo_week,
        date="whatif",
        home_id=home_id,
        away_id=away_id,
        home_score=int(home_score),
        away_score=int(away_score),
        district_game=district_game,
        neutral=neutral,
    )

    common = dict(
        roster=roster,
        panel=panel,
        priors=priors,
        config=cfg,
        season=season,
    )
    before_engine = RankingEngine(teams, games, **common)
    before = before_engine.rank(through_week=base_week, with_movement=False)

    after_engine = RankingEngine(teams, list(games) + [hypo], **common)
    after = after_engine.rank(through_week=max(base_week, hypo_week), with_movement=False)
    after = attach_movement(after, before)
    return WhatIfReport(game=hypo, before=before, after=after, through_week=max(base_week, hypo_week))


def format_what_if(report: WhatIfReport) -> str:
    game = report.game
    assert game.home_score is not None and game.away_score is not None
    site = "neutral" if game.neutral else "home/away"
    header = (
        f"What-if  ·  {game.home_id} {game.home_score}–{game.away_score} {game.away_id}"
        f"  ({site}, week {game.week})"
    )
    lines = [header, "Does not write back to the season.", ""]
    lines.append(f"{'Team':<18} {'Rk':>4} {'→':>2} {'New':>4} {'ΔRk':>4}  {'Power':>8} {'→':>2} {'New':>8} {'ΔP':>7}")
    lines.append("-" * 72)
    focus = {game.home_id, game.away_id}
    shown: list[str] = []
    for row in report.after:
        if row.team_id in focus or (row.rank_delta or 0) != 0:
            shown.append(row.team_id)
    ordered_ids = [tid for tid in (game.home_id, game.away_id) if tid in shown]
    ordered_ids.extend(tid for tid in shown if tid not in ordered_ids)
    by_id = {r.team_id: r for r in report.after}
    for tid in ordered_ids:
        row = by_id[tid]
        before = report.row_before(tid)
        before_rank = before.rank if before else "—"
        before_power = f"{before.power:8.1f}" if before else "     —"
        delta_r = row.rank_delta if row.rank_delta is not None else 0
        delta_p = row.power_delta if row.power_delta is not None else 0.0
        lines.append(
            f"{row.name:<18} {before_rank:>4} → {row.rank:>4} {delta_r:>+4}  "
            f"{before_power} → {row.power:8.1f} {delta_p:+7.1f}"
        )
    return "\n".join(lines)
