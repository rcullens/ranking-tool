"""Week-over-week ranking pipeline.

Replay finals in date order, then recompute SOS, geographic density, and
the decaying panel blend. Call :meth:`RankingEngine.process_through_week`
after each Friday (it rebuilds from the preseason prior, so any week is
reachable) or :meth:`RankingEngine.rank` to run a full season.
"""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from sixman_rankings.classify import classification_matches
from sixman_rankings.confidence import assess
from sixman_rankings.elo import apply_game_update
from sixman_rankings.geography import density_map
from sixman_rankings.history import attach_movement, place_matches
from sixman_rankings.models import (
    EngineConfig,
    Game,
    PanelAdjustment,
    PriorRating,
    RankedTeam,
    RosterFactor,
    Team,
    TeamState,
)
from sixman_rankings.panel import blend_panel, panel_index
from sixman_rankings.recency import recency_weight
from sixman_rankings.sos import strength_of_schedule, team_efficiency
from sixman_rankings.ties import rank_key
from sixman_rankings.turnover import apply_turnover_decay, turnover_decay


def _index_teams(teams: Sequence[Team]) -> dict[str, Team]:
    idx = {t.team_id: t for t in teams}
    if len(idx) != len(teams):
        raise ValueError("duplicate team_id in team list")
    return idx


def _validate_games(teams: Mapping[str, Team], games: Sequence[Game]) -> None:
    known = set(teams)
    for game in games:
        if game.home_id not in known:
            raise ValueError(f"{game.game_id}: unknown home_id {game.home_id}")
        if game.away_id not in known:
            raise ValueError(f"{game.game_id}: unknown away_id {game.away_id}")
        if game.home_id == game.away_id:
            raise ValueError(f"{game.game_id}: team cannot play itself")


class RankingEngine:
    """Stateful engine that can be stepped week by week."""

    def __init__(
        self,
        teams: Sequence[Team],
        games: Sequence[Game],
        *,
        roster: Optional[Sequence[RosterFactor]] = None,
        panel: Optional[Sequence[PanelAdjustment]] = None,
        priors: Optional[Sequence[PriorRating]] = None,
        config: Optional[EngineConfig] = None,
        season: Optional[int] = None,
    ) -> None:
        self.config = config or EngineConfig()
        self.teams = _index_teams(teams)
        self.games = sorted(games, key=lambda g: (g.week, g.date, g.game_id))
        _validate_games(self.teams, self.games)
        self.season = season
        self.roster = {
            r.team_id: r
            for r in (roster or [])
            if season is None or r.season == season
        }
        self.panel = panel_index(
            [p for p in (panel or []) if season is None or p.season == season]
        )
        self.priors = {
            p.team_id: p
            for p in (priors or [])
            if season is None or p.season == season
        }
        self.states: dict[str, TeamState] = {}
        self._processed_game_ids: set[str] = set()
        self._as_of_week: int = 0
        self.reset_preseason()

    def reset_preseason(self) -> None:
        """Apply prior-season ratings, turnover decay, and the week-0 panel mix."""

        mean = self.config.initial_rating
        self.states = {}
        self._processed_game_ids = set()
        self._as_of_week = 0
        for tid, team in self.teams.items():
            legacy = self.priors[tid].rating if tid in self.priors else mean
            factor = self.roster.get(tid)
            decay = turnover_decay(factor, self.config) if factor else 0.0
            preseason = apply_turnover_decay(legacy, mean, decay)
            notes: list[str] = []
            if decay >= self.config.turnover_strip * 0.85:
                notes.append("one-hit-wonder decay")
            elif decay > 0:
                notes.append("roster decay")
            state = TeamState(
                team_id=tid,
                elo=preseason,
                preseason_elo=preseason,
                power=preseason,
                turnover_decay=decay,
                notes=notes,
            )
            # Week-0 panel blend so preseason magazines land on the table
            # before any Friday is played.
            computer = preseason
            blended, w = blend_panel(computer, 0, self.panel.get(tid), self.config)
            state.power = blended
            state.panel_weight_used = w
            self.states[tid] = state
        # Full schedule for density; no finals yet so SOS does not leak future weeks.
        self._recompute_components(through_week=None, finals_only_through=0)

    def _games_through(self, week: Optional[int], *, finals_only: bool) -> list[Game]:
        out: list[Game] = []
        for game in self.games:
            if week is not None and game.week > week:
                continue
            if finals_only and not game.is_final:
                continue
            out.append(game)
        return out

    def process_game(self, game: Game, *, as_of_week: Optional[int] = None) -> None:
        """Apply one final to Elo ratings and W-L / PD accumulators."""

        if not game.is_final or game.game_id in self._processed_game_ids:
            return
        home = self.states[game.home_id]
        away = self.states[game.away_id]
        _new_home, _new_away, update = apply_game_update(
            home.elo, away.elo, game, self.config
        )
        week = as_of_week if as_of_week is not None else self._as_of_week
        weight = recency_weight(game.week, week, self.config.recency_half_life)
        home.elo += update.home_delta * weight
        away.elo += update.away_delta * weight
        assert game.home_score is not None and game.away_score is not None
        raw = float(game.home_score - game.away_score)
        cap = float(self.config.mercy_cap)
        home_capped = max(-cap, min(cap, raw))
        home.capped_pd += home_capped
        away.capped_pd -= home_capped
        home.raw_pd += raw
        away.raw_pd -= raw
        home.games_played += 1
        away.games_played += 1
        if game.home_score > game.away_score:
            home.wins += 1
            away.losses += 1
        elif game.away_score > game.home_score:
            away.wins += 1
            home.losses += 1
        else:
            home.ties += 1
            away.ties += 1
        if game.district_game:
            if game.home_score > game.away_score:
                home.district_wins += 1
                away.district_losses += 1
            elif game.away_score > game.home_score:
                away.district_wins += 1
                home.district_losses += 1
            else:
                home.district_ties += 1
                away.district_ties += 1
        self._processed_game_ids.add(game.game_id)

    def process_through_week(self, week: int) -> list[RankedTeam]:
        """Replay every final through ``week`` (inclusive) and republish."""

        # Always rebuild from preseason so callers can jump to any week.
        self.reset_preseason()
        self._as_of_week = week
        for game in self.games:
            if game.week > week:
                break
            self.process_game(game, as_of_week=week)
        self._recompute_components(through_week=week, finals_only_through=week)
        return self.table()

    def rank(
        self,
        *,
        through_week: Optional[int] = None,
        classification: Optional[str] = None,
        district: Optional[str] = None,
        region: Optional[str] = None,
        association: Optional[str] = None,
        with_movement: bool = True,
    ) -> list[RankedTeam]:
        """Process the season (or through ``through_week``) and return the table."""

        if through_week is None:
            weeks = [g.week for g in self.games]
            through_week = max(weeks) if weeks else 0
        scoped = bool(classification or district or region or association)
        previous = None
        if with_movement and through_week > 0:
            previous = self.process_through_week(through_week - 1)
            if scoped:
                previous = self._apply_scope(
                    previous,
                    classification=classification,
                    district=district,
                    region=region,
                    association=association,
                )
        current = self.process_through_week(through_week)
        if scoped:
            current = self._apply_scope(
                current,
                classification=classification,
                district=district,
                region=region,
                association=association,
            )
        if with_movement:
            current = attach_movement(current, previous)
        return current

    def weekly_history(
        self,
        through_week: Optional[int] = None,
        *,
        classification: Optional[str] = None,
        district: Optional[str] = None,
        region: Optional[str] = None,
        association: Optional[str] = None,
    ) -> dict[int, list[RankedTeam]]:
        """Snapshot every week from 0 (preseason) through ``through_week``."""

        if through_week is None:
            weeks = [g.week for g in self.games]
            through_week = max(weeks) if weeks else 0
        snaps: dict[int, list[RankedTeam]] = {}
        self.reset_preseason()
        snaps[0] = self.table(
            classification=classification, district=district, region=region, association=association
        )
        prev = snaps[0]
        for week in range(1, through_week + 1):
            current = self.process_through_week(week)
            if classification or district or region or association:
                current = self._apply_scope(
                    current,
                    classification=classification,
                    district=district,
                    region=region,
                    association=association,
                )
            snaps[week] = attach_movement(current, prev)
            prev = snaps[week]
        return snaps

    def _rerank_subset(
        self,
        rows: Sequence[RankedTeam],
        classification: str,
    ) -> list[RankedTeam]:
        return self._apply_scope(rows, classification=classification)

    def _apply_scope(
        self,
        rows: Sequence[RankedTeam],
        *,
        classification: Optional[str] = None,
        district: Optional[str] = None,
        region: Optional[str] = None,
        association: Optional[str] = None,
    ) -> list[RankedTeam]:
        from dataclasses import replace

        subset = list(rows)
        if classification:
            subset = [r for r in subset if classification_matches(r.classification, classification)]
        if district:
            subset = [r for r in subset if place_matches(r.district, district)]
        if region:
            subset = [r for r in subset if place_matches(r.region, region)]
        if association:
            want = association.strip().upper()
            subset = [
                r for r in subset if (getattr(r, "association", None) or "UIL").upper() == want
            ]
        return [replace(row, rank=i) for i, row in enumerate(subset, start=1)]

    def _recompute_components(
        self,
        *,
        through_week: Optional[int],
        finals_only_through: Optional[int],
    ) -> None:
        schedule = self._games_through(through_week, finals_only=False)
        finals = self._games_through(finals_only_through, finals_only=True)
        team_ids = list(self.teams)
        densities = density_map(self.teams, schedule, self.config)
        as_of = through_week if through_week is not None else self._as_of_week
        sos = strength_of_schedule(team_ids, finals, self.config, as_of_week=as_of)
        eff = team_efficiency(finals, self.config.mercy_cap)
        sos_values = [sos[tid] for tid in team_ids]
        mean_sos = sum(sos_values) / len(sos_values) if sos_values else 0.0
        mean_elo = self.config.initial_rating

        for tid, state in self.states.items():
            density = densities.get(tid, 1.0)
            raw_sos = sos.get(tid, 0.0)
            # Density haircuts the schedule term so an insular 9-0 is not
            # credited with a "strong" SOS it never earned.
            sos_adj = raw_sos * density
            sos_elo = mean_elo + self.config.sos_to_elo * (sos_adj - mean_sos)
            # Map density from [floor, 1] onto [density_elo_floor, 1] so a
            # team sitting at the isolation floor actually loses Elo credit
            # instead of keeping ~96% of a bubble rating.
            span = 1.0 - self.config.density_floor
            if span <= 0:
                t = 1.0
            else:
                t = min(1.0, max(0.0, (density - self.config.density_floor) / span))
            elo_kept = self.config.density_elo_floor + (
                1.0 - self.config.density_elo_floor
            ) * t
            elo_shrunk = mean_elo + (state.elo - mean_elo) * elo_kept
            computer = (
                self.config.elo_blend * elo_shrunk
                + self.config.sos_blend * sos_elo
            )
            power, panel_w = blend_panel(
                computer,
                state.games_played,
                self.panel.get(tid),
                self.config,
            )
            conf, sigma, low = assess(state.games_played, density, self.config)
            state.sos = sos_adj
            state.sos_elo = sos_elo
            state.density = density
            state.efficiency = eff.get(tid, 0.0)
            state.power = power
            state.panel_weight_used = panel_w
            state.confidence = conf
            state.sigma = sigma

            notes = [n for n in state.notes if n in {"one-hit-wonder decay", "roster decay"}]
            if density <= self.config.density_floor + 0.06:
                notes.append("insular schedule")
            if panel_w >= 0.08:
                notes.append("panel active")
            if low:
                notes.append("low confidence")
            state.notes = notes

    def table(
        self,
        *,
        classification: Optional[str] = None,
        district: Optional[str] = None,
        region: Optional[str] = None,
        association: Optional[str] = None,
    ) -> list[RankedTeam]:
        finals = self._games_through(self._as_of_week, finals_only=True)
        states = list(self.states.values())
        if classification:
            states = [
                s
                for s in states
                if classification_matches(self.teams[s.team_id].classification, classification)
            ]
        if district:
            states = [
                s for s in states if place_matches(self.teams[s.team_id].district, district)
            ]
        if region:
            states = [
                s for s in states if place_matches(self.teams[s.team_id].region, region)
            ]
        if association:
            want = association.strip().upper()
            states = [
                s
                for s in states
                if (getattr(self.teams[s.team_id], "association", None) or "UIL").upper() == want
            ]
        ordered = sorted(states, key=rank_key(finals, self.config))
        rows: list[RankedTeam] = []
        for rank, state in enumerate(ordered, start=1):
            team = self.teams[state.team_id]
            low = "low confidence" in state.notes
            rows.append(
                RankedTeam(
                    rank=rank,
                    team_id=state.team_id,
                    name=team.name,
                    district=team.district,
                    region=team.region,
                    classification=team.classification,
                    association=getattr(team, "association", None) or "UIL",
                    record=state.record,
                    district_record=state.district_record,
                    power=state.power,
                    elo=state.elo,
                    sos=state.sos,
                    density=state.density,
                    capped_pd=state.capped_pd,
                    raw_pd=state.raw_pd,
                    turnover_decay=state.turnover_decay,
                    panel_weight=state.panel_weight_used,
                    wins=state.wins,
                    losses=state.losses,
                    ties=state.ties,
                    district_wins=state.district_wins,
                    district_losses=state.district_losses,
                    district_ties=state.district_ties,
                    games_played=state.games_played,
                    confidence=state.confidence,
                    sigma=state.sigma,
                    low_confidence=low,
                    notes=", ".join(state.notes),
                )
            )
        return rows


def rank_season(
    teams: Sequence[Team],
    games: Sequence[Game],
    *,
    roster: Optional[Sequence[RosterFactor]] = None,
    panel: Optional[Sequence[PanelAdjustment]] = None,
    priors: Optional[Sequence[PriorRating]] = None,
    config: Optional[EngineConfig] = None,
    through_week: Optional[int] = None,
    season: Optional[int] = None,
    classification: Optional[str] = None,
    district: Optional[str] = None,
    region: Optional[str] = None,
    association: Optional[str] = None,
    with_movement: bool = True,
) -> list[RankedTeam]:
    """Functional entry point used by the CLI and by library callers."""

    engine = RankingEngine(
        teams,
        games,
        roster=roster,
        panel=panel,
        priors=priors,
        config=config,
        season=season,
    )
    return engine.rank(
        through_week=through_week,
        classification=classification,
        district=district,
        region=region,
        association=association,
        with_movement=with_movement,
    )


def weekly_snapshots(
    teams: Sequence[Team],
    games: Sequence[Game],
    **kwargs,
) -> dict[int, list[RankedTeam]]:
    """Recompute the full table after every week that has a final."""

    classification = kwargs.pop("classification", None)
    district = kwargs.pop("district", None)
    region = kwargs.pop("region", None)
    engine = RankingEngine(teams, games, **kwargs)
    weeks = sorted({g.week for g in games if g.is_final})
    through = max(weeks) if weeks else 0
    return engine.weekly_history(
        through, classification=classification, district=district, region=region
    )
