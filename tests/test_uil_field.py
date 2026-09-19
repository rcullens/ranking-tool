"""Full UIL 1A six-man field: catalog size, Aquilla, no silent truncation."""

from sixman_rankings.catalog import uil_schools
from sixman_rankings.io import load_uil_dataset
from sixman_rankings.live.service import LiveSeasonService
from sixman_rankings.pipeline import rank_season


def test_catalog_is_the_full_uil_1a_field_and_includes_aquilla():
    schools = uil_schools()
    assert len(schools) >= 150
    aquilla = next(s for s in schools if s.team_id == "aquilla")
    assert aquilla.name == "Aquilla"
    assert aquilla.district == "14-1A DI"
    assert aquilla.uil_region == 4
    assert aquilla.classification == "1A DI"


def test_uil_rankings_list_every_team_from_first_to_last():
    teams, games, roster, panel, priors = load_uil_dataset()
    assert len(teams) == len(uil_schools())
    assert any(t.team_id == "aquilla" for t in teams)
    table = rank_season(
        teams, games, roster=roster, panel=panel, priors=priors, with_movement=False
    )
    assert len(table) == len(teams)
    assert [row.rank for row in table] == list(range(1, len(teams) + 1))
    aquilla = next(row for row in table if row.team_id == "aquilla")
    assert aquilla.rank >= 1
    assert aquilla.rank <= len(teams)


def test_offline_uil_snapshot_is_not_capped_at_twenty():
    service = LiveSeasonService.from_uil(start_week=99)
    table = service.rankings()
    assert len(table) == len(service.teams)
    assert len(table) > 20
    assert any(row.team_id == "aquilla" for row in table)
    assert [row.rank for row in table] == list(range(1, len(table) + 1))
