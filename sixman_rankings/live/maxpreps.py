"""Parse MaxPreps school schedule pages (``__NEXT_DATA__`` contests).

Adapted from sixmanmadness ``mp-core.ts`` packed-contest layout, without
cloning that app's UI. Used as the GHA-friendly live-score source.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Optional

from sixman_rankings.catalog import CatalogSchool
from sixman_rankings.smf import week_dates

NEXT_DATA = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(?P<json>.*?)</script>',
    re.I | re.S,
)
RESULT_CELL = re.compile(r"\b([WLT])\s+(\d{1,3})\s*[-–]\s*(\d{1,3})\b", re.I)
MD_ROW = re.compile(
    r"\|\s*(?P<when>\d{1,2}/\d{1,2}(?:/\d{2,4})?(?:\s+\d{1,2}:\d{2}\s*(?:am|pm)?)?)\s*"
    r"\|\s*(?P<opp>(?:vs\.?|@)\s+[^|]+)\s*"
    r"\|\s*(?P<result>[^|]*)\|",
    re.I,
)


@dataclass
class MaxPrepsGame:
    date: str
    week: int
    us_name: str
    opp_name: str
    us_score: Optional[int]
    opp_score: Optional[int]
    site: str  # home / away / neutral
    district: bool
    final: bool
    source_url: str = ""


def date_to_week(iso_date: str, *, season: int = 2026) -> int:
    """Map a calendar date onto the UIL week index (Week 0 Thursday = Aug 20)."""

    raw = (iso_date or "")[:10]
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        return 0
    week0_thu = date(season, 8, 20)
    if day < week0_thu:
        return 0
    return (day - week0_thu).days // 7


def _num(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _page_props(html: str) -> Optional[dict]:
    match = NEXT_DATA.search(html or "")
    if not match:
        return None
    try:
        data = json.loads(match.group("json"))
    except json.JSONDecodeError:
        return None
    props = data.get("props") if isinstance(data, dict) else None
    if not isinstance(props, dict):
        return None
    page = props.get("pageProps")
    return page if isinstance(page, dict) else None


def _packed_team(row: Any) -> Optional[dict]:
    if not isinstance(row, list) or len(row) < 15:
        return None
    name = str(row[14] or "").strip()
    if not name:
        return None
    ha = _num(row[11]) or 0
    site = "away" if ha == 1 else "neutral" if ha == 2 else "home"
    return {
        "name": name,
        "mascot": str(row[21] or "").strip() if len(row) > 21 else "",
        "city": str(row[15] or "").strip(),
        "score": _num(row[6]),
        "result": str(row[5] or "").upper() or None,
        "site": site,
        "district": (_num(row[12]) == 0),
        "is_us": bool(row[10]) if len(row) > 10 else False,
    }


def parse_contests(html: str, *, school_name: str, season: int = 2026) -> list[MaxPrepsGame]:
    """Read packed contests from a MaxPreps schedule page."""

    page = _page_props(html)
    contests = page.get("contests") if page else None
    if not isinstance(contests, list):
        return parse_schedule_table(html, school_name=school_name, season=season)

    want = re.sub(r"[^a-z0-9]+", "", school_name.lower())
    games: list[MaxPrepsGame] = []
    for raw in contests:
        if not isinstance(raw, list) or len(raw) < 12:
            continue
        stamp = str(raw[11] or "")
        if not stamp:
            continue
        iso = stamp[:10]
        us = _packed_team(raw[37] if len(raw) > 37 else None)
        opp = _packed_team(raw[38] if len(raw) > 38 else None)
        if us and want and re.sub(r"[^a-z0-9]+", "", us["name"].lower()) != want:
            if opp and re.sub(r"[^a-z0-9]+", "", opp["name"].lower()) == want:
                us, opp = opp, us
        if not us or not opp:
            continue
        us_score, opp_score = us["score"], opp["score"]
        final = us_score is not None and opp_score is not None
        games.append(
            MaxPrepsGame(
                date=iso,
                week=date_to_week(iso, season=season),
                us_name=us["name"],
                opp_name=opp["name"],
                us_score=us_score if final else None,
                opp_score=opp_score if final else None,
                site=us["site"],
                district=bool(us["district"] or opp["district"]),
                final=final,
            )
        )
    return games


def parse_schedule_table(text: str, *, school_name: str, season: int = 2026) -> list[MaxPrepsGame]:
    """Fallback for reader/markdown conversions of a schedule table."""

    games: list[MaxPrepsGame] = []
    for match in MD_ROW.finditer(text or ""):
        when = match.group("when").strip()
        opp_raw = match.group("opp").strip()
        result = match.group("result").strip()
        site = "away" if opp_raw.lower().startswith("@") else "home"
        opp = re.sub(r"^(?:vs\.?|@)\s+", "", opp_raw, flags=re.I)
        opp = re.sub(r"\s*\([^)]*\)\s*$", "", opp).strip()
        day = _md_date(when, season)
        if not day or not opp:
            continue
        scores = RESULT_CELL.search(result)
        us_score = opp_score = None
        final = False
        if scores:
            mark, a, b = scores.group(1).upper(), int(scores.group(2)), int(scores.group(3))
            # Cell is always "our score - their score" after W/L.
            us_score, opp_score = a, b
            if mark == "L" and a > b:
                us_score, opp_score = b, a
            final = True
        games.append(
            MaxPrepsGame(
                date=day,
                week=date_to_week(day, season=season),
                us_name=school_name,
                opp_name=opp,
                us_score=us_score,
                opp_score=opp_score,
                site=site,
                district="*" in result or "*" in opp_raw,
                final=final,
            )
        )
    return games


def _md_date(when: str, season: int) -> Optional[str]:
    m = re.match(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", when.strip())
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    year = season
    if m.group(3):
        y = int(m.group(3))
        year = y if y > 100 else 2000 + y
    elif month < 7:
        year = season + 1
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def games_to_rows(
    games: Iterable[MaxPrepsGame],
    schools: Iterable[CatalogSchool],
) -> list[dict]:
    """Keep catalog matchups (any association). Home/away follows MaxPreps site flags."""

    from sixman_rankings.catalog import slugify
    from sixman_rankings.smf import build_name_index, resolve_smf_name

    roster = list(schools)
    index = build_name_index(roster)
    by_id = {s.team_id: s for s in roster}
    rows: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    for game in games:
        us_id = resolve_smf_name(game.us_name, index)
        opp_id = resolve_smf_name(game.opp_name, index)
        if not us_id or not opp_id or us_id == opp_id:
            continue
        if game.site == "away":
            home_id, away_id = opp_id, us_id
            home_score, away_score = game.opp_score, game.us_score
        else:
            home_id, away_id = us_id, opp_id
            home_score, away_score = game.us_score, game.opp_score
        key = (tuple(sorted((home_id, away_id))), game.week)
        if key in seen:
            continue
        seen.add(key)
        home, away = by_id[home_id], by_id[away_id]
        district = game.district or home.district == away.district
        final = game.final and home_score is not None and away_score is not None
        rows.append(
            {
                "game_id": f"w{game.week:02d}-{slugify(home_id)}-{slugify(away_id)}",
                "week": game.week,
                "date": game.date or week_dates(game.week),
                "home_id": home_id,
                "away_id": away_id,
                "home_score": home_score if final else None,
                "away_score": away_score if final else None,
                "district_game": district,
                "neutral": game.site == "neutral",
                "source": "maxpreps",
            }
        )
    rows.sort(key=lambda r: (r["week"], r["date"], r["game_id"]))
    return rows


def parse_stamp(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
