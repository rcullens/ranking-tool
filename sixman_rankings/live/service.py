"""In-memory live season: merge scores, republish rankings, expose chart series."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Optional

from sixman_rankings.export import ranked_record
from sixman_rankings.history import (
    district_groups,
    format_region_label,
    power_groups_by_district,
    region_groups,
)
from sixman_rankings.io import load_dataset, load_sample_dataset, load_uil_dataset
from sixman_rankings.live.merge import hide_scores_after, merge_finals
from sixman_rankings.live.providers import FetchResult, default_feed_url, fetch_json_feed, parse_feed_payload
from sixman_rankings.live.window import in_football_window, next_window_start, now_central, window_label
from sixman_rankings.models import EngineConfig, Game, PanelAdjustment, PriorRating, RankedTeam, RosterFactor, Team
from sixman_rankings.pipeline import RankingEngine


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass
class LiveStatus:
    provider: str
    football_window: bool
    window_label: str
    last_sync: Optional[str]
    last_result: str
    current_week: int
    finals: int
    scheduled: int
    week_complete: bool
    next_window: str
    updates_last_sync: int
    feed_url: Optional[str]


@dataclass
class LiveSeasonService:
    """Holds the working season and republishes after every successful sync."""

    teams: list[Team]
    games: list[Game]
    roster: list[RosterFactor] = field(default_factory=list)
    panel: list[PanelAdjustment] = field(default_factory=list)
    priors: list[PriorRating] = field(default_factory=list)
    config: EngineConfig = field(default_factory=EngineConfig)
    season: Optional[int] = 2026
    start_week: int = 99
    release_batch: int = 2
    feed_url: Optional[str] = None
    _held: dict[str, tuple[int, int]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    last_sync: Optional[datetime] = None
    last_result: str = "idle"
    updates_last_sync: int = 0
    provider_name: str = "replay"

    @classmethod
    def from_demo(cls, *, start_week: Optional[int] = None) -> "LiveSeasonService":
        """20-team synthetic fixture used by engine tests and the football-night replay."""

        teams, games, roster, panel, priors = load_sample_dataset()
        week = start_week if start_week is not None else _env_int("SIXMAN_LIVE_START_WEEK", 4)
        trimmed, held = hide_scores_after(games, week)
        return cls(
            teams=teams,
            games=trimmed,
            roster=roster,
            panel=panel,
            priors=priors,
            season=2025,
            start_week=week,
            release_batch=_env_int("SIXMAN_RELEASE_BATCH", 2),
            feed_url=default_feed_url(),
            _held=held,
            provider_name="json-feed" if default_feed_url() else "replay",
        )

    @classmethod
    def from_uil(cls, *, start_week: Optional[int] = None) -> "LiveSeasonService":
        """Full Texas six-man catalog with ingested MaxPreps / SixManFootball scores."""

        teams, games, roster, panel, priors = load_uil_dataset()
        week = start_week if start_week is not None else _env_int("SIXMAN_LIVE_START_WEEK", 99)
        trimmed, held = hide_scores_after(games, week)
        return cls(
            teams=teams,
            games=trimmed,
            roster=roster,
            panel=panel,
            priors=priors,
            season=2026,
            start_week=week,
            release_batch=_env_int("SIXMAN_RELEASE_BATCH", 2),
            feed_url=default_feed_url(),
            _held=held,
            provider_name="json-feed" if default_feed_url() else "uil-snapshot",
        )

    @classmethod
    def from_sample(cls, *, start_week: Optional[int] = None) -> "LiveSeasonService":
        """Default board dataset: the full UIL field."""

        return cls.from_uil(start_week=start_week)

    @classmethod
    def from_data_dir(cls, data_dir, *, start_week: Optional[int] = None) -> "LiveSeasonService":
        from pathlib import Path

        root = Path(data_dir)
        teams, games, roster, panel, priors = load_dataset(
            teams_path=root / "teams.csv",
            games_path=root / "games.csv",
            roster_path=root / "roster_factors.csv" if (root / "roster_factors.csv").exists() else None,
            panel_path=root / "panel_adjustments.csv" if (root / "panel_adjustments.csv").exists() else None,
            priors_path=root / "priors.csv" if (root / "priors.csv").exists() else None,
        )
        week = start_week if start_week is not None else _env_int("SIXMAN_LIVE_START_WEEK", 99)
        trimmed, held = hide_scores_after(games, week)
        return cls(
            teams=teams,
            games=trimmed,
            roster=roster,
            panel=panel,
            priors=priors,
            start_week=week,
            _held=held,
            feed_url=default_feed_url(),
            provider_name="json-feed" if default_feed_url() else "replay",
        )

    def current_week(self) -> int:
        finals = [g.week for g in self.games if g.is_final]
        return max(finals) if finals else 0

    def _engine(self) -> RankingEngine:
        return RankingEngine(
            self.teams,
            self.games,
            roster=self.roster,
            panel=self.panel,
            priors=self.priors,
            config=self.config,
            season=self.season,
        )

    def rankings(
        self,
        *,
        classification: Optional[str] = None,
        district: Optional[str] = None,
        region: Optional[str] = None,
        association: Optional[str] = None,
    ) -> list[RankedTeam]:
        with self._lock:
            engine = self._engine()
            return engine.rank(
                through_week=self.current_week(),
                classification=classification,
                district=district,
                region=region,
                association=association,
                with_movement=True,
            )

    def _board_rows(
        self,
        rows: list[RankedTeam],
        statewide_rank: dict[str, int],
        *,
        week: int,
    ) -> list[dict]:
        packed = []
        for local_rank, row in enumerate(rows, start=1):
            rec = ranked_record(row, week=week, season=self.season)
            rec["local_rank"] = local_rank
            rec["statewide_rank"] = statewide_rank.get(row.team_id)
            rec["rank"] = local_rank
            packed.append(rec)
        return packed

    def boards(self) -> dict:
        """District and region tables: local power rank plus district W-L race."""

        statewide = self.rankings()
        week = self.current_week()
        statewide_rank = {row.team_id: row.rank for row in statewide}

        districts = []
        for name, power_members in power_groups_by_district(statewide).items():
            standings = district_groups(power_members).get(name, power_members)
            districts.append(
                {
                    "id": name,
                    "label": name,
                    "kind": "district",
                    "team_ids": [row.team_id for row in power_members],
                    "power": self._board_rows(power_members, statewide_rank, week=week),
                    "standings": self._board_rows(standings, statewide_rank, week=week),
                }
            )

        regions = []
        for name, members in region_groups(statewide).items():
            regions.append(
                {
                    "id": name,
                    "label": format_region_label(name),
                    "kind": "region",
                    "team_ids": [row.team_id for row in members],
                    "power": self._board_rows(members, statewide_rank, week=week),
                }
            )
        return {"week": week, "districts": districts, "regions": regions}

    def history(self) -> dict[int, list[RankedTeam]]:
        with self._lock:
            engine = self._engine()
            return engine.weekly_history(self.current_week())

    def compare_series(
        self,
        team_ids: list[str],
        *,
        metric: str = "power",
    ) -> dict:
        hist = self.history()
        weeks = sorted(hist)
        series = []
        for tid in team_ids:
            points = []
            for week in weeks:
                row = next((r for r in hist[week] if r.team_id == tid), None)
                if row is None:
                    points.append({"week": week, "value": None, "rank": None})
                    continue
                value = row.rank if metric == "rank" else row.power
                points.append({"week": week, "value": round(float(value), 2), "rank": row.rank})
            team = next((t for t in self.teams if t.team_id == tid), None)
            series.append(
                {
                    "team_id": tid,
                    "name": team.name if team else tid,
                    "classification": team.classification if team else "",
                    "points": points,
                }
            )
        return {
            "metric": metric,
            "weeks": weeks,
            "current_week": self.current_week(),
            "series": series,
        }

    def presets(self) -> dict[str, list[str]]:
        from sixman_rankings.classify import classification_matches

        table = self.rankings()
        hist = self.history()
        week = self.current_week()
        last = hist.get(week - 1, [])
        districts: dict[str, list[str]] = {}
        regions: dict[str, list[str]] = {}
        for team in self.teams:
            assoc = getattr(team, "association", None) or "UIL"
            if assoc != "UIL":
                continue
            districts.setdefault(team.district, []).append(team.team_id)
            regions.setdefault(team.region, []).append(team.team_id)
        return {
            "this_week_top10": [r.team_id for r in table[:10]],
            "last_week_top10": [r.team_id for r in last[:10]],
            "undefeated": [r.team_id for r in table if r.losses == 0 and r.games_played > 0],
            "division_di": [r.team_id for r in table if classification_matches(r.classification, "DI")],
            "division_dii": [r.team_id for r in table if classification_matches(r.classification, "DII")],
            **{f"district:{key}": ids for key, ids in districts.items()},
            **{f"region:{key}": ids for key, ids in regions.items()},
        }

    def status(self) -> LiveStatus:
        stamp = now_central()
        finals = sum(1 for g in self.games if g.is_final)
        scheduled = sum(1 for g in self.games if not g.is_final)
        week = self.current_week()
        week_games = [g for g in self.games if g.week == week]
        complete = bool(week_games) and all(g.is_final for g in week_games)
        return LiveStatus(
            provider=self.provider_name,
            football_window=in_football_window(stamp),
            window_label=window_label(stamp),
            last_sync=self.last_sync.isoformat() if self.last_sync else None,
            last_result=self.last_result,
            current_week=week,
            finals=finals,
            scheduled=scheduled,
            week_complete=complete,
            next_window=next_window_start(stamp).isoformat(),
            updates_last_sync=self.updates_last_sync,
            feed_url=self.feed_url,
        )

    def _release_held(self, batch: int) -> int:
        pending = [
            g
            for g in self.games
            if (not g.is_final) and g.game_id in self._held
        ]
        pending.sort(key=lambda g: (g.week, g.date, g.game_id))
        released = 0
        by_id = {g.game_id: i for i, g in enumerate(self.games)}
        for game in pending[:batch]:
            hs, aws = self._held[game.game_id]
            idx = by_id[game.game_id]
            self.games[idx] = replace(game, home_score=hs, away_score=aws)
            released += 1
        return released

    def ingest_payload(self, payload) -> FetchResult:
        games = parse_feed_payload(payload, self.teams)
        return FetchResult(games, "webhook", True, f"accepted {len(games)} games")

    def ingest_and_merge(self, payload) -> int:
        fetched = self.ingest_payload(payload)
        with self._lock:
            self.games, n = merge_finals(self.games, fetched.games)
            self.updates_last_sync = n
            self.last_result = f"ingested {n} updates"
            self.last_sync = now_central()
            self.provider_name = "webhook"
        return n

    def resolve_team_id(self, raw: str) -> Optional[str]:
        from sixman_rankings.live.names import build_alias_index, resolve_team_id

        return resolve_team_id(raw, build_alias_index(self.teams))

    def what_if(
        self,
        *,
        home_id: str,
        away_id: str,
        home_score: Optional[int] = None,
        away_score: Optional[int] = None,
        margin: Optional[float] = None,
        neutral: bool = False,
        district_game: bool = False,
    ) -> dict:
        """Provisional Friday — does not write back to the live season."""

        from sixman_rankings.whatif import simulate_what_if

        home = self.resolve_team_id(home_id) or home_id
        away = self.resolve_team_id(away_id) or away_id
        with self._lock:
            report = simulate_what_if(
                self.teams,
                self.games,
                home_id=home,
                away_id=away,
                home_score=home_score,
                away_score=away_score,
                margin=margin,
                neutral=neutral,
                district_game=district_game,
                roster=self.roster,
                panel=self.panel,
                priors=self.priors,
                config=self.config,
                season=self.season,
            )
        focus = {report.game.home_id, report.game.away_id}
        movers = []
        for row in report.after:
            if row.team_id not in focus and not (row.rank_delta or 0):
                continue
            before = report.row_before(row.team_id)
            movers.append(
                {
                    "team_id": row.team_id,
                    "name": row.name,
                    "rank_before": before.rank if before else None,
                    "rank_after": row.rank,
                    "rank_delta": row.rank_delta,
                    "power_before": round(before.power, 2) if before else None,
                    "power_after": round(row.power, 2),
                    "power_delta": round(row.power_delta or 0.0, 2),
                }
            )
        ordered = [m for tid in focus for m in movers if m["team_id"] == tid]
        ordered.extend(m for m in movers if m["team_id"] not in focus)
        return {
            "provisional": True,
            "writes_back": False,
            "game": {
                "home_id": report.game.home_id,
                "away_id": report.game.away_id,
                "home_score": report.game.home_score,
                "away_score": report.game.away_score,
                "week": report.game.week,
                "neutral": report.game.neutral,
                "district_game": report.game.district_game,
            },
            "through_week": report.through_week,
            "movers": ordered,
        }

    def sync(
        self,
        *,
        force_replay: bool = False,
        live_sources: bool = True,
        skip_maxpreps: bool = False,
        skip_smf: bool = False,
    ) -> LiveStatus:
        """Pull MaxPreps / SMF (and optional JSON feed). Demo replay stays off the UIL board.

        Replay of held sample finals only runs for the 20-team demo dataset,
        and only inside the Thu–Sat window (or when ``force_replay`` is set).
        """

        with self._lock:
            updates = 0
            notes: list[str] = []
            if self.feed_url:
                fetched = fetch_json_feed(self.feed_url, self.teams)
                self.provider_name = "json-feed"
                if fetched.ok:
                    self.games, n = merge_finals(self.games, fetched.games)
                    updates += n
                    notes.append(fetched.detail)
                else:
                    notes.append(f"feed failed: {fetched.detail}")
            if live_sources and len(self.teams) > 30 and os.environ.get("SIXMAN_SKIP_LIVE") != "1":
                try:
                    from sixman_rankings.catalog import uil_schools
                    from sixman_rankings.live.ingest import merge_game_rows, pull_maxpreps, pull_smf, rows_as_games

                    schools = uil_schools()
                    season = self.season or 2026
                    batches = []
                    if not skip_maxpreps:
                        rows, report = pull_maxpreps(schools, season=season)
                        batches.append(rows)
                        notes.append(f"maxpreps: {report.detail}")
                    if not skip_smf:
                        rows, report = pull_smf(schools, season=season, persist=True)
                        batches.append(rows)
                        notes.append(f"smf: {report.detail}")
                    incoming = rows_as_games(merge_game_rows(batches))
                    self.games, n = merge_finals(self.games, incoming)
                    updates += n
                    self.provider_name = "maxpreps+smf"
                except Exception as exc:  # noqa: BLE001 — keep the board up if a pull fails
                    notes.append(f"live ingest failed: {exc}")
            live = in_football_window() or force_replay
            if live and self._held and len(self.teams) <= 30:
                n = self._release_held(self.release_batch)
                updates += n
                if n:
                    notes.append(f"replayed {n} held finals")
                    if not self.feed_url:
                        self.provider_name = "replay"
            if not notes:
                if live:
                    notes.append("no new scores")
                else:
                    notes.append("outside Thu–Sat window; waiting")
            self.updates_last_sync = updates
            self.last_sync = now_central()
            self.last_result = "; ".join(notes)
        return self.status()


_SERVICE: Optional[LiveSeasonService] = None
_SERVICE_LOCK = threading.Lock()


def get_service() -> LiveSeasonService:
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            data_dir = os.environ.get("SIXMAN_DATA_DIR")
            if data_dir:
                _SERVICE = LiveSeasonService.from_data_dir(data_dir)
            else:
                _SERVICE = LiveSeasonService.from_sample()
            # Publish the starting week immediately so the graph has history.
            _SERVICE.last_result = f"loaded through week {_SERVICE.current_week()}"
            _SERVICE.last_sync = now_central()
        return _SERVICE


def reset_service() -> None:
    global _SERVICE
    with _SERVICE_LOCK:
        _SERVICE = None
