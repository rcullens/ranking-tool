"""Parse MaxPreps / SMF / DCTF public boards and compare them to our ranks."""

from sixman_rankings.catalog import catalog_schools
from sixman_rankings.live.source_ranks import (
    SourcePack,
    build_payload,
    compare_rows,
    parse_dctf_article_html,
    parse_dctf_grid_html,
    parse_maxpreps_division,
    parse_smf_week_html,
    pick_latest_smf_week_path,
    seed_smf_ranks,
)
from sixman_rankings.models import Team

MP_HTML = """
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"layoutProps":{"tableData":[
  {"schoolName":"Aquilla","overallStandingPlacement":12,"overallWins":3,"overallLosses":0},
  {"schoolName":"First Baptist Christian","overallStandingPlacement":4,"overallWins":3,"overallLosses":1}
]}}}}
</script>
"""

SMF_HTML = """
<h3 class="block-header">UIL Division I</h3>
<table>
<tr class="dataList-row">
  <td class="dataList-cell">7</td>
  <td class="dataList-cell">Aquilla</td>
  <td class="dataList-cell">3-0</td>
</tr>
</table>
<h3 class="block-header">TAPPS Division I</h3>
<table>
<tr class="dataList-row">
  <td class="dataList-cell">2</td>
  <td class="dataList-cell">First Baptist Christian</td>
  <td class="dataList-cell">3-1</td>
</tr>
</table>
"""

DCTF_GRID = """
<a href="/team/foo" class="c-member-grid-row">
  <span class="c-member-grid-rank">1</span>
  <div class="c-member-grid-col">Gordon</div>
  <div class="c-member-grid-col">Record: 4-0</div>
</a>
"""

DCTF_ARTICLE = """
<h2>CLASS 1A DIVISION I</h2>
<table>
<tr><th>1</th><td>Gordon (4-0)</td></tr>
<tr><th>7</th><td>Aquilla (3-0)</td></tr>
</table>
<h2>PRIVATE SCHOOLS — 6-MAN</h2>
<table>
<tr><th>1</th><td>First Baptist Christian (3-1)</td></tr>
</table>
"""


def test_parsers_map_aquilla_and_first_baptist():
    mp = parse_maxpreps_division(MP_HTML)
    smf = parse_smf_week_html(SMF_HTML)
    grid = parse_dctf_grid_html(DCTF_GRID)
    article = parse_dctf_article_html(DCTF_ARTICLE)
    assert mp["aquilla"] == 12
    assert mp["first-baptist-christian"] == 4
    assert smf["aquilla"] == 7
    assert smf["first-baptist-christian"] == 2
    assert grid["gordon"] == 1
    assert article["aquilla"] == 7
    assert article["first-baptist-christian"] == 1


def test_smf_hub_prefers_status_new():
    hub = """
    <a href="/rankings/2026/week-3/" class="week-card status-final">
    <a href="/rankings/2026/week-4/" class="week-card status-new">
    """
    path, week = pick_latest_smf_week_path(hub, 2026)
    assert path == "/rankings/2026/week-4/"
    assert week == "Week 4"


def test_compare_rows_use_ours_minus_theirs_and_nr_for_missing():
    schools = {s.team_id: s for s in catalog_schools()}
    aquilla = schools["aquilla"]
    fba = schools["first-baptist-christian"]
    teams = [
        Team(
            team_id=s.team_id,
            name=s.name,
            district=s.district,
            region=s.region,
            classification=s.classification,
            association=s.association,
            city=s.city,
        )
        for s in (aquilla, fba)
    ]
    packs = {
        "maxpreps": SourcePack("maxpreps", "MaxPreps", True, ranks={"aquilla": 12, "first-baptist-christian": 4}),
        "smf": SourcePack("smf", "SMF", True, ranks={"aquilla": 7}),
        "dctf": SourcePack("dctf", "DCTF", True, ranks={}),
    }
    rows = {row["team_id"]: row for row in compare_rows(teams, {"aquilla": 23, "first-baptist-christian": 77}, packs)}
    assert rows["aquilla"]["delta_maxpreps"] == 11
    assert rows["aquilla"]["delta_smf"] == 16
    assert rows["aquilla"]["delta_dctf"] is None
    assert rows["first-baptist-christian"]["smf"] is None
    payload = build_payload(teams, {"aquilla": 23, "first-baptist-christian": 77}, packs, week=4)
    assert len(payload["rows"]) == 2
    assert payload["sources"]["maxpreps"]["count"] == 2


def test_smf_seed_includes_aquilla_week1_rank():
    ranks = seed_smf_ranks()
    assert ranks["aquilla"] == 7
