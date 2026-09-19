"""Score providers: JSON feed, webhook payload, and football-night replay.

sixmanfootball.com is the community scoreboard for Texas 6-man, but it sits
behind Cloudflare and has no public API. This module therefore:

* pulls any URL that serves our feed JSON (``SIXMAN_FEED_URL``),
* accepts the same JSON via ``POST /api/ingest``,
* and, for a running demo with no feed, replays held sample finals during
  the Thursday–Saturday window so the ranking list and graph move live.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

from sixman_rankings.live.names import build_alias_index, resolve_team_id
from sixman_rankings.models import Game, Team

USER_AGENT = "sixman-rankings/0.3 (+https://localhost; Texas 6-man live ingest)"


@dataclass
class FetchResult:
    games: list[Game]
    source: str
    ok: bool
    detail: str


def parse_feed_payload(payload: Any, teams: list[Team]) -> list[Game]:
    """Accept a list of game objects or ``{"games": [...]}``."""

    if isinstance(payload, dict):
        rows = payload.get("games") or payload.get("results") or []
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError("feed JSON must be a list or an object with a games array")

    index = build_alias_index(teams)
    known = {t.team_id for t in teams}
    parsed: list[Game] = []
    for i, raw in enumerate(rows):
        if not isinstance(raw, dict):
            continue
        home = raw.get("home_id") or raw.get("home") or raw.get("home_team") or ""
        away = raw.get("away_id") or raw.get("away") or raw.get("away_team") or ""
        home_id = home if home in known else resolve_team_id(str(home), index)
        away_id = away if away in known else resolve_team_id(str(away), index)
        if not home_id or not away_id:
            continue
        status = str(raw.get("status") or "final").lower()
        home_score = raw.get("home_score")
        away_score = raw.get("away_score")
        if status in {"upcoming", "scheduled", "preview"}:
            home_score = away_score = None
        if home_score is not None:
            home_score = int(home_score)
        if away_score is not None:
            away_score = int(away_score)
        week = int(raw.get("week") or 0)
        date = str(raw.get("date") or "")
        game_id = str(raw.get("game_id") or f"feed-{week}-{home_id}-{away_id}-{i}")
        parsed.append(
            Game(
                game_id=game_id,
                week=week,
                date=date,
                home_id=home_id,
                away_id=away_id,
                home_score=home_score,
                away_score=away_score,
                district_game=bool(raw.get("district_game") or False),
                neutral=bool(raw.get("neutral") or False),
            )
        )
    return parsed


def fetch_json_url(url: str, timeout: float = 12.0) -> Any:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("feed URL must be http or https")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    if "html" in ctype.lower() or body.lstrip().startswith(b"<"):
        raise RuntimeError("feed returned HTML instead of JSON (often a bot challenge)")
    return json.loads(body.decode("utf-8"))


def fetch_json_feed(url: str, teams: list[Team]) -> FetchResult:
    try:
        payload = fetch_json_url(url)
        games = parse_feed_payload(payload, teams)
        return FetchResult(games, url, True, f"pulled {len(games)} games")
    except urllib.error.HTTPError as exc:
        return FetchResult([], url, False, f"HTTP {exc.code} from feed")
    except Exception as exc:  # noqa: BLE001 — surface any transport/parse failure
        return FetchResult([], url, False, str(exc))


def default_feed_url() -> Optional[str]:
    url = (os.environ.get("SIXMAN_FEED_URL") or "").strip()
    return url or None
