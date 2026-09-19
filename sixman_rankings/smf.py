"""Parse SixManFootball week scoreboards (HTML or markdown conversion).

Adapted from sixmanmadness ``parse-smf-scores.ts`` pairing rules, without
cloning that app's UI. Cloudflare often blocks raw curl; saved week texts
under ``data/smf/`` are the reproducible source for the bundled season.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from sixman_rankings.catalog import NAME_ALIASES, CatalogSchool, slugify

SKIP_LINE = re.compile(
    r"^(?:"
    r"week\s+\d+"
    r"|texas six-man.*"
    r"|live\b.*"
    r"|final(?:/ff)?"
    r"|halftime"
    r"|\d+(st|nd|rd|th)\s+qtr"
    r"|yesterday at.*"
    r"|scores needed"
    r"|live scoreboard"
    r"|friday night lights"
    r"|saturday results"
    r"|thursday night football"
    r"|wednesday finals"
    r"|icon for.*"
    r"|performing security.*"
    r"|this website uses.*"
    r"|verification successful.*"
    r"|enable javascript.*"
    r"|ray id:.*"
    r"|performance and security.*"
    r"|#\s*20\d{2}.*"
    r"|20\d{2} week.*"
    r")$",
    re.I,
)

NAV_WEEKS = re.compile(r"^week\s+0\s+week\s+1", re.I)
RANK_NAME = re.compile(r"^(?:#(?P<rank>\d+)\s+)?(?P<name>.+?)\s*$")
SCORE_ONLY = re.compile(r"^\d{1,3}$")
LIVE_MARK = re.compile(r"halftime|\d+(st|nd|rd|th)\s+qtr|^live\b", re.I)
SECTION_HEAD = re.compile(
    r"friday|saturday|thursday|wednesday|scores needed|live scoreboard",
    re.I,
)

# Tokens that are never a school name.
NOT_A_TEAM = re.compile(
    r"^(scores|final|live|week|icon|ray|enable|this website|performing|verification)",
    re.I,
)


@dataclass
class SmfGame:
    week: int
    home: str
    away: str
    home_score: Optional[int]
    away_score: Optional[int]
    final: bool
    section: str


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def build_name_index(schools: Iterable[CatalogSchool]) -> dict[str, str]:
    """Map messy SMF labels onto catalog team_id."""

    index: dict[str, str] = {}
    for school in schools:
        keys = {
            school.name,
            f"{school.name} {school.mascot}",
            school.city,
            f"{school.city} {school.name}",
            school.name.replace("-", " "),
            school.name.replace("'", "").replace("'", ""),
            school.name.replace("Leveretts", "Leverett's"),
        }
        if school.name == "Springlake-Earth":
            keys.add("Springlake Earth")
        if school.name == "Valley":
            keys.update({"Turkey Valley", "Valley Patriots", "Turkey"})
        if school.name == "Three Way":
            keys.add("Three-Way")
        if school.name == "O'Donnell":
            keys.update({"ODonnell", "O Donnell", "O'Donnell Eagles"})
        keys.update(NAME_ALIASES.get(school.team_id, ()))
        for key in keys:
            n = _norm(key)
            if n:
                index[n] = school.team_id
    return index


def resolve_smf_name(raw: str, index: dict[str, str]) -> Optional[str]:
    text = re.sub(r"^#\d+\s+", "", (raw or "").strip())
    text = re.sub(r"\s+", " ", text)
    if not text:
        return None
    key = _norm(text)
    if key in index:
        return index[key]
    # Drop a trailing mascot / parenthetical and retry from the left.
    pieces = text.split()
    for end in range(len(pieces), 0, -1):
        cand = _norm(" ".join(pieces[:end]))
        if cand in index:
            return index[cand]
    # Prefix only — never "valley" inside "prairievalley".
    for alias, tid in sorted(index.items(), key=lambda kv: -len(kv[0])):
        if len(alias) < 6:
            continue
        if key.startswith(alias) or alias.startswith(key):
            return tid
    return None


def parse_smf_week_text(text: str, week: int) -> list[SmfGame]:
    """Pair consecutive team blocks from an SMF week page (HTML or markdown)."""

    html_games = _parse_html_matchups(text, week)
    if html_games:
        return html_games
    return _parse_markdown_blocks(text, week)


def _parse_html_matchups(html: str, week: int) -> list[SmfGame]:
    if "block-matchup" not in html and "contentRow--team" not in html:
        return []
    games: list[SmfGame] = []
    sections = re.split(r'<div class="block block--game-date">', html, flags=re.I)
    for section in sections[1:]:
        header_m = re.search(r'<h3 class="block-header">\s*([^<]+)', section, re.I)
        label = _decode(header_m.group(1)) if header_m else "Scores"
        matchups = re.split(r'<div class="block-matchup fauxBlockLink">', section, flags=re.I)
        for chunk in matchups[1:]:
            teams = re.split(r'<div class="contentRow contentRow--team">', chunk, flags=re.I)
            if len(teams) < 3:
                continue
            t1 = _html_team(teams[1])
            t2 = _html_team(teams[2])
            if not t1 or not t2:
                continue
            status_m = re.search(
                r'fauxBlockLink-blockLink"[^>]*>\s*([^<]+)', chunk, re.I
            ) or re.search(r"contentRow--time-remaining[\s\S]*?<div>\s*([^<]+)", chunk, re.I)
            status = _decode(status_m.group(1)) if status_m else ""
            upcoming = bool(re.match(r"upcoming", status, re.I))
            live = bool(LIVE_MARK.search(status))
            s1, s2 = t1[1], t2[1]
            if upcoming or live:
                s1 = s2 = None
            games.append(
                SmfGame(
                    week=week,
                    home=t1[0],
                    away=t2[0],
                    home_score=s1,
                    away_score=s2,
                    final=s1 is not None and s2 is not None and not live,
                    section=label,
                )
            )
    return games


def _html_team(chunk: str) -> Optional[tuple[str, Optional[int]]]:
    name_m = re.search(r'<a href="/teams/[^"]+">([^<]+)</a>', chunk, re.I)
    if not name_m:
        return None
    name = _decode(name_m.group(1))
    score_m = re.search(
        r'<div class="contentRow-score[^"]*">\s*([^<]*?)\s*</div>', chunk, re.I
    )
    raw = (score_m.group(1) if score_m else "").strip()
    score = int(raw) if raw.isdigit() else None
    return name, score


def _decode(value: str) -> str:
    return (
        value.replace("&amp;", "&")
        .replace("&nbsp;", " ")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
        .strip()
    )


def _parse_markdown_blocks(text: str, week: int) -> list[SmfGame]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().strip("*").strip()
        if not line:
            continue
        if NAV_WEEKS.match(line) or SKIP_LINE.match(line):
            continue
        if line.startswith("#") and not re.match(r"^#\d+", line):
            continue
        lines.append(line)

    games: list[SmfGame] = []
    entries: list[tuple[str, Optional[int], bool]] = []
    pending_name: Optional[str] = None
    live = False
    section = "Scores"

    def flush_pending() -> None:
        nonlocal pending_name
        if pending_name:
            entries.append((pending_name, None, live))
            pending_name = None

    def emit_section() -> None:
        nonlocal entries
        flush_pending()
        games.extend(_pair_entries(entries, week, section))
        entries = []

    for line in lines:
        if SECTION_HEAD.search(line) and not re.match(r"^#\d+", line):
            emit_section()
            section = line
            live = bool(re.search(r"live scoreboard", line, re.I))
            continue
        if LIVE_MARK.search(line):
            live = True
            continue
        if SCORE_ONLY.match(line):
            if pending_name:
                entries.append((pending_name, int(line), live))
                pending_name = None
            continue
        if NOT_A_TEAM.match(line):
            continue
        flush_pending()
        m = RANK_NAME.match(line)
        pending_name = m.group("name").strip() if m else line
        live = "live scoreboard" in section.lower()
    emit_section()
    return games


def _pair_entries(
    entries: list[tuple[str, Optional[int], bool]],
    week: int,
    section: str,
) -> list[SmfGame]:
    games: list[SmfGame] = []
    i = 0
    section_live = "live scoreboard" in section.lower()

    def emit(a, b) -> None:
        a_name, a_score, a_live = a
        b_name, b_score, b_live = b
        is_live = a_live or b_live or section_live
        final = a_score is not None and b_score is not None and not is_live
        games.append(
            SmfGame(
                week=week,
                home=a_name,
                away=b_name,
                home_score=a_score if not is_live else None,
                away_score=b_score if not is_live else None,
                final=final,
                section=section,
            )
        )

    while i + 1 < len(entries):
        # Markdown conversion sometimes inserts a TAPPS/out-of-state
        # leftover before a UIL pair (Balmorhea 76, Dell City).
        if i + 2 < len(entries):
            a, b, c = entries[i], entries[i + 1], entries[i + 2]
            if (
                a[1] is None
                and b[1] is not None
                and c[1] is None
                and _probably_non_uil(a[0])
            ):
                emit(b, c)
                i += 3
                continue
        emit(entries[i], entries[i + 1])
        i += 2
    return games


def _probably_non_uil(name: str) -> bool:
    return bool(
        re.search(
            r"christian|academy|homeschool|catholic|prep|charter|11-man|\bjv\b|,\s*nm",
            name,
            re.I,
        )
    )


def week_dates(week: int, *, season: int = 2026) -> str:
    """Friday of each 2026 UIL week (Week 0 = Aug 22)."""

    # Week 0 Friday 2026-08-21; subsequent Fridays +7.
    from datetime import date, timedelta

    start = date(season, 8, 21)
    day = start + timedelta(days=7 * week)
    return day.isoformat()


def games_to_rows(
    games: Iterable[SmfGame],
    schools: Iterable[CatalogSchool],
) -> list[dict]:
    """Keep catalog matchups; drop unresolved / JV / out-of-state sides."""

    roster = list(schools)
    index = build_name_index(roster)
    by_id = {s.team_id: s for s in roster}
    rows: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    for game in games:
        home_id = resolve_smf_name(game.home, index)
        away_id = resolve_smf_name(game.away, index)
        if not home_id or not away_id or home_id == away_id:
            continue
        key = (tuple(sorted((home_id, away_id))), game.week)
        if key in seen:
            continue
        seen.add(key)
        home = by_id[home_id]
        away = by_id[away_id]
        district = home.district == away.district
        gid = f"w{game.week:02d}-{slugify(home_id)}-{slugify(away_id)}"
        rows.append(
            {
                "game_id": gid,
                "week": game.week,
                "date": week_dates(game.week),
                "home_id": home_id,
                "away_id": away_id,
                "home_score": game.home_score if game.final else None,
                "away_score": game.away_score if game.final else None,
                "district_game": district,
                "neutral": False,
            }
        )
    rows.sort(key=lambda r: (r["week"], r["date"], r["game_id"]))
    return rows
