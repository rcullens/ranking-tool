"""Live ingest never invents district slates; incomplete SMF rows get MaxPreps scores."""

from sixman_rankings.live.ingest import merge_game_rows


def test_merge_does_not_invent_pairings():
    only = [
        {
            "game_id": "w01-aquilla-calvert",
            "week": 1,
            "date": "2026-08-28",
            "home_id": "aquilla",
            "away_id": "calvert",
            "home_score": 54,
            "away_score": 7,
            "district_game": False,
            "neutral": False,
            "source": "maxpreps",
        }
    ]
    merged = merge_game_rows([only, []])
    assert len(merged) == 1
    assert not any("dist-" in row["game_id"] for row in merged)
