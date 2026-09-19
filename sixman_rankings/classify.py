"""Classification / division tags (Texas 6-man DI vs DII, plus free-form)."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable, Optional, Sequence

from sixman_rankings.models import RankedTeam, Team

_DII = re.compile(r"dii|\bd2\b|division\s*ii\b|division\s*2\b", re.I)
_DI = re.compile(r"\bdi\b|\bd1\b|division\s*i\b|division\s*1\b", re.I)
_ASSOC = re.compile(r"^(UIL|TAPPS|TAIAO|TCAF|TCAL|IND)\b", re.I)
ASSOCIATIONS = ("UIL", "TAPPS", "TAIAO", "TCAF", "TCAL", "IND")


def association_of(tag: str, fallback: str = "UIL") -> str:
    hit = _ASSOC.match((tag or "").strip())
    if hit:
        return hit.group(1).upper()
    return fallback


def division_of(tag: str) -> Optional[str]:
    """Return ``'DI'``, ``'DII'``, or ``None`` if the tag has no division."""

    if not tag:
        return None
    if _DII.search(tag):
        return "DII"
    if _DI.search(tag):
        return "DI"
    return None


def canonical_classification(tag: str) -> str:
    """Normalize common UIL six-man spellings to ``1A DI`` / ``1A DII``."""

    raw = (tag or "").strip()
    if not raw:
        return ""
    assoc = association_of(raw, "")
    if assoc and assoc != "UIL":
        return raw
    div = division_of(raw)
    if div and re.search(r"1a|six", raw, re.I):
        return f"1A {div}"
    if div and raw.upper() in {div, f"D{1 if div == 'DI' else 2}"}:
        return f"1A {div}"
    if div and not assoc:
        return f"1A {div}"
    return raw


def classification_matches(team_tag: str, query: str) -> bool:
    """True when ``query`` selects ``team_tag`` (exact, canonical, or DI/DII)."""

    if not query or not query.strip():
        return True
    q = query.strip()
    if team_tag.strip().lower() == q.lower():
        return True
    if canonical_classification(team_tag) == canonical_classification(q):
        return True
    q_div = division_of(q)
    t_div = division_of(team_tag)
    if q_div and t_div and q_div == t_div:
        # Bare "DI" / "DII" selects UIL 1A only — TAPPS/TAIAO have their own tags.
        q_canon = canonical_classification(q)
        t_canon = canonical_classification(team_tag)
        if q_canon in {f"1A {q_div}", q_div}:
            return t_canon == f"1A {q_div}"
        if t_canon == q_canon:
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
