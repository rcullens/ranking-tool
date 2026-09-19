"""What-if games are provisional and leave the saved season untouched."""

from sixman_rankings.io import load_sample_dataset
from sixman_rankings.pipeline import rank_season
from sixman_rankings.whatif import scores_from_margin, simulate_what_if


def test_margin_is_capped_at_45():
    home, away = scores_from_margin(80, 45)
    assert home - away == 45


def test_what_if_is_non_destructive():
    teams, games, roster, panel, priors = load_sample_dataset()
    snapshot = [(g.game_id, g.home_score, g.away_score) for g in games]
    n = len(games)
    before_table = rank_season(
        teams, games, roster=roster, panel=panel, priors=priors, with_movement=False
    )
    report = simulate_what_if(
        teams,
        games,
        home_id="borden-county",
        away_id="darrouzett",
        margin=45,
        roster=roster,
        panel=panel,
        priors=priors,
    )
    assert len(games) == n
    assert [(g.game_id, g.home_score, g.away_score) for g in games] == snapshot
    after_table = rank_season(
        teams, games, roster=roster, panel=panel, priors=priors, with_movement=False
    )
    assert [r.power for r in before_table] == [r.power for r in after_table]
    assert report.game.game_id.startswith("whatif-")
    assert report.game.game_id not in {g.game_id for g in games}


def test_what_if_moves_the_provisional_table():
    teams, games, roster, panel, priors = load_sample_dataset()
    report = simulate_what_if(
        teams,
        games,
        home_id="darrouzett",
        away_id="borden-county",
        home_score=70,
        away_score=14,
        roster=roster,
        panel=panel,
        priors=priors,
    )
    before = report.row_before("darrouzett")
    after = report.row_after("darrouzett")
    assert before is not None and after is not None
    assert after.power > before.power
    assert (after.rank_delta or 0) >= 0
