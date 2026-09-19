"""Export schema, published tie-break, and DI/DII filtering."""

from sixman_rankings.classify import classification_matches, division_of
from sixman_rankings.export import RANKING_FIELDS, ranked_record, write_rankings_csv, write_rankings_json
from sixman_rankings.io import load_sample_dataset
from sixman_rankings.models import EngineConfig, Game, TeamState
from sixman_rankings.pipeline import rank_season
from sixman_rankings.ties import compare_states, head_to_head_cmp


def test_classification_di_vs_dii():
    assert division_of("1A DI") == "DI"
    assert division_of("1A DII") == "DII"
    assert classification_matches("1A DI", "DI")
    assert classification_matches("1A DII", "DII")
    assert not classification_matches("1A DII", "DI")
    assert classification_matches("1A Division II", "d2")


def test_split_rankings_are_within_class():
    teams, games, roster, panel, priors = load_sample_dataset()
    di = rank_season(
        teams, games, roster=roster, panel=panel, priors=priors, classification="DI", with_movement=False
    )
    dii = rank_season(
        teams, games, roster=roster, panel=panel, priors=priors, classification="DII", with_movement=False
    )
    assert {r.classification for r in di} == {"1A DI"}
    assert {r.classification for r in dii} == {"1A DII"}
    assert [r.rank for r in di] == list(range(1, len(di) + 1))
    assert len(di) + len(dii) == 20


def test_head_to_head_breaks_equal_power_and_sos():
    cfg = EngineConfig()
    a = TeamState("a", elo=1500, preseason_elo=1500, power=1600, sos=2.0, capped_pd=10)
    b = TeamState("b", elo=1500, preseason_elo=1500, power=1600, sos=2.0, capped_pd=40)
    games = [Game("h2h", 4, "2025-09-19", "a", "b", 40, 28)]
    assert head_to_head_cmp("a", "b", games) == -1
    assert compare_states(a, b, games, cfg) == -1


def test_capped_pd_breaks_when_h2h_is_empty():
    cfg = EngineConfig()
    a = TeamState("a", elo=1500, preseason_elo=1500, power=1600, sos=2.0, capped_pd=10)
    b = TeamState("b", elo=1500, preseason_elo=1500, power=1600, sos=2.0, capped_pd=40)
    assert compare_states(a, b, [], cfg) == 1


def test_export_schema_is_stable(tmp_path):
    teams, games, roster, panel, priors = load_sample_dataset()
    rows = rank_season(teams, games, roster=roster, panel=panel, priors=priors)
    rec = ranked_record(rows[0], week=9, season=2025)
    assert list(rec.keys()) == list(RANKING_FIELDS)
    json_path = write_rankings_json(tmp_path / "rankings.json", rows, week=9, season=2025)
    csv_path = write_rankings_csv(tmp_path / "rankings.csv", rows, week=9, season=2025)
    text = json_path.read_text(encoding="utf-8")
    assert '"schema_version"' in text
    assert '"rankings"' in text
    header = csv_path.read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",")[0] == "schema_version"
    assert "district_record" in header
    assert "confidence" in header


def test_district_record_is_populated_and_not_the_overall_record():
    teams, games, roster, panel, priors = load_sample_dataset()
    rows = rank_season(teams, games, roster=roster, panel=panel, priors=priors, with_movement=False)
    borden = next(r for r in rows if r.team_id == "borden-county")
    assert borden.record == "8-1"
    assert borden.district_record == "3-0"
    assert borden.district_wins == 3


def test_district_and_region_filters_rerank_locally():
    teams, games, roster, panel, priors = load_sample_dataset()
    district = rank_season(
        teams, games, roster=roster, panel=panel, priors=priors, district="8-1A DI", with_movement=False
    )
    assert {r.district for r in district} == {"8-1A DI"}
    assert [r.rank for r in district] == list(range(1, len(district) + 1))
    assert district[0].team_id == "borden-county"

    region = rank_season(
        teams,
        games,
        roster=roster,
        panel=panel,
        priors=priors,
        region="Trans Pecos",
        with_movement=False,
    )
    assert {r.region for r in region} == {"trans-pecos"}
    assert [r.rank for r in region] == list(range(1, len(region) + 1))
    assert any(r.team_id == "marathon" for r in region)
