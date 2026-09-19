"""Toy-engine expected-spread updates."""

from sixman_rankings.elo import (
    apply_game_update,
    cover_multiplier,
    expected_spread,
    expected_win_probability,
    toy_update,
)
from sixman_rankings.models import EngineConfig, Game


def test_equal_ratings_neutral_expected_spread_is_zero():
    cfg = EngineConfig()
    assert abs(expected_spread(1500, 1500, cfg, hfa=0.0)) < 1e-9
    assert abs(expected_win_probability(1500, 1500, cfg.elo_scale) - 0.5) < 1e-12


def test_home_field_tilts_expected_spread():
    cfg = EngineConfig(home_field=35.0)
    home = expected_spread(1500, 1500, cfg, hfa=cfg.home_field)
    road = expected_spread(1500, 1500, cfg, hfa=0.0)
    assert home > 0
    assert abs(road) < 1e-9
    from sixman_rankings.elo import toy_update

    upd = toy_update(1500, 1500, 28, 28, cfg, neutral=True)
    assert abs(upd.expected_home_spread) < 1e-9
    hosted = toy_update(1500, 1500, 28, 28, cfg, neutral=False)
    assert hosted.expected_home_spread > 0


def test_favorite_has_positive_expected_spread():
    cfg = EngineConfig()
    mu = expected_spread(1700, 1400, cfg, hfa=0.0)
    assert mu > 20
    assert mu < cfg.mercy_cap


def test_update_is_zero_sum():
    cfg = EngineConfig()
    upd = toy_update(1500, 1500, 52, 38, cfg, neutral=True)
    assert abs(upd.home_delta + upd.away_delta) < 1e-12
    assert upd.home_delta > 0
    assert upd.actual_home_spread == 14


def test_mercy_cap_makes_72_12_identical_to_52_7():
    cfg = EngineConfig()
    blowout = toy_update(1500, 1500, 72, 12, cfg, neutral=True)
    mercy = toy_update(1500, 1500, 52, 7, cfg, neutral=True)
    assert blowout.actual_home_spread == mercy.actual_home_spread == 45
    assert abs(blowout.home_delta - mercy.home_delta) < 1e-12


def test_cover_multiplier_is_logarithmic_and_capped():
    cfg = EngineConfig()
    m0 = cover_multiplier(0, cfg)
    m_small = cover_multiplier(3, cfg)
    m_mid = cover_multiplier(20, cfg)
    m_cap = cover_multiplier(45, cfg)
    m_over = cover_multiplier(80, cfg)
    assert m0 == 1.0
    assert m_small > m0
    assert m_mid > m_small
    assert m_cap == m_over
    early = cover_multiplier(4, cfg) - cover_multiplier(1, cfg)
    late = cover_multiplier(44, cfg) - cover_multiplier(41, cfg)
    assert early > late


def test_beating_the_spread_moves_more_than_a_narrow_cover():
    cfg = EngineConfig(home_field=0.0)
    big = toy_update(1500, 1500, 52, 7, cfg, neutral=True)
    small = toy_update(1500, 1500, 28, 27, cfg, neutral=True)
    assert big.home_delta > small.home_delta * 3


def test_upset_uses_asymmetric_k():
    cfg = EngineConfig(home_field=0.0, upset_boost=0.15)
    miss = toy_update(1800, 1400, 21, 20, cfg, neutral=True)
    cover = toy_update(1800, 1400, 72, 12, cfg, neutral=True)
    assert miss.k_effective > cfg.elo_k
    assert cover.k_effective == cfg.elo_k


def test_apply_game_update_mutates_pair():
    cfg = EngineConfig()
    game = Game("g", 1, "2025-09-01", "h", "a", 48, 30, neutral=True)
    h, a, upd = apply_game_update(1500, 1500, game, cfg)
    assert h == 1500 + upd.home_delta
    assert a == 1500 + upd.away_delta
    assert h > 1500 > a
