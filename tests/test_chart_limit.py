"""Mirrors web/src/chartLimit.ts — keep the compare graph at 10 series."""

CHART_TEAM_LIMIT = 10


def _sort_by_power(ids, teams):
    by_id = {t["team_id"]: t for t in teams}

    def key(tid):
        row = by_id.get(tid, {})
        power = row.get("power")
        rank = row.get("rank")
        return (
            -(power if power is not None else float("-inf")),
            rank if rank is not None else 9999,
        )

    return sorted(ids, key=key)


def top_teams_by_power(ids, teams, limit=CHART_TEAM_LIMIT):
    if len(ids) <= limit:
        return list(ids)
    return _sort_by_power(ids, teams)[:limit]


def add_chart_team(current, tid, teams, limit=CHART_TEAM_LIMIT):
    if tid in current:
        return [x for x in current if x != tid], None
    if len(current) < limit:
        return [*current, tid], None
    weakest = _sort_by_power(current, teams)[-1]
    return [x for x in current if x != weakest] + [tid], weakest


def test_large_preset_charts_only_the_strongest_ten():
    ids = [f"t{i}" for i in range(38)]
    teams = [{"team_id": f"t{i}", "power": float(i), "rank": 38 - i} for i in range(38)]
    charted = top_teams_by_power(ids, teams)
    assert len(charted) == 10
    assert charted == [f"t{i}" for i in range(37, 27, -1)]


def test_eleventh_check_drops_the_weakest_of_the_current_ten():
    teams = [
        {"team_id": "strong", "power": 1600, "rank": 1},
        {"team_id": "mid", "power": 1500, "rank": 2},
        {"team_id": "weak", "power": 1400, "rank": 3},
        {"team_id": "new", "power": 1550, "rank": 4},
    ]
    current = ["strong", "mid", "weak"] + [f"pad{i}" for i in range(7)]
    for i in range(7):
        teams.append({"team_id": f"pad{i}", "power": 1410 + i, "rank": 10 + i})
    next_ids, dropped = add_chart_team(current, "new", teams)
    assert dropped == "weak"
    assert "new" in next_ids
    assert "weak" not in next_ids
    assert len(next_ids) == 10


def test_uncheck_does_not_drop_someone_else():
    next_ids, dropped = add_chart_team(["a", "b"], "a", [])
    assert next_ids == ["b"]
    assert dropped is None
