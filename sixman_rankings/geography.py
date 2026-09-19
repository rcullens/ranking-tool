"""Geographic density coefficient for insular rural schedules.

A district that never shares non-district opponents with the rest of the
state can manufacture an undefeated record against a closed graph. The
coefficient lives in ``[density_floor, 1]`` and is multiplied onto SOS
(and, more gently, onto Elo deviation from the mean) so 10-0 inflation
in an isolated Trans-Pecos or Panhandle bubble does not become a
statewide #1.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping, Sequence

from sixman_rankings.models import EngineConfig, Game, Team


def scheduled_opponents(games: Iterable[Game]) -> dict[str, list[str]]:
    """Adjacency from the full published schedule, including unplayed weeks."""

    opps: dict[str, list[str]] = defaultdict(list)
    for game in games:
        opps[game.home_id].append(game.away_id)
        opps[game.away_id].append(game.home_id)
    return dict(opps)


def district_members(teams: Mapping[str, Team]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for tid, team in teams.items():
        groups[team.district].append(tid)
    return dict(groups)


def _unique(seq: Iterable[str]) -> set[str]:
    return set(seq)


def district_nd_window(
    district_ids: Sequence[str],
    teams: Mapping[str, Team],
    opponents: Mapping[str, Sequence[str]],
) -> set[str]:
    """Non-district opponents touched by anyone in this district."""

    district_set = set(district_ids)
    window: set[str] = set()
    for tid in district_ids:
        for opp in opponents.get(tid, ()):
            other = teams.get(opp)
            if other is None:
                continue
            if opp in district_set:
                continue
            # Also treat "same district string" as district even if id lists drift.
            if other.district == teams[tid].district:
                continue
            window.add(opp)
    return window


def geographic_density(
    team_id: str,
    teams: Mapping[str, Team],
    games: Sequence[Game],
    config: EngineConfig,
) -> float:
    """Return a coefficient in ``[config.density_floor, 1.0]``.

    Three isolation signals, equally blended after the first is emphasized:

    1. **District ND overlap** — do this district's non-district opponents
       also appear on other districts' slates? Zero overlap is the classic
       insular-rural pattern the spec calls out.
    2. **Region reach (1 hop)** — how many distinct regions do this team's
       opponents represent?
    3. **Region reach (2 hops)** — do opponents themselves leave the bubble?
    """

    if team_id not in teams:
        return 1.0

    opponents = scheduled_opponents(games)
    scheduled_n = len(opponents.get(team_id, ()))
    if scheduled_n < config.density_min_scheduled:
        return 1.0

    team = teams[team_id]
    members = [tid for tid, t in teams.items() if t.district == team.district]
    window = district_nd_window(members, teams, opponents)

    outside_nd: set[str] = set()
    for tid, t in teams.items():
        if t.district == team.district:
            continue
        for opp in opponents.get(tid, ()):
            other = teams.get(opp)
            if other is None or other.district == t.district:
                continue
            outside_nd.add(opp)

    if window:
        overlap = len(window & outside_nd) / len(window)
    else:
        # No ND opponents at all: the district is a closed loop.
        overlap = 0.0

    all_regions = {t.region for t in teams.values() if t.region}
    n_regions = max(len(all_regions), 1)

    hop1_regions = set()
    hop2_regions = set()
    for opp in _unique(opponents.get(team_id, ())):
        other = teams.get(opp)
        if other and other.region:
            hop1_regions.add(other.region)
        for hop2 in _unique(opponents.get(opp, ())):
            if hop2 == team_id:
                continue
            hop2_team = teams.get(hop2)
            if hop2_team and hop2_team.region:
                hop2_regions.add(hop2_team.region)

    region_div = len(hop1_regions) / n_regions
    hop2_div = len(hop2_regions) / n_regions

    # Overlap is the spec's primary anti-inflation lever; region reach
    # stops a district that "exchanges" one shared cupcake from looking
    # connected.
    connectivity = 0.50 * overlap + 0.25 * region_div + 0.25 * hop2_div
    connectivity = min(1.0, max(0.0, connectivity))

    # Smoothstep so middling West-Texas slates stay near 1.0 and only
    # genuine bubbles are haircut.
    x = connectivity
    smooth = x * x * (3.0 - 2.0 * x)
    return config.density_floor + (1.0 - config.density_floor) * smooth


def density_map(
    teams: Mapping[str, Team],
    games: Sequence[Game],
    config: EngineConfig,
) -> dict[str, float]:
    return {tid: geographic_density(tid, teams, games, config) for tid in teams}
