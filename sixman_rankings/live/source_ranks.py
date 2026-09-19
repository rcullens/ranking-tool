"""Public-board ranks from MaxPreps, SixManFootball, and DCTF.

Parsers follow rcullens/sixmanmadness (``multi-ranks.ts``, ``parse-smf.ts``,
``parse-dctf.ts``). UIL and TAPPS six-man boards are kept so First Baptist
Christian and other private programs appear next to our power ranks.
"""

from __future__ import annotations

import html as html_lib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional

from sixman_rankings.catalog import (
    SMF_WEEK1_DI,
    SMF_WEEK1_DII,
    catalog_schools,
    football_season_year,
    maxpreps_season_path,
    slugify,
)
from sixman_rankings.live.http import FetchError, fetch_with_fallback, post_json
from sixman_rankings.live.names import build_alias_index, resolve_team_id
from sixman_rankings.live.window import now_central
from sixman_rankings.models import Team

PACKAGE_DATA = Path(__file__).resolve().parents[1] / "data"
LAST_GOOD_PATH = PACKAGE_DATA / "source_ranks.json"

SOURCE_KEYS = ("maxpreps", "smf", "dctf")
SOURCE_LABELS = {
    "maxpreps": "MaxPreps",
    "smf": "SixManFootball",
    "dctf": "DCTF",
}

MAXPREPS_BOARDS = (
    ("uil-d1", "division-1a-6-man-1", "aeae15f7-798e-4385-b130-256db10f448a"),
    ("uil-d2", "division-1a-6-man-2", "0da3e2ac-f28f-4d2e-b601-bbad90d21e3d"),
    ("tapps-i", "division-tapps-i-6-man", "018d077c-1db0-45c9-a168-9be8851d941d"),
    ("tapps-ii", "division-tapps-ii-6-man", "96cb936e-833a-41df-b3e9-c07a257e20d6"),
    ("tapps-iii", "division-tapps-iii-6-man", "94b47bd2-b2e8-4068-bad0-b63f803d6569"),
)

DCTF_API = "https://www.texasfootball.com/api/rankings/hsGetTeamList"
DCTF_CLASS_DI = 33
DCTF_CLASS_DII = 330

SMF_SECTION_TO_BOARD = {
    "uil division i": "uil-d1",
    "uil division ii": "uil-d2",
    "tapps division i": "tapps-i",
    "tapps division ii": "tapps-ii",
    "tapps division iii": "tapps-iii",
}


@dataclass
class SourcePack:
    key: str
    label: str
    ok: bool
    week: str = "—"
    error: Optional[str] = None
    ranks: dict[str, int] = field(default_factory=dict)
    via: Optional[str] = None

    def meta(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "week": self.week,
            "label": self.label,
            "error": self.error,
            "count": len(self.ranks),
            "via": self.via,
        }


def decode_html(value: str) -> str:
    text = html_lib.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", text).strip()


def approx_ap_week(today: date | None = None) -> int:
    stamp = today or date.today()
    year = football_season_year(stamp)
    start = date(year, 8, 18)
    if stamp < start:
        return 1
    return min(15, ((stamp - start).days // 7) + 1)


def resolve_source_team(raw: str, index: dict[str, str]) -> Optional[str]:
    hit = resolve_team_id(raw, index)
    if hit:
        return hit
    cleaned = re.sub(r"\s+\S+$", "", raw or "").strip()
    if cleaned and cleaned != raw:
        hit = resolve_team_id(cleaned, index)
        if hit:
            return hit
    key = re.sub(r"[^a-z0-9]+", "", (raw or "").lower())
    if not key:
        return None
    hits = [(alias, tid) for alias, tid in index.items() if alias and (alias in key or key in alias)]
    if not hits:
        return None
    hits.sort(key=lambda item: len(item[0]), reverse=True)
    return hits[0][1]


def _index_from_teams(teams: Iterable[Team] | None = None) -> dict[str, str]:
    if teams is None:
        return build_alias_index(
            Team(
                team_id=s.team_id,
                name=s.name,
                district=s.district,
                region=s.region,
                classification=s.classification,
                association=s.association,
                city=s.city,
            )
            for s in catalog_schools()
        )
    return build_alias_index(teams)


def map_named_ranks(pairs: Iterable[tuple[str, int]], index: dict[str, str]) -> dict[str, int]:
    ranks: dict[str, int] = {}
    for name, rank in pairs:
        if not name or not rank or rank < 1:
            continue
        tid = resolve_source_team(name, index)
        if tid and tid not in ranks:
            ranks[tid] = int(rank)
    return ranks


def seed_smf_ranks() -> dict[str, int]:
    ranks: dict[str, int] = {}
    for i, name in enumerate(SMF_WEEK1_DI, start=1):
        ranks[slugify(name)] = i
    for i, name in enumerate(SMF_WEEK1_DII, start=1):
        ranks[slugify(name)] = i
    return ranks


def parse_maxpreps_division(html: str, index: dict[str, str] | None = None) -> dict[str, int]:
    match = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>',
        html,
        re.I,
    )
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    table = (
        data.get("props", {})
        .get("pageProps", {})
        .get("layoutProps", {})
        .get("tableData")
    )
    if not isinstance(table, list):
        return {}
    pairs: list[tuple[str, int]] = []
    for raw in table:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("schoolName") or "").strip()
        try:
            rank = int(raw.get("overallStandingPlacement"))
        except (TypeError, ValueError):
            continue
        if name and rank > 0:
            pairs.append((name, rank))
    return map_named_ranks(pairs, index or _index_from_teams())


def parse_smf_week_html(html: str, index: dict[str, str] | None = None) -> dict[str, int]:
    alias = index or _index_from_teams()
    ranks: dict[str, int] = {}
    parts = re.split(r'<h3 class="block-header">\s*', html, flags=re.I)
    for chunk in parts[1:]:
        end = chunk.lower().find("</h3>")
        if end < 0:
            continue
        title = decode_html(chunk[:end]).lower()
        if title not in SMF_SECTION_TO_BOARD:
            continue
        body = chunk[end + 5 :]
        for row in re.finditer(r'<tr class="dataList-row">([\s\S]*?)</tr>', body, re.I):
            cells = [
                decode_html(cell)
                for cell in re.findall(
                    r'<td class="dataList-cell[^"]*">([\s\S]*?)</td>',
                    row.group(1),
                    re.I,
                )
            ]
            if len(cells) < 2:
                continue
            poll = re.sub(r"[^0-9]", "", cells[0])
            name = cells[1].strip()
            if not poll or not name:
                continue
            tid = resolve_source_team(name, alias)
            if tid and tid not in ranks:
                ranks[tid] = int(poll)
    return ranks


def pick_latest_smf_week_path(hub_html: str, year: int) -> tuple[str, str]:
    cards = list(
        re.finditer(
            r'<a href="(/rankings/\d{4}/(?:week-\d+|pre-season)/)"\s+class="week-card\s+(status-[a-z]+)"',
            hub_html,
            re.I,
        )
    )
    scored = []
    for match in cards:
        path, status = match.group(1), match.group(2).lower()
        week_n = re.search(r"week-(\d+)", path, re.I)
        n = int(week_n.group(1)) if week_n else 0
        status_score = 300 if status == "status-new" else 200 if status == "status-final" else 0
        scored.append((status_score + n, path, n))
    if not scored:
        return f"/rankings/{year}/week-1/", "Week 1"
    scored.sort(reverse=True)
    _, path, n = scored[0]
    if "pre-season" in path:
        week = "Pre-Season"
    elif n:
        week = f"Week {n}"
    else:
        week = "Rankings"
    return path, week


def parse_dctf_grid_html(html: str, index: dict[str, str] | None = None) -> dict[str, int]:
    alias = index or _index_from_teams()
    ranks: dict[str, int] = {}
    for match in re.finditer(
        r'<a href="/team/[^"]+" class="c-member-grid-row">([\s\S]*?)</a>',
        html,
        re.I,
    ):
        body = match.group(1)
        rank_m = re.search(r"c-member-grid-rank[^>]*>\s*([^<]+)", body, re.I)
        poll = re.sub(r"[^0-9]", "", rank_m.group(1) if rank_m else "")
        if not poll:
            continue
        no_logo = re.sub(
            r'<span class="c-member-grid-team-logo">[\s\S]*?</span>',
            "",
            body,
            flags=re.I,
        )
        cols = [
            decode_html(col)
            for col in re.findall(
                r'<div class="c-member-grid-col">([\s\S]*?)</div>',
                no_logo,
                re.I,
            )
        ]
        if not cols:
            continue
        school = re.sub(r"^\d+\.\s*", "", cols[0]).strip()
        tid = resolve_source_team(school, alias)
        if tid and tid not in ranks:
            ranks[tid] = int(poll)
    return ranks


def parse_dctf_article_html(html: str, index: dict[str, str] | None = None) -> dict[str, int]:
    alias = index or _index_from_teams()
    ranks: dict[str, int] = {}
    headings = (
        r"CLASS\s+1A\s+DIVISION\s+I\b",
        r"CLASS\s+1A\s+DIVISION\s+II\b",
        r"PRIVATE\s+SCHOOLS\s*(?:&mdash;|—|-)\s*6-MAN",
    )
    for heading in headings:
        start = re.search(heading, html, re.I)
        if not start:
            continue
        slice_html = html[start.start() : start.start() + 8000]
        table = re.search(r"<table[\s\S]*?</table>", slice_html, re.I)
        if not table:
            continue
        for tr in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", table.group(0), re.I):
            th = re.search(r"<th[^>]*>\s*(\d+)\s*</th>", tr.group(1), re.I)
            td = re.search(r"<td[^>]*>\s*([\s\S]*?)</td>", tr.group(1), re.I)
            if not th or not td:
                continue
            poll = int(th.group(1))
            cell = decode_html(td.group(1))
            name = re.sub(r"\([^)]*\)\s*$", "", cell).strip()
            tid = resolve_source_team(name, alias)
            if tid and tid not in ranks:
                ranks[tid] = poll
    return ranks


def dctf_article_candidates(year: int, week: int) -> list[str]:
    known = {
        1: f"https://www.texasfootball.com/article/{year}/08/24/official-week-1-txhsfb-rankings",
        2: f"https://www.texasfootball.com/article/{year}/08/31/official-txhsfb-ap-week-2-rankings-powered-by-dctx",
        3: f"https://www.texasfootball.com/article/{year}/09/07/official-txhsfb-ap-week-3-rankings-powered-by-dctx",
        4: f"https://www.texasfootball.com/article/{year}/09/14/official-txhsfb-ap-week-4-rankings-powered-by-dctx",
        5: f"https://www.texasfootball.com/article/{year}/09/21/official-txhsfb-ap-week-5-rankings-powered-by-dctx",
        6: f"https://www.texasfootball.com/article/{year}/09/28/official-txhsfb-ap-week-6-rankings-powered-by-dctx",
    }
    urls: list[str] = []
    for w in range(week, 0, -1):
        if w in known:
            urls.append(known[w])
        else:
            urls.append(
                f"https://www.texasfootball.com/article/{year}/09/official-txhsfb-ap-week-{w}-rankings-powered-by-dctx"
            )
    return urls


def _unwrap_dctf_payload(raw: Any) -> str:
    envelope = raw
    if isinstance(raw, dict) and isinstance(raw.get("d"), str):
        try:
            envelope = json.loads(raw["d"])
        except json.JSONDecodeError as exc:
            raise FetchError("DCTF rankings API returned invalid JSON") from exc
    if not isinstance(envelope, dict) or not envelope.get("success"):
        raise FetchError("DCTF rankings API returned no data")
    data = envelope.get("data")
    if not isinstance(data, str):
        raise FetchError("DCTF rankings API returned no HTML")
    return data


def pull_maxpreps(index: dict[str, str], *, season: Optional[int] = None) -> SourcePack:
    path = maxpreps_season_path(season)
    ranks: dict[str, int] = {}
    errors: list[str] = []
    via = None
    for board_id, slug, state_id in MAXPREPS_BOARDS:
        url = f"https://www.maxpreps.com/tx/football/{path}/division/{slug}/?statedivisionid={state_id}"
        try:
            html, source = fetch_with_fallback(url, referer="https://www.maxpreps.com/")
            parsed = parse_maxpreps_division(html, index)
            ranks.update(parsed)
            via = source
            if not parsed:
                errors.append(f"{board_id} empty")
        except FetchError as exc:
            errors.append(f"{board_id}: {exc}")
    if ranks:
        return SourcePack("maxpreps", SOURCE_LABELS["maxpreps"], True, "—", None, ranks, via)
    return SourcePack(
        "maxpreps",
        SOURCE_LABELS["maxpreps"],
        False,
        "—",
        "; ".join(errors) or "No MaxPreps division tables posted yet.",
        {},
        via,
    )


def pull_smf(index: dict[str, str], *, season: Optional[int] = None) -> SourcePack:
    year = season or football_season_year()
    hub = f"https://sixmanfootball.com/rankings/{year}/"
    try:
        hub_html, _ = fetch_with_fallback(hub, referer="https://sixmanfootball.com/")
        rel, week = pick_latest_smf_week_path(hub_html, year)
        week_url = f"https://sixmanfootball.com{rel}"
        html, via = fetch_with_fallback(week_url, referer=hub)
        ranks = parse_smf_week_html(html, index)
        if ranks:
            return SourcePack("smf", SOURCE_LABELS["smf"], True, week, None, ranks, via)
        return SourcePack(
            "smf",
            SOURCE_LABELS["smf"],
            False,
            week,
            "SixManFootball page had no UIL/TAPPS tables.",
            {},
            via,
        )
    except FetchError as exc:
        return SourcePack("smf", SOURCE_LABELS["smf"], False, "—", str(exc), {})


def pull_dctf(index: dict[str, str], *, season: Optional[int] = None) -> SourcePack:
    year = season or football_season_year()
    week_n = approx_ap_week()
    week_label = f"Week {week_n}"
    ranks: dict[str, int] = {}
    try:
        for class_id in (DCTF_CLASS_DI, DCTF_CLASS_DII):
            raw = post_json(
                DCTF_API,
                {"weekId": -1, "classConfTagId": class_id, "currentWeek": True},
                referer="https://www.texasfootball.com/rankings/",
            )
            ranks.update(parse_dctf_grid_html(_unwrap_dctf_payload(raw), index))
        if ranks:
            return SourcePack("dctf", SOURCE_LABELS["dctf"], True, week_label, None, ranks, "api")
    except FetchError:
        ranks = {}

    last_err = "No DCTF AP article found."
    for url in dctf_article_candidates(year, week_n):
        try:
            html, via = fetch_with_fallback(
                url, referer="https://www.texasfootball.com/rankings/"
            )
            parsed = parse_dctf_article_html(html, index)
            week_m = re.search(r"Week\s+(\d+)\s+statewide", html, re.I) or re.search(
                r"week-(\d+)", url, re.I
            )
            label = f"Week {week_m.group(1)}" if week_m else week_label
            if parsed:
                return SourcePack("dctf", SOURCE_LABELS["dctf"], True, label, None, parsed, via)
            last_err = "AP article had no 1A / private 6-man tables."
        except FetchError as exc:
            last_err = str(exc)
    return SourcePack("dctf", SOURCE_LABELS["dctf"], False, week_label, last_err, {})


def pull_live_packs(
    teams: Iterable[Team] | None = None,
    *,
    season: Optional[int] = None,
) -> dict[str, SourcePack]:
    index = _index_from_teams(teams)
    return {
        "maxpreps": pull_maxpreps(index, season=season),
        "smf": pull_smf(index, season=season),
        "dctf": pull_dctf(index, season=season),
    }


def empty_pack(key: str, error: str | None = None) -> SourcePack:
    return SourcePack(key, SOURCE_LABELS[key], False, "—", error, {})


def packs_from_payload(payload: dict[str, Any]) -> dict[str, SourcePack]:
    sources = payload.get("sources") or {}
    rows = payload.get("rows") or []
    packs: dict[str, SourcePack] = {}
    for key in SOURCE_KEYS:
        meta = sources.get(key) or {}
        ranks = {
            row["team_id"]: int(row[key])
            for row in rows
            if row.get("team_id") and row.get(key) is not None
        }
        packs[key] = SourcePack(
            key=key,
            label=meta.get("label") or SOURCE_LABELS[key],
            ok=bool(meta.get("ok") and ranks),
            week=str(meta.get("week") or "—"),
            error=meta.get("error"),
            ranks=ranks,
            via=meta.get("via"),
        )
    return packs


def merge_packs(
    live: dict[str, SourcePack],
    cached: dict[str, SourcePack],
    *,
    seed_smf: bool = True,
) -> dict[str, SourcePack]:
    merged: dict[str, SourcePack] = {}
    for key in SOURCE_KEYS:
        incoming = live.get(key)
        previous = cached.get(key)
        if incoming and incoming.ok and incoming.ranks:
            merged[key] = incoming
        elif previous and previous.ranks:
            keep = SourcePack(
                key,
                SOURCE_LABELS[key],
                previous.ok,
                previous.week,
                incoming.error if incoming and not incoming.ok else previous.error,
                dict(previous.ranks),
                previous.via,
            )
            merged[key] = keep
        elif key == "smf" and seed_smf:
            merged[key] = SourcePack(
                "smf",
                SOURCE_LABELS["smf"],
                False,
                "Week 1",
                (incoming.error if incoming else None) or "Using SixManFootball Week 1 seed.",
                seed_smf_ranks(),
                "seed",
            )
        else:
            merged[key] = incoming or previous or empty_pack(key)
    return merged


def load_last_good(path: Path | str | None = None) -> dict[str, SourcePack]:
    dest = Path(path) if path else LAST_GOOD_PATH
    if not dest.exists():
        return {}
    try:
        return packs_from_payload(json.loads(dest.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError, KeyError):
        return {}


def _delta(ours: Optional[int], theirs: Optional[int]) -> Optional[int]:
    if ours is None or theirs is None:
        return None
    return ours - theirs


def compare_rows(
    teams: Iterable[Team],
    our_ranks: dict[str, int],
    packs: dict[str, SourcePack],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for team in teams:
        ours = our_ranks.get(team.team_id)
        mp = packs.get("maxpreps").ranks.get(team.team_id) if packs.get("maxpreps") else None
        smf = packs.get("smf").ranks.get(team.team_id) if packs.get("smf") else None
        dctf = packs.get("dctf").ranks.get(team.team_id) if packs.get("dctf") else None
        rows.append(
            {
                "team_id": team.team_id,
                "name": team.name,
                "classification": team.classification,
                "association": getattr(team, "association", None) or "UIL",
                "district": team.district,
                "region": team.region,
                "our_rank": ours,
                "maxpreps": mp,
                "smf": smf,
                "dctf": dctf,
                "delta_maxpreps": _delta(ours, mp),
                "delta_smf": _delta(ours, smf),
                "delta_dctf": _delta(ours, dctf),
            }
        )
    rows.sort(
        key=lambda row: (
            row["our_rank"] is None,
            row["our_rank"] if row["our_rank"] is not None else 10**9,
            row["name"],
        )
    )
    return rows


def build_payload(
    teams: Iterable[Team],
    our_ranks: dict[str, int],
    packs: dict[str, SourcePack],
    *,
    week: int | None = None,
    pulled_at: str | None = None,
) -> dict[str, Any]:
    roster = list(teams)
    return {
        "week": week,
        "pulled_at": pulled_at or now_central().isoformat(),
        "note": (
            "External ranks are each source's published board (MaxPreps division "
            "standing; SMF / DCTF polls). Delta = our statewide rank minus theirs. "
            "NR / — means that source has not listed the team."
        ),
        "sources": {key: (packs.get(key) or empty_pack(key)).meta() for key in SOURCE_KEYS},
        "rows": compare_rows(roster, our_ranks, packs),
    }


def save_last_good(payload: dict[str, Any], path: Path | str | None = None) -> Path:
    dest = Path(path) if path else LAST_GOOD_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def our_ranks_from_service(service) -> dict[str, int]:
    return {row.team_id: row.rank for row in service.rankings()}


def should_pull_sources(explicit: Optional[bool] = None) -> bool:
    if explicit is not None:
        return explicit
    env = os.environ.get("SIXMAN_PULL_SOURCE_RANKS")
    if env is not None:
        return env.strip() not in {"0", "false", "False"}
    return False


def source_ranks_payload(
    service,
    *,
    pull: Optional[bool] = None,
    last_good_path: Path | str | None = None,
    persist: bool = True,
    season: Optional[int] = None,
) -> dict[str, Any]:
    cached = load_last_good(last_good_path)
    live: dict[str, SourcePack] = {}
    if should_pull_sources(pull):
        try:
            live = pull_live_packs(service.teams, season=season or service.season)
        except Exception as exc:  # noqa: BLE001
            live = {key: empty_pack(key, str(exc)) for key in SOURCE_KEYS}
    packs = merge_packs(live, cached, seed_smf=True)
    payload = build_payload(
        service.teams,
        our_ranks_from_service(service),
        packs,
        week=service.current_week(),
    )
    if persist and any((packs.get(key) and packs[key].ranks) for key in SOURCE_KEYS):
        try:
            save_last_good(payload, last_good_path)
        except OSError:
            pass
    return payload
