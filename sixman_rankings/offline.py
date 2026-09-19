"""Bundled JSON snapshots so the Android/PWA shell works without a server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from sixman_rankings.export import ranked_record
from sixman_rankings.live.service import LiveSeasonService
from sixman_rankings.live.source_ranks import source_ranks_payload


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
                "association": getattr(team, "association", None) or "UIL",
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
    association: Optional[str] = None,
) -> dict[str, Any]:
    rows = service.rankings(
        classification=classification,
        district=district,
        region=region,
        association=association,
    )
    week = service.current_week()
    return {
        "week": week,
        "classification": classification,
        "district": district,
        "region": region,
        "association": association,
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
    meta_note = ""
    try:
        from pathlib import Path
        import json

        meta_path = Path(__file__).resolve().parent / "data" / "ingest_meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            finals = meta.get("finals")
            pulled = meta.get("pulled_at")
            meta_note = f"{finals} live finals"
            if pulled:
                meta_note += f" · ingested {pulled}"
    except Exception:  # noqa: BLE001
        meta_note = ""
    if len(service.teams) > 30:
        status["provider"] = "live-cron"
        status["last_result"] = service.last_result if service.last_result not in {"idle", ""} else (
            (meta_note + " · ") if meta_note else ""
        ) + "GitHub Actions refreshes this board Thu–Sat (America/Chicago)"
        if meta_note and "live finals" not in (status["last_result"] or ""):
            status["last_result"] = f"{status['last_result']} · {meta_note}"
    else:
        status["provider"] = "offline-snapshot"
        status["last_result"] = "bundled snapshot · set a live server URL for Thu–Sat pulls"
    return status


def snapshot(
    service: LiveSeasonService,
    *,
    pull_sources: Optional[bool] = None,
) -> dict[str, Any]:
    return {
        "status": status_payload(service),
        "teams": teams_payload(service),
        "presets": {"presets": service.presets()},
        "rankings": rankings_payload(service),
        "boards": service.boards(),
        "history": history_payload(service),
        "source_ranks": source_ranks_payload(service, pull=pull_sources, persist=False),
    }


def write_offline_bundle(
    dest: Path | str,
    *,
    service: Optional[LiveSeasonService] = None,
    pull_sources: Optional[bool] = None,
    persist_source_ranks: bool = False,
) -> Path:
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True)
    live = service or LiveSeasonService.from_sample()
    payload = snapshot(live, pull_sources=pull_sources)
    for name, body in payload.items():
        (root / f"{name}.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    if persist_source_ranks:
        from sixman_rankings.live.source_ranks import save_last_good

        try:
            save_last_good(payload["source_ranks"])
        except OSError:
            pass
    return root
