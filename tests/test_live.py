"""Live ingest, football window, replay, and compare series."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sixman_rankings.live.merge import hide_scores_after, merge_finals
from sixman_rankings.live.names import build_alias_index, resolve_team_id
from sixman_rankings.live.providers import parse_feed_payload
from sixman_rankings.live.service import LiveSeasonService
from sixman_rankings.live.window import in_football_window
from sixman_rankings.models import Game, Team


def test_football_window_covers_thu_fri_sat_and_late_sunday():
    tz = ZoneInfo("America/Chicago")
    assert in_football_window(datetime(2026, 9, 17, 19, 0, tzinfo=tz))
    assert in_football_window(datetime(2026, 9, 18, 21, 0, tzinfo=tz))
    assert in_football_window(datetime(2026, 9, 19, 16, 0, tzinfo=tz))
    assert in_football_window(datetime(2026, 9, 20, 1, 0, tzinfo=tz))
    assert not in_football_window(datetime(2026, 9, 16, 19, 0, tzinfo=tz))
    assert not in_football_window(datetime(2026, 9, 17, 8, 0, tzinfo=tz))


def test_name_resolver_maps_display_names():
    teams = [Team("borden-county", "Borden County", "8-1A DI", "west-texas", city="Gail")]
    index = build_alias_index(teams)
    assert resolve_team_id("Borden County", index) == "borden-county"
    assert resolve_team_id("Gail Borden County Coyotes", index) == "borden-county"


def test_json_feed_parses_and_merge_updates_scheduled_game():
    teams = [
        Team("borden-county", "Borden County", "D", "west"),
        Team("rankin", "Rankin", "D", "west"),
    ]
    scheduled = Game("g1", 5, "2026-09-18", "borden-county", "rankin")
    payload = {
        "games": [
            {
                "week": 5,
                "home": "Borden County",
                "away": "Rankin",
                "home_score": 48,
                "away_score": 22,
                "status": "final",
            }
        ]
    }
    incoming = parse_feed_payload(payload, teams)
    merged, n = merge_finals([scheduled], incoming)
    assert n == 1
    assert merged[0].is_final
    assert merged[0].home_score == 48


def test_replay_releases_held_finals_and_moves_week():
    service = LiveSeasonService.from_demo(start_week=4)
    assert service.current_week() == 4
    held_before = len(service._held)
    assert held_before > 0
    scheduled_before = sum(1 for g in service.games if not g.is_final)
    status = service.sync(force_replay=True)
    assert service.updates_last_sync > 0
    scheduled_after = sum(1 for g in service.games if not g.is_final)
    assert scheduled_after < scheduled_before
    assert status.current_week >= 4


def test_compare_series_includes_selected_teams():
    service = LiveSeasonService.from_demo(start_week=4)
    data = service.compare_series(["borden-county", "marathon"], metric="power")
    assert data["weeks"][0] == 0
    assert data["current_week"] == 4
    names = {s["name"] for s in data["series"]}
    assert names == {"Borden County", "Marathon"}
    assert all(p["value"] is not None for p in data["series"][0]["points"])


def test_hide_scores_after_keeps_early_weeks():
    games = [
        Game("a", 3, "d", "h", "a", 20, 10),
        Game("b", 6, "d", "h", "a", 40, 14),
    ]
    trimmed, held = hide_scores_after(games, 4)
    assert trimmed[0].is_final
    assert not trimmed[1].is_final
    assert held["b"] == (40, 14)
