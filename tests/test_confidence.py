"""Confidence bands shrink as games accumulate."""

from sixman_rankings.confidence import assess, rating_sigma
from sixman_rankings.io import load_sample_dataset
from sixman_rankings.models import EngineConfig
from sixman_rankings.pipeline import RankingEngine


def test_sigma_shrinks_and_confidence_rises_with_games():
    cfg = EngineConfig()
    s0 = rating_sigma(0, 1.0, cfg)
    s3 = rating_sigma(3, 1.0, cfg)
    s9 = rating_sigma(9, 1.0, cfg)
    assert s0 > s3 > s9
    c0, _, low0 = assess(0, 1.0, cfg)
    c9, _, low9 = assess(9, 1.0, cfg)
    assert c9 > c0
    assert low0 is True
    assert low9 is False


def test_sparse_density_widens_the_band():
    cfg = EngineConfig()
    connected = rating_sigma(6, 1.0, cfg)
    isolated = rating_sigma(6, 0.72, cfg)
    assert isolated > connected


def test_sample_week1_is_flagged_week9_is_not():
    teams, games, roster, panel, priors = load_sample_dataset()
    engine = RankingEngine(teams, games, roster=roster, panel=panel, priors=priors)
    week1 = engine.process_through_week(1)
    week9 = engine.process_through_week(9)
    assert all(row.low_confidence for row in week1)
    assert all(not row.low_confidence for row in week9)
    mean_sigma_1 = sum(r.sigma for r in week1) / len(week1)
    mean_sigma_9 = sum(r.sigma for r in week9) / len(week9)
    assert mean_sigma_9 < mean_sigma_1
