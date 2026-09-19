"""Stable CSV / JSON export schema for sheets and downstream sites."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from sixman_rankings.constants import EXPORT_SCHEMA_VERSION
from sixman_rankings.models import RankedTeam

# Column order is part of the contract. Add at the end; do not rename.
RANKING_FIELDS: tuple[str, ...] = (
    "schema_version",
    "week",
    "season",
    "rank",
    "rank_delta",
    "team_id",
    "name",
    "district",
    "region",
    "classification",
    "record",
    "district_record",
    "wins",
    "losses",
    "ties",
    "district_wins",
    "district_losses",
    "district_ties",
    "games_played",
    "power",
    "power_delta",
    "elo",
    "sos",
    "density",
    "capped_pd",
    "raw_pd",
    "sigma",
    "confidence",
    "low_confidence",
    "turnover_decay",
    "panel_weight",
    "notes",
)


def _round_opt(value: Optional[float], digits: int) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def ranked_record(
    row: RankedTeam,
    *,
    week: Optional[int] = None,
    season: Optional[int] = None,
) -> dict[str, Any]:
    """One ranking row as a JSON-safe dict with a stable key set."""

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "week": week,
        "season": season,
        "rank": row.rank,
        "rank_delta": row.rank_delta,
        "team_id": row.team_id,
        "name": row.name,
        "district": row.district,
        "region": row.region,
        "classification": row.classification,
        "record": row.record,
        "district_record": row.district_record,
        "wins": row.wins,
        "losses": row.losses,
        "ties": row.ties,
        "district_wins": row.district_wins,
        "district_losses": row.district_losses,
        "district_ties": row.district_ties,
        "games_played": row.games_played,
        "power": round(row.power, 2),
        "power_delta": _round_opt(row.power_delta, 2),
        "elo": round(row.elo, 2),
        "sos": round(row.sos, 3),
        "density": round(row.density, 3),
        "capped_pd": round(row.capped_pd, 1),
        "raw_pd": round(row.raw_pd, 1),
        "sigma": round(row.sigma, 2),
        "confidence": round(row.confidence, 3),
        "low_confidence": bool(row.low_confidence),
        "turnover_decay": round(row.turnover_decay, 3),
        "panel_weight": round(row.panel_weight, 3),
        "notes": row.notes,
    }


def rankings_document(
    rows: Sequence[RankedTeam],
    *,
    week: Optional[int] = None,
    season: Optional[int] = None,
    classification: Optional[str] = None,
    history: Optional[Mapping[int, Sequence[RankedTeam]]] = None,
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "week": week,
        "season": season,
        "classification": classification,
        "rankings": [ranked_record(r, week=week, season=season) for r in rows],
    }
    if history is not None:
        doc["history"] = {
            str(w): [ranked_record(r, week=int(w), season=season) for r in week_rows]
            for w, week_rows in sorted(history.items(), key=lambda kv: int(kv[0]))
        }
    return doc


def write_rankings_json(
    path: str | Path,
    rows: Sequence[RankedTeam],
    **kwargs,
) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rankings_document(rows, **kwargs), indent=2) + "\n", encoding="utf-8")
    return dest


def write_rankings_csv(
    path: str | Path,
    rows: Sequence[RankedTeam],
    *,
    week: Optional[int] = None,
    season: Optional[int] = None,
) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    records = [ranked_record(r, week=week, season=season) for r in rows]
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RANKING_FIELDS))
        writer.writeheader()
        writer.writerows(records)
    return dest


def write_history_csv(
    path: str | Path,
    history: Mapping[int, Sequence[RankedTeam]],
    *,
    season: Optional[int] = None,
) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RANKING_FIELDS))
        writer.writeheader()
        for week in sorted(history):
            for row in history[week]:
                writer.writerow(ranked_record(row, week=int(week), season=season))
    return dest


def iter_ranked_dicts(rows: Iterable[RankedTeam], **kwargs) -> Iterable[dict[str, Any]]:
    for row in rows:
        yield ranked_record(row, **kwargs)
