"""CSV / JSON loaders for the ranking pipeline."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Optional

from sixman_rankings.models import (
    Game,
    PanelAdjustment,
    PriorRating,
    RosterFactor,
    Team,
)

PACKAGE_DATA = Path(__file__).resolve().parent / "data"


def _as_path(path: str | Path) -> Path:
    return Path(path).expanduser()


def _blank(value: Optional[str]) -> bool:
    return value is None or str(value).strip() == ""


def _opt_int(value: Optional[str]) -> Optional[int]:
    if _blank(value):
        return None
    return int(value)


def _opt_float(value: Optional[str]) -> Optional[float]:
    if _blank(value):
        return None
    return float(value)


def _as_bool(value: Optional[str]) -> bool:
    if _blank(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def load_teams_csv(path: str | Path) -> list[Team]:
    teams: list[Team] = []
    with _as_path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            teams.append(
                Team(
                    team_id=row["team_id"].strip(),
                    name=row["name"].strip(),
                    district=row["district"].strip(),
                    region=row["region"].strip(),
                    classification=(row.get("classification") or "1A").strip(),
                    city=(row.get("city") or "").strip(),
                    lat=_opt_float(row.get("lat")),
                    lon=_opt_float(row.get("lon")),
                )
            )
    return teams


def load_games_csv(path: str | Path) -> list[Game]:
    games: list[Game] = []
    with _as_path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            games.append(
                Game(
                    game_id=row["game_id"].strip(),
                    week=int(row["week"]),
                    date=row.get("date", "").strip(),
                    home_id=row["home_id"].strip(),
                    away_id=row["away_id"].strip(),
                    home_score=_opt_int(row.get("home_score")),
                    away_score=_opt_int(row.get("away_score")),
                    district_game=_as_bool(row.get("district_game")),
                    neutral=_as_bool(row.get("neutral")),
                )
            )
    return games


def load_roster_csv(path: str | Path) -> list[RosterFactor]:
    rows: list[RosterFactor] = []
    with _as_path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                RosterFactor(
                    team_id=row["team_id"].strip(),
                    season=int(row["season"]),
                    graduation_rate=float(row.get("graduation_rate") or 0),
                    positional_turnover=float(row.get("positional_turnover") or 0),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return rows


def load_panel_csv(path: str | Path) -> list[PanelAdjustment]:
    rows: list[PanelAdjustment] = []
    with _as_path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                PanelAdjustment(
                    team_id=row["team_id"].strip(),
                    season=int(row["season"]),
                    panel_rating=float(row["panel_rating"]),
                    weight=float(row.get("weight") or 1),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return rows


def load_priors_csv(path: str | Path) -> list[PriorRating]:
    rows: list[PriorRating] = []
    with _as_path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                PriorRating(
                    team_id=row["team_id"].strip(),
                    season=int(row["season"]),
                    rating=float(row["rating"]),
                )
            )
    return rows


def _objects_from_json(path: str | Path, key: Optional[str]) -> list[dict]:
    payload = json.loads(_as_path(path).read_text(encoding="utf-8"))
    if key and isinstance(payload, dict):
        payload = payload[key]
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list (or an object with key {key!r})")
    return payload


def load_teams_json(path: str | Path) -> list[Team]:
    return [Team(**row) for row in _objects_from_json(path, "teams")]


def load_games_json(path: str | Path) -> list[Game]:
    return [Game(**row) for row in _objects_from_json(path, "games")]


def load_dataset(
    *,
    teams_path: str | Path,
    games_path: str | Path,
    roster_path: Optional[str | Path] = None,
    panel_path: Optional[str | Path] = None,
    priors_path: Optional[str | Path] = None,
) -> tuple[
    list[Team],
    list[Game],
    list[RosterFactor],
    list[PanelAdjustment],
    list[PriorRating],
]:
    """Load a complete input set from CSV or JSON (suffix-selected)."""

    def pick(path: str | Path, csv_fn, json_fn):
        suffix = _as_path(path).suffix.lower()
        if suffix == ".json":
            return json_fn(path)
        return csv_fn(path)

    teams = pick(teams_path, load_teams_csv, load_teams_json)
    games = pick(games_path, load_games_csv, load_games_json)
    roster: list[RosterFactor] = []
    panel: list[PanelAdjustment] = []
    priors: list[PriorRating] = []
    if roster_path:
        roster = pick(roster_path, load_roster_csv, lambda p: [RosterFactor(**r) for r in _objects_from_json(p, "roster")])
    if panel_path:
        panel = pick(panel_path, load_panel_csv, lambda p: [PanelAdjustment(**r) for r in _objects_from_json(p, "panel")])
    if priors_path:
        priors = pick(priors_path, load_priors_csv, lambda p: [PriorRating(**r) for r in _objects_from_json(p, "priors")])
    return teams, games, roster, panel, priors


def sample_data_dir() -> Path:
    """Directory of bundled synthetic Texas 6-man fixtures."""

    return PACKAGE_DATA


def load_sample_dataset() -> tuple[
    list[Team],
    list[Game],
    list[RosterFactor],
    list[PanelAdjustment],
    list[PriorRating],
]:
    data = sample_data_dir()
    return load_dataset(
        teams_path=data / "teams.csv",
        games_path=data / "games.csv",
        roster_path=data / "roster_factors.csv",
        panel_path=data / "panel_adjustments.csv",
        priors_path=data / "priors.csv",
    )


def iter_ranked_dicts(rows, **kwargs) -> Iterable[dict]:
    from sixman_rankings.export import ranked_record

    for row in rows:
        yield ranked_record(row, **kwargs)
