"""Bundled JSON snapshots so the Android/PWA shell works without a server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from sixman_rankings.export import ranked_record
from sixman_rankings.live.service import LiveSeasonService


def teams_payload(service: LiveSeasonService) -> dict[str, Any]:
    table = {row.team_id: row for row in service.rankings()}
    rows = []
    for team in service.teams:
        ranked = table.get(team.team_id)
        rows.append(
            {
                "team_id": team.team_id,
                "name": team.name,
                "district": team.district,
                "region": team.region,
                "classification": team.classification,
                "rank": ranked.rank if ranked else None,
                "record": ranked.record if ranked else "",
                "power": round(ranked.power, 2) if ranked else None,
            }
        )
    rows.sort(key=lambda r: (r["rank"] is None, r["rank"] if r["rank"] is not None else 10**9, r["name"]))
    return {"teams": rows}


def rankings_payload(
    service: LiveSeasonService,
    *,
    classification: Optional[str] = None,
    district: Optional[str] = None,
    region: Optional[str] = None,
) -> dict[str, Any]:
    rows = service.rankings(classification=classification, district=district, region=region)
    week = service.current_week()
    return {
        "week": week,
        "classification": classification,
        "district": district,
        "region": region,
        "rankings": [ranked_record(r, week=week, season=service.season) for r in rows],
    }


def history_payload(service: LiveSeasonService) -> dict[str, Any]:
    hist = service.history()
    return {
        "weeks": sorted(hist),
        "history": {
            str(week): [ranked_record(r, week=week, season=service.season) for r in rows]
            for week, rows in hist.items()
        },
    }


def status_payload(service: LiveSeasonService) -> dict[str, Any]:
    status = service.status().__dict__ | {"interval_sec": 300.0}
    status["provider"] = "offline-snapshot"
    status["last_result"] = "bundled snapshot · set a live server URL for Thu–Sat pulls"
    return status


def snapshot(service: LiveSeasonService) -> dict[str, Any]:
    return {
        "status": status_payload(service),
        "teams": teams_payload(service),
        "presets": {"presets": service.presets()},
        "rankings": rankings_payload(service),
        "boards": service.boards(),
        "history": history_payload(service),
    }


def write_offline_bundle(dest: Path | str, *, service: Optional[LiveSeasonService] = None) -> Path:
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True)
    payload = snapshot(service or LiveSeasonService.from_sample())
    for name, body in payload.items():
        (root / f"{name}.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return root
