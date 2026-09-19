"""35% roster-turnover decay (one-hit-wonder filter)."""

from sixman_rankings.models import EngineConfig, RosterFactor
from sixman_rankings.turnover import (
    apply_turnover_decay,
    combined_turnover,
    turnover_decay,
)


def test_near_total_turnover_strips_about_35_percent():
    cfg = EngineConfig()
    factor = RosterFactor("rankin", 2025, graduation_rate=1.0, positional_turnover=1.0)
    decay = turnover_decay(factor, cfg)
    assert abs(decay - 0.35) < 1e-9
    adjusted = apply_turnover_decay(1800, 1500, decay)
    assert abs(adjusted - 1695.0) < 1e-9


def test_sample_rankin_wipeout_hits_the_full_strip():
    cfg = EngineConfig()
    factor = RosterFactor("rankin", 2025, 0.90, 0.95)
    assert combined_turnover(factor) >= cfg.turnover_full
    assert abs(turnover_decay(factor, cfg) - cfg.turnover_strip) < 1e-9


def test_low_turnover_is_not_decayed():
    cfg = EngineConfig()
    factor = RosterFactor("borden-county", 2025, 0.22, 0.18)
    assert turnover_decay(factor, cfg) == 0.0
    assert apply_turnover_decay(1688, 1500, 0.0) == 1688


def test_mid_turnover_is_between_zero_and_full_strip():
    cfg = EngineConfig()
    factor = RosterFactor("mid", 2025, 0.70, 0.70)
    decay = turnover_decay(factor, cfg)
    assert 0.0 < decay < cfg.turnover_strip


def test_decay_is_clamped():
    assert apply_turnover_decay(1800, 1500, 2.0) == 1500
    assert apply_turnover_decay(1800, 1500, -1.0) == 1800
