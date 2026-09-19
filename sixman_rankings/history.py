"""Week-over-week movement: rank delta, power delta, notable movers."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional, Sequence

from sixman_rankings.models import RankedTeam


def attach_movement(
    current: Sequence[RankedTeam],
    previous: Optional[Sequence[RankedTeam]],
) -> list[RankedTeam]:
    """Copy ``current`` rows with rank/power deltas vs ``previous``."""

    prev_by_id = {row.team_id: row for row in (previous or [])}
    out: list[RankedTeam] = []
    for row in current:
        prior = prev_by_id.get(row.team_id)
        if prior is None:
            out.append(row)
            continue
        out.append(
            replace(
                row,
                rank_delta=prior.rank - row.rank,
                power_delta=row.power - prior.power,
                prev_rank=prior.rank,
            )
        )
    return out


def notable_movers(
    rows: Sequence[RankedTeam],
    *,
    min_rank: int = 1,
    min_power: float = 12.0,
    limit: int = 8,
) -> list[RankedTeam]:
    """Teams that jumped at least ``min_rank`` spots or ``min_power`` rating points."""

    movers = [
        row
        for row in rows
        if row.rank_delta is not None
        and (
            abs(row.rank_delta) >= min_rank
            or (row.power_delta is not None and abs(row.power_delta) >= min_power)
        )
    ]
    movers.sort(
        key=lambda r: (
            -abs(r.rank_delta or 0),
            -abs(r.power_delta or 0.0),
            r.rank,
        )
    )
    return movers[:limit]


def format_rank_delta(delta: Optional[int]) -> str:
    if delta is None:
        return "—"
    if delta > 0:
        return f"+{delta}"
    if delta < 0:
        return str(delta)
    return "—"


def normalize_place(value: str) -> str:
    """Case-insensitive slug for district / region filters."""

    return (value or "").strip().lower().replace("_", "-").replace(" ", "-")


def format_region_label(value: str) -> str:
    special = {
        "west-texas": "West Texas",
        "trans-pecos": "Trans-Pecos",
        "rolling-plains": "Rolling Plains",
        "panhandle": "Panhandle",
    }
    key = normalize_place(value)
    if key in special:
        return special[key]
    raw = (value or "").replace("-", " ").replace("_", " ").strip()
    return raw.title() if raw else "Unassigned"


def place_matches(team_value: str, query: str) -> bool:
    if not query or not query.strip():
        return True
    return normalize_place(team_value) == normalize_place(query)


def district_groups(rows: Iterable[RankedTeam]) -> dict[str, list[RankedTeam]]:
    """District W-L view — sort is district record, not power."""

    groups: dict[str, list[RankedTeam]] = {}
    for row in rows:
        groups.setdefault(row.district, []).append(row)
    for district, members in groups.items():
        members.sort(
            key=lambda r: (
                -r.district_wins,
                r.district_losses,
                -r.district_ties,
                -r.capped_pd,
                r.name,
            )
        )
        groups[district] = members
    return dict(sorted(groups.items()))


def region_groups(rows: Iterable[RankedTeam]) -> dict[str, list[RankedTeam]]:
    """Region power view — members stay in statewide power order."""

    groups: dict[str, list[RankedTeam]] = {}
    for row in rows:
        groups.setdefault(row.region, []).append(row)
    return dict(sorted(groups.items(), key=lambda kv: format_region_label(kv[0])))


def power_groups_by_district(rows: Iterable[RankedTeam]) -> dict[str, list[RankedTeam]]:
    groups: dict[str, list[RankedTeam]] = {}
    for row in rows:
        groups.setdefault(row.district, []).append(row)
    return dict(sorted(groups.items()))
