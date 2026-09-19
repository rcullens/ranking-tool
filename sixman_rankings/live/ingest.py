"""Pull current-season Texas six-man scores and rewrite the bundled field.

Sources (same peers sixmanmadness uses):
  * MaxPreps school schedule contests (preferred — both scores, GHA-friendly)
  * SixManFootball week scoreboards (HTML or cached markdown)
  * optional JSON feed (``SIXMAN_FEED_URL``)

Cross-association games count (UIL vs TAPPS, etc.). Invented district
slates are never written. Teams with no finals stay on the board via
priors / low confidence.
"""

from __future__ import annotations

import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from sixman_rankings.catalog import (
    CatalogSchool,
    football_season_year,
    maxpreps_schedule_urls,
    maxpreps_season_path,
    prior_rating,
    uil_schools,
)
from sixman_rankings.live.http import FetchError, fetch_text, fetch_with_fallback
from sixman_rankings.live.maxpreps import MaxPrepsGame, games_to_rows as mp_to_rows, parse_contests
from sixman_rankings.live.window import now_central
from sixman_rankings.smf import games_to_rows as smf_to_rows, parse_smf_week_text, week_dates

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DATA = Path(__file__).resolve().parents[1] / "data"
SMF_DIR = PACKAGE_DATA / "smf"


@dataclass
class SourceReport:
    name: str
    ok: bool
    detail: str
    games: int = 0
    finals: int = 0


@dataclass
class IngestReport:
    season: int
    teams: int
    games: int
    finals: int
    sources: list[SourceReport] = field(default_factory=list)
    pulled_at: str = ""
    wrote: Optional[str] = None
    offline: Optional[str] = None

    def summary(self) -> str:
        bits = [f"{self.teams} six-man teams", f"{self.finals} finals / {self.games} games"]
        for src in self.sources:
            mark = "ok" if src.ok else "fail"
            bits.append(f"{src.name} {mark}: {src.detail}")
        return " · ".join(bits)


def _season() -> int:
    raw = os.environ.get("SIXMAN_SEASON")
    if raw and raw.strip():
        return int(raw)
    return football_season_year()


def current_week(season: Optional[int] = None) -> int:
    from sixman_rankings.live.maxpreps import date_to_week

    return date_to_week(now_central().date().isoformat(), season=season or _season())


def merge_game_rows(batches: Iterable[list[dict]]) -> list[dict]:
    """Deduplicate catalog games; prefer a two-score final over a scheduled row."""

    best: dict[tuple, dict] = {}
    rank = {"maxpreps": 3, "smf": 2, "feed": 2, "cache": 1}

    def key(row: dict) -> tuple:
        return (tuple(sorted((row["home_id"], row["away_id"]))), int(row["week"]))

    for batch in batches:
        for row in batch:
            k = key(row)
            cur = best.get(k)
            if cur is None:
                best[k] = row
                continue
            incoming_final = row.get("home_score") is not None and row.get("away_score") is not None
            current_final = cur.get("home_score") is not None and cur.get("away_score") is not None
            if incoming_final and not current_final:
                best[k] = row
            elif incoming_final and current_final:
                if rank.get(row.get("source", ""), 0) >= rank.get(cur.get("source", ""), 0):
                    # Keep our home/away if the pair is swapped.
                    if {row["home_id"], row["away_id"]} == {cur["home_id"], cur["away_id"]}:
                        if row["home_id"] != cur["home_id"]:
                            row = {
                                **row,
                                "home_id": cur["home_id"],
                                "away_id": cur["away_id"],
                                "home_score": row["away_score"],
                                "away_score": row["home_score"],
                                "game_id": cur["game_id"],
                            }
                    best[k] = row
            elif not incoming_final and not current_final:
                if rank.get(row.get("source", ""), 0) > rank.get(cur.get("source", ""), 0):
                    best[k] = row
    rows = list(best.values())
    rows.sort(key=lambda r: (r["week"], r["date"], r["game_id"]))
    return rows


def pull_maxpreps(
    schools: list[CatalogSchool],
    *,
    season: int,
    workers: int = 8,
) -> tuple[list[dict], SourceReport]:
    path = maxpreps_season_path(season)
    games: list[MaxPrepsGame] = []
    ok = 0
    failed = 0

    def one(school: CatalogSchool) -> list[MaxPrepsGame]:
        last_err: Optional[Exception] = None
        for url in maxpreps_schedule_urls(school, season_path=path):
            try:
                html = fetch_text(url, referer="https://www.maxpreps.com/")
            except FetchError as exc:
                last_err = exc
                if exc.status == 404:
                    continue
                raise
            parsed = parse_contests(html, school_name=school.name, season=season)
            if parsed:
                return parsed
        if last_err:
            raise last_err
        return []

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futs = {pool.submit(one, school): school for school in schools}
        for fut in as_completed(futs):
            school = futs[fut]
            try:
                parsed = fut.result()
                games.extend(parsed)
                ok += 1
            except Exception as exc:  # noqa: BLE001 — surface per-school failure
                failed += 1
                if os.environ.get("SIXMAN_INGEST_DEBUG"):
                    print(f"maxpreps {school.team_id}: {exc}")

    rows = mp_to_rows(games, schools)
    finals = sum(1 for r in rows if r["home_score"] is not None)
    report = SourceReport(
        name="maxpreps",
        ok=ok > 0,
        detail=f"{ok} school pages, {failed} missed, {finals} catalog finals",
        games=len(rows),
        finals=finals,
    )
    return rows, report


def pull_smf(
    schools: list[CatalogSchool],
    *,
    season: int,
    weeks: Optional[list[int]] = None,
    persist: bool = True,
) -> tuple[list[dict], SourceReport]:
    if weeks is None:
        last = max(current_week(season) + 1, 4)
        weeks = list(range(0, last + 1))
    texts: dict[int, str] = {}
    fetched = 0
    cached = 0
    for week in weeks:
        url = f"https://www.sixmanfootball.com/scores/{season}/week-{week}/"
        body = None
        try:
            body, via = fetch_with_fallback(url, referer=f"https://www.sixmanfootball.com/scores/{season}/")
            if via == "direct" or (body and "block-matchup" in body) or len(body) > 400:
                texts[week] = body
                fetched += 1
                if persist:
                    dest = SMF_DIR / f"week-{week}.md"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(body, encoding="utf-8")
        except FetchError:
            body = None
        if week not in texts:
            cached_path = SMF_DIR / f"week-{week}.md"
            if cached_path.exists():
                texts[week] = cached_path.read_text(encoding="utf-8")
                cached += 1

    parsed = []
    for week, text in sorted(texts.items()):
        parsed.extend(parse_smf_week_text(text, week))
    rows = smf_to_rows(parsed, schools)
    for row in rows:
        row["source"] = "smf"
    finals = sum(1 for r in rows if r["home_score"] is not None)
    report = SourceReport(
        name="sixmanfootball",
        ok=bool(rows),
        detail=f"weeks {weeks[0]}–{weeks[-1]} ({fetched} live, {cached} cached), {finals} finals",
        games=len(rows),
        finals=finals,
    )
    return rows, report


def write_field(data_dir: Path, schools: list[CatalogSchool], rows: list[dict], *, season: int) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)

    def dump(name: str, fieldnames: list[str], payload: list[dict]) -> None:
        with (data_dir / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(payload)

    dump(
        "teams.csv",
        ["team_id", "name", "district", "region", "classification", "association", "city", "lat", "lon"],
        [
            {
                "team_id": s.team_id,
                "name": s.name,
                "district": s.district,
                "region": s.region,
                "classification": s.classification,
                "association": s.association,
                "city": s.city,
                "lat": "",
                "lon": "",
            }
            for s in schools
        ],
    )
    dump(
        "games.csv",
        ["game_id", "week", "date", "home_id", "away_id", "home_score", "away_score", "district_game", "neutral"],
        [
            {
                **row,
                "home_score": "" if row.get("home_score") is None else row["home_score"],
                "away_score": "" if row.get("away_score") is None else row["away_score"],
                "district_game": str(bool(row.get("district_game"))).lower(),
                "neutral": str(bool(row.get("neutral"))).lower(),
            }
            for row in rows
        ],
    )
    dump(
        "priors.csv",
        ["team_id", "season", "rating"],
        [{"team_id": s.team_id, "season": season, "rating": prior_rating(s.name, s.division)} for s in schools],
    )
    for empty, fields in (
        ("roster_factors.csv", ["team_id", "season", "graduation_rate", "positional_turnover", "notes"]),
        ("panel_adjustments.csv", ["team_id", "season", "panel_rating", "weight", "notes"]),
    ):
        path = data_dir / empty
        if not path.exists():
            dump(empty, fields, [])


def run_ingest(
    *,
    data_dir: Path | str | None = None,
    write: bool = True,
    export_offline: bool = False,
    skip_maxpreps: bool = False,
    skip_smf: bool = False,
    persist_smf: bool = True,
    season: Optional[int] = None,
) -> IngestReport:
    season = season or _season()
    dest = Path(data_dir) if data_dir else PACKAGE_DATA
    schools = uil_schools()
    batches: list[list[dict]] = []
    sources: list[SourceReport] = []

    if not skip_maxpreps:
        rows, report = pull_maxpreps(schools, season=season)
        batches.append(rows)
        sources.append(report)
    if not skip_smf:
        rows, report = pull_smf(schools, season=season, persist=persist_smf)
        batches.append(rows)
        sources.append(report)

    merged = merge_game_rows(batches)
    pulled = now_central().isoformat()
    report = IngestReport(
        season=season,
        teams=len(schools),
        games=len(merged),
        finals=sum(1 for r in merged if r.get("home_score") is not None),
        sources=sources,
        pulled_at=pulled,
    )
    if write:
        write_field(dest, schools, merged, season=season)
        meta = {
            "pulled_at": pulled,
            "season": season,
            "teams": report.teams,
            "games": report.games,
            "finals": report.finals,
            "sources": [src.__dict__ for src in sources],
            "note": "Live Texas six-man results (UIL + TAPPS + TAIAO + others). Pages board refreshes via GitHub Actions cron.",
        }
        (dest / "ingest_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        report.wrote = str(dest)
    if export_offline:
        from sixman_rankings.live.service import LiveSeasonService, reset_service
        from sixman_rankings.offline import write_offline_bundle

        reset_service()
        out = Path(os.environ.get("SIXMAN_OFFLINE_DIR") or (ROOT / "web" / "public" / "offline"))
        service = LiveSeasonService.from_data_dir(dest) if dest != PACKAGE_DATA else LiveSeasonService.from_uil()
        service.last_result = report.summary()
        service.last_sync = now_central()
        service.provider_name = "live-ingest"
        write_offline_bundle(out, service=service)
        report.offline = str(out)
    return report


def rows_as_games(rows: list[dict]):
    from sixman_rankings.models import Game

    games = []
    for row in rows:
        games.append(
            Game(
                game_id=row["game_id"],
                week=int(row["week"]),
                date=str(row.get("date") or week_dates(int(row["week"]))),
                home_id=row["home_id"],
                away_id=row["away_id"],
                home_score=row.get("home_score"),
                away_score=row.get("away_score"),
                district_game=bool(row.get("district_game")),
                neutral=bool(row.get("neutral")),
            )
        )
    return games
