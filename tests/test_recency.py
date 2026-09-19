"""Recent games must outweigh early-season tape when a half-life is set."""

from sixman_rankings.models import EngineConfig, Game, Team
from sixman_rankings.pipeline import RankingEngine
from sixman_rankings.recency import recency_weight


def test_recency_weight_decays_with_age():
    assert recency_weight(9, 9, 5.0) == 1.0
    assert recency_weight(4, 9, 5.0) == 0.5
    assert recency_weight(1, 9, 5.0) < recency_weight(8, 9, 5.0)


def test_zero_half_life_disables_decay():
    assert recency_weight(1, 9, 0.0) == 1.0
    assert recency_weight(1, 9, -3.0) == 1.0


def test_recent_result_moves_elo_more_than_an_old_mirror():
    teams = [Team("a", "A", "D", "west"), Team("b", "B", "D", "west")]
    games = [
        Game("w1", 1, "2025-08-29", "a", "b", 52, 7),
        Game("w9", 9, "2025-10-24", "b", "a", 52, 7),
    ]
    flat = RankingEngine(teams, games, config=EngineConfig(recency_half_life=0.0, panel_mix=0.0))
    recency = RankingEngine(teams, games, config=EngineConfig(recency_half_life=3.0, panel_mix=0.0))
    flat.rank(through_week=9, with_movement=False)
    recency.rank(through_week=9, with_movement=False)
    assert recency.states["b"].elo > recency.states["a"].elo
    assert recency.states["b"].elo - recency.states["a"].elo > (
        flat.states["b"].elo - flat.states["a"].elo
    )
