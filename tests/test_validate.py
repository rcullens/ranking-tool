"""Validation harness against the bundled sample season."""

from sixman_rankings.cli import main
from sixman_rankings.io import load_sample_dataset
from sixman_rankings.pipeline import RankingEngine
from sixman_rankings.validate import run_validation


def test_bundled_sample_passes_expectation_cards():
    report = run_validation()
    assert report.ok, report.summary()


def test_history_attaches_week_over_week_deltas():
    teams, games, roster, panel, priors = load_sample_dataset()
    engine = RankingEngine(teams, games, roster=roster, panel=panel, priors=priors)
    hist = engine.weekly_history(4)
    assert set(hist) >= {0, 1, 4}
    week4 = hist[4]
    assert any(row.rank_delta is not None for row in week4)


def test_cli_validate_and_what_if_exit_zero():
    assert main(["validate"]) == 0
    assert main(["what-if", "--home", "borden-county", "--away", "rankin", "--margin", "20"]) == 0
