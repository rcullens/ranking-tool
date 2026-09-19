#!/usr/bin/env python3
"""Build bundled UIL 1A teams/games/priors from the sixmanmadness catalog + SMF weeks."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sixman_rankings.catalog import prior_rating, uil_schools
from sixman_rankings.smf import parse_smf_week_text, games_to_rows, week_dates

DATA = ROOT / "sixman_rankings" / "data"
SMF_DIR = DATA / "smf"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def scheduled_district_games(existing: list[dict], *, start_week: int = 5, weeks: int = 4) -> list[dict]:
    """Fill remaining district pairings so every club has a published slate."""

    schools = uil_schools()
    played: set[tuple[str, str]] = set()
    for row in existing:
        played.add(tuple(sorted((row["home_id"], row["away_id"]))))

    by_district: dict[str, list] = defaultdict(list)
    for school in schools:
        by_district[school.district].append(school)

    extras: list[dict] = []
    week = start_week
    for district, members in sorted(by_district.items()):
        members = sorted(members, key=lambda s: s.team_id)
        pairs = []
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                key = tuple(sorted((a.team_id, b.team_id)))
                if key not in played:
                    pairs.append((a, b))
        for offset, (home, away) in enumerate(pairs):
            w = start_week + (offset % weeks)
            extras.append(
                {
                    "game_id": f"w{w:02d}-dist-{home.team_id}-{away.team_id}",
                    "week": w,
                    "date": week_dates(w),
                    "home_id": home.team_id,
                    "away_id": away.team_id,
                    "home_score": None,
                    "away_score": None,
                    "district_game": True,
                    "neutral": False,
                }
            )
    extras.sort(key=lambda r: (r["week"], r["game_id"]))
    return extras


def main() -> int:
    schools = uil_schools()
    parsed = []
    for path in sorted(SMF_DIR.glob("week-*.md")):
        week = int(path.stem.split("-")[1])
        parsed.extend(parse_smf_week_text(path.read_text(encoding="utf-8"), week))
    rows = games_to_rows(parsed, schools)
    rows.extend(scheduled_district_games(rows))

    write_csv(
        DATA / "teams.csv",
        ["team_id", "name", "district", "region", "classification", "city", "lat", "lon"],
        [
            {
                "team_id": s.team_id,
                "name": s.name,
                "district": s.district,
                "region": s.region,
                "classification": s.classification,
                "city": s.city,
                "lat": "",
                "lon": "",
            }
            for s in schools
        ],
    )
    write_csv(
        DATA / "games.csv",
        ["game_id", "week", "date", "home_id", "away_id", "home_score", "away_score", "district_game", "neutral"],
        [
            {
                **row,
                "home_score": "" if row["home_score"] is None else row["home_score"],
                "away_score": "" if row["away_score"] is None else row["away_score"],
                "district_game": str(row["district_game"]).lower(),
                "neutral": "false",
            }
            for row in rows
        ],
    )
    write_csv(
        DATA / "priors.csv",
        ["team_id", "season", "rating"],
        [
            {
                "team_id": s.team_id,
                "season": 2026,
                "rating": prior_rating(s.name, s.division),
            }
            for s in schools
        ],
    )
    write_csv(
        DATA / "roster_factors.csv",
        ["team_id", "season", "graduation_rate", "positional_turnover", "notes"],
        [],
    )
    write_csv(
        DATA / "panel_adjustments.csv",
        ["team_id", "season", "panel_rating", "weight", "notes"],
        [],
    )
    finals = sum(1 for r in rows if r["home_score"] is not None)
    print(
        f"Wrote {len(schools)} UIL teams, {len(rows)} games "
        f"({finals} finals) → {DATA}"
    )
    aquilla = next(s for s in schools if s.team_id == "aquilla")
    print(f"Aquilla: {aquilla.district} {aquilla.classification} region={aquilla.region}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
