"""45-point mercy-rule cap behavior."""

from sixman_rankings.margin import (
    cap_margin,
    game_margins,
    is_mercy_win,
    signed_capped_margin,
)
from sixman_rankings.models import Game


def test_cap_leaves_sub_mercy_margins_alone():
    assert cap_margin(30) == 30
    assert cap_margin(-12) == -12
    assert cap_margin(0) == 0


def test_cap_hard_stops_at_45():
    assert cap_margin(45) == 45
    assert cap_margin(46) == 45
    assert cap_margin(60) == 45
    assert cap_margin(72 - 12) == 45
    assert cap_margin(-80) == -45


def test_blowout_and_mercy_win_share_dominance_weight():
    # 72-12 (raw +60) and 52-7 (raw +45) are the same ranking input.
    assert signed_capped_margin(72, 12) == signed_capped_margin(52, 7) == 45


def test_game_margins_are_zero_sum_after_cap():
    game = Game("g", 1, "2025-09-01", "home", "away", 80, 10)
    home_raw, away_raw, home_capped, away_capped = game_margins(game)
    assert home_raw == 70
    assert away_raw == -70
    assert home_capped == 45
    assert away_capped == -45
    assert is_mercy_win(home_raw)


def test_custom_cap():
    assert cap_margin(50, mercy_cap=40) == 40
