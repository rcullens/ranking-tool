"""Classification / division tags (UIL 1A DI vs DII, TAPPS/TAIAO, plus free-form)."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable, Optional, Sequence

from sixman_rankings.catalog import association_of
from sixman_rankings.models import RankedTeam, Team

_DIII = re.compile(r"diii|\bd3\b|division\s*iii\b|division\s*3\b", re.I)
_DII = re.compile(r"dii|\bd2\b|division\s*ii\b|division\s*2\b", re.I)
_DI = re.compile(r"\bdi\b|\bd1\b|division\s*i\b|division\s*1\b", re.I)
_ASSOC = {"UIL", "TAPPS", "TAIAO", "TCAF", "TCAL", "IND"}


def division_of(tag: str) -> Optional[str]:
    """Return ``'DI'``, ``'DII'``, ``'DIII'``, or ``None`` if the tag has no division."""

    if not tag:
        return None
    if _DIII.search(tag):
        return "DIII"
    if _DII.search(tag):
        return "DII"
    if _DI.search(tag):
        return "DI"
    return None


def canonical_classification(tag: str) -> str:
    """Normalize UIL spellings to ``1A DI`` / ``1A DII``; keep TAPPS/TAIAO prefixes."""

    raw = (tag or "").strip()
    if not raw:
        return ""
    assoc = association_of(raw)
    if assoc != "UIL":
        if re.search(r"freelance", raw, re.I):
            return f"{assoc} Freelance"
        div = division_of(raw)
        if div:
            return f"{assoc} {div}"
        return assoc
    div = division_of(raw)
    if div and re.search(r"1a|six", raw, re.I):
        return f"1A {div}"
    if div and raw.upper() in {div, f"D{1 if div == 'DI' else 2}"}:
        return f"1A {div}"
    if div:
        return f"1A {div}"
    return raw


def classification_matches(team_tag: str, query: str) -> bool:
    """True when ``query`` selects ``team_tag`` (exact, association, or UIL DI/DII)."""

    if not query or not query.strip():
        return True
    q = query.strip()
    if team_tag.strip().lower() == q.lower():
        return True
    q_upper = q.upper()
    if q_upper in _ASSOC:
        return association_of(team_tag) == q_upper
    if canonical_classification(team_tag) == canonical_classification(q):
        return True
    q_div = division_of(q)
    t_div = division_of(team_tag)
    if q_div and t_div and q_div == t_div:
        # Bare "DI" / "DII" select the UIL 1A field only — TAPPS DI stays TAPPS.
        q_canon = canonical_classification(q)
        if q_canon in {f"1A {q_div}", q_div}:
            return association_of(team_tag) == "UIL"
        if canonical_classification(team_tag) == q_canon:
            return True
    return False


def filter_teams(teams: Sequence[Team], query: Optional[str]) -> list[Team]:
    if not query:
        return list(teams)
    return [t for t in teams if classification_matches(t.classification, query)]


def group_rows_by_classification(
    rows: Iterable[RankedTeam],
) -> dict[str, list[RankedTeam]]:
    groups: dict[str, list[RankedTeam]] = defaultdict(list)
    for row in rows:
        key = canonical_classification(row.classification) or row.classification or "Unclassified"
        groups[key].append(row)
    return dict(groups)
