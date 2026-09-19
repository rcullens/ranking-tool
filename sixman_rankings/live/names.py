"""Resolve messy feed names onto our team slugs."""

from __future__ import annotations

import re
from typing import Iterable, Optional

from sixman_rankings.models import Team


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def team_aliases(team: Team) -> set[str]:
    aliases = {_norm(team.team_id), _norm(team.name), _norm(team.city)}
    aliases.discard("")
    return aliases


def build_alias_index(teams: Iterable[Team]) -> dict[str, str]:
    index: dict[str, str] = {}
    for team in teams:
        for alias in team_aliases(team):
            index[alias] = team.team_id
    return index


def resolve_team_id(raw: str, index: dict[str, str]) -> Optional[str]:
    key = _norm(raw)
    if not key:
        return None
    if key in index:
        return index[key]
    # "Borden County Coyotes" / "Gail Borden"
    for alias, tid in index.items():
        if alias and (alias in key or key in alias):
            return tid
    return None
