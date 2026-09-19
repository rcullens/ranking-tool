"""Combined UIL + TAPPS + TAIAO field: First Baptist, Aquilla SOS, full ranks."""

from sixman_rankings.catalog import all_schools, uil_schools
from sixman_rankings.live.maxpreps import games_to_rows, parse_schedule_table
from sixman_rankings.pipeline import rank_season
from sixman_rankings.smf import build_name_index, games_to_rows as smf_to_rows, parse_smf_week_text, resolve_smf_name


def test_catalog_includes_every_private_association_and_first_baptist():
    schools = all_schools()
    by_assoc = {}
    for school in schools:
        by_assoc.setdefault(school.association, []).append(school)
    assert len(schools) > 159
    assert len(uil_schools()) >= 150
    assert len(by_assoc["TAPPS"]) >= 60
    assert "TAIAO" in by_assoc
    assert "TCAF" in by_assoc
    assert "TCAL" in by_assoc
    fbc = next(s for s in schools if s.team_id == "first-baptist-christian")
    assert fbc.name == "First Baptist Christian"
    assert fbc.association == "TAPPS"
    assert fbc.classification == "TAPPS DI"
    aquilla = next(s for s in schools if s.team_id == "aquilla")
    assert aquilla.association == "UIL"
    assert aquilla.district == "14-1A DI"


def test_smf_resolves_pasadena_first_baptist_and_skips_jv():
    index = build_name_index(all_schools())
    assert resolve_smf_name("Pasadena First Baptist", index) == "first-baptist-christian"
    assert resolve_smf_name("First Baptist Christian Warriors", index) == "first-baptist-christian"
    assert resolve_smf_name("Pasadena First Baptist JV", index) is None


def test_smf_week1_keeps_aquilla_vs_first_baptist():
    text = """
# 2026 Week 1 Scores
### Friday night lights
Aquilla
95
Pasadena First Baptist
54
"""
    games = parse_smf_week_text(text, 1)
    rows = smf_to_rows(games, all_schools())
    assert len(rows) == 1
    game = rows[0]
    assert {game["home_id"], game["away_id"]} == {"aquilla", "first-baptist-christian"}
    assert {game["home_score"], game["away_score"]} == {95, 54}


def test_aquilla_first_baptist_final_moves_power_and_sos():
    from sixman_rankings.models import Game, PriorRating, Team

    schools = {s.team_id: s for s in all_schools()}
    teams = [
        Team(
            team_id=s.team_id,
            name=s.name,
            district=s.district,
            region=s.region,
            classification=s.classification,
            city=s.city,
            association=s.association,
        )
        for s in (schools["aquilla"], schools["first-baptist-christian"], schools["calvert"])
    ]
    priors = [PriorRating(team.team_id, 2026, 1500) for team in teams]
    without = rank_season(teams, [], priors=priors, with_movement=False)
    with_game = rank_season(
        teams,
        [
            Game(
                "w01-aquilla-first-baptist-christian",
                1,
                "2026-08-28",
                "aquilla",
                "first-baptist-christian",
                95,
                54,
            )
        ],
        priors=priors,
        with_movement=False,
    )
    aq0 = next(r for r in without if r.team_id == "aquilla")
    aq1 = next(r for r in with_game if r.team_id == "aquilla")
    fbc1 = next(r for r in with_game if r.team_id == "first-baptist-christian")
    assert aq1.games_played == 1
    assert aq1.wins == 1
    assert fbc1.losses == 1
    assert aq1.power != aq0.power
    assert aq1.sos != aq0.sos


def test_maxpreps_tapps_vs_tapps_is_kept():
    md = """
| Date/Time | Opponent | Result | Watch | Game Info |
| 9/4 7:30pm | vs Founders Christian | W 48-12 | | Box Score |
"""
    games = parse_schedule_table(md, school_name="First Baptist Christian", season=2026)
    rows = games_to_rows(games, all_schools())
    assert len(rows) == 1
    assert {rows[0]["home_id"], rows[0]["away_id"]} == {
        "first-baptist-christian",
        "founders-christian",
    }
