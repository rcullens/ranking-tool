from sixman_rankings.catalog import uil_schools
from sixman_rankings.smf import build_name_index, parse_smf_week_text, resolve_smf_name


def test_aquilla_and_springlake_resolve():
    index = build_name_index(uil_schools())
    assert resolve_smf_name("#9 Aquilla Cougars", index) == "aquilla"
    assert resolve_smf_name("Springlake Earth Wolverines", index) == "springlake-earth"
    assert resolve_smf_name("Leverett's Chapel Lions", index) == "leveretts-chapel"
    assert resolve_smf_name("O'Donnell Eagles", index) == "odonnell"


def test_prairie_valley_does_not_steal_uil_valley():
    index = build_name_index(uil_schools())
    assert resolve_smf_name("Prairie Valley Bulldogs", index) is None
    assert resolve_smf_name("Valley Patriots", index) == "valley"


def test_week_text_pairs_aquilla():
    text = """
# 2026 Week 3 Scores
### Thursday night football
#9 Aquilla Cougars
64
#91 Avalon Eagles
12
"""
    games = parse_smf_week_text(text, 3)
    assert len(games) == 1
    assert games[0].home == "Aquilla Cougars"
    assert games[0].away == "Avalon Eagles"
    assert games[0].home_score == 64
    assert games[0].away_score == 12
    assert games[0].final
