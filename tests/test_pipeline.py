"""End-to-end pipeline and geographic-density behavior on sample data."""

from sixman_rankings.geography import geographic_density
from sixman_rankings.io import load_sample_dataset
from sixman_rankings.models import EngineConfig, Game, Team
from sixman_rankings.pipeline import RankingEngine, rank_season


def test_sample_season_produces_a_full_table():
    teams, games, roster, panel, priors = load_sample_dataset()
    table = rank_season(teams, games, roster=roster, panel=panel, priors=priors)
    assert len(table) == 20
    assert [row.rank for row in table] == list(range(1, 21))
    records = {row.team_id: row.record for row in table}
    assert records["borden-county"] == "8-1"
    assert records["sterling-city"] == "8-1"
    assert records["follett"] == "8-1"
    assert records["marathon"] == "9-0"


def test_insular_undefeated_does_not_outrank_connected_eight_and_ones():
    teams, games, roster, panel, priors = load_sample_dataset()
    table = rank_season(teams, games, roster=roster, panel=panel, priors=priors)
    by_id = {row.team_id: row for row in table}
    marathon = by_id["marathon"]
    assert marathon.density < by_id["borden-county"].density
    assert marathon.density < 0.85
    assert "insular" in marathon.notes
    assert marathon.rank > by_id["borden-county"].rank
    assert marathon.rank > by_id["sterling-city"].rank
    assert marathon.rank > by_id["follett"].rank


def test_rankin_opens_decayed_off_the_one_hit_wonder_prior():
    teams, games, roster, panel, priors = load_sample_dataset()
    engine = RankingEngine(teams, games, roster=roster, panel=panel, priors=priors)
    pre = engine.states["rankin"]
    assert pre.turnover_decay == 0.35
    assert abs(pre.preseason_elo - 1672.25) < 1e-6


def test_week_over_week_is_deterministic_and_monotonic_in_games():
    teams, games, roster, panel, priors = load_sample_dataset()
    engine = RankingEngine(teams, games, roster=roster, panel=panel, priors=priors)
    week3 = engine.process_through_week(3)
    week9 = engine.process_through_week(9)
    played3 = {row.team_id: row.games_played for row in week3}
    played9 = {row.team_id: row.games_played for row in week9}
    assert all(played3[tid] == 3 for tid in played3)
    assert all(played9[tid] == 9 for tid in played9)
    week3_again = engine.process_through_week(3)
    assert [r.power for r in week3] == [r.power for r in week3_again]


def test_capped_pd_is_strictly_smaller_than_raw_for_marathon():
    teams, games, roster, panel, priors = load_sample_dataset()
    table = rank_season(teams, games, roster=roster, panel=panel, priors=priors)
    marathon = next(r for r in table if r.team_id == "marathon")
    assert marathon.raw_pd > marathon.capped_pd
    assert marathon.capped_pd <= 9 * 45


def test_density_closed_district_vs_crossover_district():
    teams = {
        "a": Team("a", "A", "D1", "bubble"),
        "b": Team("b", "B", "D1", "bubble"),
        "c": Team("c", "C", "D2", "plains"),
        "d": Team("d", "D", "D2", "plains"),
        "e": Team("e", "E", "D3", "west"),
        "f": Team("f", "F", "D3", "west"),
    }
    games = [
        Game("1", 1, "d", "a", "b", 40, 20),
        Game("2", 1, "d", "b", "a", 30, 28),
        Game("3", 1, "d", "c", "e", 34, 30),
        Game("4", 1, "d", "d", "f", 28, 24),
        Game("5", 1, "d", "e", "d", 36, 22),
        Game("6", 1, "d", "f", "c", 32, 30),
        Game("7", 1, "d", "c", "d", 40, 14, district_game=True),
        Game("8", 1, "d", "e", "f", 38, 20, district_game=True),
    ]
    cfg = EngineConfig(density_min_scheduled=2)
    bubble = geographic_density("a", teams, games, cfg)
    connected = geographic_density("c", teams, games, cfg)
    assert bubble < connected
    assert bubble <= cfg.density_floor + 0.05
