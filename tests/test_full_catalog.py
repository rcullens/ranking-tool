"""Full Texas six-man catalog: all associations, cross-association games."""

import json
from pathlib import Path

from sixman_rankings.catalog import catalog_schools, uil_schools
from sixman_rankings.classify import classification_matches
from sixman_rankings.io import load_uil_dataset
from sixman_rankings.live.maxpreps import games_to_rows, parse_schedule_table
from sixman_rankings.live.service import LiveSeasonService
from sixman_rankings.pipeline import rank_season
from sixman_rankings.smf import build_name_index, resolve_smf_name

from tests.test_maxpreps import AQUILLA_MD


def test_catalog_imports_every_association_and_first_baptist():
    schools = catalog_schools()
    by_assoc: dict[str, int] = {}
    for school in schools:
        by_assoc[school.association] = by_assoc.get(school.association, 0) + 1
    assert by_assoc["UIL"] == 159
    assert by_assoc["TAPPS"] >= 70
    assert by_assoc["TAIAO"] >= 50
    assert by_assoc["TCAF"] >= 7
    assert by_assoc["TCAL"] >= 1
    assert by_assoc["IND"] >= 3
    assert len(schools) > 250
    assert uil_schools() == schools
    ids = {s.team_id for s in schools}
    assert "aquilla" in ids
    assert "first-baptist-christian" in ids
    fba = next(s for s in schools if s.team_id == "first-baptist-christian")
    assert fba.association == "TAPPS"
    assert fba.classification == "TAPPS DI"


def test_bare_di_filter_stays_uil_only():
    schools = catalog_schools()
    di = [s for s in schools if classification_matches(s.classification, "DI")]
    dii = [s for s in schools if classification_matches(s.classification, "DII")]
    assert all(s.association == "UIL" for s in di)
    assert all(s.association == "UIL" for s in dii)
    assert len(di) + len(dii) == 159
    assert not any(s.team_id == "first-baptist-christian" for s in di)


def test_aquilla_vs_first_baptist_counts():
    games = parse_schedule_table(AQUILLA_MD, school_name="Aquilla", season=2026)
    rows = games_to_rows(games, catalog_schools())
    ids = {(r["home_id"], r["away_id"], r["week"]) for r in rows}
    assert ("aquilla", "first-baptist-christian", 1) in ids
    fba = next(r for r in rows if r["away_id"] == "first-baptist-christian")
    assert fba["home_score"] == 95
    assert fba["away_score"] == 54


def test_smf_resolves_first_baptist_aliases():
    index = build_name_index(catalog_schools())
    assert resolve_smf_name("First Baptist Christian Warriors", index) == "first-baptist-christian"
    assert resolve_smf_name("First Baptist Academy", index) == "first-baptist-christian"


def test_ranked_field_is_1_through_last_and_includes_tapps():
    teams, games, roster, panel, priors = load_uil_dataset()
    assert len(teams) == len(catalog_schools())
    assert any(t.team_id == "first-baptist-christian" for t in teams)
    table = rank_season(teams, games, roster=roster, panel=panel, priors=priors, with_movement=False)
    assert len(table) == len(teams)
    assert [row.rank for row in table] == list(range(1, len(teams) + 1))
    aquilla = next(row for row in table if row.team_id == "aquilla")
    fba = next(row for row in table if row.team_id == "first-baptist-christian")
    assert aquilla.association == "UIL"
    assert fba.association == "TAPPS"


def test_live_service_exposes_the_combined_field():
    service = LiveSeasonService.from_uil(start_week=99)
    table = service.rankings()
    assert len(table) == len(service.teams)
    assert len(table) > 159
    assert any(row.team_id == "first-baptist-christian" for row in table)
    tapps = service.rankings(association="TAPPS")
    assert tapps
    assert all(row.association == "TAPPS" for row in tapps)


def test_committed_offline_rankings_include_tapps():
    root = Path(__file__).resolve().parents[1] / "web" / "public" / "offline"
    teams = json.loads((root / "teams.json").read_text(encoding="utf-8"))["teams"]
    rankings = json.loads((root / "rankings.json").read_text(encoding="utf-8"))["rankings"]
    ids = {row["team_id"] for row in rankings}
    assert len(rankings) > 159
    assert len(teams) == len(rankings)
    assert "first-baptist-christian" in ids
    assert "aquilla" in ids
    assocs = {row.get("association") for row in rankings}
    assert "UIL" in assocs
    assert "TAPPS" in assocs
