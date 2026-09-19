"""Three-tier recursive strength-of-schedule."""

from sixman_rankings.models import EngineConfig, Game
from sixman_rankings.sos import (
    opp_opp_efficiency,
    opponent_tier_efficiency,
    recursive_quality,
    strength_of_schedule,
    team_efficiency,
    team_win_pct,
)


def _game(gid: str, home: str, away: str, hs: int, aws: int) -> Game:
    return Game(gid, 1, "2025-09-01", home, away, hs, aws)


def _mini_graph():
    games = [
        _game("a-b", "A", "B", 40, 28),
        _game("a-c", "A", "C", 36, 30),
        _game("b-d", "B", "D", 34, 28),
        _game("c-d", "C", "D", 30, 24),
        _game("d-e", "D", "E", 42, 20),
        _game("f-g", "F", "G", 56, 12),
        _game("f-h", "F", "H", 60, 8),
        _game("g-h", "G", "H", 38, 14),
    ]
    ids = ["A", "B", "C", "D", "E", "F", "G", "H"]
    return ids, games


def test_efficiency_is_mean_capped_pd():
    games = [_game("1", "A", "B", 40, 20), _game("2", "A", "C", 30, 24)]
    eff = team_efficiency(games, mercy_cap=45)
    assert eff["A"] == (20 + 6) / 2
    assert eff["B"] == -20


def test_win_pct_counts_ties_as_half():
    games = [_game("1", "A", "B", 20, 20), _game("2", "A", "C", 30, 10)]
    pct = team_win_pct(games)
    assert abs(pct["A"] - 0.75) < 1e-12


def test_direct_opponent_efficiency_and_opp_opp():
    ids, games = _mini_graph()
    cfg = EngineConfig()
    eff = team_efficiency(games, cfg.mercy_cap)
    from sixman_rankings.sos import played_opponents

    opps = played_opponents(games)
    a_direct = opponent_tier_efficiency("A", eff, opps)
    f_direct = opponent_tier_efficiency("F", eff, opps)
    assert a_direct > f_direct
    a_hop2 = opp_opp_efficiency("A", eff, opps)
    f_hop2 = opp_opp_efficiency("F", eff, opps)
    assert a_hop2 > f_hop2


def test_recursive_quality_walks_three_tiers():
    ids, games = _mini_graph()
    cfg = EngineConfig()
    from sixman_rankings.sos import played_opponents

    eff = team_efficiency(games, cfg.mercy_cap)
    opps = played_opponents(games)
    q0 = recursive_quality(eff, opps, depth=0, alpha=1.0, team_ids=ids)
    q3 = recursive_quality(eff, opps, depth=3, alpha=1.0, team_ids=ids)
    assert q0["A"] == eff["A"]
    assert q3["A"] > q3["F"]


def test_combined_sos_ranks_connected_slate_above_cupcake_slate():
    ids, games = _mini_graph()
    sos = strength_of_schedule(ids, games, EngineConfig())
    assert sos["A"] > sos["F"]


def test_teams_without_games_get_neutral_sos():
    teams = ["Z"]
    sos = strength_of_schedule(teams, [], EngineConfig())
    assert sos["Z"] == 0.0
