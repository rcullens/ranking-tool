"""MaxPreps contest / markdown schedule parsing and ingest merge."""

from sixman_rankings.catalog import catalog_schools, maxpreps_schedule_urls, uil_schools
from sixman_rankings.live.ingest import merge_game_rows
from sixman_rankings.live.maxpreps import date_to_week, games_to_rows, parse_contests, parse_schedule_table


AQUILLA_HTML = """
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"contests":[
  [null,"g1",null,null,null,"",null,null,null,null,0,"2026-09-18T19:30:00",
   null,null,null,null,null,null,"https://example.test/game",null,null,null,
   null,null,null,null,null,null,null,"summary",null,null,null,null,null,null,null,
   ["id","sid","ssid","W 60-6",1,"W",60,false,false,false,true,0,1,"u","Aquilla","Aquilla"],
   ["id","sid","ssid","L 60-6",2,"L",6,false,false,false,false,1,1,"u","Kopperl","Kopperl"]
  ],
  [null,"g2",null,null,null,"",null,null,null,null,0,"2026-09-04T19:30:00",
   null,null,null,null,null,null,"https://example.test/game",null,null,null,
   null,null,null,null,null,null,null,"summary",null,null,null,null,null,null,null,
   ["id","sid","ssid","W 54-7",1,"W",54,false,false,false,true,0,1,"u","Aquilla","Aquilla"],
   ["id","sid","ssid","L 54-7",2,"L",7,false,false,false,false,1,1,"u","Calvert","Calvert"]
  ]
]}}}
</script>
"""

AQUILLA_MD = """
| Date/Time | Opponent | Result | Watch | Game Info |
| 8/28 8:00pm | vs First Baptist Christian | W 95-54 | | Box Score |
| 9/4 7:30pm | vs Calvert | W 54-7 | | Box Score |
| 9/10 7:30pm | @ Avalon | W 64-6 | | Box Score |
| 9/18 7:30pm | vs Kopperl | W 60-6 | | Box Score |
| 9/25 7:30pm | @ Jonesboro | | | Preview Game |
"""


def test_date_to_week_maps_2026_fridays():
    assert date_to_week("2026-08-21") == 0
    assert date_to_week("2026-08-28") == 1
    assert date_to_week("2026-09-10") == 3
    assert date_to_week("2026-09-18") == 4


def test_parse_contests_reads_both_scores():
    games = parse_contests(AQUILLA_HTML, school_name="Aquilla", season=2026)
    assert len(games) == 2
    kopperl = next(g for g in games if g.opp_name == "Kopperl")
    assert kopperl.final
    assert kopperl.us_score == 60
    assert kopperl.opp_score == 6
    assert kopperl.week == 4
    assert kopperl.site == "home"


def test_markdown_table_keeps_uil_and_tapps_on_row_convert():
    games = parse_schedule_table(AQUILLA_MD, school_name="Aquilla", season=2026)
    assert len(games) == 5
    rows = games_to_rows(games, catalog_schools())
    ids = {(r["home_id"], r["away_id"], r["week"]) for r in rows}
    assert ("aquilla", "calvert", 2) in ids
    assert ("avalon", "aquilla", 3) in ids
    assert ("aquilla", "kopperl", 4) in ids
    assert ("aquilla", "first-baptist-christian", 1) in ids
    kopperl = next(r for r in rows if r["away_id"] == "kopperl")
    assert kopperl["home_score"] == 60
    assert kopperl["away_score"] == 6


def test_merge_prefers_complete_maxpreps_over_one_sided_smf():
    smf = [
        {
            "game_id": "w04-aquilla-kopperl",
            "week": 4,
            "date": "2026-09-18",
            "home_id": "aquilla",
            "away_id": "kopperl",
            "home_score": 60,
            "away_score": None,
            "district_game": False,
            "neutral": False,
            "source": "smf",
        }
    ]
    mp = [
        {
            "game_id": "w04-aquilla-kopperl",
            "week": 4,
            "date": "2026-09-18",
            "home_id": "aquilla",
            "away_id": "kopperl",
            "home_score": 60,
            "away_score": 6,
            "district_game": False,
            "neutral": False,
            "source": "maxpreps",
        }
    ]
    merged = merge_game_rows([smf, mp])
    assert len(merged) == 1
    assert merged[0]["away_score"] == 6
    assert merged[0]["source"] == "maxpreps"


def test_aquilla_maxpreps_url_uses_cougars_slug():
    aquilla = next(s for s in uil_schools() if s.team_id == "aquilla")
    urls = maxpreps_schedule_urls(aquilla, season_path="26-27")
    assert any("/tx/aquilla/aquilla-cougars/football/26-27/schedule/" in u for u in urls)
